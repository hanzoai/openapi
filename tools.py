#!/usr/bin/env python3
"""Project the published document into the MCP tool catalogue.

    python3 tools.py            # write dist/tools.json
    python3 tools.py --check    # drift gate: regenerate and diff against dist/
    python3 tools.py --stat     # counts only, write nothing

ONE source, and the source is the DOCUMENT. A tool name is an operation id:
not derived from the path, not looked up in a table, not invented here. The
fleet's own door already answers that way — every tool `POST /v1/mcp` lists is
verbatim an id hanzo-inc/cloud emitted — so a catalogue built any other way would
name tools the API cannot be told to run. Which is measurable, and was measured
against the door: the id, not the published `operationId`. `publish.py` rule 6
suffixes an id when two collide under a generator's identity, and that suffix is
a fact about Go rather than about the API — see `wire()`, which is the only
place a tool gets its name.
That is the whole defect this file removes: three client distributions
(npm `@hanzo/mcp`, PyPI `hanzo-mcp`, crates.io `hanzo-mcp`) each hand-kept
their own idea of what the fleet exposes, and hand-kept sets do not agree.

Why a client needs this at all, when hanzo-inc/cloud deliberately does NOT commit
one: the server can ASK its subsystems at the moment it is asked (package
fleet), so a checked-in catalogue there would be a second artifact free to go
stale beside the first — which is exactly how plugin/<app>/mcp.json went 353
operations stale and why it was deleted. A CLIENT has no such luxury. It is
installed from a registry with no fleet in reach, so it ships a list; the only
honest list is a projection of the contract, regenerated and diffed.

The projection is total and mechanical:

  • every operation becomes exactly one tool, keyed by the id it is served
    under (`x-id` where the projection had to rename, `operationId` otherwise);
  • OPTIONS and TRACE never do — CORS preflight and request echo are transport
    machinery, not something an agent calls;
  • `inputSchema` is the operation's parameters and request body as one flat
    JSON Schema object, component `$ref`s carried along into `$defs` — the same
    shape the live door serves, so a tool generated here and a tool listed
    there are callable the same way.

WHICH operations a given deployment will actually answer for is not a fact
about the document — it is a fact about what that deployment mounts and what
the caller's key reaches. The door answers that at runtime. This file answers
the other question, the only one a static artifact can: what the contract says
exists. Filtering here would bake one deployment's answer into every client.

Determinism is a hard requirement (`--check` rests on it): sorted tools, sorted
keys, fixed separators, trailing newline, and no clock, host or random value
ever enters the file.
"""
import argparse
import json
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))
DOCUMENT = os.path.join(ROOT, "hanzo.yaml")
OUT = os.path.join(ROOT, "dist", "tools.json")

SCHEMA_ID = "hanzo.mcp-tools/v1"

# The verbs an agent can be told to call. OPTIONS/TRACE are transport
# machinery and are never tools; the live door omits them too.
VERBS = ("get", "post", "put", "patch", "delete")

REFS = "#/components/schemas/"


def wire(op: dict):
    """The name a caller can actually use — the id hanzo-inc/cloud emitted.

    `publish.py` rule 6 suffixes an operationId when two of them collide under
    the identity a GENERATOR uses (punctuation stripped, case folded), so that
    Go does not declare one request type twice. That suffix is a fact about
    codegen: `DELETE /v1/o11y/sessions` is `DeleteSession_2` in the published
    document and `DeleteSession` on the wire, and the door answers to exactly
    one of those. Publishing the other named a tool in three client
    distributions that nothing can be told to run. Where the projection had to
    change the name it records the original as `x-id`, so this is the whole
    rule: `x-id` when it is there, `operationId` when it is not.
    """
    return op.get("x-id") or op.get("operationId")


def prose(op: dict) -> str:
    """The tool's description: the operation's summary, then its longer prose.

    Both, when both exist — a summary alone is often a single clause, and the
    description carries the conditions an agent needs to choose correctly."""
    head = (op.get("summary") or "").strip()
    body = (op.get("description") or "").strip()
    if head and body and not body.startswith(head):
        return f"{head}\n\n{body}"
    return body or head


def deref(doc: dict, ref: str):
    """Resolve one local `#/...` pointer against the document. None when off-doc."""
    if not isinstance(ref, str) or not ref.startswith("#/"):
        return None
    node = doc
    for part in ref[2:].split("/"):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def rewrite(node, need: set):
    """Copy a schema, repointing component `$ref`s at `$defs` and recording which.

    The catalogue is one self-contained object per tool, so a pointer into
    `#/components/schemas` — which exists only in the document — has to become a
    pointer into the tool's own `$defs`. `need` collects the names so the caller
    can carry them, transitively, without walking the tree a second time."""
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith(REFS):
            name = ref[len(REFS):]
            need.add(name)
            rest = {k: rewrite(v, need) for k, v in node.items() if k != "$ref"}
            return {"$ref": f"#/$defs/{name}", **rest}
        return {k: rewrite(v, need) for k, v in node.items()}
    if isinstance(node, list):
        return [rewrite(v, need) for v in node]
    return node


