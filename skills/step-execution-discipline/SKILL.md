---
name: step-execution-discipline
description: Use this skill when a coder (django-developer / vue-developer / react-developer) or a tester (api-tester / ui-tester) executes a multi-step PLAN. Encodes (a) how to size steps with the 5-budget AND-filter and vertical-slice rule, (b) the one-step-per-invocation loop with checkbox state in PLAN sub-issue description, and (c) the self-handoff that lets plane-conductor re-spawn the agent for the next step.
---

# Step-Execution Discipline

Multi-step PLANs are how the team avoids 14-step single-run burnouts: tokens burn, sessions hang on step 4, no visible progress, no resume point. This skill encodes the contract.

Two parts:
1. **Sizing** — how to decompose a SPEC into the right number of steps with the right edges.
2. **Execution** — one invocation per step + self-handoff + checkbox state in PLAN sub-issue description.

The infra side (queue-on-running so self-handoff doesn't race the webhook) lives in `plane-conductor` ≥ the PR that landed queue-on-running. If your conductor is older, self-handoff drops on the floor — escalate before relying on this skill.

---

## Part 1 — Sizing

You author the PLAN. The SA produces SPEC with acceptance criteria; only you know what's hard. Don't ask SA to pre-size — they don't know the codebase shape you're about to touch.

### 5-budget AND-filter (every step must pass ALL five)

| Budget | Limit | Why |
|---|---|---|
| **Time** | ≤15–20 min wall-clock work | Beyond this, hang risk + context bloat + retry chains land in the wrong place |
| **Files** | ≤10 touched | More = mixing concerns; next-step diff becomes unreadable |
| **Diff** | ≤300–500 net LoC | More = reviewer (human or agent) can't track between-step delta |
| **Acceptance** | exactly ONE binary statement | «After this step, endpoint X returns 201 with {id}». NOT «feature works», NOT «tests pass» — that's not a step, that's a goal |
| **Verifiability** | compiles + existing tests still green | Next step starts on a working tree, not on a half-broken one |

A draft step violating any budget → split further. Recursion until clean. The filter is AND, not OR.

### Vertical slices by default

Each step is a **thin vertical pass through all layers** (model + migration + view + minimal smoke), not a horizontal layer (all models, then all APIs, then all UI).

❌ Horizontal (wrong):
```
1. All models
2. All migrations
3. All endpoints
4. All serializers
5. All UI
```
After step 1 nothing works. Until step 5 nothing works. No demoable point.

✅ Vertical (right):
```
1. POST /transactions creates record (model + migration + view + 1 smoke)
2. GET /transactions returns list (filter on tenant)
3. UI: transactions list page
4. UI: create-transaction form
```
Each step ships something demoable. Pipeline can pause at any step with the product in a working state.

**Horizontal only with explicit justification** in PLAN: «not demoable, but justified because <reason>» — e.g. a shared helper that two later vertical slices both consume. If you can't articulate why, it's wrong.

### Anti-patterns to refuse

| Anti-pattern | Why it's wrong |
|---|---|
| «Step: implement feature X» | That's the whole task, not a step |
| «Step: make tests pass» | That's an acceptance criterion, not a step |
| «Step: rename variable on line 42» | Cold-start overhead > the work itself |
| «Step: refactor module Y» | Not verifiable mid-way; either nothing works during or after |
| «Step: cleanup» | Vague. Either it has a concrete edit list (then write it) or it isn't a step |

---

## Part 2 — Execution loop

Each invocation = **exactly one step**. Not a loop over many steps.

### Per-invocation procedure

```
1. read_artifact(my role sub-issue) → parse PLAN steps
2. next_step = first [ ] in PLAN
   if no next_step → FINAL PASS (see below); STOP
3. implement next_step (code only — no other steps)
4. run scoped verification (the step's `Verify:` command)
   if red:
       post_comment("Step N blocked: <details>")
       update_comment("blocked at Step N")
       STOP — wait for initiator
   if green:
       update PLAN description: change [ ] to [x] for this step
       update_sub_issue_description(updated PLAN)
       post_comment("Step N done. <1-line summary>. ✅")
5. request_handoff(sub_uuid=<my sub-issue uuid>, target_role='<my own role>',
                   message_html='Step N done. Continuing.')
6. STOP — exit cleanly. The conductor receives the webhook and re-spawns
   you for the next step. Do NOT try to execute step N+1 in this session.
```

### Final pass (when no [ ] remains)

When step 2 above finds no unchecked items:
- Run full DoD verification (all commands from `$KB_DIR/kb/verify.md` for coders; ISTQB-shaped report for testers)
- Compose CHANGES (template in `artifact-templates`)
- `post_changes(... ready_for_review=True)`
- `request_handoff(target_role='reviewer', ...)` — handoff to next role, not to self
- STOP

### Self-handoff requires conductor queue-on-running

`request_handoff(target_role='<self>')` posts a webhook-triggering comment. Plane delivers it ~ms after your subprocess starts shutting down. Without conductor's `request_spawn` queue-on-running, the re-spawn lands on a still-active triple and is dropped as duplicate — chain dies silently.

Conductor PR that landed queue-on-running: `plane-conductor` `feat/queue-on-running` (merged 2026-06-19). If your conductor is older, escalate to initiator before starting — your handoffs will drop.

### Re-entry semantics

- **Mid-step crash**: next invocation reads PLAN, sees first `[ ]` (the one you crashed on), **re-runs that step from scratch**. Any partial work in code is overwritten by the fresh implementation. Don't try to detect partial progress — re-do.
- **Initiator unchecked a step**: same flow. First `[ ]` from top, re-run.
- **Initiator added a step mid-PLAN**: same flow. PLAN is the only source of truth between invocations.

### What never goes in a single invocation

- Two steps in a row (even if «small»)
- A loop over steps
- A speculative «I'll do step N+1 while I'm here»

If you find yourself wanting any of those — the steps were sized wrong. Stop, fix PLAN, hand off.

---

## When to draft a multi-step PLAN at all

Not every task needs step-execution. The trigger is the **existence of multi-step work**, not its size.

- Single-file typo / lint fix / dep bump → no PLAN, direct CHANGES. Step-execution overhead is wasted.
- Anything that touches >1 file with >1 acceptance criterion → PLAN, even if it's only 2-3 steps. Visibility + resume-on-fail beats overhead.

If unsure: draft the PLAN. Worst case the PLAN has 2 steps and you handed off once — cheap. Best case you caught that «trivial» work was actually 6 steps in disguise.

---

## Cross-references

- `artifact-templates` skill — PLAN template (includes Files / Acceptance / Slice per step)
- `plane-operations` skill — `request_handoff`, `update_sub_issue_description`, re-entry detection
- `documentation-discipline` — final-pass DoD includes doc updates
- `code-review-discipline` — what reviewer checks when you hand off final CHANGES
