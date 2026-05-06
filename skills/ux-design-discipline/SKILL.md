---
name: ux-design-discipline
description: Use this skill when working as the designer — producing UX flow + Figma frame inventory for SPEC implementation, evaluating accessibility (WCAG 2.1 AA), applying Nielsen usability heuristics, choosing platform conventions (Material 3 web / iOS HIG / desktop). Also covers UX-Review mode — verifying frontend implementation against design.
---

# UX Design Discipline

This skill encodes the design lens for the designer agent. Two modes:
- **Mode A: Design brief** — produces a Design sub-issue with UX flow + Figma frame inventory before frontend coders start.
- **Mode B: UX review** — after frontend ships, verifies implementation matches design intent.

Inspired by:
- **Nielsen 10 Usability Heuristics** (Jakob Nielsen) — universal evaluation framework
- **WCAG 2.1 Level AA** (W3C) — accessibility compliance
- **Material Design 3** (Google) — for web / Android components
- **iOS Human Interface Guidelines** (Apple) — for iOS-flavoured UIs
- **Inclusive Design Principles** (Microsoft / W3C) — beyond a11y to broader inclusion

---

## Nielsen 10 Usability Heuristics — apply during Design brief AND UX review

Walk through these 10 for every screen / flow:

1. **Visibility of system status** — user always knows what's happening (loading spinner, success toast, progress bar).
2. **Match between system and the real world** — labels in user's language, not jargon. "Order delivered" not "txn_status_5".
3. **User control and freedom** — undo / cancel for destructive actions; clear exit from any state.
4. **Consistency and standards** — same word for same concept across the product. Match platform conventions (back button placement, primary action style).
5. **Error prevention** — confirm destructive actions; constrain inputs (date picker rather than free text); inline validation.
6. **Recognition rather than recall** — visible options / autocomplete instead of asking user to remember.
7. **Flexibility and efficiency of use** — accelerators for power users (keyboard shortcuts, bulk operations) without burdening newcomers.
8. **Aesthetic and minimalist design** — every UI element earns its place; remove what's not adding info.
9. **Help users recognize, diagnose, and recover from errors** — error messages explain what went wrong + suggest fix.
10. **Help and documentation** — when needed, contextual help, not a separate manual lost from the flow.

For Design brief: every screen / state in the design must answer: which heuristics are addressed?
For UX review: every heuristic violated in implementation = a finding.

---

## State coverage — every screen has 8 states minimum

Designs that only show "happy path" cause downstream pain. For every page / component, design and document:

1. **Empty** — no data yet (first-time user, empty list, no results)
2. **Loading** — async data not yet arrived (skeleton, spinner, progress)
3. **Partial** — some data, more loading (e.g. above-fold loaded, infinite scroll spinner below)
4. **Success / populated** — normal use
5. **Error** — API failure, network down, validation failure
6. **Permission denied** — user without access (forbidden, not just hidden)
7. **Edge / extreme** — very long names, very many items, missing optional fields
8. **Disabled / read-only** — when interaction not currently allowed (pre-launch, locked due to status)

In the Design brief, list which states each component supports + Figma frame for each.

---

## Accessibility (WCAG 2.1 Level AA) — overlap with the ui-tester but the designer owns the **intent**

The designer's responsibility: design must be **a11y-by-default**. The ui-tester verifies; the designer prevents.

### Color and contrast
- Text contrast ≥ 4.5:1 (normal) / ≥ 3:1 (large 18pt+ or 14pt+ bold). Decorative graphics excepted.
- Don't use color alone to convey meaning — pair with icon, text, or pattern.
- Test designs at 200% browser zoom — does it still work without horizontal scroll?

### Touch targets
- Minimum 44×44 px (iOS HIG) / 48×48 dp (Material 3) for touch targets.
- Spacing between adjacent targets — at least 8 px so finger doesn't hit wrong one.

### Typography
- Body text minimum 16 px (12 pt) on web / 14 pt on iOS.
- Line height ≥ 1.5 for body. Letter spacing default unless specific need.

### Focus indicators
- Every interactive element shows visible focus state when keyboard-navigated. Default browser ring acceptable; custom ring also OK if visible (≥ 2 px, ≥ 3:1 contrast).
- DON'T `outline: none` without replacement.

