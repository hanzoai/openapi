#!/usr/bin/env python3
"""Regenerate the unified master `hanzo.yaml` AND `CAPABILITIES.md` from the ONE
source of truth, `capabilities.yaml`, plus every per-service spec.

    python3 merge.py

There is ONE registry: `capabilities.yaml`. This script READS it — there is no
hand-kept category map here. From it we derive TWO artifacts:

  • `hanzo.yaml`  — the unified OpenAPI surface. A pure aggregation of every
    `<svc>/openapi.yaml`; every service is exposed at
    `https://api.hanzo.ai/v1/<svc>/*`, so paths never collide, and component
    schemas/responses/parameters are namespaced `<svc>_<Name>` (with `$ref`s
    rewritten) so two services can both define `Error`/`User` without clobbering.
    Grouped by `x-tagGroups` — one group per `capabilities.yaml` domain (using
    the domain `title`) plus a `Core` group.

  • `CAPABILITIES.md` — a human index. GENERATED; never edit by hand.

Build invariant (fail loud — orthogonality is enforced, not hoped):
  • every present `<svc>/openapi.yaml` dir maps to EXACTLY ONE entry across
    `domains ∪ core` (orphan / unlisted / double-listed → sys.exit);
  • a `collapsed` name MUST have NO spec dir (a reappeared dir → sys.exit);
  • `internal` services are EXCLUDED from the master + x-tagGroups (their dirs,
    if any, are skipped);
  • `pending` / `review` / domain names WITHOUT a dir are fine (not-yet-authored
    or future-fold candidates) — only a dir on disk is load-bearing.
"""
import os
import sys
import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))
CAPABILITIES = os.path.join(ROOT, "capabilities.yaml")


def load_registry():
    """The ONE source of truth. Returns (categories, internal, collapsed, cap).

    `categories` is an ordered list of (group_name, [services]) — one per domain
    (keyed by the domain `title`) then `Core`. This is the ONLY place the
    category taxonomy comes from; nothing here is hand-maintained.
    """
    cap = yaml.safe_load(open(CAPABILITIES))
    categories = [(d["title"], list(d["services"])) for d in cap["domains"]]
    categories.append(("Core", list(cap.get("core") or [])))
    internal = set(cap.get("internal") or [])
    collapsed = set(cap.get("collapsed") or {})
    return categories, internal, collapsed, cap


def spec_dirs():
    """Every present `<svc>/openapi.yaml` dir (the ground truth)."""
    return sorted(
        d for d in os.listdir(ROOT)
        if os.path.isdir(os.path.join(ROOT, d))
        and os.path.isfile(os.path.join(ROOT, d, "openapi.yaml"))
        and d != "shared"
    )


def check_invariant(present, categories, internal, collapsed):
    """Fail loud unless the registry and the spec dirs on disk agree exactly."""
    grouped_list = [s for _, members in categories for s in members]
    grouped = set(grouped_list)

    dupes = sorted({s for s in grouped_list if grouped_list.count(s) > 1})
    if dupes:
        sys.exit(f"merge: name(s) listed in >1 domain/core in capabilities.yaml: {dupes}")

    # A collapsed name is a REMOVED capability — its dir must be gone.
    collapsed_with_dir = sorted(collapsed & set(present))
    if collapsed_with_dir:
        sys.exit(f"merge: `collapsed` name(s) still have a spec dir "
                 f"(group them in a domain or delete the dir): {collapsed_with_dir}")

    # Internal dirs are excluded from the master; they must NOT be grouped.
    internal_grouped = sorted(internal & grouped)
    if internal_grouped:
        sys.exit(f"merge: `internal` name(s) also listed in a domain/core "
                 f"(internal is excluded from the master): {internal_grouped}")

    # Every present (non-internal) spec dir must be grouped exactly once.
    orphans = sorted(s for s in present if s not in grouped and s not in internal)
    if orphans:
        sys.exit(f"merge: spec dir(s) present but not in any domain/core of "
                 f"capabilities.yaml (add them): {orphans}")


def prefix(node, svc):
    """Rewrite local component $refs to the namespaced `<svc>_` form."""
    if isinstance(node, dict):
        out = {}
        for k, v in node.items():
            if k == "$ref" and isinstance(v, str) and v.startswith("#/components/"):
                kind = v.split("/")[2]  # schemas | responses | parameters | ...
                if kind in ("schemas", "responses", "parameters", "requestBodies"):
                    name = "/".join(v.split("/")[3:])
                    out[k] = f"#/components/{kind}/{svc}_{name}"
                    continue
            if k == "mapping" and isinstance(v, dict):
                # discriminator.mapping values are component-ref STRINGS (not $ref
                # keys) — namespace them too, or they dangle post-merge.
                out[k] = {mk: (f"#/components/schemas/{svc}_{mv.split('/', 3)[-1]}"
                               if isinstance(mv, str) and mv.startswith("#/components/schemas/")
                               else mv)
                          for mk, mv in v.items()}
                continue
            out[k] = prefix(v, svc)
        return out
    if isinstance(node, list):
        return [prefix(x, svc) for x in node]
    return node


