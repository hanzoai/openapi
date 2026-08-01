#!/usr/bin/env python3
"""Placement — every authored operation under the app that owns its route.

Runnable standalone (`python3 test_placement.py`, non-zero exit on failure) AND
under pytest, like test_flows.py beside it.

capabilities.yaml states the law this file enforces: "the route IS the identity:
one capability = one name = one /v1/<name> = one <name>/openapi.yaml." Nothing
enforced it, so 103 authored paths had drifted out of their owner's prefix and
four products (`kv`, `s3`, `search`, `vector`) were each described by TWO specs
at once — the namesake and a `provisioning` bucket that squatted on seven other
products' roots. A reader asking "who owns /v1/vector" got two answers, and the
CLI, the SDKs and the agent-skills catalog each picked one.

Two assertions:

  1. ONE OWNER PER PRODUCT. No two authored specs may claim paths under the same
     `/v1/<product>` prefix. This is absolute — there is no exception list,
     because a second claimant is never a fact about a server, it is always two
     descriptions of one thing.

  2. THE ROUTE IS THE IDENTITY. `<svc>/openapi.yaml` claims `/v1/<svc>` paths.
     Every exception is declared BELOW with the reason it is true, so a new one
     fails here instead of arriving silently.

`cloud/openapi.yaml` is exempt from both: it is not authored here. It is
hanzoai/cloud's own woven document, regenerated from that binary's router and
drift-gated there, and merge.py merges it LAST so it wins every route an
authored spec also claims. It describes whatever cloud serves, wherever cloud
serves it, and this repo does not get a vote.
"""
import glob
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))
TRUTH = "cloud"

# The declared exceptions to rule 2, each measured against api.hanzo.ai.
#
# Every path here is SERVED at the address given — none is a placeholder. What
# they have in common is a BINARY that answers at a top-level noun which is not
# its service's name, so moving the operation into a same-named spec would
# either invent a route nobody serves or split one service across many specs.
# The fix for each is a route move in the serving repo; until then this table is
# the honest statement of where the surface actually lives.
OFF_PREFIX = {
    # IAM additionally answers OIDC/OAuth DISCOVERY at the three unprefixed
    # addresses the standards fix — a bare-origin client and the gateway's
    # default look there and nowhere else (RFC 8414 §3, OIDC Discovery §4). Each
    # is the same handler as its /v1/iam twin over the same keys: one document,
    # two spellings of where to find it. Measured off the binary's route table.
    # Documented in LLM.md.
    #
    # The eight OTHER unprefixed paths this list used to carry — /oauth/token,
    # /oauth/userinfo, /oauth/introspect, /oauth/callback, /oauth/token/refresh,
    # /.well-known/webfinger and the two /.well-known/{application}/… — were the
    # dead entity store's addresses. iam serves the protocol endpoints under
    # /v1/iam/oauth/ and its own discovery document says so. Probing the old ones
    # on iam.hanzo.ai returns 200 text/html: the portal's catch-all, byte-identical
    # to what a nonsense path returns. A 200 is not liveness.
    "iam": ["/.well-known/jwks", "/.well-known/openid-configuration",
            "/.well-known/oauth-authorization-server"],
    # The inference edge answers at the top of /v1 because a model call names a
    # model and nothing else — there is no product noun between the caller and
    # the model. The gateway is the binary that serves them.
    "gateway": ["/healthz", "/v1/audio/speech", "/v1/chat/completions",
                "/v1/completions", "/v1/embeddings", "/v1/images/generations",
                "/v1/messages", "/v1/models", "/v1/models/{model}", "/v1/rerank"],
    # Liveness/scrape endpoints, outside /v1 by convention.
    "search": ["/metrics"],
    # The compute plane answers at the resource nouns, not under /v1/visor.
    "visor": ["/v1/bots", "/v1/clusters", "/v1/clusters/{clusterId}/pools",
              "/v1/clusters/{clusterId}/pools/{poolId}",
              "/v1/clusters/{clusterId}/pools/{poolId}/scale",
              "/v1/compute/regions", "/v1/compute/sizes", "/v1/gpus",
              "/v1/gpus/alerts", "/v1/machines", "/v1/machines/{id}"],
    # The zero-trust fabric answers at the fabric nouns, not under /v1/zt.
    "zt": ["/v1/mesh/services", "/v1/networks", "/v1/networks/{id}"],
    # Base serves its record CRUD at /v1/collections/*; /v1/base is its health.
    "base": ["/v1/collections/{collection}/records",
             "/v1/collections/{collection}/records/{id}"],
    # The DigitalOcean provider serves VPCs at the resource noun.
    "do": ["/v1/vpcs", "/v1/vpcs/{id}"],
    # A session's file transfer is addressed by the verb, not by /v1/exec.
    "exec": ["/v1/download/{id}", "/v1/files/{session_id}", "/v1/upload"],
    # The graph service serves these two registries at their own nouns.
    "graph": ["/v1/indexers", "/v1/oracles"],
    # Sites are served at /v1/sites; /v1/projects is the same service's other
    # noun. (cloud also serves /v1/platform/sites — that collision is cloud's to
    # settle, and cloud's document is the one that wins it.)
    "projects": ["/v1/sites", "/v1/sites/deploy"],
    # Routing data export/erase, served by the ai binary at /v1/router.
    "ai": ["/v1/router/data"],
}


