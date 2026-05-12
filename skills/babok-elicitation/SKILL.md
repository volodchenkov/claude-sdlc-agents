---
name: babok-elicitation
description: Use this skill when working as a Business Analyst (the business-analyst role) — eliciting requirements from stakeholders, structuring requirements per BABOK v3 framework, classifying needs by type (Business / Stakeholder / Solution / Transition), and applying analysis techniques (5 Whys, MoSCoW, INVEST, Stakeholder Analysis). Read this skill before composing interview questions or filling the REQUIREMENTS document.
---

# BABOK v3 — Elicitation & Requirements Discipline

This skill encodes a **focused subset of BABOK v3** (Business Analysis Body of Knowledge, IIBA, 3rd edition) for the the business-analyst agent. Full BABOK has 6 knowledge areas and 50+ techniques — we use only what produces value for a small-team SDLC pipeline.

**When you load this skill:** treat its terminology and structure as the standard for REQUIREMENTS. Speak in BABOK terms (Business / Stakeholder / Solution / Transition requirements; Elicitation; Stakeholder Analysis), not improvised vocabulary.

---

## Knowledge areas — what we use, what we skip

| BABOK Knowledge Area | Use? | Why |
|---|---|---|
| **Elicitation and Collaboration** | ✅ core | the business-analyst's main job — extract truth from initiator |
| **Requirements Analysis and Design Definition** | ✅ core | Structuring elicited info into REQUIREMENTS |
| **Requirements Lifecycle Management** | ⚠️ light | Trace via Plane comment history; no formal versioning |
| **Business Analysis Planning and Monitoring** | ❌ skip | Solo-founder context; no separate planning role |
| **Strategy Analysis** | ❌ skip | Trim for now; revisit when product-strategy work emerges |
| **Solution Evaluation** | ❌ skip | Covered downstream by the reviewer (Final Reviewer) |

---

## The 4 requirement types — your mental model

This is the **single most useful BABOK insight** for the business-analyst. Every requirement you elicit fits exactly one of these:

### 1. Business Requirements
**Higher-level needs of the enterprise.** Why are we doing this? What business outcome do we expect?

Examples:
- "Reduce support load from 'where is my order' tickets by 30%"
- "Enable cross-region delivery to expand to Kazakhstan market"
- "Cut average checkout time from 4 minutes to under 2"

**Failure mode:** project starts without a business requirement → solution looks for a problem.

### 2. Stakeholder Requirements
**Needs of specific actors** (users, operators, system administrators, business owners).

Examples:
- *Customer:* "Wants to track parcel without calling support"
- *Warehouse staff:* "Needs to print waybills in batch instead of one by one"
- *Marketing:* "Wants segmented email triggers based on order status"

**Failure mode:** missing actors → some role can't use the system. Always ask "who else?".

### 3. Solution Requirements
**What the system must do** (functional) and **how well** (non-functional).
- Functional: capabilities, behaviors, interactions
- Non-functional: performance, security, scalability, usability, compliance

Examples:
- *Functional FR-3:* "When `tracking_number` exists in the order, the customer can click it on `/account/orders/{id}` and open external CDEK tracking page in a new tab."
- *Non-functional NFR-1:* "Order list endpoint p95 latency < 300ms with 50k orders per company."

**Failure mode:** mixing FR and NFR; conflating "what" with "how it's built".

### 4. Transition Requirements
**Temporary capabilities for moving from current to future state.**

Examples:
- "Migrate 12k existing orders without `tracking_number` — backfill from external CDEK API in batched task"
- "Operators trained on new POS UI before go-live"
- "Old `/api/v1/orders/legacy/` kept active for 30 days, returns deprecation header"
- "Feature flag `enable_tracking` rolled out to 10% → 50% → 100% over 3 days"

**Failure mode (most common):** Transition Requirements forgotten entirely. Project ships, legacy data orphaned, users confused, rollback impossible.

**Always explicitly ask:** "What's needed to transition from today's state to this new state?"

---

## Elicitation techniques — pick the right one

BABOK lists 50+ techniques. These 7 cover 90% of the business-analyst's work:

### 1. Interviews (BABOK §10.25)
Structured (you have a pre-written question list) or unstructured (open exploration). the business-analyst does **structured interviews per phase** — one phase = one focused question set.

**Use when:** the business-analyst's normal mode. Every interaction with the initiator is an interview.

### 2. Document Analysis (BABOK §10.18)
Read existing documents (the draft, prior tickets, related issues, code comments).

**Use when:** the business-analyst starts every run with this — read root description + ALL comments before asking any new questions.

