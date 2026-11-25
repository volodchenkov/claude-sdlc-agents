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
import shlex
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


def codex_mode(cmd):
    """'plan' / 'diff' when a shell command runs codex-review, else None.

    Only a command word counts — «echo 'codex-review --plan'» runs nothing.
    Leading wrappers, their options and VAR=value words are skipped.
    """
    for seg in re.split(r"&&|\|\||[;|&\n(]", cmd):
        try:
            words = shlex.split(seg)
        except ValueError:
            continue
        while words and (
            "=" in words[0]
            or words[0] in WRAPPERS
            or words[0].startswith("-")
            or words[0].replace(".", "").isdigit()
        ):
            words.pop(0)
        if words and os.path.basename(words[0]) == "codex-review":
            return "plan" if "--plan" in words[1:] else "diff"
    return None


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


def bill(entries, since, seen, own_role=None):
    """Token sums and counts of the assistant messages at or after `since`.

    Claude Code writes each content block of one message as its own entry,
    every one with the same id and usage: usage counts once per message id,
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
        if isinstance(usage, dict) and (key == (None, None) or key not in seen):
            seen.add(key)
            for kind, field in USAGE.items():
                v = usage.get(field)
                out[kind] += v if isinstance(v, int) else 0
        for part in msg.get("content") or []:
            if not isinstance(part, dict) or part.get("type") != "tool_use":
                continue
            tid = ("tool", part.get("id"))
            if part.get("id") and tid in seen:
                continue
            seen.add(tid)
            inp = part.get("input") if isinstance(part.get("input"), dict) else {}
            name = str(part.get("name", ""))
            mode = codex_mode(str(inp.get("command", ""))) if name == "Bash" else None
            if mode:
                out["codex_" + mode] += 1
            elif name.endswith("request_handoff") and own_role:
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
    pattern = os.path.join(os.path.expanduser(root), "*", "*.jsonl")
    for path in sorted(glob.glob(pattern)):
        subs = [
            p
            for p in sorted(
                glob.glob(os.path.join(path[: -len(".jsonl")], "subagents", "*.jsonl"))
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
            bill(entries, since, seen, own_role=role)
            if main_fresh
            else collections.Counter()
        )
        if any(main[k] for k in KINDS + COUNTS):
            rows.append(dict(base, role=role, sub=False, bill=main))
        for sub in subs:
            sbill = bill(_load(sub), since, seen)
            if any(sbill[k] for k in KINDS + COUNTS):
                rows.append(dict(base, role=role + " [sub]", sub=True, bill=sbill))
    return rows


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
