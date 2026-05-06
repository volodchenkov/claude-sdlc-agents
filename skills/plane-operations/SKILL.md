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
| **read_artifact** | To read full content of an artifact = description + comments of its sub-issue. |
| **create_sub_issue** | First-run only — create your role's sub-issue with proper label and assignee. |
| **post_startup_comment** | First-run only — log "I started working" comment, save its `comment_id`. |
| **update_sub_issue_description** | When the artifact lives in `description_html` (PLAN, SPEC, REVIEW) and needs to be updated. |
| **post_artifact_comment** | When the artifact lives as a comment (CHANGES, ARCH_REVIEW, bug reports). |
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

Project-specific identifiers (project UUID, workspace slug, base URL, member UUIDs, state UUIDs, label UUIDs) are configured by Plane Conductor and passed via environment variables, or stored in your project's gitignored `plane-config.local.md` after `plane-conductor setup` runs.

Reference template for `plane-config.local.md`:

```python
PROJECT_ID         = "<uuid>"           # set by Plane Conductor PLANE_PROJECT_ID env var
PROJECT_IDENTIFIER = "<SHORTCODE>"      # e.g. "ACME", "TODO"
WORKSPACE_SLUG     = "<slug>"           # set by PLANE_WORKSPACE_SLUG
PLANE_BASE_URL     = "<https://...>"    # set by PLANE_BASE_URL

# Initiator (real user)
INITIATOR_UUID = "<uuid>"               # set by INITIATOR_UUID env var

# State IDs (read once via mcp__plane__list_states; usually only Backlog / In Progress / Done are used)
STATE_BACKLOG     = "<uuid>"            # default for new sub-issues
STATE_IN_PROGRESS = "<uuid>"
STATE_DONE        = "<uuid>"            # only set by initiator at finalize_done

# Bot member UUIDs (one per role nickname, populated after `plane-conductor setup`)
# Reference them by nickname for clarity in code:
NICKNAME_TO_MEMBER_UUID = {
    "<nickname-1>": "<uuid>",
    "<nickname-2>": "<uuid>",
    # ...
}
```

The agent itself reads `$AGENT_NICKNAME` and `$AGENT_MEMBER_ID` at runtime; the rest is from config.

---

## Mention syntax — strict rule

The initiator is a real Plane user; agents need to notify them → use full HTML component:

```html
<mention-component entity_identifier="<INITIATOR_UUID>" entity_name="user_mention"></mention-component>
```

Plain text `@<username>` does **not** trigger Plane notifications.

**Agents never @mention each other** — only the initiator triggers the next role. If you feel like writing `@<other-nickname>` in your summary — stop. The initiator sees the artifact, decides who runs next, mentions them.

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
artifact:review         # reviewer
```

```
role:business-analyst   role:system-analyst   role:architect      role:designer
role:python-developer   role:vue-developer    role:react-developer
role:api-tester         role:ui-tester        role:reviewer
```

Label UUIDs are stored in `plane-config.local.md` after setup. Reference them as `LABEL_ARTIFACT_SPEC`, `LABEL_ROLE_BUSINESS_ANALYST`, etc.

---

## Standard workflow (every agent, every run)

```
0. read_project_context() → operational map (optional; None if empty, no STOP)
1. pickup_issue(<PROJECT_IDENTIFIER>-<N>) → root_uuid
2. find_artifact_by_label(<label_for_my_role>, parent=root_uuid) → my_sub
3. Branch on result:
   - my_sub is None → first run → continue at step 4
   - my_sub exists → re-entry → see "Re-entry algorithm" below
4. find_artifact_by_label(<labels_for_my_dependencies>) → upstream artifacts
5. read_artifact(<each upstream>) → context
6. Check preconditions per role prompt. If unmet → ask_blocking_question, STOP.
7. create_sub_issue(name=<role title — PROJECT-N>, label=<my role label>) → my_sub
8. post_startup_comment(my_sub) → save comment_id
9. Do the role work (varies per agent — see role prompt)
10. update_sub_issue_description(my_sub, content=<artifact text>)
    OR post_artifact_comment(my_sub, content=<artifact text>)
11. update_startup_to_summary(comment_id, "<role> done. Summary. <mention initiator>")
```

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
