---
name: documentation-discipline
description: Use this skill when working as a coder (the django-developer / the vue-developer / the react-developer) and your implementation is complete — what documentation to update, where, and how. Covers docstrings, README updates, API endpoint docs, ADR status updates, migration notes, inline comments. The author of the change is responsible for the documentation.
---

# Documentation Discipline

**Rule:** the author of the change owns the documentation. No one else picks it up after you. Code without documentation is incomplete — it stays in PLAN, not in CHANGES.

---

## What to document, when, where

### 1. Docstrings (Python — <backend-app>)

A common Django setup uses **Sphinx with napoleon extension** (`<backend-app>/docs/source/conf.py`). Style: **Google-style docstrings** (napoleon's default and most readable).

**When:** every non-trivial function / class / module you add OR significantly modify.

**Where:** in the file, immediately after the `def` / `class` line.

**Google-style format:**

```python
def calculate_delivery_estimate(order, region):
    """Estimate the delivery date for an order to a region.

    Combines carrier SLA (CDEK / Yandex), warehouse processing time,
    and the region's holiday calendar.

    Args:
        order: Order instance to estimate delivery for.
        region: Region instance (destination).

    Returns:
        datetime.date — the expected delivery date in region's local TZ,
        the latest of (now + carrier SLA) and (next working day in region).

    Raises:
        ValueError: if region has no carrier configured.
    """
```

**Class docstrings:**
```python
class OrderViewSet(ModelViewSet):
    """REST endpoints for customer-facing order management.

    Filtered by `request.user.company` — multitenancy enforced.
    Customer can list / retrieve their own orders, cancel pending ones.
    Admin actions (status change, refund) are in employees.orders.
    """
```

**Module docstring** (top of `models.py`, `services.py`, etc.):
```python
"""Customer-facing order domain.

Aggregates: Order, OrderItem, OrderHistory.
Owns the customer side of the order lifecycle (placement → cancellation).
Admin-side mutations are delegated to `employees.orders`.
"""
```

**Skip:** trivial getters / one-line setters / obvious property declarations. Comments noise = bad.

**Module-level RST files**: each Django app has a `.rst` in `<backend-app>/docs/source/<app>.rst` for architectural overview. When adding a new app or significantly changing one — update or create the corresponding RST.

### 1b. Frontend documentation (Vue 2 / Vue 3 / Angular / TypeScript)

For frontend coders (the vue-developer, the react-developer) — industry standard is **TSDoc / JSDoc** inline plus README.md per significant directory. We don't ship a generated docs site for each frontend (yet); inline + README is the pragmatic minimum.

#### TSDoc / JSDoc — for any non-trivial composable / utility / class component

```typescript
/**
 * Resolves the customer's tracking URL for a given order.
 *
 * Maps carrier code (cdek / yandex / boxberry) to the carrier's tracking page
 * URL, URL-encodes the tracking_number safely.
 *
 * @param order - Order with tracking_number and carrier_code populated
 * @returns the absolute URL to the carrier's tracking page, or null if the
 *   order has no tracking_number yet.
 */
export function resolveTrackingUrl(order: Order): string | null {
  if (!order.tracking_number) return null
  const enc = encodeURIComponent(order.tracking_number)
  return CARRIER_URLS[order.carrier_code].replace('{n}', enc)
}
```

For Vue 3 components (`<script setup>`):

```vue
<script setup lang="ts">
/**
 * Renders an order's status timeline as a vertical stepper.
 * Skips cancelled state if order was never confirmed.
 */
const props = defineProps<{ order: Order }>()
const emit = defineEmits<{ refresh: [] }>()
</script>
```

For Vue 2 class components (`vue-property-decorator`):

```vue
<script lang="ts">
import { Component, Vue, Prop } from 'vue-property-decorator'

/**
 * Internal employee POS view of an order.
 * Allows status edits, refund initiation. Customer-side view is OrderCustomerView.
 */
@Component
export default class OrderEmployeeView extends Vue {
  @Prop({ required: true }) readonly orderId!: string
}
</script>
```

For Angular services:

```typescript
@Injectable({ providedIn: 'root' })
/**
 * Caches and resolves products for the <angular-admin-app> admin views.
 * Cache TTL: 60s. Invalidated on product mutation (see ProductMutationService).
 */
export class ProductCacheService { ... }
```

#### README.md per significant directory

Each frontend project's significant directory (`components/`, `composables/`, `stores/`, `pages/`) gets a short `README.md` describing:
- What this directory is for
- Conventions (naming, file layout)
- Examples of imports / usage
- Anything non-obvious about the dependency graph

Example `<storefront-app>/composables/README.md`:
```markdown
# Composables

Reusable composition functions for Vue 3 components.

## Conventions
- File name matches default export: `useOrders.ts` exports `useOrders`
- Composables prefixed with `use`
- Use `useFetch` / `useAsyncData` from Nuxt 3 for data fetching
- Pinia stores live in `stores/`, NOT here

## Files
- `useOrders.ts` — list / retrieve / cancel orders
- `useTracking.ts` — resolveTrackingUrl + carrier name display
```

#### Storybook / Compodoc

**Optional**, not required by DoD. Add when the frontend has UI components reused across pages and regression risk is high. For now, inline + README is sufficient.

### 2. Inline comments

**When:** the code's "why" isn't obvious from the "what".
- Working around a known bug in a library → cite the issue link
- Counter-intuitive choice (e.g. "intentionally not using `select_related` here because the queryset is consumed once") → explain
- TEMP / TODO / FIXME → with author + ticket reference

**Don't:** comment what the code already says. `# increment counter` next to `counter += 1` = noise.

### 3. README / docs updates

**When:** the change affects how others (developers, ops, customers) interact with the system.
- New CLI command → update README usage section
- New env var → update `.env.example` and docs
- New deployment requirement → update operational runbook
- New public API endpoint → update API documentation index

**Where (common conventions):**
- Backend public APIs: `<backend-app>/docs/` directory
- Frontend conventions: `<project>/README.md` at the root of each frontend project
- Operations: helm-values comments, helm-charts README

**How:** Conventional language, examples, gotchas. Assume reader is a smart developer new to the project.

### 4. ADR status update (collaboration with the system-analyst / the architect)

When you implement a feature with an Accepted ADR (from SPEC §6):
- After successful implementation — update the ADR status to `Implemented` in the SPEC sub-issue (post a short comment, don't edit description).
- If implementation revealed the ADR decision was wrong (rare) — flag in CHANGES under "Deviations from PLAN", post comment to SPEC sub-issue with mention to the architect.

### 5. Migration notes

When your change includes a migration:
- In the migration file's docstring/operations[0]: short description of intent.
- In CHANGES (Plane comment): explain whether the migration is reversible, expected runtime on prod data volume, any manual ops needed (CONCURRENTLY index in separate deploy, etc.).
- If the migration is part of a multi-step transition (per SPEC §5 Migration plan): mark this step number explicitly.

### 6. API endpoint documentation — drf-spectacular contract

Both qsale (`qa-server`) and coinex (`coinex-server`) use **drf-spectacular** to generate OpenAPI schema → ReDoc / Swagger UI. The schema is built from the view's source code: by default, **the view's docstring becomes the operation description in the published API docs**. No docstring → empty docs in production.

For every new / modified API endpoint, do all of this — these are **measurable** requirements, not formalities:

1. **View class has a docstring**, single-line summary on the first line + structured body. drf-spectacular splits the first line as `summary` and the rest as `description`. Example:

   ```python
   class OrderTrackingView(APIView):
       """Return tracking info for a customer's order.

       Path:    GET /api/v1/orders/{id}/tracking/
       Returns: 200 with {tracking_number, carrier, last_event}
                404 if the order does not belong to the authenticated tenant
       Errors:  401 unauthenticated, 403 wrong role
       """
   ```

2. **Override only when the docstring is not enough** — use `@extend_schema(...)` on the view method (`get`, `post`, etc.) to add precise request/response schemas, status codes, examples. Keep the docstring as the human-readable description; let `@extend_schema` carry the structured contract.

3. **Run the project's OpenAPI verifier as part of CHANGES verification.** The exact command is project-specific and lives in `$KB_DIR/kb/verify.md` — typically a slash-command like `/verify-openapi` wrapping a `make.sh openapi-check` target that runs `python manage.py spectacular --validate --fail-on-warn …` under the hood. Do NOT inline raw `manage.py` commands in your CHANGES — call the project's wrapper so behaviour stays consistent across runs and projects. The wrapper must:

   - run `spectacular --validate --fail-on-warn` (or equivalent) to make missing-description / missing-help_text warnings fatal,
   - exit non-zero on any warning or error.

   The CHANGES `verification` field MUST include this command and its result (e.g. `✅ /verify-openapi — 0 warnings, 0 errors`). `post_changes(ready_for_review=True)` (`plane-api.md` §6.7d) refuses without it.

   If the project does not yet expose this verifier in `kb/verify.md`, that's a project-side gap — surface it via `escalate_upstream_gap` (`plane-api.md` §6.7c) before claiming `ready_for_review=True`.

4. **Help text on serializer fields** — every non-trivial Serializer field should pass `help_text="..."`. drf-spectacular pulls it into the schema's field description; without it, ReDoc shows naked field names.

5. **For non-standard endpoints** (idempotency keys, custom headers, file upload, async polling) — document in the view docstring AND mirror in `@extend_schema(parameters=[...])` so they appear in the published docs.

### 7. Test names as documentation

Test function names ARE documentation:
- ❌ `test_order_1`, `test_create`
- ✅ `test_create_order_returns_201_with_order_uuid`
- ✅ `test_cancel_already_cancelled_order_returns_409_conflict`

A reader of the test suite should understand the API behaviour from test names alone.

---

## What NOT to document

- **Auto-generated code** (Django migrations operations, except top docstring; ORM-generated SQL; build artifacts).
- **Obvious code** (`def get_id(): return self.id` doesn't need a docstring).
- **Internal helpers used in one place** — better: rename for clarity. If the function is only called once and the name is clear, no docstring needed.
- **Outdated information** — better no docs than wrong docs. If you can't keep it current, don't write it.
- **Implementation details that may change** — document the contract / behaviour, not the current internal mechanism.

---

## Where docs live (common patterns)

| Documentation type | Location |
|---|---|
| Python docstrings | inline in code |
| API endpoint behaviour | view class docstrings + drf-spectacular schemas |
| Backend developer guide | `<backend-app>/docs/` directory |
| Frontend project README | `<project>/README.md` (<storefront-app>, <admin-panel>, <pos-panel>, <angular-admin-app>) |
| Architecture decisions | SPEC sub-issue ADRs in Plane (long-lived) |
| Operational runbooks | `helm-values`, `helm-charts` repos |
| User-facing features | external help center (the business-analyst's domain, not coder's) |

---

## Definition of Done — documentation slice

A coder's CHANGES is incomplete unless:

- [ ] All new public functions / classes / modules have docstrings
- [ ] Inline comments explain non-obvious "why"
- [ ] If new public API / CLI command → relevant README / docs updated
- [ ] If new env var → `.env.example` updated
- [ ] If implementing an ADR → ADR status posted as comment on SPEC sub-issue
- [ ] Migration files have intent docstring
- [ ] Test names are descriptive
- [ ] No outdated documentation left after refactor

This goes in the final step of Phase 2, alongside `/run-tests-all` etc. Don't mark step `[x]` until docs are also updated.

---

## Anti-patterns

- "I'll document it later" — there is no later. Either now or never.
- Docstrings copy-pasted from related but different functions — wrong information is worse than no information.
- README of 50 lines unchanged for 2 years while the project shipped 100 features — you contributed to this; update it.
- Inline comments for every line — noise degrades signal.
- Documenting **how** when SPEC documents **what** — link to SPEC, don't restate.

---

## When in doubt

- Read affected files first — see what doc style is established. Match it.
- If no doc style exists in a file you're editing — be the one to start. One docstring is better than zero.
- For tricky decisions with broader impact — bump up to ADR (in SPEC), don't bury in inline comments.
