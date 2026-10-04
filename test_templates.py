#!/usr/bin/env python3
"""The python row's template overrides, proved on a client generated through them.

Runnable standalone (`python3 test_templates.py`) and under pytest. It needs java
and fetches the pinned generator like generate.py does; with no java it FAILS,
because a template test that skips is a gate that is green over nothing.

templates/python corrects two things the generator emits.

  • Its oneOf and anyOf wrappers gain a model validator that reads a raw value the
    way from_json does. Without it, pydantic takes a dict handed to
    model_validate (or to any model holding the wrapper as a field) for the
    wrapper's own fields and leaves actual_instance None, so
    AiDecisionsRequest.model_validate({...}) serialized every question as null.
  • ApiClient writes every header value as text. X-Max-Cost is a number in the
    document, and urllib3 refuses a float header value with a TypeError, so no
    Python caller could bound a routed call.

The fixture is those shapes: a oneOf of three variants told apart by `type`, one
variant whose field is an anyOf, held in a map by a request.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

import yaml

import generate

ROOT = os.path.dirname(os.path.abspath(__file__))

FIXTURE = {
    "openapi": "3.1.0",
    "info": {"title": "templates", "version": "v1"},
    "paths": {"/v1/ask": {"post": {
        "operationId": "post_ask",
        "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Ask"}}}},
        "responses": {"200": {"description": "ok"}},
    }}},
    "components": {"schemas": {
        "Ask": {"type": "object", "required": ["questions"], "properties": {
            "questions": {"type": "object", "additionalProperties": {"$ref": "#/components/schemas/Question"}}}},
        "Question": {
            "oneOf": [{"$ref": "#/components/schemas/Choice"}, {"$ref": "#/components/schemas/Score"},
                      {"$ref": "#/components/schemas/Noul"}],
            "discriminator": {"propertyName": "type", "mapping": {
                "choice": "#/components/schemas/Choice", "score": "#/components/schemas/Score",
                "noul": "#/components/schemas/Noul"}}},
        "Choice": {"type": "object", "required": ["type", "criteria"], "properties": {
            "type": {"type": "string", "enum": ["choice"]},
            "criteria": {"type": "object", "additionalProperties": {"type": "string"}}}},
        "Score": {"type": "object", "required": ["type", "criteria"], "properties": {
            "type": {"type": "string", "enum": ["score"]},
            "criteria": {"type": "array", "items": {"type": "string"}}}},
        "Noul": {"type": "object", "required": ["type"], "properties": {
            "type": {"type": "string", "enum": ["noul"]},
            "level": {"anyOf": [{"type": "string"}, {"type": "integer"}]}}},
    }},
}

PROBE = r'''
import json
from client.models import Ask, Choice, Noul, Question, Score

raw = {"questions": {
    "c": {"type": "choice", "criteria": {"a": "first", "b": "second"}},
    "s": {"type": "score", "criteria": ["low", "high"]},
    "n": {"type": "noul", "level": 3},
}}
kinds = lambda a: {k: type(q.actual_instance).__name__ for k, q in a.questions.items()}
want = {"c": "Choice", "s": "Score", "n": "Noul"}

for how, ask in [("model_validate", Ask.model_validate(raw)), ("from_dict", Ask.from_dict(raw))]:
    assert kinds(ask) == want, (how, kinds(ask))
    assert json.loads(ask.to_json()) == raw, (how, ask.to_json())

typed = Ask(questions={"c": Choice(type="choice", criteria={"a": "first", "b": "second"}),
                       "s": Question(Score(type="score", criteria=["low", "high"])),
                       "n": Noul(type="noul", level=3)})
assert kinds(typed) == want, kinds(typed)
assert json.loads(typed.to_json()) == raw, typed.to_json()
assert Noul.model_validate({"type": "noul", "level": "three"}).level.actual_instance == "three"

from client.api_client import ApiClient
_, _, sent, _, _ = ApiClient().param_serialize(method="POST", resource_path="/v1/ask",
                                               header_params={"X-Max-Cost": 0.01, "X-Max-Latency-Ms": 800, "X-On": True})
assert (sent["X-Max-Cost"], sent["X-Max-Latency-Ms"], sent["X-On"]) == ("0.01", "800", "true"), sent
print("ok")
'''


def test_a_raw_value_resolves_the_union():
    assert shutil.which("java"), "java is required: the templates are proved on a generated client"
    conf = yaml.safe_load(open(os.path.join(ROOT, "sdks.yaml")))
    row = dict(conf["sdks"]["python"], properties={"packageName": "client", "library": "urllib3",
                                                   "generateSourceCodeOnly": "true"})
    assert row.get("templates") == "templates/python"
    with tempfile.TemporaryDirectory() as tmp:
        spec = os.path.join(tmp, "spec.json")
        with open(spec, "w") as f:
            json.dump(FIXTURE, f)
        out = os.path.join(tmp, "out")
        assert generate.emit("python", row, spec, str(conf["generator"]), out)
        r = subprocess.run(["uv", "run", "--no-project", "--python", "3.12", "--with", "pydantic",
                            "--with", "python-dateutil", "--with", "urllib3", "--with", "typing-extensions",
                            "python", "-c", PROBE], cwd=out, capture_output=True, text=True)
        assert r.returncode == 0 and r.stdout.strip() == "ok", r.stdout + r.stderr


if __name__ == "__main__":
    test_a_raw_value_resolves_the_union()
    print("test_templates: ok")
