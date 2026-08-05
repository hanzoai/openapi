#!/usr/bin/env python3
"""Project the Hanzo Cloud API document into every language SDK.

    python3 generate.py --all              # regenerate every client in place
    python3 generate.py python typescript  # just these
    python3 generate.py --all --check      # fail if a committed client drifted
    python3 generate.py python --repo DIR  # the SDK repo is somewhere else

THE DOCUMENT COMES FROM THE CODE, AND NOT FROM ANYONE'S OPINION.

hanzoai/cloud emits `openapi.yaml` by projecting its own routers, and gates the
emission by regenerating from source and failing on any diff — so it cannot
describe a route the binary does not serve and cannot miss one it does. That is
the only description of this API with that property, and a client generated from
anything else describes a release nobody shipped.

`hanzo.yaml` used to be that anything else: a HAND-MERGED union of 52 authored
specs with cloud's document laid on top, carrying 185 operations cloud does not
serve, every one of which reached four SDKs as a method that 404s. It is not any
more. `publish.py` DERIVES it from cloud's emission at one pinned ref, and
`--check` regenerates and diffs, so it cannot contain an operation cloud does not
serve. Existence comes from the code either way; the file is a projection now,
not a second opinion.

WHY A PROJECTION AND NOT THE EMISSION ITSELF — measured, because the obvious
answer is wrong. Generating from cloud's raw document produces NOTHING in every
language:

    openapi-generator-cli 7.14.0 validate -i <cloud openapi.yaml>
      → [error] Spec has 1012 errors     (one per route the weave publishes
                                          with an address and no `responses`)
    …           generate -g typescript-axios -i <same>
      → SpecValidationException: There were issues with the specification
      → 0 files written

`hanzo.yaml` is the same document with the six codegen rules in `publish.py`
applied — 0 errors, and typescript-axios writes `api.ts`. Pointing a client at
the emission directly is correct about authority and produces no client, which
is the wrong trade for a repo whose whole output is clients. The rules are all
candidates to move UPSTREAM into cloud's emitter; the day they do, this default
becomes cloud's document itself and `publish.py` goes.

WHICH document is still a fact about the CLIENT when the client says so. An SDK
repo's `.spec-lock` names the ref and sha256 it is a projection of — written by
hanzoai/ci's `client:` lane when a release dispatched to it — and `document()`
reads it; `--spec` is the same document passed by value when the caller already
fetched it (which the lane always does). With neither, this checkout's own
`hanzo.yaml` is the document, which is what a maintainer regenerating by hand
gets.

This file and sdks.yaml stay: the INVOCATION is still logic that lives once, and
every per-language knob is still data beside it. An SDK repo carries only a call
site, so nothing in a client repo can drift on its own — `--check` is what makes
that a fact rather than a convention.
"""
import argparse
import concurrent.futures as futures
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.request
from fnmatch import fnmatch

import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.dirname(ROOT)  # sibling checkouts: ~/work/hanzo/<repo>
CACHE = os.path.expanduser("~/.cache/openapi-generator")
MAVEN = "https://repo1.maven.org/maven2/org/openapitools/openapi-generator-cli"


def jar(version):
    """The pinned generator, fetched once. A version is a version everywhere.

    Every language downloads into its OWN temp file, because `main` maps the
    languages over a thread pool and a cold cache therefore calls this once per
    language at the same moment. A shared `<jar>.part` made those writes one
    file: both threads opened it, both wrote the same 30 MB into it, the first
    to finish renamed it away, and the second's `os.replace` died with
    FileNotFoundError on a path it had just written. Measured on `generate.py
    java kotlin` — java emitted 2274 files and kotlin never ran. The failure
    needs an empty cache, so it misses every re-run and lands on CI and on the
    first clone, which is where it costs the most.

    `os.replace` is atomic on POSIX and on Windows, so the losers of the race
    simply overwrite an identical file with an identical file.
    """
    path = os.path.join(CACHE, f"openapi-generator-cli-{version}.jar")
    if not os.path.exists(path):
        os.makedirs(CACHE, exist_ok=True)
        url = f"{MAVEN}/{version}/openapi-generator-cli-{version}.jar"
        print(f"fetching {url}", flush=True)
        fd, part = tempfile.mkstemp(dir=CACHE, prefix=f"{version}.", suffix=".part")
        try:
            with urllib.request.urlopen(url) as r, os.fdopen(fd, "wb") as f:
                shutil.copyfileobj(r, f)
            os.replace(part, path)
        except BaseException:
            if os.path.exists(part):
                os.unlink(part)
            raise
    return path


