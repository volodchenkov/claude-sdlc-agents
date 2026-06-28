---
name: istqb-test-design
description: Use this skill when working as a tester (the api-tester for API testing, the ui-tester for UX/E2E testing) — designing test cases per ISTQB Foundation framework, choosing the right test design technique (Equivalence Partitioning, Boundary Value Analysis, Decision Table, State Transition, Use Case Testing), classifying test levels and types, structuring bug reports. Read before composing a test plan or executing test cases.
---

# ISTQB Test Design — disciplined testing framework

This skill encodes ISTQB Foundation Level (CTFL syllabus v4.0) — the de-facto standard for software testing knowledge. We use a **focused subset** suitable for a small-team SDLC pipeline.

Reference: ISTQB CTFL syllabus, ISO 29119 (test process).

---

## SPEC-Rev citation — every TC traces to a SPEC version

Every test case in the plan MUST cite the SPEC section and Revision it tests against. Format: `Tests: SPEC §X.Y (Rev N) — FR-Z` in the TC header or as a dedicated row.

**Why**: SPEC drifts between iterations (Rev 4 → Rev 5 changes API contract); without an explicit citation, the test plan silently asserts old behaviour and a tester «re-runs» green tests against new code that no longer matches. This is how COIN-126 ended up with `PeriodicTask created` assertions surviving after backend dropped `periodic_task` entirely.

### Regen-on-Rev-bump

When SPEC Rev is bumped (you see a new `Rev N+1` in SPEC sub-issue description or a SA `SPEC-delta confirmation` comment):

1. Diff what changed in SPEC §X.Y between Rev N and Rev N+1
2. For every TC citing the changed §: mark as **stale** — re-derive expected results from the new Rev, do NOT just re-run with old assertions
3. New TCs may be needed (changed § may have new error paths / state transitions). Apply the right technique (EP / BVA / Decision Table / State Transition) afresh
4. Update each TC header: `Tests: SPEC §X.Y (Rev N+1)` and adjust assertions to match
5. The test-plan iteration counter bumps when SPEC Rev bumps

**Never re-run TCs whose SPEC cite is older than the latest SPEC Rev without redoing the «re-derive expected results» step.** A green stale TC is worse than a red one — it gives false confidence the change didn't break anything when in fact the test is just measuring the wrong thing.

---

## Test levels — where the test sits in the SDLC

| Level | Who | What | Out of scope here |
|---|---|---|---|
| **Unit (component)** | Coders themselves | Individual functions / methods | the api-tester / the ui-tester don't write unit tests |
| **Integration** | Coders + the api-tester | Multiple components / API + DB | the api-tester for API integration |
| **System** | the api-tester + the ui-tester | End-to-end through real entry points | the api-tester for API system, the ui-tester for UI E2E |
| **Acceptance** | the initiator | Does it match REQUIREMENTS Acceptance Criteria? | the initiator approves; testers gather evidence |

the api-tester focuses on **System level via REST API**. the ui-tester focuses on **System / Acceptance level via UI**.

---

## Test types — what aspect we're testing

ISTQB classifies test types into 4:

1. **Functional** — does it do what it should? (FR coverage)
2. **Non-functional** — how well does it do it? (performance, security, usability, accessibility)
3. **Structural** (white-box) — code paths, branches. Out of scope for the api-tester / the ui-tester (coders handle in their pytest suites).
4. **Change-related** — regression after changes; smoke after deploy.

**the api-tester covers:** Functional + Non-functional (API perf, basic security like auth/permissions) + Change-related (regression).
**the ui-tester covers:** Functional (UI flows) + Non-functional (usability, accessibility) + Change-related.

---

## Test design techniques — pick the right one per test case

This is the **core discipline** of ISTQB. Every TC must declare which technique it uses.

### Black-box techniques (no knowledge of internal code)

#### 1. Equivalence Partitioning (EP)
Group inputs into classes where the system should behave the same. Test ONE value per class.

Example for `?status=...` filter:
- Valid statuses: `pending`, `confirmed`, `shipped`, `delivered`, `cancelled` → one class (test `confirmed`)
- Invalid status string → one class (test `xyz`)
- Empty / missing → one class (test no param)
- Multiple comma-separated → one class (test `pending,shipped`)

