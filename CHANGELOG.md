# Changelog

## v1.0.0

### 2026-07-10 — o11y resynced to the flat, version-less live surface

Reconciled `o11y/openapi.yaml` to the live cloud routes in
`hanzoai/cloud/clients/o11y` (`scope.go` + `query.go` + `vmproxy.go` +
`event_ingest.go`). The prior spec modelled a fictional Loki/Tempo/Grafana
surface (LogQL `logs/query`, `logs/push`, `logs/tail`, Prom `series`/`labels`,
`traces`, `dependencies`, notification `channels`, dashboard/rule CRUD) that
was never served at these flat paths. The o11y subsystem also collapsed from
five registrations to one `o11y` concept; the spec now reads as a single `O11y`
surface (one tag).

The spec is now exactly the live public surface (12 flat, version-less paths —
no nested `/v1/o11y/api/vN/*` or `/v1/o11y/vN/*`):

- `POST /v1/o11y/query`, `POST /v1/o11y/query_range` — the one canonical
  composite builder query (was wrongly `GET` PromQL); the upstream engine
  version stays internal, never in the route.
- `GET /v1/o11y/logs`, `/v1/o11y/metrics`, `/v1/o11y/status` — tenant-scoped,
  org-pinned reads (product logs, RED + LLM usage, live service health) with
  schemas grounded in the Go response structs.
- **`GET /v1/o11y/vm/query`, `GET /v1/o11y/vm/query_range`** — NEW. The
  SuperAdmin-only VictoriaMetrics read proxy backing the platform
  infrastructure-health board; `query` allowlisted to `up`/`sum(up)`/`count(up)`,
  returning the native Prometheus envelope verbatim.
- `GET /v1/o11y/services`, `/v1/o11y/dashboards`, `/v1/o11y/rules`,
  `/v1/o11y/health` — served by the embedded o11y runtime.
- `POST /v1/o11y/ingestion` — native-Go LLM-observability event ingest
  (traces/observations/scores).

`hanzo.yaml` regenerated via `merge.py`: 68 services, 1797 paths (−10 from the
removed fictional o11y paths).

### Canonical capability manifest + category grouping

- Added `CAPABILITIES.md` — the authoritative index of every public
  capability: one canonical name each, grouped into the eight categories
  (Identity, AI, Messaging, Observability, Commerce, Platform,
  Applications, Core), with `/v1/<name>` prefixes. Internal infra
  (principal, goja, mpc, controlplane) is explicitly excluded.
- `merge.py` now emits `x-tagGroups` so the unified `hanzo.yaml` is
  navigable by category, and fails closed if any spec is ungrouped.

### Cloud product-surface specs (clients/* → live /v1 flat prefixes)

Authored per-service specs for the fused `api.hanzo.ai/v1` cloud-binary
surface, route-accurate to the Go handlers in `hanzoai/cloud/clients/<x>`:

- `/v1/agents/*` (agents + runs + live session tree) is covered by
  `cloud/openapi.yaml` (landed on main); the 21 specs below are the rest.
- Added `functions/openapi.yaml` — `/v1/functions/*` (serverless functions,
  metered invoke) from `clients/functions`.
- Added `framework/openapi.yaml` — `/v1/framework/*` (doctypes, modules, roles,
  generic document CRUD) from `clients/framework`.
- Added `tracker/openapi.yaml` — `/v1/tracker/*` (projects + issues) from
  `clients/tracker`.
- Added `crm/openapi.yaml` — `/v1/crm/*` (companies, contacts, opportunities)
  from `clients/crm`.
- Added `automations/openapi.yaml` — `/v1/automations/*` (flows, versions,
  runs, pieces, MCP) from `clients/automations`.
- Added `integrations/openapi.yaml` — `/v1/integrations/*` (provider connect
  + Slack events/commands/link) from `clients/integrations`.
- Added `admin/openapi.yaml` — `/v1/admin/*` (god-view overview, orgs, users,
  customers, finance, revenue, audit) from `clients/admin`.
- Added `plan/openapi.yaml` — `/v1/plans/*` (plan catalog, resolve,
  entitlements) from `clients/plan`.
- Added `kb/openapi.yaml` — `/v1/kb/*` (search + connectors) from `clients/kb`.
- Added `prompts/openapi.yaml` — `/v1/prompts/*` (prompt library, catalog,
  metrics) from `clients/prompts`.
- Added `templates/openapi.yaml` — `/v1/templates/*` (template gallery) from
  `clients/templates`.
- Added `git/openapi.yaml` — `/v1/git/*` (repos + Git smart-HTTP transport)
  from `clients/git`.
- Added `billing/openapi.yaml` — `/v1/billing/*` (usage, balance,
  gpu-eligibility, gpu-charge, payment-methods) from `clients/billing`.
- Added `security/openapi.yaml` — `/v1/security/*` (rules, scans, findings)
  from `clients/security`.
- Added `graph/openapi.yaml` — `/v1/indexers`, `/v1/oracles` from
  `clients/graph` (flat prefixes, not `/v1/graph`).
