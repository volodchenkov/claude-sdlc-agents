---
name: plane-operations
description: Use this skill whenever an agent interacts with Plane (https://plane.so) — picking up issues, creating sub-issues for artifacts, posting comments, finding artifacts by label, mentioning users, handling re-entry (continuation vs rework), or completing work. Triggers on any usage of mcp__plane__* tools. Encodes the Plane Conductor pipeline protocol.
---

# Plane Operations — Pipeline Protocol

This skill provides the **operational vocabulary** every agent uses to interact with Plane in the Plane Conductor pipeline. The full protocol — operations with parameter shapes, re-entry algorithm, preconditions per role, commit format — is in the bundled [`plane-api.md`](plane-api.md) (sibling file in this skill). Agents reference it by §-anchor.

**When you load this skill:** use the operation names below (e.g. `pickup_issue`, `create_sub_issue`) instead of inlining MCP tool calls. The MCP details are abstracted; you focus on intent.

---

## Quick reference — operation names

| Operation | When to use |
|---|---|
| **read_project_context** | At session start — fetches the Plane project's `description` field for operational orientation (repo URL, staging, initiator, pipeline notes). Optional: returns `None` if empty. Wraps `mcp__plane-<workspace_slug>__retrieve_project(PROJECT_ID)`. |
| **pickup_issue** | At the start of every run. Resolves `<PROJECT_IDENTIFIER>-<N>` to a UUID. |
| **find_artifact_by_label** | To locate an upstream artifact (SPEC, Backend CHANGES, etc.) among root sub-issues. |
| **list_sub_issues** | All children of a root in one call (regardless of label). Used by reviewer's audit pass. See `plane-api.md` §6.3b. |
| **read_artifact** | Read a sub-issue's description + a slice of its comments. Returns Markdown by default (`description_format='markdown'`), with the newest 20 comments and `has_more_comments` so you can page back via `comments_offset`. See `plane-api.md` §6.4. |
| **create_sub_issue** | First-run only — create your role's sub-issue with proper label and assignee. |
| **post_startup_comment** | First-run only — log "I started working" comment, save its `comment_id`. |
| **update_sub_issue_description** | When the artifact lives in `description_html` (PLAN, SPEC, Design brief) and needs to be updated. |
| **mark_phase_complete** | BA / SA — flip `[ ] Phase N` → `[x] Phase N` in your sub-issue's description with ordering check. See `plane-api.md` §6.6b. |
| **post_artifact_comment** | When the artifact lives as a comment (intermediate notes, ad-hoc updates). For canonical CHANGES / bug reports / reviews use the dedicated ops below. |
| **post_changes** | Coder finals — `post_changes(target='backend', files=…, migrations=…, ready_for_review=True)` renders the canonical CHANGES from fields and posts on the role sub-issue. See `plane-api.md` §6.7d. |
| **post_bug_report** | Testers — `post_bug_report(target='api-tests', affected_role='backend', severity=…, …)` writes the ISTQB bug on the test sub-issue and back-links the affected coder's sub-issue. See `plane-api.md` §6.7e. |
| **post_review** | Reviewer & architect. Call as `post_review(target=…, verdict=…, body=…)`; the operation routes the comment to the right sub-issue (or root) based on `target` and stamps the iteration marker. See `plane-api.md` §6.7b. |
| **mark_spec_approved** | Architect — after the final APPROVED ARCH_REVIEW, post the SPEC_APPROVED marker that coders watch for. See `plane-api.md` §6.7f. |
| **escalate_upstream_gap** | When you find a defect upstream (missing FR, ambiguous AC, broken design contract) — comment in your own sub-issue, mention initiator, STOP. Do not patch locally, do not create a "prerequisite" sub-issue. See `plane-api.md` §6.7c. |
| **update_startup_to_summary** | At end of run — turn the startup comment into the final "done"/"PLAN ready" summary. |
| **ask_blocking_question** | When stuck — comment with mention to the initiator, then STOP. |
| **attach_screenshot** | UX Tester only — upload PNG to object storage, link via `create_work_item_link`. |
| **redirect_task** | When triggered for a task outside your role — comment with mention to the initiator. |

Full operation specs with parameter schemas and examples are in the bundled [`plane-api.md`](plane-api.md) §6.

---

## MCP tool naming — workspace-prefixed

The Plane MCP server is registered **per workspace** in your Claude Code config. Tool names take the form `mcp__plane-<workspace_slug>__<operation>` — e.g. `mcp__plane-acme__retrieve_work_item`. Throughout this skill, examples may show the bare `mcp__plane__*` form for brevity; substitute your workspace slug in real calls. Each agent's `tools:` allowlist enumerates the exact prefixed names for the workspaces it can serve.

---

## Project context vs. KB — two layers

Two parallel sources of orientation, with non-overlapping scope:

| Source | Where it lives | What it owns |
|---|---|---|
| **Plane project description** | Plane → Project → Settings → Description | Operational truth: repo URL, staging URL, production URL, initiator handle, pipeline trigger notes, project-level overrides. Mutates with hosting / team changes, not with code. |
| **`$KB_DIR/AGENTS.md` + `kb/*.md`** | In the project repo, versioned with code | Technical truth: stack, conventions, multitenancy rules, migration discipline, KB routing per role. Mutates with the codebase. |

`read_project_context()` fetches the first; the agent's role prompt directs reads of the second. They are not redundant — if a fact would belong in either, it goes to the layer that owns it. `AGENTS.md` links to the Plane project description for operational facts; it does not duplicate them.

If `read_project_context()` returns `None` (empty description) — no STOP. Continue with `$KB_DIR/AGENTS.md` only.

---

## Configuration values

Project-specific identifiers (workspace slug, project UUID, base URL, initiator UUID, label UUIDs, member UUIDs) are held by the tower MCP server, hydrated at boot from `conductor.d/<workspace>.yaml`. **Agents never read a config file for these.** Pass `workspace=…` to a tower tool when one workspace can't be inferred; everything else (label resolution, member UUID for mentions, project ID) is resolved server-side.

The agent itself reads two env vars at runtime: `AGENT_NICKNAME` (own bot nickname for greetings + identifying own comments) and `AGENT_MEMBER_ID` (own bot UUID for `assignees` field). That's it — there is no `plane-config.local.md` to load.

---

## Mentions — tower-managed

**Agents never type `<mention-component>` HTML.** The tower constructs it from structured params; free-form `post_comment` / `update_comment` reject any `<mention-component>` in the body and raise `MentionInBodyError`.

How agents declare intent:

- Structured artifact tools (`post_review`, `post_changes`, `post_bug_report`, `mark_spec_approved`, `mark_phase_complete`, `escalate_upstream_gap`) auto-stamp the **initiator** mention. Pass `next_role='<role>'` (or `upstream_role` on escalations) to add a second mention to whoever should pick up next.
- Standalone routing or pings: `mcp__plane-tower__request_handoff(sub_uuid, target_role, message_html='', workspace=…)`. `target_role='initiator'` is the special case for pinging the human; any other value (`reviewer`, `architect`, `system-analyst`, `django-developer`, …) matches the workspace's agents roster.

The old rule «mention initiator only, never the next agent» still holds in spirit, but you don't enforce it by writing UUIDs by hand — you enforce it by choosing the right tool. See `plane-api.md` §5 for the full table.

---

## Labels (artifact discovery)

The pipeline uses two label families. The setup script creates them; agents query by UUID.

```
artifact:requirements   # root issue (optional)
artifact:spec           # system-analyst
artifact:design         # designer
artifact:backend        # django-developer (or other backend role)
artifact:frontend       # vue-developer or react-developer
artifact:api-testing    # api-tester
artifact:ux-testing     # ui-tester
```

There is no `artifact:review` label. The reviewer (and the architect) own no sub-issue — reviews are comments on the artifact being reviewed.

```
role:business-analyst   role:system-analyst   role:architect      role:designer
role:python-developer   role:vue-developer    role:react-developer
role:api-tester         role:ui-tester        role:reviewer
```

Label UUIDs are hydrated server-side by the tower from `conductor.d/<workspace>.yaml`. Agents pass labels by role name (`'spec'`, `'backend'`, `'reviewer'`, …) to structured tools (`find_artifact_by_label`, `create_sub_issue`, `post_review`, …); the tower resolves to UUIDs internally. No label-UUID constants in agent prompts.

---

## Hard rules — read before doing anything in Plane

These invariants override anything below. Violating them is the most common failure mode and produces the messy trees the pipeline is designed to prevent.

1. **One sub-issue per role per root, ever.** The single role sub-issue is the canonical artifact. Iterations, follow-ups, per-feature splits, rework, "prerequisite" work — all of these update the existing sub-issue's `description_html` or add comments. They never spawn a second sub-issue with the same role label. If `find_artifact_by_label` returns more than one match, that is a fatal consistency error: post `BLOCKED — duplicate sub-issues` on root, mention initiator, STOP. (`plane-api.md` §6.3.)
2. **A review is a comment on the artifact reviewed.** Architect's `ARCH_REVIEW` lives on the SPEC sub-issue. Final reviewer posts on each artifact sub-issue it has findings for, plus a cross-cutting verdict on root. The location encodes scope: comment on SPEC = SPEC review; comment on Backend = backend code review; comment on root = end-to-end verdict. Iteration markers (`REVIEW (iter N)`) go into the comment text. (`plane-api.md` §6.7b.)
3. **Coders never split CHANGES across sub-issues.** Multiple FRs, multiple features, multiple migrations — all live inside one Backend (or Frontend) sub-issue's `description_html`, structured by sections. Plane's tree is not a partitioning tool. (`plane-api.md` §6.7.)
4. **Tree depth is exactly two: root → role sub-issue.** A sub-issue must never have its own children. If scope outgrows the root, the initiator creates a **new root** and links it via `relation: related-to`. (`plane-api.md` §6.13.)
5. **Found a defect upstream → escalate, don't patch.** Missing FR, ambiguous AC, broken design contract — post `BLOCKED — upstream gap` in your own sub-issue, mention initiator, STOP. The upstream role updates its **existing** artifact; no new "prerequisite" sub-issue. (`plane-api.md` §6.7c.)

---

## Standard workflow (every agent, every run)

```
0. read_project_context() → operational map (optional; None if empty, no STOP)
1. pickup_issue(<PROJECT_IDENTIFIER>-<N>) → root_uuid, root_name
2. find_artifact_by_label(<label_for_my_role>, parent=root_uuid) → my_sub
3. Branch on result:
   - my_sub is None → first run → continue at step 4
   - my_sub exists → re-entry → see "Re-entry algorithm" below
   - len > 1        → fatal consistency error → BLOCKED, STOP
4. find_artifact_by_label(<labels_for_my_dependencies>) → upstream artifacts
5. read_artifact(<each upstream>) → context
6. Check preconditions per role prompt. If unmet → ask_blocking_question, STOP.
7. create_sub_issue(name="<Role>: <root_name> (<PROJECT-N>)", label=<my role label>) → my_sub
8. post_startup_comment(my_sub) → save comment_id
9. Do the role work (varies per agent — see role prompt)
10. update_sub_issue_description(my_sub, content=<artifact text>)
    OR post_artifact_comment(my_sub, content=<artifact text>)
11. update_comment(work_item_uuid, comment_id, "<role> done. Summary.")  # body only, no mention HTML
```

**Reviewers (final reviewer + architect) skip steps 2, 7, 8** — they have no own sub-issue and no role label of their own. Their algorithm:
1. `pickup_issue` → root_uuid, root_name
2. `find_artifact_by_label` for each artifact in scope (SPEC, Backend, Frontend, tests, design)
3. Read each + scan its comments for prior review markers (`REVIEW (iter N)` / `ARCH_REVIEW (iter N)`) → determine iteration
4. If artifact unchanged since last review → IDLE, STOP
5. Compose review, `post_review` on each artifact sub-issue (and root for cross-cutting verdict)
6. `update_startup_to_summary` (startup comment lives on root since no own sub-issue)

For re-entry (continuation/rework), skip steps 7-8 and operate on the existing `my_sub`. Full algorithm in [`plane-api.md`](plane-api.md) §7.

---

## Common pitfalls

### Don't create duplicate sub-issues
If your sub-issue already exists, you are in re-entry mode. Update it; don't create a second one.

### Don't post fresh startup comments on re-entry
Re-use the existing startup `comment_id` via `update_startup_to_summary`. A linear stack of "I started" comments is noise.

### Don't filter `list_work_items` by `parent` — it doesn't support that
The MCP tool has no `parent` parameter. Filter by `label_ids` then post-filter results in code:

```python
items = mcp__plane__list_work_items(
    project_id=PROJECT_ID,
    label_ids=[LABEL_ARTIFACT_SPEC],
)
my = [i for i in items if i["parent"] == root_uuid]
```

### Don't move root issue status
Only the initiator transitions root → Done at the end of the pipeline. Agents only manage their own sub-issue status. Even that is decorative — protocol does not depend on status.

### Don't mention the next agent
Plane Conductor only triggers from initiator's mentions. If you `@mention` the next role, nothing happens — but it pollutes the comment thread.

---

## When in doubt — read

- The bundled [`plane-api.md`](plane-api.md) — full protocol with §-anchors. Sibling file in this skill; ships with the pack.
- This SKILL.md gives the operational vocabulary; `plane-api.md` is the authoritative spec.

---

## What this skill does NOT cover

- Role-specific work (writing code, tests, design). That is in the role's agent prompt.
- Deciding **which** agent should run next. That is the initiator's call, communicated via `@mention`.
- Setup of bot users, labels, states. That is `plane-conductor setup` CLI.
- Artifact content templates (PLAN, SPEC, CHANGES). See sibling skill `artifact-templates`.