# Written INTO a client tree by the language runtime, never by the generator, so
# they are not evidence of drift. Importing the Python client once is enough to
# make --check report 2142 phantom deletions, and a check that cries wolf is one
# nobody runs. Every one of these is already gitignored in its repo.
ARTIFACTS = ("__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache", "node_modules")


def as_json(path):
    """The document as JSON, because YAML has a ceiling and JSON does not.

    swagger-parser hands a YAML document to snakeyaml, which refuses anything
    over 3 * 1024 * 1024 = 3145728 code points. The document passed that mark
    long ago (cloud@v1.801.383 is 3,568,239 bytes) and the failure does not say
    so: the parser logs SnakeException, silently falls through to the SWAGGER
    2.0 compat reader, and dies with "Issues with the OpenAPI input", which
    reads like a malformed spec. It is not — the document validates at 0 errors.

    `-DmaxYamlCodePoints` lifts the cap, and it is NOT the fix: the property is
    honoured by the swagger-parser in generator 7.24.0 and IGNORED by the one in
    7.14.0, which is the version this file pins. Feeding JSON instead avoids
    snakeyaml altogether — measured, not assumed: a JSON 539 KB OVER the ceiling
    validates clean on 7.14.0. The generator reads either format from -i, so
    this costs one temp file and removes a ceiling the document will keep
    growing into.

    Deliberately not written back to disk as a second committed artifact. There
    is one document, it lives in hanzoai/cloud, and every copy of it anywhere
    else is a copy that can be stale.
    """
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     dir=os.environ.get("TMPDIR")) as f:
        json.dump(yaml.safe_load(open(path)), f)
        return f.name


def lock(repo):
    """`.spec-lock` as a dict — the client's own statement of which document it is.

    hanzoai/ci's `client:` lane writes it (ref, sha256, repo, path) the moment a
    cloud release regenerates this tree, and re-verifies the digest on every
    later push. So it is a receipt, not configuration: nobody edits it to choose
    a document, a release moves it.
    """
    path = os.path.join(repo, ".spec-lock")
    if not os.path.exists(path):
        return None
    out = {}
    for line in open(path):
        k, _, v = line.strip().partition("=")
        if k:
            out[k] = v
    return out


def fetch(spec, dest):
    """The document at the locked ref, from GitHub, digest-checked.

    hanzoai/cloud is private, so raw.githubusercontent.com answers 404 rather
    than 403 and an anonymous miss is indistinguishable from a deleted file. The
    contents API with a token says which case it is. Same credential names every
    SDK call site already takes.
    """
    token = (os.environ.get("SPEC_TOKEN") or os.environ.get("GH_TOKEN")
             or os.environ.get("GITHUB_TOKEN")
             or subprocess.run(["gh", "auth", "token"], capture_output=True,
                               text=True).stdout.strip())
    if not token:
        sys.exit(f"generate: {spec['repo']} is private and no SPEC_TOKEN / GH_TOKEN /"
                 f" GITHUB_TOKEN is set (nor `gh auth login`). Pass --spec instead.")
    req = urllib.request.Request(
        f"https://api.github.com/repos/{spec['repo']}/contents/{spec['path']}"
        f"?ref={spec['ref']}",
        headers={"Authorization": f"Bearer {token}",
                 "Accept": "application/vnd.github.raw"})
    with urllib.request.urlopen(req) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f)
    got = hashlib.sha256(open(dest, "rb").read()).hexdigest()
    # A pinned ref whose bytes moved means someone moved a tag, and no amount of
    # regenerating makes that safe. The same refusal hanzoai/ci makes, for the
    # same reason, so a hand run and a CI run cannot disagree about what they read.
    want = spec.get("sha256")
    if want and got != want:
        sys.exit(f"generate: {spec['repo']}@{spec['ref']}:{spec['path']} hashes to "
                 f"{got}, but .spec-lock says {want} — the ref moved under this "
                 f"projection")
    return dest