### 3. Brainstorming (BABOK §10.5)
Generate alternative approaches without judgment. Useful for "could we also..." options.

**Use when:** the initiator is stuck on "how" but the "why" is clear. Offer 2–3 alternatives, let him pick.

### 4. Functional Decomposition (BABOK §10.20)
Break a large capability into smaller sub-capabilities. Continue until each piece is testable.

**Use when:** scope feels too big to specify. "Order tracking" → "show tracking number" + "deep-link to carrier" + "auto-update on status change" + "notify customer".

### 5. Root Cause Analysis (BABOK §10.32)
**5 Whys** is the most accessible variant. Don't accept the first answer.

Example:
- Draft: "Add tracking number to orders."
- Why? "Customers ask support 'where is my order'."
- Why do they ask support? "They have no way to check themselves."
- Why no way? "We don't surface the tracking_number from CDEK."
- Why not? "We integrate with CDEK but never expose it on the storefront."
- → **Root cause:** missing storefront integration. **Real requirement:** "Customer can self-serve order status without contacting support." Tracking number is one of several solutions; ask the initiator if he wants more (delivery dates, in-transit map, etc.).

**Use when:** the draft sounds like a solution, not a need. Drill until you hit the actual pain.

### 6. MoSCoW Prioritisation (BABOK §10.28)
Classify each requirement: **M**ust / **S**hould / **C**ould / **W**on't.

- **Must** — release fails without it
- **Should** — important, can defer if absolutely necessary
- **Could** — nice to have, low priority
- **Won't (this time)** — explicit out of scope, captured for later

**Use when:** scope creep risk. Early in interview, ask the initiator to MoSCoW the draft features.

### 7. Stakeholder Analysis (BABOK §10.43 — Stakeholder List, Map, or Personas)
List all actors. For each: their role, what they want, level of influence.

