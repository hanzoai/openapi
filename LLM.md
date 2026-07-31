# openapi

OpenAPI 3.1 specifications for all Hanzo services. Release generation
**V8 · Open Edition** (`info.version: 8.0.0`); the `/v1` route prefix is the
immutable compatibility contract. No backwards compatibility, no `/api/`
prefixes, no cross-brand references.

## Layout

- `capabilities.yaml` — the ONE canonical registry: every capability name, in
  exactly one domain (or `core`), plus `internal` / `collapsed` / `pending` /
  `review`. This is the single source of truth — `merge.py` READS it. Edit
  this, then run `python3 merge.py`.
- `CAPABILITIES.md` — GENERATED from `capabilities.yaml` by `merge.py`. A
  derived human index; never hand-edit (it carries a `GENERATED — DO NOT EDIT`
  header).
- `hanzo.yaml` — THE PUBLISHED DOCUMENT. Every SDK, doc site and tool generates
  from this file and from nothing else, at
  `https://raw.githubusercontent.com/hanzoai/openapi/main/hanzo.yaml`. Consumers
  PULL it; nothing here pushes to them. Aggregated by `merge.py` and grouped
  (`x-tagGroups`) from `capabilities.yaml`.
  **The repo is private: that URL is a 404 without `Authorization: Bearer
  $GITHUB_TOKEN`, and 200 with it.** A 404 for a private file reads as "the file
  moved", so a fetcher missing the header goes looking for the wrong bug —
  `hanzoai/js-sdk`'s `scripts/generate.sh:22` fetches it unauthenticated today
  and dies on `curl -f`. The in-repo path (`generate.py`, which reads the local
  file) needs no network at all and is the one to prefer.
- `<service>/openapi.yaml` — one self-contained spec per service.
- `cloud/openapi.yaml` — the ONE spec NOT authored here: hanzoai/cloud's own
  woven document, copied verbatim by `sync.py`. Source-true, and it wins (below).
- `sync.py` — the resync, one command: pull cloud's document, then merge.
- `flows.yaml` — the canonical example set. Six journeys, named by operationId,
  rendered by every SDK's `examples/` so they are the SAME journeys everywhere.
  `test_flows.py` is its gate: an id that stops resolving fails there, once.
- `shared/` — shared schemas usable by individual specs in their `components`.
- `generated/<name>.json` — specs a SERVICE EMITTED from its own routes. Not
  hand-written, not merged into the master; the measured counterpart of the
  contract of the same name (see below).
- `audit.py` — measures a generated spec against that contract.
- `README.md` — the front door.
- `CHANGELOG.md` — release notes.

`merge.py` enforces one-and-one-way as a build invariant: every present
`<service>/openapi.yaml` dir MUST map to exactly one entry across
`domains ∪ core` in `capabilities.yaml` (orphan / unlisted / double-listed →
build fails); a `collapsed` name must have NO spec dir; `internal` services are
excluded from the master and `x-tagGroups`; no two AUTHORED specs may claim one
route.

## The one source-true spec — cloud wins

`cloud/openapi.yaml` is hanzoai/cloud's own woven document, not a contract
written here. Cloud builds it by projecting each app's router into
`plugin/<app>/openapi.json`, weaving the projections, and gating the weave by
REGENERATING from source and failing on any diff — so it cannot describe a route
the binary does not serve, and cannot miss one it does. That is the property no
hand-written spec has.

So `merge.py` merges it LAST and lets it WIN every route an authored spec also
claims (298 of them today), explicitly rather than by where `cloud` falls in the
alphabet, which is how those paths used to resolve. The authored specs describe
what the OTHER binaries serve — iam, ai, kv, s3, search, commerce, world — and
cloud's document describes what cloud serves; `hanzo.yaml` is the union with
truth on top.

`python3 sync.py` is the whole resync: fetch `origin/main` in a hanzoai/cloud
checkout, write `origin/main:openapi.yaml` here byte-for-byte, re-merge.
`--check` reports staleness without writing. It is one-way BY CONSTRUCTION —
this repo reads a ref and never writes to hanzoai/cloud.

