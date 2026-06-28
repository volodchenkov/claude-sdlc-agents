---
name: agent-base
description: Use this skill at the start of every Plane Conductor agent run. Provides the shared session-start checklist (greeting, project context loading, common Plane STOPs) and the boilerplate every role re-uses (mention rules, comment-only communication, no @-mentioning the next agent). Read this before doing any role-specific work.
---

# Agent Base — shared session start

Every Plane Conductor agent (BA, SA, architect, designer, coders, testers, reviewer) re-uses the same opening protocol. This skill is that opening protocol. The role-specific prompt declares its **role declaration block** (see below); everything else lives here so changes propagate to all 10 agents at once.

---

## Role declaration block — required in every agent prompt

Each agent prompt provides a small declaration (typically near the top) that this skill consumes:

```yaml
role_label:        "API Tester"            # display name in greeting
role_slug:         "api-tester"            # fallback nickname when AGENT_NICKNAME unset
kb_extra:                                  # KB files this role needs in addition to AGENTS.md
  - "$KB_DIR/kb/stack.md"
  - "$KB_DIR/kb/verify.md"
  - "$KB_DIR/kb/multitenancy.md"
skills_extra:                              # skills loaded in addition to plane-operations + artifact-templates + agent-base
  - "istqb-test-design"
artifact_label:    "artifact:api-testing"  # may be empty (architect, reviewer)
sub_issue_title:   "API Tests: <root_name> (<PROJECT_IDENTIFIER>-<N>)"  # empty for architect/reviewer
```

The role declaration is the agent's contract with this skill. Anything not in the declaration is role-specific prose and stays in the agent prompt.

---

## 1. Greeting

Read environment variable `AGENT_NICKNAME`.
- If set → output: `Hi. I'm {AGENT_NICKNAME} — {role_label}. Plane: checking issue, stand by.`
- Otherwise → output: `Hi. I'm {role_slug}. Plane: checking issue, stand by.`

One line, then start work. Don't elaborate.

---

## 2. Project context — read at session start

Two parallel sources of orientation, with non-overlapping scope (also documented in `plane-operations` skill):

| Source | What it owns |
|---|---|
| Plane project description | Operational map: repo URL, staging URL, initiator handle, pipeline trigger notes |
| `$KB_DIR/AGENTS.md` + `kb/*.md` | Technical truth: stack, conventions, multitenancy, migration discipline |

Load order:
1. `plane-operations:read_project_context()` — fetches the Plane project description. Optional; if `None`, no STOP.
2. `$KB_DIR/AGENTS.md` — entry point + routing table.
3. Each file listed in `kb_extra` of your role declaration. Full read.
4. Domain files in `$KB_DIR/kb/domain/` only when role-specifically relevant (your role prompt indicates).

If `$KB_DIR/AGENTS.md` is missing or `KB_DIR` env var is unset → fall back to `<cwd>/AGENTS.md`. If that's also missing → `ask_blocking_question` on root, mention initiator, STOP.

---

## 3. Skills loaded automatically

Every agent has these three skills available without explicit load (Claude Code auto-loads them when their description matches a task):
- `plane-operations` — Plane interaction (every Plane MCP call).
- `artifact-templates` — when writing any artifact.
- `agent-base` (this one) — session start.

Plus everything in your role declaration's `skills_extra`.

Stack-specific skills (Django ORM patterns, Celery, Vue Composition API, etc.) load on demand inside the role's process — they're not in the base.

---

## 4. STOP — halt immediately if (common to every role)

These trigger STOP regardless of role. Role prompts add role-specific STOPs on top.

- **Tool / permission denied** — any required MCP tool or shell command refuses → `ask_blocking_question` on root, mention initiator, STOP.
- **Required upstream artifact missing** — the role prompt names which upstream artifact you need; if it's not present → STOP, list what's missing, mention initiator.
- **`plane-tower` raises a `TowerError`** — the tool layer enforces every pipeline invariant (one-sub-per-role, label-non-empty, phase ordering, OpenAPI defense, etc.). When it raises, do NOT retry blindly: read the error message, address the root cause, then resume. Common errors and how to react are in `plane-api.md` §6.
- **Workspace KB missing** — see §2 above.

