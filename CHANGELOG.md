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

### 2026-07-01 — reconcile specs against the live `/v1` surface

Audited every service spec against the REAL served routes (live probes of
`api.hanzo.ai`, `hanzo.id`, `vm.hanzo.ai`, `commerce.hanzo.ai`) and the actual
service source (cloud `subsystems/subsystems.go` + `clients/*`, `hanzoai/ai`
router, `hanzoai/iam`, `hanzoai/commerce`, `hanzoai/vm`). Ground truth: OIDC
discovery at `https://hanzo.id/.well-known/openid-configuration`.

**IAM — OAuth/OIDC paths corrected (were wrong).** The spec advertised
top-level `/oauth/*` and `/.well-known/jwks`; the live service (and OIDC
discovery doc) serve these under `/v1/iam/*`:
- `/oauth/token` → `/v1/iam/oauth/token`; `/oauth/introspect` →
  `/v1/iam/oauth/introspect`; `/oauth/userinfo` → `/v1/iam/oauth/userinfo`;
  `/oauth/token/refresh` → `/v1/iam/oauth/token/refresh`; `/oauth/callback` →
  `/v1/iam/oauth/callback`; `/.well-known/jwks` → `/v1/iam/.well-known/jwks`.
- Added the discovery-advertised endpoints that were missing:
  `/v1/iam/oauth/authorize`, `/v1/iam/oauth/device`, `/v1/iam/oauth/register`,
  `/v1/iam/oauth/revoke` (all confirmed live). `/.well-known/openid-configuration`
  stays at the root (OIDC requires it there).
- Fixed a pre-existing invalid `test_apiKey` security reference → `BearerAuth`.

**Cloud — the real top-level `/v1/*` product surface is now documented.** The
spec was almost entirely `/v1/cloud/<verb>-<resource>` casibase RPC routes and
was missing the primary surface. Added (all probe-confirmed live): OpenAI-
compatible `/v1/chat/completions`, `/v1/completions`, `/v1/embeddings`,
`/v1/rerank`, `/v1/messages`, `/v1/models`; catalog `/v1/pricing`, `/v1/plans`;
API health `/v1/health`; the provisioning data plane `/v1/{sql,vector,kv,s3,
docdb,datastore,search}` (Bearer + `X-Org-Id`); `/v1/projects[/{id}]`; code
interpreter `/v1/exec`, `/v1/files`. Removed the misleading `/health` (that
path serves the console SPA at the gateway; the JSON API health is `/v1/health`).
The `/v1/cloud/*` RPC routes are retained — they are the same casibase surface,
also reachable at `/v1/*` via the gateway's `V1CloudRewriteFilter`.

**Visor — rewritten to the real `vm.hanzo.ai` compute API.** Dropped the
fictional `/v1/visor/<verb>-<resource>` infix (the service serves everything at
`/v1/*`). Added the public REST catalog `/v1/regions`, `/v1/sizes`, `/v1/gpus`
and the machines REST surface `/v1/machines`, `/v1/machines/launch`,
`/v1/machines/{id}`; added the volumes and plans (`/v1/get-plans`) surfaces that
were missing. Server pinned to `https://vm.hanzo.ai` only (compute is NOT
gateway-proxied — `api.hanzo.ai/v1/machines` is 404). NOTE: there is no
`/v1/plans` on visor (that was an authz 403, not a route).

**Commerce — added the live `/v1/billing/*` money surface.** The spec had 78
`/v1/commerce/*` routes but was missing all of `/v1/billing/*` (balance, tier,
usage, deposit, refund, invoices, subscriptions, payment-methods, portal, …),
which is what is actually served and metered. Also added the native
`/v1/commerce/{tenant,deposits,webhooks}` hosted-checkout routes.

**Master + shared.** `hanzo.yaml` OIDC example and `BearerAuth` description
now use `/v1/iam/oauth/*` + `/v1/iam/.well-known/jwks`; `/v1/health` example
matches the real `{status,msg,data,data2}` envelope; the discovery/OIDC ops are
annotated (OIDC discovery is served at `hanzo.id`, not proxied at
`api.hanzo.ai`; the aggregated `/v1/discovery` JSON endpoint is not yet wired).
`shared/auth.yaml` oauth2 flow URLs → `https://hanzo.id/v1/iam/oauth/*`; the
API-key scheme is now `hk-` Bearer (was a fictional `X-API-Key` /key/generate).

**Confirmed accurate (no change):** `pricing` (`/v1/pricing/*` + `/health` all
live 200); `chat` `/oauth/<provider>` social-login routes (LibreChat serves
these at the root — confirmed live, the `/v1/chat/*` convention does not apply).

**Flagged (spec ≠ reality, left for a decision — not guessed):**
- `commerce`: the legacy resource routes (`product`, `order`, `store`, `cart`,
  `user`, `account`, `subscribe`, `checkout`, …) are documented under
  `/v1/commerce/*` but the standalone service serves them at top-level `/v1/*`
  (the `/v1/commerce/*` rewrite is a stubbed no-op; the cloud-binary mount at
  `/v1/commerce` is not live at the gateway). Prefix reconciliation pending.
- `nexus`: `nexus.hanzo.ai` returns 404 for all probed routes — the service is
  unreachable; its 131-path spec is unverifiable and likely stale.
- `gateway`: the `/v1/gateway/*` admin surface (key/spend/team/routes) is 404 at
  `api.hanzo.ai` — documented but not live; left untouched pending verification.

Validation: `hanzo.yaml`, `iam`, `cloud`, `visor`, `commerce` lint clean under
`@redocly/cli` (0 errors; only house-standard warnings remain).

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
