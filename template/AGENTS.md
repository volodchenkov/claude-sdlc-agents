# Project Agents Manual

> Entry point for AI agents working on this codebase. Read this first
> on every session. Then load specific `kb/<file>.md` based on your
> task — see the routing table below.

This file follows the [agents.md](https://agents.md/) convention
(adopted by Cursor / OpenAI Codex / Aider / Claude Code). Detailed
content lives in `kb/` to keep this file scannable.

---

## Quick orientation (fill in)

- **What this project is**: <one-paragraph elevator pitch>
- **Primary stack**: <e.g. "Django 4.2 + DRF backend; Vue 3 + Nuxt 3 storefront">
- **Initiator / point of contact**: <who decides scope, who triggers agents>

---

## Knowledge base index

| Topic | File | Read when... |
|---|---|---|
| Tech stack & versions | [`kb/stack.md`](kb/stack.md) | always (session start) |
| Code conventions (lint, types, naming) | [`kb/conventions.md`](kb/conventions.md) | always (session start) |
| Verification commands (lint, tests, build) | [`kb/verify.md`](kb/verify.md) | before claiming "done" / for slash-commands |
| Architecture (services, modules, import boundaries) | [`kb/architecture.md`](kb/architecture.md) | designing or refactoring features |
| Multi-tenancy rules | [`kb/multitenancy.md`](kb/multitenancy.md) | any backend code touching user data |
| Database migrations | [`kb/migrate.md`](kb/migrate.md) | when changing models / schemas |
| Frontend stacks per project | [`kb/frontends.md`](kb/frontends.md) | any frontend work |
| Documentation discipline | [`kb/document.md`](kb/document.md) | before posting CHANGES |
| Domain knowledge files | [`kb/domain/`](kb/domain/) | on-demand per task |

---

## Routing table (per role)

When agents launch, they should preload these files based on their role:

| Role | Always reads | Reads when relevant |
|---|---|---|
| business-analyst | `AGENTS.md`, `kb/architecture.md` (for context) | — |
| system-analyst | all of `kb/` (lightweight skim) | `kb/domain/*` per scope |
| architect | all of `kb/` | `kb/domain/*` per scope |
| designer | `kb/frontends.md`, `kb/conventions.md` | — |
| django-developer | `kb/stack.md`, `kb/conventions.md`, `kb/verify.md`, `kb/multitenancy.md`, `kb/migrate.md`, `kb/architecture.md`, `kb/document.md` | `kb/domain/*` per task |
| vue-developer | `kb/stack.md`, `kb/conventions.md`, `kb/verify.md`, `kb/frontends.md`, `kb/document.md` | — |
| react-developer | `kb/stack.md`, `kb/conventions.md`, `kb/verify.md`, `kb/frontends.md`, `kb/document.md` | — |
| api-tester | `kb/stack.md`, `kb/verify.md`, `kb/multitenancy.md` | — |
| ui-tester | `kb/frontends.md`, `kb/verify.md` | — |
| reviewer | all of `kb/` | `kb/domain/*` for cross-trace |

---

## Project-specific rules at a glance (fill in)

List 3–7 rules every agent should know in 30 seconds. Each rule
links to the file with full detail and rationale.

- TODO example: "Every queryset for tenant data filters by `<tenant_key>` — see [`kb/multitenancy.md`](kb/multitenancy.md)"
- TODO example: "Migrations run only via the canonical settings module — see [`kb/migrate.md`](kb/migrate.md)"
- TODO example: "No type annotations in Python (legacy decision) — see [`kb/conventions.md`](kb/conventions.md)"

---

## When something is missing

If an agent needs information that's not in `AGENTS.md` / `kb/`:
1. **Don't invent rules.** Use `ask_blocking_question` (see `plane-operations` skill) and mention the initiator.
2. **After the answer**, update `AGENTS.md` and / or the relevant `kb/<file>.md` as part of CHANGES — the missing rule should not need to be re-asked.

---

## Related

- [README.md](README.md) — human-facing project docs
- [CONTRIBUTING.md](CONTRIBUTING.md) — contributor onboarding (for humans)
- This file — AI agent context
