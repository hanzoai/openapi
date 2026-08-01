# Changelog

## v1.0.0

### IAM: the dead store's document is gone, and a path names a thing

`iam/openapi.yaml` was the entity store this fleet replaced, imported whole. It
declared **234 operations**; hanzoai/iam serves **94**. `audit.py` had been
reporting that gap the whole time — 217 declared-and-unserved, 77
served-and-undeclared — and nothing acted on it.

The **38 verb-noun addresses** in it were the loudest half: `run-casbin-command`,
`all-actions`, `all-objects`, `all-roles`, `global-users`, `global-certs`,
`sorted-users`, `ldap-users`, `filtered-policies`, `remove-policy`,
`is-session-duplicated`, `impersonation-user`, `pay-order`, `place-order`,
`invoice-payment`, `user-orders`, `user-payments`, `permissions-by-roles`,
`records-filters`, `version-infos`, `table-infos` and the rest. None is served by
any binary in the fleet. They reached a customer as `hanzo iam all-actions` and as
a method in every generated SDK. **223 summaries** were a title-cased Go
controller method — "Api Controller Get All Actions", "Api Controller Get
Ldapser" — and one operation was named after an outside vendor's policy engine.

The file is now built from what the binary serves: the 75 typed operations
`App.OpenAPISpec()` emits, with the handlers' own doc comments as their prose,
plus the OIDC/OAuth, front-door, SCIM 2.0 and credential surface authored at the
addresses measured off `app.Fiber().GetRoutes()`. **112 paths, 133 operations, 0
verb-noun segments, 0 undescribed, 0 controller names.** operationIds are one
shape — `<kind>_<verb>` — where the emitter had left three (`get_v1_iam_users`,
`listOrganizations`, `addProvider`); those are SDK method names, so the spelling
is the customer's business.

`test_placement.py`'s `OFF_PREFIX` for iam went from eleven unprefixed paths to
three. `/oauth/token`, `/oauth/userinfo`, `/oauth/introspect`, `/oauth/callback`,
`/oauth/token/refresh`, `/.well-known/webfinger` and the two
`/.well-known/{application}/…` were the dead store's addresses; iam serves the
protocol endpoints under `/v1/iam/oauth/` and its own discovery document says so.
Probing the old ones returns 200 `text/html` — the portal's catch-all,
byte-identical to what a nonsense path returns. A 200 is not liveness. What
remains is discovery at the three addresses the standards fix.

**`compat` leaves the published document.** An operation the SERVING binary tags
`compat` is a legacy address it keeps reachable for consumers pinned to it, not
something the contract teaches. hanzoai/iam declares 51 of them — the entity
verbs (`get-users`, `add-application`, `set-preferred-mfa`) and the singular
`application` address from before that kind was pluralized — each on the SAME
handler as its canonical noun twin. `merge.py` drops them, the same call as
dropping TRACE: the served surface is unchanged and the published one says each
thing once. This repo is not taking a vote about what a server serves; the
serving repo made the declaration and this respects it.

### One product, one owning spec — placement, and 31 dead paths deleted

`capabilities.yaml` has always stated the law — "the route IS the identity: one
capability = one name = one /v1/<name> = one <name>/openapi.yaml" — and nothing
enforced it. Measured against the live route table at api.hanzo.ai: **103
authored paths** sat outside their owner's prefix and **four products** (`kv`,
`s3`, `search`, `vector`) were described by TWO specs at once.

`provisioning/openapi.yaml` was the bucket: it claimed `/v1/sql`, `/v1/vector`,
`/v1/datastore`, `/v1/kv`, `/v1/search`, `/v1/s3` and `/v1/docdb` — seven other
products' roots — and its own header says why it could: "these routes are keyed
by RESOURCE KIND at top-level /v1/, NOT under /v1/provisioning/." There is no
`/v1/provisioning` route and never was. Each kind's spec owns its own quartet
now; `sql`, `datastore` and `docdb` became their own specs under `data`;
`provisioning` is `collapsed`.

