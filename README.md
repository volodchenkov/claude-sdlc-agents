# claude-sdlc-agents

> SDLC agent pack for [Plane Conductor](https://github.com/volodchenkov/plane-conductor)
> — 10 Claude Code agents grounded in industry methodologies (BABOK,
> C4, ISTQB, OWASP, WCAG).

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

### `prompts/` — 10 generic agent definitions

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

Each file is a [Claude Code agent definition](https://docs.claude.com/en/docs/claude-code/sub-agents)
with YAML frontmatter (`name`, `description`, `model`, `tools`) and a
long-form prompt body. Prompts read project-specific KB files (see
below) and the matching skill before composing artifacts.

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
├── AGENTS.md            # entry point: index, routing table, project rules at a glance
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

### 1. Get the agent files into Claude Code

User-level (available to every Claude Code session):

```bash
git clone https://github.com/volodchenkov/claude-sdlc-agents.git ~/Projects/claude-sdlc-agents
ln -s ~/Projects/claude-sdlc-agents/prompts ~/.claude/agents
ln -s ~/Projects/claude-sdlc-agents/skills  ~/.claude/skills
```

Project-level only:

```bash
cd /your/project
cp -r ~/Projects/claude-sdlc-agents/prompts .claude/agents
cp -r ~/Projects/claude-sdlc-agents/skills  .claude/skills
```

### 2. Drop the KB template into your project

```bash
cp -r ~/Projects/claude-sdlc-agents/template/AGENTS.md  /your/project/
cp -r ~/Projects/claude-sdlc-agents/template/kb         /your/project/
```

Fill in `/your/project/AGENTS.md` and `/your/project/kb/*.md` (every
file has a `# Fill in:` block describing what to write).

### 3. Wire up Plane Conductor

In your Plane Conductor `.env`:

```bash
PROMPTS_DIR=/your/project/.claude/agents     # or ~/.claude/agents if user-level
KB_DIR=/your/project                          # AGENTS.md + kb/ live here
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

`v0.1` — freshly extracted from a private codebase, working in
production for one team. Prompts will evolve as patterns settle. Not
yet versioned for the public; pin a commit if you depend on a specific
shape.

PRs welcome — especially if you adapt the pack to a different
methodology (DSDM, SAFe, FDD, …) or different stack.

---

## Inspiration / acknowledgements

The Django-specific skills (`django-models`, `celery-patterns`,
`pytest-django-patterns`, `systematic-debugging`) are commonly bundled
separately — if you use Django, look at
[kjnez/claude-code-django](https://github.com/kjnez/claude-code-django)
(MIT) for a richer set. The `agents.md` convention is from
[agents.md](https://agents.md/) — one entry-point file at the repo
root, kb/ for details.

---

## License

[MIT](LICENSE) © 2026 Dmitry Volodchenkov
