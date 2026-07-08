# Hanzo Capability Manifest

The **canonical index** of every public Hanzo capability: one canonical name per
capability, grouped into eight categories, each with its `/v1/<name>` route
prefix and a one-line description. This file is authoritative — the OpenAPI
per-service specs, the cloud binary's mounted subsystems, and the console's
API client all reconcile to these names and groups. One name, one way.

**Rules**

- One canonical name per capability. No `svc` suffixes, no synonyms.
- Every route is `/v1/<name>/<resource>` (the `ai` inference surface is the one
  documented exception — see below).
- Categories are fixed: Identity, AI, Messaging, Observability, Commerce,
  Platform, Applications, Core.
- Internal infrastructure is **not** a public capability and never appears in the
  public spec (see "Internal" at the end).
- Backing column: the cloud subsystem id (`clients/<id>`) that mounts it, or the
  standalone deployment (`hanzoai/<svc>`) when it is not fused into the cloud
  binary. `(was /v1/x)` marks a canonical rename still cutting over.

---

## Identity

Who you are, what you may do, and the secrets/keys behind it.

| Capability | Route | What it does | Backing |
|---|---|---|---|
| `auth` | `/oauth/*`, `/.well-known/*`, `/login/oauth/*` | OAuth2 / OIDC login + token issuance (the identity **authentication** surface). | `clients/iamsvc` |
| `iam` | `/v1/iam` | Identity authority — orgs, users, apps, SCIM, adapters, OIDC discovery. | `clients/iamsvc` |
| `authz` | `/v1/authz` | Fine-grained per-org access-control policies + `check`. | `hanzoai/authz` |
| `security` | `/v1/security` | Org security posture + security-event surface. | cloud |
| `audit` | `/v1/audit` | Org-scoped, tamper-evident, hash-chained audit trail. | `clients/auditlog` |
| `wallets` | `/v1/wallets` | Custody / accounts / keys / sign (KMS single-sig + luxfi/mpc ring). | `clients/wallets` |
| `kms` | `/v1/kms` | Per-org, zero-knowledge secret store (embedded luxfi/kms). | `clients/kmssvc` |
| `zero-trust` | `/v1/zt` | Overlay networks, service mesh, edge nodes (OpenZiti fabric). | `clients/zt` |

## AI

Inference, agents, evaluation, and the DocType foundation.

| Capability | Route | What it does | Backing |
|---|---|---|---|
| `ai` | `/v1/chat/completions`, `/v1/completions`, `/v1/embeddings`, `/v1/models`, `/v1/rerank`, `/v1/messages` | OpenAI- and Claude-compatible inference. **Top-level** — the path is the SDK compatibility contract, so it is NOT under `/v1/ai`. | `hanzoai/ai` |
| `agents` | `/v1/agents` | Agent definitions + the live agent-session control plane. | `clients/agents` |
| `models` | `/v1/models`⁽ᵃ⁾ | Per-org deployed model serving (KServe InferenceServices). `(was /v1/ml)` | `clients/ml` |
| `evals` | `/v1/evals` | Evaluation scores, datasets, evaluators, runs. | `clients/eval` |
| `prompts` | `/v1/prompts` | Versioned prompt library. | `clients/prompts` |
| `functions` | `/v1/functions` | Serverless functions. | `clients/functions` |
| `exec` | `/v1/exec` | Code-Interpreter sandbox (exec / upload / download / files). | `clients/exec` |
| `framework` | `/v1/framework` | Metadata-driven DocType engine — the foundation CMS/ERP/CRM/Help build on. | `clients/framework` |
| `graph` | `/v1/graph` | Chain data — indexers + on-chain price/data oracles. | `clients/graph` |

⁽ᵃ⁾ Deployed-model serving lives on the org-namespaced `/v1/models`; the top-level
OpenAI-compat `/v1/models` LIST belongs to `ai`. Same path, disjoint scope — the
serving control-plane sub-paths (`/v1/models/:name/predict`) are unambiguous.

## Messaging

Move events, jobs, and notifications.

| Capability | Route | What it does | Backing |
|---|---|---|---|
| `pubsub` | `/v1/pubsub` | Embedded NATS + JetStream publish / subscribe. | `clients/pubsub` |
| `kafka` | `/v1/kafka` | Kafka-wire publish / consume adaptor. | `clients/kafka` |
| `tasks` | `/v1/tasks` | Durable task / workflow engine. | `clients/tasksvc` |
| `notify` | `/v1/notify` | Notification delivery. | `clients/notify` |

## Observability

See what the platform and your org are doing.

| Capability | Route | What it does | Backing |
|---|---|---|---|
| `o11y` | `/v1/o11y` | Logs / traces / metrics + alert rules (SigNoz runtime). | `hanzoai/o11y` |
| `metrics` | `/v1/metrics` | Process / runtime metrics. | `hanzoai/metrics` |
| `observe` | `/v1/o11y/{logs,metrics,status}`, `/v1/settings` | Org-scoped o11y read plane + console product-detail data plane. | `clients/observe` |
| `analytics` | `/v1/analytics` | Per-org warehouse analytics (LLM usage + web/commerce lenses). | `clients/analytics` |
| `usage` | `/v1/usage` | Cost roll-up (spend by category) + LLM usage totals. | `clients/usage` |
| `tracker` | `/v1/tracker` | Native issue tracker (projects + issues). | `clients/tracker` |

## Commerce

Money, plans, and growth loops.