def defs(doc: dict, need: set) -> dict:
    """Every component schema the tool reaches, transitively, keyed by bare name."""
    out, seen = {}, set()
    queue = sorted(need)
    while queue:
        name = queue.pop(0)
        if name in seen:
            continue
        seen.add(name)
        target = deref(doc, REFS + name)
        if target is None:
            continue
        more = set()
        out[name] = rewrite(target, more)
        queue.extend(sorted(more - seen))
    return out


def schema(doc: dict, path: dict, op: dict) -> dict:
    """One flat JSON Schema object: parameters and request body together.

    Path, query and header parameters become top-level properties; the request
    body's own properties are folded in beside them, because a tool call is one
    flat argument object and an agent has no other way to say "this one goes in
    the URL". A body that is not an object (an array, a scalar) cannot be folded
    and is carried under `body`, which is the only name that could collide and
    the only case where anything is invented at all."""
    props, required, need = {}, [], set()

    for p in (path.get("parameters") or []) + (op.get("parameters") or []):
        if isinstance(p, dict) and "$ref" in p:
            p = deref(doc, p["$ref"]) or {}
        if not isinstance(p, dict) or p.get("in") == "cookie":
            continue
        name = p.get("name")
        if not name:
            continue
        sub = rewrite(p.get("schema") or {"type": "string"}, need)
        if p.get("description"):
            sub = {**sub, "description": p["description"]}
        props[name] = sub
        if p.get("required"):
            required.append(name)

    content = ((op.get("requestBody") or {}).get("content") or {})
    media = content.get("application/json") or next(iter(content.values()), None)
    if isinstance(media, dict):
        body = media.get("schema") or {}
        if isinstance(body, dict) and "$ref" in body:
            resolved = deref(doc, body["$ref"])
            if resolved is not None:
                # Fold the named body's own properties in, but keep whatever it
                # refers to reachable — the $defs walk below sees `need`.
                body = resolved
        body = rewrite(body, need) if isinstance(body, dict) else {}
        if body.get("type") == "object" or "properties" in body:
            for k, v in (body.get("properties") or {}).items():
                props.setdefault(k, v)
            for k in (body.get("required") or []):
                if k not in required:
                    required.append(k)
        elif body:
            props.setdefault("body", body)

    out = {"type": "object", "properties": props}
    if required:
        out["required"] = sorted(required)
    reach = defs(doc, need)
    if reach:
        out["$defs"] = reach
    return out


def catalogue(document: str = DOCUMENT) -> list:
    """Every operation in the document, as one sorted list of MCP tools."""
    doc = yaml.safe_load(open(document)) or {}
    out, seen = [], {}
    for path, item in sorted((doc.get("paths") or {}).items()):
        if not isinstance(item, dict):
            continue
        for method in VERBS:
            op = item.get(method)
            if not isinstance(op, dict):
                continue
            name = wire(op)
            if not name:
                # A tool has no name to be called by. Nothing to emit, and
                # nothing to invent — the document is where that is fixed.
                continue
            if name in seen:
                raise SystemExit(
                    f"tools: operationId {name!r} is claimed twice — "
                    f"{seen[name]} and {method.upper()} {path}. A tool name is an "
                    f"operation id, so two operations with one id are two tools "
                    f"with one name and the second is unreachable.")
            seen[name] = f"{method.upper()} {path}"
            out.append({
                "name": name,
                "description": prose(op),
                "inputSchema": schema(doc, item, op),
            })
    out.sort(key=lambda t: t["name"])
    return out


def render(tools: list) -> str:
    """The catalogue as the exact bytes that get written. Deterministic."""
    return json.dumps(
        {"schema": SCHEMA_ID, "count": len(tools), "tools": tools},
        sort_keys=True, indent=1, separators=(",", ": "),
    ) + "\n"


def generate(out: str = OUT, document: str = DOCUMENT) -> int:
    tools = catalogue(document)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as fh:
        fh.write(render(tools))
    return len(tools)


def main():
    ap = argparse.ArgumentParser(description="Generate the MCP tool catalogue.")
    ap.add_argument("--out", default=OUT, help=f"output file (default: {OUT})")
    ap.add_argument("--document", default=DOCUMENT, help="source document")
    ap.add_argument("--check", action="store_true",
                    help="drift gate: regenerate and diff against --out")
    ap.add_argument("--stat", action="store_true", help="counts only, write nothing")
    args = ap.parse_args()

    if args.stat:
        tools = catalogue(args.document)
        print(f"{len(tools)} tools from {os.path.basename(args.document)}")
        return 0

    if args.check:
        if not os.path.isfile(args.out):
            sys.exit(f"tools --check: {args.out} does not exist (run tools.py first)")
        want = render(catalogue(args.document))
        got = open(args.out).read()
        if want != got:
            print(f"tools --check: DRIFT — regenerate with `python3 tools.py`\n"
                  f"  {args.out}: {len(got)} bytes on disk, {len(want)} bytes fresh",
                  file=sys.stderr)
            sys.exit(1)
        print(f"tools --check: OK — {args.out} matches a fresh generation")
        return 0

    n = generate(args.out, args.document)
    print(f"generated {n} tools → {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
