# Plane — agent runtime protocol

> The canonical pipeline protocol shipped with the `plane-operations` skill.
> Agents reference this document by §-anchor (e.g. "§7 Re-entry").
> All Plane interactions go through `mcp__plane-<workspace_slug>__*` MCP tools — no `curl` / direct REST.

---

## 1. Configuration

Two env vars are read by the agent itself; everything else is held by the tower MCP server (hydrated at boot from `conductor.d/<workspace>.yaml`) and resolved server-side when you call a tool.

| Key | Source | Used for |
|---|---|---|
| `AGENT_NICKNAME` | env | this agent's bot nickname for greetings + identifying own comments |
| `AGENT_MEMBER_ID` | env | this agent's bot member UUID for `assignees` field |
| workspace slug, project UUID, base URL, initiator UUID, label UUIDs, member UUIDs | tower (server-side) | passed implicitly by the structured tools (`pickup_issue`, `find_artifact_by_label`, `post_review`, …); pass `workspace=<slug>` only when one workspace can't be inferred |

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
└── UX Tests sub-issue           ← test plan in description, immutable (ui-tester)
        comments = bugs (with screenshot links), final report
```

The architect's `ARCH_REVIEW` and the final reviewer's `REVIEW` are not sub-issues — they are comments posted on the artifact being reviewed (SPEC sub-issue, Backend sub-issue, root for cross-cutting verdict). See §6.7b.

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
| `reviewer.md` | (no sub-issue; comments on each reviewed artifact + cross-cut on root) |

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
```

There is no `artifact:review` label — the reviewer (and the architect) post review comments on the relevant artifact's sub-issue rather than owning their own sub-issue.

**Role labels** — reserved for cases where a role posts on another role's sub-issue:

```
role:business-analyst   role:system-analyst   role:architect      role:designer
role:python-developer   role:vue-developer    role:react-developer
role:api-tester         role:ui-tester        role:reviewer
```

> **Finding sub-issues among root's children** — `list_work_items` does NOT support a `parent` filter. Algorithm: query by label, then post-filter by `parent == <root_uuid>` in code. Expect exactly 0 or 1 result.

---

## 5. Mentions — tower-managed, never hand-rolled

