---
name: architecture-review-framework
description: Use this skill when working as the architect — reviewing a SPEC produced by the system-analyst, evaluating ADRs, checking cross-trace to REQUIREMENTS, producing ARCH_REVIEW with verdict (APPROVED / CHANGES_REQUIRED) and the SPEC_APPROVED marker. Encodes a 7-area review checklist (Area 0 implementation-readiness + 6 technical areas), SOLID and DDD lenses, and ADR governance.
---

# Architecture Review Framework

This skill defines how the architect reviews SPECs and CHANGES. Goal: produce a **verifiable, professional ARCH_REVIEW** that catches problems early and leaves a paper trail. Inspired by:
- **C4 Model** review at Context and Container levels
- **SOLID principles** (Robert C. Martin) — for code review
- **DDD** bounded context discipline — service boundary checks
- **ADR pattern** (Michael Nygard) — for capturing and approving architectural decisions
- **Code review best practices** (Google eng-practices, Smartbear)

---

## Two review modes

### Mode A: SPEC review (most common)
Triggered after the system-analyst posts SPEC. The architect reads SPEC + REQUIREMENTS, evaluates against 7 review areas (Area 0 implementation-readiness + 6 technical areas), evaluates each ADR, validates traceability matrix.
**Output:** ARCH_REVIEW comment in SPEC sub-issue + SPEC_APPROVED marker (when all green).

### Mode B: CHANGES review (less common — assist the reviewer)
After coders post CHANGES. The architect cross-checks that implementation respects the architectural decisions in SPEC.
**Output:** ARCH_REVIEW iteration comment in coder's sub-issue. Note: the reviewer is the canonical reviewer for CHANGES; the architect intervenes only when architectural drift is suspected.

This skill focuses on **Mode A**; Mode B uses the same 7-area lens.

---

## The 7 Review Areas

Every ARCH_REVIEW iteration covers all 7 — even if some are N/A for the given SPEC, **explicitly state why N/A**. Silent skipping is the most common architecture review failure mode.

### Area 0: Implementation-readiness (ATAM-style concrete scenarios)

A formally correct SPEC that leaves implementation to guesswork is **not APPROVED**. For every affected backend service and frontend, verify:

- Every model field has explicit type, constraints, and `on_delete` semantics (coder doesn't extrapolate from "similar models").
- Every endpoint has request shape, response shape, and ALL error codes (not just success).
- Every user-facing screen has explicit loading / empty / error / partial / success states.
- Every business rule (§4 BRs) is a testable invariant with explicit inputs and expected outputs — not an aspiration ("handle X gracefully", "good UX").

If any item fails — severity **major**, verdict **CHANGES_REQUIRED**, escalate the specific gaps to system-analyst (and to initiator if the gap is intent-flavored — "what should this screen do when X is empty?"). Do NOT approve a SPEC that effectively says "implementation details TBD by coder".

❌ SPEC §4 BR-3: "system must handle blockchain errors gracefully" → approve → coder writes `try/except: pass` → silent prod failures.
✅ Verdict: CHANGES_REQUIRED. BR-3 must specify (a) error classes (network / RPC / signature / consensus); (b) per-class retry strategy (immediate / exponential / abandon); (c) user-visible outcome (block / partial / queue for ops review). Escalate intent gaps to initiator.

### Area 1: Service boundaries (DDD bounded contexts + import contracts)

The canonical bounded contexts and import contracts are declared in `$KB_DIR/kb/architecture.md`.

**What to check:**
- Does the SPEC respect the project's bounded contexts?
- Are there cross-context imports that violate the project's import contracts (per `$KB_DIR/kb/architecture.md`)?
- Does logic live in the right service / bounded context?
- New service / bounded context proposed? — high bar; usually rejected unless necessary

**Failure modes:**
- Domain logic creeping into the wrong service because "the model is closer to that service" — check the domain ownership.
- "Helper" placed in the shared layer that knows about a specific service — leaks domain into shared layer.

### Area 2: Multitenancy

If `$KB_DIR/kb/multitenancy.md` declares the project is multi-tenant:

**What to check:**
- Every new model has the tenant FK (e.g. `<tenant_key> = ForeignKey('<tenant-app>.<TenantModel>', on_delete=PROTECT)`) — confirmed in §2 Data Model
- Every new endpoint queryset filters by the tenant key — confirmed in §3 API and §5 Security
- No "global" data without explicit business justification (e.g. system-wide settings)
- Cross-tenant access points (admin tools, audit) clearly identified and access-controlled

**Failure modes:**
- New model without the tenant FK — silent cross-tenant data leak waiting to happen.
- Endpoint that accepts the tenant ID as a parameter — privilege escalation vector.

If multitenancy is N/A, mark this area N/A with reason and skip.

### Area 3: Performance

**What to check:**
- N+1 risks in proposed querysets — does SPEC mention `select_related` / `prefetch_related` patterns?
- Indexes for hot query paths — composite indexes for multi-column filters
- Caching strategy explicit (TTL, invalidation triggers)
- Heavy operations moved to the queue (no synchronous calls to slow external APIs from the request path)
- Pagination on list endpoints
- Realistic QPS estimates? Can the design handle 10x?

**Failure modes:**
- "We'll add an index later" — accept now or defer with explicit ticket.
- Synchronous external API call in the request path — must be a background task with retry policy.

### Area 4: Transactions and concurrency

**What to check:**
- Multi-step writes wrapped in transactions
- Race conditions in state transitions — row-level locking where appropriate
- Idempotency on POST endpoints that change state (Idempotency-Key header)
- Optimistic locking (version field) for concurrent updates — if relevant

**Failure modes:**
- Two operations that "should always happen together" not in a transaction — partial state on crash.
- Cancel endpoint with no idempotency — double-cancel produces error or worse.

### Area 5: Integration security

**What to check:**
- External integrations: HMAC verification on incoming webhooks
- Outgoing: timeout, retry policy, exponential backoff
- Secrets via env vars, never in code or logs
- Rate limiting / circuit breaker for unreliable external services
- Logging discipline: never log PII, never log secrets, never log full request bodies of payment endpoints

**Failure modes:**
- Webhook endpoint without HMAC — anyone can post to it.
- API key / token in error messages — leaks via support / logs.

### Area 6: Migrations and Transition Requirements

**What to check (cross-ref REQUIREMENTS Transition Requirements + `$KB_DIR/kb/migrate.md`):**
- Backward-compatible migration: nullable / default / multi-step
- Destructive operations multi-step: deploy code that doesn't read field → backfill → remove field → final deploy
- Large-table migrations: concurrent index creation, batched for data
- Feature flags for gradual rollout
- Deprecation plan for old endpoints (deprecation header, sunset date)
- Data migration tested with realistic volume

**Failure modes:**
- Single-deploy field removal — instant breakage during rolling deploy (old workers still try to read).
- Massive-row migration without concurrent index creation — table locks, downtime.
- Feature shipped without flag — can't kill-switch in incident.

---

## ADR governance — what the architect does with each ADR

The system-analyst proposes ADRs in SPEC §6 with status `Proposed`. The architect either accepts, modifies, or rejects.

| Action | When | Outcome in ARCH_REVIEW |
|---|---|---|
| **Accept** | The decision is sound and the alternatives correctly analyzed | "ADR-N: Accepted. Status changes to Accepted on SPEC_APPROVED." |
| **Modify** | Decision direction is right but execution needs change | "ADR-N: Modify decision text to {new wording}. Re-propose." → CHANGES_REQUIRED |
| **Reject + counter** | Wrong choice; pick a different alternative or a new option | "ADR-N: Reject. Take Alternative 2 / propose new ADR with {context}." → CHANGES_REQUIRED |

If SPEC has architectural choices **not** captured as ADRs but should be — flag in review: "Section §X contains a non-trivial decision; lift into ADR-{new}". → CHANGES_REQUIRED.

---

## Traceability check (Phase 6 cross-validation)

The system-analyst's §7 Traceability matrix maps every REQUIREMENTS FR/NFR to a SPEC section. The architect validates:

- Every FR has at least one SPEC entry → no orphan requirements
- Every NFR has at least one SPEC entry → quality attributes addressed
- Every Transition Requirement has corresponding §5 Migration plan entry
- Every SPEC §-section traces to a FR/NFR or is in "Assumptions" — no invented scope

Failures here are **blockers** — SPEC cannot be APPROVED with traceability gaps.

---

## SOLID lens — for code-level review (Mode B)

In Mode B (code-level review of CHANGES), apply SOLID alongside the 6 architectural areas. Full breakdown of SRP / OCP / LSP / ISP / DIP with concrete signals lives in `code-review-discipline` SKILL §"SOLID — code quality lens" — read it once and keep the same lens here. The architectural angle: SRP at the **module / service** boundary (not method), OCP via new types, LSP at the **adapter** layer (port/adapter substitutability).

In Django / web-framework context this often means: thin views, fat models, services layer for cross-cutting flows, testable without DB hits.

---

## Verdict semantics

ARCH_REVIEW concludes with one verdict:

| Verdict | When |
|---|---|
| **APPROVED** | All 7 areas green (including Area 0 implementation-readiness), all ADRs accepted (or trivially modified), traceability complete, no blockers |
| **CHANGES_REQUIRED** | Any blocker finding, any rejected ADR, any traceability gap |
| **BLOCKED** | Cannot complete review — missing input (SPEC incomplete, REQUIREMENTS too vague, system-analyst hasn't addressed prior CHANGES_REQUIRED) |

After APPROVED → post separate `SPEC_APPROVED` marker comment (see `artifact-templates` skill ARCH_REVIEW template).

---

## Severity classification for findings

The architect uses the same blocker / major / minor scale as the final reviewer. Definitions + verdict logic live in `code-review-discipline` SKILL §"Severity classification" — read it once. Architecture-specific examples per severity:

- **blocker** — missing tenant filter (multitenancy leak), no transition plan for breaking change, cross-context import violating import contracts
- **major** — missing index for a hot query, no idempotency on payment endpoint, ADR alternatives not analyzed
- **minor** — naming inconsistency, missing optional field documentation, "could also do X" optimisations

---

## When in doubt

- Read SPEC fully before writing review — don't drive-by-comment first sections
- Read REQUIREMENTS to validate trace
- If unsure about a domain decision (when business-analyst's interview wasn't deep enough) — escalate to the initiator, don't override the system-analyst
- Use `system-design-techniques` skill for cross-reference of conventions the system-analyst should be following
