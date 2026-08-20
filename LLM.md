# openapi

**This repo does not decide what the Hanzo API is. It publishes what the API
says about itself.**

`hanzo.yaml` is OUTPUT. It is derived, by `publish.py`, from hanzo-inc/cloud's own
emitted `openapi.yaml` at one pinned release. To change the API you change the
code in hanzo-inc/cloud; there is nothing here to edit that would make a route
exist, and nothing here that can describe one that does not.

```
hanzo-inc/cloud  typed ops + handler doc comments
     │           (projected per app, woven, gated by regenerate-and-diff)
     ▼
  openapi.yaml @ a release   ── the ONE authority on what exists
     │
     ▼  publish.py            ── six codegen rules; no new operations, no new prose
  hanzo.yaml + CAPABILITIES.md + .spec-lock   ── this repo's whole output
     │
     ├─→ generate.py → python · typescript · java · kotlin · rust · go · ruby · php
     ├─→ skills.py   → /.well-known/agent-skills/  (hanzo · lux · zoo)
     └─→ the doc site, hanzoai/console's proxy-allow test, hanzoai/world
```

## The one command

```bash
python3 publish.py                   # re-pin to hanzo-inc/cloud's main, derive, write
python3 publish.py --ref v1.801.383  # re-pin to one release
python3 publish.py --check           # THE GATE: re-derive at the pinned ref and diff
python3 publish.py --current         # has cloud's document moved past the pin?
```

It reads a hanzo-inc/cloud checkout (`--cloud`, `CLOUD_DIR`, default `../cloud`)
and writes exactly three files: `hanzo.yaml`, `CAPABILITIES.md`, `.spec-lock`.
Nothing is ever written back to hanzo-inc/cloud — the traffic is one-way by
construction, this repo reads a ref.

## What was here before, and what it measured out to

52 hand-authored `<service>/openapi.yaml` specs, merged with cloud's document
laid on top. Measured at `hanzo-inc/cloud@v1.801.383`, both documents loaded and
keyed by (METHOD, path):

| | |
|---|---:|
| the hand-merged master | **2093** operations |
| cloud's emitted document | **2333** |
| shared | **1908** |
| **master-only — nothing cloud serves under that name** | **185** |
| **cloud-only — served, and the master never mentioned it** | **425** |

Both halves are the same bug. The master described 8% of an API that does not
exist and missed 18% of the one that does, and it was the input to seven SDKs,
the doc site, the MCP tool catalogue and the agent-skills plane.

### The 185, triaged — with a nonsense-sibling control on every probe

Each was probed at `api.hanzo.ai` with **its own method** (a POST-only route
answers 404 to GET, so a GET sweep cannot tell "absent" from "wrong verb"), and
each probe carries a CONTROL: the same address with `-zzq9` appended to its last
literal segment. 119 are addresses no live route pattern covers; 66 sit under a
`{wildcardN}` relay door, which by construction answers identically for a real
path and an invented one and therefore decides nothing.

| verdict | n | reading |
|---|---:|---|
| **ABSENT** — real 404, control 404 | **36** | refuted. Nothing serves this. |
| **UNFALSIFIABLE** — real ≠ 404, control identical | **44** | a gate or a door answered, not a route |
| **SERVED** — real ≠ 404, control 404 | **39** | live, and cloud's document lacks it |
| absorbed by a `{wildcardN}` door | 66 | unfalsifiable by construction |

**A 404 on both sides IS a refutation, and it is the only way absence can ever be
shown.** The control exists to stop a 401/403/200 being read as existence — a
relay answers those for anything. It does not make 404 mean nothing; treating it
that way makes absence unprovable by construction, which would be a rule about
falsifiability that is itself unfalsifiable. `hanzoai/cli`'s drift gate settled
this from the other side: 404 refutes, 403 does not.

The 36 refuted: 8 `search` (Meilisearch's `dumps`, `export`, `keys`,
`multi-search`, `network`, `snapshots`, `swap-indexes`, `webhooks`), 6 `s3`
(`PUT /v1/s3/{bucket}` and its five `?policy`-style subresources), 12 `o11y`
(`api/v2/{healthz,livez,readyz}`, `ingestion`, `vm/query`, `vm/query_range`, and
six methods of an authored `{wildcard1}`), 3 `kv` (`batch`, `clusters`,
`namespaces`), 3 `billing` (`gpu-charge`, `gpu-eligibility`, `payment-methods`),
`POST /v1/admin/promos`, `GET /v1/edge/nodes`, `GET /v1/models/{model}`.