def schema(node, svc):
    """Namespace a component schema. `title` goes: after namespacing, the KEY is
    the name, and a title still reading `Error` leaves six schemas claiming one
    name. Every generator prefers `title` over the key, so the duplicates collapse
    into each other — silently in most languages, and in the Rust codegen into a
    null model name that aborts the build. Every title in the per-service specs
    only restates that spec's own key, so nothing is lost."""
    node = prefix(node, svc)
    if isinstance(node, dict):
        node.pop("title", None)
    return node


HTTP_METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace")


def namespace_ops(item, svc, path):
    """Normalize every operation on one path item for the merged document.

    Two normalizations, both about codegen identity, both needing the same walk:

    operationId gets a `<svc>_` prefix. OpenAPI requires operationId to be unique
    across the whole document; common names (login, healthCheck, createTeam)
    collide across services and break codegen otherwise. Mirrors the `<svc>_`
    component namespacing. When a spec omits operationId, synthesize a
    deterministic one from method + path.

    tags collapse to the FIRST one. A tag is a grouping hint to a human reader,
    but every generator reads it as the class an operation is emitted INTO, so an
    operation with two tags is emitted TWICE — once per tag, with the same
    identifier both times. In Go that is `ApiPricingGetFullPricingRequest
    redeclared in this block` and the client does not compile; other languages
    take the duplicate more quietly, which is worse. Seven operations were in
    that state (commerce authorize/capture/charge/refund/storeAuthorize/
    storeCharge, pricing getFullPricing) and this file has claimed to collapse
    them since the Stainless retirement without doing it. The FIRST tag is the
    primary by OpenAPI convention — it is what Redoc groups under — so keeping it
    changes no rendering, and the secondary tag was never reachable as a group
    anyway once x-tagGroups is emitted from capabilities.yaml.
    """
    if not isinstance(item, dict):
        return item
    for method, op in item.items():
        if method not in HTTP_METHODS or not isinstance(op, dict):
            continue
        base = op.get("operationId")
        if not base:
            slug = "_".join(seg for seg in "".join(
                c if c.isalnum() else " " for c in path).split())
            base = f"{method}_{slug}"
        op["operationId"] = f"{svc}_{base}"
        if len(op.get("tags") or []) > 1:
            op["tags"] = op["tags"][:1]
    return item


def build_master(present, categories, internal):
    """Aggregate every present per-service spec into the unified hanzo.yaml dict.

    Internal services are excluded (their dirs, if any, are skipped)."""
    included = [s for s in present if s not in internal]

    paths, schemas, responses, params, reqbodies, secschemes, tags = {}, {}, {}, {}, {}, {}, []
    for svc in included:
        spec = yaml.safe_load(open(os.path.join(ROOT, svc, "openapi.yaml")))
        comps = spec.get("components", {}) or {}
        for p, item in (spec.get("paths", {}) or {}).items():
            paths[p] = namespace_ops(prefix(item, svc), svc, p)
        for n, x in (comps.get("schemas", {}) or {}).items():
            schemas[f"{svc}_{n}"] = schema(x, svc)
        for n, x in (comps.get("responses", {}) or {}).items():
            responses[f"{svc}_{n}"] = prefix(x, svc)
        for n, x in (comps.get("parameters", {}) or {}).items():
            params[f"{svc}_{n}"] = prefix(x, svc)
        for n, x in (comps.get("requestBodies", {}) or {}).items():
            reqbodies[f"{svc}_{n}"] = prefix(x, svc)
        for n, x in (comps.get("securitySchemes", {}) or {}).items():
            secschemes.setdefault(n, x)
        tags.append({"name": svc, "description": spec.get("info", {}).get("title", svc)})

    # x-tagGroups: one group per capabilities.yaml category, present tags only,
    # in registry order.
    tag_groups = []
    for name, members in categories:
        member_tags = [s for s in members if s in included]
        if member_tags:
            tag_groups.append({"name": name, "tags": member_tags})

    components = {
        "securitySchemes": secschemes or {"bearerAuth": {"type": "http", "scheme": "bearer"}},
        "schemas": dict(sorted(schemas.items())),
    }
    if responses:
        components["responses"] = dict(sorted(responses.items()))
    if params:
        components["parameters"] = dict(sorted(params.items()))
    if reqbodies:
        components["requestBodies"] = dict(sorted(reqbodies.items()))

    master = {
        "openapi": "3.1.0",
        "info": {
            "title": "Hanzo Cloud — Unified API (V8 · Open Edition)",
            "description": (
                "The single unified OpenAPI surface for ALL Hanzo services, "
                "aggregated from the per-service specs. Every route is "
                "https://api.hanzo.ai/v1/<service>/*. Grouped by the canonical "
                "domains in capabilities.yaml (the ONE registry). Regenerated by "
                "merge.py — edit the per-service <svc>/openapi.yaml + "
                "capabilities.yaml, not this file."
            ),
            "version": "8.0.0",
            "contact": {"name": "Hanzo AI", "url": "https://hanzo.ai", "email": "support@hanzo.ai"},
            "license": {"name": "BSD 3-Clause License", "identifier": "BSD-3-Clause"},
        },
        "servers": [{"url": "https://api.hanzo.ai", "description": "Hanzo Gateway"}],
        "tags": tags,
        "x-tagGroups": tag_groups,
        "security": [{"bearerAuth": []}],
        "paths": dict(sorted(paths.items())),
        "components": components,
    }
    return master, len(included), len(paths), len(schemas), len(responses), len(params), len(tag_groups)


