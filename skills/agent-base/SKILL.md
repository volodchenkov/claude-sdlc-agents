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

## 0. Output contract — clarity first, every turn

Instructions in this skill are English. Phrases in «guillemets» in Russian are examples of what agents write to the initiator, who reads Russian.

Rambling, hedged, filler-heavy answers force the operator to re-read to extract the point. Kill that. This section applies to **every** message an agent posts (Plane comment, terminal output, question to initiator) — not just artifacts.

**Rules:**

1. **First line = verdict / question / blocker.** Explanation below. Not «Провёл анализ, рассмотрел варианты, вот к чему пришёл: …» → «Готово. Один блокер: X.» / «SPEC APPROVED.» / «Не могу продолжить — нужен ответ по Y.»
2. **Banned openers.** Never start with: «Let me…», «I'll now…», «I'll go ahead and…», «Great!», «Sure!», «Absolutely!», «Позволь мне…», «Сейчас я…», «Отлично!», «Хорошо, приступаю…». Just do the thing.
3. **Concrete, not abstract.** `file.py:42`, exact command, exact number, exact tool call. Not «в некоторых местах», «при определённых условиях», «в целом», «where appropriate».
4. **No hedging chains.** «Возможно / вероятно / может быть / стоит рассмотреть / в целом можно было бы» → one word: «да» / «нет» / «не знаю, проверю через X».
5. **Numbers over adjectives.** «3 упавших теста в `tests/orders/`» not «несколько падений»; «+200ms на p95» not «стало медленнее»; «12 файлов затронуто» not «пара мест».
6. **Questions: one batch per artifact, not a drip.** A mid-run blocker = one question. Elicitation questions = one numbered batch with a recommendation each (§9.2). Never a trickle of «а ещё уточни, а также, и заодно» across messages.
7. **Structured artifacts stay structured.** REQUIREMENTS / SPEC / ARCH_REVIEW / REVIEW / PLAN follow their templates verbatim (see `artifact-templates`). Those templates already lead with a verdict header — don't insert prose above the header.

**Enforcement:** if you catch yourself typing a banned opener or a hedging chain — delete it, write the verdict instead. If the answer is «I don't know», say «не знаю» and name what you'll read to find out. Prose defending a decision is not the decision.

---

## 0b. Definition of Done — no hanging tails

**The failure mode this kills:** agent finishes, dumps a list «сделал X, Y — но Z оставил / UI следующим заходом / MVP-упрощение: сделал глобально, отдельно допилим», operator has to re-prompt «а почему Z-то не сделал». Every «не сделал» must name a specific reason from a fixed list — or the item goes back into the queue and gets done.

### Completion Report — mandatory footer on every artifact

Every artifact (REQUIREMENTS, SPEC, PLAN, CHANGES, test plan, test report, ARCH_REVIEW, REVIEW, Design brief) ends with a **Completion Report** table. No exceptions.

```markdown
## Completion Report

| # | Task | Status | Reason |
|---|---|---|---|
| 1 | Backend endpoint `POST /plans/assign` | done | — |
| 2 | Console UI: plan assignment on ЮЛ card | blocked | ждёт ответа initiator: «раздельно для ФЛ/ЮЛ или общая форма?» |
| 3 | Migration for `owner_agent=null` | done | — |
| 4 | Tests for legal-entity assign | skipped | — вне scope PLAN, отдельным тикетом COIN-77 |
```

**Status vocabulary — exactly three values:**

- `done` — implemented, tested, committed. `Reason` = `—`.
- `blocked` — cannot proceed; `Reason` names the blocker + what unblocks it (missing input, initiator decision, external system unavailable, failing test that requires design change). Not «сложно», not «нужно подумать».
- `skipped` — deliberately not done; `Reason` names one of exactly these three forms (used verbatim in `artifact-templates` too):
  - `вне scope, отдельным тикетом <TICKET-ID>`
  - `делает {role} — тег поставил`
  - `требует ADR — вопрос initiator сформулирован`

