<p align="center"><img src=".github/hero.svg" alt="openapi" width="880"></p>

# Hanzo OpenAPI

OpenAPI 3.1 specifications for every Hanzo service. **v1.0.0 — locked in.**

Forward-only. No backwards compatibility. No deprecated paths. No `/api/`
prefixes. No cross-brand references.

Single bearer JWT issued by Hanzo IAM (`https://hanzo.id`) authenticates
every service. Every route is `/v1/<service>/<resource>` so the same path
works through the gateway (`api.hanzo.ai`) and through the service's own
hostname (`<service>.hanzo.ai`).

**One exception — AI inference is top-level.** The `ai` service
(`hanzoai/ai`) exposes its OpenAI- and Claude-compatible surface at the bare
`/v1/*` paths (`/v1/chat/completions`, `/v1/completions`, `/v1/embeddings`,
`/v1/models`, `/v1/rerank`, `/v1/messages`) — NOT `/v1/ai/*` — because every
OpenAI/Anthropic SDK hard-codes those paths, so the path is the compatibility
contract. Everything else stays under `/v1/<service>/`.

```bash
# AI inference (top-level, OpenAI-compatible)
curl -H "Authorization: Bearer ${HANZO_TOKEN}" \
     https://api.hanzo.ai/v1/chat/completions -d '{"model":"zen5","messages":[...]}'

# Control-plane (per-service prefix)
curl -H "Authorization: Bearer ${HANZO_TOKEN}" \
     https://api.hanzo.ai/v1/cloud/get-providers
```

OIDC discovery:
`https://hanzo.id/.well-known/openid-configuration`

## Service Index

| Service | Spec | Hostname | Gateway prefix |
|---------|------|----------|----------------|
| ai | [ai/openapi.yaml](ai/openapi.yaml) | `api.hanzo.ai` | `/v1/{chat,completions,embeddings,models,rerank,messages}` (top-level — OpenAI/Claude-compatible) |
| analytics | [analytics/openapi.yaml](analytics/openapi.yaml) | `analytics.hanzo.ai` | `/v1/analytics` |
| app | [app/openapi.yaml](app/openapi.yaml) | `api.hanzo.ai` | `/v1/projects` (top-level — hanzo.app projects & deploy) |
| auto | [auto/openapi.yaml](auto/openapi.yaml) | `auto.hanzo.ai` | `/v1/auto` |
| base | [base/openapi.yaml](base/openapi.yaml) | `base.hanzo.ai` | `/v1/collections` (top-level — Base records store) |
| bot | [bot/openapi.yaml](bot/openapi.yaml) | `app.hanzo.bot` | `/v1/bot` |
| chat | [chat/openapi.yaml](chat/openapi.yaml) | `hanzo.chat` | `/v1/chat` |
| cloud | [cloud/openapi.yaml](cloud/openapi.yaml) | `api.hanzo.ai` | `/v1/cloud` |
| commerce | [commerce/openapi.yaml](commerce/openapi.yaml) | `commerce.hanzo.ai` | `/v1/commerce` |
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
| visor | [visor/openapi.yaml](visor/openapi.yaml) | `vm.hanzo.ai` | `/v1/visor` |
| zt | [zt/openapi.yaml](zt/openapi.yaml) | `zt.hanzo.ai` | `/v1/zt` |

Discovery: [hanzo.yaml](hanzo.yaml) at `https://api.hanzo.ai/v1/discovery`
returns the canonical list of services with their spec URLs.

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
