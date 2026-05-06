# Architecture

> Fill in: how this codebase is organised — services, modules, import
> boundaries. Agents check these before designing or refactoring.
>
> Write `"N/A — monolithic single-app"` if your project is a single
> trivial module without enforced boundaries.

## High-level layout

Describe directory layout at the level agents need to understand:

```
<repo>/
├── apps/
│   ├── backend/        # Django, all backend code
│   ├── storefront/     # Vue 3 / Nuxt 3
│   └── admin/          # React / Next.js
├── packages/           # shared TS libs (if any)
└── infra/              # k8s / terraform / helm
```

## Services / bounded contexts

If your backend is split into multiple services or apps that own
distinct domains, list them. Otherwise `N/A`.

| Service / app | Domain | Owns |
|---|---|---|
| `users` | identity, accounts | User, tenant entities, permissions |
| `customers` | customer-facing storefront | Customer, Order, Cart |
| `employees` | internal staff console | Employee, internal roles |
| `common` | cross-cutting domain | callbacks / webhooks |
| `shared` | shared libs | utility models with no domain |

## Import contracts (importlinter / equivalent)

If you enforce service boundaries via [import-linter](https://github.com/seddonym/import-linter),
file-based ESLint rules, or by convention, document them here.

- Tool: `import-linter` / Custom ESLint / `pyproject.toml` ruleset / N/A
- Config: `pyproject.toml` `[tool.importlinter]` / `.importlinter.cfg` / …

### Forbidden patterns

List what cross-service imports are forbidden:
- e.g. "`<service-A>` cannot import from `<service-B>.views / .serializers / .filters / .permissions`"
- e.g. "Anything in `apps/` cannot import from `apps/admin/internal/`"

### Allowed patterns

List what is explicitly allowed:
- e.g. "Cross-service imports of `models` are allowed"
- e.g. "Anything can import from `shared/`"

### How to verify

- Local check: `<command from kb/verify.md>`
- CI: `<which job runs it>`

## Module structure conventions

For Django apps:
- Where do views go? (e.g. `<app>/views/<resource>.py`, one resource per file)
- Where do serializers go?
- Where do business services live? (e.g. `<app>/services.py`, separate from views)
- Where do tests live? (e.g. `tests/<app>/test_<feature>.py`)

For frontends — see [`frontends.md`](frontends.md).

## Key cross-cutting modules

- `<repo>/<path>` — (e.g. shared decorators, base models, common middleware)
- `<repo>/<path>` — (e.g. settings module hierarchy)