The 44 unfalsifiable are almost all one thing. `apps/product` installs
`requireKey` middleware on the `/v1/search` and `/v1/vector` subtrees, so every
address under those prefixes 401s BEFORE routing — real and invented alike —
while cloud registers exactly four routes under each (`/indexes`, `/stats`;
`/collections`, `/stats`). The master's 40 `search` and 15 `vector` operations
were verbatim copies of Meilisearch's and Qdrant's own APIs, describing an
upstream this fleet proxies nothing to. Decided by SOURCE rather than by probe,
they are absent too.

**The 39 SERVED are the honest cost, and every one is a hanzo-inc/cloud defect** —
itemised under "Handed to hanzo-inc/cloud". None is fixable here: authoring them
back would restore exactly the property this change removes.

### Fourteen more that were not even the right API

`account.yaml`, `auth.yaml`, `checkout.yaml`, `collection.yaml`, `coupon.yaml`,
`form.yaml`, `order.yaml`, `product.yaml`, `referrer.yaml`, `site.yaml`,
`store.yaml`, `transaction.yaml`, `user.yaml`, `variant.yaml` — **Swagger 2.0**
documents for `host: api.hanzo.io`, read by nothing in this repo or the fleet.
`api.hanzo.io` is a parked domain today: HTTPS presents no certificate for the
name (`tlsv1 unrecognized name`), and over HTTP `/account`, `/store` and the
control `/account-zzq9` all return the same registrar lander HTML. Deleted.

## `publish.py` — the six rules, and why each exists

A projection may not add an operation, may not remove one that is served, and may
not invent prose. It may only make the one document generatable. The measurement
that says the projection is needed at all:

```
openapi-generator-cli 7.14.0 validate -i <cloud openapi.yaml>  → [error] Spec has 1012 errors
                              generate -g typescript-axios     → SpecValidationException, 0 files
same, against hanzo.yaml                                       → 0 errors; api.ts written
```

| # | rule | n | the failure it prevents |
|---|---|---:|---|
| 1 | drop TRACE | 26 | the JVM generator writes `RequestMethod.TRACE` beside an enum that stops at PUT, so no Java or Kotlin client compiles. They are wildcard relays projecting every method their router matches — a fact about the router, not a client surface, and one every edge disables anyway. |
| 2 | drop `compat`-tagged ops | 23 | the SERVING binary declares that tag for a legacy address it keeps reachable. Dropping it respects the declaration: the served surface is unchanged, and the published one says each thing once instead of shipping two spellings of one operation. |
| 3 | two tags → the first | 23 | a generator emits one class per tag, so a two-tag operation is emitted twice under one identifier (`ApiPricingGetFullPricingRequest redeclared`). |
| 4 | no tag → `x-app`, else the `/v1/<product>` segment | 42 | untagged is not ungrouped, it is `DefaultApi`. |
| 5 | no `responses` → a `default` that says so | 986 | **the 1012.** A `default` with no content states exactly what is known: the route answers, and its shape is not declared at the source. Inventing a schema is the one thing this must not do. |
| 6 | operationIds unique under `genid`, original kept as `x-id` | 1 | unique as STRINGS is what OpenAPI asks and it is not enough — every generator strips punctuation and camel-cases, so `deleteSession` and `DeleteSession` become one name and the client declares one request type twice. |

Rule 6 is the one rule that CHANGES a value rather than dropping or adding one,
and an operationId is not only a codegen identifier — it is the **wire name of an
MCP tool**. `DELETE /v1/o11y/sessions` is published as `DeleteSession_2` and
served as `DeleteSession`, and the suffix went out verbatim in the tool catalogue
of three client distributions, naming a tool `POST /v1/mcp` answers to no such
name. So the rename now records what it renamed: `x-id` is the id hanzo-inc/cloud
emitted, written only where the two differ, and `tools.py`'s `wire()` is the one
place a tool takes its name. Measured against the live door: 1299/1323 before,
1300/1323 after. The collision itself belongs upstream — two operations whose ids
differ only in case are one name to every generator there is.

