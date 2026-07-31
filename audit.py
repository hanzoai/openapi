#!/usr/bin/env python3
"""Measure a GENERATED spec against the hand-written contract it wants to replace.

    python3 audit.py                      # report every service that emits a spec
    python3 audit.py iam                  # one service
    python3 audit.py --check              # the gate: fail on a DERIVED regression
    python3 audit.py --json               # machine-readable, for CI annotations

Why this exists, and why it runs BEFORE anything is overwritten:

A spec generated from a service's routes is honest — it cannot describe a route
the service does not serve, which is the failure the hand-written files have.
But it is only as complete as the TYPED surface: zip projects `zip.Get[In,Out]`
and nothing else, so an untyped `app.Get(path, fn)` and an adapted net/http
subtree contribute zero operations. Swapping a complete hand-written spec for an
incomplete generated one is a regression no test notices and a customer finds.

So the generated spec does not replace anything until it measurably covers what
it replaces. This script is that measurement, and `derived:` in
capabilities.yaml is the ratchet: a service moves into that list only once the
audit is clean, and from then on `--check` fails the build if it ever stops
being clean. Report-only for everything else — an unpromoted service is
information, not a broken build.

Inputs, by convention rather than configuration:

  <name>/openapi.yaml           the published contract (hand-written today).
  <name>.yaml                   …or, for the MASTER, a single file at the root:
                                hanzo.yaml is a contract too, and the
                                whole-binary spec would otherwise have nothing
                                to measure against.
  generated/<name>.json|.yaml   what the service emits from its own routes —
                                zip's App.OpenAPISpec() folded over the live
                                router.

There is no `generated/hanzo.json` any more, and its absence is the point.
hanzoai/cloud's emission is no longer something this repo measures the master
against — `sync.py` copies it in as `cloud/openapi.yaml` and `merge.py` merges it,
winning every route it and a hand-written spec both claim. What the audit used to
report for the whole binary is now true by construction: the master cannot
declare a cloud route the binary does not serve, and cannot miss one it does.

A service with no file under generated/ is not audited: it has not joined the
pipeline yet, and saying so once is more useful than failing.
"""
import argparse
import json
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))
GENERATED = os.path.join(ROOT, "generated")
CAPABILITIES = os.path.join(ROOT, "capabilities.yaml")

METHODS = ("get", "put", "post", "delete", "patch", "head", "options", "trace")

# A templated segment is a parameter, whatever it is spelled. /v1/iam/users/{id}
# and /v1/iam/users/{name} are the same route, and a spec that renames a
# parameter has not changed the surface — it has changed a label. Comparing on
# the shape keeps a rename out of the coverage numbers, and the spellings are
# reported separately, where a human can judge them.
TEMPLATE = re.compile(r"\{[^}]*\}")


def shape(path):
    """The route's identity: literal segments, with every parameter erased."""
    return TEMPLATE.sub("{}", path)


def load_spec(path):
    with open(path) as f:
        if path.endswith(".json"):
            return json.load(f)
        return yaml.safe_load(f)


def operations(spec, prefix=""):
    """Every operation in spec, keyed by (route shape, METHOD).

    prefix is prepended to each path, for an app whose routes are registered
    relative to a mount point rather than absolutely.
    """
    ops = {}
    for path, item in (spec.get("paths") or {}).items():
        if not isinstance(item, dict):
            continue
        full = prefix + path
        for method, op in item.items():
            if method.lower() not in METHODS or not isinstance(op, dict):
                continue
            ops[(shape(full), method.upper())] = {"path": full, "op": op}
    return ops


def prose(op):
    """Which documentation an operation actually carries.

    Presence, not quality: a generated spec is allowed to word a description
    differently, but it is not allowed to drop one the contract had.
    """
    have = set()
    if (op.get("description") or "").strip():
        have.add("description")
    if (op.get("summary") or "").strip():
        have.add("summary")
    if _example(op.get("requestBody")):
        have.add("request-example")
    for status, resp in (op.get("responses") or {}).items():
        if str(status).startswith("2") and _example(resp):
            have.add("response-example")
            break
    return have


def _example(node):
    """True when a requestBody/response carries an example a reader can copy."""
    if not isinstance(node, dict):
        return False
    for media in (node.get("content") or {}).values():
        if not isinstance(media, dict):
            continue
        if media.get("example") is not None or media.get("examples"):
            return True
        schema = media.get("schema")
        if isinstance(schema, dict) and schema.get("example") is not None:
            return True
    return False


def audit(service, hand_path, gen_path, prefix=""):
    """Compare one service's generated spec against its hand-written contract."""
    hand = operations(load_spec(hand_path))
    gen = operations(load_spec(gen_path), prefix)

    shared = sorted(set(hand) & set(gen))
    missing = sorted(set(hand) - set(gen))
    extra = sorted(set(gen) - set(hand))

    # Prose the contract has and the generated spec does not: the second way a
    # replacement regresses, and the quieter one — the route still exists, the
    # reference page just goes blank.
    lost = {}
    renamed = []
    for key in shared:
        gone = prose(hand[key]["op"]) - prose(gen[key]["op"])
        if gone:
            lost[key] = sorted(gone)
        if hand[key]["path"] != gen[key]["path"]:
            renamed.append((hand[key]["path"], gen[key]["path"], key[1]))

    return {
        "service": service,
        "hand_ops": len(hand),
        "generated_ops": len(gen),
        "covered": len(shared),
        "missing": [f"{m} {hand[k]['path']}" for k, m in ((k, k[1]) for k in missing)],
        "extra": [f"{m} {gen[k]['path']}" for k, m in ((k, k[1]) for k in extra)],
        "lost_prose": {f"{k[1]} {hand[k]['path']}": v for k, v in sorted(lost.items())},
        "renamed_params": [
            {"contract": h, "generated": g, "method": m} for h, g, m in renamed
        ],
        "complete": not missing and not lost,
    }


