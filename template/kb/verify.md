# Verification commands

> Fill in: the commands agents run to verify their work — lint, tests,
> build, migration checks, type checks. These are the source of truth
> for `Definition of Done` in every coder agent.
>
> Define them as **slash-commands** in `<your-repo>/.claude/commands/`
> for stable invocation across sessions. Document them here.

## Slash-commands

List every project-specific slash-command and what it does. Each
docstring should reference how the command is implemented (which `make`
target, npm script, or shell snippet it wraps).

| Command | Purpose | Wraps |
|---|---|---|
| `/check-style` | Full lint (formatter + linter + framework checks) | `make.sh lint` |
| `/check-importlinter` | Import contracts only (faster) | `pre-commit run import-linter --all-files` |
| `/run-tests <service>` | Pytest for one service | `make.sh test-<service>` |
| `/run-tests-all` | Full parallel matrix (mirrors pre-commit) | `make.sh test-parallel` |
| `/check-migrations` | Pending-migrations across all apps | `manage.py makemigrations --check --dry-run --settings <canonical>` |
| `/run-django-check` | Quick Django sanity | `manage.py check --fail-level WARNING` |
| `/run-build-<frontend>` | Frontend typecheck + build | `<project>/yarn build` or `nuxi typecheck && nuxi build` |

(Adjust to your project's actual commands.)

## Definition-of-Done command sequence

After all PLAN steps complete, agents run these in order:

1. `/check-style` — must exit 0
2. `/check-migrations` — must exit 0 (any pending in any app blocks deploy)
3. `/run-tests-all` — must pass (= what `git commit` runs in pre-commit)
4. (frontend) `/run-build-<frontend>` — must succeed

Report actual command output in CHANGES "Verification" section. Don't claim "passed" without seeing it.

## Activation prerequisites

Most commands need a virtualenv / nvm / poetry shell active. Document:

- venv path: `<your venv path>` (or `pdm shell` / `poetry shell` / etc.)
- Frontend: `corepack enable` / `nvm use` / etc.
- Slash-commands handle activation automatically (each prepends `. <venv>/bin/activate`).

## Anti-patterns

- Filtered test runs (`pytest -k <name>`) for final verification — hides regressions in unrelated tests
- Lint-only verification — misses build / type / template errors
- Skipping `/check-migrations` because "my task didn't add a migration" — pending migrations from any app block deploy
