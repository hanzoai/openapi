# openapi

OpenAPI 3.1 specifications for all Hanzo services. v1.0.0 lock-in as of
2026-05-31. No backwards compatibility, no `/api/` prefixes, no cross-brand
references.

## Layout

- `CAPABILITIES.md` — the CANONICAL capability index: one name per
  capability, grouped into the eight categories, each with its `/v1/<name>`
  prefix. Authoritative — every spec, the cloud binary, and the console
  reconcile to it.
- `hanzo.yaml` — unified master, aggregated + grouped by `merge.py`.
- `<service>/openapi.yaml` — one self-contained spec per service.
- `shared/` — shared schemas usable by individual specs in their `components`.
- `README.md` — service index and usage.
- `CHANGELOG.md` — v1 lock-in entry.

## Conventions

- Routing: every route is `/v1/<service>/<resource>`.
- IAM additionally exposes `/oauth/*` and `/.well-known/*`.
- Security: every operation uses `BearerAuth` (JWT from `https://hanzo.id`).
- `info.version: 1.0.0` on every spec.
- No cross-file `$ref`. Each spec is self-contained.
- No `deprecated: true`. Forward-only.
- No `/api/` prefix anywhere.
- Master grouping: `merge.py` emits `x-tagGroups` (the eight canonical
  categories from `CAPABILITIES.md`); every present spec must belong to
  exactly one group or the merge fails.

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
5. Update `CHANGELOG.md` with a dated entry under the v1.0.0 heading.
6. Run `python3 merge.py` (regenerates `hanzo.yaml`) and commit both.

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
