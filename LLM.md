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
- `hanzo.yaml` — unified master, aggregated from the per-service specs and
  grouped (`x-tagGroups`) by `merge.py` straight from `capabilities.yaml`.
- `<service>/openapi.yaml` — one self-contained spec per service.
- `shared/` — shared schemas usable by individual specs in their `components`.
- `generated/<name>.json` — specs a SERVICE EMITTED from its own routes. Not
  hand-written, not merged into the master; the measured counterpart of the
  contract of the same name (see below).
- `audit.py` — measures a generated spec against that contract.
- `README.md` — service index and usage.
- `CHANGELOG.md` — release notes.

`merge.py` enforces one-and-one-way as a build invariant: every present
`<service>/openapi.yaml` dir MUST map to exactly one entry across
`domains ∪ core` in `capabilities.yaml` (orphan / unlisted / double-listed →
build fails); a `collapsed` name must have NO spec dir; `internal` services are
excluded from the master and `x-tagGroups`.

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
| `hanzo.json` | `hanzoai/cloud` — the whole `/v1` binary | `make openapi OPENAPI_DIR=<this repo>` in `~/work/hanzo/cloud` |
| `iam.json` | `hanzoai/iam` — zip typed ops | zip's `App.OpenAPISpec()` |

`hanzo.json` is named for `hanzo.yaml`, not for `cloud/`: the binary serves the
whole fused surface, so it is the generated counterpart of the MASTER. It is
one document folded from two readings of one router — the live route table
(every operation, its address, its product tag) over zip's typed-op registry
(`zip.Get[In, Out]` → JSON Schema, parameters, responses, plus the prose
`cmd/zipdoc` lifts out of the handlers' doc comments at build time). A route
that is not a typed op appears with its address and nothing invented.

Its `info` block comes from the emitting binary, so it carries the API contract
version (`v1`) rather than this repo's V8 release generation — it is a machine
artifact, not one of the authored specs the `8.0.0` convention governs.

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
(never `generated/hanzo.json`, never the wire) and emits a `SKILL.md` for every
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

| Lang | Repo | Generator | Package | Publish |
|------|------|-----------|---------|---------|
| Python | `hanzoai/python-sdk` (`pkg/hanzoai`) | `python` (urllib3, pydantic v2) | `hanzoai` on PyPI | tag `v*` → twine |
| Go | `hanzoai/go-sdk` | `go` (package `hanzoai`) | `github.com/hanzoai/go-sdk` | tag `v*` → pkg.go.dev |
| TypeScript | `hanzoai/js-sdk` | `typescript-axios` | `hanzoai` on npm | tag `v*` → npm publish |
| C++ | `hanzoai/cpp-sdk` | `cpp-restsdk` | — | artifact (this repo's matrix) |
| Dart | `hanzoai/dart-sdk` | `dart-dio` | — | artifact (this repo's matrix) |
| Rust | `hanzoai/rust-sdk` | hand-written | `hanzo` crate | reconcile (openapi-generator emits no Rust) |

Generator version pinned to **7.14.0** everywhere. The merged surface is
verified codegen-clean AND compile-clean for go / python / typescript-axios
(spec fixes that made it so: pubsub `ack_wait` int64; platform DeployJob /
CancelDeploymentJob oneOf → named subschemas; merge.py namespaces operation
tags + discriminator mappings per-service and collapses to one primary tag).

There is NO unified `hanzoai/sdk` multi-lang monorepo generator — that repo's
`gen/` is the retired SECOND way; `hanzoai/sdk` is CLI-only now.

### Remaining spec-coverage gaps — measured, not remembered

`python3 audit.py hanzo` is the answer to "how far has the contract drifted
from the binary", and it replaces every anecdote that used to live here. It
reads `hanzo.yaml` against `generated/hanzo.json`, so both numbers move on
their own the moment either side changes. Neither `/v1/memory` nor
`/v1/videos` is in the live router at all — the earlier note that they were is
exactly the kind of claim this measurement exists to stop repeating.

Read the two columns as two different bugs. `missing` = the contract declares
operations nothing serves, so every SDK ships methods that 404. `undeclared` =
the routes serve operations the contract never named, so no SDK can reach
them. `prose lost` = an operation both sides have, where only the hand-written
side has the words — the reason a generated spec does not simply overwrite a
contract on the day it first covers it.

The SDK-generation surface is the FUSED `api.hanzo.ai/v1` binary. `merge.py`
unions the per-service specs into it.
