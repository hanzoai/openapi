# Hanzo OpenAPI Specifications

Unified OpenAPI specifications for ALL Hanzo services. Single `HANZO_API_KEY` for everything via `api.hanzo.ai`.

**Version**: 4.0.0 — Hanzo Unified Cloud

## Services (26)

### Core

| Service | Version | Spec | Endpoint | Description |
|---------|---------|------|----------|-------------|
| **IAM** | 1.503.0 | `iam/openapi.yaml` | `hanzo.id` | Identity, auth, OAuth2/OIDC/SAML/Web3 |
| **Commerce** | 1.0.0 | `commerce/openapi.yaml` | `commerce.hanzo.ai` | Billing, payments, invoicing, orders, subscriptions |
| **Cloud** | 1.70.0 | `cloud/openapi.yaml` | `api.cloud.hanzo.ai` | AI model API (86+ models), usage tracking |
| **Gateway** | 1.1.0 | `gateway/openapi.yaml` | `api.hanzo.ai` | Unified API proxy, LLM routing, CDN, edge routing |
| **Console** | 1.0.0 | `console/openapi.yaml` | `console.hanzo.ai` | Observability, traces, scores, prompts |
| **KMS** | 1.0.0 | `kms/openapi.yaml` | `kms.hanzo.ai` | Secrets management, encryption, audit |

### Application

| Service | Version | Spec | Endpoint | Description |
|---------|---------|------|----------|-------------|
| **Chat** | 1.0.0 | `chat/openapi.yaml` | `hanzo.chat` | AI chat, conversations, messages |
| **Flow** | 1.0.0 | `flow/openapi.yaml` | `flow.hanzo.ai` | Visual workflow builder, automations |
| **Auto** | 1.0.0 | `auto/openapi.yaml` | `auto.hanzo.ai` | Workflow automation, scheduling |
| **Analytics** | 1.0.0 | `analytics/openapi.yaml` | `analytics.hanzo.ai` | Web analytics, events, sessions |
| **Bot** | 1.0.0 | `bot/openapi.yaml` | `app.hanzo.bot` | Bot framework, 743 skills |
| **Search** | 1.0.0 | `search/openapi.yaml` | `search.hanzo.ai` | AI-powered search, generative UI |

### Infrastructure

| Service | Version | Spec | Endpoint | Org | Description |
|---------|---------|------|----------|-----|-------------|
| **PaaS** | 1.0.0 | `paas/openapi.yaml` | `paas.hanzo.ai` | @hanzoai | K8s-native GitOps, cluster management |
| **Platform** | 1.0.0 | `platform/openapi.yaml` | `platform.hanzo.ai` | @hanzoai | Local dev PaaS, Docker deployments |
| **Visor** | 1.0.0 | `visor/openapi.yaml` | `vm.hanzo.ai` | @hanzoai | VM management, cloud instances |
| **Operative** | 1.0.0 | `operative/openapi.yaml` | `operative.hanzo.ai` | @hanzoai | Computer use, browser automation |
| **Vector** | 1.0.0 | `vector/openapi.yaml` | `vector.hanzo.ai` | @hanzoai | Vector database, collections, search |
| **Nexus** | 1.70.0 | `nexus/openapi.yaml` | `nexus.hanzo.ai` | @hanzoai | Knowledge base, RAG, embeddings |
| **Registry** | 1.0.0 | `registry/openapi.yaml` | `registry.hanzo.ai` | @hanzocr | Container registry |
| **DB** | 1.0.0 | `db/openapi.yaml` | `db.hanzo.ai` | @hanzosql | Serverless Postgres, instant branching |
| **Edge** | 1.0.0 | `edge/openapi.yaml` | `edge.hanzo.ai` | @hanzofn | Edge functions, Deno-based serverless |
| **KV** | 1.0.0 | `kv/openapi.yaml` | `kv.hanzo.ai` | @hanzokv | Key-value store, caching |
| **MQ** | 1.0.0 | `mq/openapi.yaml` | `mq.hanzo.ai` | @hanzomsg | Message queue, pub/sub, streams (NATS) |

