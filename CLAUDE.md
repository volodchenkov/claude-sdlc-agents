# Claude Code rules for this repo

## Release / version bump

`.claude-plugin/plugin.json` carries the published plugin version. **Every PR that touches `agents/`, `skills/`, `template/`, or `tools/` MUST bump it.** A PR that ships the same version as `main` is broken — the marketplace will refuse to update for users.

- Default to **patch** bumps (`0.5.6 → 0.5.7`). Prompt rewording, bug fixes, contradiction cleanup — all patch, even if commits are labelled `feat:`.
- **Minor** bumps only when the surface grows: a new agent file, a new skill directory, a new MCP integration, a new top-level capability. If unsure between patch and minor, ask — don't guess up.
- Major (`1.x.0`) — never without explicit user instruction.
- Bump goes in the same commit as the content change. One PR = one commit (unless explicitly split).

## PR workflow

- All changes go through a PR. **Never push to `main` directly**, never force-push to `main`.
- One PR can carry multiple themes if they're discovered in the same pass — use one commit per theme for a readable history, but ship one PR.
- Branch naming: `feat/<topic>`, `fix/<topic>`, `chore/<topic>`. Rename the branch if the scope drifts before opening the PR.
- Don't open a PR with the wrong version still in `plugin.json`. Check the diff before pushing.

## Git safety

- Never `git push --force` to `main`, never `git reset --hard` on a shared branch.
- Never `--no-verify` / `--no-gpg-sign` unless the user explicitly asked.
- `git commit` / `git push` require explicit user OK before each batch — don't chain pushes from one "yes".
- If a hook fails, fix the underlying issue and create a NEW commit. Don't `--amend` past hook failures.

## Memory hygiene

Project rules live here (in this file). Personal preferences / tone live under `~/.claude/projects/<this>/memory/`. If a rule is universal to anyone working on this repo, it belongs in this file, not in private memory.
