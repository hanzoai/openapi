#!/usr/bin/env python3
"""Tests for the published artifact — the gate that makes `hanzo.yaml` OUTPUT.

Runnable standalone (`python3 test_publish.py`, non-zero exit on failure) AND
under pytest, like test_flows.py beside it.

These are the OFFLINE half. They read the committed `hanzo.yaml` and assert the
properties `publish.py` promises, so a hand edit that satisfies none of them is
caught here without a network or a hanzoai/cloud checkout.

The half that reaches the world is `python3 publish.py --served`, which refutes
every published operation against the document api.hanzo.ai actually serves. It
is what CI runs, because it is the only one of the three online questions that
needs no credential — see the last test in this file, which asserts it is still
WIRED. `publish.py --check` is the sharper question and needs a hanzoai/cloud
checkout; it runs where one exists.

None of them replaces another: `--check` needs the input, `--served` needs the
deployment, these need nothing.
"""
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))
METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace")


def load():
    doc = yaml.safe_load(open(os.path.join(ROOT, "hanzo.yaml")))
    ops = [(m, p, op) for p, item in doc["paths"].items()
           for m, op in item.items() if m in METHODS and isinstance(op, dict)]
    return doc, ops


def lock():
    out = {}
    for line in open(os.path.join(ROOT, ".spec-lock")):
        k, _, v = line.strip().partition("=")
        if k:
            out[k] = v
    return out


def test_the_artifact_names_the_release_it_came_from():
    """Without this the document cannot answer "which release am I?", and every
    consumer pinning it is pinning a file rather than a version."""
    doc, _ = load()
    spec, have = doc["info"]["x-spec"], lock()
    assert spec["repo"] == have["repo"] == "hanzoai/cloud"
    assert spec["path"] == have["path"] == "openapi.yaml"
    assert spec["ref"] == have["ref"], "hanzo.yaml and .spec-lock name different refs"
    assert re.fullmatch(r"[0-9a-f]{64}", spec["sha256"])
    assert spec["sha256"] == have["sha256"], "hanzo.yaml and .spec-lock name different digests"


def test_every_operation_is_generatable():
    """The six projection rules, checked on the OUTPUT rather than trusted from
    the code that wrote it. Each failure here is a language that stops compiling:
    a missing `responses` is 1012 validator errors and zero files written, two
    tags is one identifier declared twice, no tag is DefaultApi, and TRACE is a
    `RequestMethod` constant the JVM generator never emits."""
    _, ops = load()
    assert ops, "no operations"
    for m, p, op in ops:
        assert m != "trace", f"TRACE survived at {p}"
        assert op.get("responses"), f"{m.upper()} {p} declares no responses"
        assert len(op.get("tags") or []) == 1, f"{m.upper()} {p} has tags {op.get('tags')}"
        assert op.get("operationId"), f"{m.upper()} {p} has no operationId"


def test_operationids_are_unique_to_a_generator():
    """Unique as STRINGS is what OpenAPI asks and is not enough: every generator
    strips punctuation and camel-cases, so `x-y` and `x_y` arrive as one name and
    the client declares one request type twice."""
    _, ops = load()
    seen = {}
    for _, p, op in ops:
        key = re.sub(r"[^a-z0-9]", "", op["operationId"].lower())
        assert key not in seen, (f"{op['operationId']} ({p}) and {seen[key]} are one "
                                 f"identifier to a generator")
        seen[key] = f"{op['operationId']} ({p})"


def test_a_client_can_authenticate():
    """cloud's emission declares no security scheme, so a client generated from
    it sends no Authorization header and every call 401s."""
    doc, _ = load()
    assert doc.get("security"), "no document-level security"
    assert (doc["components"].get("securitySchemes") or {}).get("bearerAuth")


def test_every_capability_is_grouped_exactly_once():
    """The curation law, from the artifact's side. capabilities.yaml is the one
    editorial file left here, and it may only ARRANGE the served API — a tag it
    misses is a product no doc site files anywhere, a tag it adds is a heading
    with nothing under it."""
    doc, ops = load()
    used = {op["tags"][0] for _, _, op in ops}
    grouped = [t for g in doc["x-tagGroups"] for t in g["tags"]]
    assert sorted(grouped) == sorted(set(grouped)), "a capability is in two domains"
    assert set(grouped) == used, (f"ungrouped: {sorted(used - set(grouped))}; "
                                 f"grouped but unserved: {sorted(set(grouped) - used)}")


# Schemas whose PROPERTY NAMES cannot be projected into Go, pinned as a ceiling
# rather than gated to zero. Every generator Pascal-cases a property name and
# emits `Get<F>`, `Get<F>Ok`, `Has<F>`, `Set<F>` beside it, so two spellings of
# one field collide into one struct field, and a field literally named
# `hasClusterName` collides with the accessor for `clusterName`:
#
#   o11y.GettableAgentCheckIn  integration_config + integrationConfig
#                              removed_at + removedAt
#   o11y.O11yPodOnboarding     hasClusterName / hasNamespaceName / hasNodeName
#   o11y.PostableProfile       has_existing_observability_tool
#
# MEASURED at cloud@v1.801.383: `go build ./...` on the generated client fails on
# these three and on nothing else — renaming those keys in a scratch copy of the
# document and regenerating gives exit 0. They are hanzoai/cloud's schemas to fix
# and this repo must NOT rename a field, because a field name is the wire.
#
# A ceiling and not a zero, because holding the publish hostage to another repo's
# schema helps nobody: what matters is that a FOURTH one cannot arrive unnoticed.
GO_UNSAFE = {"o11y.GettableAgentCheckIn", "o11y.O11yPodOnboarding", "o11y.PostableProfile"}


