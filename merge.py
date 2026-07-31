#!/usr/bin/env python3
"""Regenerate the unified `hanzo.yaml` AND `CAPABILITIES.md` from the ONE
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
  • no two AUTHORED specs may claim one route — only TRUTH may take a route
    from someone (see TRUTH), and it does so explicitly;
  • `internal` services are EXCLUDED from the unified + x-tagGroups (their dirs,
    if any, are skipped);
  • `pending` / `review` / domain names WITHOUT a dir are fine (not-yet-authored
    or future-fold candidates) — only a dir on disk is load-bearing.
"""
import os
import sys
import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))
CAPABILITIES = os.path.join(ROOT, "capabilities.yaml")

# The one spec here that is NOT authored here: `cloud/openapi.yaml` is
# hanzoai/cloud's own woven document, copied verbatim by `sync.py` from that
# repo's origin/main. A binary's document cannot describe a route the binary
# does not serve — cloud's is regenerated from its router and drift-gated there
# — so where it and a hand-written spec both claim a path, IT WINS. It is
# merged LAST to make that happen, explicitly, instead of by where its name
# falls in the alphabet, which is how the same paths used to resolve.
TRUTH = "cloud"

# What a route with no declared response shape says for itself.
UNTYPED = ("The route answers; its response shape is not declared at the source "
           "(not a typed op).")


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

    # Internal dirs are excluded from the unified; they must NOT be grouped.
    internal_grouped = sorted(internal & grouped)
    if internal_grouped:
        sys.exit(f"merge: `internal` name(s) also listed in a domain/core "
                 f"(internal is excluded from the unified): {internal_grouped}")

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

    responses get a `default` when the source declares none. An operation with no
    responses is legal OpenAPI 3.1 and useless to every generator: 7.14.0 counts
    each one an ERROR and, told to generate anyway, emits a method whose return
    type is the raw HTTP response. The woven document says so for every route
    that is not a typed op — it publishes the address and invents nothing, which
    is the honest reading — so the fix is not to invent a schema here either. A
    `default` response with no content says exactly what is known: the route
    answers, and its shape is not declared at the source. The document validates,
    the generator stops erroring, and the client is no less typed than the route.
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
        # An untagged operation is not ungrouped, it is grouped somewhere nobody
        # named: every generator files it under `DefaultApi` and every doc site
        # leaves it out of the movements. The service that serves it is the one
        # true answer, so it is the tag. (68 of these, all the non-/v1 routes the
        # cloud weave tags for no product: `/`, `/.well-known/*`, the git wire.)
        if not op.get("tags"):
            op["tags"] = [svc]
        elif len(op["tags"]) > 1:
            op["tags"] = op["tags"][:1]
        if not op.get("responses"):
            op["responses"] = {"default": {"description": UNTYPED}}
    return item


def key(tag):
    """A tag's identity, ignoring case, space and punctuation. `AI` and `ai`,
    `API Keys` and `api-keys` name one concept and become one module in every
    client, so they are one key here too."""
    return "".join(c for c in tag.lower() if c.isalnum())