There is no `generated/hanzo.json` any more. It was a second, older copy of the
same emission, and measuring `hanzo.yaml` against a document `hanzo.yaml` now
CONTAINS is tautology dressed as a gate. `audit.py` still measures every service
that has one (`iam`), and the cloud half of that question is now answered
structurally instead of reported. `hanzoai/cli`'s offline fallback reads that
path — its successor is `cloud/openapi.yaml`, the same document fresher, and its
product registry can now come from `hanzo.yaml`'s own tags (below).

## Conventions

- Routing: every route is `/v1/<service>/<resource>`.
- IAM additionally exposes `/oauth/*` and `/.well-known/*`.
- Security: every operation uses `BearerAuth` (JWT from `https://hanzo.id`).
- `info.version: 8.0.0` on every spec (the V8 generation; the `/v1` path is the
  immutable contract).
- operationIds are BARE in each spec (e.g. `logs_query`); `merge.py` namespaces
  them `<svc>_` in the master. Never self-prefix a spec's operationIds.
- No cross-file `$ref`. Each spec is self-contained.
- No `deprecated: true`. Forward-only.
- No `/api/` prefix anywhere.
- Master grouping: `merge.py` emits `x-tagGroups` from the domains in
  `capabilities.yaml` (their `title`) plus a `Core` group; every present spec
  must belong to exactly one group or the merge fails.

## Tags — the document's own table of contents

