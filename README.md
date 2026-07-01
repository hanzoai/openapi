# Hanzo OpenAPI

OpenAPI 3.1 specifications for every Hanzo service. **v1.0.0 — locked in.**

Forward-only. No backwards compatibility. No deprecated paths. No `/api/`
prefixes. No cross-brand references.

Single bearer JWT issued by Hanzo IAM (`https://hanzo.id`) authenticates
every service. Every route is `/v1/<service>/<resource>` so the same path
works through the gateway (`api.hanzo.ai`) and through the service's own
hostname (`<service>.hanzo.ai`).

```bash
curl -H "Authorization: Bearer ${HANZO_TOKEN}" \
     https://api.hanzo.ai/v1/cloud/models
```

OIDC discovery:
`https://hanzo.id/.well-known/openid-configuration`

## Service Index

| Service | Spec | Hostname | Gateway prefix |
|---------|------|----------|----------------|
| analytics | [analytics/openapi.yaml](analytics/openapi.yaml) | `analytics.hanzo.ai` | `/v1/analytics` |
| auto | [auto/openapi.yaml](auto/openapi.yaml) | `auto.hanzo.ai` | `/v1/auto` |
| bot | [bot/openapi.yaml](bot/openapi.yaml) | `app.hanzo.bot` | `/v1/bot` |
| chat | [chat/openapi.yaml](chat/openapi.yaml) | `hanzo.chat` | `/v1/chat` |
| cloud | [cloud/openapi.yaml](cloud/openapi.yaml) | `api.hanzo.ai` | `/v1/cloud` |
| commerce | [commerce/openapi.yaml](commerce/openapi.yaml) | `commerce.hanzo.ai` | `/v1/billing/*` + `/v1/*` |
| console | [console/openapi.yaml](console/openapi.yaml) | `console.hanzo.ai` | `/v1/console` |
| db | [db/openapi.yaml](db/openapi.yaml) | `db.hanzo.ai` | `/v1/db` |
| did | [did/openapi.yaml](did/openapi.yaml) | `did.hanzo.ai` | `/v1/did` |
| dns | [dns/openapi.yaml](dns/openapi.yaml) | `dns.hanzo.ai` | `/v1/dns` |
| edge | [edge/openapi.yaml](edge/openapi.yaml) | `edge.hanzo.ai` | `/v1/edge` |
| engine | [engine/openapi.yaml](engine/openapi.yaml) | `engine.hanzo.ai` | `/v1/engine` |
| flow | [flow/openapi.yaml](flow/openapi.yaml) | `flow.hanzo.ai` | `/v1/flow` |
| gateway | [gateway/openapi.yaml](gateway/openapi.yaml) | `api.hanzo.ai` | `/v1/gateway` |
| guard | [guard/openapi.yaml](guard/openapi.yaml) | `guard.hanzo.ai` | `/v1/guard` |
| iam | [iam/openapi.yaml](iam/openapi.yaml) | `hanzo.id` | `/v1/iam` + `/oauth/*` + `/.well-known/*` |
| kms | [kms/openapi.yaml](kms/openapi.yaml) | `kms.hanzo.ai` | `/v1/kms` |
| kv | [kv/openapi.yaml](kv/openapi.yaml) | `kv.hanzo.ai` | `/v1/kv` |
| ml | [ml/openapi.yaml](ml/openapi.yaml) | `ml.hanzo.ai` | `/v1/ml` |
| mq | [mq/openapi.yaml](mq/openapi.yaml) | `mq.hanzo.ai` | `/v1/mq` |
| nexus | [nexus/openapi.yaml](nexus/openapi.yaml) | `nexus.hanzo.ai` | `/v1/nexus` |
| o11y | [o11y/openapi.yaml](o11y/openapi.yaml) | `o11y.hanzo.ai` | `/v1/o11y` |
| operative | [operative/openapi.yaml](operative/openapi.yaml) | `operative.hanzo.ai` | `/v1/operative` |
| paas | [paas/openapi.yaml](paas/openapi.yaml) | `paas.hanzo.ai` | `/v1/paas` |
| platform | [platform/openapi.yaml](platform/openapi.yaml) | `platform.hanzo.ai` | `/v1/platform` |
| pricing | [pricing/openapi.yaml](pricing/openapi.yaml) | `pricing.hanzo.ai` | `/v1/pricing` |
| pubsub | [pubsub/openapi.yaml](pubsub/openapi.yaml) | `pubsub.hanzo.ai` | `/v1/pubsub` |
| registry | [registry/openapi.yaml](registry/openapi.yaml) | `registry.hanzo.ai` | `/v1/registry` |
| s3 | [s3/openapi.yaml](s3/openapi.yaml) | `s3.hanzo.ai` | `/v1/s3` |
| search | [search/openapi.yaml](search/openapi.yaml) | `search.hanzo.ai` | `/v1/search` |
| stream | [stream/openapi.yaml](stream/openapi.yaml) | `stream.hanzo.ai` | `/v1/stream` |
| vector | [vector/openapi.yaml](vector/openapi.yaml) | `vector.hanzo.ai` | `/v1/vector` |
| visor | [visor/openapi.yaml](visor/openapi.yaml) | `vm.hanzo.ai` | `/v1/*` (not gateway-proxied) |
| zt | [zt/openapi.yaml](zt/openapi.yaml) | `zt.hanzo.ai` | `/v1/zt` |

