# Changelog

## v1.0.0 — 2026-05-31

Forward-only v1 lock-in. No prior versions, no backwards compatibility.

### Scope

All 34 service specifications plus the master discovery spec
(`hanzo.yaml`) are now at `info.version: 1.0.0`.

### Routing

- Every route is `/v1/<service>/<resource>`. The same path resolves through
  the gateway at `api.hanzo.ai` and through the service's own hostname.
- `/api/` prefixes are removed from every spec (794 routes rewritten).
- IAM also exposes `/oauth/*` (RFC 6749 / OIDC) and `/.well-known/*`
  (RFC 5785) at the root.

### IAM

- 227 legacy Casdoor RPC-style `/api/<verb>-<resource>` routes rewritten to
  REST under `/v1/iam/<resource>[/{id}]`. Verb is encoded in the HTTP method.
- 233 input paths consolidated to 150 REST paths after collision merging.
- OIDC and OAuth2 endpoints (`/oauth/token`, `/oauth/authorize`,
  `/oauth/userinfo`, `/oauth/introspect`, `/oauth/callback`) moved to
  canonical paths per RFC 6749.

### Security

- Every operation uses `BearerAuth` (JWT issued by Hanzo IAM at
  `https://hanzo.id`).
- Bearer scheme cites the OIDC discovery URL
  (`https://hanzo.id/.well-known/openid-configuration`).
- No service has its own login flow.

### Cleanup

- 1 `deprecated: true` operation removed (console).
- 1 cross-brand DID method reference removed from the did spec; only the `did:hanzo` method is supported.
- Loki upstream paths (`/loki/api/v1/*`) renamed to `/v1/o11y/logs/*` for
  consistency.
- chat had two competing `bearerAuth` / `BearerAuth` security schemes;
  consolidated to `BearerAuth` only.
- Master `hanzo.yaml` rewritten as a thin v1 discovery index. The previous
  1202-line union-of-services dump is replaced by a 3-route document
  (`/v1/discovery`, `/v1/health`, `/.well-known/openid-configuration`)
  plus a `Service` schema. Per-service detail lives in each service's own
  spec; there is no cross-file `$ref`.

### 2026-06-30 — cloud product surface documented at /v1

- Added the previously-undocumented cloud product/docs-RAG surface to
  `cloud/openapi.yaml`, top-level per the lock-in (no `/api/`): `/v1/search-docs`,
  `/v1/search-docs/indexes`, `/v1/search-docs/stats`, `/v1/chat-docs`,
  `/v1/index-docs`, `/v1/vector/collections`, `/v1/vector/stats`. These are the
  console Search/Vector panels + docs-RAG clients (python-sdk, hanzo-docs). The
  routes served the residual `/api/<route>` form and were renamed to `/v1/<route>`
  in hanzoai/cloud (productsvc) + hanzoai/ai; the spec now matches. New tag:
  `Search API`. Whole-repo `/api/` sweep confirms zero remaining Hanzo paths.

### Coverage

| Service     | Paths | Routes |
|-------------|-------|--------|
| analytics   | 63    | all `/v1/analytics/*` |
| auto        | 50    | all `/v1/auto/*` |
| bot         | 30    | all `/v1/bot/*` |
| chat        | 171   | all `/v1/chat/*` |
| cloud       | 151   | all `/v1/cloud/*` |
| commerce    | 78    | all `/v1/commerce/*` |
| console     | 43    | all `/v1/console/*` |
| db          | 17    | all `/v1/db/*` |
| did         | 11    | all `/v1/did/*` |
| dns         | 10    | all `/v1/dns/*` |
| edge        | 12    | all `/v1/edge/*` |
| engine      | 22    | all `/v1/engine/*` |
| flow        | 87    | all `/v1/flow/*` |
| gateway     | 24    | all `/v1/gateway/*` |
| guard       | 6     | all `/v1/guard/*` |
| iam         | 150   | `/v1/iam/*` + `/oauth/*` + `/.well-known/*` |
| kms         | 52    | all `/v1/kms/*` |
| kv          | 22    | all `/v1/kv/*` |
| ml          | 14    | all `/v1/ml/*` |
| mq          | 28    | all `/v1/mq/*` |
| nexus       | 151   | all `/v1/nexus/*` |
| o11y        | 22    | all `/v1/o11y/*` |
| operative   | 10    | all `/v1/operative/*` |
| paas        | 29    | all `/v1/paas/*` |
| platform    | 132   | all `/v1/platform/*` |
| pricing     | 23    | all `/v1/pricing/*` |
| pubsub      | 20    | all `/v1/pubsub/*` |
| registry    | 14    | all `/v1/registry/*` |
| s3          | 12    | all `/v1/s3/*` |
| search      | 34    | all `/v1/search/*` |
| stream      | 9     | all `/v1/stream/*` |
| vector      | 13    | all `/v1/vector/*` |
| visor       | 41    | all `/v1/visor/*` |
| zt          | 30    | all `/v1/zt/*` |

Master `hanzo.yaml` discovery spec: 3 paths.