`tags` and `x-tagGroups` describe the tags OPERATIONS CARRY. They used to
describe the spec DIRECTORIES: 55 names, four of which any operation carried, so
a doc site grouped 4 of 239 tags and every description it had belonged to a
heading nothing was filed under. Now every tag an operation carries is declared
once (260), described where the declaring spec said anything (210 — cloud's are
the owning Go package's doc synopsis), and grouped exactly once. The registry
still decides the movements: a tag's group is the domain of the SERVICE that
introduced it, so there is no second taxonomy to keep.

Three normalizations make a tag or an id mean one thing to a generator, all in
`namespace_ops`/`build_unified` and nowhere else: tags collapse to the first
(two tags = the operation emitted twice); tag SPELLING canonicalizes on
case/punctuation (`AI` and `ai` are one module, and the loser used to vanish);
and operationIds are made unique under the identity a GENERATOR uses — strip
punctuation, camel-case — not the string identity OpenAPI states.
`cloud_get_v1_pricing-policy` (GET /v1/pricing-policy) and
`cloud_get_v1_pricing_policy` (GET /v1/pricing/policy) are distinct strings and
the same Go type; the second is suffixed. An operation with no tag takes its
service's name rather than landing in `DefaultApi`, and an operation with no
`responses` — 668 of them, the untyped routes cloud publishes with nothing
invented — gets a `default` that says exactly that, so the document validates
without anyone inventing a schema.

## Validate

```bash
python3 -c "import yaml, glob; [yaml.safe_load(open(s)) for s in glob.glob('*/openapi.yaml') + ['hanzo.yaml']]; print('OK')"
```

## When changing a spec

1. Bump nothing — `info.version` stays at `8.0.0`; the `/v1` path is immutable.
2. Add new resources under `/v1/<service>/<resource>`.
3. Add components in the spec's own `components.schemas`. No `$ref` to
   other service yamls.
4. Examples must come from real responses.
5. If you add or remove a `<service>/openapi.yaml` dir, add/remove its name in
   `capabilities.yaml` (exactly one domain, or `core`) — the merge FAILS
   otherwise.
6. Update `CHANGELOG.md` with a dated entry under the v1.0.0 heading.
7. Run `python3 merge.py` (regenerates `hanzo.yaml` AND `CAPABILITIES.md`) and
   commit all three.

## Generated specs — a spec cannot describe a route its service does not serve

The 69 `<service>/openapi.yaml` files are hand-written, and a hand-written spec
drifts silently in both directions: it declares operations nothing serves, and
it misses operations that are served. `generated/` is the other reading — what
a binary emits from its OWN route table — and `audit.py` is the measurement
between the two. Nothing is overwritten by a generated spec until it measurably
covers the contract it would replace; `derived:` in `capabilities.yaml` is the
ratchet, and `audit.py --check` fails the build only for a name on that list.

| generated | emitted by | the ONE command |
|---|---|---|
| `iam.json` | `hanzoai/iam` — zip typed ops | zip's `App.OpenAPISpec()` |

Cloud left this table by being MERGED instead of measured — `sync.py` +
`cloud/openapi.yaml`, above. What its emission is has not changed: one document
folded from two readings of one router — the live route table (every operation,
its address, its product tag) over zip's typed-op registry (`zip.Get[In, Out]` →
JSON Schema, parameters, responses, plus the prose `cmd/zipdoc` lifts out of the
handlers' doc comments at build time). A route that is not a typed op appears
with its address and nothing invented, which is why `merge.py` gives those
operations a `default` response rather than a shape nobody knows.

Its `info` block comes from the emitting binary, so it carries the API contract
version (`v1`) rather than this repo's V8 release generation — a machine
artifact, not one of the authored specs the `8.0.0` convention governs. The
merged document keeps this repo's `8.0.0`.

## Who reads this repo — five consumers, two different contracts

An authored spec is not documentation. Five repos read these files as INPUT, and
they disagree about what an unserved operation means — which is the whole reason
`generated/` and `audit.py` exist.

| consumer | reads | filters against the live router? |
|---|---|---|
| `hanzoai/cli` | `hanzo.yaml` → `genspec` → `spec/cloud.json` → `genproduct` | YES — refutes per owned product |
| `hanzoai/console` | `hanzo.yaml` (proxy-allow test) | YES — asserts the proxy allows only declared paths |
| `hanzoai/cloud` agent-skills | `<svc>/openapi.yaml` via `skills.py` | **NO** |
| hanzo.ai oss-catalog | `capabilities.yaml` + `<svc>/openapi.yaml` | NO |
| `hanzoai/world` cloud-pulse | `hanzo.yaml` | NO |

**`skills.py` has NO liveness filter.** It opens `<svc>/openapi.yaml` directly
(never the wire) and emits a `SKILL.md` for every
authored operation. So an operation nothing serves still ships as a skill an
agent will call and get a 404 from. The CLI is protected by refutation; the
skills plane is protected by nothing but this file being true. Authoring a route
that does not exist is therefore not a harmless placeholder — it is a live
instruction to call a dead endpoint.

Annotating an unserved product was the previous answer, and it does not hold.
`genspec` refutes an authored operation only where the live router OWNS its
product, so a product the router has never heard of is refuted by NOTHING — it
survives every gate — and a comment at the top of a spec is read by no generator
at all. So the 18 products that were authored here and served nowhere are now
DELETED, not annotated: each was probed on its OWN authored routes, at
`api.hanzo.ai` and at its own host, and every one answered a route-level 404
(the router's own `404 page not found`, not an empty result from a live
handler). Deleting the source is the only move every consumer in the table above
obeys — including the skills plane, which obeys nothing else. A product returns
to this repo the day it is actually served.

## SDK generation — the ONE way (Stainless RETIRED, 2026-07)

The one interface is `hanzo.yaml`; the generator backend is
**openapi-generator** for EVERY language — no Stainless, no API key. Each
language repo owns its generation via a `scripts/generate.sh` that runs
openapi-generator against this `hanzo.yaml`, plus a `generate.yml` workflow
that regenerates + opens a PR on the `spec-update` repository_dispatch fired
by this repo's `regenerate-sdks.yml`.

| Lang | Canonical repo | Generator | Ships as | Driven by |
|------|------|-----------|---------|---------|
| Python | `hanzoai/python-sdk` | `python` (urllib3, pydantic v2) | `hanzoai` on PyPI (`pkg/hanzoai/cloud`) | `generate.py` |
| TypeScript | `hanzoai/js-sdk` | `typescript-axios` | `hanzoai` on npm (`src/`) | `generate.py` |
| Java | `hanzoai/java-sdk` | `java` (okhttp-gson) | `ai.hanzo:hanzo-java-cloud` | `generate.py` |
| Kotlin | `hanzoai/kotlin-sdk` | `kotlin` (okhttp4+gson) | `ai.hanzo:hanzo-kotlin-cloud` | `generate.py` |
| Ruby | `hanzoai/ruby-sdk` | `ruby` | gem | `generate.py` |
| Rust | **`hanzo-rs/sdk`** | `rust` (reqwest) | `crates/hanzo-client`, not on crates.io | its own `scripts/generate.sh` |
| Go | **`hanzo-go/sdk`** | `go` | `package hanzoai` at the MODULE ROOT, imported as `github.com/hanzoai/go-sdk` | its own `scripts/generate.sh` |

Three of those repos were RENAMED and answer through a redirect —
`hanzoai/go-sdk` → `hanzo-go/sdk`, `hanzoai/rust-sdk` → `hanzo-rs/sdk`,
`hanzoai/cpp-sdk` → `hanzo-cpp/sdk` — so a stale name still resolves and hides
the move. `gh api repos/<old> --jq .full_name` prints the new one. Go's module
path stays `github.com/hanzoai/go-sdk` regardless: that is what the proxy has
and what consumers require.

**When a language leaves `sdks.yaml`** — the boundary, so it is a rule and not a
mood: a row exists while the WHOLE invocation is expressible as data. A language
leaves when its invocation needs something that is not data. Both departures are
that, and neither is neglect.

- **go** needs the client at the MODULE ROOT, beside `go.mod` and `.git`, which
  `take` cannot express: `sdk()` rmtree's what it owns, so `{.: .}` deletes the
  repository.
- **rust** needs a `reqwest/api.mustache` override for 14 operations whose
  binary body is OPTIONAL (`Option<Vec<u8>>`, which no type mapping reaches —
  the problem is the Option, not the type). A template is a FILE; it must sit
  beside the invocation, and so must the `--type-mappings=file=Vec<u8>` it works
  with, or the halves drift apart.

Both then own their whole invocation in their own `scripts/generate.sh` — same
generator, same 7.14.0 pin, same `hanzo.yaml` pulled from here. What is NOT
allowed is a row here AND flags there: two declarations of one contract.
`hanzoai/js-sdk` and `hanzoai/java-sdk` are the other shape and the reason the
line matters — their scripts carry no flags at all, they exec `generate.py`, and
js-sdk removed its own copy only after the two disagreed about `modelPackage`
and about whether the client lands in `src/` or `src/cloud/`, which built an
orphan second copy of all 2143 files. Stripping THEIR properties out of this
file would recreate exactly that.

Both deleted rows would have written a SECOND client beside the shipped one
rather than updating it — `go` at `cloud/` with `packageName: cloud`, `rust` at
`crates/hanzo-cloud` — and both had been verified against a LOCAL checkout.
Check a `take` against the canonical remote.

Generator version pinned to **7.14.0** everywhere. The merged surface is
verified codegen-clean AND compile-clean for go / python / typescript-axios
(spec fixes that made it so: pubsub `ack_wait` int64; platform DeployJob /
CancelDeploymentJob oneOf → named subschemas; merge.py namespaces operation
tags + discriminator mappings per-service, collapses to one primary tag, gives
an untyped route a `default` response, and separates two operationIds the
generator could not tell apart). `validate` reports 0 errors, 0 warnings; the
generated Go client builds.

Every SDK also renders `flows.yaml` into its `examples/` — the same six
journeys, from the same operationIds, in every language. An SDK does not choose
its own examples any more than it chooses its own methods.

There is NO unified `hanzoai/sdk` multi-lang monorepo generator — that repo's
`gen/` is the retired SECOND way; `hanzoai/sdk` is CLI-only now.

### Remaining spec-coverage gaps — measured, not remembered

`python3 audit.py` is the answer to "how far has a contract drifted from its
binary", and it replaces every anecdote that used to live here. It reads
`<name>/openapi.yaml` against `generated/<name>.json`, so both numbers move on
their own the moment either side changes. Cloud is no longer one of its rows:
its emission is merged, so the drift it measured is gone rather than reported.
`iam` remains, and it is the shape of the work left.

Read the columns as three different bugs. `missing` = the contract declares
operations nothing serves, so every SDK ships methods that 404. `undeclared` =
the routes serve operations the contract never named, so no SDK can reach them.
`prose lost` = an operation both sides have, where only the hand-written side
has the words — the reason a generated spec does not simply overwrite a contract
on the day it first covers it, and the reason cloud's emission could be merged
the day it started carrying prose of its own.

The SDK-generation surface is the FUSED `api.hanzo.ai/v1` binary. `merge.py`
unions the per-service specs into it, cloud's document last.

### An empty field from the winner must not delete a populated one

This was the resync's worst defect and it survived two rounds of measurement
here, because I measured `parameters` and never looked at `requestBody`.

`merge.py` took the whole operation OBJECT from `cloud/openapi.yaml` wherever it
took a route. But an untyped route's emission is an address and nothing else, so
that replaced described operations with undescribed ones: **47 request bodies**
and **135 response sets** (100 of them reduced to the synthesized `default`)
left the document. `POST /v1/authz/check`, `POST /v1/agents/{ref}/run`,
`POST /v1/kms/secrets`, the five agent-session control ops. Downstream the CLI's
typed-flag operations fell 574 → 515 and its raw `--data` fallbacks rose
187 → 378; `hanzo kms secrets create` lost the `value` field its stdin-only
guard exists to protect, so the guard had nothing to guard.

The error was reading cloud's silence about an untyped route as EMPTY when it
means UNKNOWN. `fuse()` now overlays field by field: TRUTH still wins existence,
operationId, tags and prose unconditionally, and wins any field it POPULATES —
it just no longer deletes by being silent.

`requestBody` and `responses` are kept by `KEEP`; `parameters` by `union()`,
because their emptiness is ambiguous in one extra way. TRUTH omitting the field
means unknown. But TRUTH declaring ONLY the path parameters means the same
thing — the weave derives those from the route template, so `[{id}]` is what an
untyped route emits whether or not it accepts twenty query parameters. Reading
that as a complete list is the identical silence-for-emptiness mistake one level
down, and it cost `GET /v1/integrations/{provider}/callback` its `code` and
`state` — the whole OAuth handshake — while a sibling route with no path
template kept everything. Same evidence, opposite outcome, decided by whether
the URL happened to contain a brace. So parameters union by name, TRUTH's
definition winning any name it defines.

**An earlier version of this section claimed query parameters were deliberately
dropped. The code never did that**, and the claim was wrong on the merits too. A
rule written here that the code does not implement is worse than no rule; the
check that caught it was reading the published document back and noticing
`GET /v1/kms/secrets` still had `path` and `env`.

Verified against `d86248f` (the pre-resync document): **0 parameters and 0
request bodies that existed then are missing now**, and 0 duplicate parameters.

That last number needed its own check, and the reason is worth keeping.
Uniqueness is per OPERATION and spans both levels — a path item's `parameters`
apply to every operation under it — and the two sides habitually disagree about
where the path parameter goes: authored specs hoist `{id}` to the item, the
weave emits it per operation. Unioning without accounting for that left 115
operations declaring `{id}` twice. **openapi-generator's validator does not
resolve `$ref` parameters, so it reported zero errors on a document that was
invalid** — green and wrong at the same time. Anything the gate cannot see has
to be measured here instead.

The counter on every build is `kept` — 242 authored shapes that are load-bearing
because cloud took a route without declaring one. It is not a gate. It is the
number that **falls to zero as the typing lane converts those routes**: a typed
`zip.Get[In, Out]` carries body, parameters and response from the code itself,
`sync.py` picks it up, and the authored shape stops being needed. All 47 body
losses were routes cloud serves UNTYPED and **zero were typed-with-no-body**, so
there is no emission bug to chase — only routes to type.

**Bucket (a) — 47 routes whose only body description lives here.** Highest SDK
value, because no body means no call: `POST /v1/authz/check`,
`POST /v1/agents/{ref}/run`, the five agent-session controls (`events`,
`message`, `pause`, `resume`, `stop`), `POST /v1/kms/secrets`, `POST /v1/exec`,
`POST /v1/upload`, `POST /v1/functions` + `/v1/functions/{name}/invoke`,
`POST /v1/projects` + `fork` + `{slug}/deploy`, `POST /v1/sites` + `sites/deploy`,
the four `evals` creates, `POST /v1/notify/send{,/email,/sms}`,
`POST /v1/o11y/query{,_range}`, `POST /v1/billing/gpu-charge`,
`POST /v1/billing/spend-alerts` + `PATCH .../{id}`, `POST /v1/affiliates/apply`
+ `attribute`, `POST /v1/admin/affiliates/{id}/{approve,payout}`,
`POST /v1/automations/flows/{id}/operations` + `runs/{id}/resume`,
`POST /v1/machines`, `POST /v1/ml/models`, `POST /v1/security/scans`,
`POST /v1/tracker/projects` + `{key}/issues`, `POST /v1/framework/{doctype}` +
`PUT .../{name}`, `POST /v1/integrations/slack/{commands,events}`,
`POST /v1/kms/auth/login`, `POST /v1/projects/{slug}/deployments/{id}/complete`,
`PATCH /v1/projects/{slug}`.

28 routes rest on authored query parameters; `GET /v1/ml/models` is the one that
is a real cloud bug rather than an untyped route — it IS typed, and its `In`
struct is simply missing `stage` and `search`.

| route | parameters the binary does not declare |
|---|---|
| `GET /v1/admin/affiliates` | `limit` |
| `GET /v1/admin/referrals` | `limit` |
| `GET /v1/agents/sessions/stream` | `root` |
| `GET /v1/billing/balance` | `currency` |
| `GET /v1/billing/gpu-eligibility` | `amountCents`, `minPrepaidCents`, `currency` |
| `GET /v1/billing/spend-alerts/authorize` | `user`, `project`, `service`, `amount`, `pv`, `currency` |
| `GET /v1/billing/usage` | `start`, `end` |
| `GET /v1/evals/scores` | `runName`, `limit` |
| `GET /v1/functions/metrics` | `range` |
| `GET /v1/functions/{name}/invocations` | `limit` |
| `GET /v1/git/{org}/{repo}/info/refs` | `service` |
| `GET /v1/integrations/slack/link` | `state` |
| `GET /v1/integrations/slack/link/callback` | `code`, `state`, `error` |
| `GET /v1/integrations/slack/link/slack` | `code`, `state`, `error` |
| `GET /v1/integrations/{provider}/callback` | `state`, `code`, `error` |
| `GET /v1/kms/secrets` | `path`, `env` |
| `GET /v1/ml/models` | `stage`, `search` — TYPED op, `In` struct incomplete |
| `POST /v1/notify/send` | `sync` |
| `POST /v1/notify/send/email` | `sync` |
| `POST /v1/notify/send/sms` | `sync` |
| `GET /v1/o11y/vm/query` | `query` |
| `GET /v1/o11y/vm/query_range` | `query`, `start`, `end`, `step` |
| `GET /v1/platform/fleet` | `env`, `health`, `drift` |
| `POST /v1/platform/fleet/{app}/deploy` | `env` |
| `GET /v1/research/artifacts/{sha256}` | `project` |
| `GET /v1/security/findings` | `scanId`, `minSeverity`, `limit` |
| `GET /v1/security/scans` | `limit` |
| `GET /v1/websearch/search` | `q`, `format` |

Two of those are worse than a missing filter. The three OAuth callbacks take
`code` and `state`, which is the whole protocol, and `GET /v1/o11y/vm/query`
takes `query` — a query endpoint that declares no query. If the server honours
them (it presumably does, or they would not have been authored), the typed
input is the one place that makes them callable from any client.

### The next quality lever — 637 of 2454 operations declare no 2xx schema

**It was 728, and 91 of those were self-inflicted** — authored response schemas
the whole-object handover had deleted, restored by `fuse()`. Every number this
repo reported for that gap before the fix (754, 728, 696) was measuring its own
damage along with the real thing. The honest figure is 637, 26%, and it is a
measure of cloud's typed coverage rather than of anything editable here: the
remainder is the `default` synthesized for routes the weave publishes with an
address and nothing else, so it still rises with every untyped route cloud adds.

The corollary is worth keeping: a number that only ever went up should have been
suspicious. This one went up because the pipeline was eating its own inputs.

**What it costs is language-dependent, and worse than it looks.** Go returns
`*http.Response`, so the body is still there and a caller can decode it by hand.
**Rust returns `Result<(), _>` and DROPS THE BODY ENTIRELY** — the response is
unreachable from the generated client at any effort. An operation with no
response schema projects to a method that returns nothing, which is a method not
worth calling.

`/v1/billing/balance`, `/v1/billing/usage` and `/v1/agents/{ref}/run` — the
three canonical `flows.yaml` operations two SDK lanes had to hand-write
raw-decode helpers for — are now OUT of the set: their authored schemas were
among the 91 restored, and `agents/{ref}/run` has its request body back too.
Those helpers can be deleted. 16 of the 25 `/v1/billing` operations remain in
the gap, and 602 of the 637 are cloud's.

**The lever is in hanzoai/cloud, not here.** A route becomes typed when its
handler becomes a `zip.Get[In, Out]`; the weave then carries the schema and
`sync.py` picks it up with no change in this repo. Doing it here instead would
mean inventing shapes, which is the one thing the `default` exists to refuse.
Two generator-blocking defects the SDK lanes fixed at the source ARE holding:
`/v1/platform` is 41 operations with 0 missing `responses`, and
`ai_ChatCompletionResponse.choices` items now `$ref` `ai_ChatChoice`.

### operationId is the SDK method name — and 249 of them changed

Say it plainly: the resync renamed methods in every language, and it was a
consequence I did not enumerate at the time. Where cloud's woven document took a
route an authored spec also described (366 operations), the document now carries
cloud's operationId. For 117 of those, cloud's id is its handler's own name
(`adminAnalytics`) and nothing was lost. For **249**, cloud's id is synthesized
from the route, so `affiliates_adminListAffiliates` became
`cloud_get_v1_admin_affiliates` — `AdminListAffiliates()` became
`CloudGetV1AdminAffiliates()` for every consumer.

It stands, deliberately, and the reason is stability rather than beauty. A
route-derived id is a total function of the `/v1` path, which is the immutable
contract: it cannot move unless the route moves. A hand-authored id is owned by
a spec that no longer describes the route, so it changes whenever that spec is
edited and VANISHES when the spec is deleted — and this repo deletes specs
routinely, which would make the same break happen again, later, silently. The
route-derived name is also the one the MCP door already uses (a tool name is the
operationId minus its `<service>_` prefix), so one name identifies an operation
in the SDK, in the tool catalogue and in the URL.

The break is therefore once, now, and cannot recur for these operations. Pin
against the document, not against a remembered method name.

### What is still authored and not served — and how to tell

Two authored surfaces `flows.yaml` had to route around, both measured at
`api.hanzo.ai`: the KV VALUE plane (`/v1/kv/keys/{key}` — `kv_setKey`,
`kv_getKey`, `kv_deleteKey`) and the automations MCP door
(`/v1/automations/mcp` — `automations_mcp`).

The tell is the method spread, and it is worth learning because a bare 404 is
ambiguous — a live handler says "not found" too. A route the binary HAS replies
401 or 403 unauthenticated: it routed, then refused (`/v1/kv`, `/v1/kv/namespaces`,
`/v1/tools`, `/v1/billing/balance`). A route it does NOT have replies 404 to GET
and **405 method not allowed** to PUT, POST and DELETE, because the only thing
matching the path is a GET-only wildcard.

**Probe the method the route declares, not GET** — and this is the correction,
not a nuance. A POST-only route ALSO answers 404 to GET, so a GET probe cannot
tell "absent" from "wrong verb". `POST /v1/mcp` answers 200 with 796 tools,
unauthenticated, while `GET /v1/mcp` is 404; reading that 404 as absence is how
the fleet's one MCP door went undeclared, and how this file previously said it
did not exist. The two surfaces above survive the corrected test — every method
their specs declare was probed, and none of them routed — but one verb is never
a liveness probe, and a single GET has now been wrong once in this repo.