- Added `do/openapi.yaml` — `/v1/vpcs`, `/v1/load-balancers` from `clients/do`
  (flat prefixes, not `/v1/do`).
- Added `exec/openapi.yaml` — `/v1/exec`, `/v1/upload`, `/v1/download`,
  `/v1/files` (code interpreter, `X-API-Key` service auth) from `clients/exec`.
- Added `websearch/openapi.yaml` — `/v1/websearch/{search,scrape}` (SearXNG +
  Firecrawl-shaped over Hanzo Crawl) from `clients/websearch`.
- Added `tasks/openapi.yaml` — `/v1/tasks/*` (durable workflow engine surface,
  identity-gated) from `clients/tasksvc`.
- Re-based `visor/openapi.yaml` onto its live flat prefixes `/v1/machines`,
  `/v1/gpus`, `/v1/clusters`, `/v1/bots`, `/v1/compute/*`, `/v1/agent-bindings`
  from `clients/visor` (was wrongly under `/v1/visor/*`).
- Re-based `zt/openapi.yaml` onto its live flat prefixes `/v1/networks`,
  `/v1/mesh/services`, `/v1/edge/nodes` from `clients/zt` (was wrongly under
  `/v1/zt/*`).
- `hanzo.yaml` regenerated: 58 services, 1698 paths.

### Frontend surface completeness (hanzo.app + hanzo.chat)

- Added the `app` service spec (`app/openapi.yaml`): the hanzo.app projects &
  deployments surface at top-level `/v1/projects/*` — `GET/POST /v1/projects`,
  `GET/PATCH/DELETE /v1/projects/{slug}`, `POST /v1/projects/{slug}/deploy`
  (tar artifact or git build), `GET /v1/projects/{slug}/deployments`.
- Added the `base` service spec (`base/openapi.yaml`): the Hanzo Base records
  store at top-level `/v1/collections/{collection}/records[/{id}]` (CRUD),
  backing hanzo.app's `site_drafts` working-draft store.
- `ai` spec: defined the image and audio operations its own description already
  advertised — `POST /v1/images/generations`, `POST /v1/audio/speech`,
  `POST /v1/audio/transcriptions` (OpenAI-compatible).
- Confirmed zero `/api/` paths across every spec; the only non-`/v1` routes are
  the unversioned infra probes `/health`, `/healthz`, `/metrics`.
- `hanzo.yaml` regenerated: 38 services, 1590 paths.

## v1.0.0 — 2026-06-30

### AI inference namespace

- Added the `ai` service spec (`ai/openapi.yaml`): the top-level OpenAI- and
  Claude-compatible inference surface served by `hanzoai/ai` — `/v1/chat/completions`,
  `/v1/completions`, `/v1/embeddings`, `/v1/rerank`, `/v1/models`, `/v1/models/{model}`,
  `/v1/messages` (Anthropic). These are the ONE deliberate exception to the
  `/v1/<service>/` rule (SDK path-compatibility is the contract).
- Un-nested inference from the cloud control plane: removed
  `/v1/cloud/chat/completions` (moved to top-level `ai`). `/v1/cloud/*` is now the
  user-org control plane only.
- `hanzo.yaml` discovery now lists `ai` (gateway_route `/v1/chat/completions`) and
  corrects `cloud` to `/v1/cloud`.

### 2026-07-03 — agents + sessions control plane documented at /v1

- Documented the previously-undocumented core agents surface in
  `cloud/openapi.yaml` (grep `/v1/agents` returned nothing before this). Sourced
  from the real handlers in `hanzoai/cloud` (`clients/agents/{agents,store,
  sessions,sessions_store,sessions_stream}.go`), not guessed. Top-level per the
  lock-in (no legacy prefix): `/v1/agents` (list/create), `/v1/agents/{ref}`
  (get/patch/delete), `/v1/agents/{ref}/run` (+ credit drawdown metered
  product=agent), `/v1/agents/{ref}/runs`, `/v1/agents/metrics`,
  `/v1/agents/activity`.
- Documented the live session/subagent control plane: `/v1/agents/sessions`
  (register/list), `/v1/agents/sessions/{id}` (detail/patch),
  `/v1/agents/sessions/{id}/tree` (subagent tree),
  `/v1/agents/sessions/{id}/events`, the control commands
  `.../{pause,resume,stop,message}`, and the SSE feed
  `/v1/agents/sessions/stream` (streams over ZAP).
- New tags: `Agents API`, `Agent Sessions API`. New self-contained schemas under
  `components.schemas` (`agents.*`): Agent, AgentDetail, Run, CreateAgentRequest,
  UpdateAgentRequest, RunRequest, Metrics, Activity, Session, SessionDetail,
  Event, TreeNode, RegisterSessionRequest, PatchSessionRequest, EventRequest,
  ControlRequest, ControlResult. Every route is org-scoped (X-Org-Id minted by
  the gateway from the validated IAM token, HIP-0026).
- `info.version` stays `1.0.0` per the lock-in (this repo tracks changes here,
  not via per-spec version bumps). Whole-repo `/api/` sweep remains zero routes
  (the two residual mentions were `#` comments, reworded away).

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