### Operations

| Service | Version | Spec | Endpoint | Org | Description |
|---------|---------|------|----------|-----|-------------|
| **Engine** | 1.0.0 | `engine/openapi.yaml` | `engine.hanzo.ai` | @hanzo-ml | GPU scheduling, ML pipelines, model serving |
| **O11y** | 1.0.0 | `o11y/openapi.yaml` | `o11y.hanzo.ai` | @hanzoo11y | Logs, metrics, traces, alerts |
| **DNS** | 1.0.0 | `dns/openapi.yaml` | `dns.hanzo.ai` | @hanzodns | DNS zones, records, DNSSEC |
| **ZT** | 1.0.0 | `zt/openapi.yaml` | `zt.hanzo.ai` | @hanzozt | Zero-trust networking, overlay mesh |

## Platform Capabilities

Full Heroku/Vercel parity and beyond:

| Capability | Service | Spec | Org | Status |
|---|---|---|---|---|
| AI Model API (86+ providers) | Cloud | `cloud/openapi.yaml` | @hanzoai | Existing |
| Unified API Gateway | Gateway | `gateway/openapi.yaml` | @hanzoai | Updated |
| Identity & Auth (OAuth2/OIDC/SAML/Web3) | IAM | `iam/openapi.yaml` | @hanzoai | Existing |
| Billing & Metering | Commerce | `commerce/openapi.yaml` | @hanzoai | Existing |
| Build System (Nixpacks) | PaaS | `paas/openapi.yaml` | @hanzoai | **NEW** |
| Container Registry | Registry | `registry/openapi.yaml` | @hanzocr | **NEW** |
| Managed Databases (Serverless Postgres) | DB | `db/openapi.yaml` | @hanzosql | **NEW** |
| Key-Value Store / Caching | KV | `kv/openapi.yaml` | @hanzokv | **NEW** |
| Edge Functions (Deno) | Edge | `edge/openapi.yaml` | @hanzofn | **NEW** |
| Cron / Scheduled Jobs | Auto | `auto/openapi.yaml` | @hanzoai | Existing |
| Log Aggregation / SIEM | O11y | `o11y/openapi.yaml` | @hanzoo11y | **NEW** |
| Metrics / APM | O11y | `o11y/openapi.yaml` | @hanzoo11y | **NEW** |
| DNS Management | DNS | `dns/openapi.yaml` | @hanzodns | **NEW** |
| CDN | Gateway | `gateway/openapi.yaml` | @hanzoai | Updated |
| Message Queue / Pub-Sub | MQ | `mq/openapi.yaml` | @hanzomsg | **NEW** |
| GPU Scheduling / ML Pipelines | Engine | `engine/openapi.yaml` | @hanzo-ml | **NEW** |
| Zero Trust Networking | ZT | `zt/openapi.yaml` | @hanzozt | **NEW** |
| VM Management | Visor | `visor/openapi.yaml` | @hanzoai | Existing |
| Computer Use / Automation | Operative | `operative/openapi.yaml` | @hanzoai | Existing |
| Vector Database | Vector | `vector/openapi.yaml` | @hanzoai | Existing |
| Knowledge Base / RAG | Nexus | `nexus/openapi.yaml` | @hanzoai | Existing |
| AI Chat | Chat | `chat/openapi.yaml` | @hanzoai | Existing |
| Workflow Automation | Flow | `flow/openapi.yaml` | @hanzoai | Existing |
| Bot Framework (743 skills) | Bot | `bot/openapi.yaml` | @hanzoai | Existing |
| AI Search (Generative UI) | Search | `search/openapi.yaml` | @hanzoai | Existing |
| Secrets Management | KMS | `kms/openapi.yaml` | @hanzoai | Existing |
| Observability / Tracing | Console | `console/openapi.yaml` | @hanzoai | Existing |

## GitHub Organizations