The inference edge — `/v1/chat/completions`, `/v1/completions`, `/v1/embeddings`,
`/v1/rerank`, `/v1/models`, `/v1/models/{model}`, `/v1/messages`,
`/v1/images/generations`, `/v1/audio/speech` — moved from `ai/` to `gateway/`,
the binary that answers it. The `/v1/admin/*` operations authored in
`affiliates/`, `authors/`, `referrals/` and `plugin/` moved to `admin/`;
`/v1/edge/nodes` moved from `zt/` to `edge/`. `plan/` → `plans/` and `plugin/` →
`plugins/`, because the routes are `/v1/plans` and `/v1/plugins` and the route is
the part that cannot move.

**31 paths deleted**, each probed at api.hanzo.ai and absent from the live route
table: the whole `/v1/gateway/*` subtree (23 — a phantom second copy of the
inference edge, which is also why three operationIds needed a `_2` suffix to
stay distinct in codegen and no longer do), `/v1/load-balancers` ×2 (the served
product is `/v1/balancers`), `/v1/bots/launch|{id}|{id}/{action}` (served at
`/v1/compute/bots/*`), `/v1/machines/{id}/bind-agent|agent-binding` (served at
`/v1/machines/{id}/agent`), and `/v1/audio/transcriptions`. Nothing served was
removed: hanzo.yaml went 1742 → 1711 paths, 31 removed and 0 added.

Fifteen more authored paths 404 at the server while the live route table lists
them as keys — `/v1/admin/{affiliates,authors}/*` writes, `/v1/admin/plugins/*`
control, `/v1/sites/deploy`, `/v1/clusters/{clusterId}/pools*`. Those are
hanzoai/cloud describing routes whose handlers are not reachable, not authoring
defects, so they stay until cloud fixes them — this repo cannot refute the
registry it trusts.

`test_placement.py` is the gate, in CI via `hanzo.yml`. Rule 1 (no two authored
specs claim one product) is absolute. Rule 2 (a spec claims its own prefix)
carries `OFF_PREFIX`, 48 declared exceptions each measured live, each a binary
answering at a top-level noun that is not its service's name — the fix for those
is a route move in the serving repo, and a stated gap beats a silent one.

### An empty field from the winner was deleting a populated one — 182 shapes back

The resync's worst defect, and it outlived two rounds of measurement here
because both measured `parameters` and never looked at `requestBody`.

`merge.py` took the whole operation OBJECT from cloud wherever it took a route,
and an untyped route's emission is an address and nothing else — so described
operations were replaced by undescribed ones. **47 request bodies** and **135
response sets** (100 of them reduced to the synthesized `default`) had left the
document: `POST /v1/authz/check`, `POST /v1/agents/{ref}/run`,
`POST /v1/kms/secrets`, the five agent-session control ops, and more. The CLI
measured it downstream: typed-flag operations 574 → 515, raw `--data` fallbacks
187 → 378, and `hanzo kms secrets create` lost the `value` field whose
stdin-only guard then had nothing to guard.

The mistake was reading cloud's silence about an untyped route as EMPTY when it
means UNKNOWN. `fuse()` overlays field by field now: cloud still wins existence,
operationId, tags and prose unconditionally, and wins any field it POPULATES. It
simply cannot delete one by being silent.

`requestBody` and `responses` are kept; query `parameters` are not, and the
asymmetry is the rule rather than an exception. A body IS the operation — silence
there does not prevent a lie, it prevents the CALL. A response describes what
comes back and cannot corrupt a request. A query parameter is the one a client
SENDS to a handler that may ignore it, so restoring it asserts a filter that may
silently do nothing — a wrong answer rather than a missing method.