def build_unified(present, categories, internal):
    """Aggregate every present per-service spec into the unified hanzo.yaml dict.

    Internal services are excluded (their dirs, if any, are skipped); TRUTH is
    merged LAST so its routes win over any hand-written spec that claims them."""
    included = [s for s in present if s not in internal]
    included = [s for s in included if s != TRUTH] + [s for s in included if s == TRUTH]

    paths, schemas, responses, params, reqbodies, secschemes = {}, {}, {}, {}, {}, {}
    claim, owner, described, titles = {}, {}, {}, {}
    overrides = 0
    for svc in included:
        spec = yaml.safe_load(open(os.path.join(ROOT, svc, "openapi.yaml")))
        comps = spec.get("components", {}) or {}
        titles[key(svc)] = (spec.get("info") or {}).get("title") or svc
        for p, item in (spec.get("paths", {}) or {}).items():
            if p in claim:
                # Two hand-written specs claiming one route is ambiguity with no
                # right answer — the resolution used to be alphabetical. Only
                # TRUTH may take a route from someone, because only TRUTH is
                # evidence of what is served.
                if svc != TRUTH:
                    sys.exit(f"merge: {claim[p]}/openapi.yaml and {svc}/openapi.yaml "
                             f"both claim {p} — one route has one owner")
                overrides += 1
            claim[p] = svc
            item = namespace_ops(prefix(item, svc), svc, p)
            paths[p] = item
            for op in (item or {}).values():
                for t in (op.get("tags") or []) if isinstance(op, dict) else []:
                    owner.setdefault(key(t), svc)
        # A tag's prose belongs to whoever declared it. TRUTH is merged last, so
        # for a tag it also declares, the owning Go package's synopsis wins.
        for t in spec.get("tags") or []:
            if isinstance(t, dict) and t.get("name") and (t.get("description") or "").strip():
                described[key(t["name"])] = t["description"].strip()
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

    # Case-canonicalize operation tags — the LAST codegen-identity normalization,
    # and the one this file claimed but never did. openapi-generator emits one
    # class/module PER TAG STRING and sanitizes the name (strip non-alnum, Pascal),
    # so `AI` and `ai`, `API Keys` and `api-keys`, `Users` and `users` map to the
    # SAME module under different keys: the second silently overwrites the first,
    # and 127 of 411 operations in 23 colliding groups vanished from every SDK.
    # One spelling per concept, chosen deterministically — most uppercase wins
    # (the designed `AI`/`MCP`/`Users` over the lazy lowercase), ties by the
    # lexicographically smallest (the human-readable `Object Store` over
    # `ObjectStore`). Applied to the merged surface so no per-service spec's
    # casing can ever reach a generator uncanonicalized.
    canon = {}
    for item in paths.values():
        for op in (item or {}).values():
            for t in (op.get("tags") or []) if isinstance(op, dict) else []:
                best = canon.get(key(t))
                rank = (sum(c.isupper() for c in t), tuple(-ord(c) for c in t))
                if best is None or rank > best[1]:
                    canon[key(t)] = (t, rank)
    used = []
    for item in paths.values():
        for op in (item or {}).values():
            if isinstance(op, dict) and op.get("tags"):
                op["tags"] = [canon[key(t)][0] for t in op["tags"]]
                for t in op["tags"]:
                    if t not in used:
                        used.append(t)

    # operationId uniqueness under the identity a GENERATOR uses, not the one the
    # spec states. OpenAPI requires operationIds to be unique as STRINGS, and
    # they are: `cloud_get_v1_pricing-policy` (GET /v1/pricing-policy) and
    # `cloud_get_v1_pricing_policy` (GET /v1/pricing/policy) differ by one
    # character. Every generator then strips the punctuation and camel-cases what
    # is left, so both arrive as CloudGetV1PricingPolicy: the Go client declares
    # `ApiCloudGetV1PricingPolicyRequest` twice and does not compile — the same
    # class of failure as the tag casing above, one level down. Both routes are
    # real, so neither may be dropped; the later one by path order takes a
    # suffix, which is what the generator does for the duplicates it can see.
    taken, renamed = set(), 0
    for p in sorted(paths):
        for m in HTTP_METHODS:
            op = (paths[p] or {}).get(m)
            if not isinstance(op, dict):
                continue
            oid, n = op["operationId"], 2
            while key(oid) in taken:
                oid, n = f"{op['operationId']}_{n}", n + 1
            renamed += oid != op["operationId"]
            taken.add(key(oid))
            op["operationId"] = oid

    # x-tagGroups and `tags` describe the tags OPERATIONS CARRY. Both used to
    # describe the spec DIRECTORIES instead — 55 names, 4 of which any operation
    # carried — so a doc site grouped 4 of 239 tags, left the other 235
    # ungrouped, and every description it did have belonged to a heading nothing
    # was filed under. A tag's group is the domain of the service that
    # introduced it, so the registry still decides the movements; a tag's prose
    # is whatever the declaring spec said about it.
    svc_group = {s: g for g, members in categories for s in members}
    tag_groups = []
    for name, _ in categories:
        member_tags = [t for t in used if svc_group.get(owner[key(t)]) == name]
        if member_tags:
            tag_groups.append({"name": name, "tags": member_tags})
    tags = []
    for t in (t for g in tag_groups for t in g["tags"]):
        # The declaring spec's words if it wrote any; otherwise the title of the
        # service that serves the tag — which is all a service-name tag means.
        prose = described.get(key(t)) or titles.get(key(t))
        tags.append({"name": t, "description": prose} if prose else {"name": t})

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

    unified = {
        "openapi": "3.1.0",
        "info": {
            "title": "Hanzo Cloud — Unified API (V8 · Open Edition)",
            "description": (
                "The single unified OpenAPI surface for ALL Hanzo services, "
                "aggregated from the per-service specs. Every route is "
                "https://api.hanzo.ai/v1/<service>/*. Grouped by the canonical "
                "domains in capabilities.yaml (the ONE registry). "
                "cloud/openapi.yaml is hanzoai/cloud's own woven document, "
                "copied verbatim by sync.py, and it wins wherever it and a "
                "hand-written spec describe the same route. Regenerated by "
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
    ops = [op for item in paths.values() for m, op in (item or {}).items()
           if m in HTTP_METHODS and isinstance(op, dict)]
    return unified, {
        "services": len(included),
        "paths": len(paths),
        "schemas": len(schemas),
        "responses": len(responses),
        "params": len(params),
        "groups": len(tag_groups),
        "tags": len(tags),
        "described_tags": sum(1 for t in tags if t.get("description")),
        "ops": len(ops),
        "described_ops": sum(1 for op in ops if (op.get("description") or "").strip()),
        "overrides": overrides,
        "renamed": renamed,
    }


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
        "`hanzo.yaml`'s `x-tagGroups`, so this index and the unified never drift."
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
                     "Excluded from the unified, `x-tagGroups`, SDKs and docs.")
        lines.append("")
        lines.append(", ".join(f"`{s}`" for s in internal))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main():
    categories, internal, collapsed, cap = load_registry()
    present = spec_dirs()
    check_invariant(present, categories, internal, collapsed)

    unified, n = build_unified(present, categories, internal)
    yaml.dump(unified, open(os.path.join(ROOT, "hanzo.yaml"), "w"),
              default_flow_style=False, sort_keys=False, width=120)

    md = render_capabilities_md(present, categories, cap)
    open(os.path.join(ROOT, "CAPABILITIES.md"), "w").write(md)

    print(f"merged {n['services']} services → {n['paths']} paths, {n['schemas']} schemas, "
          f"{n['responses']} responses, {n['params']} params, {n['groups']} categories")
    print(f"{n['ops']} operations, {n['described_ops']} described; "
          f"{n['tags']} tags, {n['described_tags']} described; "
          f"{n['overrides']} paths taken by {TRUTH} (source-true), "
          f"{n['renamed']} operationIds suffixed to stay distinct in codegen")
    print(f"generated CAPABILITIES.md ({n['groups']} categories) from capabilities.yaml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
