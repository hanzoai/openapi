#!/usr/bin/env python3
"""Tests for flows.yaml — the manifest that keeps every SDK's examples the same six.

Runnable standalone (`python3 test_flows.py`, non-zero exit on failure) AND under
pytest, like test_audit.py beside it.

The manifest is only worth having if it cannot drift from the spec it names. An
operationId that no longer exists is the exact failure this catches: without it,
deleting a route upstream leaves six SDKs each carrying an example that no longer
compiles, discovered six separate times. Here it is one red test in one repo.
"""
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))

# The set is closed on purpose. A seventh flow is a fleet-wide decision — every
# language owes the same six — so adding one should require editing this line.
CANONICAL = ["hello", "chat", "money", "store", "agent", "tools"]


def load():
    flows = yaml.safe_load(open(os.path.join(ROOT, "flows.yaml")))["flows"]
    spec = yaml.safe_load(open(os.path.join(ROOT, "hanzo.yaml")))
    methods = ("get", "post", "put", "patch", "delete", "head", "options")
    ids = {
        op["operationId"]
        for item in spec["paths"].values()
        for verb, op in item.items()
        if verb in methods and isinstance(op, dict) and op.get("operationId")
    }
    return flows, ids


def test_the_six_are_present_and_only_those():
    flows, _ = load()
    assert list(flows) == CANONICAL, f"flows.yaml lists {list(flows)}, expected {CANONICAL}"


def test_every_operation_exists_in_the_spec():
    flows, ids = load()
    missing = [
        (name, op)
        for name, flow in flows.items()
        for op in flow["operations"]
        if op not in ids
    ]
    assert not missing, "flows.yaml names operations hanzo.yaml does not have: " + repr(missing)


def test_every_flow_says_what_it_does():
    flows, _ = load()
    for name, flow in flows.items():
        assert flow.get("summary"), f"{name} has no summary"
        assert flow.get("operations"), f"{name} names no operations"


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