def specs():
    out = {}
    for f in sorted(glob.glob(os.path.join(ROOT, "*", "openapi.yaml"))):
        svc = os.path.basename(os.path.dirname(f))
        if svc == TRUTH:
            continue
        out[svc] = list((yaml.safe_load(open(f)) or {}).get("paths") or {})
    return out


def tags():
    """Per authored spec: (declared tag names, tag names its operations use)."""
    out = {}
    for f in sorted(glob.glob(os.path.join(ROOT, "*", "openapi.yaml"))):
        svc = os.path.basename(os.path.dirname(f))
        if svc == TRUTH:
            continue
        doc = yaml.safe_load(open(f)) or {}
        declared = [t.get("name") for t in (doc.get("tags") or [])]
        used = set()
        for item in (doc.get("paths") or {}).values():
            for method, op in (item or {}).items():
                if method in ("get", "post", "put", "patch", "delete"):
                    used.update(op.get("tags") or [])
        out[svc] = (declared, used)
    return out


def product(path):
    seg = path.split("/")
    return seg[2] if len(seg) > 2 and seg[1] == "v1" else None


def test_one_owner_per_product():
    owners = {}
    for svc, paths in specs().items():
        for p in paths:
            prod = product(p)
            if prod:
                owners.setdefault(prod, set()).add(svc)
    clashes = {k: sorted(v) for k, v in owners.items() if len(v) > 1}
    assert not clashes, (
        "two authored specs describe one product — one of them must die:\n" +
        "\n".join(f"  /v1/{k} <- {v}" for k, v in sorted(clashes.items())))


def test_the_route_is_the_identity():
    stray = {}
    for svc, paths in specs().items():
        allowed = set(OFF_PREFIX.get(svc, []))
        bad = [p for p in paths
               if not (p == f"/v1/{svc}" or p.startswith(f"/v1/{svc}/"))
               and p not in allowed]
        if bad:
            stray[svc] = sorted(bad)
    assert not stray, (
        "an authored spec claims a route outside its own product. Move the "
        "operation into the spec that owns the prefix, or — if a binary really "
        "does answer it there — add it to OFF_PREFIX in this file with the "
        "reason:\n" +
        "\n".join(f"  {k}/openapi.yaml claims {v}" for k, v in sorted(stray.items())))


def test_no_orphan_tag_declarations():
    """A tag is a BUCKET, and a bucket with nothing in it is a claim on a name
    that no operation redeems.

    The tag namespace is GLOBAL in the merged `hanzo.yaml`: every spec's tags land
    in one list, and an SDK, the MCP tool list and the docs all group by it. So a
    declaration left behind after its operations go on claiming a name another
    product may need — and worse, describing it. `search` declared `Logs:
    "Configure logging"` after `/v1/search/logs/stream` was refuted; the merge
    folds names case-insensitively, so that sentence became the description of
    cloud's `/v1/logs` observability product, which is not what it describes.

    Same rule as OFF_PREFIX above: an exception that names nothing is a comment
    pretending to be a rule, and it must go when the thing it named does.
    """
    stale = {s: [t for t in decl if t not in used] for s, (decl, used) in tags().items()}
    stale = {s: t for s, t in stale.items() if t}
    assert not stale, (
        "a spec declares tags no operation in it uses — delete the declarations:\n" +
        "\n".join(f"  {k}/openapi.yaml: {v}" for k, v in sorted(stale.items())))


def test_no_stale_exceptions():
    """An exception that no longer names a real path is a comment pretending to
    be a rule — it must go when the path does."""
    have = specs()
    stale = {}
    for svc, paths in OFF_PREFIX.items():
        if svc not in have:
            stale[svc] = ["(no such spec)"]
            continue
        gone = [p for p in paths if p not in have[svc]]
        if gone:
            stale[svc] = gone
    assert not stale, (
        "OFF_PREFIX declares paths that no longer exist — delete the entries:\n" +
        "\n".join(f"  {k}: {v}" for k, v in sorted(stale.items())))


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"ok   {name}")
            except AssertionError as e:
                fails += 1
                print(f"FAIL {name}\n{e}")
    sys.exit(1 if fails else 0)