**Agents never construct `<mention-component>` HTML.** The tower owns it. Free-form `post_comment` / `update_comment` refuse `<mention-component>` in the body and raise `MentionInBodyError` before the POST. This eliminates the self-mention class of bugs (typing your own UUID instead of the target's).

How to ping someone:

| Intent | API |
|---|---|
| Pre-stamped initiator mention on a structured artifact comment (CHANGES, REVIEW, bug report, SPEC_APPROVED, escalation) | Auto — tower already adds it. Pass `next_role='reviewer'` (or any role) to the same call to add a second mention. |
| Standalone routing comment on any sub/root | `mcp__plane-tower__request_handoff(sub_uuid, target_role, message_html='', workspace=…)` — tower resolves the role to the bot's UUID and stamps the mention. |
| Ping the human who started the workflow | `request_handoff(target_role='initiator', message_html=…)` |
| Heartbeat / status update with no mention | `update_comment(comment_html='…')` — no mention in body, tower allows it. |

Role names (`target_role`, `next_role`, `upstream_role`) are matched against the workspace's `agents` roster by `prompt_role` bare name. Both `sdlc-agents:reviewer` and `reviewer` work. The special value `'initiator'` resolves to the workspace's human initiator UUID.

The old rule «mention initiator, never mention the next agent» still holds in spirit — but you don't enforce it by writing UUIDs by hand. You enforce it by choosing the right tool: `next_role=`/`request_handoff` for routing, structured-tool defaults for artifact comments, plain `update_comment` for heartbeats.

---

## 6. Operations — named procedures

All pipeline operations are tools on the **`plane-tower` MCP** — a single virtual server (one process per host, no per-workspace prefix). Workspace routing happens inside the tower from the `WORKSPACE_SLUG` env Plane Conductor injects on agent spawn. Agents call `mcp__plane-tower__<op>(…)` with role names (`spec`, `backend`, …) instead of raw label/state/member UUIDs; the tower resolves them from its in-memory snapshot of Plane state.

Most invariants documented in this section (one-sub-per-role, label-non-empty, iteration counters, OpenAPI defense, phase ordering, etc.) are enforced **inside the tower** — see `plane-conductor/src/plane_conductor/mcp_tower.py`. Agents that try to violate them get a `TowerError` back, not a silent data-corruption.

The named-operation bodies below stay as documentation of behaviour: what the tool does, when it raises, what shape it returns. Agents read them to know the contract; they do not re-implement them.

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
Save the response's `id` as `<root_uuid>` and `name` as `<root_name>` for later operations (the root name goes into sub-issue titles — see §6.5).

### 6.2 post_startup_comment
At the start of work, post a startup comment via `request_handoff` (it auto-stamps the initiator mention so the human sees the pickup). Save the returned `comment_id` for the heartbeat updates (§6.2b) and the final summary (§6.8).

```python
result = mcp__plane-tower__request_handoff(
    sub_uuid="<sub_uuid_or_root_uuid>",   # your own sub-issue if it exists, else root
    target_role="initiator",
    message_html="<p><strong>{Agent} picked up.</strong> Reading {inputs}.</p>",
    workspace="<workspace_slug>",
)
startup_comment_id = result["comment_id"]
```

### 6.2b Progress heartbeat
While the run executes, update the startup comment at every meaningful step — phase boundaries, before any operation expected to take >60 seconds, after it returns. **No mentions in the body** — it's a status line, not a routing event. Minimum interval 60 seconds between updates (don't spam).

```python
mcp__plane-tower__update_comment(
    work_item_uuid="<same_as_above>",
    comment_id=startup_comment_id,
    comment_html="<p><strong>{Agent}:</strong> Phase 2/5 — about to: pytest --create-db tests/users.</p>",
    workspace="<workspace_slug>",
)
```

This makes silent runs observable: the operator can `mcp__plane-conductor__list_active_agents` + `read_log`; if stdout is empty BUT the Plane comment shows recent updates, the agent is alive (likely doing a long op), not zombie.

### 6.3 find_artifact_by_label
Find a sub-issue with a given `artifact:*` label among root's children.

```python
items = mcp__plane-<workspace>__list_work_items(
    project_id=PROJECT_ID,
    label_ids=["<artifact:role_label_uuid>"],
)
my = [i for i in items if i["parent"] == "<root_uuid>"]
# my == []           → not yet created → first run
# len(my) == 1       → found            → re-entry, update existing
# len(my) > 1        → fatal consistency error → see below
```

**Hard invariant: one sub-issue per role per root.** There must never be more than one sub-issue with the same `artifact:*` label sharing the same root. If `len(my) > 1`:
1. Do **not** pick one and continue. Do **not** create another.
2. Post a `BLOCKED — duplicate sub-issues for <label>` comment on the **root** issue, list every duplicate UUID, mention the initiator, STOP.
3. The initiator merges manually (one survives, others archived) before re-triggering you.

### 6.3b list_sub_issues
Return every direct child of a root issue, regardless of label. Used by reviewer's Step 0 (audit which artifacts exist) and by anyone needing the full tree map without N separate label queries.

```python
items = mcp__plane-<workspace>__list_work_items(project_id=PROJECT_ID)
children = [i for i in items if i["parent"] == "<root_uuid>"]
```

The MCP tool has no `parent` filter; post-filter in code. Plane caps results — for large projects pass `per_page=100` and paginate.

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

```python
mcp__plane-tower__create_sub_issue(
    role="spec",                                  # symbolic; tower resolves to artifact:spec UUID
    root_uuid="<root_uuid>",
    description_html="<initial artifact body>",
    nickname="<your bot nickname>",               # tower resolves to assignee UUID
)
```

