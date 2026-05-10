# claude-sdlc-agents

> SDLC agent pack for [Plane Conductor](https://github.com/volodchenkov/plane-conductor)
> — 10 pipeline agents + 2 meta-agents, grounded in industry methodologies
> (BABOK, C4, ISTQB, OWASP, WCAG).

A starter pack of specialised Claude Code agents wired to follow
standard software-engineering methodologies, designed to drop into
[Plane Conductor](https://github.com/volodchenkov/plane-conductor) as a
full SDLC pipeline triggered by Plane mentions.

Project-specific details (stack, conventions, multi-tenancy rules,
verification commands, frontends inventory) are kept **outside** the
prompts — in your own project's KB, populated from the `template/`
directory in this repo.

---

## What's inside

### `agents/` — generic agent definitions

#### SDLC pipeline (10) — triggered by Plane @-mentions

| File (also the `name:` for `claude --agent <name>`) | Role | Methodology |
|---|---|---|
| `business-analyst.md` | Business Analyst | BABOK v3 (4 requirement types, MoSCoW, INVEST, 5 Whys) |
| `system-analyst.md` | System Analyst | C4 + DDD bounded contexts + REST + IEEE 29148 + ADR |
| `architect.md` | Architect | SOLID + DDD + ADR governance + 6-area review checklist |
| `designer.md` | UX/UI Designer | WCAG 2.1 AA + Nielsen heuristics + Material/HIG |
| `django-developer.md` | Django backend developer | project-conventions-driven |
| `vue-developer.md` | Vue developer (Vue 2 / Vue 3) | project-conventions-driven |
| `react-developer.md` | React / Next.js developer | project-conventions-driven |
| `api-tester.md` | API Tester | ISTQB Foundation (EP, BVA, decision tables, state transition, use-case) |
| `ui-tester.md` | UX/E2E Tester | ISTQB + WCAG 2.1 AA |
| `reviewer.md` | Final Reviewer | OWASP Top 10 + SOLID + Google review checklist |

#### Meta agents (2) — invoked directly by the user, not by Plane

| File | `name:` (alias) | What it does |
|---|---|---|
| `prompt-architect.md` | `zuse` | Designs and audits agent prompts, skills, and KB reference docs. Plan-then-edit; runs a 9-block audit on every prompt before changing it. |
| `project-manager.md` | `tron` | Personal PM. Triages incoming work into "fix it myself" / "file in Plane and run the pipeline" / "clarify first". Reads GitHub / GitLab / kubectl / helm freely; every state change requires explicit approval. |

Each file is a [Claude Code agent definition](https://docs.claude.com/en/docs/claude-code/sub-agents)
with YAML frontmatter (`name`, `description`, `model`, `tools`) and a
long-form prompt body. SDLC prompts read project-specific KB files (see
below) and the matching skill before composing artifacts. Meta-agent
prompts have no project-specific reads — they work in any repo.

### `skills/` — 9 reusable [Claude Code skills](https://docs.claude.com/en/docs/claude-code/skills)

| Skill | Used by | Encodes |
|---|---|---|
| `babok-elicitation` | business-analyst | BABOK v3 elicitation + analysis knowledge areas |
| `system-design-techniques` | system-analyst | C4, DDD bounded contexts, REST conventions, ADR pattern |
| `architecture-review-framework` | architect | 6-area review checklist, SOLID + DDD lenses, ADR governance |
| `ux-design-discipline` | designer | WCAG 2.1 AA, Nielsen heuristics, platform conventions |
| `documentation-discipline` | coders | docstrings, README updates, ADR status, migration notes |
| `istqb-test-design` | api-tester, ui-tester | EP / BVA / decision tables / state transition / use case |
| `code-review-discipline` | reviewer | OWASP Top 10, SOLID, Google review checklist, cross-trace |
| `artifact-templates` | every agent | canonical Markdown templates for every artifact type |
| `plane-operations` | every agent | the Plane read/write protocol (pickup, sub-issue, comments, mentions, re-entry) |

### `template/` — KB template you copy into your project

Project-specific facts go in your own repo — versioned alongside your
code. The pack ships an empty template:

```
template/
├── AGENTS.md                  # entry point: index, routing table, project rules at a glance
├── PROJECT_DESCRIPTION.md     # draft of the Plane project description (operational layer)
└── kb/
    ├── stack.md         # languages, frameworks, libs, versions
    ├── conventions.md   # lint, types, naming, TDD policy
    ├── architecture.md  # services / bounded contexts / import contracts
    ├── verify.md        # slash-commands / make / npm scripts for lint, tests, builds
    ├── multitenancy.md  # tenant isolation rules (or "N/A")
    ├── migrate.md       # DB migration discipline
    ├── frontends.md     # per-frontend stacks, build commands
    ├── document.md      # docstring style, doc-generation tool
    └── domain/          # ad-hoc domain knowledge files
```

You copy `template/` into your repo, fill it in, commit. The agents
read it via `$KB_DIR` env var (set by Plane Conductor) or fall back to
`<cwd>/AGENTS.md`.

This follows the [agents.md](https://agents.md/) emerging convention
(Cursor / OpenAI Codex / Aider / Claude Code).

---

## How it fits with Plane Conductor

Plane Conductor is the orchestrator: it receives a Plane webhook on
`@<nickname>` mention, resolves the nickname, and spawns
`claude --agent <prompt-role> --print` locally. **What that agent
actually does is defined by the prompt + skills here.**

```
  human posts "@castor draft requirements" in Plane
            │
            ▼
  Plane Conductor (orchestrator)
  │  —  resolves bot user `castor` → prompt_role `business-analyst`
  │  —  sets env: KB_DIR, AGENT_NICKNAME=castor, AGENT_MEMBER_ID, ...
  │
  ▼ spawns
  claude --agent business-analyst --print
  │
  ▼ loads
  prompts/business-analyst.md
  + babok-elicitation skill + plane-operations skill + artifact-templates
  + reads $KB_DIR/AGENTS.md and relevant kb/*.md
  │
  ▼ writes
  structured REQUIREMENTS into the root issue's description, posts comments
```

Nicknames (`castor`, `sark`, `flynn`, ...) live in *your* Plane workspace
and `conductor.yaml` config; the prompts are nickname-agnostic. The
Greeting line uses the `AGENT_NICKNAME` env var if Plane Conductor sets
it, falling back to the role name.

---

## Install

### 1. Install the plugin

The pack ships as a Claude Code plugin via marketplace.

```bash
claude plugin marketplace add volodchenkov/claude-sdlc-agents
claude plugin install sdlc-agents@sdlc-agents-marketplace
```

This makes 10 agents (`claude --agent business-analyst`,
`system-analyst`, …) and 9 skills available globally.

For local-development install pointing at a checkout:

```bash
claude plugin marketplace add /path/to/claude-sdlc-agents
claude plugin install sdlc-agents@sdlc-agents-marketplace
```

The same commands are available as slash-commands inside an
interactive Claude Code session (`/plugin marketplace add …`,
`/plugin install …`).

### 2. Drop the KB template into your project

```bash
cp ~/Projects/claude-sdlc-agents/template/AGENTS.md  /your/project/
cp -r ~/Projects/claude-sdlc-agents/template/kb      /your/project/
```

Fill in `/your/project/AGENTS.md` and `/your/project/kb/*.md` (every
file has a `# Fill in:` block describing what to write).

### 2b. Set up the Plane project description (optional but recommended)

Agents read a short *operational* one-pager from your Plane project's
**Settings → Description** at session start (repo URL, staging,
initiator, pipeline notes). It is **complementary** to `AGENTS.md`
(technical truth, in repo) — never duplicated.

Use the version-controlled draft as a starting point, then paste the
body into Plane:

```bash
cat ~/Projects/claude-sdlc-agents/template/PROJECT_DESCRIPTION.md
```

If the description is empty, agents skip this layer with no STOP.

### 3. Wire up Plane Conductor

In your Plane Conductor workspace YAML (`conductor.d/<slug>.yaml`):

```yaml
prompts_dir: ~/.claude/plugins/.../sdlc-agents/agents   # or your project's .claude/agents
kb_dir:      /your/project                              # AGENTS.md + kb/ live here
```

In `conductor.yaml` reference the prompt-role names from `prompts/`:

```yaml
agents:
  - { nickname: castor,  prompt_role: business-analyst }
  - { nickname: sark,    prompt_role: system-analyst }
  - { nickname: flynn,   prompt_role: architect }
  - { nickname: quorra,  prompt_role: designer }
  - { nickname: rinzler, prompt_role: django-developer }
  - { nickname: ram,     prompt_role: vue-developer }
  - { nickname: beck,    prompt_role: react-developer }
  - { nickname: yori,    prompt_role: api-tester }
  - { nickname: gem,     prompt_role: ui-tester }
  - { nickname: dumont,  prompt_role: reviewer }
```

(Pick your own nicknames — above is illustrative.)

---

## Adapting to your own pipeline

- **Different roles?** Edit / add prompt files; update your
  `conductor.yaml` roster. Methodology skills are independent — keep
  some, drop others, add new ones.
- **Different methodologies?** Replace the skill content. Prompts
  reference skills by name, so as long as you keep the slug, the agent
  picks up your version.
- **Different stack?** Fill in `kb/stack.md`, `kb/conventions.md`,
  `kb/frontends.md`, `kb/migrate.md` to match. Coder prompts are
  conventions-agnostic; they read your KB.
- **No multi-tenancy?** Set `kb/multitenancy.md` to `"N/A —
  single-tenant"`. Agents skip multitenancy checks entirely.
- **No service boundaries?** Set `kb/architecture.md` to
  `"N/A — monolithic single-app"`. Skip imports / DDD framework checks.

---

## Status

`v0.2` — packaged as a Claude Code plugin (`marketplace.json` /
`plugin.json`), 10 agents + 9 skills, KB template + Plane project
description template. Working in production for one team. Prompts will
evolve as patterns settle.

PRs welcome — especially if you adapt the pack to a different
methodology (DSDM, SAFe, FDD, …) or different stack.

---

## Optional companion skills

This pack stays stack-agnostic on purpose. For Django projects, the
`django-developer` agent references four extra skills that are NOT
shipped here — they're authored separately and remain optional:

- `django-models` — fat-model / thin-view patterns, QuerySet composition
- `celery-patterns` — task design, retries, idempotency
- `pytest-django-patterns` — fixtures, factories, pytest-django
- `systematic-debugging` — 4-phase root-cause methodology

Recommended source: [kjnez/claude-code-django](https://github.com/kjnez/claude-code-django) (MIT).

The `django-developer` agent works without them — it falls back to
first principles + your `$KB_DIR/kb/` rules. With them installed, it
loads them automatically when designing models, writing Celery tasks,
writing pytest, or debugging.

The `agents.md` convention is from [agents.md](https://agents.md/) —
one entry-point file at the repo root, `kb/` for details.

---

## License

[MIT](LICENSE) © 2026 Dmitry Volodchenkov