Discovery: [hanzo.yaml](hanzo.yaml) is the canonical index of services and
their spec URLs. (The aggregated `GET /v1/discovery` JSON endpoint at the
gateway is not yet wired; the specs in this repo are the machine-readable index.)

### Reality notes (spec vs. live surface)

The "Gateway prefix" column above is the intended `/v1/<service>/*` convention.
Where the live surface differs, the per-service spec follows reality:

- **cloud** — the fused binary serves the primary product routes at the **top
  level** (`/v1/chat/completions`, `/v1/embeddings`, `/v1/models`, `/v1/pricing`,
  `/v1/plans`, the `/v1/{sql,vector,kv,s3,docdb,datastore,search}` data plane,
  `/v1/projects`, `/v1/exec`), not under `/v1/cloud/*`. The `/v1/cloud/*` RPC
  routes remain valid — the same casibase surface is reachable both ways.
- **iam** — OAuth/OIDC endpoints live under `/v1/iam/oauth/*` and
  `/v1/iam/.well-known/jwks`; only `/.well-known/openid-configuration` is at the
  root (per OIDC).
- **commerce** — the money surface is `/v1/billing/*`; the resource models are
  served at top-level `/v1/*` on the standalone host (the `/v1/commerce/*`
  prefix is pending reconciliation).
- **visor** — compute is served at `/v1/*` on `vm.hanzo.ai` and is not
  gateway-proxied.
- **nexus**, **gateway** `/v1/gateway/*` — documented but not currently live at
  their hostnames (unverified; specs left as-is).

## v1.0.0 Conventions

- **Versioning**: `info.version: 1.0.0` on every service. There is no `v0`.
  There will be no `v2`. Breaking changes ship as new resources or new
  endpoints under `/v1/`, never as a parallel `/v2/` tree.
- **Routing**: every route is `/v1/<service>/<resource>`. No `/api/` prefix.
  IAM additionally exposes `/oauth/*` (RFC 6749) and `/.well-known/*`
  (RFC 5785) for OIDC discovery.
- **Security**: every operation uses `BearerAuth` (JWT from Hanzo IAM).
  No service has its own login flow.
- **Cross-file `$ref`**: never. Each service spec is self-contained.
- **Errors**: 4xx for client errors, 5xx for server errors. Every error
  response has a JSON body with a `status` and `msg`.

## Validate

```bash
# Parse + schema validation across all specs:
python3 -c "import yaml, glob, sys; \
  [yaml.safe_load(open(s)) for s in glob.glob('*/openapi.yaml') + ['hanzo.yaml']]; \
  print('OK')"

# Spectral lint per spec:
for spec in */openapi.yaml hanzo.yaml; do
  npx -y @stoplight/spectral-cli lint "$spec"
done

# Redoc preview:
npx -y @redocly/cli preview-docs hanzo.yaml
```

## Code generation

```bash
# Python client for cloud service:
npx -y @openapitools/openapi-generator-cli generate \
  -i cloud/openapi.yaml -g python -o clients/python/cloud

# TypeScript client for chat service:
npx -y @openapitools/openapi-generator-cli generate \
  -i chat/openapi.yaml -g typescript-axios -o clients/ts/chat
```

## License

Proprietary. Copyright 2024-2026 Hanzo AI, Inc.
