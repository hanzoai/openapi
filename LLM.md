# openapi

OpenAPI 3.1 specifications for all Hanzo services. v1.0.0 lock-in as of
2026-05-31. No backwards compatibility, no `/api/` prefixes, no cross-brand
references.

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
- `README.md` — service index and usage.
- `CHANGELOG.md` — v1 lock-in entry.

`merge.py` enforces one-and-one-way as a build invariant: every present
`<service>/openapi.yaml` dir MUST map to exactly one entry across
`domains ∪ core` in `capabilities.yaml` (orphan / unlisted / double-listed →
build fails); a `collapsed` name must have NO spec dir; `internal` services are
excluded from the master and `x-tagGroups`.

## Conventions

- Routing: every route is `/v1/<service>/<resource>`.
- IAM additionally exposes `/oauth/*` and `/.well-known/*`.
- Security: every operation uses `BearerAuth` (JWT from `https://hanzo.id`).
- `info.version: 1.0.0` on every spec.
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

1. Bump nothing — version stays at `1.0.0`.
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

### Remaining spec-coverage gaps (SDKs cover the spec faithfully; the spec
lacks these live prefixes — author from the Go routes, then the SDKs pick
them up automatically on the next regeneration):

- **`/v1/memory`** and **`/v1/videos`** are LIVE (cloud binary) but have no
  paths in `hanzo.yaml` yet.
- The broader "author the remaining `/v1` product specs from
  `cloud/clients/<x>/*.go`" backlog still applies for any prefix not yet
  present in the per-service specs.

The SDK-generation surface is the FUSED `api.hanzo.ai/v1` binary. `merge.py`
unions the per-service specs into it.