The tower (see plane-conductor `mcp_tower.py`) enforces:
- one-sub-per-role-per-root → raises `DuplicateSubIssueError` if a sub with this role already exists; use re-entry path on the existing one instead
- label resolution from live Plane state at boot → no missing-label-UUID class of bug
- post-create assert that the labels list is non-empty → raises `UnlabelledSubIssueError` on Plane data-corruption (UUID typo dropped silently)
- title shape `<Role>: <root_name> (<PROJECT_IDENTIFIER>-<N>)` from the root's name + identifier — agents do not type the title

Returns `{id, sequence_id, name, labels, parent, ...}`.

**Sub-issue title format:** `<Role>: <root_name> (<PROJECT_IDENTIFIER>-<N>)`. The root name comes from `pickup_issue` (§6.1). Don't truncate — Plane handles UI overflow itself. Always include the parent identifier in parentheses so the title remains traceable when sub-issues are listed out of context (e.g. global "assigned to me" view).

**Sub-issue names per role** (root issue named `Add user dashboard`, key `QSALE-42`, for illustration):
- `SPEC: Add user dashboard (QSALE-42)` (system-analyst)
- `Design: Add user dashboard (QSALE-42)` (designer)
- `Backend: Add user dashboard (QSALE-42)` (backend coder)
- `Frontend: Add user dashboard (QSALE-42)` (vue) or `Frontend (React): Add user dashboard (QSALE-42)` (react — `(React)` qualifier prevents collision with vue-developer when both run)
- `API Tests: Add user dashboard (QSALE-42)` (api-tester)
- `UX Tests: Add user dashboard (QSALE-42)` (ui-tester)

**Reviews live as comments on the artifact being reviewed** — same pattern the architect already uses for `ARCH_REVIEW` on SPEC. Review of SPEC → comment on SPEC sub-issue. Review of Backend → comment on Backend sub-issue. Cross-cutting end-to-end verdict → comment on root. See §6.7b for the full pattern, including the iteration marker.

**One sub-issue per role per root, ever.** Iterations, follow-ups, per-feature splits, "prerequisite" work — none of these are reasons to create a second sub-issue with the same role label. The single sub-issue's `description_html` is the canonical artifact and is updated in place; intermediate findings live in comments on it. If scope genuinely outgrows the root → create a **new root issue** with `relation: related-to`, not a nested sub-issue (see §6.13).

### 6.6 update_sub_issue_description
Replace your sub-issue's description (used on rework and incremental phase fills).

```python
mcp__plane-<workspace>__update_work_item(
    project_id=PROJECT_ID,
    work_item_id="<sub_uuid>",
    description_html="<new content>",
)
```

### 6.6b mark_phase_complete (business-analyst, system-analyst)
Phase-decomposed agents (BA, SA) carry a "Phase status" checklist inside their sub-issue's `description_html`. At the end of every phase they flip `- [ ] Phase N: …` to `- [x] Phase N: …`. The named operation hides the read-modify-write cycle and enforces ordering.

```python
# 1. Read current description
sub = mcp__plane-<workspace>__retrieve_work_item(project_id=PROJECT_ID, work_item_id=my_sub_uuid)
desc = sub["description_html"]

# 2. Validate ordering — refuse to close phase N if any earlier phase is still open
#    (parses checklist, asserts all "[ ] Phase 1..N-1" are now "[x]")

# 3. Replace `- [ ] Phase N:` with `- [x] Phase N:`
new_desc = desc.replace(f"- [ ] Phase {N}:", f"- [x] Phase {N}:", 1)

# 4. Persist
mcp__plane-<workspace>__update_work_item(
    project_id=PROJECT_ID,
    work_item_id=my_sub_uuid,
    description_html=new_desc,
)
```

