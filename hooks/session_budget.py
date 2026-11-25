#!/usr/bin/env python3
"""PostToolUse / PostToolUseFailure hook: tell a pipeline agent when its session is over budget.

A pipeline run (plane-conductor sets WORKSPACE_SLUG on every spawn) gets a
message in its context once the session passes the context budget or the time
budget, and again every further REMIND_K of context or REMIND_MIN minutes —
only coder roles (CODERS), the ones that follow agent-base §9.5 step 3a:

    SESSION BUDGET REACHED (...). agent-base §9.5 step 3a: ...

Context = input + cache_read + cache_creation tokens of the last assistant
message that carries `usage` in the transcript. The context budget counts the
growth since the baseline: the context at the session's first successful PLAN
write (BASELINE_TOOL — the coder writes or ticks its PLAN there). Entering a
task (prompt, agent-base, the task, the KB) costs 100-170k by itself, so an
absolute threshold fired before the first step had started. No PLAN write yet
-> no context message; the time budget still applies. Time = now minus the
timestamp of the first transcript entry that has one.

Budgets: SDLC_CONTEXT_GROWTH_K (default 60, about two PLAN steps) and
SDLC_TIME_BUDGET_MIN (default 30). Interactive sessions (no WORKSPACE_SLUG)
are left alone. Re-check them with tools/session_stats.py.

Fails open: any error -> exit 0, no output. It never blocks a tool.
"""

import fcntl
import json
import os
import sys
import tempfile
import time
from datetime import datetime

CHUNK = 256 * 1024
# Roles that follow agent-base §9.5 step 3a; others get no message.
CODERS = ("django-developer", "react-developer", "vue-developer", "devops-engineer")
REMIND_K = 25
REMIND_MIN = 10
BASELINE_TOOL = "mcp__plane-tower__update_sub_issue_description"


def _int_env(name, default):
    try:
        return max(1, int(os.environ.get(name, default)))
    except ValueError:
        return default


def _usage_total(raw):
    try:
        entry = json.loads(raw)
    except ValueError:
        return 0
    if entry.get("type") != "assistant":
        return 0
    usage = (entry.get("message") or {}).get("usage") or {}
    return (
        usage.get("input_tokens", 0)
        + usage.get("cache_read_input_tokens", 0)
        + usage.get("cache_creation_input_tokens", 0)
    )


def context_tokens(path):
    """Context of the last assistant message with usage, reading back by chunks.

    A line cut at a chunk start is carried into the next (earlier) read, so a
    large tool result never hides the usage line behind it.
    """
    with open(path, "rb") as f:
        end = os.fstat(f.fileno()).st_size
        carry = b""
        while end > 0:
            start = max(0, end - CHUNK)
            f.seek(start)
            lines = (f.read(end - start) + carry).split(b"\n")
            carry = lines.pop(0) if start > 0 else b""
            for raw in reversed(lines):
                if b'"usage"' in raw:
                    total = _usage_total(raw)
                    if total:
                        return total
            end = start
        if carry and b'"usage"' in carry:
            return _usage_total(carry) or None
    return None


def head_info(path):
    """(start time, agent) from the first entries: the first timestamp and the
    `agentSetting` of the `agent-setting` entry (e.g. «sdlc-agents:django-developer»)."""
    started = agent = None
    with open(path, "rb") as f:
        for _ in range(200):
            raw = f.readline()
            if not raw or (started and agent):
                break
            try:
                entry = json.loads(raw)
            except ValueError:
                continue
            if not isinstance(entry, dict):
                continue
            if agent is None and entry.get("type") == "agent-setting":
                agent = entry.get("agentSetting")
            if started is None and entry.get("timestamp"):
                started = datetime.fromisoformat(entry["timestamp"]).timestamp()
    return started, agent


def _state_path(session_id):
    safe = "".join(c for c in session_id if c.isalnum() or c in "-_") or "unknown"
    return os.path.join(tempfile.gettempdir(), f"sdlc-budget-{safe}.json")


def _load_state(path):
    try:
        with open(path) as f:
            state = json.load(f)
        return state if isinstance(state, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_state(path, state):
    # Atomic: two hooks racing never leave a half-written file.
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".sdlc-budget-")
    with os.fdopen(fd, "w") as f:
        json.dump(state, f)
    os.replace(tmp, path)


