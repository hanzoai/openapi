# openapi

OpenAPI 3.1 specifications for all Hanzo services. v1.0.0 lock-in as of
2026-05-31. No backwards compatibility, no `/api/` prefixes, no cross-brand
references.

## Layout

- `hanzo.yaml` — master discovery spec (3 routes).
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

## SDK generation — the ONE way, and its current drift (READ THIS)

The one interface is `hanzo.yaml`; the generator backend is an orthogonal
per-language concern (one interface, orthogonal backends):

| Lang | Repo | Backend | Why |
|------|------|---------|-----|
| Python/Go/JS | `hanzoai/{python,go,js}-sdk` | Stainless project `hanzo-ai` | best DX, already published |
| Rust | `hanzoai/rust-sdk` | hand-written crates | Stainless emits no Rust |
| C++ | `hanzoai/cpp-sdk` | openapi-generator `cpp-restsdk` on ARC | Stainless emits no C++ |
| Dart (if wanted) | `hanzoai/dart-sdk` | openapi-generator `dart-dio` on ARC | Stainless emits no Dart |

One repo per language, each derives from `hanzo.yaml`. There is NO unified
`hanzoai/sdk` multi-lang monorepo generator — that repo's `gen/` (openapi-
generator over all 10 langs, "replaces Stainless") is the retired SECOND way;
`hanzoai/sdk` is CLI-only now.

### Known drift (2026-07 audit — must be fixed for the SDKs to be truthful)

1. **Stainless points at the LEGACY LLM-gateway spec, not `hanzo.yaml`.** The
   published python/go/js SDKs expose only the LiteLLM inference + gateway-admin
   surface (188 endpoints / 49 resources: chat, models, embeddings, Key, User,
   Team, Spend, Budget, Guardrails, provider passthrough). They cover NONE of
   the cloud product surface. Fix = repoint the Stainless `hanzo-ai` project's
   spec source to `hanzo.yaml` and expand its resource tree to the full surface.
   `python-sdk/.stats.yml` (spec `87bc62c…`) is also diverged from go/js
   (`9b3181f…`) — the repoint resyncs all three.
2. **~28 LIVE `/v1` product prefixes have no usable spec** (so even after the
   repoint they'd be uncovered). The cloud binary (`hanzoai/cloud`
   `subsystems.go`) mounts these flat; they need per-service specs authored from
   the Go routes in `cloud/clients/<x>/*.go`:
   `agents, tracker, crm, framework(+cms/erp/help/kb), kb, prompts, tasks,
   functions, git, templates, security, integrations, notify, automations,
   billing, plans, graph(indexers/oracles), exec, websearch, admin, do
   (vpcs/load-balancers), provisioning(sql/datastore/docdb), memory, vfs,
   licensing, authz, ml(train)`.
3. **Prefix-mismatch specs — re-base onto the live flat prefix:** `visor` →
   `/v1/machines,/v1/gpus,/v1/clusters`; `zt` → `/v1/networks,/v1/mesh,/v1/edge`;
   `flow` → `/v1/automations`; `guard` → `/v1/security`.
4. **Stale specs (legacy monolith, NOT fused into the cloud binary):**
   `cloud/` (157) and `nexus/` (151) are the retired RPC monolith — only the
   `/v1/search-docs` + `/v1/vector` slices survive (via `clients/product`).
   `mq, pubsub, stream, registry, db, did, engine` are not live. Separate
   deployments that legitimately keep their spec: `iam, chat, gateway,
   operative, dns, flow`.

The SDK-generation surface is the FUSED `api.hanzo.ai/v1` binary, not the union
of every deployment. `merge.py` currently unions all per-service specs; the
correct target is the live cloud surface (add the 28, re-base the 4, drop the
stale monolith).
