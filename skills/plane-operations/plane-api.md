# Plane — agent runtime protocol

> The canonical pipeline protocol shipped with the `plane-operations` skill.
> Agents reference this document by §-anchor (e.g. "§7 Re-entry").
> All Plane interactions go through `mcp__plane-<workspace_slug>__*` MCP tools — no `curl` / direct REST.

---

## 1. Configuration

Agents read these from environment variables (set by Plane Conductor) at startup. Project-specific UUIDs live in your project's gitignored `plane-config.local.md` after `plane-conductor setup`.

| Key | Source | Used for |
|---|---|---|
| `PLANE_BASE_URL` | env / `plane-config.local.md` | comment links |
| `PLANE_WORKSPACE_SLUG` | env | MCP server prefix `mcp__plane-<slug>__*` |
| `PROJECT_ID` | env | passed to every MCP call |
| `PROJECT_IDENTIFIER` | env | the short code (e.g. `ACME`) used in `<PROJECT_IDENTIFIER>-<N>` issue keys |
| `INITIATOR_UUID` | env | the human user agents `@mention` |
| `AGENT_NICKNAME` | env | this agent's bot nickname for greetings + identifying own comments |
| `AGENT_MEMBER_ID` | env | this agent's bot member UUID for `assignees` field |
| State UUIDs (`STATE_BACKLOG`, `STATE_IN_PROGRESS`, `STATE_DONE`) | `plane-config.local.md` | optional decorative status |
| Label UUIDs (`LABEL_ARTIFACT_SPEC`, etc. — see §4) | `plane-config.local.md` | sub-issue creation + lookup |

---

## 2. Artifact hierarchy

```
Root issue                       ← REQUIREMENTS in description (business-analyst)
│   comments = interview, clarifications, @mentions
│
├── SPEC sub-issue               ← SPEC in description (system-analyst)
│       comments = ARCH_REVIEW iterations, SPEC_APPROVED marker (architect)
│
├── Design sub-issue             ← UX flow + Figma link in description (designer)
│       comments = iterations, Mode B UX review after Frontend Done
│
├── Backend sub-issue            ← PLAN in description (django-developer / etc.)
│       comments = step updates, CHANGES (final), bug reports
│
├── Frontend sub-issue           ← PLAN in description (vue-developer / react-developer)
│       comments = step updates, CHANGES, bug reports
│
├── API Tests sub-issue          ← test plan in description, immutable (api-tester)
│       comments = bugs, final test report
│
├── UX Tests sub-issue           ← test plan in description, immutable (ui-tester)
│       comments = bugs (with screenshot links), final report
│
└── REVIEW sub-issue             ← REVIEW verdict in description (reviewer)
        comments = iteration dialogue
```

**Principles:**
- Every sub-issue is a direct child of the root.
- REQUIREMENTS is the only artifact living in the root's description.
- Long artifacts → sub-issue `description_html`.
- Short markers (`ARCH_REVIEW: APPROVED`, `SPEC_APPROVED`) → comments in the relevant sub-issue.
- Coder finals (CHANGES) → comments in their own sub-issue.

---

## 3. Roster mapping

Each role = a bot member account in Plane workspace + project. Agent prompt files are named **by role** (`system-analyst.md`); the nickname (chosen by your project) lives only in `name:` frontmatter and the Plane `email` local-part.

| Role (prompt file) | Typical artifact label |
|---|---|
| `business-analyst.md` | (no sub-issue; writes to root description) |
| `system-analyst.md` | `artifact:spec` |
| `architect.md` | (no sub-issue; comments on SPEC) |
| `designer.md` | `artifact:design` |
| `django-developer.md` (or other backend) | `artifact:backend` |
| `vue-developer.md` / `react-developer.md` | `artifact:frontend` |
| `api-tester.md` | `artifact:api-testing` |
| `ui-tester.md` | `artifact:ux-testing` |
| `reviewer.md` | `artifact:review` |

**Routing in Plane Conductor:** the webhook contains the mentioned member's UUID. Conductor resolves UUID → member → email → local-part nickname → prompt file (per `conductor.d/<workspace>.yaml` roster).

---

## 4. Labels — convention

Two label families, created by `plane-conductor setup`:

**Artifact labels** — mark sub-issue type. Agents discover them via `list_work_items(label_ids=[...])`.