| Org | Purpose | Upstream Forks |
|-----|---------|----------------|
| [@hanzoai](https://github.com/hanzoai) | Core platform | — |
| [@hanzozt](https://github.com/hanzozt) | Zero-trust networking | OpenZiti (79 repos) |
| [@hanzo-ml](https://github.com/hanzo-ml) | GPU/ML infrastructure | kubeflow, kuberay |
| [@hanzodns](https://github.com/hanzodns) | DNS management | coredns |
| [@hanzofn](https://github.com/hanzofn) | Edge functions | supabase/edge-runtime |
| [@hanzosql](https://github.com/hanzosql) | Serverless Postgres | neondatabase/neon |
| [@hanzokv](https://github.com/hanzokv) | Key-value store | valkey-io/valkey |
| [@hanzocr](https://github.com/hanzocr) | Container registry | goharbor/harbor |
| [@hanzomsg](https://github.com/hanzomsg) | Messaging (MQ + Pub/Sub) | nats-io/nats-server, nats.go, nats.js, nats.py |
| [@hanzoo11y](https://github.com/hanzoo11y) | Observability | grafana/loki, grafana/grafana, SigNoz/signoz |

## Directory Structure

```
openapi/
├── README.md              # This file
├── hanzo.yaml             # Master unified spec (v4.0.0, OpenAPI 3.1.0)
├── shared/
│   ├── errors.yaml        # Shared error responses
│   ├── pagination.yaml    # Pagination schemas
│   └── auth.yaml          # Auth schemas
│
│   # Core (6)
├── iam/openapi.yaml
├── commerce/openapi.yaml
├── cloud/openapi.yaml
├── gateway/openapi.yaml
├── console/openapi.yaml
├── kms/openapi.yaml
│
│   # Application (6)
├── chat/openapi.yaml
├── flow/openapi.yaml
├── auto/openapi.yaml
├── analytics/openapi.yaml
├── bot/openapi.yaml
├── search/openapi.yaml
│
│   # Infrastructure (10)
├── paas/openapi.yaml       # NEW — K8s-native PaaS
├── platform/openapi.yaml
├── visor/openapi.yaml
├── operative/openapi.yaml
├── vector/openapi.yaml
├── nexus/openapi.yaml
├── registry/openapi.yaml   # NEW — Container registry
├── db/openapi.yaml         # NEW — Serverless Postgres
├── edge/openapi.yaml       # NEW — Edge functions
├── kv/openapi.yaml         # NEW — Key-value store
├── mq/openapi.yaml         # NEW — Message queue / pub-sub
│
│   # Operations (4)
├── engine/openapi.yaml     # NEW — GPU/ML
├── o11y/openapi.yaml       # NEW — Observability
├── dns/openapi.yaml        # NEW — DNS management
└── zt/openapi.yaml         # NEW — Zero trust
```

## Authentication

All services use a single `HANZO_API_KEY`:

```bash
# Using curl
curl -H "Authorization: Bearer hk-your-api-key" https://api.hanzo.ai/v1/models

# Using the Hanzo SDK
from hanzo import Hanzo
client = Hanzo(api_key="hk-your-api-key")
```

API keys are managed at [hanzo.id](https://hanzo.id) or [console.hanzo.ai](https://console.hanzo.ai).

## Unified API Gateway

All 26 services accessible through `api.hanzo.ai`:

```
# Core
api.hanzo.ai/v1/chat/completions    → Cloud API (AI models)
api.hanzo.ai/v1/models              → Cloud API (model listing)
api.hanzo.ai/v1/billing/*           → Commerce (billing/usage)
api.hanzo.ai/v1/auth/*              → IAM (identity)
api.hanzo.ai/v1/kms/*               → KMS (secrets)
api.hanzo.ai/v1/console/*           → Console (observability)

# Application
api.hanzo.ai/v1/analytics/*         → Analytics
api.hanzo.ai/v1/search/*            → Search
api.hanzo.ai/v1/flow/*              → Flow (workflows)
api.hanzo.ai/v1/bot/*               → Bot framework
api.hanzo.ai/v1/chat/*              → Chat

# Infrastructure
api.hanzo.ai/v1/paas/*              → PaaS (GitOps deployments)
api.hanzo.ai/v1/platform/*          → Platform (local dev)
api.hanzo.ai/v1/vm/*                → Visor (VMs)
api.hanzo.ai/v1/operative/*         → Operative (computer use)
api.hanzo.ai/v1/vector/*            → Vector DB
api.hanzo.ai/v1/nexus/*             → Nexus (knowledge base)
api.hanzo.ai/v1/registry/*          → Registry (containers)
api.hanzo.ai/v1/db/*                → DB (Postgres)
api.hanzo.ai/v1/edge/*              → Edge (functions)
api.hanzo.ai/v1/kv/*                → KV (key-value store)
api.hanzo.ai/v1/mq/*                → MQ (message queue / pub-sub)

# Operations
api.hanzo.ai/v1/engine/*            → Engine (GPU/ML)
api.hanzo.ai/v1/o11y/*              → O11y (observability)
api.hanzo.ai/v1/dns/*               → DNS
api.hanzo.ai/v1/zt/*                → ZT (zero trust)
```

## Platform Architecture

### Multi-Tenancy

All services are **multi-tenant** in production. Every resource is scoped by `org_id` derived from the authenticated IAM token. Tenant isolation is enforced at the API gateway, service, and database layers. No cross-tenant data leakage is possible.

### Unified Authentication (Hanzo IAM)

Every service authenticates via **Hanzo IAM** (`hanzo.id`). No service runs its own login system in production. All apps use OAuth2/OIDC via `hanzo.id/login/oauth/authorize`. Local development may use standalone auth, but production always goes through IAM.

- OAuth2 Authorization Code + PKCE for user-facing apps
- Client Credentials for service-to-service
- JWT tokens with org/role claims
- Single `HANZO_API_KEY` for API access

### Secrets Management (Hanzo KMS)

All secrets, credentials, TLS certificates, and connection strings are managed via **Hanzo KMS** (`kms.hanzo.ai`). Services never store secrets in environment variables or config files in production. The KMS Operator (`ghcr.io/hanzoai/kms-operator`) syncs secrets into K8s namespaces automatically.

### ZAP Protocol

All services implement the **ZAP** (Zero-knowledge Attestation Protocol) for end-to-end verifiable data integrity. ZAP provides cryptographic attestation from database writes through API responses, enabling trustless verification of all platform operations across every service boundary. See [github.com/hanzoai/zap](https://github.com/hanzoai/zap).

### PaaS-Managed Deployment

All core cloud services are deployed and managed via **Hanzo PaaS** (`paas.hanzo.ai`). Services run on per-org DOKS clusters with fleet management, automated scaling, and GitOps-driven continuous deployment.

### NPM Packages

| Package | Service | Description |
|---------|---------|-------------|
| `@hanzo/kv` | KV | Key-value store client |
| `@hanzo/mq` | MQ | Message queue client (NATS) |
| `@hanzo/pubsub` | MQ | Pub/sub client (NATS JetStream) |

## Generate Clients

```bash
# Python client
openapi-generator generate -i hanzo.yaml -g python -o clients/python

# TypeScript client
openapi-generator generate -i hanzo.yaml -g typescript-axios -o clients/typescript

# Go client
openapi-generator generate -i hanzo.yaml -g go -o clients/go

# Rust client
openapi-generator generate -i hanzo.yaml -g rust -o clients/rust
```

## Validate

```bash
# Validate all specs
for spec in */openapi.yaml; do
  echo "Validating $spec..."
  openapi-generator validate -i "$spec"
done

# Validate master spec
npx @redocly/cli lint hanzo.yaml
```

## Serve Documentation

```bash
# Redoc (recommended)
npx @redocly/cli preview-docs hanzo.yaml

# Swagger UI
docker run -p 8080:8080 -e SWAGGER_JSON=/specs/hanzo.yaml \
  -v $(pwd):/specs swaggerapi/swagger-ui

# Scalar (modern alternative)
npx @scalar/cli serve hanzo.yaml
```

## License

Copyright 2024-2026 Hanzo AI, Inc. All rights reserved.