There was a seventh, and it is gone, which is what the end state looks like when
it arrives one rule at a time. Cloud's emission used to declare **no security
scheme**, so a client generated from it sent no `Authorization` header and every
call 401'd; `publish.py` added `bearerAuth` and a document-level `security`.
Cloud declares both halves itself now — `bearer`, with the header spellings it
accepts — and the addition stopped adding and started **corrupting**: the
`setdefault` no longer fired while the requirement it wrote still did, so the
published document required a scheme it did not define. Measured on the
generated typescript: 2498 bearer call sites from cloud's document, 0 from the
projection, leaving 191 files importing a credential helper none of them called.
`test_a_client_can_authenticate` now asserts the pair agrees, whoever supplies
it.

**Every one of these belongs upstream.** The day cloud's emitter writes the
`default` and tags its own untagged routes, `publish.py` shrinks to nothing and
`hanzo.yaml` becomes a byte copy — or this repo becomes unnecessary. That is the
intended end state, and rule 5 alone is 90% of what is left.

### Three versions, three meanings, and they must not be collapsed

- the **API's** version is `/v1`, in the path, immutable;
- the **emitting release** is `info.x-spec.ref` (and `.spec-lock`), and the rule
  for choosing it is not "the newest": it is the newest release `api.hanzo.ai`
  fully answers for, which `--served` decides. Cloud's `main` runs ahead of the
  deployment — measured at 108 commits and 60 published-but-unserved operations —
  so pinning there would publish 60 dead endpoints to every SDK, doc page and
  agent skill;
- `info.version` is **8.0.0**, the generation of this PUBLICATION, and it is what
  every SDK's package version is cut from (`sdks.yaml`'s rust row pins
  `packageVersion` to it). It may only move forward: putting the cloud ref there
  would publish `1.801.383` over an `8.x` npm package and be rejected as a
  downgrade.

## `capabilities.yaml` — the one editorial decision left here

The document says which product owns an operation. It does not say which DOMAIN
a product belongs to when a reader is shown the whole API at once, and there is
no source in the code for that — a doc site's movements are a taste decision
about a reader. So `capabilities.yaml` groups the document's tags into nine
domains, and `publish.py` gates it BOTH ways: a served capability it does not
group fails the publish, and a name it groups that the document does not carry
fails too. The list cannot describe an API other than the one served; it can only
be a better or worse arrangement of it.

`internal`, `collapsed`, `pending`, `review` and `derived` are gone with the spec
dirs they were about. A capability appears the release it starts being served and
leaves the release it stops.

## The gates

| gate | question | needs | where |
|---|---|---|---|
| **`publish.py --served`** | **is every published operation one `api.hanzo.ai` answers for?** | **nothing** | **`hanzo.yml` `test:`, every build** |
| `test_publish.py` | does the committed artifact hold the six rules, offline? | nothing | same |
| `test_flows.py` | does every operationId `flows.yaml` names still exist? | nothing | same |
| `test_skills.py` | is the skills surface deterministic and well-formed? | nothing | same |
| `publish.py --check` | is `hanzo.yaml` what its own pinned input projects to? | a hanzo-inc/cloud checkout | `spec sync`, every push and PR |
| `publish.py --current` | has cloud's document moved past the pin? | same | same workflow, hourly clock only |
| `skills.py --check` | did `dist/` drift from the document? | nothing | on demand |
| `generate.py --check` | did a committed client drift from the document? | nothing | each SDK repo's own CI |

**The `needs` column is the whole lesson, and it was learned the expensive way.**
`--check` is the better question and it was the only one gating this artifact, so
when it turned out it could not run, nothing did. Twice, for two different
reasons, and the second one wore the first one's clothes.

FIRST, NOBODY COLLECTED IT. Both callers had been moved to `.hanzo/workflows`,
which only git.hanzo.ai collects, and at the time nothing on git.hanzo.ai
collected a push to this repo: it answered `ls-remote` and refused `push` with
*mirror repository is read-only*, pulling from github rather than receiving from
anyone, so `gh workflow list` returned nothing at all. That is fixed —
git.hanzo.ai is where this repo lives now, and `.hanzo/workflows` is where its
callers run.