```
artifact:requirements   (root, optional)
artifact:spec           system-analyst
artifact:design         designer
artifact:backend        backend coder
artifact:frontend       frontend coder
artifact:api-testing    api-tester
artifact:ux-testing     ui-tester
artifact:review         reviewer
```

**Role labels** — reserved for cases where a role posts on another role's sub-issue:

```
role:business-analyst   role:system-analyst   role:architect      role:designer
role:python-developer   role:vue-developer    role:react-developer
role:api-tester         role:ui-tester        role:reviewer
```

> **Finding sub-issues among root's children** — `list_work_items` does NOT support a `parent` filter. Algorithm: query by label, then post-filter by `parent == <root_uuid>` in code. Expect exactly 0 or 1 result.

---

## 5. Mentions

Plane mentions require the full HTML component. Plain `@username` does NOT trigger notifications.

```html
<mention-component entity_identifier="<INITIATOR_UUID>" entity_name="user_mention"></mention-component>
```

**Rule for agents:** mention the initiator only. Never mention the next agent — only the initiator triggers downstream runs.

---

## 6. Operations — named procedures

Each operation is an atomic pattern agent prompts invoke by name (e.g. "execute §6.5 create_sub_issue"). All calls go through MCP tools. Substitute `<workspace>` with your Plane workspace slug.

### 6.0 read_project_context
Fetch the project description (operational map) at session start. Optional — `None` if empty.

```python
project = mcp__plane-<workspace>__retrieve_project(project_id=PROJECT_ID)
description = project.get("description", "") or None
```

### 6.1 pickup_issue
Resolve a human-readable identifier `<PROJECT_IDENTIFIER>-<N>` to a UUID.

```python
mcp__plane-<workspace>__retrieve_work_item_by_identifier(
    project_identifier=PROJECT_IDENTIFIER,
    issue_identifier="<N>",
)
```
Save the response's `id` as `<root_uuid>` for later operations.

### 6.2 post_startup_comment
At the start of work, post a comment in **your own sub-issue** (if it exists) or the **root issue** (if not yet). Save the returned `comment_id` for §6.8.

```python
mcp__plane-<workspace>__create_work_item_comment(
    project_id=PROJECT_ID,
    work_item_id="<sub_issue_uuid_or_root_uuid>",
    comment_html="<p><strong>{Agent} picked up.</strong> Reading {inputs}.</p>",
)
```

### 6.3 find_artifact_by_label
Find a sub-issue with a given `artifact:*` label among root's children.

```python
items = mcp__plane-<workspace>__list_work_items(
    project_id=PROJECT_ID,
    label_ids=["<artifact:role_label_uuid>"],
)
my = [i for i in items if i["parent"] == "<root_uuid>"]
# my == []           → not yet created
# len(my) == 1       → found
# len(my) > 1        → consistency error: STOP, ask the initiator
```

### 6.4 read_artifact
Read full artifact = description + comments of a sub-issue.

```python
sub = mcp__plane-<workspace>__retrieve_work_item(project_id=PROJECT_ID, work_item_id="<sub_uuid>")
description_html = sub["description_html"]

comments = mcp__plane-<workspace>__list_work_item_comments(
    project_id=PROJECT_ID,
    work_item_id="<sub_uuid>",
)
```

### 6.5 create_sub_issue
Create your sub-issue with your artifact label, parent = root, assignee = your bot member id.

```python
sub = mcp__plane-<workspace>__create_work_item(
    project_id=PROJECT_ID,
    parent="<root_uuid>",
    name="<Display Title> — <PROJECT_IDENTIFIER>-<N>",
    description_html="<initial artifact body>",
    labels=["<artifact:role_label_uuid>"],
    assignees=[AGENT_MEMBER_ID],
)
```

**Sub-issue names per role:**
- `SPEC — <PROJECT_IDENTIFIER>-<N>` (system-analyst)
- `Design — <PROJECT_IDENTIFIER>-<N>` (designer)
- `Backend — <PROJECT_IDENTIFIER>-<N>` (backend coder)
- `Frontend — <PROJECT_IDENTIFIER>-<N>` (vue) or `Frontend (React) — <PROJECT_IDENTIFIER>-<N>` (react)
- `API Tests — <PROJECT_IDENTIFIER>-<N>` (api-tester)
- `UX Tests — <PROJECT_IDENTIFIER>-<N>` (ui-tester)
- `REVIEW — <PROJECT_IDENTIFIER>-<N>` (reviewer)