If you're closing the final phase, also append a Phase status note like `- All phases complete — ready for ARCH_REVIEW`. The agent's role prompt defines the next-phase trigger conditions.

### 6.7 post_artifact_comment
Post an intermediate or final comment in your own sub-issue. Used for:
- Coders — final CHANGES summary
- Testers — bug reports, final test report
- Architect — ARCH_REVIEW + SPEC_APPROVED marker (on the SPEC sub-issue)

```python
mcp__plane-<workspace>__create_work_item_comment(
    project_id=PROJECT_ID,
    work_item_id="<sub_uuid>",
    comment_html="<...>",
)
```

**Coders' rule: never split CHANGES across multiple sub-issues.** If the SPEC has FR-1, FR-2, FR-3, you do NOT create a sub-issue per FR. You produce **one** Backend (or Frontend) sub-issue whose `description_html` covers all FRs in one CHANGES artifact, updated as you progress. Split inside the artifact (sections, headings) — never in Plane's tree.

### 6.7b post_review (reviewer + architect)

A review is a comment posted on the sub-issue (or root) whose contents you reviewed — the location encodes the scope. Agents invoke this by name (`post_review(target='backend', verdict='CHANGES_REQUIRED', body=…)`); the recipe below is what that means in MCP terms.

**Targets and routing:**

| `target=` | Resolves to | Use for |
|---|---|---|
| `spec` | sub-issue with `artifact:spec` | SPEC consistency, traceability, ADRs (architect uses this for `ARCH_REVIEW`) |
| `backend` | sub-issue with `artifact:backend` | Backend implementation review |
| `frontend` | sub-issue with `artifact:frontend` | Frontend implementation review |
| `api-tests` | sub-issue with `artifact:api-testing` | API test plan / report review |
| `ux-tests` | sub-issue with `artifact:ux-testing` | UX test plan / report review |
| `design` | sub-issue with `artifact:design` | Design brief or Mode B verdict review |
| `root` | the root issue itself | Cross-cutting end-to-end verdict |

**Recipe:**

```python
# 1. Resolve target_uuid:
#    target == 'root'  → root_uuid
#    else              → find_artifact_by_label(f"artifact:{target_to_label}", parent=root_uuid)
target_uuid = ...

# 2. Determine iteration N by scanning target's comments for prior markers
#    `REVIEW (iter X) —` or `ARCH_REVIEW (iter X) —` authored by AGENT_MEMBER_ID:
prior = [c for c in list_comments(target_uuid) if c.author == AGENT_MEMBER_ID and re.search(r"(REVIEW|ARCH_REVIEW) \(iter (\d+)\)", c.html)]
N = (max(int(re.search(r"\(iter (\d+)\)", c.html).group(1)) for c in prior) + 1) if prior else 1

# 3. Idempotency guard — if your last review on this target is the most recent activity AND
#    nothing has changed since (no newer comment by anyone else, no description edit) → IDLE, STOP.

# 4. Post via tower (auto-stamps initiator mention; pass next_role to also ping the role that should pick up next):
mcp__plane-tower__post_review(
    target=target,                # 'spec' | 'backend' | 'frontend' | 'api-tests' | 'ux-tests' | 'design' | 'root'
    verdict=verdict,              # 'APPROVED' | 'CHANGES_REQUIRED' | 'BLOCKED'
    body_html="<p>{findings, severity, traceability}</p>",   # NO <mention-component> — tower refuses
    root_uuid=root_uuid,
    next_role=None,               # e.g. 'system-analyst' if you want to ping the SA on CHANGES_REQUIRED
    workspace="<workspace_slug>",
)
```

`marker` is `ARCH_REVIEW` for the architect and `REVIEW` for the final reviewer; tower picks it from `AGENT_NICKNAME`. `verdict` is `APPROVED` / `CHANGES_REQUIRED` / `BLOCKED`. The body must not contain `<mention-component>` — the tower stamps initiator (and optional `next_role`) itself.