SECOND, IT ASKED THE WRONG REPOSITORY. `SPEC_REPO` said `hanzoai/cloud`, and
that name now belongs to the re-rooted OSS core: twelve commits on `main`, no
shared ancestor with the product, no `openapi.yaml` anywhere in it. Being
public, the checkout SUCCEEDED and the failure arrived a step later as
publish.py's `no remote of .cloud carries openapi.yaml on 'main'` — which the
workflow discarded and replaced with a fixed sentence saying `hanzo.yaml` had
been hand-edited. It had not been: re-derived at its own pinned ref, the
committed artifact was byte-for-byte what that ref projects to. **A step that
overwrites a precise diagnosis with a canned one sends every reader hunting for
a diff that does not exist**, and it is why neither `::error::` wrapper exists
any more: publish.py says what is wrong, and `set -e` fails the step.

THE CREDENTIAL IS STILL THE OPEN ONE. hanzo-inc/cloud is private and in another
org, and the per-job token Hanzo Git mints reads the run's OWN repository and
anything public — nothing else. Measured on hanzoai/python-sdk run 91449, which
named the right repo and still took `curl: (22) ... 404` on the raw read. So
`spec sync` takes `HANZO_GIT_TOKEN`, the one name in this fleet for a credential
that reads git.hanzo.ai, and says which credential is missing rather than
letting `actions/checkout` report a private repo as "repository not found". It
is not sealed yet, and until it is, `--check` runs by hand and `served` holds
the line.

Measured while none of it ran: the pin was **81 hanzo-inc/cloud commits stale**,
`hanzo.yaml` carried a **hand edit** (a route deleted straight out of a generated
file), `--check` exited 1, `--current` exited 1, and `test_publish.py` failed —
three red gates on `main`, none of them running anywhere. The published document
advertised **19 operations nothing serves**, including `POST /v1/admin/credits`,
a money mint hanzo-inc/cloud had deleted.

`--served` is deliberately the WEAKER question, because it needs nothing: cloud
serves its own emission unauthenticated at `/v1/openapi.json`, so the running
deployment refutes a published route by itself. It runs in `hanzo.yml`'s `test:`
block — the one lane both hanzoai/ci and platform.hanzo.ai read — and it is now
the gate holding the line. Same shape and same rule as hanzo.ai's
`scripts/audit-catalog.mjs`, which gates the same document: one direction only,
and never fail on an unreachable API.

`--current` is on the clock and not on pushes deliberately: a stale pin is not a
broken artifact, and failing an unrelated PR for it trains people to ignore red.

### Which remote is cloud's main — discovered, never named

`--current` asked `origin/main` for two years, and `origin` is not a fact about a
checkout, only the name a clone happened to use. hanzo-inc/cloud answers on several
remotes and they are NOT one lineage: where `origin` is the GitHub OSS mirror,
`origin/main` holds no `openapi.yaml` at its root at all, so the question went to
a repository that does not carry the document and could only die or agree by
accident. It died, quietly, and the pin drifted 24 releases while nothing went
red. **A gate that cannot fail is not a gate**, and that is the whole reason
`--current` now resolves the remote instead of assuming it: fetch every remote,
keep those whose `main` holds the document, take the one that contains the
others. On a normal clone that is `origin`; on this fleet's checkouts it is
whichever remote points at git.hanzo.ai, and neither is written down anywhere.
The same resolution is the default when re-pinning, so `python3 publish.py` with
no `--ref` can no longer publish from the wrong lineage either.

### The known weakness of `--served`, stated rather than discovered

It ASKS THE NETWORK IN CI, and `hanzoai/cli`'s `driftgate` — the same gate for
the same document, one repo over — argues against exactly that: *"a gate that
needs the network in CI gets switched off, and a switched-off gate is worse than
none."* Its answer is to decomplect the two halves: `--refresh` asks and writes
`spec/live.json` (evidence, checked in), and the default RULES over that
evidence with no network at all.

That is the stronger shape and this is not it. `--served` never FAILS on an
unreachable API — no network, no verdict, exit 0, said loudly — which trades
driftgate's problem for a quieter one: an outage does not turn the build red, it
turns the gate OFF for that run, and nothing distinguishes a passing build from
an unasked one except the word NO VERDICT in the log.

