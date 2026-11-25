"""Tests for hooks/session_budget.py (the PostToolUse session-budget hook).

Run: python3 -I -m unittest discover -s tools -p 'test_*.py'
"""

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import UTC, datetime

HOOK = os.path.join(os.path.dirname(__file__), "..", "hooks", "session_budget.py")
PLAN_WRITE = "mcp__plane-tower__update_sub_issue_description"


def iso(ts):
    return datetime.fromtimestamp(ts, UTC).isoformat().replace("+00:00", "Z")


def assistant(ctx_tokens, ts):
    return {
        "type": "assistant",
        "timestamp": iso(ts),
        "message": {
            "usage": {
                "input_tokens": 4,
                "cache_read_input_tokens": ctx_tokens - 4,
                "cache_creation_input_tokens": 0,
            }
        },
    }


class Hook(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.transcript = os.path.join(self.dir, "t.jsonl")
        self.env = dict(os.environ, WORKSPACE_SLUG="coinex", TMPDIR=self.dir)
        self.env.pop("SDLC_CONTEXT_GROWTH_K", None)
        self.env.pop("SDLC_TIME_BUDGET_MIN", None)

    def write(self, entries, agent="sdlc-agents:django-developer"):
        head = [{"type": "agent-setting", "agentSetting": agent}] if agent else []
        with open(self.transcript, "w") as f:
            f.writelines(
                (e if isinstance(e, str) else json.dumps(e)) + "\n"
                for e in head + entries
            )

    def run_hook(self, session="s1", env=None, stdin=None, tool="Bash"):
        payload = (
            stdin
            if stdin is not None
            else json.dumps(
                {
                    "transcript_path": self.transcript,
                    "session_id": session,
                    "tool_name": tool,
                }
            )
        )
        r = subprocess.run(
            [sys.executable, "-I", HOOK],
            input=payload,
            capture_output=True,
            text=True,
            check=False,
            env=env or self.env,
            timeout=30,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        return (
            json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
            if r.stdout
            else None
        )

    def test_below_budget_silent(self):
        now = time.time()
        self.write(
            [{"type": "user", "timestamp": iso(now - 60)}, assistant(50_000, now)]
        )
        self.assertIsNone(self.run_hook())

    def baseline(self, ctx, session="s1", now=None):
        now = time.time() if now is None else now
        start = {"type": "user", "timestamp": iso(now - 60)}
        self.write([start, assistant(ctx, now)])
        self.assertIsNone(self.run_hook(session=session, tool=PLAN_WRITE))
        return start

    def test_entry_cost_alone_never_fires(self):
        # COINEX-293: entering the task cost 102k and the message came 19 s in,
        # before the first step; 19 sessions of one step each.
        now = time.time()
        start = {"type": "user", "timestamp": iso(now - 60)}
        self.write([start, assistant(250_000, now)])
        self.assertIsNone(self.run_hook())

    def test_over_growth_fires_once_then_every_25k(self):
        now = time.time()
        start = self.baseline(150_000, now=now)
        self.write([start, assistant(209_000, now)])
        self.assertIsNone(self.run_hook())
        self.write([start, assistant(214_000, now)])
        msg = self.run_hook()
        self.assertIn("SESSION BUDGET REACHED", msg)
        self.assertIn("context +64k / +60k since the first PLAN write", msg)
        self.assertIn("§9.5 step 3a", msg)
        self.write([start, assistant(230_000, now)])
        self.assertIsNone(self.run_hook())
        self.write([start, assistant(240_000, now)])
        self.assertIn("context +90k", self.run_hook())

    def test_baseline_is_the_first_plan_write_only(self):
        now = time.time()
        start = self.baseline(150_000, now=now)
        self.write([start, assistant(200_000, now)])
        self.assertIsNone(self.run_hook(tool=PLAN_WRITE))  # a later tick
        self.write([start, assistant(211_000, now)])
        self.assertIn("context +61k", self.run_hook())

    def test_failed_plan_write_sets_no_baseline(self):
        now = time.time()
        start = {"type": "user", "timestamp": iso(now - 60)}
        self.write([start, assistant(150_000, now)])
        payload = json.dumps(
            {
                "transcript_path": self.transcript,
                "session_id": "fail",
                "tool_name": PLAN_WRITE,
            }
        )
        r = subprocess.run(
            [sys.executable, "-I", HOOK, "PostToolUseFailure"],
            input=payload,
            capture_output=True,
            text=True,
            env=self.env,
            timeout=30,
            check=False,
        )
        self.assertEqual(r.stdout, "")
        self.write([start, assistant(260_000, now)])
        self.assertIsNone(self.run_hook(session="fail"))

    def test_over_time_fires_then_every_10_min_even_without_usage(self):
        now = time.time()
        self.write(
            [
                {"type": "user", "timestamp": iso(now - 31 * 60)},
                {"type": "assistant", "timestamp": iso(now)},
            ]
        )
        self.assertIn("31 min / 30 min", self.run_hook())
        self.assertIsNone(self.run_hook())
        self.write(
            [
                {"type": "user", "timestamp": iso(now - 41 * 60)},
                {"type": "assistant", "timestamp": iso(now)},
            ]
        )
        self.assertIn("41 min / 30 min", self.run_hook())

    def test_parallel_hooks_fire_once(self):
        now = time.time()
        start = self.baseline(100_000, session="p", now=now)
        self.write([start, assistant(164_000, now)])
        payload = json.dumps(
            {"transcript_path": self.transcript, "session_id": "p", "tool_name": "Bash"}
        )
        procs = [
            subprocess.Popen(
                [sys.executable, "-I", HOOK],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=self.env,
            )
            for _ in range(8)
        ]
        results = [(p.communicate(payload, timeout=30), p.returncode) for p in procs]
        for (_, err), code in results:
            self.assertEqual(code, 0, err)
        self.assertEqual(sum(1 for (out, _), _ in results if out), 1)

    def test_env_budget_override(self):
        now = time.time()
        start = self.baseline(100_000, now=now)
        self.write([start, assistant(130_000, now)])
        env = dict(self.env, SDLC_CONTEXT_GROWTH_K="25")
        self.assertIn("context +30k / +25k", self.run_hook(env=env))

    def test_interactive_session_silent(self):
        now = time.time()
        self.write(
            [{"type": "user", "timestamp": iso(now - 3600)}, assistant(300_000, now)]
        )
        env = dict(self.env)
        env.pop("WORKSPACE_SLUG")
        self.assertIsNone(self.run_hook(env=env))

    def test_failure_event_named_in_output(self):
        now = time.time()
        self.write([{"type": "user", "timestamp": iso(now - 31 * 60)}])
        payload = json.dumps({"transcript_path": self.transcript, "session_id": "f"})
        r = subprocess.run(
            [sys.executable, "-I", HOOK, "PostToolUseFailure"],
            input=payload,
            capture_output=True,
            text=True,
            env=self.env,
            timeout=30,
            check=False,
        )
        out = json.loads(r.stdout)["hookSpecificOutput"]
        self.assertEqual(out["hookEventName"], "PostToolUseFailure")
        self.assertIn("SESSION BUDGET REACHED", out["additionalContext"])

    def test_subagent_call_silent(self):
        now = time.time()
        self.write(
            [{"type": "user", "timestamp": iso(now - 60)}, assistant(150_000, now)]
        )
        payload = json.dumps(
            {"transcript_path": self.transcript, "session_id": "sub", "agent_id": "a1"}
        )
        self.assertIsNone(self.run_hook(stdin=payload))

    def test_only_coder_roles(self):
        now = time.time()
        entries = [
            {"type": "user", "timestamp": iso(now - 60)},
            assistant(150_000, now),
        ]
        late = [{"type": "user", "timestamp": iso(now - 31 * 60)}, entries[1]]
        self.write(late, agent="sdlc-agents:system-analyst")
        self.assertIsNone(self.run_hook(session="sa"))
        self.write(late, agent=None)
        self.assertIsNone(self.run_hook(session="none"))
        self.write(late, agent="sdlc-agents:devops-engineer")
        self.assertIsNotNone(self.run_hook(session="devops"))

    def test_bad_input_fails_open(self):
        self.assertIsNone(self.run_hook(stdin="not json"))
        self.assertIsNone(
            self.run_hook(stdin=json.dumps({"transcript_path": "/nonexistent"}))
        )
        self.write(["{broken", '{"type": "assistant", "message": {"usage": "x"}}'])
        self.assertIsNone(self.run_hook())

    def test_usage_found_behind_a_large_tool_result(self):
        now = time.time()
        big = {
            "type": "user",
            "timestamp": iso(now),
            "message": {"content": "x" * (600 * 1024)},
        }
        start = self.baseline(40_000, now=now)
        self.write([start, assistant(110_000, now), big])
        self.assertIn("context +70k", self.run_hook())

    def test_large_transcript_is_fast(self):
        now = time.time()
        filler = [
            {"type": "user", "timestamp": iso(now), "message": {"content": "y" * 5000}}
            for _ in range(1000)
        ]
        start = self.baseline(40_000, now=now)
        self.write([start] + filler + [assistant(105_000, now)])
        started = time.monotonic()
        self.assertIn("context +65k", self.run_hook())
        self.assertLess(time.monotonic() - started, 2.0)

    def test_sessions_do_not_share_state(self):
        now = time.time()
        start = self.baseline(100_000, session="a", now=now)
        self.write([start, assistant(170_000, now)])
        self.assertIsNotNone(self.run_hook(session="a"))
        self.assertIsNone(self.run_hook(session="b"))  # b has no baseline of its own


if __name__ == "__main__":
    unittest.main()
