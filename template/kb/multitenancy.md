# Multitenancy

> Fill in: does your project serve multiple tenants from one database?
> If yes, describe the isolation pattern. If no, write `"N/A —
> single-tenant"`.

## Status

Multi-tenant: yes / no

If **no** → the rest of this file is `"N/A — single-tenant"`. Agents
skip multitenancy checks entirely.

If **yes** → fill in everything below.

## Tenant key

- Field name on tenant-scoped models: `company` / `account` / `tenant` / `org` / …
- Field type: `ForeignKey('users.Company', on_delete=PROTECT)` / `UUIDField` / …
- Where the tenant is resolved per request: `request.user.company` / middleware-set `request.tenant` / JWT claim / …

## QuerySet rule

**Every** QuerySet for a tenant-scoped model must filter by the tenant
key. Examples for your project:

```python
# ✅ Mandatory
def get_queryset(self):
    return SomeModel.objects.filter(<tenant_key>=self.request.user.<tenant_key>)

# ❌ Cross-tenant leak
def get_queryset(self):
    return SomeModel.objects.all()
```

## Models exempt from the rule

List models that are intentionally global (system-wide settings, shared
catalogues, reference data). Each exemption needs a one-line
justification. Default: empty list — every model is tenant-scoped.

- `models.GlobalSetting` — singleton system config (admin-only)
- `models.Country` — reference data

## Endpoint rule

No endpoint accepts the tenant ID as a parameter — that's a privilege
escalation vector. The tenant comes from the authenticated user only.

## Test discipline

- Every endpoint must have a **negative TC** for cross-tenant access:
  user from tenant A tries to access resource owned by tenant B,
  expects 404 (not 403 — avoids leaking existence).
- See `prompts/api-tester.md` STOP rules — the API tester refuses to
  APPROVE without these TCs.

## Skill overrides

Generality of `prompts/django-developer.md` discipline rules: when this
file declares multitenancy, agents enforce the tenant filter strictly.
When it says `"N/A"`, agents skip the check entirely. No middle ground.