It is the right trade HERE, for a reason that is about this repo rather than
about gates: the evidence driftgate commits would be a second derived copy of
the served path set, in the repo whose entire defect was keeping a second copy
of the API by hand. `hanzo.ai/scripts/audit-catalog.mjs` gates this same
document the same way for the same reason. If an outage is ever measured to have
hidden a real drift, take driftgate's shape — the ask and the rule are already
separate functions here (`refuted()` fetches; the caller decides).

## Who reads this repo

| consumer | reads | can it name an unserved route? |
|---|---|---|
| `hanzoai/{python,js}-sdk` | `hanzo.yaml` via `generate.py`, unless a `.spec-lock` names a release — then cloud's own document | no |
| `hanzo-go/sdk` | `hanzo.yaml` via its own `scripts/generate.sh` | no |
| `hanzo-rs/sdk` | `hanzo-inc/cloud@ref:openapi.yaml` directly, from git.hanzo.ai — it passes `--skip-validate-spec` and `cargo build` is the real gate | no |
| `hanzo-inc/cloud` agent-skills | `hanzo.yaml` via `skills.py` | no |
| `hanzoai/console` proxy-allow test | `hanzo.yaml` | no |
| `hanzoai/world` cloud-pulse | `hanzo.yaml` | no |
| the doc site | `hanzo-inc/cloud@ref:openapi.yaml` directly, from git.hanzo.ai | no |
| `hanzoai/cli` | `hanzo-inc/cloud@ref:openapi.yaml` directly — it needs raw existence, not codegen | no |

**The doc site left this document, and the reason generalises.** The six rules
make a document GENERATABLE; a doc page needs none of them, because it reads
paths, tags, summaries and schemas, every one of which cloud emits itself. So the
projection bought the reference nothing and cost it currency — its pin sat 19
cloud releases back, rendering four relay-door products with twelve operations
each where the document has one, one, one and two. A consumer belongs here only
while it needs what `publish.py` adds. Codegen does; prose does not.

**Reading the document is a git.hanzo.ai operation now.** `generate.py`'s
`fetch()` asked api.github.com, which mirrors hanzo-inc/cloud thousands of
commits behind and does not serve openapi.yaml at all, so it could only 404 —
and it reported that 404 as a missing credential, which sent readers hunting for
a token to fix a host with no file on it. One host, one credential:
`git.hanzo.ai/v1` and `HANZO_GIT_TOKEN`, the same name hanzoai/ci's client lane
hands its own read.
A fallback chain across hosts holding different documents is not a fallback, it
is a coin flip about which document you get.

**The skills plane is why "no" has to be structural.** `skills.py` emits a
`SKILL.md` per capability and nothing downstream re-checks it: no refutation
step, no liveness filter, no human between the file and the request. A skill for
an operation nothing serves is not a stale document, it is a working instruction
to an agent to call a dead endpoint. It reads `hanzo.yaml` now, cut by the
operation's own TAG — never by path prefix, because the two disagree wherever a
binary answers at a noun that is not its name (`/v1/chat/completions` is `chat`).
506 skills across 159 capabilities × 3 brands.

## Handed to hanzo-inc/cloud — the whole cost of this change, itemised

Nothing below is fixable in this repo, and every item is measured at
`cloud@v1.801.383`.

### 1. Served and undescribed — the 39

- **17 are `/v1/ai/*`**: `deployments` (7), `signin-sessions` (7),
  `usages/{by-user,user-names}` (2), plus the ones the emission still calls
  `applications`/`sessions`. `apps/ai` projects that product from a committed
  `plugin/ai/openapi.json` subset instead of the mounted plugin's live registry —
  **a second authority INSIDE cloud, the same disease one level down**. This is
  the highest-value fix on the list, and it also collapses ~11 tags in
  `capabilities.yaml` (`query`, `query_multiple`, `install-patch`, `dev-bridge`,
  `wecom-bot`, `traffic`, `provider-flags`, `docs`, `health`, `feedback`,
  `documents`) that are that seam's hand-declared shrapnel rather than products.
- **`POST /v1/mcp`** — 200 with the tool list, control `/v1/mcp-zzq9` 404, in no
  document. The fleet's one MCP door is undeclared, which cost `flows.yaml` its
  `tools` example. Note it answers 404 to GET, which is why a GET-only sweep has
  twice concluded it does not exist.
