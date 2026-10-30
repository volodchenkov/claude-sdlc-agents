#!/usr/bin/env bash
# pre-push hook: a branch that changes agents/, skills/, template/ or tools/
# must carry a plugin version different from origin/master (CLAUDE.md
# «Release / version bump»). Without it the marketplace refuses to update.
#
# Checks the ref being pushed (pre-commit sets PRE_COMMIT_TO_REF), HEAD when
# run by hand.
set -euo pipefail

base=origin/master
ref=${PRE_COMMIT_TO_REF:-HEAD}

if ! git fetch -q origin master 2>/dev/null; then
  if ! git rev-parse -q --verify "$base" >/dev/null; then
    echo "version-bump: no $base and cannot fetch it — check skipped" >&2
    exit 0
  fi
  echo "version-bump: fetch failed — comparing with the local $base" >&2
fi

changed=$(git diff --name-only "$base"..."$ref" -- agents skills template tools)
[ -z "$changed" ] && exit 0

version() {
  git show "$1:.claude-plugin/plugin.json" |
    python3 -c 'import json, sys; print(json.load(sys.stdin)["version"])'
}

if [ "$(version "$base")" = "$(version "$ref")" ]; then
  echo "version-bump: $ref changes agents/skills/template/tools but" >&2
  echo "  .claude-plugin/plugin.json still has $(version "$ref"), same as $base." >&2
  echo "  Bump the patch version in the same commit (CLAUDE.md «Release / version bump»)." >&2
  exit 1
fi