A single run may invoke `post_review` against multiple targets (one per artifact with findings) plus a cross-cutting `target='root'`. Each call is independent; iteration counters are per-target.

### 6.7c escalate_upstream_gap (any agent finding a defect upstream)
When a downstream agent (coder, tester, designer, reviewer) discovers a gap that belongs upstream — missing FR in SPEC, ambiguous AC, contradictory requirement, design decision needed — do NOT create a `prerequisite` sub-issue. Do NOT silently fix it locally. Escalate:

```python
mcp__plane-tower__escalate_upstream_gap(
    my_sub_uuid="<my_sub_uuid>",
    affected="SPEC §X.Y | REQUIREMENTS FR-N | Design Frame Z",
    issue="{1-2 sentences describing what is missing or contradictory}",
    proposed_resolution="re-trigger {role} to update {artifact}; I'll resume on the next run",
    upstream_role=None,           # e.g. 'system-analyst' to also ping SA alongside the initiator
    workspace="<workspace_slug>",
)
```

Then STOP. The initiator decides whether to re-trigger the upstream role; that role updates its **existing** artifact (no new sub-issue) and the initiator re-triggers you. This is how nuance is handled: artifacts are mutable, sub-issues are stable.

### 6.7d post_changes (coders)
The coders' final CHANGES summary on a Backend / Frontend sub-issue. Wraps the `artifact-templates` CHANGES template — agent supplies fields, operation renders the canonical HTML and posts as a comment.

```python
post_changes(
    target='backend',           # 'backend' or 'frontend'
    files=[                     # list of changed files with one-line summaries
        ("apps/orders/models.py", "Add `Order.tracking_number`"),
        ("apps/orders/serializers.py", "URL-encode tracking_number"),
    ],
    migrations=[                # may be empty list
        ("0042_order_tracking_number", "adds nullable column, default null"),
    ],
    perf=None,                  # optional dict with N+1 / latency notes
    docs=[
        "docstrings on Order.tracking_url",
        "README §API: tracking endpoint section",
    ],
    ready_for_review=True,      # only set True when DoD met (see role prompt)
)
```

Recipe:
1. Resolve `target_uuid = find_artifact_by_label('artifact:' + target, parent=root_uuid)`.
2. Render the canonical CHANGES section per `artifact-templates` SKILL (sections: Summary, Files, Migrations, Performance, Documentation, READY FOR REVIEW).
3. `create_work_item_comment(target_uuid, comment_html)`.

Validations the operation enforces:
- If `migrations` is non-empty → the rendered HTML includes a "## Migrations" section.
- If `ready_for_review=True` → all DoD checkboxes from your role prompt must be reflected in the body (no gaps).
- The same `target` always resolves to the same single sub-issue (one-sub-per-role invariant, §6.5).
- **API documentation defense (Django coders).** When `target='backend'` and any path in `files` matches `**/views.py` / `**/serializers.py` / `**/schemas.py` (or a file diff touches a `class .*View` / `class .*Serializer` / `@extend_schema`), the op refuses `ready_for_review=True` unless `verification` contains a passing run of the project's OpenAPI verifier slash-command (typically `/verify-openapi`, defined in `$KB_DIR/kb/verify.md`; under the hood it wraps `manage.py spectacular --validate --fail-on-warn`). Zero warnings, zero errors. Catches the common pattern where coders ship endpoints without docstrings → ReDoc/Swagger empty in production. Full requirements (view docstring, `@extend_schema`, serializer `help_text`) live in `documentation-discipline` SKILL §"API endpoint documentation — drf-spectacular contract". If the project hasn't yet registered the verifier — `escalate_upstream_gap` (§6.7c).
- **Frontend coders** (target='frontend') — analogous defense pending; for now `verification` must include the project's own type-check (e.g. `tsc --noEmit`) and lint runs as separate lines.