def render_capabilities_md(present, categories, cap):
    """Render CAPABILITIES.md FROM capabilities.yaml — a DERIVED artifact.

    A present spec dir gets a live `/v1/<name>` route; a listed name with no dir
    yet is shown as `pending` (not-yet-authored)."""
    present = set(present)
    lines = []
    lines.append("<!-- GENERATED by merge.py from capabilities.yaml — DO NOT EDIT. "
                 "Edit capabilities.yaml and run `python3 merge.py`. -->")
    lines.append("")
    lines.append(f"# Hanzo Capability Manifest — {cap.get('edition', '')}".rstrip())
    lines.append("")
    lines.append(
        "GENERATED from `capabilities.yaml`, the ONE registry of Hanzo "
        "capabilities. Do NOT edit this file by hand — edit `capabilities.yaml` "
        "and run `python3 merge.py`. `merge.py` reads the same registry to emit "
        "`hanzo.yaml`'s `x-tagGroups`, so this index and the master never drift."
    )
    lines.append("")
    lines.append(
        "One canonical name per capability = one `/v1/<name>` route = one "
        "`<name>/openapi.yaml`. A ✓ marks a name with a present spec dir "
        "(live in `hanzo.yaml`); *pending* marks a listed name whose spec is "
        "not yet authored."
    )
    lines.append("")

    for name, members in categories:
        dom = next((d for d in cap["domains"] if d["title"] == name), None)
        lines.append(f"## {name}")
        lines.append("")
        if dom and dom.get("role"):
            lines.append(f"*{dom['role']}*")
            lines.append("")
        lines.append("| Capability | Route | Spec |")
        lines.append("|---|---|---|")
        for svc in members:
            if svc in present:
                lines.append(f"| `{svc}` | `/v1/{svc}` | ✓ |")
            else:
                lines.append(f"| `{svc}` | `/v1/{svc}` | pending |")
        lines.append("")

    collapsed = cap.get("collapsed") or {}
    if collapsed:
        lines.append("## Collapsed")
        lines.append("")
        lines.append("Resolved duplicates / consolidations — removed, no spec dir. "
                     "The capability now lives where noted.")
        lines.append("")
        lines.append("| Was | Now lives in |")
        lines.append("|---|---|")
        for k, v in collapsed.items():
            lines.append(f"| `{k}` | {v} |")
        lines.append("")

    pending = cap.get("pending") or []
    if pending:
        lines.append("## Pending")
        lines.append("")
        lines.append("Live surfaces missing a spec — author these to complete the set.")
        lines.append("")
        lines.append(", ".join(f"`{p}`" for p in pending))
        lines.append("")

    review = cap.get("review") or {}
    if review:
        lines.append("## Under review")
        lines.append("")
        lines.append("Braids to verify before folding — grouped today (a spec dir "
                     "exists), consolidation is a separate verified decision.")
        lines.append("")
        for k, v in review.items():
            lines.append(f"- **{k}** — {v}")
        lines.append("")

    internal = cap.get("internal") or []
    if internal:
        lines.append("## Internal — NOT public capabilities")
        lines.append("")
        lines.append("Trust boundaries and runtime hosts with no public API surface. "
                     "Excluded from the master, `x-tagGroups`, SDKs and docs.")
        lines.append("")
        lines.append(", ".join(f"`{s}`" for s in internal))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main():
    categories, internal, collapsed, cap = load_registry()
    present = spec_dirs()
    check_invariant(present, categories, internal, collapsed)

    master, n_svc, n_paths, n_schemas, n_resp, n_params, n_groups = build_master(
        present, categories, internal)
    yaml.dump(master, open(os.path.join(ROOT, "hanzo.yaml"), "w"),
              default_flow_style=False, sort_keys=False, width=120)

    md = render_capabilities_md(present, categories, cap)
    open(os.path.join(ROOT, "CAPABILITIES.md"), "w").write(md)

    print(f"merged {n_svc} services → {n_paths} paths, {n_schemas} schemas, "
          f"{n_resp} responses, {n_params} params, {n_groups} categories")
    print(f"generated CAPABILITIES.md ({n_groups} categories) from capabilities.yaml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