def test_no_new_schema_becomes_ungeneratable_in_go():
    doc, _ = load()

    def pascal(p):
        return "".join(w[:1].upper() + w[1:] for w in re.split(r"[^A-Za-z0-9]+", p) if w)

    bad = set()
    for name, schema in (doc["components"].get("schemas") or {}).items():
        props = (schema or {}).get("properties") or {}
        fields = [pascal(p) for p in props]
        if len(set(fields)) != len(fields):
            bad.add(name)
        for f in fields:
            for prefix in ("Get", "Has", "Set"):
                if f.startswith(prefix) and f[len(prefix):] in fields:
                    bad.add(name)
    assert bad <= GO_UNSAFE, (
        f"schema(s) the Go client cannot be generated from, beyond the pinned "
        f"three: {sorted(bad - GO_UNSAFE)}. Two spellings of one field, or a "
        f"property named for its own accessor. Fix in hanzoai/cloud — a field "
        f"name is the wire, and renaming it here would be a lie.")


def test_no_authored_spec_survives():
    """The inversion, as a fact about the tree. A `<svc>/openapi.yaml` reappearing
    is a second authority reappearing, and it would reach the skills plane — which
    has no liveness filter — as an instruction to call whatever it declares."""
    strays = sorted(d for d in os.listdir(ROOT)
                    if os.path.isfile(os.path.join(ROOT, d, "openapi.yaml")))
    assert not strays, (f"hand-authored spec dir(s) are back: {strays}. The API is "
                        f"declared in hanzoai/cloud; this repo publishes what it emits.")


def test_the_drift_gate_is_wired_into_the_build():
    """A gate that cannot fail a build is not a gate, and this repo proved it.

    `publish.py --check` was the only thing standing between a hand edit and
    seven SDKs, and it lived in a workflow no forge collected, needing a
    credential no secret supplied. It exited 1 on `main` for 81 hanzoai/cloud
    commits while every consumer regenerated happily. Nothing NOTICED, because
    nothing ran it.

    So the gate that replaced it is asserted from inside the suite that does
    run: `served` must be a `test:` entry in hanzo.yml — the one file both
    hanzoai/ci and platform.hanzo.ai read — and it must invoke `--served`.
    Deleting the gate now has to delete this test, in the same diff, on purpose.
    """
    cfg = yaml.safe_load(open(os.path.join(ROOT, "hanzo.yml"))) or {}
    gates = {g.get("name"): g.get("run", "") for g in (cfg.get("test") or [])}
    assert "served" in gates, (
        f"hanzo.yml declares no `served` test gate, so nothing refutes a "
        f"published operation against the running deployment. Gates: "
        f"{sorted(gates)}")
    assert "publish.py --served" in gates["served"], (
        "the `served` gate does not run `publish.py --served`")


def test_every_declared_image_can_be_named():
    """The checks above run only if the steps BEFORE them succeed, so this one
    guards the whole suite's right to execute.

    hanzoai/ci names an image with bin/imgver, which reads a version from
    package.json / Cargo.toml / VERSION / pyproject.toml and refuses to invent
    one. This repo is a script and a document; it had none of the four, so imgver
    exited 1, `Build & push images` failed, and every later step of that job —
    including the one that runs THIS FILE — was skipped. 100% of cicd runs failed
    that way, which is how a repo ends up with two carefully-written checks and
    no evidence either has ever run.

    A version file is therefore not packaging trivia here, it is the precondition
    for being checked at all. `0.0.0` is spelled out because imgver discards it
    as a workspace stub, which would fail exactly as if the file were missing.
    """
    cfg = yaml.safe_load(open(os.path.join(ROOT, "hanzo.yml"))) or {}
    for img in (cfg.get("images") or []):
        ctx = img.get("context", ".")
        named = [f for f in ("package.json", "Cargo.toml", "VERSION", "pyproject.toml")
                 if os.path.isfile(os.path.join(ROOT, ctx, f))]
        assert named, (
            f"hanzo.yml declares image {img.get('name')!r} at context {ctx!r}, but "
            f"nothing there declares a version. imgver refuses to publish a sha, so "
            f"the build fails and every test step after it is skipped.")
        if "VERSION" in named:
            v = open(os.path.join(ROOT, ctx, "VERSION")).read().strip().lstrip("v")
            assert re.fullmatch(r"\d+\.\d+\.\d+", v), f"VERSION is not semver: {v!r}"
            assert v != "0.0.0", "imgver discards 0.0.0 as a stub — name a real version"


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"ok   {name}")
            except AssertionError as e:
                failures += 1
                print(f"FAIL {name}: {e}")
    sys.exit(1 if failures else 0)