Restored: 0 operations still missing a body d86248f had, 0 still reduced to the
synthesized `default`. Operations carrying parameters-or-body 1687 → **1767** of
2454. And the response-schema gap this repo had been reporting was partly its
own damage: **728 → 637**, with 91 of the "missing" schemas simply deleted by
the merge. Every figure published for that gap (754, 728, 696) was measuring
this defect alongside the real one. A number that only ever went up should have
been suspicious.

All 47 body losses were routes cloud serves UNTYPED; **zero** were typed-with-
no-body, so there is no emission bug to chase — only untyped routes to type.
LLM.md carries the 47 as a handover list, prioritised by what they cost: no body
means no call.

`merge.py` prints one number every build — 242 authored shapes still
load-bearing — designed to fall to zero as the typing lane converts those
routes, since a typed `zip.Get[In, Out]` carries body, parameters and response
from the code itself.

### A rule stated in a comment that the code did not implement

The first version of this fix kept `requestBody` and `responses` and declared
that query `parameters` were deliberately dropped. Reading the published
document back showed `GET /v1/kms/secrets` still carrying `path` and `env`: the
code had never dropped them, because the overlay starts from the authored
operation and replaces only what cloud populates.

The claim was wrong on the merits too. Cloud declaring ONLY the path parameters
is not a typed struct saying "no query parameters exist" — the weave derives
those from the route template, so `[{id}]` is what an untyped route emits either
way. Treating that as complete was the same silence-for-emptiness error one
level down, and it cost `GET /v1/integrations/{provider}/callback` its `code`
and `state` — the whole OAuth handshake — while a sibling route with no path
template kept everything. Same evidence, opposite outcome, decided by whether
the URL contained a brace.

`union()` merges parameters by name now, cloud's definition winning any name it
defines, and the comment says what the code does. Verified against `d86248f`:
**0 parameters and 0 request bodies that existed pre-resync are missing.**

The union needed two corrections the gate could not supply. A `$ref` parameter
has no `name`, so comparing on the key that was not there made eight
`/v1/admin/**` routes declare `{id}` twice — that one openapi-generator caught.
Then uniqueness turned out to span both levels: a path item's `parameters` apply
to every operation under it, the two sides disagree about where the path
parameter belongs (authored specs hoist it, the weave emits it per operation),
and 115 operations ended up declaring `{id}` twice. **The validator does not
resolve `$ref` parameters, so it reported zero errors on an invalid document.**
Green and wrong at the same time; both are measured here now.

### The SDK matrix pointed at two clients that do not exist

`sdks.yaml`'s `go` and `rust` rows were verified against local checkouts, and
both local checkouts are behind their canonical remotes. Running either would
not have updated a client — it would have written a SECOND one beside the
shipped one. `go` said `take: {.: cloud}` / `packageName: cloud` while
`hanzo-go/sdk` ships `package hanzoai` at the module root and has no `cloud/`
at all; `rust` said `crates/hanzo-cloud` while `hanzo-rs/sdk` ships
`crates/hanzo-client`.

Both rows are now DELETED, and the boundary is written down rather than decided
per case: a row exists while the WHOLE invocation is expressible as data, and a
language leaves when it needs something that is not. `go` needs the client at
the module root, which `take` cannot express — it rmtree's what it owns, so
`{.: .}` deletes the repository. `rust` needs a `reqwest/api.mustache` override
for 14 operations whose binary body is optional (`Option<Vec<u8>>`, which no
type mapping reaches), and a template is a file that must sit beside the
invocation — as must the `--type-mappings=file=Vec<u8>` it works with. The old
rust row had neither, plus `useSingleRequestParameter` and the spec's version as
the crate's.

The remaining five rows stay, because the same test says so: `hanzoai/js-sdk`
and `hanzoai/java-sdk` carry NO flags in their own scripts — they exec
`generate.py` — and js-sdk removed its copy only after the two disagreed and
built an orphan second copy of all 2143 files. A row here AND flags there is the
lie; a row here and a bare call site there is one declaration.

