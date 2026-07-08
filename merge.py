#!/usr/bin/env python3
"""Regenerate the unified master `hanzo.yaml` from every per-service spec.

The master is the ONE unified OpenAPI surface for all Hanzo services. It is a
pure aggregation — edit a per-service `<svc>/openapi.yaml`, then run this:

    python3 merge.py

Every service is exposed at `https://api.hanzo.ai/v1/<service>/*`, so paths are
already namespaced and never collide. Component schemas/responses/parameters ARE
namespaced here (`<svc>_<Name>`) with their `$ref`s rewritten to match, so two
services can both define `Error`/`User`/etc. without clobbering each other.

The master is grouped by the eight canonical categories via `x-tagGroups` (the
Redocly navigation extension). The category taxonomy is the SAME one documented
in `CAPABILITIES.md` — that manifest is authoritative; `GROUPS` here mirrors it
for the present per-service specs.
"""
import os
import sys
import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))

# Canonical category -> the per-service spec dirs that belong to it. Mirrors the
# capability categories in CAPABILITIES.md; legacy/duplicate spec dirs (e.g. ml,
# s3, mq, auto) are grouped under the SAME category as their canonical name so the
# master stays navigable while the specs are reconciled. Every present
# `<svc>/openapi.yaml` MUST appear in exactly one group; `check_groups` fails the
# build otherwise so the grouping never drifts.
GROUPS = {
    "Identity": ["iam", "authz", "security", "kms", "zt", "guard", "did"],
    "AI": ["ai", "agents", "ml", "eval", "evals", "prompts", "functions",
           "exec", "framework", "graph", "engine"],
    "Messaging": ["pubsub", "mq", "stream", "tasks", "notify"],
    "Observability": ["o11y", "observe", "analytics", "tracker"],
    "Commerce": ["billing", "pricing", "plan", "referrals", "affiliates",
                 "crm", "product", "commerce"],
    "Platform": ["platform", "paas", "provisioning", "gateway", "visor", "base",
                 "do", "edge", "dns", "registry", "nexus", "operative", "db",
                 "kv", "vector"],
    "Applications": ["console", "projects", "git", "templates", "integrations",
                     "bot", "kb", "search", "websearch", "s3", "authors",
                     "automations", "chat", "auto", "app", "flow", "world"],
    "Core": ["admin", "plugin", "cloud"],
}


def group_of(svc):
    for name, members in GROUPS.items():
        if svc in members:
            return name
    return None


def check_groups(services):
    """Every present service must be grouped exactly once; fail loud on drift."""
    grouped = [s for members in GROUPS.values() for s in members]
    dupes = {s for s in grouped if grouped.count(s) > 1}
    if dupes:
        sys.exit(f"merge: service(s) in >1 group: {sorted(dupes)}")
    ungrouped = [s for s in services if group_of(s) is None]
    if ungrouped:
        sys.exit(f"merge: service(s) not in any GROUPS category "
                 f"(add to GROUPS + CAPABILITIES.md): {ungrouped}")


def prefix(node, svc):
    """Rewrite local component $refs to the namespaced `<svc>_` form."""
    if isinstance(node, dict):
        out = {}
        for k, v in node.items():
            if k == "$ref" and isinstance(v, str) and v.startswith("#/components/"):
                kind = v.split("/")[2]  # schemas | responses | parameters | ...
                if kind in ("schemas", "responses", "parameters"):
                    name = "/".join(v.split("/")[3:])
                    out[k] = f"#/components/{kind}/{svc}_{name}"
                    continue
            out[k] = prefix(v, svc)
        return out
    if isinstance(node, list):
        return [prefix(x, svc) for x in node]
    return node


def main():
    services = sorted(
        d for d in os.listdir(ROOT)
        if os.path.isdir(os.path.join(ROOT, d))
        and os.path.isfile(os.path.join(ROOT, d, "openapi.yaml"))
        and d != "shared"
    )
    check_groups(services)

    paths, schemas, responses, params, secschemes, tags = {}, {}, {}, {}, {}, []
    for svc in services:
        spec = yaml.safe_load(open(os.path.join(ROOT, svc, "openapi.yaml")))
        comps = spec.get("components", {}) or {}
        for p, item in (spec.get("paths", {}) or {}).items():
            paths[p] = prefix(item, svc)
        for n, x in (comps.get("schemas", {}) or {}).items():
            schemas[f"{svc}_{n}"] = prefix(x, svc)
        for n, x in (comps.get("responses", {}) or {}).items():
            responses[f"{svc}_{n}"] = prefix(x, svc)
        for n, x in (comps.get("parameters", {}) or {}).items():
            params[f"{svc}_{n}"] = prefix(x, svc)
        for n, x in (comps.get("securitySchemes", {}) or {}).items():
            secschemes.setdefault(n, x)
        tags.append({"name": svc, "description": spec.get("info", {}).get("title", svc)})

    # x-tagGroups: canonical category → its present service tags, in category order.
    tag_groups = []
    for name in GROUPS:
        members = [s for s in GROUPS[name] if s in services]
        if members:
            tag_groups.append({"name": name, "tags": members})

    components = {
        "securitySchemes": secschemes or {"bearerAuth": {"type": "http", "scheme": "bearer"}},
        "schemas": dict(sorted(schemas.items())),
    }
    if responses:
        components["responses"] = dict(sorted(responses.items()))
    if params:
        components["parameters"] = dict(sorted(params.items()))

    out = {
        "openapi": "3.1.0",
        "info": {
            "title": "Hanzo Cloud — Unified API (V8 · Open Edition)",
            "description": (
                "The single unified OpenAPI surface for ALL Hanzo services, "
                "aggregated from the per-service specs. Every route is "
                "https://api.hanzo.ai/v1/<service>/*. Grouped by the eight "
                "canonical categories (see CAPABILITIES.md). Regenerated by "
                "merge.py — edit the per-service <svc>/openapi.yaml, not this file."
            ),
            "version": "8.0.0",
            "contact": {"name": "Hanzo AI", "url": "https://hanzo.ai", "email": "support@hanzo.ai"},
            "license": {"name": "Proprietary"},
        },
        "servers": [{"url": "https://api.hanzo.ai", "description": "Hanzo Gateway"}],
        "tags": tags,
        "x-tagGroups": tag_groups,
        "security": [{"bearerAuth": []}],
        "paths": dict(sorted(paths.items())),
        "components": components,
    }
    yaml.dump(out, open(os.path.join(ROOT, "hanzo.yaml"), "w"),
              default_flow_style=False, sort_keys=False, width=120)
    print(f"merged {len(services)} services → {len(paths)} paths, "
          f"{len(schemas)} schemas, {len(responses)} responses, {len(params)} params, "
          f"{len(tag_groups)} categories")
    return 0


if __name__ == "__main__":
    sys.exit(main())
