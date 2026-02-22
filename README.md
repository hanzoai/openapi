# Hanzo Cloud API

One API key. One gateway. 26 services.

```bash
curl -H "Authorization: Bearer hk-your-api-key" https://api.hanzo.ai/v1/models
```

```python
from hanzo import Hanzo
client = Hanzo(api_key="hk-your-api-key")
```

**Version 4.0.0** — [api.hanzo.ai](https://api.hanzo.ai) — [docs.hanzo.ai](https://docs.hanzo.ai)

---

## What is Hanzo Cloud?

Hanzo Cloud is a unified AI infrastructure platform. Every service — from LLM inference to databases to DNS — is accessible through a single API gateway at `api.hanzo.ai` with a single API key. All services share identity (Hanzo IAM), secrets (Hanzo KMS), and multi-tenant isolation.

Think: AWS + Vercel + Heroku, but unified under one auth system with AI-native primitives built in.

---

## Services

### AI & Intelligence

| Service | Endpoint | What it does |
|---------|----------|--------------|
| **Cloud** | `api.cloud.hanzo.ai` | LLM inference API — 86+ models (OpenAI, Anthropic, open-source), usage tracking |
| **Chat** | `hanzo.chat` | Multi-model AI chat with MCP tools, agents, assistants, RAG |
| **Search** | `search.hanzo.ai` | Typo-tolerant full-text search with faceted filtering |
| **Bot** | `app.hanzo.bot` | Bot framework with 743 skills and plugin marketplace |
| **Nexus** | `nexus.hanzo.ai` | Knowledge base — document management, embeddings, semantic Q&A |
| **Vector** | `vector.hanzo.ai` | Vector database — collections, similarity search, hybrid retrieval |

### Automation & Workflows

| Service | Endpoint | What it does |
|---------|----------|--------------|
| **Flow** | `flow.hanzo.ai` | Visual workflow builder — drag-and-drop, 600+ integrations |
| **Auto** | `auto.hanzo.ai` | Trigger-based automations, cron jobs, scheduled tasks |
| **Operative** | `operative.hanzo.ai` | Computer use — AI controls a desktop via screenshot/mouse/keyboard |

### Platform & Identity

| Service | Endpoint | What it does |
|---------|----------|--------------|
| **IAM** | `hanzo.id` | Identity — OAuth2, OIDC, SAML, Web3 login, MFA, org management |
| **Commerce** | `commerce.hanzo.ai` | Billing — payments, invoicing, subscriptions, usage metering |
| **Gateway** | `api.hanzo.ai` | Unified API proxy — routing, rate limiting, CDN, spend tracking |
| **Console** | `console.hanzo.ai` | Observability — LLM traces, scores, prompt versioning, datasets |
| **KMS** | `kms.hanzo.ai` | Secrets — API keys, certificates, encryption, dynamic secrets |
| **Analytics** | `analytics.hanzo.ai` | Web analytics — pageviews, events, sessions, reports |

### Infrastructure

| Service | Endpoint | What it does |
|---------|----------|--------------|
| **PaaS** | `paas.hanzo.ai` | K8s-native deployments — GitOps, per-org clusters, fleet management |
| **Platform** | `platform.hanzo.ai` | Local dev PaaS — Docker-based deployments for development |
| **DB** | `db.hanzo.ai` | Serverless Postgres — instant branching, autoscaling, point-in-time restore |
| **KV** | `kv.hanzo.ai` | Key-value store — caching, TTL, pub/sub channels, streams |
| **MQ** | `mq.hanzo.ai` | Message queue — pub/sub, durable streams, request/reply, KV buckets |
| **Edge** | `edge.hanzo.ai` | Edge functions — deploy TypeScript/JS globally, zero cold starts |
| **Registry** | `registry.hanzo.ai` | Container registry — image storage, vulnerability scanning, webhooks |
| **Visor** | `vm.hanzo.ai` | VM management — cloud instances, remote desktop (RDP/SSH) |

### Operations

| Service | Endpoint | What it does |
|---------|----------|--------------|
| **Engine** | `engine.hanzo.ai` | GPU scheduling — ML training jobs, Ray clusters, model serving |
| **O11y** | `o11y.hanzo.ai` | Observability — logs (LogQL), metrics (PromQL), distributed traces, alerts |
| **DNS** | `dns.hanzo.ai` | DNS hosting — zones, records, DNSSEC, query analytics |
| **ZT** | `zt.hanzo.ai` | Zero-trust networking — identity-based overlay mesh, no open ports |

---

## Gateway Routes

Every service is accessible through `api.hanzo.ai`:

```
# AI
api.hanzo.ai/v1/chat/completions   → Cloud (LLM inference)
api.hanzo.ai/v1/models             → Cloud (model listing)
api.hanzo.ai/v1/chat/*             → Chat
api.hanzo.ai/v1/search/*           → Search
api.hanzo.ai/v1/bot/*              → Bot
api.hanzo.ai/v1/nexus/*            → Nexus (knowledge base)
api.hanzo.ai/v1/vector/*           → Vector DB

# Automation
api.hanzo.ai/v1/flow/*             → Flow (workflows)
api.hanzo.ai/v1/operative/*        → Operative (computer use)

# Platform
api.hanzo.ai/v1/auth/*             → IAM
api.hanzo.ai/v1/billing/*          → Commerce
api.hanzo.ai/v1/kms/*              → KMS
api.hanzo.ai/v1/console/*          → Console
api.hanzo.ai/v1/analytics/*        → Analytics

# Infrastructure
api.hanzo.ai/v1/paas/*             → PaaS
api.hanzo.ai/v1/platform/*         → Platform
api.hanzo.ai/v1/db/*               → DB (Postgres)
api.hanzo.ai/v1/kv/*               → KV
api.hanzo.ai/v1/mq/*               → MQ
api.hanzo.ai/v1/edge/*             → Edge (functions)
api.hanzo.ai/v1/registry/*         → Registry
api.hanzo.ai/v1/vm/*               → Visor (VMs)

# Operations
api.hanzo.ai/v1/engine/*           → Engine (GPU/ML)
api.hanzo.ai/v1/o11y/*             → O11y
api.hanzo.ai/v1/dns/*              → DNS
api.hanzo.ai/v1/zt/*               → ZT (zero trust)
```

---

## Authentication

All services use a single `HANZO_API_KEY`:

```bash
curl -H "Authorization: Bearer hk-your-api-key" https://api.hanzo.ai/v1/models
```

Get your API key at [hanzo.id](https://hanzo.id) or [console.hanzo.ai](https://console.hanzo.ai).

### Auth Methods

| Method | Use Case | How |
|--------|----------|-----|
| **API Key** | Server-to-server, scripts | `Authorization: Bearer hk-...` |
| **OAuth2 + PKCE** | User-facing apps | `hanzo.id/login/oauth/authorize` |
| **Client Credentials** | Service-to-service | `POST hanzo.id/api/login/oauth/access_token` |
| **JWT** | After OAuth login | `Authorization: Bearer eyJ...` |

---

## Architecture

### Multi-Tenancy

Every resource is scoped by `org_id` from the IAM token. Tenant isolation is enforced at the gateway, service, and database layers. No cross-tenant access is possible.

### Unified Identity (Hanzo IAM)

No service has its own login in production. All authentication flows through `hanzo.id` via OAuth2/OIDC. JWT tokens carry org and role claims. One login, all services.

### Secrets (Hanzo KMS)

All credentials, TLS certs, and connection strings are managed by `kms.hanzo.ai`. The KMS Operator syncs secrets into K8s namespaces. No hardcoded secrets in production.

### ZAP Protocol

All services implement ZAP (Zero-knowledge Attestation Protocol) for end-to-end verifiable data integrity — cryptographic attestation from database writes through API responses. See [github.com/hanzoai/zap](https://github.com/hanzoai/zap).

### Deployment

All services deploy via Hanzo PaaS on per-org DOKS clusters with GitOps, fleet management, and autoscaling.

---

## SDKs & Client Libraries

### Official SDKs

```bash
pip install hanzo          # Python
npm install @hanzo/sdk     # TypeScript/Node
go get github.com/hanzoai/go-sdk  # Go
```

### Generate from OpenAPI

```bash
# Python
openapi-generator generate -i hanzo.yaml -g python -o clients/python

# TypeScript
openapi-generator generate -i hanzo.yaml -g typescript-axios -o clients/typescript

# Go
openapi-generator generate -i hanzo.yaml -g go -o clients/go

# Rust
openapi-generator generate -i hanzo.yaml -g rust -o clients/rust
```

### NPM Packages

| Package | Description |
|---------|-------------|
| `@hanzo/sdk` | Unified client for all Hanzo services |
| `@hanzo/kv` | Key-value store client |
| `@hanzo/mq` | Message queue client |
| `@hanzo/pubsub` | Pub/sub and streaming client |

---

## OpenAPI Specs

Every service has a complete OpenAPI 3.1.0 specification:

```
openapi/
├── hanzo.yaml              # Master unified spec (all 26 services)
├── shared/
│   ├── errors.yaml         # Shared error responses
│   ├── pagination.yaml     # Pagination schemas
│   └── auth.yaml           # Auth schemas
│
├── iam/openapi.yaml        # Identity & auth
├── commerce/openapi.yaml   # Billing & payments
├── cloud/openapi.yaml      # AI model API
├── gateway/openapi.yaml    # API gateway
├── console/openapi.yaml    # Observability
├── kms/openapi.yaml        # Secrets management
│
├── chat/openapi.yaml       # AI chat
├── flow/openapi.yaml       # Workflows
├── auto/openapi.yaml       # Automations
├── analytics/openapi.yaml  # Web analytics
├── bot/openapi.yaml        # Bot framework
├── search/openapi.yaml     # Full-text search
│
├── paas/openapi.yaml       # K8s PaaS
├── platform/openapi.yaml   # Local dev PaaS
├── visor/openapi.yaml      # VM management
├── operative/openapi.yaml  # Computer use
├── vector/openapi.yaml     # Vector database
├── nexus/openapi.yaml      # Knowledge base / RAG
├── registry/openapi.yaml   # Container registry
├── db/openapi.yaml         # Serverless Postgres
├── edge/openapi.yaml       # Edge functions
├── kv/openapi.yaml         # Key-value store
├── mq/openapi.yaml         # Message queue
│
├── engine/openapi.yaml     # GPU / ML pipelines
├── o11y/openapi.yaml       # Logs, metrics, traces
├── dns/openapi.yaml        # DNS management
└── zt/openapi.yaml         # Zero-trust networking
```

### Validate

```bash
# All specs
for spec in */openapi.yaml; do
  echo "Validating $spec..."
  openapi-generator validate -i "$spec"
done

# Master spec
npx @redocly/cli lint hanzo.yaml
```

### Serve Docs Locally

```bash
npx @redocly/cli preview-docs hanzo.yaml           # Redoc
npx @scalar/cli serve hanzo.yaml                    # Scalar
docker run -p 8080:8080 -e SWAGGER_JSON=/specs/hanzo.yaml \
  -v $(pwd):/specs swaggerapi/swagger-ui             # Swagger UI
```

---

## Open Source

Hanzo Cloud is built on world-class open-source infrastructure:

| GitHub Org | Focus | Key Projects |
|------------|-------|-------------|
| [@hanzoai](https://github.com/hanzoai) | Core platform | All 26 services |
| [@hanzozt](https://github.com/hanzozt) | Zero-trust networking | 79 repos |
| [@hanzo-ml](https://github.com/hanzo-ml) | GPU/ML | kubeflow, kuberay |
| [@hanzodns](https://github.com/hanzodns) | DNS | coredns |
| [@hanzofn](https://github.com/hanzofn) | Edge functions | edge-runtime |
| [@hanzosql](https://github.com/hanzosql) | Databases | neon |
| [@hanzokv](https://github.com/hanzokv) | Key-value store | valkey |
| [@hanzocr](https://github.com/hanzocr) | Container registry | harbor |
| [@hanzomsg](https://github.com/hanzomsg) | Messaging | nats-server, nats.go, nats.js, nats.py |
| [@hanzoo11y](https://github.com/hanzoo11y) | Observability | loki, grafana, signoz |

---

Copyright 2024-2026 Hanzo AI, Inc. All rights reserved.