Three SDK repos answer through a rename redirect, which is how a stale name
keeps resolving: `hanzoai/go-sdk` → `hanzo-go/sdk`, `hanzoai/rust-sdk` →
`hanzo-rs/sdk`, `hanzoai/cpp-sdk` → `hanzo-cpp/sdk`. Go's module path stays
`github.com/hanzoai/go-sdk` — the proxy has it and consumers require it.

### operationId renamed 249 SDK methods — the decision, stated

Where cloud's document took a route an authored spec also had (366 operations),
the document now carries cloud's operationId. 117 of those are the handler's own
name and lost nothing; **249 are synthesized from the route**, so
`affiliates_adminListAffiliates` became `cloud_get_v1_admin_affiliates` — a
cross-language method rename, not cosmetics. It fell out of the resync rather
than being chosen, and on review it stands: a route-derived id is a total
function of the immutable `/v1` path, while a hand-authored id is owned by a
spec that no longer describes the route and vanishes when that spec is deleted —
the same break again, later, silently. It is also the name the MCP door already
uses. The break is once, now, and cannot recur for these operations.

### `mcp_Request.id` is a string — a scalar `oneOf` does not survive codegen

`id` was declared `oneOf: [integer, string]`, which is what JSON-RPC 2.0 permits
and what no typed generator can project: openapi-generator emits an empty
carrier class for a scalar `oneOf` (Kotlin `class McpRequestId()` with no
members) that serializes to `{}` — not a legal id anywhere. Java and C++ produce
the same shape, so it blocked three languages on one declaration.

Verified on the live door before changing it, because the fix is only safe if
the wire agrees: `id: "1"`, `id: 1` and `id: "abc-123"` are all accepted and all
echoed back with the TYPE they were sent; omitting `id` returns `null`. A string
is therefore always legal, and a client generated from this document always
reads back the string it sent.

Declared `type: string` on both `Request` and `Response`, with the polymorphism
recorded in the prose rather than in a shape — no second door, no alias, one
declaration. The generated field is now `kotlin.String?`, `private String id`,
`Id *string`; the `McpRequestId`/`McpResponseId` carriers are gone from every
client.

### Declare the MCP door — `POST /v1/mcp`, the one address an MCP client speaks

The fleet's JSON-RPC door has been answering all along and was in no spec:
`POST /v1/mcp` returns 200 with 796 tools, unauthenticated. It read as missing
because the probe was a GET — the route is POST-only, so GET is 404 — and
because the document held only `/v1/mcp/servers`, the registry of external
servers, which made the 404 look confirmed. `mcp/openapi.yaml` now declares one
operation (`mcp_rpc`) with the JSON-RPC 2.0 request and response typed:
`initialize`, `tools/list`, `tools/call`, a `Tool` with its `inputSchema`, and
both failure channels that live INSIDE a 200 — `error` (`-32601` for an unknown
method) and `result.isError` (a tool that ran and refused). Verified against the
live door, not guessed: `serverInfo`, `protocolVersion: 2025-06-18`, and the
`content[]` shape are all copied from its own answers.

The `tools` flow moves onto it, and the probe rule that hid it is corrected
everywhere it was written: **probe the method the document declares, not GET.**
A POST-only route and an absent route are indistinguishable from a GET.

What the door exposes is recorded because it cannot be derived: 796 tools
against 2479 operations, so about two thirds of the surface is not a tool, and
the split is the binary's decision. The naming rule is mechanical — a tool name
is its operationId minus the leading `<service>_` — holding for 795 of 796. The
one exception is this document's own doing: `cloud_get_v1_pricing_policy_2`
carries a `_2` because `/v1/pricing-policy` and `/v1/pricing/policy` collapse to
one identifier in every generator, while its tool is still `get_v1_pricing_policy`.

A tag whose key is a service NAME now belongs to that service's domain rather
than to whichever spec used it first: `MCP` was tagged by four specs, the
earliest alphabetically was `automations`, and the fleet's MCP door was being
filed under Streams.