### Icons + labels
- Icon-only buttons need `aria-label`. Avoid icon-only buttons in primary flow (recognition > recall).
- Use clear, action-oriented labels ("Save" not "Submit", "Cancel order" not "X").

### Forms
- Every input has a visible `<label>`. Placeholder is NOT a label — it disappears on input.
- Error messages near the field, in plain language, with how to fix.

### Motion
- Don't depend on animation for understanding. Provide alternatives for `prefers-reduced-motion`.
- Avoid auto-playing video / aggressive parallax.

For full reference: https://www.w3.org/WAI/WCAG21/quickref/

---

## Platform conventions — pick one per surface

Projects often ship multiple frontends with different conventions. The project's `$KB_DIR/kb/frontends.md` declares the inventory. Common patterns:

### Customer-facing storefront (typically Vue 3 / Nuxt 3 or React / Next.js)
- Convention: **Material 3** simplified — Material's spacing / shape / motion principles, but visual style is project-branded.
- Mobile-first responsive. Breakpoints: 360 / 768 / 1024 / 1440.
- Touch targets 48 dp.
- Standard web nav (top bar, hamburger on mobile).

### Admin / POS / internal panels
- Convention: **desktop-first** — power users, dense info, keyboard shortcuts.
- Tables, forms, action buttons; less marketing flair.
- UI library per panel (Buefy / Bulma / Material UI / Ant Design / custom) per `$KB_DIR/kb/frontends.md`.
- Mobile responsive only for "view-only" cases; primary use is desktop.

### iOS / Android native (future, if any)
- Use platform HIG / Material 3 directly. Don't impose web conventions.

---

## Mode A: Design brief — what to produce

For every Plane task that has a frontend impact, the designer creates a Design sub-issue with:

1. **Figma link(s)** — anchored to specific frame (`?node-id=...` URL form)
2. **UX flow** — 5–10 lines, step-by-step user journey
3. **Screen / state list** — table: screen name × states (8-state matrix)
4. **Component spec** (when introducing a new component) — variants, props if known, behaviour states
5. **Constraints** — brand tokens, accessibility callouts, motion limits
6. **Open questions** — for the initiator / system-analyst / architect (e.g. "should empty state show CTA to create?")

Don't include implementation details (Vue 3 vs Vue 2, Pinia vs Vuex). That's coder territory.

---

## Mode B: UX review — what to check after frontend ships

Triggered after Frontend CHANGES posted. The designer re-runs through the design to verify:

1. **All 8 states present** — empty / loading / partial / success / error / permission / edge / disabled
2. **Nielsen 10** — each heuristic considered; flag violations
3. **WCAG 2.1 AA quick pass** — contrast, focus, touch targets, alt text (rough check; the ui-tester does the deep audit)
4. **Pixel-vs-Figma** — not pixel-perfect, but functional and structural match (heading hierarchy, primary action prominent, layout responsive)
5. **Brand tokens used** (colors, spacing, typography) — not hardcoded values
6. **Motion / micro-interactions** — present, accessible, not distracting

Output: review comment in Frontend sub-issue with severity-classified findings (blocker / major / minor) and suggested fix.

---

## Anti-patterns

- "Just use Material" — convention chosen without thought to brand or context (POS user vs storefront customer have different needs)
- Designs that show only happy path — leads to ad-hoc empty / loading / error states implemented without thought
- "Accessibility is QA's job" — wrong; designer prevents, QA verifies
- Pixel-perfect obsession — implementation will diverge by a few px; that's fine. What matters is structure, hierarchy, behaviour.
- "Designer doesn't need to write" — Figma alone isn't documentation; the brief explains the **why** behind the frames

---

## When in doubt

- Start with REQUIREMENTS Stakeholder Requirements (section 3) — design serves them, not aesthetic preference.
- Start with SPEC §4 Frontend Behaviour — that's the contract; don't contradict it.
- For accessibility unsure? Consult the WCAG 2.1 quickref linked above.
- For component patterns unsure? Look at existing project patterns; don't introduce a new visual language without explicit need.
