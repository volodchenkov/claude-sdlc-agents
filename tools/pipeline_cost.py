#!/usr/bin/env python3
"""Token cost of pipeline runs, from Claude Code transcripts (read-only).

Run on the pipeline host:

    python3 -I tools/pipeline_cost.py [--hours 24 | --since 2026-11-25T07:00] [--root ~/.claude/projects] [--json]

A pipeline run is a transcript whose first user message starts with
«Triggered as @<nick>» (plane-conductor's spawn prompt); its «Issue UUID»
names the issue it was spawned on. Every other transcript counts as
interactive. A subagent transcript (<run>/subagents/*.jsonl) is billed to its
parent run, as «<role> [sub]».

Per kind, role, project and issue: sessions, cache write, cache read, input
and output tokens, self-handoffs (`request_handoff` to the own role) and
`codex-review` runs (diff / --plan). Tokens are summed once per assistant
message (message id + request id): a streamed message repeats its usage.

How Anthropic converts these token kinds into plan limits is not published;
the four kinds are printed apart.
"""

import argparse
import collections
import glob
import json
import os
import re
import sys
from datetime import UTC, datetime, timedelta

USAGE = {
    "cache_write": "cache_creation_input_tokens",
    "cache_read": "cache_read_input_tokens",
    "input": "input_tokens",
    "output": "output_tokens",
}
KINDS = tuple(USAGE)
COUNTS = ("codex_diff", "codex_plan", "self_handoffs")
SPAWN = re.compile(r"Triggered as @(\w+)")
ISSUE = re.compile(r"Issue UUID:\s*([0-9a-f-]{36})")


def _ts(entry):
    raw = entry.get("timestamp")
    if not isinstance(raw, str):
        return None
    try:
        ts = datetime.fromisoformat(raw)
    except ValueError:
        return None
    return ts if ts.tzinfo else ts.replace(tzinfo=UTC)


UNREADABLE = []  # transcripts that could not be read: named on stderr
BROKEN = [0]  # records that are not JSON (a run killed mid-write): counted on stderr


def _load(path):
    entries = []
    try:
        with open(path, "rb") as f:
            for line in f:
                try:
                    entry = json.loads(line.decode("utf-8"))
                except ValueError:  # incl. UnicodeDecodeError: a cut-off record
                    BROKEN[0] += 1
                    continue
                if isinstance(entry, dict):
                    entries.append(entry)
    except OSError:
        UNREADABLE.append(path)
    return entries


def _text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            b.get("text", "")
            for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        )
    return ""


WRAPPERS = {"timeout", "nohup", "env", "time", "nice"}
# reserved words a command may follow: if true; then codex-review; fi
KEYWORDS = {"if", "then", "else", "elif", "while", "until", "do", "!", "{"}
DURATION = re.compile(r"^\d+(\.\d+)?[smhd]?$")  # GNU timeout: 10, 1.5, 10m
OPS = "<>&|;"  # runs of these are one operator; ( ) and newline stand alone
DQ_ESCAPES = '"\\$`'


def _array_end(cmd, i):
    """Index after the «)» that closes the array opened at cmd[i]; quotes and
    nested parentheses are skipped. Its values are data: a command
    substitution inside one is not counted."""
    depth, quote, j = 0, None, i
    while j < len(cmd):
        c = cmd[j]
        if c == "\\" and quote != "'":
            j += 2
            continue
        if quote:
            quote = None if c == quote else quote
        elif c in "'\"":
            quote = c
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if not depth:
                return j + 1
        j += 1
    return len(cmd)


def _tokens(cmd):
    """Bash tokens of `cmd`: ("w", word) with quotes removed, or ("op", text).

    Single and double quotes, backslashes (a backslash-newline joins lines),
    `#` comments at the start of a word, and heredoc bodies (skipped) follow
    bash. A «$(…)» inside double quotes is scanned as its own command list:
    its quotes nest, and its commands are tokens too.
    """
    return _scan(cmd, 0, False)[0]


