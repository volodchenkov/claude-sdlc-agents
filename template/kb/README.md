# `kb/` — detailed project knowledge

This directory holds project-specific knowledge that the generic agent
prompts in `claude-sdlc-agents/prompts/` need to do their job in your
codebase.

Entry point is [`../AGENTS.md`](../AGENTS.md) — it lives at the repo root by
convention. Agents read AGENTS.md first; AGENTS.md links here.

## How to use this template

1. Copy the parent `template/` (both `AGENTS.md` and `kb/`) into
   your project repo. Conventional location: repo root.
2. Fill in each file. Each file's `# Fill in:` section tells you what to
   write.
3. Configure Plane Conductor: `KB_DIR=<your-repo-root>`. Falls back to
   `<cwd>` if not set.
4. Commit with your code. The KB versions alongside the codebase — when
   the stack changes, both update in the same PR.

## Contents

| File | Purpose | If not applicable |
|---|---|---|
| `stack.md` | Backend / frontend stacks, versions, notable libs | required |
| `conventions.md` | Lint, format, type annotation policy, naming | required |
| `verify.md` | Slash-commands / make / npm scripts to run lint / tests / build / migration checks | required |
| `architecture.md` | Services, modules, bounded contexts, import contracts | write `"N/A — monolithic single-app"` if trivial |
| `multitenancy.md` | Tenant isolation rules | write `"N/A — single-tenant"` if not applicable |
| `migrate.md` | DB migration discipline (settings module, large-table policy, multi-step plan) | required for backend |
| `frontends.md` | Per-frontend stacks, build commands | required if any frontend |
| `document.md` | Docstring style, doc-generation tool | required |
| `domain/` | Drop ad-hoc domain knowledge files here | optional |

## Don't

- Don't store secrets here. Secrets go in `.env` / your secret manager.
- Don't restate the agent prompts. Prompts encode methodology;
  the KB tells them about *your* codebase.
- Don't put `"N/A"` everywhere to avoid filling them out — agents need
  to be able to trust either a real rule or an explicit non-rule.
