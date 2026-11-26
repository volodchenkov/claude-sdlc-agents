"""Tests for tools/pipeline_cost.py (token cost of pipeline runs).

Run: python3 -I -m unittest discover -s tools -p 'test_*.py'
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

TOOL = os.path.join(os.path.dirname(__file__), "pipeline_cost.py")
ISSUE = "cfd10a49-9153-4b8d-89e6-1d731f0c153a"


def assistant(mid, ts, cw=0, cr=0, out=0, tools=()):
    return {
        "type": "assistant",
        "timestamp": ts,
        "requestId": "r-" + mid,
        "message": {
            "id": mid,
            "usage": {
                "input_tokens": 1,
                "cache_creation_input_tokens": cw,
                "cache_read_input_tokens": cr,
                "output_tokens": out,
            },
            "content": [
                {"type": "tool_use", "id": f"t-{mid}-{k}", "name": n, "input": i}
                for k, (n, i) in enumerate(tools)
            ],
        },
    }


def spawn(nick="beck", role="sdlc-agents:react-developer", ts="2026-11-25T10:00:00Z"):
    return [
        {"type": "agent-setting", "agentSetting": role},
        {
            "type": "user",
            "timestamp": ts,
            "message": {"content": f"Triggered as @{nick}.\nIssue UUID: {ISSUE}\n"},
        },
    ]


class Cost(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.mkdir(os.path.join(self.root, "proj"))

    def write(self, name, records, tail=b""):
        path = os.path.join(self.root, "proj", name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.writelines(json.dumps(r).encode() + b"\n" for r in records)
            f.write(tail)
        return path

    def run_tool(self, *extra):
        r = subprocess.run(
            [
                sys.executable,
                "-I",
                TOOL,
                "--root",
                self.root,
                "--since",
                "2026-11-25T00:00",
                *extra,
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def rows(self):
        return [json.loads(line) for line in self.run_tool("--json").splitlines()]

    def test_streamed_message_counted_once(self):
        msg = assistant("m1", "2026-11-25T10:01:00Z", cw=100_000, cr=5, out=7)
        self.write("a.jsonl", spawn() + [msg, msg, msg])
        (row,) = self.rows()
        self.assertEqual(row["bill"]["cache_write"], 100_000)
        self.assertEqual(row["bill"]["output"], 7)
        self.assertEqual(
            (row["role"], row["issue"], row["pipeline"]),
            ("react-developer", ISSUE, True),
        )

    def test_blocks_of_one_message_split_over_entries(self):
        # Claude Code writes each content block as its own entry, same id and usage.
        a = assistant(
            "m1",
            "2026-11-25T10:01:00Z",
            cw=100,
            tools=[("Bash", {"command": "codex-review --plan a.md"})],
        )
        b = assistant(
            "m1",
            "2026-11-25T10:01:00Z",
            cw=100,
            tools=[("Bash", {"command": "codex-review --plan b.md"})],
        )
        a["message"]["content"][0]["id"] = "t1"
        b["message"]["content"][0]["id"] = "t2"
        self.write("a.jsonl", spawn() + [a, b, b])
        bill = self.rows()[0]["bill"]
        self.assertEqual((bill["cache_write"], bill["codex_plan"]), (100, 2))

    def test_before_since_not_counted(self):
        self.write(
            "a.jsonl",
            spawn()
            + [
                assistant("old", "2026-11-24T23:59:00Z", cw=999),
                assistant("new", "2026-11-25T00:01:00Z", cw=10),
            ],
        )
        (row,) = self.rows()
        self.assertEqual(row["bill"]["cache_write"], 10)

    def test_self_handoff_and_codex_runs(self):
        self.write(
            "a.jsonl",
            spawn()
            + [
                assistant(
                    "m",
                    "2026-11-25T10:01:00Z",
                    cw=1,
                    tools=[
                        (
                            "mcp__plane-tower__request_handoff",
                            {"target_role": "react-developer"},
                        ),
                        (
                            "mcp__plane-tower__request_handoff",
                            {"target_role": "ui-tester"},
                        ),
                        (
                            "Bash",
                            {
                                "command": "~/.claude/bin/codex-review --conventions --base origin/master"
                            },
                        ),
                        (
                            "Bash",
                            {
                                "command": "~/.claude/bin/codex-review --plan /tmp/spec.md"
                            },
                        ),
                    ],
                )
            ],
        )
        b = self.rows()[0]["bill"]
        self.assertEqual(
            (b["self_handoffs"], b["codex_diff"], b["codex_plan"]), (1, 1, 1)
        )

    def test_subagent_billed_to_parent_role(self):
        self.write(
            "run.jsonl", spawn() + [assistant("m", "2026-11-25T10:01:00Z", cw=5)]
        )
        self.write(
            "run/subagents/agent-x.jsonl",
            [assistant("s", "2026-11-25T10:02:00Z", cw=50)],
        )
        rows = {r["role"]: r for r in self.rows()}
        self.assertEqual(rows["react-developer [sub]"]["bill"]["cache_write"], 50)
        self.assertTrue(rows["react-developer [sub]"]["sub"])
        out = self.run_tool()
        self.assertIn("total: 1 sessions, 1 subagents", out)

    def test_interactive_and_broken_lines(self):
        self.write(
            "i.jsonl",
            [
                {
                    "type": "user",
                    "timestamp": "2026-11-25T10:00:00Z",
                    "message": {"content": "hi"},
                },
                assistant("m", "2026-11-25T10:01:00Z", cw=3),
            ],
            tail=b'{"type": "assistant", "trunc',
        )
        (row,) = self.rows()
        self.assertEqual(
            (row["role"], row["pipeline"], row["issue"]), ("plain", False, None)
        )

    def test_report_groups(self):
        self.write(
            "a.jsonl", spawn() + [assistant("a", "2026-11-25T10:01:00Z", cw=131_000)]
        )
        self.write(
            "b.jsonl", spawn() + [assistant("b", "2026-11-25T11:01:00Z", cw=131_000)]
        )
        out = self.run_tool()
        self.assertIn("total: 2 sessions", out)
        line = next(
            x for x in out.splitlines() if x.strip().startswith("react-developer")
        )
        self.assertIn("131k", line)  # cache write per session
        self.assertIn("cfd10a49 (proj)", out)

    def test_fresh_subagent_of_idle_parent_counts(self):
        parent = self.write(
            "run.jsonl", spawn() + [assistant("m", "2026-11-24T10:01:00Z", cw=5)]
        )
        os.utime(parent, (1, 1))  # parent idle long before --since
        self.write(
            "run/subagents/agent-x.jsonl",
            [assistant("s", "2026-11-25T10:02:00Z", cw=50)],
        )
        (row,) = self.rows()
        self.assertEqual(
            (row["role"], row["bill"]["cache_write"]), ("react-developer [sub]", 50)
        )

    def test_output_of_a_message_is_its_largest_count(self):
        # a first entry may carry a partial output count, a later one the final
        a = assistant("m1", "2026-11-25T10:01:00Z", cw=70, out=3)
        b = assistant("m1", "2026-11-25T10:01:00Z", cw=70, out=40)
        self.write("a.jsonl", spawn() + [a, b, a])
        bill = self.rows()[0]["bill"]
        self.assertEqual((bill["cache_write"], bill["output"]), (70, 40))

    def test_output_largest_across_transcripts(self):
        # a resumed session repeats a message of its parent transcript
        a = assistant("m1", "2026-11-25T10:01:00Z", cw=70, out=3)
        b = assistant("m1", "2026-11-25T10:01:00Z", cw=70, out=40)
        self.write("a.jsonl", spawn() + [a])
        self.write("b.jsonl", spawn() + [b])
        rows = self.rows()
        self.assertEqual(sum(r["bill"].get("output", 0) for r in rows), 40)
        self.assertEqual(sum(r["bill"].get("cache_write", 0) for r in rows), 70)

    def test_output_raised_on_a_row_that_started_empty(self):
        first = assistant("m1", "2026-11-25T10:01:00Z")
        first["message"]["usage"]["input_tokens"] = 0  # a record with no tokens
        self.write("a.jsonl", spawn() + [first])
        self.write(
            "b.jsonl", spawn() + [assistant("m1", "2026-11-25T10:01:00Z", out=9)]
        )
        rows = self.rows()
        self.assertEqual(sum(r["bill"].get("output", 0) for r in rows), 9)

    def test_nested_workflow_subagent_counts(self):
        parent = self.write(
            "run.jsonl", spawn() + [assistant("m", "2026-11-24T10:01:00Z", cw=5)]
        )
        os.utime(parent, (1, 1))
        self.write(
            "run/subagents/workflows/w1/agent-a.jsonl",
            [assistant("s", "2026-11-25T10:02:00Z", cw=60)],
        )
        (row,) = self.rows()
        self.assertEqual(
            (row["role"], row["bill"]["cache_write"]), ("react-developer [sub]", 60)
        )

    def test_usage_on_a_later_entry_of_the_message_counts(self):
        a = assistant("m1", "2026-11-25T10:01:00Z")
        del a["message"]["usage"]
        b = assistant("m1", "2026-11-25T10:01:00Z", cw=70)
        self.write("a.jsonl", spawn() + [a, b])
        self.assertEqual(self.rows()[0]["bill"]["cache_write"], 70)

    def test_codex_counted_only_as_a_command(self):
        cmds = [
            "~/.claude/bin/codex-review --plan /tmp/s.md > /tmp/o.txt 2>&1",
            "cd /w && timeout 600 ~/.claude/bin/codex-review --conventions --base origin/master",
            "echo 'codex-review --plan spec.md'",
            "grep -n codex-review agents/*.md",
        ]
        tools = [("Bash", {"command": c}) for c in cmds]
        self.write(
            "a.jsonl",
            spawn() + [assistant("m", "2026-11-25T10:01:00Z", cw=1, tools=tools)],
        )
        b = self.rows()[0]["bill"]
        self.assertEqual((b.get("codex_plan", 0), b.get("codex_diff", 0)), (1, 1))

    def test_codex_counted_as_bash_runs_it(self):
        # one project per command: a false hit cannot cancel a miss
        cases = {
            "echo 'before; codex-review --plan s.md; after'": None,
            'echo "a && codex-review x"': None,
            'echo ";" codex-review --plan p': None,
            "echo hi > codex-review": None,
            "cat <<EOF > n.md\ncodex-review --plan p\nEOF\ntrue": None,
            "# codex-review --plan p": None,
            "# note\n\ncodex-review --plan p": "plan",
            'env X="a b" codex-review --plan p': "plan",
            "codex-review \\\n  --plan p": "plan",
            "cat <<-'E' >x\n\tcodex-review\n\tE\nls": None,
            "git commit -m \"$(cat <<'EOF'\ncodex-review --plan p\nEOF\n)\"": None,
            "echo hello#world; codex-review --plan p": "plan",
            "timeout 10m codex-review --plan s.md": "plan",
            "timeout -k 5s 1.5h codex-review": "diff",
            "codex-review --plan p > o.txt 2>&1": "plan",
            "2>/dev/null codex-review --plan p": "plan",
            "sleep 2 >x; 3<in codex-review": "diff",
            "true\ncodex-review --plan p.md": "plan",
            "(cd /w; codex-review --plan p)": "plan",
            "cat <<'X'\nhi\nX\ncodex-review --base m": "diff",
            "cat <<EOF; codex-review --plan p\nbody\nEOF": "plan",
            "cat <<'EOF'\n EOF\ncodex-review --plan p\nEOF\n": None,
            "timeout --signal TERM 600 codex-review --plan p.md": "plan",
            "nice -n 10 codex-review": "diff",
            "codex-review --base master; codex-review --plan p.md": "both",
            "args=(codex-review --plan spec.md)": None,
            'args=(")" codex-review --plan p)': None,
            'opts=(-o "r=$(<f)"); codex-review --plan p': "plan",
            "git commit -m \"$(echo a | sed 's/x/don'\"'\"'t/')\"; codex-review --plan p": "plan",
            'echo "$(codex-review --plan p)"': "plan",
            'echo "$((codex-review))"': None,
            'echo "$(( $(codex-review --plan p) + 1 ))"': "plan",
            "echo \"$(( $(echo '$(codex-review)') + (1) ))\"": None,
            'echo "$(cat <<\'EOF\'\nit\'s "codex-review"\nEOF\n)"; codex-review': "diff",
            "(codex-review --plan spec.md)": "plan",
            "if true; then codex-review --plan spec.md; fi": "plan",
            "while ! codex-review; do sleep 5; done": "diff",
            "{ codex-review --plan p; } 2>&1": "plan",
        }
        for k, cmd in enumerate(cases):
            d = os.path.join(self.root, f"p{k}")
            os.mkdir(d)
            with open(os.path.join(d, "a.jsonl"), "w") as f:
                f.writelines(
                    json.dumps(r) + "\n"
                    for r in spawn()
                    + [
                        assistant(
                            f"m{k}",
                            "2026-11-25T10:01:00Z",
                            cw=1,
                            tools=[("Bash", {"command": cmd})],
                        )
                    ]
                )
        got = {}
        for row in self.rows():
            b = row["bill"]
            got[row["project"]] = {
                (1, 0): "plan",
                (0, 1): "diff",
                (1, 1): "both",
                (0, 0): None,
            }.get((b.get("codex_plan", 0), b.get("codex_diff", 0)), "many")
        self.assertEqual(set(got), {f"p{k}" for k in range(len(cases))})
        for k, (cmd, want) in enumerate(cases.items()):
            self.assertEqual(got[f"p{k}"], want, cmd)

    def test_unreadable_transcript_warned_on_stderr(self):
        path = self.write(
            "a.jsonl", spawn() + [assistant("m", "2026-11-25T10:01:00Z", cw=1)]
        )
        os.chmod(path, 0)
        if os.access(path, os.R_OK):
            self.skipTest("running as root")
        r = subprocess.run(
            [
                sys.executable,
                "-I",
                TOOL,
                "--root",
                self.root,
                "--since",
                "2026-11-25T00:00",
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(r.stdout, "")
        self.assertIn("unreadable", r.stderr)

    def test_missing_root_is_an_error(self):
        r = subprocess.run(
            [sys.executable, "-I", TOOL, "--root", "/nonexistent-root"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(r.returncode, 2)
        self.assertIn("no such directory", r.stderr)

    def test_project_name_shortened(self):
        os.mkdir(os.path.join(self.root, "-home-u-Projects-coinex"))
        path = os.path.join(self.root, "-home-u-Projects-coinex", "a.jsonl")
        with open(path, "w") as f:
            f.write(json.dumps(assistant("m", "2026-11-25T10:01:00Z", cw=1)) + "\n")
        self.assertEqual(self.rows()[0]["project"], "coinex")


if __name__ == "__main__":
    unittest.main()