| Capability | Route | What it does | Backing |
|---|---|---|---|
| `billing` | `/v1/billing` | Org-scoped billing reads (usage / balance). | `clients/billing` |
| `pricing` | `/v1/pricing` | Pricing catalog + feature-enablement registry. | `clients/pricing` |
| `plans` | `/v1/plans` | Subscription plans. | `clients/plan` |
| `treasury` | `/v1/finance` | Double-entry reserve fund + finance ledger of record. | `clients/treasury` |
| `referrals` | `/v1/referrals` | Viral-loop referral credit. | `clients/referrals` |
| `affiliates` | `/v1/affiliates` | Partner-commission loop. | `clients/affiliates` |
| `licensing` | `/v1/licensing` | Engine license issuance / validation. | `hanzoai/licensing` |
| `crm` | `/v1/crm` | Native CRM (companies / contacts / opportunities). | `clients/crm` |
| `product` | `/v1/product` | Product catalog / registry. | `clients/product` |

## Platform

The substrate: provision resources, deploy apps, route the edge.

| Capability | Route | What it does | Backing |
|---|---|---|---|
| `platform` | `/v1/platform` | Per-org container-app PaaS (projects / apps / deploy). | `clients/platform` |
| `paas` | `/v1/paas` | Admin fleet deploy board (operator Service CRs). | `clients/paas` |
| `provisioning` | `/v1/{sql,vector,datastore,kv,search,docdb,storage,vpcs,load-balancers}` | Managed data resources + DO-native VPCs / load-balancers. | `clients/provisioning`, `clients/do` |
| `gateway` | `api.hanzo.ai` | API gateway + LLM router (edge; routes to this binary). | `hanzoai/gateway` |
| `ingress` | `/v1/ingress` | Runtime edge — routes / TLS / ACME / middlewares. | `clients/ingress` |
| `visor` | `/v1/visor`, `/v1/{machines,gpus,clusters}` | Compute inventory — machines / GPUs / clusters. | `clients/visor` |
| `fleet` | `/v1/visor/clusters` | BYO-cluster registry (kubeconfig fabric under visor). | `clients/fleet` |
| `base` | `/v1/collections` | Embedded Hanzo Base — collections / records store. | `hanzoai/base` |

## Applications

The products users open.

| Capability | Route | What it does | Backing |
|---|---|---|---|
| `console` | `/v1/console` | Cloud API-key mint/revoke + org onboarding. | `clients/console` |
| `team` | `/v1/team` | Team workspace read-plane + bots-as-members. | `clients/team` |
| `projects` | `/v1/projects` | Buildable / deployable projects (artifact/git → S3 → live URL). | `clients/projects` |
| `git` | `/v1/git` | Git repositories surface. | `clients/git` |
| `templates` | `/v1/templates` | Starter-kit gallery. | `clients/templates` |
| `integrations` | `/v1/integrations` | Provider-agnostic OAuth connector framework. | `clients/integrations` |
| `bot` | `/v1/bot` | Bot gateway (reverse proxy → bot-gateway). | `clients/bot` |
| `world` | `/v1/world` | News data plane (GDELT + allowlisted RSS). | `clients/world` |
| `knowledge` | `/v1/knowledge`⁽ᵇ⁾ | Knowledge base + unified AI memory (wiki tree + vector). `(was /v1/kb)` | `clients/kb` |
| `search` | `/v1/search`⁽ᵇ⁾ | Web meta-search + scrape (SearXNG + Crawl4AI). `(was /v1/websearch)` | `clients/websearch` |
| `storage` | `/v1/storage`⁽ᵇ⁾ | Org object-storage file manager (buckets / objects). `(was /v1/s3)` | `clients/s3` |
| `authors` | `/v1/authors` | OSS-author royalty loop. | `clients/authors` |
| `automations` | `/v1/automations` | Connectors + flows engine (706-connector catalog). | `clients/automations` |
| `sites` | (Host-based) | Published-site edge — served by Host; its control plane is `/v1/projects`. | `clients/sites` |
| `cms` | (on `framework`) | Content-types as DocTypes. No bespoke REST — documents live on `/v1/framework`. | `clients/cms` |
| `erp` | (on `framework`) | ERPNext DocTypes + business hooks. No bespoke REST — on `/v1/framework`. | `clients/erp` |
| `help` | (on `framework`) | Helpdesk DocTypes. No bespoke REST — documents on `/v1/framework`. | `clients/help` |

⁽ᵇ⁾ Canonical rename in progress (kb→knowledge, websearch→search, s3→storage);
the old route is preserved as an alias during cutover.

## Core

Platform-wide primitives.

| Capability | Route | What it does | Backing |
|---|---|---|---|
| `admin` | `/v1/admin` | Platform SuperAdmin cross-tenant control plane (the god view). | `clients/admin` |
| `plugins` | `/v1/plugins` | Runtime WASM / proxy plugins. | `clients/plugin` |

---

## Internal — NOT public capabilities

These are trust boundaries and runtime hosts with **no public API surface**. They
must never appear in the public spec, the capability manifest, or a client's
known-heads list.

| Internal | Why it is not a capability |
|---|---|
| `principal` | Tenant-resolution trust boundary — a middleware seam, not a mountable surface. |
| `goja` | JavaScript runtime host for base-embedded node services — an execution host. |
| `mpc` | Threshold sealing / signing ring — reached only via `wallets`, never directly. |
| `controlplane` | Build-tagged consensus simulation — off in production builds. |

---

*Reconciliation note.* The per-service specs under `<service>/openapi.yaml` are
the historical, hand-authored set and are being reconciled to the capability
names above. Where a spec's directory still uses a legacy name (`ml`, `s3`,
`zt`, `mq`, …), the canonical name in this manifest is the target. The master
`hanzo.yaml` groups every present tag into these categories via `x-tagGroups`.
