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
