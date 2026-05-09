#!/usr/bin/env python3
"""Regenerate `tools:` frontmatter across all agent prompts for a given set of
Plane workspace slugs.

Claude Code does not support wildcards in agent `tools:` allowlists for MCP
tool names (see anthropics/claude-code#13077, #2928). When a new workspace is
added, every agent's frontmatter must be updated to include the per-workspace
`mcp__plane-<slug>__*` tool names. This script automates that update.

Usage
-----

    # Read workspaces from /etc/plane-conductor/conductor.d/*.yaml
    python tools/regenerate_tools.py

    # Or pass slugs explicitly
    python tools/regenerate_tools.py --workspaces qsale coinex acme

The set of MCP operations each agent needs is derived from its current
frontmatter (we strip the workspace prefix and re-emit per workspace), so
adding a new workspace is a pure expansion. To add or remove an op for an
agent, edit the agent's frontmatter directly and re-run this script.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = REPO_ROOT / "agents"
DEFAULT_CONDUCTOR_DIR = Path("/etc/plane-conductor/conductor.d")

PLANE_PREFIX_RE = re.compile(r"^mcp__plane-([a-z0-9][a-z0-9-]*)__([a-z0-9_]+)$")
FRONTMATTER_TOOLS_RE = re.compile(r"^tools:\s*(.+?)$", re.MULTILINE)


def read_slugs_from_conductor(conductor_dir: Path) -> list[str]:
    """Extract workspace_slug from each /etc/plane-conductor/conductor.d/*.yaml.

    We don't import pyyaml — just match the simple `workspace_slug: …` line.
    """
    if not conductor_dir.exists():
        return []
    slugs: set[str] = set()
    for yaml_path in sorted(conductor_dir.glob("*.yaml")):
        try:
            text = yaml_path.read_text()
        except OSError:
            continue
        m = re.search(r"^workspace_slug:\s*([a-z0-9][a-z0-9-]*)\s*$", text, re.MULTILINE)
        if m:
            slugs.add(m.group(1))
    return sorted(slugs)


def parse_tools(tools_line: str) -> tuple[list[str], list[str]]:
    """Split a tools line into (non_plane_tools, plane_op_names_unique).

    `plane_op_names_unique` is the set of distinct MCP operation names
    (`retrieve_work_item`, `list_labels`, ...) extracted from any
    `mcp__plane-<slug>__<op>` entry, regardless of the slug it was scoped to.
    """
    raw = [t.strip() for t in tools_line.split(",") if t.strip()]
    non_plane: list[str] = []
    plane_ops: set[str] = set()
    for tool in raw:
        m = PLANE_PREFIX_RE.match(tool)
        if m:
            plane_ops.add(m.group(2))
        else:
            non_plane.append(tool)
    return non_plane, sorted(plane_ops)


def render_tools(non_plane: list[str], plane_ops: list[str], workspaces: list[str]) -> str:
    parts = list(non_plane)
    for op in plane_ops:
        for slug in workspaces:
            parts.append(f"mcp__plane-{slug}__{op}")
    return ", ".join(parts)


def regenerate_agent(path: Path, workspaces: list[str]) -> bool:
    """Rewrite the `tools:` line of one agent prompt. Returns True if changed."""
    text = path.read_text()
    m = FRONTMATTER_TOOLS_RE.search(text)
    if not m:
        print(f"  {path.name}: no `tools:` line, skipping", file=sys.stderr)
        return False
    non_plane, plane_ops = parse_tools(m.group(1))
    if not plane_ops:
        return False
    new_line = "tools: " + render_tools(non_plane, plane_ops, workspaces)
    new_text = text[: m.start()] + new_line + text[m.end():]
    if new_text == text:
        return False
    path.write_text(new_text)
    return True


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--workspaces",
        nargs="+",
        help="Workspace slugs (e.g. qsale coinex). If omitted, read from "
        f"{DEFAULT_CONDUCTOR_DIR}.",
    )
    p.add_argument(
        "--conductor-dir",
        default=str(DEFAULT_CONDUCTOR_DIR),
        type=Path,
        help="Path to plane-conductor's conductor.d directory.",
    )
    p.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if any agent would be modified (CI guard).",
    )
    args = p.parse_args()

    workspaces = args.workspaces or read_slugs_from_conductor(args.conductor_dir)
    if not workspaces:
        print(
            "no workspaces given (and none found in conductor.d). pass --workspaces.",
            file=sys.stderr,
        )
        return 2

    workspaces = sorted(set(workspaces))
    print(f"regenerating agent tools for workspaces: {workspaces}")

    changed = 0
    for agent_path in sorted(AGENTS_DIR.glob("*.md")):
        if regenerate_agent(agent_path, workspaces):
            print(f"  updated {agent_path.name}")
            changed += 1
    print(f"{changed} file(s) modified")

    if args.check and changed:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
