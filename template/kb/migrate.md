# Database migrations

> Fill in: how migrations work in your project — the canonical
> settings module to use, large-table rules, multi-step plan policy.

## Migration tool

- Framework: Django migrations / Alembic / Flyway / Liquibase / …
- Tracking: `migrations/` folders per app / single `versions/` directory / …

## Canonical command

In multi-settings projects (Django with split settings per service), one
settings module is canonical for migrations — it sees all apps. Document
yours:

```bash
# ✅ Always via the canonical settings module
python manage.py makemigrations --settings <canonical-settings-module>

# Examples per project type:
#   apps.users.settings        (split-settings architecture, one settings module per service)
#   config.settings.production (Django cookiecutter)
#   <none — single settings.py> (most small projects)
```

**Do NOT run `makemigrations` against other settings modules** — it
produces misleading results.

## Backward compatibility

- **Adding a field** — nullable or with a default. Never `null=False`
  on an existing populated table without a default.
- **Removing a field** — multi-step plan:
  1. Deploy code that doesn't read the field. Field still in DB.
  2. (Optional) Backfill any data dependent on field's existence.
  3. Deploy migration that removes the field.
  4. Final deploy if needed.
- **Renaming a field** — add new + dual-write + deprecate old + remove old (4 deploys minimum).
- **Changing field type** — add new column with new type, dual-write, switch reads, drop old.

## Large tables

For tables > 1M rows or critical hot paths:

- Use `CREATE INDEX CONCURRENTLY` (Postgres) — never blocking index creation in production
- Batch data migrations with `RunPython` chunked by primary key range
- Avoid `ALTER TABLE` operations that rewrite the table — prefer add-new-column + backfill + swap

## Pending-migrations rule

**Pending migration in ANY app blocks deployment of the whole project**
(typical Django setup deploys all apps together). Agents must not
dismiss "not from my task" pending migrations — escalate to the
initiator.

Verification: see `kb/verify.md` (`/check-migrations` or equivalent).

## Migration documentation

Every migration file must have:
- A docstring at the top of the migration class explaining intent
- A note in CHANGES if the migration is not reversible
- A note in CHANGES if the migration takes >5 minutes on production data volume

See `kb/document.md` for the docstring style.