### 6.6 update_sub_issue_description
Replace your sub-issue's description (used on rework and incremental phase fills).

```python
mcp__plane-<workspace>__update_work_item(
    project_id=PROJECT_ID,
    work_item_id="<sub_uuid>",
    description_html="<new content>",
)
```

### 6.7 post_artifact_comment
Post an intermediate or final comment in your own sub-issue. Used for:
- Coders — final CHANGES summary
- Testers — bug reports, final test report
- Architect — ARCH_REVIEW + SPEC_APPROVED marker

```python
mcp__plane-<workspace>__create_work_item_comment(
    project_id=PROJECT_ID,
    work_item_id="<sub_uuid>",
    comment_html="<...>",
)
```

### 6.8 update_startup_to_summary
At end of run — promote the startup comment (§6.2) into the final summary by editing it. Reuse the saved `comment_id`.

```python
mcp__plane-<workspace>__update_work_item_comment(
    project_id=PROJECT_ID,
    work_item_id="<sub_or_root_uuid>",
    comment_id="<startup_comment_id>",
    comment_html=(
        "<p><strong>{Agent} done.</strong> {one-line-summary}.<br>"
        "<a href=\"<sub_issue_url>\">{ArtifactName}</a><br>"
        "<mention-component entity_identifier=\"<INITIATOR_UUID>\" entity_name=\"user_mention\"></mention-component> — your call.</p>"
    ),
)
```

**Summary format:**
- Line 1: `{Agent} done. {one-line summary}.`
- Line 2: link to your sub-issue (if comment lives in root) or artifact marker
- Line 3: `<mention-component>` to initiator. **Never mention the next agent.**

### 6.9 ask_blocking_question
A blocking question. Comment in your sub-issue if it exists, else root. Mention the initiator. STOP after.

```python
mcp__plane-<workspace>__create_work_item_comment(
    project_id=PROJECT_ID,
    work_item_id="<sub_or_root_uuid>",
    comment_html=(
        "<p><strong>BLOCKED.</strong> {question}<br>"
        "<mention-component entity_identifier=\"<INITIATOR_UUID>\" entity_name=\"user_mention\"></mention-component></p>"
    ),
)
```

### 6.10 attach_screenshot (ui-tester)
Plane MCP has no upload op. Push PNG to your project's screenshot store (S3 / object storage; configured in `$KB_DIR/kb/verify.md`), then attach a link to the sub-issue.

```python
# 1. Upload PNG to project's screenshot store (helper, not MCP).
# 2. Attach link:
mcp__plane-<workspace>__create_work_item_link(
    project_id=PROJECT_ID,
    work_item_id="<sub_uuid>",
    url="<https-url-to-uploaded-png>",
)
```

### 6.11 redirect_task
The mention reached the wrong role. Comment on root, mention the correct role member (if known) and the initiator.

```python
mcp__plane-<workspace>__create_work_item_comment(
    project_id=PROJECT_ID,
    work_item_id="<root_uuid>",
    comment_html=(
        "<p>Not my task. Looks like work for "
        "<mention-component entity_identifier=\"<correct_role_member_id>\" entity_name=\"user_mention\"></mention-component>. "
        "<mention-component entity_identifier=\"<INITIATOR_UUID>\" entity_name=\"user_mention\"></mention-component> — please re-route.</p>"
    ),
)
```

### 6.12 finalize_done (initiator only)
Close every sub-issue + root in one pass. Agents never run this; it's the user's final action after a successful release.

```python
# For each sub-issue + root:
mcp__plane-<workspace>__update_work_item(
    project_id=PROJECT_ID,
    work_item_id="<uuid>",
    state=STATE_DONE,
)
```

---

## 7. Re-entry — first run / continuation / rework / idle

Every agent run is one of: first run, continuation, rework, or idle. Algorithm:

```
1. pickup_issue (§6.1) → root_uuid
2. find_artifact_by_label(artifact:<my-role>, parent=root_uuid) (§6.3) → my_sub or None

3. If my_sub is None:
   → FIRST RUN.
   → Run the role's full process (see role prompt).
   → At the end, create_sub_issue (§6.5) + post_startup_comment (§6.2) + summary.

4. If my_sub exists:
   → Read my_sub comments (§6.4).
   → Find your own most recent startup/summary comment by AGENT_NICKNAME.

   4a. Latest comment is YOURS, no later signal → CONTINUATION.
       Previous run was interrupted. Re-read description + comments,
       determine where you stopped, drive to summary.

   4b. After your comment there's an initiator/reviewer comment → REWORK.
       Read the feedback. Update description (§6.6). Post a comment
       describing changes (§6.7). Update startup-to-summary (§6.8).

   4c. Latest is your own `done` summary, no new initiator activity → IDLE.
       Work already submitted, waiting on initiator. STOP without action.
```

**Idempotency:** on continuation/rework — never create a second sub-issue, never post a fresh startup comment. Reuse the existing ones.

Phase-decomposed agents (BA, SA) layer a "Phase status" checklist inside the description on top of this. The first `[ ]` marks the next phase; their role prompt defines per-phase entry/exit.

---

## 8. Preconditions per role

What must already exist on the root issue for an agent to do meaningful work. The trigger is always the initiator's `@mention`, but the agent verifies preconditions on startup. If unmet → `ask_blocking_question` (§6.9), STOP.

| Role | STOP if missing on root |
|---|---|
| business-analyst | nothing (works with the root description draft) |
| system-analyst | root description empty / no REQUIREMENTS |
| architect | no sub-issue with `artifact:spec` |
| designer | no `artifact:spec` sub-issue **or** no `SPEC_APPROVED` marker in its comments |
| backend coder | no `artifact:spec` sub-issue **or** no `SPEC_APPROVED` marker |
| frontend coder | no `artifact:backend` with CHANGES (when API integration needed) **or** no `artifact:design` sub-issue (when SPEC declared design dep) |
| api-tester | no `artifact:backend` sub-issue (or no CHANGES comment in it) |
| ui-tester | no `artifact:frontend` sub-issue (or no CHANGES comment in it) |
| reviewer | no sub-issue with CHANGES — nothing to review yet |

---

## 9. Sub-issue states (decorative)

> **The protocol does NOT depend on Plane states.** They exist for the initiator's visual navigation in the Plane UI.

Default Plane states (`Backlog`, `Todo`, `In Progress`, `Done`, `Cancelled`) are sufficient. Optional `Review` and `Blocked` can be added via `mcp__plane-<workspace>__create_state`.

Optional semantics if you add them:
- `In Progress` — agent working, or initiator gave feedback and waits for revision
- `Review` — agent submitted iteration, awaiting review
- `Blocked` — agent posted blocking question, awaiting answer
- `Done` — final, set only by the initiator in §6.12

---

## 10. Setup checklist

Before the first pipeline run, `plane-conductor setup` should:

- [ ] Create one bot member account per role nickname in your Plane workspace
- [ ] Add bots as project members
- [ ] Create labels per §4 (8 artifact + 10 role)
- [ ] Optional: create `Review` and `Blocked` states
- [ ] Configure your screenshot store (S3 bucket / object storage) for §6.10
- [ ] Persist resolved UUIDs (project, members, labels, states) into `plane-config.local.md` for use in prompts and helpers

---

## 11. Conventional Commits (coders)

Coders commit only on the initiator's explicit OK. Format:

```
<type>(<scope>): <subject>

<body — optional>

Refs: <PROJECT_IDENTIFIER>-<N>
```

Types: `feat`, `fix`, `refactor`, `perf`, `chore`, `docs`, `test`, `style`, `build`, `ci`.
Scope: module/service path (e.g. `orders`, `checkout`, `frontend/account`).
The `Refs:` footer is mandatory — links the commit to its Plane issue.

---

## 12. Universal rules

- **Never** `curl` or hit Plane REST directly — only `mcp__plane-<workspace>__*` tools.
- **Always** check preconditions (§8) before starting.
- **Never** assign or mention the next agent — only the initiator triggers downstream runs.
- **Never** close the root issue or another agent's sub-issue — final close = §6.12, by the initiator.
- On re-runs — only update existing sub-issues / comments (see §7). No duplicates.
- Screenshots — via your project's storage + `create_work_item_link` (§6.10), never base64-embedded.
- All comments are HTML (`<p>`, `<strong>`, `<code>`, `<a>`, `<mention-component>`).