### `hanzo.yaml` is THE published document — cloud's woven spec merged, and it wins

`cloud/openapi.yaml` stopped being a hand-written contract and became a verbatim
copy of hanzoai/cloud's own woven document, pulled by the new `sync.py` from that
repo's `origin/main`. Cloud regenerates that document from its router and fails
its own build on any diff, so it cannot describe a route the binary does not
serve — the property no spec here has. `merge.py` therefore merges it LAST and
lets it WIN every route an authored spec also claims (298), explicitly instead of
by where `cloud` falls in the alphabet.

1132 → **1720 paths**, 1519 → **2457 operations**, and the prose came with it:
699 → **1196 operations carry a description**, lifted from the handlers' Go doc
comments. Tags too — `tags`/`x-tagGroups` now describe the tags OPERATIONS carry
(260, of which 210 described, cloud's being the owning package's synopsis)
instead of the 55 spec directories, 4 of which any operation carried. A tag's
group is still the domain of the service that introduced it, so `capabilities.yaml`
remains the only taxonomy.

Three defects that reached generators are fixed at the one place that owns
codegen identity: an operation with no `responses` (668, cloud's untyped routes)
gets a `default` that says exactly that rather than an invented schema; an
operation with no tag takes its service's name rather than `DefaultApi`; and
`cloud_get_v1_pricing-policy` vs `cloud_get_v1_pricing_policy` — two real routes,
distinct strings, one Go type — are separated. Without the first, cloud's
document alone would be 668 generator errors. openapi-generator 7.14.0 reports
**0 errors, 0 warnings** on the result (346 recommendations, all unused models),
go and typescript-axios both generate, and the generated Go client compiles.

Six collisions surfaced when the merge stopped resolving them by alphabet, and
all six were duplicate authoring: `/health` declared by nine specs (and answering
with the SPA at `api.hanzo.ai`, while `/healthz` answers JSON) is now `gateway`'s
alone; `observe`, `app` and `product` declared only other services' routes and
are collapsed into `o11y`, `projects` and `vector` + `search-docs`. Every route
they held is in the document, from cloud.

`generated/hanzo.json` is deleted: measuring `hanzo.yaml` against a document it
now contains is tautology, and a second, older copy of one emission is the drift
this change exists to end.

### `flows.yaml` — repointed at what the wire actually answers

The six journeys landed naming ids the merge then moved or that were never
served, so every one was re-resolved against the merged document AND probed.
`money` and `agent` move to cloud's ids (`billing_*` and
`cloud_AgentsController.*` no longer exist — the binary's document owns those
routes now). `store` moves from the KV value plane to the store itself, and
`tools` from the automations MCP door to `/v1/tools`: both of the originals
reply 404 to GET and 405 to PUT/POST/DELETE, which is what a GET-only wildcard
answers when nothing is routed there. `hello` and `chat` were already right —
`ai_getAccount` returns 200 with the owner and name to print.

The method spread is the lesson: a bare 404 is ambiguous because a live handler
says "not found" too, so one GET is not a liveness probe.

### Delete the 18 products authored here and served nowhere — 655 paths, 849 operations

Every product below was probed on its OWN authored routes, at `api.hanzo.ai` and
at the hostname this repo claimed for it, and every one answered a route-level
404 — the router's own plaintext `404 page not found`, not an empty result from a
live handler. `hanzoai/cloud`'s `openapi.yaml` does not own them either.

Authoring a route nothing serves is not a harmless placeholder. `hanzoai/cli`'s
`genspec` refutes an authored operation only where the live route table OWNS its
product, so a product the router has never heard of is refuted by NOTHING: it
survives every gate and ships as a `hanzo` command, an SDK method, and a
`SKILL.md` under `/.well-known/agent-skills` instructing an agent to call a dead
endpoint — `skills.py` has no liveness filter at all. Annotating the spec
`UNSERVED` was the previous answer; no generator reads a comment.