ONE_DOCUMENT = threading.Lock()


def document(repo, given, cache):
    """THE document this client is a projection of, as a path to JSON.

    Three sources, one order, and the last one is safe now in a way it was not
    before. `given` is `--spec`: the document by value, already fetched and
    digest-checked by hanzoai/ci's lane. Otherwise the client's own `.spec-lock`
    names it, which is how a release pins every language to one digest. With
    neither, this checkout's `hanzo.yaml` — which `publish.py` derives from
    cloud's emission and `publish.py --check` regenerates and diffs, so it can no
    longer be the hand-merged second authority whose 185 unserved operations put
    a 404 behind a type signature in four clients.

    Cached per distinct document rather than per language: `--all` projects ONE
    release into every client, which is G2 (one release, one document) and not
    an optimisation.
    """
    if given:
        key, spec = ("given", os.path.abspath(given)), given
    else:
        spec = lock(repo)
        if not spec or not spec.get("ref"):
            here = os.path.join(ROOT, "hanzo.yaml")
            if not os.path.exists(here):
                sys.exit("generate: no --spec, no .spec-lock, and no hanzo.yaml — "
                         "run `python3 publish.py` first")
            key, spec = ("given", here), here
            given = here
        else:
            key = (spec["repo"], spec["path"], spec["ref"])
    with ONE_DOCUMENT:
        if key not in cache:
            if not given:
                print(f"document: {spec['repo']}@{spec['ref']}:{spec['path']}", flush=True)
                spec = fetch(spec, tempfile.NamedTemporaryFile(
                    suffix=".yaml", delete=False,
                    dir=os.environ.get("TMPDIR")).name)
            cache[key] = as_json(spec)
        return cache[key]


def digest(path):
    """Content of a tree as {relpath: sha256}; a file is a one-entry tree."""
    if os.path.isfile(path):
        return {"": hashlib.sha256(open(path, "rb").read()).hexdigest()}
    out = {}
    for base, dirs, names in os.walk(path):
        dirs[:] = [d for d in dirs if d not in ARTIFACTS]
        for n in names:
            p = os.path.join(base, n)
            out[os.path.relpath(p, path)] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    return out


def diff(src, dst):
    """(added, removed, changed) going from the committed dst to a fresh src."""
    a, b = digest(src), digest(dst) if os.path.exists(dst) else {}
    return (
        sorted(set(a) - set(b)),
        sorted(set(b) - set(a)),
        sorted(k for k in set(a) & set(b) if a[k] != b[k]),
    )


def prune(stage, drops):
    """Delete the staged files that belong to the repo rather than the client."""
    for base, dirs, names in os.walk(stage, topdown=False):
        for n in dirs + names:
            p = os.path.join(base, n)
            rel = os.path.relpath(p, stage)
            if any(fnmatch(rel, d) or fnmatch(n, d) for d in drops):
                shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)