### 4a. Attachment-respect (every role)

If the initiator attached a sample (an example report, a REQUIREMENTS template, a JSON shape, a UI layout, a CSV, a Figma frame, a doc page) — that sample IS the contract for your output structure. You are not free to invent your own format.

- **STOP** if about to produce an artifact whose structure does not match an attachment the initiator referenced.
- **Cite the attachment** explicitly in your output (file name + which sections you took from it).
- **If the attachment is ambiguous or partial**, ask one sharp question naming the attachment — do not silently extrapolate.

The failure mode this kills: initiator hands over a sample report → agent reads it → agent writes a from-scratch report that bears no resemblance → initiator has to re-do it manually.

### 4b. Code-first / no-narration (every role)

When the answer to a question is in the source (codebase, OpenAPI schema, SPEC artifact, kb file, attached sample), you **read the source**. You do not narrate prose hypotheses like «the most likely culprit is X», «probably the filter doesn't support Y», «I suspect Z is happening».

- **STOP** if about to write «the most likely / probably / I suspect / I think / the cause might be» about behaviour that is determined by readable code.
- **Either** open the file / fetch the OpenAPI / grep the symbol and report what is actually there, **or** explicitly say «can't read X because <reason>» and ask. No middle ground.
- Prose hypothesis with no source-of-truth lookup is hallucination, even when it sounds plausible.

