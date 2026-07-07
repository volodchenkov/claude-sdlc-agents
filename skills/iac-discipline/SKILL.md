---
name: iac-discipline
description: Use this skill when working on Yandex Cloud infrastructure — provisioning clusters, databases, buckets, VMs; writing OpenTofu / Argo CD / Crossplane; setting up GitLab CI pipelines for infra; onboarding a new tenant; or reviewing a `tofu plan`. Encodes the modern 2026 default stack (OpenTofu Stacks + Argo CD + Crossplane + external-secrets → YC Lockbox), the blast-radius classification for applies, and the discipline rules that keep IaC repeatable — plan-as-review-artifact, no long-lived tokens, semver-pinned modules, no manual UI steps in bootstrap.
---

# IaC Discipline

**Rule:** infrastructure code is provable, not persuadable. The deliverable is not «it worked once from my laptop», it is «`tofu plan` in a merge request reads clean, matches the SPEC, and applies idempotently on a fresh account». Everything below exists to make that possible.

Read this skill in full before touching any infrastructure code, opening an infra MR, or reviewing an infra `plan`. For code style, tests, and GitOps details, cite the referenced skills — don't restate them.

---

## Default stack (2026 modern)

Use these unless the ticket says otherwise:

| Layer | Choice | Notes |
|---|---|---|
| Provisioning | **OpenTofu 1.10+** | Not Terraform. Community-standard fork since 2024. |
| Multi-env | **OpenTofu Stacks** | Native 1.9+ feature. Groups modules into stacks; each env is a *deployment* of the stack. Replaces Terragrunt's DRY layer. |
| State backend | **YC Object Storage + YDB locks + KMS encryption** | S3-compatible, native YC. Never local state past the bootstrap step. |
| Module registry | **GitLab Terraform Module Registry** (native) | Modules pinned by semver tag (`version = "2.2.5"`), never `main`, never a branch. |
| k8s app delivery | **Argo CD** with app-of-apps + ApplicationSet | No `helm upgrade` from CI. CI builds images; Argo CD syncs manifests. |
| k8s day-2 resources | **Crossplane** with YC provider | App teams request DBs / buckets via `kubectl apply` on a Claim; platform team owns Compositions. |
| Secrets | **YC Lockbox + external-secrets operator** | Never env vars, never k8s Secret checked in, never plain values in Helm values. |
| Cluster boot | cert-manager · external-dns · external-secrets · reloader · kyverno | Applied by Argo CD from a `cluster-bootstrap/` app-of-apps. |
| Observability | **VictoriaMetrics + VictoriaLogs + Grafana** | VL replaced Loki by 2025 benchmarks. YC Monitoring is opt-in for small envs. |
| CI/CD auth | **GitLab OIDC → YC IAM federation** (`$CI_JOB_JWT_V2`) | No long-lived tokens. No `YCLOUD_TOKEN` env var. |
| CI plan pattern | `tofu plan` on MR → comment; `apply` on merge as **manual job on protected environment** | Never auto-apply on merge. Never apply from a laptop past bootstrap. |
| Version bumps | **Renovate** | Modules, providers, base images. Auto-MR, human-approved. |
| Security scan | **checkov + tflint + trivy config** | Pre-commit + CI. Blocks MR on high-severity. |

Style / testing / GitOps details are elsewhere. Cite these, don't restate:

- **HCL style** → `terraform-style-guide` skill
- **Module tests** (`.tftest.hcl`) → `terraform-test` skill
- **Module library shape** (`main.tf` / `variables.tf` / `outputs.tf` / `README.md`) → `terraform-module-library` skill
- **Argo CD setup + sync policies** → `gitops-workflow` skill
- **GitLab CI stanzas** (caching, artifacts, needs graph) → `gitlab-ci-patterns` skill

---

## Repository shape

One repo per tenant. Do not co-mingle tenants — separate GitLab project, separate YC organization/cloud, separate state buckets.

