#!/usr/bin/env python3
"""Golden test for tools.py — the MCP tool catalogue generator.

Runnable standalone (`python3 test_tools.py`, non-zero exit on failure) AND under
pytest (functions named `test_*`). It reads the COMMITTED `hanzo.yaml` and
asserts the properties the catalogue promises, WITHOUT depending on any committed
output (dist/ is generated, never committed):

  • name IS the id the operation is SERVED under — verbatim, every tool, no
    exception. This is the whole contract. A generator that synthesises names
    from paths is a THIRD naming rule, and a third rule is the disease this file
    exists to prevent — as is publishing `publish.py` rule 6's codegen suffix,
    which the door does not answer to;
  • one name, one tool     — a duplicate id makes the second tool unreachable;
  • callable verbs only    — OPTIONS/TRACE are transport machinery, never tools;
  • self-contained schemas — every `$ref` a tool emits resolves inside that
    tool's OWN `$defs`. A pointer into `#/components` would leave the catalogue
    depending on a document the client does not ship;
  • total                  — every named operation in the document becomes a
    tool. A projection that silently drops operations is how a client ends up
    with 25 tools while the API has thousands;
  • deterministic          — two generations are byte-identical, which is what
    the `--check` drift gate rests on.
"""
import json
import os
import tempfile

import yaml

import tools

DOC = yaml.safe_load(open(tools.DOCUMENT))
CATALOGUE = tools.catalogue()


def _ids():
    """(served id, METHOD path) for every callable operation in the document."""
    for path, item in (DOC.get("paths") or {}).items():
        if not isinstance(item, dict):
            continue
        for method in tools.VERBS:
            op = item.get(method)
            if isinstance(op, dict) and tools.wire(op):
                yield tools.wire(op), f"{method.upper()} {path}"


def test_name_is_the_operation_id():
    # Every tool name is an id the document actually publishes — verbatim.
    published = {oid for oid, _ in _ids()}
    for t in CATALOGUE:
        assert t["name"] in published, \
            f"tool {t['name']!r} is not an operationId in the document — a name was invented"


def test_no_codegen_suffix_becomes_a_tool_name():
    """Rule 6's suffix is a fact about Go, and the door does not answer to it.

    `publish.py` renames an operationId when two collide under the identity a
    generator uses, so `DELETE /v1/o11y/sessions` is published as
    `DeleteSession_2` and served as `DeleteSession`. Shipped verbatim, that put
    a name in three client distributions — npm `@hanzo/mcp`, PyPI `hanzo-mcp`,
    crates.io `hanzo-mcp` — that nothing can be told to run, which is exactly the
    defect the catalogue exists to remove and the one shape of it a static
    artifact CAN refuse: the document itself records what it renamed.
    """
    got = {t["name"] for t in CATALOGUE}
    wrong = []
    for path, item in (DOC.get("paths") or {}).items():
        if not isinstance(item, dict):
            continue
        for method in tools.VERBS:
            op = item.get(method)
            if not isinstance(op, dict) or not op.get("x-id"):
                continue
            if op["x-id"] not in got:
                wrong.append(f"{method.upper()} {path}: served as {op['x-id']!r}, no tool")
            if op["operationId"] in got:
                wrong.append(f"{method.upper()} {path}: published the codegen name "
                             f"{op['operationId']!r} as a tool")
    assert not wrong, "\n".join(wrong)


def test_names_unique_and_sorted():
    names = [t["name"] for t in CATALOGUE]
    assert len(names) == len(set(names)), "duplicate tool names"
    assert names == sorted(names), "catalogue is not sorted by name"


def test_total():
    # Nothing named in the document is dropped on the floor.
    published = {oid for oid, _ in _ids()}
    got = {t["name"] for t in CATALOGUE}
    missing = published - got
    assert not missing, f"{len(missing)} operations produced no tool: {sorted(missing)[:10]}"


def test_no_transport_verbs():
    # OPTIONS/TRACE exist in the document and must never become tools.
    got = {t["name"] for t in CATALOGUE}
    leaked = []
    for path, item in (DOC.get("paths") or {}).items():
        if not isinstance(item, dict):
            continue
        for method in ("options", "trace", "head"):
            op = item.get(method)
            if isinstance(op, dict) and tools.wire(op) in got:
                leaked.append(f"{method.upper()} {path}")
    assert not leaked, f"transport verbs became tools: {leaked[:10]}"


def test_schemas_are_self_contained():
    # Every $ref resolves inside the tool's own $defs. Nothing points at
    # #/components, which the client does not ship.
    def refs(node):
        if isinstance(node, dict):
            r = node.get("$ref")
            if isinstance(r, str):
                yield r
            for v in node.values():
                yield from refs(v)
        elif isinstance(node, list):
            for v in node:
                yield from refs(v)

    dangling, foreign = [], []
    for t in CATALOGUE:
        s = t["inputSchema"]
        have = set(s.get("$defs") or {})
        for r in refs(s):
            if not r.startswith("#/$defs/"):
                foreign.append((t["name"], r))
            elif r[len("#/$defs/"):] not in have:
                dangling.append((t["name"], r))
    assert not foreign, f"{len(foreign)} refs escape the tool: {foreign[:5]}"
    assert not dangling, f"{len(dangling)} refs resolve to nothing: {dangling[:5]}"


def test_input_schema_shape():
    for t in CATALOGUE:
        s = t["inputSchema"]
        assert isinstance(s, dict), t["name"]
        assert s.get("type") == "object", f"{t['name']}: inputSchema is not an object schema"
        assert isinstance(s.get("properties"), dict), f"{t['name']}: no properties map"
        for k in (s.get("required") or []):
            assert k in s["properties"], f"{t['name']}: required {k!r} is not a property"


def test_deterministic():
    a = tools.render(tools.catalogue())
    b = tools.render(tools.catalogue())
    assert a == b, "two generations differ"
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "tools.json")
        n = tools.generate(p)
        assert n == len(CATALOGUE), f"generate() reported {n}, catalogue has {len(CATALOGUE)}"
        assert open(p).read() == a, "written bytes differ from render()"
        assert json.load(open(p))["count"] == len(CATALOGUE)


def test_duplicate_id_is_refused():
    # The one thing that must fail loudly rather than silently shadow a tool.
    doc = {"paths": {"/a": {"get": {"operationId": "dup"}},
                     "/b": {"get": {"operationId": "dup"}}}}
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "doc.yaml")
        open(p, "w").write(yaml.safe_dump(doc))
        try:
            tools.catalogue(p)
        except SystemExit as e:
            assert "dup" in str(e)
            return
        raise AssertionError("a duplicate operationId was accepted")


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"ok   {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
