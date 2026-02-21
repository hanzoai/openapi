# Hanzo OpenAPI Specifications

Unified OpenAPI specifications for ALL Hanzo services. Single `HANZO_API_KEY` for everything via `api.hanzo.ai`.

## Services

### Core

| Service | Version | Spec | Endpoint | Description |
|---------|---------|------|----------|-------------|
| **IAM** | 1.503.0 | `iam/openapi.yaml` | `hanzo.id` | Identity, auth, OAuth2/OIDC/SAML/Web3 |
| **Commerce** | 1.0.0 | `commerce/openapi.yaml` | `commerce.hanzo.ai` | Billing, payments, invoicing, orders, subscriptions |
| **Cloud** | 1.70.0 | `cloud/openapi.yaml` | `api.cloud.hanzo.ai` | AI model API (86+ models), usage tracking |
| **Gateway** | 1.0.0 | `gateway/openapi.yaml` | `api.hanzo.ai` | Unified API proxy, LLM routing, rate limiting |
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

| Service | Version | Spec | Endpoint | Description |
|---------|---------|------|----------|-------------|
| **Platform** | 1.0.0 | `platform/openapi.yaml` | `platform.hanzo.ai` | PaaS, deployments, containers |
| **Visor** | 1.0.0 | `visor/openapi.yaml` | `vm.hanzo.ai` | VM management, cloud instances |
| **Operative** | 1.0.0 | `operative/openapi.yaml` | `operative.hanzo.ai` | Computer use, browser automation |
| **Vector** | 1.0.0 | `vector/openapi.yaml` | `vector.hanzo.ai` | Vector database, collections, search |
| **Nexus** | 1.70.0 | `nexus/openapi.yaml` | `nexus.hanzo.ai` | Knowledge base, RAG, embeddings |

## Directory Structure

```
openapi/
├── README.md              # This file
├── hanzo.yaml             # Master unified spec (OpenAPI 3.1.0)
├── shared/
│   ├── errors.yaml        # Shared error responses
│   ├── pagination.yaml    # Pagination schemas
│   └── auth.yaml          # Auth schemas
├── iam/openapi.yaml       # → ../../iam/swagger/swagger.yml
├── commerce/openapi.yaml  # → ../../commerce/openapi.yaml
├── cloud/openapi.yaml     # → ../../cloud/swagger/swagger.yml
├── nexus/openapi.yaml     # → ../../nexus/swagger/swagger.yml
├── gateway/openapi.yaml
├── vector/openapi.yaml
├── chat/openapi.yaml
├── analytics/openapi.yaml
├── flow/openapi.yaml
├── auto/openapi.yaml
├── bot/openapi.yaml
├── search/openapi.yaml
├── kms/openapi.yaml
├── console/openapi.yaml
├── platform/openapi.yaml
├── operative/openapi.yaml
└── visor/openapi.yaml
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

All services are accessible through `api.hanzo.ai`:

```
api.hanzo.ai/v1/chat/completions    → Cloud API (AI models)
api.hanzo.ai/v1/models              → Cloud API (model listing)
api.hanzo.ai/v1/billing/*           → Commerce (billing/usage)
api.hanzo.ai/v1/auth/*              → IAM (identity)
api.hanzo.ai/v1/analytics/*         → Analytics
api.hanzo.ai/v1/search/*            → Search
api.hanzo.ai/v1/flow/*              → Flow (workflows)
api.hanzo.ai/v1/bot/*               → Bot framework
api.hanzo.ai/v1/kms/*               → KMS (secrets)
api.hanzo.ai/v1/vm/*                → Visor (VMs)
api.hanzo.ai/v1/platform/*          → Platform (PaaS)
api.hanzo.ai/v1/console/*           → Console (observability)
```

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
