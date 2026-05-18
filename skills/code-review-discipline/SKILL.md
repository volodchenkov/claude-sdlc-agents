---
name: code-review-discipline
description: Use this skill when working as the final Reviewer (the reviewer role) — comprehensive cross-cutting review before closing a Plane issue. Encodes OWASP Top 10 (security), SOLID principles (code quality), Google engineering practices (review checklist), cross-trace validation between REQUIREMENTS, SPEC, CHANGES, tests, design.
---

# Code Review Discipline

This skill defines how the reviewer produces a final REVIEW that catches problems missed by upstream agents and validates end-to-end coherence. Inspired by:
- **OWASP Top 10** (2021 edition) — the de-facto security review baseline
- **SOLID principles** (Robert C. Martin) — code quality / maintainability lens
- **Google Engineering Practices** — code review patterns (small CLs, what to look for, fast turnaround)
- **CWE / SANS Top 25** — common weakness enumeration
- **Smartbear / Google research** — review effectiveness studies

---

## the reviewer's job (vs the architect / the api-tester / the ui-tester)

| Role | Reviews | When |
|---|---|---|
| the architect (Architect) | SPEC | After the system-analyst posts SPEC, before coders start |
| the api-tester | API behaviour | After Backend CHANGES |
| the ui-tester | UI behaviour, a11y | After Frontend CHANGES |
| the designer | UX intent match | After Frontend CHANGES (Mode B) |
| **the reviewer** | **End-to-end coherence: REQUIREMENTS → SPEC → CHANGES → tests → design** | After all of the above, before the initiator's final closure |

the reviewer catches drift across boundaries:
- Did the implementation match the SPEC?
- Are all FRs from REQUIREMENTS actually implemented?
- Did testing cover the full SPEC, or skip parts?
- Are there security / quality issues in code that the architect didn't see at SPEC level?

---

## Cross-trace validation — the reviewer's #1 job

Walk the chain end-to-end:

```
REQUIREMENTS (root description)
    ↓
SPEC §7 Traceability matrix (FR → SPEC §)
    ↓
CHANGES (Backend, Frontend) — what was actually shipped
    ↓
Test plans (API, UX) — what was actually tested
    ↓
Design brief (the designer's intent)
```

For every FR / NFR / Acceptance Criterion in REQUIREMENTS:
- ✓ Specified in SPEC?
- ✓ Implemented in CHANGES (Backend + Frontend as applicable)?
- ✓ Tested by the api-tester (if API) and / or the ui-tester (if UI)?
- ✓ Design intent honored (the designer UX review APPROVED)?

Any ✗ at any link in the chain = finding. Severity depends on the gap.

---

## OWASP Top 10 (2021) — security review checklist

Run through these 10 for every CHANGES that touches handling of data:

### A01:2021 — Broken Access Control
- Multitenancy: every queryset filters by `company=request.user.company`
- Permission classes on every view (no anonymous access where forbidden)
- No `company_id` accepted as parameter
- IDOR (Insecure Direct Object Reference): UUIDs not sequential IDs in user-facing URLs
- Vertical / horizontal privilege escalation paths checked

### A02:2021 — Cryptographic Failures
- Secrets in env, never in code / logs / git history
- TLS for all transports
- Password hashing via Django's PBKDF2 / Argon2 — never raw
- Sensitive PII not logged
- Tokens / API keys rotated on suspicion