def _arith(cmd, i, _sub=True):
    """(tokens, index after the closing «))») of the arithmetic «$((» whose
    second «(» is cmd[i]. Its words are numbers and operators, not commands;
    each «$( )» inside is scanned by `_scan`, so its quotes nest."""
    toks, depth, n = [], 0, len(cmd)
    i += 1
    while i < n:
        if cmd[i : i + 2] == "$(":
            inner, i = (_arith if cmd[i + 2 : i + 3] == "(" else _scan)(
                cmd, i + 2, True
            )
            toks += [("op", "\n"), *inner]
            continue
        c = cmd[i]
        if c == ")" and not depth and cmd[i + 1 : i + 2] == ")":
            return toks, i + 2
        depth += (c == "(") - (c == ")")
        i += 1
    return toks, n


def _scan(cmd, i, sub):
    """(tokens, index after the scan) from cmd[i]; `sub` = inside «$(», which
    ends at its unmatched «)»."""
    toks, nested, heredocs, word = [], [], [], None
    want_delim = None  # after «<<» / «<<-»: the operator whose delimiter comes next
    depth, n = 0, len(cmd)

    def end_word():
        nonlocal word, want_delim
        if word is not None:
            toks.append(("w", "".join(word)))
            if want_delim:
                heredocs.append((toks[-1][1], want_delim == "<<-"))
                want_delim = None
            word = None

    while i < n:
        c = cmd[i]
        if c == "\\":
            if cmd[i + 1 : i + 2] != "\n":
                word = (word or []) + [cmd[i + 1 : i + 2]]
            i += 2
        elif c == "'":
            j = cmd.find("'", i + 1)
            j = n if j < 0 else j
            word = (word or []) + [cmd[i + 1 : j]]
            i = j + 1
        elif c == '"':
            word = word or []
            i += 1
            while i < n and cmd[i] != '"':
                if cmd[i : i + 2] == "$(":
                    inner, j = (_arith if cmd[i + 2 : i + 3] == "(" else _scan)(
                        cmd, i + 2, True
                    )
                    nested += [("op", "\n"), *inner]
                    word.append(cmd[i:j])
                    i = j
                elif cmd[i] == "\\" and cmd[i + 1 : i + 2] in (*DQ_ESCAPES, "\n"):
                    word.append(cmd[i + 1] if cmd[i + 1] != "\n" else "")
                    i += 2
                else:
                    word.append(cmd[i])
                    i += 1
            i += 1
        elif c in " \t\r":
            end_word()
            i += 1
        elif c == "#" and word is None:
            j = cmd.find("\n", i)
            i = n if j < 0 else j
        elif c == "\n":
            end_word()
            toks.append(("op", "\n"))
            i += 1
            for delim, tabs in heredocs:  # the body runs to the delimiter line
                while i < n:
                    j = cmd.find("\n", i)
                    line, i = (cmd[i:], n) if j < 0 else (cmd[i:j], j + 1)
                    if (line.lstrip("\t") if tabs else line) == delim:
                        break
            heredocs = []
        elif c == "(" and word and word[-1].endswith("="):  # name=(…): array values
            j = _array_end(cmd, i)
            word.append(cmd[i:j])
            i = j
        elif sub and c == ")" and not depth:
            end_word()
            return toks + nested, i + 1
        elif c in OPS or c in "()":
            end_word()
            depth += (c == "(") - (c == ")")
            j = i + 1
            while c in OPS and j < n and cmd[j] in OPS:
                j += 1
            if cmd[i:j] == "<<":
                j += cmd[j : j + 1] == "-"
                want_delim = cmd[i:j]
            toks.append(("op", cmd[i:j]))
            i = j
        else:
            word = (word or []) + [c]
            i += 1
    end_word()
    return toks + nested, n


def _commands(cmd):
    """Word lists of the simple commands in `cmd`; a redirect's target is no word."""
    words, target = [], False
    for kind, tok in _tokens(cmd):
        if kind == "op":
            if "<" in tok or ">" in tok:
                target = True
                continue
            yield words
            words, target = [], False
        elif target:
            target = False
        else:
            words.append(tok)
    yield words


# options of timeout / nice / env / time that take the next word as their value
WRAPPER_ARGS = {"-s", "--signal", "-k", "--kill-after", "-n", "--adjustment"}
WRAPPER_ARGS |= {"-u", "--unset", "-C", "--chdir", "-f", "--format", "-o", "--output"}