### 6.7e post_bug_report (api-tester, ui-tester)
A bug found during testing. Single op writes the ISTQB-structured comment on your test sub-issue and links the affected coder's sub-issue, so the bug is discoverable from both sides.

```python
post_bug_report(
    target='api-tests',          # or 'ux-tests'
    affected_role='backend',     # role whose sub-issue contains the broken artifact
    severity='major',            # blocker | major | minor
    title='Order tracking link returns 500 when tracking_number contains special chars',
    environment='storefront-app Vue 3, Chrome 120',
    repro_steps=[
        'Login as customer (test acc 1)',
        "Open /account/orders/{id} where order has tracking_number='ABC/123'",
        'Click tracking link',
    ],
    actual='500 Internal Server Error, browser console "URLError: invalid char"',
    expected='per FR-2, opens https://cdek.ru/track/ABC%2F123 in new tab',
    fix_hint='slash not URL-encoded in serializer.tracking_url',
    screenshots=['<https-url>'],   # ui-tester only; api-tester passes []
)
```

Recipe:
1. `target_uuid = find_artifact_by_label('artifact:' + target, parent=root_uuid)` → your test sub-issue.
2. `affected_uuid = find_artifact_by_label('artifact:' + affected_role, parent=root_uuid)` → coder's sub-issue.
3. Render ISTQB bug template per `artifact-templates`/`istqb-test-design`.
4. `create_work_item_comment(target_uuid, comment_html)` — the bug lives in the test sub-issue.
5. `create_work_item_link(affected_uuid, url=<URL of the comment from step 4>)` — back-link from the affected sub-issue.

The two-way link prevents bugs from getting lost when reviewer or coder reads only one side.

### 6.7f mark_spec_approved (architect)
After the final APPROVED `post_review(target='spec', verdict='APPROVED')`, the architect posts a separate flag comment that downstream coders look for as their "ready to start" signal.

```python
mark_spec_approved(spec_sub_uuid)
```

Recipe:
1. Verify the most recent `post_review` on `spec_sub_uuid` is yours and its verdict is `APPROVED` (refuse otherwise).
2. `create_work_item_comment(spec_sub_uuid, comment_html=template)` — single short comment per `artifact-templates` "SPEC_APPROVED marker".
3. The marker carries the SPEC iteration number and a mention to the initiator.

Coders find this marker by listing comments on the SPEC sub-issue and matching the canonical opening `<p><strong>SPEC_APPROVED</strong>`.

### 6.8 update_startup_to_summary
At end of run — promote the startup comment (§6.2) into the final summary by editing it. Reuse the saved `comment_id`.

```python
mcp__plane-tower__update_comment(
    work_item_uuid="<sub_or_root_uuid>",
    comment_id="<startup_comment_id>",
    comment_html=(
        "<p><strong>{Agent} done.</strong> {one-line-summary}.<br>"
        "<a href=\"<sub_issue_url>\">{ArtifactName}</a> — your call.</p>"
    ),
    workspace="<workspace_slug>",
)
```

The body cannot contain `<mention-component>` — tower refuses. The initiator was already pinged once at startup (§6.2); a second ping here adds no signal and noise. If you genuinely need to re-ping the human at end (e.g. blocking question still unanswered), post a *new* comment via `request_handoff(target_role='initiator', message_html=…)` after the summary update.

**Summary format:**
- Line 1: `{Agent} done. {one-line summary}.`
- Line 2: link to your sub-issue (if comment lives in root) or artifact marker. **No mentions in the body.**

### 6.9 ask_blocking_question
A blocking question. Post in your sub-issue if it exists, else root. Tower stamps the initiator mention. STOP after.

