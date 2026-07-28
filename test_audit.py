#!/usr/bin/env python3
"""Tests for audit.py — the gate that decides when a generated spec may replace a
hand-written one.

Runnable standalone (`python3 test_audit.py`, non-zero exit on failure) AND under
pytest. Every case is a way a replacement can regress, because the whole value of
this script is refusing a replacement that would:

  • drop a route      — the contract declares it, the routes do not serve it;
  • drop the prose    — the route survives, its description or example does not;
  • fail silently     — an unpromoted service must NOT break the build, and a
                        promoted one MUST.

Route identity is the shape (parameters erased), so renaming {id} to {name} is
reported but is not a missing route — it is a label change, and counting it as a
gap would stall a promotion for nothing.
"""
import contextlib
import io
import json
import os
import sys
import tempfile

import yaml

import audit


def op(description=None, request_example=None, response_example=None):
    o = {"operationId": "x", "responses": {"200": {"description": "ok"}}}
    if description:
        o["description"] = description
    if request_example is not None:
        o["requestBody"] = {"content": {"application/json": {"example": request_example}}}
    if response_example is not None:
        o["responses"]["200"]["content"] = {"application/json": {"example": response_example}}
    return o


def spec(paths):
    return {"openapi": "3.1.0", "info": {"title": "t", "version": "8.0.0"}, "paths": paths}


@contextlib.contextmanager
def tree(hand, generated, derived=(), internal=()):
    """A miniature repo: one service's contract, its emitted spec, the registry."""
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "svc"))
        os.makedirs(os.path.join(root, "generated"))
        with open(os.path.join(root, "svc", "openapi.yaml"), "w") as f:
            yaml.safe_dump(hand, f)
        with open(os.path.join(root, "generated", "svc.json"), "w") as f:
            json.dump(generated, f)
        with open(os.path.join(root, "capabilities.yaml"), "w") as f:
            yaml.safe_dump({"derived": list(derived), "internal": list(internal)}, f)
        old = (audit.ROOT, audit.GENERATED, audit.CAPABILITIES)
        audit.ROOT = root
        audit.GENERATED = os.path.join(root, "generated")
        audit.CAPABILITIES = os.path.join(root, "capabilities.yaml")
        try:
            yield root
        finally:
            audit.ROOT, audit.GENERATED, audit.CAPABILITIES = old


def run(argv):
    """audit.main() with argv, capturing stdout — returns (exit code, report)."""
    old = sys.argv
    sys.argv = ["audit.py"] + argv
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
            code = audit.main()
    finally:
        sys.argv = old
    return code, buf.getvalue()


def one(hand, generated, prefix=""):
    with tempfile.TemporaryDirectory() as d:
        h = os.path.join(d, "h.yaml")
        g = os.path.join(d, "g.json")
        with open(h, "w") as f:
            yaml.safe_dump(hand, f)
        with open(g, "w") as f:
            json.dump(generated, f)
        return audit.audit("svc", h, g, prefix)


def test_identical_is_complete():
    s = spec({"/v1/svc/things": {"get": op("List things.")}})
    r = one(s, s)
    assert r["complete"], r
    assert r["covered"] == 1 and not r["missing"] and not r["extra"]


def test_missing_route_blocks_promotion():
    """The exact regression this gate exists to catch: the contract declares a
    route the typed surface never registers, so replacing it deletes an
    operation from every SDK generated downstream."""
    hand = spec({"/v1/svc/a": {"get": op()}, "/v1/svc/b": {"post": op()}})
    gen = spec({"/v1/svc/a": {"get": op()}})
    r = one(hand, gen)
    assert not r["complete"]
    assert r["missing"] == ["POST /v1/svc/b"], r["missing"]


def test_undeclared_route_is_reported_but_not_a_regression():
    """A served route the contract never declared is a gap in the CONTRACT. It is
    the reason to generate at all, so it must not block the promotion it argues
    for."""
    hand = spec({"/v1/svc/a": {"get": op()}})
    gen = spec({"/v1/svc/a": {"get": op()}, "/v1/svc/new": {"get": op()}})
    r = one(hand, gen)
    assert r["complete"], r
    assert r["extra"] == ["GET /v1/svc/new"]


def test_lost_description_blocks_promotion():
    hand = spec({"/v1/svc/a": {"get": op("What it does.")}})
    gen = spec({"/v1/svc/a": {"get": op()}})
    r = one(hand, gen)
    assert not r["complete"]
    assert r["lost_prose"] == {"GET /v1/svc/a": ["description"]}, r["lost_prose"]


def test_lost_examples_block_promotion():
    hand = spec({"/v1/svc/a": {"post": op("d", request_example={"a": 1},
                                          response_example={"b": 2})}})
    gen = spec({"/v1/svc/a": {"post": op("d")}})
    r = one(hand, gen)
    assert r["lost_prose"] == {"POST /v1/svc/a": ["request-example", "response-example"]}


