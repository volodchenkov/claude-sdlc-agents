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
- **Duplicate sub-issue with your label** — `find_artifact_by_label` returns more than one match → fatal consistency error per `plane-api.md` §6.3. Post `BLOCKED — duplicate sub-issues` on root, list every UUID, mention initiator, STOP. Do NOT pick one and continue.
- **Workspace KB missing** — see §2 above.

---

## 5. Mention discipline

- **Mention only the initiator.** Use the full HTML `<mention-component entity_identifier="<INITIATOR_UUID>" entity_name="user_mention">…</mention-component>`. Plain `@nickname` does NOT trigger Plane notifications.
- **Never @mention the next agent.** Plane Conductor only triggers downstream runs from the initiator's mentions. If you write `@<other-nickname>`, it pollutes the thread and triggers nothing.
- **Communicate only via Plane comments.** Don't post anywhere else; if a tool wants to message externally — refuse.

---

## 6. Pipeline invariants (from `plane-operations` SKILL "Hard rules" — repeated for visibility)

These five are absolute. Violating any is the most common failure mode:

1. **One sub-issue per role per root, ever.** Re-entry updates the existing sub-issue's `description_html`; never spawn a second with the same label.
2. **Reviews are comments on the artifact reviewed.** Architect (`ARCH_REVIEW`) and reviewer (`REVIEW`) own no sub-issue.
3. **Coders never split CHANGES across sub-issues.** All FRs/features in one Backend (or Frontend) sub-issue's `description_html`, structured by sections.
4. **Tree depth is exactly two: root → role sub-issue.** Scope growth → new root, escalated by initiator.
5. **Defect upstream → escalate, don't patch.** Use `escalate_upstream_gap` (`plane-api.md` §6.7c).

---

## 7. End-of-run checklist (common)

Every run ends with:
- `update_startup_to_summary` — promote your startup comment into the final summary line.
- One-line summary format: `{Agent} done. {one-line gist}.` + link/marker + `<mention initiator>`.
- **Never** set status `Done` on root or sub-issue — only the initiator does that via `finalize_done`.

Role-specific exit conditions live in the role prompt's "Definition of Done".