| product | paths | ops | source removed |
|---|---|---|---|
| chat | 171 | 206 | `chat/` |
| nexus | 150 | 150 | `nexus/` |
| flow | 87 | 120 | `flow/` |
| auto | 50 | 69 | `auto/` |
| console | 43 | 67 | `console/` |
| paas | 28 | 42 | `paas/` |
| mq | 28 | 41 | `mq/` |
| engine | 22 | 35 | `engine/` |
| db | 17 | 30 | `db/` |
| pubsub | 19 | 29 | `pubsub/` |
| registry | 13 | 22 | `registry/` |
| did | 10 | 14 | `did/` |
| stream | 8 | 13 | `stream/` |
| guard | 5 | 7 | `guard/` |
| chat-docs | 1 | 1 | path in `cloud/` |
| index-docs | 1 | 1 | path in `cloud/` |
| agent-bindings | 1 | 1 | path in `visor/` |
| sdk | 1 | 1 | `/v1/sdk/secrets` in `kms/` |

`paas` is also a standing ruling: paas and platform were two names for one deploy
plane, and `/v1/platform` is the one that answers. It moves to `collapsed:` in
`capabilities.yaml`, pointing at `platform`.

`chat` was the one case needing a scalpel rather than a verdict, because the
GATEWAY serves inference under `/v1/chat/`. All 157 `/v1/chat/*` paths in the
master were probed individually (GET for reads, POST + `{}` for writes; 180 of
181 requests returned the plaintext route-miss). Exactly one answered:
`POST /v1/chat/completions`, with 401 and a JSON body. That operation is authored
by `ai/`, not `chat/` — so it survives untouched and `chat/` goes whole. The 15
bare `/oauth/{provider}` paths `chat/` also authored return 200 HTML from the
marketing SPA's catch-all (`/__total_nonsense_xyz__` returns the same page), so
they were never API routes, and they were never under `/v1/` either.

Removing `/v1/sdk/secrets` orphaned `kms`'s entire `components.schemas`
(`SdkEnvelope`, `SdkEnvelopeIdentity`, `Error` — reachable from no surviving
path), so it goes with the operation rather than shipping as three dead models in
every SDK. `kms` itself is untouched and live: `/v1/kms/secrets` answers 403.

Unchanged and verified alive at the edge: `audio`, `completions`, `embeddings`,
`images`, `messages`, `models`, `router`, `rerank`, and `/v1/chat/completions`.
The master goes 1787 → 1132 paths; the removed set is exactly the products above.
A product returns to this repo the day it is actually served.

### `plugin/` — author the `/v1/admin/plugins` operator surface cloud already serves

`generated/hanzo.json` carried four operations the contract never named:
`GET /v1/admin/plugins` and `POST /v1/admin/plugins/{name}/{enable,disable,reload}`,
served by `hanzoai/cloud/clients/plugin` as zip typed ops. Undeclared routes are
unreachable from every consumer of this repo — no SDK method, and no `hanzo`
command, because `hanzoai/cli`'s `genspec` iterates the AUTHORED master and uses
the live route table only to REFUTE. A path absent here can never enter the CLI
spec no matter what the server serves.

They live in `plugin/`, not `admin/`: `admin/` is the aggregator subsystem
(`clients/admin`), and the convention already established by `affiliates/`,
`authors/` and `referrals/` is that a subsystem authors its own
`/v1/admin/<subsystem>` operator paths beside its public ones.

Prose, operationIds and parameters are carried verbatim from the emitted spec.
The response schemas are named rather than inlined — `ListOut` → `Host` →
`PluginStatus` → `PluginUsage`, `ActionOut` → `Result` — with each field's
description lifted from the Go type it encodes, and `since` typed as a
`date-time` string rather than the empty object a `time.Time` renders as.

### Add `research/` — the /v1/research versioned R&D evidence surface (HIP-0512)

