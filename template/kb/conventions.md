# Code conventions

> Fill in: how code is formatted, linted, named in your project. Agents
> follow these instead of generic Python / TS defaults.

## Linting / formatting (Python)

- Tool: ruff / black + isort + flake8 / pylint + black / …
- Config location: `pyproject.toml` at repo root / `setup.cfg` / `.ruff.toml`
- Line length: 120 / 88 / 80
- Quote style: single / double
- Pre-commit hooks: yes / no — if yes, what they run

## Type annotations (Python)

- Policy: required / optional / not used
  - If "not used" — explain rationale (legacy codebase, ANN ignored, etc.). Agents skip type hints accordingly.
- Type checker: mypy strict / mypy lenient / pyright / none
- Plugins: mypy-django-plugin / pydantic-mypy / …

## Linting / formatting (JS / TS)

- Tool: eslint / prettier / both — config locations
- TypeScript: strict / loose / not used
- Quote style, indent, trailing commas — only the ones that diverge from linter defaults

## Naming conventions

- Python modules: `snake_case`
- Python models: `CamelCase`
- Python functions: `snake_case`
- Python constants: `UPPER_SNAKE`
- TS / JS modules: `kebab-case` filename / `camelCase` exports
- TS / JS components: `PascalCase` filenames matching default export
- Test files: `test_<feature>.py` (Python) / `<feature>.test.ts` (TS)
- Test functions: `test_<feature>_<behaviour>` — read like documentation

## Imports order

- Strategy: isort default / Black-compatible / custom
- Forbidden imports: list anything blanket-forbidden (e.g. `from foo import *`, deep imports of internal modules)

## Comments

- Inline: only when "why" isn't obvious from "what"
- TODO format: `# TODO(<owner>): <description> — <ticket>`
- FIXME / XXX policy: allowed in dev branches; main must be clean

## TDD policy

- Mandatory red-green-refactor: yes / no
- If no — what's the practical rule? (e.g. tests written alongside or shortly after; never merged without tests)

## Skill overrides

The `pytest-django-patterns` skill prescribes strict TDD by default. If
your TDD policy above differs, the project wins. Likewise for any
other skill that conflicts with these conventions.