- **`GET /v1/{world,evals,referrals}/health`** — 200, controls 404, undescribed.
- **`GET /v1/o11y/services`** — 405, control 404: the address routes, and the
  verb is wrong on one side or the other.
- **`GET /v1/s3/` and `GET /v1/s3/{bucket}`** — 403 vs control 404. Cloud
  registers `/v1/s3/{name}` (provisioning) and `/v1/s3/buckets/…` (storage);
  `manifest/apps.go:83` already notes those two owners share one prefix.

### 2. Relay doors that can only ever emit `{wildcardN}` — 66 addresses

`bot` (32), `dns` (16), `tasks` (8), `collections` (5), `kms` (2), and one each
of `download`, `exec`, `files`. Each is a single `app.All("/v1/<x>/*")`
registration, so there is no per-operation site and the document can only show
the door. The fix is projecting the mounted registry, exactly as for `apps/ai`;
until then these addresses are unknowable from outside, and the honest document
says so rather than guessing a list.

### 3. Shapes only the deleted master had — 302 operations

Not prose: **the master carried ZERO summaries or descriptions the document
lacks.** That argument is already won — cloud's emission carries a summary on
2333 of 2333 operations and a description on 2283, out of the handlers' own doc
comments. What it lacks is TYPES on routes that are not typed ops.

| product | ops | requestBody | 2xx schema | query params |
|---|---:|---:|---:|---:|
| ai | 184 | 85 | 183 | 1 |
| iam | 30 | 24 | 0 | 6 |
| functions | 10 | 2 | 10 | 2 |
| agents | 7 | 6 | 7 | 1 |
| security | 7 | 1 | 7 | 2 |
| admin | 6 | 2 | 6 | 2 |
| integrations | 6 | 2 | 1 | 4 |
| kms | 4 | 2 | 4 | 1 |
| evals | 4 | 3 | 3 | 1 |
| notify | 3 | 3 | 3 | 3 |
| affiliates · authz · git | 3 each | 3 | 9 | 1 |
| 26 more products | 39 | 25 | 38 | 8 |
| **TOTAL** | **302** | **152** | **261** | **31** |

Those shapes were hand approximations and they are gone. A route regains its
shape by becoming a `zip.Get[In, Out]`: the weave then carries body, parameters
and response from the code itself, and `publish.py` picks it up with no change
here. Writing them back would mean inventing shapes, which is what rule 5's
`default` exists to refuse.

**The query parameters are the sharp end**, because a missing filter is a
capability no client can reach at all:

| route | parameters the binary does not declare |
|---|---|
| `GET /v1/iam/oauth/authorize` | `client_id`, `redirect_uri`, `response_type`, `scope`, `state`, `code_challenge`, `code_challenge_method`, `provider` — **the whole OAuth handshake** |
| `GET /v1/integrations/{provider}/callback` · `/v1/integrations/slack/link{,/callback,/slack}` | `code`, `state`, `error` |
| `GET /v1/billing/usage` | `start`, `end` |
| `GET /v1/security/findings` · `/v1/security/scans` | `scanId`, `minSeverity`, `limit` |
| `GET /v1/platform/fleet` | `env`, `health`, `drift` |
| `GET /v1/kms/secrets` | `path`, `env` |
| `GET /v1/ml/models` | `stage`, `search` — a TYPED op whose `In` struct is simply incomplete |
| `GET /v1/websearch/search` | `q`, `format` — a search endpoint that declares no query |
| `GET /v1/evals/scores` · `/v1/admin/{affiliates,referrals}` · `/v1/functions/{metrics,{name}/invocations}` | `limit`, `runName`, `range` |
| `POST /v1/notify/send{,/email,/sms}` | `sync` |

### 4. Tag prose attributed to the wrong package

A tag's description comes from whichever package declared it first, so `org`,
`docs`, `health`, `memory`, `rag`, `chat` and a dozen more read "Package ai is
Hanzo AI —", and `files`, `download`, `upload` read "Package exec is the code
interpreter". Cosmetic, and visible on every doc page and in `CAPABILITIES.md`.

### 5. Three o11y schemas the Go client cannot be generated from — BLOCKING

Every generator Pascal-cases a property name and emits `Get<F>`, `Get<F>Ok`,
`Has<F>` and `Set<F>` beside it. Three schemas break under that:

| schema | property names | what Go does |
|---|---|---|
| `o11y.GettableAgentCheckIn` | `integration_config` **and** `integrationConfig`; `removed_at` **and** `removedAt` | `IntegrationConfig redeclared`, `RemovedAt redeclared` — two spellings of one field, side by side, commented "Older fields for backward compatibility with existing AWS agents" |
| `o11y.O11yPodOnboarding` | `hasClusterName`, `hasNamespaceName`, `hasNodeName` beside `clusterName`… | `field and method with the same name HasClusterName` |
| `o11y.PostableProfile` | `has_existing_observability_tool` beside `existing_observability_tool` | same |

MEASURED: `go build ./...` on the client generated from `hanzo.yaml` fails on
these three **and on nothing else** — renaming those keys in a scratch copy of the
document and regenerating gives **exit 0**. This repo must NOT rename them: a
field name is the wire, and a rename here would be exactly the invention the
whole change removes. `test_publish.py` pins the three as a CEILING, so a fourth
cannot arrive unnoticed while these stay open.

The old master did not have this because its copy of cloud's document was
STALE — 1967 operations against cloud's 2333, missing the whole o11y typing lane
that introduced these schemas. The bug arrives with publishing the current
release, not with the projection.

### 6. The five emitter rules

Rules 1–5 above plus the security scheme. Landing them deletes `publish.py`.

## The inference surface is NOT answered at an edge

An earlier version of this file, and of `hanzoai/cli`'s, asserted the bare-`/v1`
inference routes are "answered at the edge, not by cloud". That was a
rationalization and it is false. Measured with nonsense-sibling controls:

```
GET  /v1/models            200   |  GET  /v1/models-zzq9            404
POST /v1/chat/completions  401   |  POST /v1/chat/completions-zzq9  404
GET  /v1/tools             403   |  GET  /v1/tools-zzq9             404
POST /v1/event             401   |  POST /v1/event-zzq9             404
```

All four are in the document, served by the same host that answers everything
else, on the one chain: ingress → gateway → ZAP → cloud → ZAP/UDS → plugin.
`/v1/chat/completions` and its siblings are top-level because every OpenAI and
Anthropic SDK hard-codes those paths — there the PATH is the compatibility
contract — not because a different server answers them. If you find prose
anywhere claiming an edge exception, it is a bug in the prose.

## SDK generation — the ONE way (Stainless RETIRED, 2026-07)

The interface is `hanzo.yaml`; the backend is **openapi-generator 7.14.0** for
every language. Each language repo owns its call site (`scripts/generate.sh`),
every per-language knob is data in `sdks.yaml`, and the invocation is logic that
lives once, in `generate.py`.

| Lang | Canonical repo | Generator | Ships as | Driven by |
|------|------|-----------|---------|---------|
| Python | `hanzoai/python-sdk` | `python` (urllib3, pydantic v2) | `hanzoai` on PyPI (`pkg/hanzo-inc/cloud`) | `generate.py` |
| TypeScript | `hanzoai/js-sdk` | `typescript-axios` | `hanzoai` on npm (`src/`) | `generate.py` |
| Java | `hanzoai/java-sdk` | `java` (okhttp-gson) | `ai.hanzo:hanzo-java-cloud` | `generate.py` |
| Kotlin | `hanzoai/kotlin-sdk` | `kotlin` (okhttp4+gson) | `ai.hanzo:hanzo-kotlin-cloud` | `generate.py` |
| Rust | **`hanzo-rs/sdk`** | `rust` (reqwest) | `crates/hanzo-client` | `generate.py` (+ `templates/rust/`) |
| Go | **`hanzo-go/sdk`** | `go` | `package hanzoai` at the MODULE ROOT, imported as `github.com/hanzoai/go-sdk` | `generate.py` |

Three repos were RENAMED and answer through a redirect (`hanzoai/go-sdk` →
`hanzo-go/sdk`, `hanzoai/rust-sdk` → `hanzo-rs/sdk`, `hanzoai/cpp-sdk` →
`hanzo-cpp/sdk`), so a stale name still resolves and hides the move;
`gh api repos/<old> --jq .full_name` prints the new one. Go's module path stays
`github.com/hanzoai/go-sdk` — that is what the proxy has.