```python
mcp__plane-tower__request_handoff(
    sub_uuid="<sub_or_root_uuid>",
    target_role="initiator",
    message_html="<p><strong>BLOCKED.</strong> {question}</p>",
    workspace="<workspace_slug>",
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
The mention reached the wrong role. Hand off to the correct role on root via `request_handoff` — tower stamps both the target-role mention and the initiator mention.

```python
mcp__plane-tower__request_handoff(
    sub_uuid="<root_uuid>",
    target_role="<correct_role>",      # e.g. 'react-developer' if SPEC mentions UI work
    message_html="<p>Not my task. Looks like work for the {target_role} — please re-route.</p>",
    workspace="<workspace_slug>",
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

### 6.13 phase_split — when scope outgrows the root
Sometimes mid-pipeline it becomes clear the work spans more than one cohesive deliverable: a follow-up phase, a parallel feature, a prerequisite that deserves its own SPEC. The wrong move is to add another SPEC sub-issue, or to nest sub-issues two levels deep. The right move:

- Agents do not split scope themselves. They post a `BLOCKED — scope growth` comment in their own sub-issue (per §6.7c structure but with `Issue: scope of root <PROJECT-N> has grown beyond original SPEC; <one-line description of split>`), mention initiator, STOP.
- The initiator creates a **new root issue** describing the new phase / feature, links it with `relation: related-to` (or `blocks` / `blocked-by` as appropriate), and triggers the pipeline against the new root.
- Sub-issues never have grandchildren. The tree is exactly two levels deep: root → role sub-issue → (comments). Any work that doesn't fit in the role sub-issue's `description_html` belongs in a different root.

### 6.13b Short pipelines — when the full SDLC is overkill

A documentation update or a one-line config tweak doesn't need 7 sub-issues + ARCH_REVIEW + REVIEW. Two short pipelines are supported:

**`pipeline:doc-only`** — pure documentation work (README, ADR notes, internal `kb/*.md`, docstrings). No code paths, no test coverage, no architecture decisions.

Flow:
1. Initiator creates the root issue with the label `pipeline:doc-only` (in addition to any artifact label).
2. Initiator triggers the relevant **coder** (django / react / vue) directly — there is no BA, SA, architect, designer, or tester run.
3. The coder works in **doc-only mode**: skips PLAN, writes only documentation, posts `post_changes(target=…, files=[…doc files…], ready_for_review=False, summary='docs only')`.
4. Initiator reviews the diff in the repo and closes manually. No final reviewer pass.

Every other agent (BA, SA, architect, designer, testers, reviewer) MUST detect this label at startup and `redirect_task` to the coder before doing any work — see role prompts.

**`pipeline:trivial`** — reserved for future use (e.g. a typo fix, a one-line config nudge). Not implemented yet; placeholder so initiators don't repurpose `pipeline:doc-only` for code work.

### 6.14 link_related_root (initiator only)
Connect a newly-created phase / parallel-feature root to its predecessor. Used right after the initiator creates the new root in response to a `phase_split` escalation. Agents do not run this — but the operation is documented here for completeness and for future tooling.

```python
link_related_root(
    other_root_uuid="<predecessor-root-uuid>",
    kind="related-to",   # "related-to" | "blocks" | "blocked-by"
)
```

Recipe:
1. `mcp__plane-<workspace>__create_work_item_relation(project_id, work_item_id=<new_root>, related_issue=<other_root>, relation_type=<kind>)`.
2. Plane creates the inverse relation automatically on the other side.

Use `blocks` / `blocked-by` only when the dependency is hard (the new phase cannot start until the old one merges). Otherwise prefer `related-to` so neither root is gated by the other.

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

**Reviewers (final reviewer + architect) skip steps 4a/4b — they have no own sub-issue.** They detect re-entry by reading their own previous review comments (markers `REVIEW (iter N)` / `ARCH_REVIEW (iter N)`) on the artifact they're reviewing (§6.7b). New iteration if and only if the artifact has changed since the last review.

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
- [ ] Persist resolved UUIDs (project, members, labels, states) into the workspace's `conductor.d/<workspace>.yaml` — the tower hydrates them at boot and exposes them to agents through the structured MCP tools

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