def codex_modes(cmd):
    """'plan' / 'diff' for each codex-review run in a shell command.

    Only a command word counts — «echo 'codex-review --plan'» runs nothing.
    Leading reserved words, wrappers, their options (with values) and
    durations, and VAR=value words are skipped.
    """
    modes = []
    for words in _commands(cmd):
        while words and (
            "=" in words[0]
            or words[0] in WRAPPERS
            or words[0] in KEYWORDS
            or words[0].startswith("-")
            or DURATION.match(words[0])
        ):
            del words[: 2 if words[0] in WRAPPER_ARGS else 1]
        if words and os.path.basename(words[0]) == "codex-review":
            modes.append("plan" if "--plan" in words[1:] else "diff")
    return modes


def describe(entries):
    """(role, issue uuid or None, pipeline run?) of a top-level transcript."""
    role = next(
        (e.get("agentSetting") for e in entries if e.get("type") == "agent-setting"),
        None,
    )
    first = next((e for e in entries if e.get("type") == "user"), None)
    text = _text((first.get("message") or {}).get("content")) if first else ""
    spawn = SPAWN.match(text)
    issue = ISSUE.search(text) if spawn else None
    role = (role or (spawn.group(1) if spawn else "plain")).split(":")[-1]
    return role, issue.group(1) if issue else None, bool(spawn)


def bill(entries, since, seen, outputs, own_role=None):
    """Token sums and counts of the assistant messages at or after `since`.

    Claude Code writes each content block of one message as its own entry,
    every one with the same id and usage: usage counts once per message id
    (output at its largest count: an early entry may hold a partial one),
    tool calls once per tool_use id.
    """
    out = collections.Counter()
    for e in entries:
        if e.get("type") != "assistant":
            continue
        ts = _ts(e)
        if ts is None or ts < since:
            continue
        msg = e.get("message") or {}
        key = (msg.get("id"), e.get("requestId"))
        usage = msg.get("usage")
        # The usage of a message counts once: at its first entry that has one.
        if isinstance(usage, dict):
            v = usage.get(USAGE["output"])
            v = v if isinstance(v, int) else 0
            if key == (None, None) or key not in seen:
                seen.add(key)
                for kind, field in USAGE.items():
                    if kind != "output":
                        n = usage.get(field)
                        out[kind] += n if isinstance(n, int) else 0
                out["output"] += v
                if key != (None, None):
                    outputs[key] = [out, v]  # the bill that holds this message
            elif key in outputs and v > outputs[key][1]:
                held, old = outputs[key]
                held["output"] += v - old  # a later entry, maybe another transcript
                outputs[key][1] = v
        for part in msg.get("content") or []:
            if not isinstance(part, dict) or part.get("type") != "tool_use":
                continue
            tid = ("tool", part.get("id"))
            if part.get("id") and tid in seen:
                continue
            seen.add(tid)
            inp = part.get("input") if isinstance(part.get("input"), dict) else {}
            name = str(part.get("name", ""))
            modes = codex_modes(str(inp.get("command", ""))) if name == "Bash" else []
            for mode in modes:
                out["codex_" + mode] += 1
            if modes:
                continue
            if name.endswith("request_handoff") and own_role:
                out["self_handoffs"] += inp.get("target_role") == own_role
    return out


def _fresh(path, since):
    try:
        return os.path.getmtime(path) >= since.timestamp()
    except OSError:
        return False


def collect(root, since):
    """Rows per session and subagent with tokens after `since`.

    The modification time filters each file on its own: a subagent written
    after `since` counts even when its parent transcript was idle since.
    """
    rows = []
    seen = set()
    outputs = {}  # message key -> [bill holding it, largest output count]
    pattern = os.path.join(os.path.expanduser(root), "*", "*.jsonl")
    for path in sorted(glob.glob(pattern)):
        subs = [
            p
            for p in sorted(
                glob.glob(  # workflow agents nest: subagents/workflows/<run>/
                    os.path.join(path[: -len(".jsonl")], "subagents", "**", "*.jsonl"),
                    recursive=True,
                )
            )
            if _fresh(p, since)
        ]
        main_fresh = _fresh(path, since)
        if not (main_fresh or subs):
            continue
        entries = _load(path)  # read even when only a subagent is fresh: role, issue
        role, issue, pipeline = describe(entries)
        project = re.sub(
            r"^-home-[^-]+-(Projects-)?", "", os.path.basename(os.path.dirname(path))
        )
        base = {"issue": issue, "pipeline": pipeline, "project": project or "~"}
        main = (
            bill(entries, since, seen, outputs, own_role=role)
            if main_fresh
            else collections.Counter()
        )
        rows.append(dict(base, role=role, sub=False, bill=main))
        for sub in subs:
            sbill = bill(_load(sub), since, seen, outputs)
            rows.append(dict(base, role=role + " [sub]", sub=True, bill=sbill))
    # empty rows go only now: a later duplicate may still raise a row's output
    return [r for r in rows if any(r["bill"][k] for k in KINDS + COUNTS)]


