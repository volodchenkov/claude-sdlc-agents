#!/usr/bin/env bash
# pre-push hook: a branch that changes agents/, skills/, template/ or tools/
# must carry a plugin version greater than origin/master (SemVer) (CLAUDE.md
# «Release / version bump»). Without it the marketplace refuses to update.
#
# Checks the ref being pushed (pre-commit sets PRE_COMMIT_TO_REF), HEAD when
# run by hand.
set -euo pipefail

base=origin/master
ref=${PRE_COMMIT_TO_REF:-HEAD}

# A stale local origin/master can miss a release made meanwhile — fail closed.
if ! git fetch -q origin master 2>/dev/null; then
  echo "version-bump: cannot fetch origin/master — cannot verify the plugin version." >&2
  echo "  Fix the connection, then push again." >&2
  exit 1
fi

version() {
  git show "$1:.claude-plugin/plugin.json" |
    python3 -c 'import json, sys; print(json.load(sys.stdin)["version"])'
}

# marketplace.json carries the same version; drift there went unnoticed
# from 0.6.18 to 0.6.22.
market_v=$(git show "$ref:.claude-plugin/marketplace.json" |
  python3 -c 'import json, sys; print(json.load(sys.stdin)["plugins"][0]["version"])')
if [ "$market_v" != "$(version "$ref")" ]; then
  echo "version-bump: marketplace.json has $market_v, plugin.json has $(version "$ref") — keep them equal." >&2
  exit 1
fi

# SemVer 2.0.0 — the official regex from semver.org.
if ! python3 - "$(version "$ref")" <<'PY'
import re, sys
N = r"(?:0|[1-9]\d*)"
ID = r"(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)"
SEMVER = rf"{N}\.{N}\.{N}(?:-{ID}(?:\.{ID})*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
sys.exit(0 if re.fullmatch(SEMVER, sys.argv[1], re.ASCII) else 1)
PY
then
  echo "version-bump: plugin.json version $(version "$ref") is not MAJOR.MINOR.PATCH." >&2
  exit 1
fi

changed=$(git diff --name-only "$base"..."$ref" -- agents skills template tools)
[ -z "$changed" ] && exit 0

base_v=$(version "$base")
ref_v=$(version "$ref")
# Greater, not just different: a branch cut at 0.6.22 must not pass once
# master has moved to 0.6.23 on its own.
if ! python3 - "$ref_v" "$base_v" <<'PY'
import sys
def key(v):
    core, _, pre = v.split("+")[0].partition("-")
    nums = tuple(int(p) for p in core.split("."))
    ids = tuple((0, int(i), "") if i.isdigit() else (1, 0, i) for i in pre.split(".")) if pre else ()
    return nums, not pre, ids  # a release outranks its prereleases
sys.exit(0 if key(sys.argv[1]) > key(sys.argv[2]) else 1)
PY
then
  echo "version-bump: $ref changes agents/skills/template/tools but" >&2
  echo "  .claude-plugin/plugin.json has $ref_v, not greater than $base_v on $base." >&2
  echo "  Bump the patch version in the same commit (CLAUDE.md «Release / version bump»)." >&2
  exit 1
fi
