# Domain knowledge files

> Drop your domain-specific knowledge files here. Agents load them
> on-demand based on what the task touches.

## What goes here

Ad-hoc files explaining non-obvious **business** or **technical**
behaviour of specific subsystems — things an agent needs to read
*before* working on that area.

Examples:
- `cache-invalidation.md` — how a critical cache works, when to bust it
- `geo-routing.md` — default region/locale logic, geo-IP fallback
- `pricing-engine.md` — how prices are calculated and cached
- `payment-flows.md` — webhook flow, idempotency keys, refund state machine
- `order-state-machine.md` — order status transitions and side effects
- `permissions-matrix.md` — role × action matrix

## What does NOT go here

- Stack info → `../stack.md`
- Service boundaries → `../architecture.md`
- Multi-tenancy rules → `../multitenancy.md`
- Migration discipline → `../migrate.md`
- Anything an *agent prompt* (in `claude-sdlc-agents/prompts/`) already says

## Format

Each file:
- Starts with a one-paragraph summary ("What this is" + "When you need to read it")
- Diagrams in Mermaid where helpful
- Code examples in fenced blocks
- Sections with `## H2` headings for fast skimming
- Cross-links to related domain files

## How agents discover them

The `system-analyst`, `architect`, `django-developer`, and `reviewer`
prompts include: "Load relevant `kb/domain/*.md` files based on what
your task touches." The agent should:
1. List filenames in `kb/domain/` (one-line glob)
2. Decide which are relevant based on task scope
3. Read those, ignore the rest

Keep filenames descriptive enough that step 2 works without opening the
file.
