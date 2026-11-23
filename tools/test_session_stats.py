"""Tests for tools/session_stats.py (transcript analysis for the session budget).

Run: python3 -I -m unittest discover -s tools -p 'test_*.py'
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

STATS = os.path.join(os.path.dirname(__file__), "session_stats.py")


def run_stats(root):
    r = subprocess.run(
        [sys.executable, "-I", STATS, "--root", root, "--days", "1"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    return r


class Stats(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.mkdir(os.path.join(self.root, "proj"))

    def transcript(self, name, records, tail=b""):
        path = os.path.join(self.root, "proj", name)
        with open(path, "wb") as f:
            f.writelines(json.dumps(rec).encode() + b"\n" for rec in records)
            f.write(tail)

    def run_records(self, ctx):
        return [
            {"type": "agent-setting", "agentSetting": "sdlc-agents:django-developer"},
            {
                "type": "user",
                "message": {"content": "Triggered as @rinzler.\nIssue UUID: x"},
            },
            {
                "type": "assistant",
                "message": {
                    "usage": {"input_tokens": ctx},
                    "content": [
                        {"type": "tool_use", "id": "t1"},
                        {"type": "tool_use", "id": "t2"},
                    ],
                },
            },
            {
                "type": "user",
                "message": {"content": [{"type": "tool_result", "tool_use_id": "t1"}]},
            },
        ]

    def test_cut_off_utf8_record_keeps_the_run(self):
        # A kill mid-write: the last record ends inside a two-byte UTF-8 character.
        self.transcript(
            "a.jsonl", self.run_records(60_000), tail='{"text": "ж'.encode()[:-1]
        )
        r = run_stats(self.root)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("pipeline runs: 1", r.stdout)
        # One call answered, one without a result, both in the 50-75k bin.
        row = next(line for line in r.stdout.splitlines() if line.startswith("50-75"))
        self.assertEqual(row.split()[1], "1")
        self.assertEqual(row.split()[3], "1")

    def test_content_blocks_prompt_counts(self):
        records = self.run_records(30_000)
        records[1] = {
            "type": "user",
            "message": {"content": [{"type": "text", "text": "Triggered as @beck."}]},
        }
        self.transcript("b.jsonl", records)
        self.assertIn("pipeline runs: 1", run_stats(self.root).stdout)

    def test_interactive_session_ignored(self):
        records = self.run_records(30_000)
        records[1] = {"type": "user", "message": {"content": "fix the bug"}}
        self.transcript("c.jsonl", records)
        self.assertIn("pipeline runs: 0", run_stats(self.root).stdout)


if __name__ == "__main__":
    unittest.main()