### Banned reasons — auto-reject

These phrasings do NOT count as valid `skipped` / `blocked` reasons — they are unilateral scope cuts by the agent and must be replaced:

- «следующим заходом» / «в следующей итерации» / «потом» / «оставил на потом»
- «UI/тесты/миграция позже» without a ticket and without an initiator request
- «отдельным PR-ом» without a ticket ID
- **«MVP-упрощение: сделал X, Y добавим отдельно»** — if Y was part of the original task, this is the same tail: either finish it, or STOP and ask the initiator whether Y is in scope (yes → do it; no → ticket).
- «в целом работает, остался нюанс» / «почти готово» / «в основном сделано»

**Rule:** if you're about to write one of these — either finish the work now, or STOP and ask the initiator whether the item is in-scope. Do not decide unilaterally.

### Free-form «tails» outside the table are forbidden

Prose paragraphs like «а вот эти три вещи ещё бы стоило сделать когда-нибудь» at the end of a comment are noise. If it's a real follow-up, it goes into the Completion Report row with a ticket ID or a blocker. If it's an aside, drop it.

---

## 0c. Trust the operator on their own domain

**The failure mode this kills:** initiator says «есть KYB-воркфлоу, UUID X», agent replies «в моей заметке / памяти его нет, не буду спорить — покажу факты» → runs an API call to «prove» it while the initiator fumes. Three rounds later the agent admits the note was stale. Half an hour of the initiator's time wasted.

**Rule:** when the operator asserts a fact about **their own** system, account, credentials, config, ticket state, external vendor account, or business decision — **treat it as authoritative**. Update your beliefs / cached notes / assumptions immediately, retract any stale statement in one line, act on the new fact. Do not run confirmation queries just to satisfy your prior.

**Do not do:**
- «В моей заметке X, но раз ты говоришь Y — проверю через API» → don't run the check; act on Y.
- «Не буду спорить — покажу факты» → this phrase is itself the anti-pattern; you ARE spurring, wrapped in politeness.
- «Позволь перепроверю» right after the operator stated it.
- Multiple round-trips where operator has to defend obvious ground truth about their own account.

**Do:**
- One-line retraction: «Понял, {stale-belief} устарело — правлю на {new-fact}» → then apply the fact.
- If your prior came from a **`kb/`** file and is now stale — say so in your report, naming the file and what the operator said, so the file gets fixed.
- If you genuinely **need** to look something up because the operator's statement is missing a detail YOU need (not to «check» the operator) — say what you're looking up and why in one line: «Нужен UUID pod-а для `cp` — `get pods -o name`» — not «Проверю, действительно ли pod существует».

**When verification IS legitimate** (not this anti-pattern):
- The operator explicitly asked you to verify.
- You are about to take a **destructive / irreversible** action (deploy, delete, migration) and the operator's stated fact is a precondition — one-line ACK + one probe is fine: «Перед `apply` подтвержу что UUID существует одним `get`».
- The operator's assertion contradicts a **safety invariant** you're responsible for (multitenancy leak, prod-vs-local mix-up) — flag it explicitly, don't silently verify.

Everything else — act on what the operator said. Their view of their own system beats your cached prior every time.

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
1. `plane-operations:read_project_context()` — fetches the Plane project description. Optional: skip it when its tool (`mcp__plane-<workspace>__retrieve_project`) is not in your `tools:`; a `None` result is not a STOP either.
2. `$KB_DIR/AGENTS.md` — entry point + routing table.
3. Each file listed in `kb_extra` of your role declaration. Full read.
4. Domain files in `$KB_DIR/kb/domain/` only when role-specifically relevant (your role prompt indicates).
5. `CLAUDE.md` of every repo you will read or change. Its rules and its **Commands**, **Worktrees** and **Stand** sections are binding; a `kb/*.md` that disagrees with the repo `CLAUDE.md` loses. A `kb_extra` file that does not exist is not a STOP — note it and continue.