### A03:2021 — Injection
- ORM used; raw SQL only via parameterized queries
- HTML escaping by default in templates / Vue / React (don't bypass without reason)
- Command injection: avoid `os.system()` / `subprocess(shell=True)` with user input
- LDAP / NoSQL / XPath injection if applicable to the change

### A04:2021 — Insecure Design
- Threat model considered for new flows? (E.g. password reset must rate-limit, must invalidate token after use)
- Defense in depth — not relying on one layer

### A05:2021 — Security Misconfiguration
- Production defaults secure (DEBUG=False, ALLOWED_HOSTS strict)
- No verbose error pages exposed
- Unused features / endpoints disabled

### A06:2021 — Vulnerable and Outdated Components
- Dependency updates: pip / npm / yarn — no known CVEs for added packages
- Pin versions, don't use unbounded ranges in production

### A07:2021 — Identification and Authentication Failures
- Session management: secure cookies, expiry
- 2FA / MFA where applicable
- Brute-force protection (rate limit on login / password reset)

### A08:2021 — Software and Data Integrity Failures
- HMAC verification on incoming webhooks (CDEK, payment gateways)
- CI / CD: signed releases, immutable artifacts
- Untrusted deserialization avoided (no `pickle.loads()` on user input)

### A09:2021 — Security Logging and Monitoring Failures
- Audit log for sensitive actions (admin role change, refund, etc.)
- Logs don't contain secrets / PII
- Alerts on suspicious patterns

### A10:2021 — Server-Side Request Forgery
- Outgoing requests to URLs derived from user input — validated against allowlist
- Don't expose metadata endpoints (cloud) accessible from app

For full reference: https://owasp.org/Top10/

---

## SOLID — code quality lens

### Single Responsibility Principle (SRP)
- Class / function / module does one thing
- 200-line model with 50 methods → split (extract service, query manager, mixin)
- 300-line view that does parsing + validation + persistence + email sending → split

### Open / Closed Principle
- Extension via new types, not modification of existing
- New status added by extending choices, not by `if status == 'new_status'` everywhere
- New payment provider = new class implementing the interface, not a series of `if provider_name == 'stripe' / 'tinkoff' / ...`

### Liskov Substitution
- Subclasses honor parent contracts (don't strengthen preconditions / weaken postconditions)
- If a base view returns 404 on missing object, the subclass should too — not raise InternalServerError

### Interface Segregation
- Don't force clients to depend on methods they don't use
- Big "Manager" classes split into specific protocols (OrderQueryRepository / OrderCommandRepository)

### Dependency Inversion
- Depend on abstractions, not concretions
- Service depends on `EmailSender` protocol, not `SMTPSender` directly
- Especially important for testability — mocks at the interface boundary

In Django context, SOLID often means: thin views, fat models, services layer for cross-cutting flows, manager / queryset for query logic, signals only for true cross-context concerns (audit log, cache invalidation).

---

## Code review patterns (from Google Engineering Practices)

### What to look for
- **Design** — is the change well-architected? Should it have been a different approach?
- **Functionality** — does the change do what it should? UX implications?
- **Complexity** — could it be simpler? Over-engineered?
- **Tests** — appropriate, well-written, will catch regressions?
- **Naming** — is everything named for clarity?
- **Comments** — clear and useful, not redundant?
- **Style** — matches existing code style?
- **Documentation** — updated as appropriate?
- **Every line** — actually look at every line; don't drive-by.

### Review effort budget
For this pipeline: the reviewer reviews work that's already passed the architect's ARCH_REVIEW (architecture) and the api-tester's / the ui-tester's testing (behaviour). the reviewer's focus = security + quality + traceability, not surface bugs (testers caught those).

### When to escalate
If finding is architectural drift from APPROVED SPEC → escalate to the architect (he may want to revise SPEC or accept the deviation).
If finding is UX misalignment → escalate to the designer.
If finding is a missed test case → escalate to the api-tester / the ui-tester (regression iteration).
If finding is security / quality / coherence → the reviewer's core domain, file directly.

---

## Severity classification

Severity describes *what kind* of finding it is — not whether it blocks the verdict. Use it to help the implementer prioritise the rework order, not to decide skip-vs-fix.

- **blocker** — release-stopping at any reasonable interpretation. Examples: security vulnerability (any A01–A10), missing FR coverage, untested critical path, broken multitenancy
- **major** — degrades the feature meaningfully. Examples: missing audit log on sensitive action, SOLID violation that will hurt maintenance, test coverage gap on edge case
- **minor** — small but real. Examples: naming inconsistency, comment polish, minor refactor opportunity, low-impact a11y violation, drift from APPROVED SPEC on an unimportant detail

## Verdict logic (zero-tolerance)

**Any finding of any severity → CHANGES_REQUIRED.** APPROVED requires the finding list to be empty.

- ❌ «Minor — leave as follow-up ticket» — forbidden. Either it's worth fixing (file as finding → CHANGES_REQUIRED) or it isn't (don't write it down at all).
- ❌ «Non-blocking, recommend separate issue» — forbidden. Same logic.
- ❌ «Major punted by discretion» — forbidden. The reviewer / architect doesn't have skip discretion.
- ✅ APPROVED is the **only** terminal verdict for «code is clean»; any concern that warrants writing down is, by definition, worth fixing in this iteration.

**Why**: every «non-blocking follow-up» the reviewer leaves behind becomes technical debt that no one comes back to. The initiator's stated rule (2026-05-13): «закрываем все замечания. Фиксите все». Don't pre-judge what's worth the implementer's time — surface everything, let the implementer fix everything, then APPROVED.

If a finding genuinely doesn't fit this iteration (e.g. requires SPEC change), escalate it as `BLOCKED — upstream gap` and STOP — not as a punted minor.

---

## What NOT to review

Don't re-do what other agents already did:
- Don't re-architect (the architect did)
- Don't deeply test behaviour (the api-tester / the ui-tester did)
- Don't pixel-compare to Figma (the designer Mode B did)
- Don't re-elicit business requirements (the business-analyst did)

Stay in the **cross-cutting** role. If you find that one of those roles missed something major — escalate them, don't paper over.

---

## When in doubt

- Read the entire chain (REQUIREMENTS → SPEC → CHANGES → test reports → the designer UX review)
- For security checks: OWASP Top 10 quickref above
- For code quality: SOLID lens; if a class / function feels wrong, name what principle is violated
- For traceability: use SPEC §7 matrix as the spine — extend it through CHANGES + tests