5 classes → 4 TCs (one per class) — not 5+ (don't test every valid status).

#### 2. Boundary Value Analysis (BVA)
For ordered inputs, test **boundaries** — they're where bugs hide.

For an integer field 1–100:
- Test 0 (just below min — invalid)
- Test 1 (min — valid)
- Test 2 (just above min — valid)
- Test 99 (just below max — valid)
- Test 100 (max — valid)
- Test 101 (just above max — invalid)

For string lengths, dates, money amounts — same logic.

#### 3. Decision Table
For combinations of conditions producing different outcomes. Build a table of rules.

Example: order discount logic
| Condition | Rule 1 | Rule 2 | Rule 3 | Rule 4 |
|---|---|---|---|---|
| Customer is VIP | yes | yes | no | no |
| Order > 5000 RUB | yes | no | yes | no |
| **→ Discount applied** | 15% | 10% | 5% | 0 |

→ 4 TCs, one per rule. Skip combinations that aren't reachable in real flows.

#### 4. State Transition Testing
For systems with states (orders, subscriptions, accounts). Test:
- Each valid transition (1 TC per arrow in the state diagram)
- Each invalid transition (e.g. trying to ship a `cancelled` order)
- Each state's terminal/non-terminal property

the system-analyst's Phase 4 state diagram in SPEC is the source. Generate TCs from it.

#### 5. Use Case Testing
End-to-end happy path of a user scenario. Each Acceptance Criterion (Given/When/Then in REQUIREMENTS §6) gives a use case TC.

Example: "Customer self-serves order tracking" → TC walking from `/account/orders` → click order → see tracking number → click → CDEK page opens.

the api-tester / the ui-tester build use case TCs from REQUIREMENTS Acceptance + SPEC Frontend behaviour.

### Experience-based techniques (less formal, complement black-box)

#### 6. Error Guessing
Based on intuition / past bugs in similar code. Examples:
- What if the user double-clicks "Place order"?
- What if the network fails mid-way?
- What if data has emoji / very long Cyrillic strings?

Useful for edge cases not covered by formal techniques.

#### 7. Exploratory Testing
Time-boxed, charter-driven open exploration. Less applicable for automated agents; reserved for the initiator's manual final validation.

---

## Coverage — what counts as "done"

For each TC declare its **purpose**:
- Validates which FR / NFR from REQUIREMENTS
- Validates which Acceptance Criterion (Given/When/Then)
- What technique used

End-of-test-plan **Coverage matrix**:

| FR / NFR | TC IDs covering it |
|---|---|
| FR-1 customer sees tracking | TC-1, TC-2, TC-3 |
| FR-2 link opens CDEK | TC-4 |
| NFR-1 list endpoint < 300ms | TC-P1 (perf) |

Every FR / NFR / Acceptance Criterion from REQUIREMENTS must have at least one TC. Gaps = test plan incomplete.

---

## Bug reports — structured, actionable

Every bug = one comment in the test sub-issue. Follow ISTQB defect template.

### Required fields
- **Title** (1 line) — bug name + affected component
- **Severity** — blocker / major / minor / trivial
- **Priority** — high / medium / low (the initiator's call, not tester's)
- **Reproducible** — always / intermittent / once
- **Environment** — browser / Python version / DB state / Plane URL
- **Steps to reproduce** — numbered, exhaustive
- **Actual result** — what happens
- **Expected result** — what should happen (cite FR / Acceptance Criterion)
- **Affected sub-issue** — link to Backend / Frontend sub-issue
- **Attachments** — screenshots (UX bugs, via the ui-tester's S3 + create_work_item_link)

### Severity vs priority
- **Severity** = how bad is the bug technically (impact, scope)
- **Priority** = how soon to fix (business decision)
- Tester sets severity. Priority is the initiator's call.

### Bad bug report
> "Tracking doesn't work"

### Good bug report
> Title: Order tracking link returns 500 when tracking_number contains special chars
> Severity: major
> Priority: TBD by the initiator
> Reproducible: always
> Environment: <storefront-app> Vue 3, Chrome 120, Plane <PROJECT_IDENTIFIER>-<N>
> Steps:
>   1. Login as customer (test acc 1)
>   2. Open /account/orders/{id} where order has tracking_number='ABC/123'
>   3. Click tracking link
> Actual: 500 Internal Server Error, browser console shows "URLError: invalid char"
> Expected: per FR-2, opens https://cdek.ru/track/ABC%2F123 in new tab
> Affected: Backend: <root_name> (<PROJECT_IDENTIFIER>-<N>) (slash not URL-encoded in serializer.tracking_url)
> Attachments: https://storage.yandexcloud.net/.../bug-tracking-500.png

---

## Test report — final summary

After all TCs executed, post final summary comment in test sub-issue:

```markdown
# Test report — {API | UX} Testing for <PROJECT_IDENTIFIER>-<N>

## Executed
- Total TCs: N
- Passed: N
- Failed: N (see bug comments above)
- Blocked (preconditions not met): N

## Coverage matrix verification
- FR-1: covered by TC-1, TC-2 — passed
- FR-2: covered by TC-3 — failed (bug above)
- NFR-1: covered by TC-P1 — passed (p95 230ms < target 300ms)

## Verdict
- READY FOR REVIEW: yes / no
- If no — what blocks release: {list of blocker bugs}

<mention initiator>
```

---

## Anti-patterns

- Testing every value (instead of one per equivalence class)
- Skipping boundary values (off-by-one bugs hide there)
- Vague "doesn't work" bugs without steps
- Mixing severity and priority
- No coverage matrix (which FR / NFR each TC validates)
- Re-running passed tests pointlessly during regression — focus on changed areas + smoke

---

## When in doubt

- Read REQUIREMENTS §6 Acceptance Criteria — these directly map to use case TCs
- Read SPEC §3 API Contract (the api-tester) or §4 Frontend Behaviour (the ui-tester) — endpoints / flows to test
- Read SPEC §7 Traceability matrix — confirms what's in scope
- Apply EP + BVA first (cover most ground with fewest TCs); add Decision Table / State Transition / Error Guessing for edge cases