def emit(name, cfg, spec, version, out):
    """Run the generator for one language into a staging dir."""
    props = ",".join(f"{k}={v}" for k, v in cfg.get("properties", {}).items())
    # Docs and stub tests are ~4000 files of nothing at this spec size. A row
    # may add its own global properties; they are per-language for the same
    # reason `properties` is — changing one here would churn every other
    # client's committed output.
    glob = ["apis", "models", "supportingFiles",
            "apiDocs=false", "modelDocs=false", "apiTests=false", "modelTests=false"]
    glob += [f"{k}={v}" for k, v in cfg.get("global", {}).items()]
    cmd = [
        "java", "-Xmx2g", "-jar", jar(version), "generate",
        "-g", cfg["generator"],
        "-i", spec,
        "-o", out,
        "--global-property", ",".join(glob),
        # The document is OpenAPI 3.1, and 3.1 made `responses` OPTIONAL on an
        # operation. The validator in generator 7.14.0 still enforces the 3.0
        # rule that it is required, so it refuses a document that is valid —
        # measured on hanzoai/cloud's openapi.yaml, where 684 of 1636 operations
        # are routes the router proves exist and whose response shape no seam can
        # state. cloud emits those with no `responses` key ON PURPOSE
        # (openapi/openapi.go: "absent stays valid and absent beats invented"),
        # and it is right; a client generator that rejects it is applying the
        # wrong version's rule.
        #
        # This is document-level, not per-language, so it is here and not a
        # sdks.yaml `flags` row — every projection reads the same document and
        # would need the same correction.
        #
        # Validation is not what keeps a bad document out. COMPILING THE CLIENT
        # is: every SDK repo's hanzo.yml `test:` block builds the generated tree
        # and then builds the six example flows against it, in the language's own
        # compiler. That catches a malformed document as a build failure with a
        # file and a line, which is strictly more than "Issues with the OpenAPI
        # input" ever told anyone.
        "--skip-validate-spec",
    ]
    if props:
        cmd += ["--additional-properties", props]
    # An escape hatch for where the generator itself is wrong: generator CLI
    # options that have no --additional-properties form, as data in sdks.yaml.
    # They do not describe the API — they say how one language's generator has
    # to be corrected to emit code that compiles.
    for flag, value in cfg.get("flags", {}).items():
        cmd += [f"--{flag}", str(value)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.stderr.write(f"[{name}] generator failed\n{r.stdout[-4000:]}{r.stderr[-4000:]}\n")
    return r.returncode == 0


def sdk(name, cfg, spec, version, drops, repo, check):
    with tempfile.TemporaryDirectory(prefix=f"sdkgen-{name}-", dir=os.environ.get("TMPDIR")) as stage:
        if not emit(name, cfg, spec, version, stage):
            return False
        prune(stage, drops)
        ok = True
        for src_rel, dst_rel in cfg["take"].items():
            src, dst = os.path.join(stage, src_rel), os.path.join(repo, dst_rel)
            if not os.path.exists(src):
                sys.stderr.write(f"[{name}] generator emitted no {src_rel}\n")
                return False
            added, removed, changed = diff(src, dst)
            if check:
                if added or removed or changed:
                    ok = False
                    print(f"[{name}] {dst_rel} DRIFTED: "
                          f"+{len(added)} -{len(removed)} ~{len(changed)}")
                    for k in (added[:5] + removed[:5] + changed[:5]):
                        print(f"          {k}")
                continue
            if os.path.isdir(src):
                shutil.rmtree(dst, ignore_errors=True)
                shutil.copytree(src, dst)
            else:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
            print(f"[{name}] {dst_rel}: +{len(added)} -{len(removed)} ~{len(changed)}")
        if check and ok:
            print(f"[{name}] clean")
        return ok


def main():
    conf = yaml.safe_load(open(os.path.join(ROOT, "sdks.yaml")))
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("langs", nargs="*", choices=sorted(conf["sdks"]) + [[]], help="languages; default --all")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--check", action="store_true", help="diff only; non-zero if a client drifted")
    ap.add_argument("--repo", help="SDK repo path (single language only)")
    # THE DOCUMENT IS AN ARGUMENT, not a fact about this checkout. hanzoai/cloud's
    # release hands each client repo openapi.yaml AT THE SHA IT DEPLOYED, and a
    # projection generated from anything else describes a release nobody shipped.
    # Omitted, the client's OWN `.spec-lock` names the same document — see
    # `document()`. There is no fallback to a file in this repo: that fallback was
    # `hanzo.yaml`, a hand-merged second authority, and every operation it carried
    # that cloud does not serve reached an SDK as a method that 404s.
    ap.add_argument("--spec", help="the API document to project; default: the ref this client's .spec-lock names")
    # java -Xmx2g per worker, and this box has been OOMed by less.
    ap.add_argument("-j", type=int, default=2, help="parallel generators")
    a = ap.parse_args()

    langs = sorted(conf["sdks"]) if (a.all or not a.langs) else a.langs
    if a.repo and len(langs) != 1:
        ap.error("--repo takes exactly one language")
    docs, version = {}, str(conf["generator"])

    def one(name):
        cfg = conf["sdks"][name]
        repo = a.repo or os.path.join(WORK, cfg["repo"])
        if not os.path.isdir(repo):
            sys.stderr.write(f"[{name}] no checkout at {repo}\n")
            return False
        return sdk(name, cfg, document(repo, a.spec, docs), version,
                   conf["drop"], repo, a.check)

    with futures.ThreadPoolExecutor(max_workers=a.j) as pool:
        results = list(pool.map(one, langs))
    if not all(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
