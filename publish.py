#!/usr/bin/env python3
"""Publish `hanzo.yaml` — a PROJECTION of hanzoai/cloud's emitted document.

    python3 publish.py                 # re-pin to hanzoai/cloud's main, derive, write
    python3 publish.py --ref v1.801.383  # re-pin to one release
    python3 publish.py --check         # THE GATE: re-derive at the pinned ref and diff
    python3 publish.py --current       # has cloud's document moved past the pin?
    python3 publish.py --served        # THE GATE with no checkout: does the deployment answer for every published operation?

THIS REPO DOES NOT DECIDE WHAT THE API IS. It never did well, and it no longer
claims to. hanzoai/cloud emits `openapi.yaml` by projecting its own routers, and
gates the emission by regenerating from source and failing on any diff — so it
cannot describe a route the binary does not serve, and cannot miss one it does.
That is the only description of this API with that property. Everything here is
DOWNSTREAM of it.

What went before: 52 hand-authored `<svc>/openapi.yaml` files were merged with
cloud's document, cloud winning on collision. Measured at cloud@v1.801.383, that
master carried 185 operations the document does not have, and the document
carried 425 the master did not — so the file every SDK generated from described
a router 18% smaller and 8% wrong. 95 of the 185 were addressed at nothing a
probe could find, 36 of those refuted outright (real address 404, nonsense
sibling 404). And an authored operation nothing serves is not a harmless
placeholder: `skills.py` turns it into a SKILL.md, which is a live instruction to
an agent to call a dead endpoint.

WHAT THIS FILE IS ALLOWED TO DO, and it is a short list. A projection may not
add an operation, may not remove one that is served, and may not invent prose.
It may only make the ONE document generatable — see `project()`, where every
rule carries the generator failure that demands it. The measurement that says
the projection is necessary at all: openapi-generator 7.14.0 refuses cloud's
document with **1012 errors**, one per operation the weave publishes with an
address and no `responses`. Every one of those rules is a candidate to move
UPSTREAM into cloud's emitter, and this file shrinks the day one does.

`.spec-lock` is the receipt — repo, path, ref, sha256 — in the same four keys
hanzoai/ci's client lane writes into every SDK repo. It is what lets anyone ask
`hanzo.yaml` "which release are you?" without running anything.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.request

import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))
LOCK = os.path.join(ROOT, ".spec-lock")
TARGET = os.path.join(ROOT, "hanzo.yaml")
INDEX = os.path.join(ROOT, "CAPABILITIES.md")
REGISTRY = os.path.join(ROOT, "capabilities.yaml")
CLOUD = os.environ.get("CLOUD_DIR") or os.path.join(os.path.dirname(ROOT), "cloud")

SPEC_REPO = "hanzoai/cloud"
SPEC_PATH = "openapi.yaml"
# Cloud SERVES its own emission, unauthenticated, from the binary that is
# actually running. It is the only input that can refute a published operation
# without a checkout, a credential or a release tag to take on trust.
SERVED = os.environ.get("SERVED_DOCUMENT", "https://api.hanzo.ai/v1/openapi.json")

HTTP_METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace")

# What a route with no declared response shape says for itself. Not a schema:
# the weave publishes an untyped route's address and invents nothing, and
# inventing one here would be the same lie one repo further downstream.
UNTYPED = ("The route answers; its response shape is not declared at the source "
           "(not a typed op).")


# ---------------------------------------------------------------- the input

def git(repo, *args):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"publish: git {' '.join(args)} failed in {repo}\n{r.stderr.strip()}")
    return r.stdout


def checkout(path):
    if subprocess.run(["git", "-C", path, "rev-parse", "--git-dir"],
                      capture_output=True).returncode:
        sys.exit(f"publish: no {SPEC_REPO} checkout at {path}\n"
                 f"         git clone git@github.com:{SPEC_REPO} {path}\n"
                 f"         (or point --cloud / CLOUD_DIR at one)")
    return path


def lock():
    """`.spec-lock` as a dict, or {} when the repo has never published."""
    if not os.path.exists(LOCK):
        return {}
    out = {}
    for line in open(LOCK):
        k, _, v = line.strip().partition("=")
        if k:
            out[k] = v
    return out


def source(repo):
    """The remote-tracking `main` that CARRIES the document.

    `origin` is not a fact about a checkout, it is the name a clone happened to
    use. hanzoai/cloud answers on several remotes and they are NOT one lineage:
    where `origin` is the GitHub OSS mirror, `origin/main` holds no
    `openapi.yaml` at its root at all. So the one question this file exists to
    ask on a clock — is the pin still current? — was being put to a repository
    that does not carry the document, where it could only die or agree by
    accident. It died quietly, and the pin drifted 24 releases behind while
    nothing went red. A gate that cannot fail is not a gate.

    So the remote is DISCOVERED, never named: fetch every one, keep those whose
    `main` holds the document, and take the one that contains all the others. A
    checkout with a `forge` remote gets no special case — forge wins here
    because it carries the file, and stops winning the day it stops carrying it.
    Unreachable is not fatal (a mirror nobody can read decides nothing) but
    stale is, which is why every remote is fetched before any is read.
    """
    ok = lambda *a: not subprocess.run(["git", "-C", repo, *a],
                                       capture_output=True).returncode
    carry = []
    for remote in git(repo, "remote").split():
        ok("fetch", "--quiet", remote)
        if ok("cat-file", "-e", f"{remote}/main:{SPEC_PATH}"):
            carry.append(f"{remote}/main")
    tip = [b for b in carry if all(ok("merge-base", "--is-ancestor", o, b) for o in carry)]
    if not tip:
        sys.exit(f"publish: no remote of {repo} carries {SPEC_PATH} on `main`\n"
                 f"         This is a {SPEC_REPO} checkout or it is nothing."
                 if not carry else
                 f"publish: {', '.join(carry)} each carry {SPEC_PATH} and have diverged "
                 f"— this checkout cannot say which one is {SPEC_REPO}'s main")
    return tip[0]


def document(repo, ref):
    """The document at one ref, with its digest. `source` has already fetched
    every remote, so a stale worktree cannot be mistaken for the branch it is
    behind, and a tag that lives on one remote resolves whoever cloned this."""
    raw = git(repo, "show", f"{ref}:{SPEC_PATH}")
    return raw, hashlib.sha256(raw.encode()).hexdigest()


# ------------------------------------------------------------ the deployment

def operations(doc):
    """{(METHOD, path)} — a document as the set of things a caller can call."""
    return {(m.upper(), p) for p, item in (doc.get("paths") or {}).items()
            for m, op in item.items() if m in HTTP_METHODS and isinstance(op, dict)}


def refuted(url=SERVED):
    """Which PUBLISHED operations the deployment does not answer for.

    `--check` proves hanzo.yaml is the projection of a git ref. That is the
    right question and it needs a hanzoai/cloud checkout to ask, so it can only
    run where a credential for a private repo exists — and this repo has none.
    So it has never run, and while it did not, this file went 81 commits stale
    and shipped `POST /v1/admin/credits` to every SDK for a mint hanzoai/cloud
    had deleted. A published operation for a route nothing serves is not a stale
    document: `skills.py` turns it into a SKILL.md, which is a live instruction
    to an agent to call a dead endpoint.

    This asks the weaker question that needs NOTHING — no checkout, no token, no
    ref — and therefore actually runs: every operation this repo publishes must
    be one `api.hanzo.ai` answers for. One direction only. Served-and-unpublished
    means the pin is behind, which `--current` already reports and which is not a
    lie about the API; published-and-unserved is the lie.

    Returns (refuted, published, served), or None when the deployment cannot be
    reached — no network, no verdict, exit 0, said loudly. Same rule as
    hanzo.ai's scripts/audit-catalog.mjs: a gate that fails on someone else's
    outage gets switched off, and then it gates nothing.
    """
    try:
        with urllib.request.urlopen(url, timeout=120) as r:
            live = operations(json.load(r))
    except Exception as e:                                    # noqa: BLE001
        print(f"publish: {url} did not answer ({e}) — NO VERDICT. "
              f"This gate refutes published operations against the running "
              f"deployment; it cannot do that from an unreachable one.")
        return None
    mine = operations(yaml.safe_load(open(TARGET)))
    return sorted(mine - live), mine, live


# ------------------------------------------------------------ the projection

def product(path):
    """The `/v1/<product>` a path belongs to, or None for the unprefixed few."""
    segs = path.strip("/").split("/")
    return segs[1] if len(segs) > 1 and segs[0] == "v1" else None


def genid(s):
    """An identifier's identity to a GENERATOR: punctuation stripped, case folded.

    OpenAPI says operationIds are unique as STRINGS, and they are —
    `get_v1_pricing-policy` and `get_v1_pricing_policy` differ by one character.
    Every generator then strips the punctuation and camel-cases what is left, so
    both arrive as `GetV1PricingPolicy` and the Go client declares one request
    type twice. Uniqueness has to be checked under the identity that breaks.
    """
    return re.sub(r"[^a-z0-9]", "", s.lower())


def project(doc, groups):
    """cloud's document -> the generatable one. SIX rules, each with its failure.

    1. TRACE is dropped (26 ops). They are cloud's wildcard relays projecting
       every method their router matches — a fact about the router, not a client
       surface — and no SDK should hand a caller a method every edge disables
       (Cross-Site Tracing). It is also the one method openapi-generator cannot
       emit for the JVM: it writes `RequestMethod.TRACE` beside a `RequestMethod`
       enum that stops at PUT, so no Java or Kotlin client compiles.

    2. `compat`-tagged operations are dropped (23). The SERVING BINARY declares
       that tag for a legacy address it keeps reachable for consumers pinned to
       it. Dropping it here respects the declaration rather than overruling it —
       the served surface is unchanged, and the published one says each thing
       once instead of putting two spellings of one operation in every SDK.

    3. Two tags become one (23 ops). A tag is a grouping hint to a reader and
       the emitted CLASS to a generator, so a two-tag operation is emitted
       TWICE under one identifier: `ApiPricingGetFullPricingRequest redeclared`
       in Go, and quieter — worse — elsewhere. The first tag is the primary by
       OpenAPI convention and what every doc site groups under.

    4. No tag becomes the owning app (44 ops). Untagged is not ungrouped, it is
       grouped somewhere nobody named: every generator files it under
       `DefaultApi`. `x-app` is the emitter's own answer to who serves it, so it
       is the tag; the `/v1/<product>` segment answers for the rest.

    5. No `responses` gets a `default` (1012 ops). THE BIG ONE, and the whole
       reason this projection exists: `openapi-generator validate` counts each
       one an ERROR and refuses the document entire, so cloud's emission cannot
       generate a client in ANY language as it stands. A `default` with no
       content says exactly what is known — the route answers, its shape is not
       declared at the source — which is what the weave already says by silence.
       This is the rule to move upstream: the day cloud's emitter writes that
       `default` itself, this rule and 90% of this function go.

    6. operationIds are made unique under `genid` (1 collision today,
       `deleteSession` vs `DeleteSession`). The later one by path order takes a
       suffix, which is what a generator does for the duplicates it can see —
       and it keeps the id cloud emitted as `x-id`, because an operationId is
       ALSO the wire name of an MCP tool. The suffix exists for Go; the door
       does not know it. Whoever needs the name a caller can use reads `x-id`
       first. The collision itself belongs upstream: two operations whose ids
       differ only in case are one name to every generator on earth.

    Nothing else. No operation is added, no served operation is removed, no
    prose is written — every summary and description below came out of a handler
    doc comment in hanzoai/cloud.
    """
    paths, dropped_trace, dropped_compat, defaults, retagged = {}, 0, 0, 0, 0
    for path, item in sorted((doc.get("paths") or {}).items()):
        out = {}
        for method, op in item.items():
            if method not in HTTP_METHODS:
                out[method] = op
                continue
            if not isinstance(op, dict):
                continue
            if method == "trace":                                       # 1
                dropped_trace += 1
                continue
            tags = list(op.get("tags") or [])
            if "compat" in tags:                                        # 2
                dropped_compat += 1
                continue
            op = dict(op)
            if len(tags) > 1:                                           # 3
                op["tags"] = tags[:1]
            elif not tags:                                              # 4
                op["tags"] = [op.get("x-app") or product(path) or "root"]
                retagged += 1
            if not op.get("responses"):                                 # 5
                op["responses"] = {"default": {"description": UNTYPED}}
                defaults += 1
            out[method] = op
        if any(m in HTTP_METHODS for m in out):
            paths[path] = out

    taken, renamed = set(), 0                                           # 6
    for path in sorted(paths):
        for method in HTTP_METHODS:
            op = paths[path].get(method)
            if not isinstance(op, dict):
                continue
            base = oid = op["operationId"]
            n = 2
            while genid(oid) in taken:
                oid, n = f"{base}_{n}", n + 1
            renamed += oid != base
            taken.add(genid(oid))
            op["operationId"] = oid
            if oid != base:
                # The id hanzoai/cloud emitted, kept because the rename above is
                # a fact about GENERATORS and the id is also the WIRE NAME: it is
                # what `POST /v1/mcp` answers to. Renaming it silently put
                # `DeleteSession_2` in the MCP catalogue of three client
                # distributions, and the door knows no such tool — a suffix
                # invented here for Go's benefit is not a thing anything serves.
                # Present only where the two differ, so its meaning is its
                # presence. `tools.py` names the tool by this.
                op["x-id"] = base

    used = []
    for item in paths.values():
        for method, op in item.items():
            if method in HTTP_METHODS and isinstance(op, dict):
                for t in op["tags"]:
                    if t not in used:
                        used.append(t)

    tag_groups, grouped = [], {}
    for domain in groups:
        members = [t for t in domain["tags"] if t in used]
        if members:
            tag_groups.append({"name": domain["title"], "tags": members})
        for t in domain["tags"]:
            grouped.setdefault(t, domain["title"])

    prose = {t["name"]: t.get("description") for t in (doc.get("tags") or [])
             if isinstance(t, dict) and t.get("name")}
    tags = [{"name": t, "description": prose[t]} if prose.get(t) else {"name": t}
            for group in tag_groups for t in group["tags"]]

    out = dict(doc)
    out["paths"] = paths
    out["tags"] = tags
    out["x-tagGroups"] = tag_groups
    # The credential, as ONE decision: the requirement is built FROM the
    # definitions, so the two names cannot disagree. A requirement naming a
    # scheme the document does not define is dropped in silence by every stage —
    # `validate` reports no issue, the generator warns about nothing, and the
    # call site asks for no credential (`_auth_settings = []` in python, no
    # `setBearerAuthToObject` in typescript, `new String[] {  }` in java) while
    # `access_token` and `HttpBearerAuth` are still emitted beside it. The client
    # compiles, the caller sets a token, and nothing is ever sent.
    #
    # cloud's emission declares its own scheme and what it accepts there — an IAM
    # access token or a pk-/sk- key, spelled `Authorization`, `X-Authorization`
    # or Basic — so the projection takes that name and that prose rather than
    # minting a second name for the one credential. When it declares none, a
    # client has no credential to send at all, so the IAM bearer is supplied.
    components = dict(out.get("components") or {})
    schemes = components.get("securitySchemes") or {
        "bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT",
                       "description": "A JWT issued by Hanzo IAM (https://hanzo.id)."}}
    components["securitySchemes"] = schemes
    out["components"] = components
    out["security"] = out.get("security") or [{name: []} for name in schemes]
    return out, {
        "paths": len(paths), "ops": len(taken), "tags": len(tags),
        "described_tags": sum(1 for t in tags if t.get("description")),
        "groups": len(tag_groups), "trace": dropped_trace, "compat": dropped_compat,
        "default": defaults, "retagged": retagged, "renamed": renamed,
        "ungrouped": sorted(set(used) - set(grouped)),
        "unused": sorted(t for t in grouped if t not in used),
    }


# ---------------------------------------------------------------- the index

def index(groups, doc):
    """CAPABILITIES.md — the human index, DERIVED, never hand-edited.

    One row per tag the document carries, with the operation count and the
    prose the owning Go package's doc comment supplied. A capability is on this
    page because the router registered it, which is the only reason a capability
    was ever supposed to be on it."""
    counts, described = {}, {}
    for item in (doc.get("paths") or {}).values():
        for method, op in item.items():
            if method in HTTP_METHODS and isinstance(op, dict):
                counts[op["tags"][0]] = counts.get(op["tags"][0], 0) + 1
    for t in doc.get("tags") or []:
        if isinstance(t, dict) and t.get("description"):
            described[t["name"]] = " ".join(t["description"].split())

    out = ["<!-- GENERATED by publish.py from hanzo.yaml — DO NOT EDIT. "
           "Change the API in hanzoai/cloud; group a new capability in "
           "capabilities.yaml; run `python3 publish.py`. -->", "",
           "# Hanzo Capability Manifest", "",
           f"Every capability the API serves, at "
           f"`{doc['info'].get('x-spec', {}).get('ref', '?')}`. GENERATED from "
           f"`hanzo.yaml` — which is itself generated from hanzoai/cloud's own "
           f"emission — so a name is on this page if and only if a router "
           f"registered operations under it. Nothing here is authored, and there "
           f"is nothing to author: a capability appears the release it starts "
           f"being served and leaves the release it stops.", ""]
    for group in doc.get("x-tagGroups") or []:
        domain = next((d for d in groups if d["title"] == group["name"]), {})
        out += [f"## {group['name']}", ""]
        if domain.get("role"):
            out += [f"*{domain['role']}*", ""]
        out += ["| Capability | Operations | What it is |", "|---|---:|---|"]
        for t in group["tags"]:
            out.append(f"| `{t}` | {counts.get(t, 0)} | {described.get(t, '')} |")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


# ---------------------------------------------------------------- the command

def derive(raw, ref, sha):
    """(hanzo.yaml text, CAPABILITIES.md text, counters) from one document."""
    groups = (yaml.safe_load(open(REGISTRY)) or {}).get("domains") or []
    doc = yaml.safe_load(raw)
    out, n = project(doc, groups)
    if n["ungrouped"]:
        sys.exit(f"publish: the document serves capabilities capabilities.yaml does "
                 f"not group: {n['ungrouped']}\n"
                 f"         A new product is a name somebody has to place. Add each "
                 f"to a domain's `tags:` and re-run.")
    if n["unused"]:
        sys.exit(f"publish: capabilities.yaml groups names the document does not "
                 f"carry: {n['unused']}\n"
                 f"         Nothing serves them, so nothing can be filed under them. "
                 f"Remove each from capabilities.yaml and re-run.")
    out["info"] = dict(out["info"])
    # The release generation of the PUBLICATION. Three versions, three meanings,
    # and they must not be collapsed: the API's is `/v1` (immutable, in the
    # path), the emitting release's is `x-spec.ref`, and this one names the shape
    # of the published projection — which is what every SDK's package version is
    # cut from, so it may only move forward.
    out["info"]["version"] = "8.0.0"
    out["info"]["x-spec"] = {"repo": SPEC_REPO, "path": SPEC_PATH,
                             "ref": ref, "sha256": sha}
    text = yaml.dump(out, default_flow_style=False, sort_keys=False, width=120)
    return text, index(groups, out), n


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cloud", default=CLOUD, help=f"{SPEC_REPO} checkout (default {CLOUD})")
    ap.add_argument("--ref", help="the release to publish (default: the pinned one, "
                                  "or the main that carries the document when re-pinning)")
    ap.add_argument("--check", action="store_true",
                    help="re-derive at the PINNED ref and diff; write nothing")
    ap.add_argument("--current", action="store_true",
                    help="report whether the pin is still the tip of the remote that "
                         "carries the document")
    ap.add_argument("--served", action="store_true",
                    help=f"THE GATE that needs no checkout: refute every published "
                         f"operation against {SERVED}")
    a = ap.parse_args()

    have = lock()

    # First, and before `checkout`: this is the one question that needs no
    # hanzoai/cloud on disk, which is the whole reason it is the one in
    # `hanzo.yml`'s `test:` block.
    if a.served:
        answer = refuted()
        if answer is None:
            return 0
        gone, mine, live = answer
        if gone:
            print(f"publish: hanzo.yaml publishes {len(gone)} operation(s) "
                  f"{SERVED} does not answer for.\n"
                  f"         Every SDK, doc page and agent skill generated from this "
                  f"file advertises them. Fix: `python3 publish.py` to re-pin to the "
                  f"release that is deployed.")
            for method, path in gone:
                print(f"           {method:7} {path}")
            return 1
        print(f"all {len(mine)} published operations are served "
              f"({len(live - mine)} more are served and not yet published — "
              f"`--current` is the question about the pin)")
        return 0

    repo = checkout(a.cloud)
    branch = source(repo)

    if a.current:
        tip = git(repo, "rev-parse", branch).strip()
        at = git(repo, "rev-parse", f"{have.get('ref', branch)}^{{commit}}").strip()
        if tip == at:
            print(f"hanzo.yaml is {SPEC_REPO}@{have.get('ref')} — {branch}")
            return 0
        _, sha = document(repo, branch)
        if sha == have.get("sha256"):
            print(f"hanzo.yaml is {SPEC_REPO}@{have.get('ref')} — {branch} has moved "
                  f"({tip[:8]}) but the document has not")
            return 0
        print(f"hanzo.yaml is {SPEC_REPO}@{have.get('ref')}; {branch} is "
              f"{tip[:8]} with a different document — run `python3 publish.py`")
        return 1

    ref = a.ref or (have.get("ref") if a.check else None) or branch
    if a.check and not have.get("ref"):
        sys.exit("publish: --check needs a .spec-lock naming the document this "
                 "artifact is a projection of; run `python3 publish.py` first")

    # Name the COMMIT from here on. `ref` arrives as whatever found the document —
    # a tag, a sha, or (by default) a remote-tracking branch. A branch is a moving
    # tip here and is not resolvable at all in the CI clone that later re-derives
    # this artifact, which has no remotes. Resolving once, before anything reads
    # it, is what keeps `x-spec.ref`, `.spec-lock`, and `--check` naming one thing.
    ref = git(repo, "rev-parse", f"{ref}^{{commit}}").strip()

    raw, sha = document(repo, ref)
    if a.check and have.get("sha256") and sha != have["sha256"]:
        sys.exit(f"publish: {SPEC_REPO}@{ref}:{SPEC_PATH} hashes to {sha}, but "
                 f".spec-lock says {have['sha256']} — the ref moved under this "
                 f"projection")

    text, md, n = derive(raw, ref, sha)

    if a.check:
        stale = [name for name, want in ((TARGET, text), (INDEX, md))
                 if (open(name).read() if os.path.exists(name) else None) != want]
        if stale:
            print(f"publish: {', '.join(os.path.basename(f) for f in stale)} is not "
                  f"what {SPEC_REPO}@{ref} projects to.\n"
                  f"         This artifact is GENERATED — an edit to it describes a "
                  f"release nobody shipped. Change the API in hanzoai/cloud, then run "
                  f"`python3 publish.py`.")
            return 1
        print(f"hanzo.yaml is the projection of {SPEC_REPO}@{ref} "
              f"({n['paths']} paths, {n['ops']} operations)")
        return 0

    open(TARGET, "w").write(text)
    open(INDEX, "w").write(md)
    open(LOCK, "w").write(f"ref={ref}\nsha256={sha}\nrepo={SPEC_REPO}\npath={SPEC_PATH}\n")
    print(f"hanzo.yaml <- {SPEC_REPO}@{ref[:12]}:{SPEC_PATH} ({sha[:12]})")
    print(f"{n['paths']} paths, {n['ops']} operations, {n['tags']} capabilities "
          f"({n['described_tags']} described) in {n['groups']} domains")
    print(f"projected: {n['trace']} TRACE and {n['compat']} compat operations dropped, "
          f"{n['default']} given a `default` response, {n['retagged']} tagged by their "
          f"app, {n['renamed']} operationIds suffixed to stay distinct in codegen")
    return 0


if __name__ == "__main__":
    sys.exit(main())