def test_reworded_prose_is_not_a_loss():
    """Presence, not prose equality — a generated description is written by the
    handler's author and will not match the hand-written wording, and demanding
    that it does would make the gate unpassable."""
    hand = spec({"/v1/svc/a": {"get": op("The old words.")}})
    gen = spec({"/v1/svc/a": {"get": op("Entirely different words.")}})
    assert one(hand, gen)["complete"]


def test_parameter_rename_is_the_same_route():
    hand = spec({"/v1/svc/things/{id}": {"get": op()}})
    gen = spec({"/v1/svc/things/{name}": {"get": op()}})
    r = one(hand, gen)
    assert r["complete"] and not r["missing"], r
    assert r["renamed_params"] == [
        {"contract": "/v1/svc/things/{id}", "generated": "/v1/svc/things/{name}", "method": "GET"}
    ]


def test_prefix_lifts_a_mounted_app():
    hand = spec({"/v1/svc/a": {"get": op()}})
    gen = spec({"/a": {"get": op()}})
    assert not one(hand, gen)["complete"]
    assert one(hand, gen, prefix="/v1/svc")["complete"]


def test_response_example_only_counts_on_success():
    """An example on a 4xx is not the example a client copies."""
    hand = spec({"/v1/svc/a": {"get": {"responses": {
        "200": {"description": "ok", "content": {"application/json": {"example": {"ok": 1}}}}}}}})
    gen = spec({"/v1/svc/a": {"get": {"responses": {
        "200": {"description": "ok"},
        "404": {"description": "no", "content": {"application/json": {"example": {"e": 1}}}}}}}})
    assert one(hand, gen)["lost_prose"] == {"GET /v1/svc/a": ["response-example"]}


def test_check_is_report_only_until_promoted():
    """The rule from the brief: land the pipeline and the drift check FIRST, in
    report-only mode. An incomplete service that nobody promoted is information."""
    hand = spec({"/v1/svc/a": {"get": op()}, "/v1/svc/b": {"get": op()}})
    gen = spec({"/v1/svc/a": {"get": op()}})
    with tree(hand, gen, derived=()):
        code, out = run(["--check"])
    assert code == 0, "an unpromoted service must not break the build"
    assert "report-only" in out


def test_check_fails_once_promoted():
    hand = spec({"/v1/svc/a": {"get": op()}, "/v1/svc/b": {"get": op()}})
    gen = spec({"/v1/svc/a": {"get": op()}})
    with tree(hand, gen, derived=["svc"]):
        code, _ = run(["--check"])
    assert code == 1, "a DERIVED service that regressed must break the build"


def test_promoted_and_clean_passes():
    s = spec({"/v1/svc/a": {"get": op("d")}})
    with tree(s, s, derived=["svc"]):
        code, out = run(["--check"])
    assert code == 0
    assert "DERIVED" in out


def test_internal_service_is_not_audited():
    hand = spec({"/v1/svc/a": {"get": op()}, "/v1/svc/b": {"get": op()}})
    gen = spec({"/v1/svc/a": {"get": op()}})
    with tree(hand, gen, derived=["svc"], internal=["svc"]):
        code, out = run(["--check"])
    assert code == 0, "internal services are outside the published contract"
    assert "internal" in out


def test_json_report_is_machine_readable():
    s = spec({"/v1/svc/a": {"get": op("d")}})
    with tree(s, s):
        _, out = run(["--json"])
    doc = json.loads(out)
    assert doc["reports"][0]["service"] == "svc"
    assert doc["reports"][0]["complete"] is True


def test_service_without_a_generated_spec_is_skipped_not_failed():
    s = spec({"/v1/svc/a": {"get": op()}})
    with tree(s, s, derived=["svc"]):
        code, out = run(["--check", "other"])
    assert code == 0
    assert "does not emit a spec yet" in out


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            fn()
            print(f"PASS {name}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL {name}: {e}")
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)


def test_master_contract_is_a_root_file_not_a_directory():
    """The whole-binary spec is measured against hanzo.yaml, which lives at the
    root rather than in a directory of its own. Both shapes are contracts, so
    finding either is what lets one script audit a service and the master."""
    s = spec({"/v1/svc/things": {"get": op("List things.")}})
    with tree(s, s) as root:
        with open(os.path.join(root, "master.yaml"), "w") as f:
            yaml.safe_dump(s, f)
        with open(os.path.join(root, "generated", "master.json"), "w") as f:
            json.dump(s, f)
        code, out = run(["master"])
    assert code == 0, out
    assert "master" in out and "skip" not in out, out