def decide(transcript, session_id, now=None, emit=None, tool_name=None):
    """Find the message to add; hand it to `emit` before the state is saved.

    The state file is read, changed and written under an exclusive lock, so
    hooks running at the same time never both fire or overwrite each other.
    It is written after `emit`, so a hook killed before its output is out
    fires again on the next call instead of going quiet. `tool_name` is the
    tool of a successful call (None for a failed one); BASELINE_TOOL sets the
    baseline once.
    """
    started, agent = head_info(transcript)
    if not agent or agent.split(":")[-1] not in CODERS:
        return None
    growth_k = _int_env("SDLC_CONTEXT_GROWTH_K", 60)
    budget_min = _int_env("SDLC_TIME_BUDGET_MIN", 30)
    ctx = context_tokens(transcript)
    now = time.time() if now is None else now
    ctx_k = ctx // 1000 if ctx else None
    minutes = int((now - started) // 60) if started else None
    over_time = minutes is not None and minutes >= budget_min
    marker = tool_name == BASELINE_TOOL and ctx_k is not None

    path = _state_path(session_id)
    state = _load_state(path)  # unlocked peek: most calls change nothing
    base_k = state.get("base_k")
    over_ctx = (
        isinstance(base_k, int) and ctx_k is not None and ctx_k >= base_k + growth_k
    )
    if not (over_ctx or over_time or (marker and not isinstance(base_k, int))):
        return None

    with open(path + ".lock", "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = _load_state(path)
        base_k = state.get("base_k")
        if not isinstance(base_k, int):
            if not marker:
                base_k = None
            else:
                base_k = state["base_k"] = ctx_k
                _save_state(path, state)
        over_ctx = (
            base_k is not None and ctx_k is not None and ctx_k >= base_k + growth_k
        )
        if not (over_ctx or over_time):
            return None
        last_k = state.get("last_k")
        last_min = state.get("last_min")
        fire = False
        if over_ctx and (not isinstance(last_k, int) or ctx_k >= last_k + REMIND_K):
            state["last_k"] = ctx_k
            fire = True
        if over_time and (
            not isinstance(last_min, int) or minutes >= last_min + REMIND_MIN
        ):
            state["last_min"] = minutes
            fire = True
        if not fire:
            return None
        message = _message(ctx_k, base_k, growth_k, minutes, budget_min)
        if emit:
            emit(message)
        _save_state(path, state)
        return message


def _message(ctx_k, base_k, growth_k, minutes, budget_min):
    parts = []
    if ctx_k is not None and base_k is not None:
        parts.append(
            f"context +{ctx_k - base_k}k / +{growth_k}k since the first PLAN write"
        )
    if minutes is not None:
        parts.append(f"{minutes} min / {budget_min} min")
    return (
        f"SESSION BUDGET REACHED ({', '.join(parts)}). agent-base §9.5 step 3a: "
        "finish the step in progress (the first step of a session always runs), tick it, "
        "update your status line, hand off to yourself on the spawn issue, stop. "
        "Do not start another step or the final pass."
    )


def main():
    if not os.environ.get("WORKSPACE_SLUG"):
        return
    try:
        data = json.load(sys.stdin)
        if data.get("agent_id"):
            return  # a subagent's call: the coder's own calls carry the message
        transcript = data.get("transcript_path")
        if not transcript or not os.path.isfile(transcript):
            return
        tool = data.get("tool_name") if _event() == "PostToolUse" else None
        decide(
            transcript,
            str(data.get("session_id") or "unknown"),
            emit=_emit,
            tool_name=tool,
        )
    except Exception:  # noqa: BLE001 — fail open, never block a tool
        return


EVENTS = ("PostToolUse", "PostToolUseFailure")


def _event():
    # hooks.json passes the event name; the output must name the same event.
    return sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in EVENTS else "PostToolUse"


def _emit(message):
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": _event(),
                "additionalContext": message,
            }
        },
        sys.stdout,
    )
    sys.stdout.flush()


if __name__ == "__main__":
    main()