Adds the `research` service under the Intelligence domain: the R&D evidence plane
(experiments, attempts, diary artifacts) served by `hanzoai/cloud/clients/research`.
Versioned append-only records with canonical-vs-retained counts, first-class provenance
(git + lib_versions), private-by-default visibility + separate consent grants, and
content-hash-addressed diary artifacts. Seven operations: ingest, list experiments,
projects, totals, grants, record artifact, list artifacts.

### Codegen-clean: dart-dio + typescript-axios crashes fixed; SDK regen unblocked

The `Regenerate SDKs` workflow failed on every merge for a week. Root causes,
all fixed here (openapi-generator 7.14.0, pinned):

- `notify/openapi.yaml` — the `sync` query param on `/v1/notify/send`,
  `/v1/notify/send/sms`, `/v1/notify/send/email` declared `type: string` but
  `enum: [true]` (a YAML boolean). typescript-axios crashed with
  `ClassCastException: Boolean cannot be cast to String` on `notify_notifySend`.
  Enum value is now the string `'true'` (matches the declared type and the
  `?sync=true` wire form).
- `vector/openapi.yaml` — the `id` path param on
  `/v1/vector/collections/{collection_name}/points/{id}` used
  `oneOf: [integer, string]`. dart-dio crashed with
  `ClassCastException: JsonSchema cannot be cast to ComposedSchema` (composed
  schemas are not supported on parameters). Path params serialize as strings on
  the wire, so it is now `type: string` (pass `"42"` or a UUID) — faithful and
  gives cleaner SDK signatures than an `any`/`object` id.
- `.github/workflows/regenerate-sdks.yml` — the `dispatch` job authenticated
  with `SDK_DISPATCH_TOKEN`, which was never set (resolved empty → 401), so
  python/go/js were never regenerated; repointed to the canonical org `GH_PAT`
  (visibility: all, repo scope) and set `fail-fast: false`. The cpp/dart job no
  longer uploads to GitHub artifact storage (that quota was exhausted and is a
  dependency we refuse per the own-CI directive) — generation itself is the
  codegen gate.

All five generators (cpp-restsdk, dart-dio, go, python, typescript-axios) now
generate clean from `hanzo.yaml` with zero exceptions.

### Usage-cap + promo canonical types (HIP-0127 primitive algebra)

Curry-precise, code-faithful types for the spend-cap / promo money surface,
aligned to the primitive algebra (Meter = usage measured, Policy = cap-deny
verdict, Money = cents, Schedule = period window).

- `billing/openapi.yaml` — `/v1/billing/spend-alerts` self-service CRUD
  (`get` list, `post`, `patch {id}`, `delete {id}`) plus
  `/v1/billing/spend-alerts/authorize` (the per-request cap verdict the cloud
  metering gate consumes). Schemas `SpendAlert` (scope + `threshold` cap cents
  + `enforce` + derived `period`/`resetsAt`/`periodSpentCents`/`over`/`warn`),
  `SpendAlertCreate`, `SpendAlertUpdate`, `CapVerdict`, and `CapReason` — where
  `spend_cap` and `insufficient_balance` are DISTINCT reasons. Shapes match
  commerce `api/billing/spend_alerts.go` + `spend_cap.go` and the cloud
  `clients/metering` verdict.
- `admin/openapi.yaml` — `/v1/admin/promos` admin-set discount CRUD with the
  `Promo` (`percentOff`, `start`, `end`, `plans`, `active`), `PromoCreate`,
  and `PromoUpdate` schemas.

### request bodies — complete the write-op contract from real handlers

Filled the missing `requestBody` shapes on write ops (POST/PUT/PATCH), each
sourced from the real handler (`hanzoai/cloud/clients/*`, `iam`, `chat`,
`commerce`, `world`, `auto`, `flow`→`auto`, `platform`, and the `hanzoai/ai`
Beego controllers behind the `cloud`/`nexus` file/connection routes) — never
guessed. Coverage across the 68 specs: **832 → 871 of 955** write ops now carry
a `requestBody`.

