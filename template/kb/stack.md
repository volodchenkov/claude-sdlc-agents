# Stack

> Fill in: what languages, frameworks, databases, queues, and notable
> libraries your project uses. Versions matter — agents make different
> choices for Django 4.2 vs 5.0, Vue 2 vs Vue 3, etc.

## Backend

- Language: Python 3.X / Node 20 / Go 1.22 / …
- Framework: Django X.Y / FastAPI / Flask / Express / …
- API layer: DRF / drf-spectacular / Strawberry / GraphQL / …
- Database: PostgreSQL X / MySQL Y / SQLite / …
- ORM extensions: psqlextra / django-postgres-extra / SQLAlchemy plugins / …
- Cache: Redis X / Memcached / in-process / N/A
- Queue / async: Celery / RQ / arq / native asyncio / N/A
- Auth: django.contrib.auth / SimpleJWT / Auth0 / Cognito / …
- Notable libs: {django-storages, django-filter, drf-yasg, …}
- Hosting: AWS / GCP / Yandex Cloud / on-prem / k8s / Docker Compose

## Frontend

Summary only — details per project in [`frontends.md`](frontends.md).

Which frontends ship in this repo:
- e.g. `apps/storefront` — Vue 3 / Nuxt 3
- e.g. `apps/admin` — React 18 / Next.js 14
- e.g. `apps/pos` — Vue 2 / Nuxt 2

## Infra

- CI / CD: GitHub Actions / GitLab CI / CircleCI / …
- Secrets: `.env` / AWS Secrets Manager / Vault / k8s Secret
- Object storage: S3 / Yandex Object Storage / GCS / Azure Blob / N/A
- Observability: Sentry / Datadog / Prometheus + Grafana / N/A

## Pinned versions (the ones that affect API surface)

```
python = 3.11
django = 4.2
djangorestframework = 3.14
postgres = 16
redis = 7.2
celery = 5.3
```