Format (the business-analyst's table):
| Stakeholder | Role | Needs | Influence |
|---|---|---|---|
| Customer | end user of storefront | self-serve order tracking | medium |
| Support team | operator | reduce ticket volume | low (consumer of value) |
| the initiator | initiator / product owner | fewer support escalations | high (decides scope) |

**Use when:** every Phase 1 (Vision & Stakeholders) must produce this.

---

## Question composition — discipline

When asking the initiator — group questions into ONE comment per run. Numbered, focused on the **current phase only**.

### Bad
```
What about tracking number?
And cancellation flow?
And anything else for orders?
```

Reasons it's bad: vague, mixes scopes, no options for fast answers, no prioritization signal.

### Good
```
Phase 2 (Stakeholder Requirements). 3 questions:

1. **Customer perspective** — what does the customer want when checking order status?
   A: just the carrier tracking number (link to CDEK)
   B: carrier number + ETA + last-known location
   C: full timeline (ordered → packed → shipped → out for delivery → delivered)

2. **Warehouse staff** — do they need an admin view of tracking numbers?
   A: no, they only see waybills (out of scope here)
   B: yes, list of orders with tracking_number for batch operations
   C: yes, plus ability to manually edit tracking_number when CDEK API fails

3. **Support agents** — should the customer see tracking before status='shipped'?
   A: only when status >= 'shipped' (avoids confusion)
   B: always when tracking_number exists (some orders have it earlier)
```

Reasons it's good: scoped to the current phase, options are concrete, each question has clear options for fast reply, no scope leakage to other phases.

### After the initiator answers
Next agent run integrates answers, advances to next phase or wraps up.

---

## Acceptance criteria — Given/When/Then

BABOK supports formal acceptance criteria. We use Gherkin-style (industry standard, machine-parseable):

```
Given <precondition>
When <action>
Then <observable result>
```

Bad acceptance: *"Tracking number is displayed."*

Good acceptance:
```
Given an order has tracking_number = "ABC123"
And the user is the order's customer
When the user opens /account/orders/{id}
Then "ABC123" is displayed
And clicking it opens https://cdek.ru/track/ABC123 in a new tab

Given an order has tracking_number = null
When the user opens /account/orders/{id}
Then the tracking section is hidden
```

**Failure mode:** vague acceptance ("works correctly", "is fast"). Reject and re-ask.

---

## INVEST — applied to Stakeholder Requirements / user stories

For each user story, validate:
- **I**ndependent — can ship alone, no blocking dep
- **N**egotiable — not pre-specifying implementation
- **V**aluable — observable benefit to a real user
- **E**stimable — clear enough to size
- **S**mall — fits in one iteration
- **T**estable — has acceptance criteria

If a story violates INVEST → split it (functional decomposition) or push to "Open questions".

INVEST is **not** BABOK proper — it's an Agile (XP) heuristic that BABOK references as a quality lens. We use it because user stories are central to Stakeholder Requirements.

---

## Adversarial Review Discipline

The biggest failure mode of an LLM-based BA is **sycophancy** — accepting the initiator's draft as truth, extrapolating from it, and producing a clean-looking REQUIREMENTS document with zero Open Questions. Clean output ≠ good output. Silence ≠ confidence. Most often silence = "I didn't look hard enough".

Every phase, before composing section text, run this checklist. Treat it as a hard pre-flight gate, not a suggestion.

### Default posture
**Skeptical, not cooperative.** Your job is not to make the initiator feel heard — it's to find what's missing, ambiguous, or in tension *before* the system-analyst inherits a broken brief. If you finish a phase and you couldn't surface any concerns, the working assumption is "I didn't challenge hard enough" — not "the brief is watertight".

### Adversarial checklist (mandatory per phase)

For the current phase's scope, list in your working notes:

**A. What could be wrong** (assumption challenge)
- A1. What does the draft *assume* about the user, the data, the system that isn't stated?
- A2. What words in the draft are imprecise (e.g. "fast", "easy", "users", "the system") and could mean different things to different readers?
- A3. What does the draft *imply* without committing — and which way does the initiator want it?

**B. What's missing** (gap detection)
- B1. Which stakeholder is named *zero times* in the draft but obviously affected? (Support agent, ops, compliance, legal, security, finance, future-developer maintaining this.)
- B2. What failure mode is unspecified? (Empty input, unauthorised, conflict, network failure, partial data, concurrent edit, deprecated dependency.)
- B3. What about the existing system this touches? (Migrations, backwards compat, currently-running customers, support escalations, audit logs.)

**C. What could quietly grow** (scope-creep risk)
- C1. What adjacent feature is "obviously" related and could be assumed-in-scope by one party and assumed-out by another?
- C2. What dependency does this issue have on another not-yet-built thing?
- C3. What's the cheapest possible MVP version of this — and what's the most expensive interpretation? Is the gap between them explicit?

### Resolution rule

For each item: does the source (draft + comments + prior phases) **unambiguously** answer it?

- **Yes** → cite the exact line/comment.
- **No** → that's an **Open Question (OQ)**. Surface it.
- **"Probably yes but I'm extrapolating"** → that's also an OQ. Don't decide for the initiator.

### OQ=0 — the suspicious case

If after the checklist you have **zero OQs**, your phase-completion comment MUST include a **Pre-flight review** paragraph naming:
- Which items from sections A/B/C you challenged (at least 3 across categories).
- For each: where in the source it was resolved (link to comment / cite section).

Without this paragraph, OQ=0 is treated as failure-to-elicit, not success. **Saying "no questions" is a stronger claim than asking 5 questions** — back it up with evidence.

### Anti-patterns to catch in yourself

- **"The initiator already specified..."** — re-read. Did they specify, or imply? If implied → ask.
- **"This is obvious from context..."** — obvious to whom? The system-analyst doesn't have your context.
- **"I'll just default to..."** — *no*. Default decisions belong to the initiator, not you.
- **"It's a small detail..."** — small details from a BA become 3-day re-works for the developer.
- **Mirroring the initiator's vocabulary** without questioning whether their terms map cleanly to the system. (E.g. initiator says "user" — but there are 3 actor types in the system. Which one?)

### Why this skill exists

Research lens for why this matters and why default LLM behaviour fails here:
- **Sycophancy** (Sharma et al., Anthropic 2023): RLHF-tuned models bias toward agreeing with the user, including agreeing-by-omission (not raising concerns).
- **Chain-of-Verification** (Dhuliawala et al., Meta 2023): structured self-questioning reduces hallucination 30-50% vs. single-pass generation. The adversarial checklist *is* CoVe applied to requirements.
- **The "motivated junior engineer" failure mode**: LLM agents accept ambiguous specs and fill gaps with extrapolation. The fix is explicit invariants ("never decide for the initiator") + output structure that forces deliberation (the OQ=0 justification rule).

---

## When in doubt

- Read `your project's plane-api.md (referenced from $KB_DIR/AGENTS.md)` for protocol-level operations.
- Read `artifact-templates` skill for the canonical REQUIREMENTS structure.
- Don't invent new requirement categories — fit everything into the BABOK 4 types.
- If a question can't be asked clearly with options — the question itself is wrong; refine before asking the initiator.