**When a language leaves `sdks.yaml`**: a row exists while the WHOLE invocation is
expressible as data. What is NOT allowed is a row here AND flags there. **Both
departures have now come back** — go when `owned()` replaced directory ownership
with a set of files, rust when `templates:` landed — so every language this repo
generates is a row, and only `cpp` is still out (it needs generator 7.24.0, and
the pin is one version for everyone).

**`rust` was the first to leave and the last to return.** It needs a
`reqwest/api.mustache` override for the 16 operations whose binary body is
OPTIONAL, and the argument was that a template is a FILE that must sit beside its
flags — right about the risk, wrong about the address. `templates:` names a
directory under THIS repo (`templates/rust/`), so the override and its flags land
in one commit. The departure is what drifted: its script defaulted to
`hanzoai/openapi` `hanzo.yaml@main` while the `.spec-lock` beside it named
`hanzo-inc/cloud` `openapi.yaml` at a commit. Regenerating at the ref that lock
named, through the driver, reports `[rust] clean` — byte-identical to what the
155-line script produced.

**`hanzoai/ruby-sdk` was a row naming a client nobody shipped** — a hard 404 with
no redirect, while every genuinely renamed SDK answers 301, and no gem under
`hanzoai_cloud` or any other candidate. A visible gap is honest; a row that
generates into nothing is not.

### Which document each client is a projection of

`generate.py` resolves it per repo: `--spec` (the document by value, what
hanzoai/ci's `client:` lane passes), else that repo's `.spec-lock`, else this
checkout's `hanzo.yaml`. The fallback was removed once, correctly, while
`hanzo.yaml` was the hand-merged master; it is back because the file is a
projection now, and because the alternative was measured to produce zero files
in every language.

**Open, for the fleet**: each SDK repo's `hanzo.yml` declares
`client.spec.repo`, defaulting to `hanzo-inc/cloud`. Those should name
`hanzoai/openapi` / `hanzo.yaml` — the generatable projection — until rules 1–5
land upstream, at which point they should name `hanzo-inc/cloud` again and mean it.
Not changed here: those are other repos.

Every SDK also renders `flows.yaml` into its `examples/` — the same six journeys,
from the same operationIds, in every language. An SDK does not choose its own
examples any more than it chooses its own methods. Two of the six moved in this
change, both because a hand-authored operationId vanished with its hand-authored
spec: `hello` was `bot_authMe` (`/v1/bot/auth/me`, now behind a relay door) and
is `get_v1_keys`; `tools` was `mcp_rpc` (`POST /v1/mcp`, undeclared) and is
`get_v1_tools`. Both replacements were probed with controls — see `flows.yaml`.

### operationIds changed, deliberately, once

The `<svc>_` prefix `merge.py` applied is gone. It existed to keep 52 authored
specs from colliding, and with one document there is exactly **one** collision in
2284 operations. `cloud_get_v1_billing_balance` is now `get_v1_billing_balance`;
`gateway_createChatCompletion` is `post_v1_chat_completions`. A prefix invented
here was a second naming authority, and the bare id is the one the MCP door
already uses — a tool name is its operationId. Pin against the document, not
against a remembered method name.

## Conventions

- Every route is `/v1/<product>/<resource>`; a path segment names a THING and the
  METHOD says the verb. Where a binary answers at an address it inherited it tags
  that operation `compat`, and rule 2 keeps it out of the publication.
- IAM also answers OIDC discovery at the three unprefixed addresses the standards
  fix — `/.well-known/{openid-configuration,jwks,oauth-authorization-server}` —
  each the same handler as its `/v1/iam/` twin.
- No `/api/` prefix, no `deprecated: true`, no cross-brand references. Forward
  only.
- White-label is by DOMAIN: `skills.py` rewrites `api.hanzo.ai` / `hanzo.id` /
  `Hanzo` per brand, longest-host-first, and a Lux surface never says Hanzo.

## Licensing

`MIT OR Apache-2.0`, at your option — per HIP-0137 (`hanzoai/hips`, `HIPs/hip-0137-one-license.md`). Relicensed from BSD-3-Clause,
which HIP-0137 puts out of scope for `hanzoai`. The history reaches back to 2016
and is Hanzo's own; no third-party source survives in HEAD. Generated clients
are projections of this repo's spec and carry the same terms; `dist/` is built,
never committed.