def registry():
    """The ONE registry, read for the two lists this script needs.

    `derived` names the services whose spec is generated and gated. `internal`
    is excluded here for the same reason merge.py excludes it: it is not part of
    the published surface, so its coverage is nobody's contract.
    """
    cap = yaml.safe_load(open(CAPABILITIES))
    return set(cap.get("derived") or []), set(cap.get("internal") or [])


def contract(name):
    """The published spec a generated one is measured against, or None.

    Two shapes, one meaning: a per-service contract lives in its own directory,
    the master is a single file at the root. Looking for both here is what lets
    the whole-binary spec be audited against hanzo.yaml with no second script.
    """
    for path in (os.path.join(ROOT, name, "openapi.yaml"), os.path.join(ROOT, name + ".yaml")):
        if os.path.isfile(path):
            return path
    return None


def generated_specs():
    """Every service that emits a spec, by name → path."""
    if not os.path.isdir(GENERATED):
        return {}
    found = {}
    for name in sorted(os.listdir(GENERATED)):
        base, ext = os.path.splitext(name)
        if ext in (".json", ".yaml", ".yml"):
            found[base] = os.path.join(GENERATED, name)
    return found


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("services", nargs="*", help="services to audit (default: all that emit)")
    ap.add_argument("--check", action="store_true",
                    help="exit non-zero if a service listed `derived:` has regressed")
    ap.add_argument("--json", action="store_true", help="emit the report as JSON")
    ap.add_argument("--prefix", default="",
                    help="prepend to every generated path (for an app mounted below its public root)")
    args = ap.parse_args()

    derived, internal = registry()
    emitting = generated_specs()
    wanted = args.services or sorted(emitting)

    reports, gaps = [], []
    for svc in wanted:
        hand_path = contract(svc)
        if svc not in emitting:
            gaps.append(f"{svc}: no generated/{svc}.json — the service does not emit a spec yet")
            continue
        if hand_path is None:
            gaps.append(f"{svc}: generated, but no {svc}/openapi.yaml or {svc}.yaml to measure against")
            continue
        if svc in internal:
            gaps.append(f"{svc}: internal — excluded from the published surface")
            continue
        r = audit(svc, hand_path, emitting[svc], args.prefix)
        r["derived"] = svc in derived
        reports.append(r)

    if args.json:
        json.dump({"reports": reports, "skipped": gaps}, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        render(reports, gaps, derived)

    if not args.check:
        return 0
    # The ratchet: only a promoted service can fail the build. Everything else
    # is a measurement of work still to do, and work still to do is not a
    # broken build.
    regressed = [r for r in reports if r["derived"] and not r["complete"]]
    for r in regressed:
        print(f"\nFAIL {r['service']}: the generated spec no longer covers its contract",
              file=sys.stderr)
        for m in r["missing"]:
            print(f"  missing: {m}", file=sys.stderr)
        for op, what in r["lost_prose"].items():
            print(f"  lost {','.join(what)}: {op}", file=sys.stderr)
    return 1 if regressed else 0


def render(reports, gaps, derived):
    if reports:
        print(f"{'service':<14}{'contract':>9}{'served':>8}{'covered':>9}"
              f"{'missing':>9}{'undeclared':>12}{'prose lost':>12}  state")
        print("-" * 87)
    for r in reports:
        state = "DERIVED" if r["derived"] else ("ready" if r["complete"] else "report-only")
        print(f"{r['service']:<14}{r['hand_ops']:>9}{r['generated_ops']:>8}{r['covered']:>9}"
              f"{len(r['missing']):>9}{len(r['extra']):>12}{len(r['lost_prose']):>12}  {state}")

    for r in reports:
        if r["complete"] and not r["extra"]:
            continue
        print(f"\n{r['service']}")
        if r["missing"]:
            print(f"  the contract declares {len(r['missing'])} operations the routes do not serve"
                  " — untyped, unmounted, or never built:")
            for m in r["missing"][:10]:
                print(f"    - {m}")
            if len(r["missing"]) > 10:
                print(f"    … {len(r['missing']) - 10} more")
        if r["extra"]:
            print(f"  the routes serve {len(r['extra'])} operations the contract never declared"
                  " — invisible to every SDK generated from it:")
            for e in r["extra"][:10]:
                print(f"    + {e}")
            if len(r["extra"]) > 10:
                print(f"    … {len(r['extra']) - 10} more")
        if r["lost_prose"]:
            print(f"  {len(r['lost_prose'])} operations would lose documentation:")
            for op, what in list(r["lost_prose"].items())[:10]:
                print(f"    ~ {op}: {', '.join(what)}")
            if len(r["lost_prose"]) > 10:
                print(f"    … {len(r['lost_prose']) - 10} more")
        if r["renamed_params"]:
            print(f"  {len(r['renamed_params'])} routes differ only in parameter name:")
            for n in r["renamed_params"][:5]:
                print(f"    ? {n['method']} {n['contract']} → {n['generated']}")

    for g in gaps:
        print(f"skip  {g}")

    if reports:
        ready = [r["service"] for r in reports if r["complete"] and not r["derived"]]
        if ready:
            print(f"\nready to promote (add to `derived:` in capabilities.yaml): {', '.join(ready)}")
        else:
            print("\nnothing is ready to promote — no hand-written spec is replaced yet")


if __name__ == "__main__":
    sys.exit(main())