def group(rows, key):
    agg = collections.defaultdict(collections.Counter)
    for r in rows:
        a = agg[key(r)]
        a["sessions"] += not r["sub"]
        a["subagents"] += r["sub"]
        for f in KINDS + COUNTS:
            a[f] += r["bill"].get(f, 0)
    return agg


def _m(n):
    return f"{n / 1e6:.2f}M"


VIEWS = (
    ("kind", lambda r: "pipeline" if r["pipeline"] else "interactive"),
    ("role", lambda r: r["role"]),
    ("project", lambda r: r["project"]),
    ("issue", lambda r: f"{r['issue'][:8]} ({r['project']})" if r["issue"] else "-"),
)


def report(rows, top):
    tot = group(rows, lambda r: "all").get("all", collections.Counter())
    total = (
        f"total: {tot['sessions']} sessions, {tot['subagents']} subagents; "
        f"cache write {_m(tot['cache_write'])}, cache read {_m(tot['cache_read'])}, "
        f"input {_m(tot['input'])}, output {_m(tot['output'])}"
    )
    lines = [total]
    head = f"  {'':34} {'sess':>5} {'sub':>4} {'c.write':>8} {'w/sess':>7} {'c.read':>8} {'input':>7} {'output':>7} {'self-ho':>7} {'cx diff':>7} {'cx plan':>7}"
    for name, key in VIEWS:
        agg = group(rows, key)
        lines += [
            f"\nby {name} (sorted by cache write; w/sess = cache write per session, or per subagent)",
            head,
        ]
        for k, v in sorted(agg.items(), key=lambda kv: -kv[1]["cache_write"])[:top]:
            per = v["cache_write"] // max(v["sessions"] or v["subagents"], 1) // 1000
            lines.append(
                f"  {str(k)[:34]:34} {v['sessions']:>5} {v['subagents']:>4} {_m(v['cache_write']):>8} {per:>6}k "
                f"{_m(v['cache_read']):>8} {_m(v['input']):>7} {_m(v['output']):>7} {v['self_handoffs']:>7} {v['codex_diff']:>7} {v['codex_plan']:>7}"
            )
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    when = ap.add_mutually_exclusive_group()
    when.add_argument("--hours", type=float, default=24)
    when.add_argument("--since", help="ISO time; UTC when it has no offset")
    ap.add_argument("--root", default="~/.claude/projects")
    ap.add_argument("--top", type=int, default=12)
    ap.add_argument("--json", action="store_true", help="one JSON object per session")
    args = ap.parse_args()
    if args.since:
        since = datetime.fromisoformat(args.since)
        since = since if since.tzinfo else since.replace(tzinfo=UTC)
    else:
        since = datetime.now(UTC) - timedelta(hours=args.hours)
    if not os.path.isdir(os.path.expanduser(args.root)):
        ap.error(f"no such directory: {args.root}")
    rows = collect(args.root, since)
    if BROKEN[0]:
        print(
            f"note: {BROKEN[0]} records were not JSON and are not counted",
            file=sys.stderr,
        )
    if UNREADABLE:
        print(
            f"WARNING: {len(UNREADABLE)} transcripts unreadable, not counted: {UNREADABLE[:3]}",
            file=sys.stderr,
        )
    if args.json:
        for r in rows:
            print(json.dumps(dict(r, bill=dict(r["bill"]))))
        return
    print(f"since {since.isoformat(timespec='minutes')}")
    print(report(rows, args.top))


if __name__ == "__main__":
    main()