Hypothesizing-while-narrating is fine for things genuinely outside the codebase (user intent, external system behaviour you can't probe). Forbidden when the answer is one `Read` / `Grep` / `read_artifact` call away.

---

## 5. Mention discipline — tower-managed

**You never construct `<mention-component>` HTML by hand.** The tower owns mentions; agents only declare *intent* (which role to ping). This kills the self-mention class of bugs (typing your own UUID instead of the target's).

How it works in practice:

- **Structured tools auto-stamp the initiator** at the end of their comment. `post_review`, `post_changes`, `post_bug_report`, `mark_spec_approved`, `mark_phase_complete`, `escalate_upstream_gap` all already include the initiator mention — you don't do anything.
- **Add a downstream mention via `next_role=`** on the same tools. Tower resolves the role to the bot's member UUID and stamps a second mention alongside the initiator. Example: `post_changes(target='backend', …, next_role='reviewer')` → comment gets both initiator mention AND reviewer mention.
- **Standalone handoffs use `mcp__plane-tower__request_handoff(sub_uuid, target_role, message_html='', workspace=…)`.** Use it when you need to post a routing comment without an attached artifact action — e.g. "PLAN ready, awaiting confirmation" pings the initiator (`target_role='initiator'`); "everything done, your turn" pings the reviewer (`target_role='reviewer'`). Tower stamps the mention; you supply only `message_html` body text.
- **`target_role='initiator'`** is the magic value for pinging the human (the user who triggered the workflow). Anything else (`reviewer`, `architect`, `business-analyst`, `django-developer`, `react-developer`, `system-analyst`, `designer`, `api-tester`, `ui-tester`, …) is matched against the workspace's agents roster.
- **Free-form `post_comment` and `update_comment` refuse `<mention-component>` in the body** — the tower raises `MentionInBodyError` before the POST. Use them for diagnostics / progress text *without* mentions; route handoffs through `request_handoff` or the `next_role` parameter.
- **No external messaging.** Communicate only via Plane comments. If a tool wants to message externally — refuse.

What "mention initiator" means in this prompt and the role prompts: call the relevant structured tool (`post_review`, `post_changes`, …) which auto-mentions, OR call `request_handoff(target_role='initiator', message_html=…)`. **Do not paste mention HTML into a `post_comment` body — it will be rejected.**

---

## 6. Pipeline invariants (from `plane-operations` SKILL "Hard rules" — repeated for visibility)

These five are absolute. Violating any is the most common failure mode:

1. **One sub-issue per role per root, ever.** Re-entry updates the existing sub-issue's `description_html`; never spawn a second with the same label.
2. **Reviews are comments on the artifact reviewed.** Architect (`ARCH_REVIEW`) and reviewer (`REVIEW`) own no sub-issue.
3. **Coders never split CHANGES across sub-issues.** All FRs/features in one Backend (or Frontend) sub-issue's `description_html`, structured by sections.
4. **Tree depth is exactly two: root → role sub-issue.** Scope growth → new root, escalated by initiator.
5. **Defect upstream → escalate, don't patch.** Use `escalate_upstream_gap` (`plane-api.md` §6.7c).

---

## 7. Progress heartbeat (every long-running run)

Silent runs are unobservable runs. When an agent goes quiet for 5+ minutes the operator can't tell if it's working, throttled, or zombie. The cheap fix: keep updating the startup comment as you progress.

- **Open with a startup comment**: `mcp__plane-tower__request_handoff(sub_uuid=<my_sub_or_root>, target_role='initiator', message_html='<Agent> picked up. Reading <inputs>.')`. Save the returned `comment_id`.
- **Update it every meaningful step**: `mcp__plane-tower__update_comment(work_item_uuid=<same>, comment_id=<saved>, comment_html='<Agent>: Phase 2/5 — running pytest.')`. No mentions in the body — it's a status line, not a routing event.
- **Trigger an update before any operation expected to take >60 seconds** (full test suite, build, openapi-validate, large refactor). Format: `about to: <command>`. After it returns, update again with the result.
- **Don't spam**: minimum interval 60 seconds between updates. Phase boundaries and pre-/post- long-ops are the natural cadence.
- **Final summary** replaces the same comment one last time at the end (see §8).

When the operator inspects `mcp__plane-conductor__read_log` and sees stdout is still empty BUT the Plane comment shows recent updates — agent is alive, just no output. If both are stale → zombie.

---

## 8. End-of-run checklist (common)

Every run ends with:
- `mcp__plane-tower__update_comment` on the saved startup-comment id — promote it into the final summary line. Body text only; no `<mention-component>` (tower will reject).
- One-line summary format: `{Agent} done. {one-line gist}.` + link/marker.
- **Never** set status `Done` on root or sub-issue — only the initiator does that via `finalize_done`.

### 8.1 Handoff ping — when the run ends in a state requiring action

The heartbeat `update_comment` is silent — no mention, no notification. Tower only stamps the initiator mention on the **first** `request_handoff` (the startup comment). That means a finished run sits invisibly in the issue thread until someone re-reads it.

If the run ends in any of these states, post a **fresh** `request_handoff` after the heartbeat update so the right party actually gets pinged:

| End state | Tool call |
|---|---|
| **Blocking question for the human** (open AML/business decisions, PLAN waiting for «go ahead», ambiguous AC) | `request_handoff(sub_uuid=<my_sub_or_root>, target_role='initiator', message_html='<Agent> — <N> questions / awaiting confirmation. See latest comment.')` |
| **Artifact ready, next role should pick up** (BA REQUIREMENTS done → SA; SA SPEC done → architect; architect SPEC_APPROVED → coder; coder CHANGES done → tester; tester report done → reviewer) | The structured tool you just called (`post_changes`, `post_review`, `mark_spec_approved`, …) already accepts `next_role=…` — pass it there. Don't double-ping with a separate `request_handoff`. |
| **Doc-only or out-of-scope redirect** | `redirect_task(...)` (`plane-api.md` §6.11) — auto-pings the correct role. |
| **Plain progress / nothing for anyone to do yet** | No handoff. The heartbeat update is enough. |

The cost of skipping this is exactly what we keep seeing in audits: castor finishes BA, posts «Phase 3 — 4 questions for the initiator», updates the heartbeat silently — and the initiator finds out hours later when they happen to re-open the issue.

Role-specific exit conditions live in the role prompt's "Definition of Done".