```
<tenant>-infra/
├── .gitlab-ci.yml                  # plan-on-MR + manual apply per env
├── .pre-commit-config.yaml         # tofu fmt · tflint · checkov · trivy config
├── CLAUDE.md                       # tenant-specific overrides
├── kb/
│   ├── conventions.md              # naming, tagging, tenant-specific rules
│   ├── verify.md                   # verification commands (tofu fmt/plan/tflint/...)
│   ├── architecture.md             # this tenant's topology
│   └── document.md                 # what to document per module
├── bootstrap/                      # LOCAL state, applied once per tenant
│   └── main.tf                     # folder + KMS + state bucket + YDB lock table + IAM
├── stacks/
│   ├── platform/                   # per-region cluster + shared services
│   │   ├── stack.tofu              # OpenTofu Stacks manifest
│   │   ├── components/
│   │   │   ├── vpc/
│   │   │   ├── k8s/
│   │   │   ├── postgresql/
│   │   │   ├── object-storage/
│   │   │   └── lockbox/
│   │   └── deployments/
│   │       ├── dev.tfdeploy.hcl
│   │       ├── stage.tfdeploy.hcl
│   │       └── prod.tfdeploy.hcl
│   └── app/                        # per-app / per-team stacks if needed
├── argocd/
│   ├── bootstrap/                  # root App-of-Apps (applied once)
│   ├── platform/                   # cluster-wide operators (cert-manager, esso, kyverno, ...)
│   └── apps/                       # ApplicationSet per team/service
└── crossplane/
    └── compositions/               # YC DB / bucket / IAM claims for app teams
```

Guardrails:
- One **stack** per bounded lifecycle. VPC + k8s + core services in `platform`; app-team resources via Crossplane, not in the platform stack.
- Each stack's `deployments/` directory is the ONLY place env-specific values live. Modules never `count = var.env == "prod"`.
- No file above 300 lines in a component. Split.

---

## Bootstrap — the chicken-and-egg

You cannot store OpenTofu state remotely until the state backend exists. The `bootstrap/` module solves this in ONE apply from a laptop, then never gets touched again by humans.

**What `bootstrap/` provisions (in order, in ONE `tofu apply`):**

1. YC folder for infra artifacts
2. YC KMS key for state encryption
3. YC Object Storage bucket for state (versioning ON, KMS-encrypted)
4. YC YDB table `<tenant>-lock-table` with column `LockID (String)` as partition key — the state lock. **Provision via `yandex_ydb_table` resource, NOT via console UI.**
5. YC service account for GitLab CI federation, with the minimum IAM roles per environment
6. YC IAM workload identity federation binding to the GitLab issuer (`https://<gitlab-host>`) with subject match `project_path:<group>/<tenant>-infra`

The bootstrap module uses **local state** (`terraform { backend "local" {} }`). After apply:
- Commit the outputs (bucket name, KMS key ID, YDB table name, SA ID, federation subject) to `bootstrap/outputs.json` — this is what every stack references.
- The local `terraform.tfstate` from bootstrap is stored in **Lockbox** (`bootstrap-state`), not in git. If bootstrap ever needs re-apply: fetch state from Lockbox, run, push back.
- All subsequent stacks use the remote backend from step 3.

**Never** manually click in YC Console to create the lock table. **Never** commit bootstrap state to git. **Never** re-run bootstrap without fetching Lockbox state first — you will orphan the KMS key and lose the state bucket.

---

## Modules