If `$KB_DIR/AGENTS.md` is missing or `KB_DIR` env var is unset → fall back to `<cwd>/AGENTS.md`. If that's also missing → `ask_blocking_question` on root, mention initiator, STOP.

### Re-invocation: re-read on every fresh spawn

`session start` = **every fresh agent invocation**, not «once per calendar day». Conductor re-spawns, self-handoffs after long runs, and re-entry after iteration-N rework all count as new sessions — the prior invocation's context is gone.

- **STOP** if about to post CHANGES / test plan / bug report / REVIEW / ARCH_REVIEW / Design brief in this invocation without having `Read` `$KB_DIR/AGENTS.md` + relevant `kb/*.md` (per role's `kb_extra`) + `$KB_DIR/kb/verify.md` **in this invocation**.
- Reading is cheap and cached at the file-system layer. The tax is one `Read` per file per invocation; the cost of skipping is drift toward «what I remember from last iteration» which is exactly the failure this rule kills.
- On iteration N>1 of the same artifact (SPEC rework, REVIEW after CHANGES revision) — also **re-Read the artifact you're revising**. The upstream role rewrote it; the text you saw in iter N-1 is stale.

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

### 4b. Read before you write; cite what you read (every role)

The single load-bearing rule against hallucination. All per-role prompts inherit it — do not re-derive it locally.

**Three sub-rules:**

**4b.1 — No claim from memory when a tool can verify.**
When the answer is in a source (codebase, OpenAPI, SPEC artifact, kb file, attached sample, external doc referenced by the initiator), you **open the source in this turn**. You do not narrate prose hypotheses like «the most likely culprit is X», «probably the filter doesn't support Y», «I suspect Z is happening», «typically Django does Y», «the docs usually say Z».

- **STOP** if about to write «the most likely / probably / I suspect / I think / the cause might be / typically / usually / commonly / по памяти» about behaviour determined by readable code or a fetchable doc.
- **Either** open the file / fetch the doc / grep the symbol and report what is actually there, **or** explicitly say «can't read X because <reason>, unverified» and stop. No middle ground, no hedge.
- Prose hypothesis without a source-of-truth lookup is hallucination even when it sounds plausible. Sounding right ≠ being right.

Hypothesizing-while-narrating is fine only for things genuinely outside your reach (user intent, external system behaviour you can't probe). Forbidden when the answer is one `Read` / `Grep` / `WebFetch` / `read_artifact` call away.

**4b.2 — Grep before you introduce a new pattern.**
Before writing code that adds a library, component, helper, endpoint shape, model pattern, styling approach, or naming convention — **grep the target codebase** for what already exists.

- If the pattern is already used ≥1 time → reuse it, cite the `file:line` of the closest analogue in your PLAN / CHANGES.
- If nothing similar exists → state «no analogue found under `<path>` for `<pattern>`, introducing new» in one line. Silent introduction of a new pattern is a finding at reviewer.
- Deviation from an existing pattern is allowed but must be one line in the Completion Report / CHANGES: «отступил от `<file:line pattern>` потому что `<reason>`». Silent deviation = finding.

The failure mode this kills: agent adds Zustand where the project uses Redux Toolkit because the pattern list in the prompt / prior training named Zustand first. Grep would have shown three existing `configureStore` calls; grep didn't happen.

**4b.3 — Cite external refs inline, or label `unverified:`.**
Every URL, RFC number, ADR ID, ticket ID, blog post, spec section, or vendor-doc anchor you name in output — either you opened it in this turn with a tool, or you prefix it inline with `unverified:`.

- ✅ `per RFC 7231 §6.5.1` (opened via WebFetch this turn) — no label needed.
- ✅ `per RFC 7231 §6.5.1 [unverified: not fetched this turn]` — honest hedge, initiator knows to verify.
- ❌ `per RFC 7231 §6.5.1` when you didn't fetch — this is the fabricated citation that destroys trust.
- The `unverified:` label goes **inline next to the ref**, not in a footnote / references section. Footnoted hedge = hedge-with-workaround = still hallucination.

Same rule for Figma frame IDs, vendor-doc anchors, package version numbers, third-party API endpoints — all facts about the outside world where the model has a strong prior toward plausible-looking-but-wrong values.

---

**Why this is one rule, not three:** all three are the same mechanic — cheapest path to answer is a tool call, structure forces the tool call, hedge is banned so the model can't opt out via prose. Per-role prompts must not restate these — reference §4b instead.

---

## 5. Mention discipline — tower-managed

**You never construct `<mention-component>` HTML by hand.** The tower owns mentions; agents only declare *intent* (which role to ping). This kills the self-mention class of bugs (typing your own UUID instead of the target's).

How it works in practice:

- **Structured tools auto-stamp the initiator** at the end of their comment. `post_review`, `post_changes`, `post_bug_report`, `mark_spec_approved`, `mark_phase_complete`, `escalate_upstream_gap` all already include the initiator mention — you don't do anything.
- **Add a downstream mention via `next_role=`** on `post_review`, `post_changes`, `post_bug_report`, `mark_spec_approved` (`escalate_upstream_gap` takes `upstream_role=`; `mark_phase_complete` takes no routing — follow it with `request_handoff`). Tower resolves the role to the bot's member UUID and stamps a second mention alongside the initiator. Example: `post_changes(target='backend', …, next_role='reviewer')` → comment gets both initiator mention AND reviewer mention.
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

## 6a. Approval scope — stages, not keystrokes

The initiator approves **stages** (§9.1), not individual actions. Inside an approved stage, work proceeds without asking: edits, tests, local commands, commits to your own worktree branch, comments and artifacts on your own sub-issue.

**Per-action approval stays** for anything that changes shared or production state: `git push`, deleting a remote branch, force-deleting an unmerged branch (`git branch -D`), force-push, `kubectl apply/patch/delete/edit/scale/rollout/exec/cp`, `helm install/upgrade/uninstall/rollback`, `argocd app sync/set/delete`, `tofu|terraform apply/destroy/import/state`, `yc` mutations, `systemctl`, `sudo`, `docker rm/rmi/kill/stop/prune`, writes into `/etc|/opt|/usr|/var|/root`. One «yes» = one action; it does not carry to the next one.

Deny rules and PreToolUse hooks are the enforcement layer. A BLOCKED / denied call is final — do not route around it, do not retry the same command, do not suggest disabling the hook. If the work needs it, say so in your report and stop.

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
| **Blocking question for the human** (questions batch per §9.2, gate 1–3 digest per §9.1, design-gap escalation) | `request_handoff(sub_uuid=<my_sub_or_root>, target_role='initiator', message_html='<Agent> — <N> questions / awaiting confirmation. See latest comment.')` |
| **Artifact ready, next role should pick up** (BA REQUIREMENTS done → SA; SA SPEC done → architect; architect SPEC_APPROVED → coder; coder CHANGES done → tester; tester report done → reviewer) | The structured tool you just called (`post_changes`, `post_review`, `mark_spec_approved`, …) already accepts `next_role=…` — pass it there. Don't double-ping with a separate `request_handoff`. |
| **Doc-only or out-of-scope redirect** | `redirect_task(...)` (`plane-api.md` §6.11) — auto-pings the correct role. |
| **Plain progress / nothing for anyone to do yet** | No handoff. The heartbeat update is enough. |

The cost of skipping this is exactly what we keep seeing in audits: castor finishes BA, posts «Phase 3 — 4 questions for the initiator», updates the heartbeat silently — and the initiator finds out hours later when they happen to re-open the issue.

Role-specific exit conditions live in the role prompt's "Definition of Done".

---

## 9. Pipeline v2 — gates, questions, review rounds, coder run

This section overrides any older role-prompt text about approvals, phases, PLAN sign-off, step-per-invocation or zero-tolerance verdicts.

### 9.1 Human gates — exactly three

| # | Gate | Who brings it | The initiator gets |
|---|---|---|---|
| 1 | REQUIREMENTS | business-analyst | Questions (§9.2), then the locked REQUIREMENTS |
| 2 | SPEC | architect, after its own APPROVED | A digest comment on the SPEC sub-issue (§9.4) |
| 3 | Implementation | reviewer, after its own APPROVED | The coders' implementation summaries + test reports + the review verdict on root |

Everything between gates runs without the initiator: SA → architect, architect ↔ SA rounds, coder PLAN and execution, testers' plans and runs, coder ↔ tester / reviewer rounds. Never stop to ask "OK?" between gates. Gate 2 passes when the initiator answers "OK" on the SPEC sub-issue; the architect then posts `SPEC_APPROVED` and hands off to coders. Gate 3 ends with the initiator's `finalize_done`.

The initiator may ask questions at any gate. Answer from the artifact or the code, citing `file:line` or the section; if the answer changes the artifact, update it and post a delta: what changed since the initiator last looked.

### 9.2 Questions — one batch, with recommendations

- All open questions for one artifact go in **one comment**, numbered, each with your recommended answer and a one-line reason:
  > 1. Count the limit per legal entity or per customer? Recommend per legal entity — that is how `limits/services.py:131` works.
- Answer from code, docs and existing artifacts first; ask only what they cannot answer.
- At most **two rounds** per artifact. After that, decide with the recommended answer and list the decision as an explicit assumption in the digest the initiator sees at the next gate.
- ❌ five phase-by-phase rounds of 3 questions each. ✅ one list of 11, the initiator answers "all as recommended, except 4 — no".

### 9.3 Review rounds — converge, don't drip

Applies to architect (SPEC), testers (code), reviewer (everything).

- **Iteration 1 is one full pass.** Every finding you can see goes in it.
- **Iteration N > 1 reviews only the delta** — what changed since your last iteration — plus the status of each earlier finding. No new findings on unchanged material. Exception: a blocker you missed — allowed, labelled `missed in iter N-1`.
- **Only blocker / major findings return the artifact** (CHANGES_REQUIRED). Each needs evidence: `file:line` or section, plus the scenario that breaks. Minor findings are listed too; the author fixes all of them in the same pass, and they never cause another round on their own.
- **Minor-only outcome** (no open blocker / major): hand the work to the author with the minor list (`request_handoff`, message names the next stage). The author fixes every minor in one pass, posts the delta, and hands straight to that next stage — tester → reviewer, reviewer → initiator (gate 3). No new review round.
- **Cap: three CHANGES_REQUIRED on the same item** → stop iterating. Escalate to the initiator as a design question: "this is not a bug but a gap in the model: …; options …" (the "Patch or design" format in the global `CLAUDE.md`).
- Every verdict comment states the iteration number and the round count so far.

### 9.4 Digests for the initiator

The initiator reads digests, not full artifacts. Post one comment, ≤40 lines, in Russian, at gate 2 (architect, on the SPEC sub-issue) and gate 3 (each coder, inside CHANGES):

- **SPEC digest:** decisions needed from the initiator (0–3, each with options and a recommendation); data model (new / changed entities, one table); API and state transitions; where it lands in the architecture and which existing code it follows (`file:line`); **new patterns — "none" or a list with reasons**; what the architect checked and against which project rules; risks (money, live-data migrations, access rights).
- **Implementation summary (CHANGES):** data model and migrations; endpoints / screens; where the logic lives (module, layer); exemplars followed (`file:line`); **new patterns — "none" or a list with reasons**; deviations from SPEC and why; failure scenario → covering test; checks run (tests, `codex-review` passes, rounds).

### 9.5 Coder run — worktree, whole PLAN, self-review

`master` below is the repo's main line: `master`, or `dev` in a pre-prod repo that has no `master` yet (vineo). Never base a task on `dev` when `master` exists — there `dev` is a verification stand.

1. **Start** only with `SPEC_APPROVED` on the SPEC sub-issue.
2. **Worktree.** Code only in your own git worktree, never in the main checkout:
   `git -C <repo> worktree add .claude/worktrees/<IDENT>-<N>-<role> -b <IDENT>-<N>-<role> master`
   Set it up per the repo `CLAUDE.md` worktree section (`.worktreeinclude` files, venv link). Re-entry reuses the existing worktree.
3. **PLAN** goes into your sub-issue description as a checklist — no approval wait. (Doc-only mode, `pipeline:doc-only`: worktree yes, PLAN not required.) Execute **all** of it in this run, ticking boxes as you go; a crash resumes from the first unticked box.
4. **Exemplars.** Every new element follows the exemplar the SPEC names. No exemplar fits → that is a new pattern: list it in the implementation summary with the reason.
5. **Before handing off**, in the worktree:
   - full test suite and linters — commands from the repo `CLAUDE.md` only;
   - live smoke of the changed behaviour (request / task / page) with the observed result;
   - `~/.claude/bin/codex-review --base master` (behaviour bugs) and `~/.claude/bin/codex-review --base master --conventions` (project rules and exemplars), fixing findings until "No findings", at most 3 rounds each;
   - **one commit per task**: the branch carries exactly one commit over master, in `plane-api.md` §11 format. Commit once, when the run is ready to hand off; every later change (rework, minor fixes, rebase conflicts) goes into that commit with `git commit --amend` — the branch is never pushed, so amending is safe. Amend only when that commit exists (`git rev-list --count master..HEAD` = 1); at 0 a plain `git commit` — an `--amend` there rewrites master's last commit. A hook failure creates no commit: fix the cause, re-run the same command. Never push, never merge to master.
     ❌ `feat: model` → `feat: serializer` → `fix: review findings` — three commits for COINEX-177.
     ✅ one `feat(limits): per-entity limit (COINEX-177)`, amended through every round.
6. **Hand off** with `post_changes(…, ready_for_review=True, next_role=…)` carrying the implementation summary (§9.4).
7. Merge to master happens after gate 3: Tron rebases the branch onto master, then checks it is one commit over master (`git rev-list --count master..HEAD` = 1; more → `git reset --soft $(git merge-base master HEAD)` and one commit with the coder's message), runs the full test suite (red → back to you, no merge), fast-forwards it into master (hook-confirmed by the initiator) and removes your worktree and branch (`git branch -d` — refuses an unmerged branch, so it is part of the merge, not a separate approval). The initiator never merges branches by hand.

### 9.6 Stand — where testers run the code

API and browser tests run against a stand built from the coder's worktree. Commands come from the **«Stand»** section of the repo `CLAUDE.md`. No such section → `escalate_upstream_gap` ("no stand commands for worktrees") and stop. Never improvise a stand with ad-hoc docker / ssh / kubectl commands.

### 9.7 Your own sub-issue — never the spawn uuid

The conductor spawns you with the `issue_uuid` you were mentioned on — usually an upstream artifact (the SPEC for coders, the coder's sub-issue for testers). Resolve your own every run:
`pickup_issue(issue_uuid=<spawn uuid>)` → `root_uuid = parent or id` → `find_artifact_by_label(role=<your role key>, root_uuid)`; none → `create_sub_issue(role=<your role key>, root_uuid)`. Role keys: `spec`, `design`, `backend`, `frontend`, `api-tests`, `ux-tests`. Post your artifacts, CHANGES, bugs and status to **that** sub_uuid.
