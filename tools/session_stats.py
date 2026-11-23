#!/usr/bin/env python3
"""Context size of pipeline runs, from Claude Code transcripts (read-only).

Re-checks the budget of hooks/session_budget.py. Run on the pipeline host:

    python3 -I tools/session_stats.py [--days 30] [--root ~/.claude/projects]

A pipeline run is a transcript whose first user message starts with
«Triggered as @<nick>» (plane-conductor's spawn prompt). Prints the runs per
role, the peak context per run (p25 / p50 / p75 / p90 / max) and, per context
bin, tool calls and the share that returned an error. Pair it with the
review verdicts in Plane to judge quality; this script only reads transcripts.
"""

import argparse
import collections
import glob
import json
import os
import re
import time

BINS = [0, 25, 50, 75, 100, 125, 150, 200, 300, 10**9]


def context(usage):
    return (
        usage.get("input_tokens", 0)
        + usage.get("cache_read_input_tokens", 0)
        + usage.get("cache_creation_input_tokens", 0)
    )


def bin_of(k):
    return next(i for i in range(len(BINS) - 1) if BINS[i] <= k < BINS[i + 1])


def runs(root, days):
    cut = time.time() - days * 86400
    for path in glob.glob(os.path.join(os.path.expanduser(root), "*", "*.jsonl")):
        if os.path.getmtime(path) < cut:
            continue
        try:
            with open(path) as f:
                entries = [json.loads(line) for line in f if line.strip()]
        except (OSError, ValueError):
            continue
        first = next((e for e in entries if e.get("type") == "user"), None)
        if not first:
            continue
        content = (first.get("message") or {}).get("content")
        if isinstance(content, list):
            content = "".join(
                b.get("text", "")
                for b in content
                if isinstance(b, dict) and b.get("type") == "text"
            )
        text = content if isinstance(content, str) else ""
        m = re.match(r"Triggered as @(\w+)", text or "")
        if m:
            role = next(
                (
                    e.get("agentSetting")
                    for e in entries
                    if e.get("type") == "agent-setting"
                ),
                None,
            )
            yield role or m.group(1), entries


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--root", default="~/.claude/projects")
    args = ap.parse_args()

    roles = collections.Counter()
    peaks = []
    calls = collections.Counter()
    errors = collections.Counter()
    for role, entries in runs(args.root, args.days):
        roles[role] += 1
        ctx = peak = 0
        pending = {}
        for e in entries:
            msg = e.get("message") or {}
            if e.get("type") == "assistant":
                ctx = context(msg.get("usage") or {}) or ctx
                peak = max(peak, ctx)
                for part in msg.get("content") or []:
                    if isinstance(part, dict) and part.get("type") == "tool_use":
                        pending[part["id"]] = ctx
            elif e.get("type") == "user" and isinstance(msg.get("content"), list):
                for part in msg["content"]:
                    if (
                        isinstance(part, dict)
                        and part.get("type") == "tool_result"
                        and part.get("tool_use_id") in pending
                    ):
                        b = bin_of(pending.pop(part["tool_use_id"]) // 1000)
                        calls[b] += 1
                        errors[b] += bool(part.get("is_error"))
        peaks.append(peak)

    print(f"pipeline runs: {sum(roles.values())} (last {args.days} days)")
    for role, n in roles.most_common():
        print(f"  {role}: {n}")
    if peaks:
        peaks.sort()

        def q(p):
            return peaks[int(p * (len(peaks) - 1))] // 1000

        print(
            f"peak context per run, k: p25 {q(0.25)}  p50 {q(0.5)}  p75 {q(0.75)}  p90 {q(0.9)}  max {q(1)}"
        )
    print(f"{'context k':<10} {'calls':>7} {'errors':>7} {'runs >=':>8}")
    for i in range(len(BINS) - 1):
        hi = BINS[i + 1] if BINS[i + 1] < 10**9 else "+"
        n = calls[i]
        reach = sum(1 for p in peaks if p >= BINS[i] * 1000)
        print(
            f"{f'{BINS[i]}-{hi}':<10} {n:>7} {100 * errors[i] / (n or 1):>6.1f}% {reach:>8}"
        )


if __name__ == "__main__":
    main()