The 84 write ops still without a body fall in two source-verified buckets, not
fabricated:

- **Body-less by design (61):** path/query/session RPC actions that read no
  body — admin suspend/reactivate/sweep; automations run/enable/disable (org is
  the validated cred, "NEVER from the body"); commerce
  capture/confirm/cancel/discard (captured amount is the stored order amount,
  never client-supplied); the Neon/Harbor/Meilisearch/Qdrant-proxied
  db/registry/search/vector actions; iam
  device/impersonation-exit/sso-logout/identification-verify; and the
  `cloud`/`nexus` query-param file/connection + signin/signout actions.
- **No live handler (23) — flagged, not authored:** iam
  user-keys/orders-cancel/invoice-payment/pay-order/place-order/refresh-engines
  (legacy swagger; billing moved to commerce); kms token-renew,
  token-auth-identity-tokens, webhook-test, secret-sync-trigger (absent from the
  Go KMS); framework install/submit/cancel (repo not in tree); flow
  solutions-apply, git-repos-pull (no such routes); bot skill undelete/stars
  (cloud proxies verbatim, upstream not located); analytics
  auth-logout/verify/sso + website-reset (Umami, no upstream in tree); paas
  doks-upgrade-ha, container-deploy (served by platform tRPC, not cloud).

Red-review fixes (fix-then-ship): `world/classify-event` corrected from POST to
GET with `title` (required) + `variant` query params, matching the handler
(`internal/world/handlers_ai.go:167`). The `cloud`/`nexus` `add-file`/`delete-file`
bodies now reference a dedicated request schema (`object.FileInput` / `FileInput`,
`owner`+`name` required) built from the real `ai/object/file.go` struct — instead
of the stale UI-tree response component `object.File`/`File`, which lacked
`owner`/`name`/`filename`/`store` and would have handed clients a wrong contract.
`delete-connection`'s `object.Connection`/`Connection` was verified correct against
`ai/object/connection.go` and left unchanged. `hanzo.yaml` + `CAPABILITIES.md`
regenerated via `merge.py` (3802 `$refs`, 0 dangling).

### 2026-07-11 — git: SSH transport, client-less push, ZAP note, sshUrl

Extended `git/openapi.yaml` to match the new native-git surface in
`hanzoai/cloud/clients/git`:

- **`/v1/git/keys` CRUD** (`registerGitKey`, `listGitKeys`, `deleteGitKey`) —
  per-user SSH public keys backing `git clone git@git.hanzo.ai:<org>/<repo>.git`.
  A key is stored with its SHA256 fingerprint (the global unique handle) and
  resolves, at SSH auth time, to its owning org.
- **`/v1/git/repos/{name}/push`** (`gitPush`) — client-less push: builds a
  commit from a set of posted files (UTF-8 or base64), advances the branch ref,
  and fires the git-push-to-deploy build exactly as a real receive-pack does.
  Creates the repo on first push.
- **`sshUrl`** added to the `Repo` schema (and the new `PushResult`): every repo
  now advertises both `cloneUrl` (HTTPS) and `sshUrl` (SSH, scp-style).
- **ZAP transport** documented in the spec description: the git control plane is
  also reachable over the shared ZAP-over-WebSocket plane at `/zap` (procedures
  `git/zap/{createRepo,listRepos,getRepo,deleteRepo,usage}`), thin adapters over
  the SAME core the REST handlers call — one implementation, two transports.

New schemas: `RegisterKey`, `Key`, `PushFile`, `PushRequest`, `PushResult`.
`hanzo.yaml` + `CAPABILITIES.md` regenerated via `merge.py`.

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
  identity-gated) from `clients/tasks`.
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

- 227 legacy RPC-style `/api/<verb>-<resource>` routes rewritten to
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