- Live in a **separate GitLab project** per module (`<org>/terraform-modules/<name>`), one repo per module. NOT a mono-repo of modules.
- Published via **GitLab Terraform Module Registry** (native — set the project's Terraform module registry visibility, push a tagged commit, done).
- Pinned in stacks by **semver tag ONLY**:
  ```hcl
  module "k8s" {
    source  = "app.terraform.io/qantor/managed-kubernetes/yandex"
    version = "2.2.5"
    # ...
  }
  ```
- **Never** `?ref=main`, `?ref=v2`, git URL without tag. Renovate opens MRs when a new tag ships; humans review.
- Module MUST have: `main.tf`, `variables.tf`, `outputs.tf`, `versions.tf` (pinned provider constraints), `README.md`, `examples/basic/`, `tests/*.tftest.hcl`.
- Module MUST NOT: create resources outside its declared scope, hardcode tenant names, pull data via `terraform_remote_state` from another stack. Inputs come as variables.

Shape details in `terraform-module-library` skill. Style in `terraform-style-guide`. Tests in `terraform-test`.

---

## Blast-radius classification

Every plan lives on one of four tiers. **Tier determines who can apply and how.**

| Tier | Scope | Who applies | How |
|---|---|---|---|
| **T0 Bootstrap** | `bootstrap/` — folder, KMS, state bucket, YDB lock, IAM federation | Human only, laptop | Once per tenant. Never in CI. |
| **T1 Prod-destructive** | k8s cluster delete, DB delete, `on_delete` change on tenant FK, KMS key rotation, IAM role removal, bucket lifecycle change on prod bucket | Human only, protected env | Manual GitLab job on `main`, per-command confirmation in MR. Two reviewers. |
| **T2 Prod-safe** | non-destructive changes on prod stack — new module, added output, larger node group, new secret | GitLab CI manual job | Protected env, one reviewer, manual trigger. |
| **T3 Non-prod** | any change on dev/stage | GitLab CI auto-apply on merge | Merged MR → CI `tofu apply` runs on-push. |

**Classification is not the author's opinion — it's derived from the plan.** MR pipeline runs `tofu plan` and posts the tier as a comment based on resource actions detected (`-/+ replace`, `-delete`, IAM changes). Author overrides with justification if needed.

**A T1 plan without a REVIEW comment from a second engineer is not applied.** Ever.

---

## Secrets

- **Storage:** YC Lockbox, one payload per logical secret. No k8s Secret objects in git.
- **Consumption:** `external-secrets operator` in every cluster, `ExternalSecret` resource references a `SecretStore` bound to Lockbox via the platform SA.
- **App teams:** request via `ExternalSecret` in their Argo CD app manifest, never a raw k8s `Secret`.
- **CI:** GitLab masks values via CI variables — but the values themselves are set as CI variables from a Lockbox fetch step at pipeline start, not stored in GitLab.
- **Rotation:** Lockbox payload versions + external-secrets `refreshInterval: 1h`. Application redeploy triggered by `reloader` on annotation change.

Never: `SECRET_KEY = "..."` in Helm values. `sops` in git (deprecated for new envs — was a stopgap before Lockbox). Long-lived service account keys.

---

## CI/CD

Two pipelines:

### 1. Infra MR pipeline (on every push to feature branch)

Stages:
1. `pre-commit` — `tofu fmt -check`, `tflint`, `checkov`, `trivy config`
2. `validate` — `tofu validate` per stack
3. `plan` — `tofu plan -out=plan.tfplan` per changed stack, one job per env. Uploads plan artifact.
4. `plan-comment` — posts plan summary to MR via `glab mr note`. Classifies blast-radius, marks with 🟢 T3 / 🟡 T2 / 🔴 T1 / ⛔ T0.
5. `security` — checkov + tfsec against plan
6. `cost` — infracost or `yc-cost-estimator` (if wired), MR comment with cost delta

**MR cannot merge without:** clean plan, security = zero high-severity, human approval matching the blast tier.

### 2. Infra deploy pipeline (on merge to `main`)

- **T3 (dev/stage):** auto-apply
- **T2/T1 (prod):** manual jobs on protected environment. `apply` job downloads the plan artifact from the MR pipeline (same plan file, no re-plan → guarantees «what was reviewed is what applies»).
- Every apply logs to CI + posts back to the source MR: apply timestamp, tofu version, provider versions, resources changed.

Auth: GitLab OIDC → YC IAM federation. `id_tokens:` block in `.gitlab-ci.yml` binds a token audience to the tenant's YC federation issuer. Service account gets short-lived (10 min) token per job. **No** `YC_TOKEN` variable in GitLab. **No** SA key checked in.

Stanzas / caching / needs graph → `gitlab-ci-patterns` skill.

---

## GitOps for k8s

- Argo CD in every cluster, self-managed (Argo CD manages Argo CD via app-of-apps).
- Repo layout under `argocd/`:
  - `bootstrap/` — the root App-of-Apps, applied once via `kubectl apply` after cluster stand-up
  - `platform/` — cluster-wide operators (cert-manager, external-dns, external-secrets, reloader, kyverno, VictoriaMetrics stack)
  - `apps/` — ApplicationSet per team/service, drives multi-env via cluster generator or list generator
- **Sync policies:** automated with `prune: true` + `selfHeal: true` for non-prod. Manual sync for prod, but auto-detect drift (alert only).
- App containers built by app-team CI, image tag written to `argocd/apps/<app>/values.yaml` by their pipeline. Argo CD picks up the change.
- No `helm upgrade` from CI. No `kubectl apply` from CI past bootstrap.

Full Argo CD setup / debug in `gitops-workflow` skill.

---

## Crossplane for day-2 resource requests

Purpose: app teams shouldn't open an MR in `<tenant>-infra` to get a new Postgres DB. They should apply a Claim in their app repo and Crossplane provisions it.

- Platform team owns `crossplane/compositions/` — the templates that map a Claim (e.g. `PostgresDB`) to concrete YC resources.
- App team writes a Claim in their app manifest:
  ```yaml
  apiVersion: platform.qantor.io/v1alpha1
  kind: PostgresDB
  metadata:
    name: orders-db
  spec:
    parameters:
      sizeGB: 20
      version: "16"
  ```
- Argo CD applies it, Crossplane provisions via YC provider, publishes connection string to a Secret referenced by the app.
- Compositions enforce guardrails (allowed sizes, backup policy, tenant filter) that individual apps cannot bypass.

Compositions are still Terraform-equivalent — same review discipline, same blast-radius rules apply to changes in `crossplane/compositions/`. Changes to a Composition can trigger reconciliation on every Claim; treat as T2 minimum.

---

## Observability

- **Metrics:** VictoriaMetrics single-node for dev/stage, cluster for prod. Grafana Operator for dashboards.
- **Logs:** VictoriaLogs (replaced Loki 2025). App teams tag with `app_name` + `env`.
- **Traces:** OpenTelemetry Collector → VictoriaTraces (or Tempo if not yet in VM stack for this tenant).
- **Alerts:** vmalert rules in git, PromQL. Route via Alertmanager to on-call.
- **YC Monitoring:** opt-in for small envs where self-hosted VM is overkill.
- Never bake dashboards / alerts by hand in Grafana UI — everything as code under `argocd/platform/observability/`.

---

## New tenant onboarding — checklist

For a fresh YC tenant (e.g. new client bootstrap):

1. Create YC organization (or use an existing one; separate cloud is minimum).
2. Create GitLab group `<tenant>` and project `<tenant>-infra`. Enable Terraform Module Registry and protected environments.
3. Clone `template-tenant-infra` repo skeleton, replace tenant name, adjust `bootstrap/main.tf` inputs (folder name, KMS purpose, bucket name, SA name).
4. Locally: `cd bootstrap && tofu init && tofu apply`. Answer prompts. Store `terraform.tfstate` in Lockbox as `<tenant>-bootstrap-state`.
5. Commit `bootstrap/outputs.json` (public data) to git.
6. Enable GitLab OIDC federation with the outputs from step 4.
7. Push to `main`; CI runs plan for `stacks/platform/` (empty deploy on first run, but proves auth works).
8. Fill in `stacks/platform/components/` (VPC → k8s → PG → Redis → buckets). One MR per component, tier T3 auto-applies to dev.
9. Bootstrap Argo CD: `kubectl apply -f argocd/bootstrap/root-app.yaml`, wait for cluster-bootstrap apps to converge.
10. First app deploy via Argo CD ApplicationSet. Never a manual `helm install`.

Total time on a familiar template: ~2–3 hours to reach a running dev cluster with observability + secrets pipeline.

---

## Verification commands (`kb/verify.md` template)

Every infra repo's `kb/verify.md` includes:

```bash
# Local, before commit
tofu fmt -check -recursive
tofu validate            # per stack
tflint --recursive
checkov -d .
trivy config .

# Read-only plan preview
tofu plan -out=/tmp/plan.tfplan
tofu show -json /tmp/plan.tfplan | jq '.resource_changes | group_by(.change.actions[0]) | map({action: .[0].change.actions[0], count: length})'

# Drift check (scheduled pipeline, or on demand)
tofu plan -detailed-exitcode
# exit 0 = no drift, 2 = drift, non-zero != 2 = failure

# Argo CD state
argocd app list -o wide
argocd app diff <app>

# Crossplane
kubectl get compositions,claims,composed -A
```

---

## Never do

- **Never `?ref=main` on a module.** Semver tag or nothing.
- **Never apply on prod from a laptop.** Even T1. Especially T1.
- **Never store `terraform.tfstate` in git.** Not even bootstrap state. Lockbox or nothing.
- **Never store secrets in Helm values.** Lockbox + external-secrets.
- **Never manually click in YC Console** to create a resource that other resources depend on. If it's a dependency, it's in the bootstrap module or in a stack. UI operations are for one-off inspection, not provisioning.
- **Never `--auto-approve` in CI on any tier past T3.** T2/T1 = manual job with human trigger.
- **Never re-plan in the apply job.** Download the plan artifact from the MR pipeline. Re-planning defeats the review — the world can shift between MR review and merge.
- **Never mix tenants in one state file.** Different tenant → different repo → different state bucket → different KMS key.
- **Never let `helm upgrade` run outside Argo CD past bootstrap.** Argo CD owns k8s state; anything else is drift.
- **Never long-lived service account keys in GitLab CI variables.** OIDC federation only.
- **Never bypass Crossplane guardrails** by directly provisioning YC resources for an app team via MR. If a Composition is missing a size / region / feature, extend the Composition. Ad-hoc bypass = drift + tech debt.
- **Never skip the blast-radius classification** on a plan review. If the MR pipeline classification looks wrong, argue in the MR — don't silently override.
