#!/usr/bin/env python3
"""pre-commit hook: every agent prompt and SKILL.md starts with YAML
frontmatter carrying non-empty `name` and `description`.

Usage: check_frontmatter.py FILE...
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

REQUIRED = ("name", "description")


def check(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return [f"{path}: no frontmatter (file must start with '---')"]
    end = text.find("\n---\n", 4)
    if end == -1:
        return [f"{path}: frontmatter is not closed with '---'"]
    try:
        meta = yaml.safe_load(text[4:end])
    except yaml.YAMLError as exc:
        return [f"{path}: frontmatter is not valid YAML: {exc}"]
    if not isinstance(meta, dict):
        return [f"{path}: frontmatter is not a mapping"]
    return [
        f"{path}: missing or empty `{key}`" for key in REQUIRED if not meta.get(key)
    ]


def main(argv: list[str]) -> int:
    errors = [err for name in argv for err in check(Path(name))]
    for err in errors:
        print(err, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
