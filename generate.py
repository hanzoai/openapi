#!/usr/bin/env python3
"""Project the Hanzo Cloud API document into every language SDK.

    python3 generate.py --all              # regenerate every client in place
    python3 generate.py python typescript  # just these
    python3 generate.py --all --check      # fail if a committed client drifted
    python3 generate.py python --repo DIR  # the SDK repo is somewhere else

THE DOCUMENT COMES FROM THE CODE, AND NOT FROM ANYONE'S OPINION.

hanzo-inc/cloud emits `openapi.yaml` by projecting its own routers, and gates the
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

THE EMISSION ITSELF, NOT A PROJECTION OF IT. Every row reads that document, and
the validator is not a reason to read anything else although it reads like one:

    openapi-generator-cli 7.14.0 validate -i <cloud openapi.yaml>
      → [error] Spec has 1012 errors     (one per route the weave publishes
                                          with an address and no `responses`)

OpenAPI 3.1 made `responses` optional and the 7.14.0 validator still applies the
3.0 rule, so it is refusing a document that is valid. `--skip-validate-spec` is
`emit()`'s, for every language, and compiling the client is what actually gates a
bad document. `hanzo.yaml` — publish.py's projection of the same bytes, with six
codegen rules applied — is the alternative, and sdks.yaml's THE DOCUMENT section
measures what reading it costs: go 46 methods and a header naming a release
counter cloud does not answer to, typescript its credential outright. Those rules
belong UPSTREAM in cloud's emitter; the day they land there, `publish.py` goes.

WHICH document is a fact about the CLIENT. An SDK repo's `.spec-lock` names the
ref and sha256 it is a projection of — written by hanzoai/ci's `client:` lane
when a release dispatched to it — and `document()` reads it; `--spec` is the same
document passed by value when the caller already fetched it (which the lane
always does). With neither, `document()` exits. There is no third source: the
one that stood there was this checkout's `hanzo.yaml`, and reading it made a
client the projection of a projection, one step stale whenever the middle step
had not run, and stale silently.

This file and sdks.yaml stay: the INVOCATION is still logic that lives once, and
every per-language knob is still data beside it. An SDK repo carries only a call
site, so nothing in a client repo can drift on its own — `--check` is what makes
that a fact rather than a convention.

A LANGUAGE IS A ROW, NOT A MECHANISM. Every language this repo generates is one
entry in sdks.yaml and nothing else; adding one is adding data. That held for
four languages and not for Go, which owned a second driver — 196 lines of bash
re-deriving the jar, the lock, the digest check, the YAML-to-JSON conversion and
the drift check — for one reason: `take` meant "the generator owns this
DIRECTORY", and Go's client sits at the module root beside go.mod and .git, so
no directory could be named. `owned()` states the rule as a set of files
instead, which every row can say, so the second driver is gone and Go is a row.
"""
import argparse
import concurrent.futures as futures
import hashlib
import json
import os
import re
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
    is one document, it lives in hanzo-inc/cloud, and every copy of it anywhere
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


# The one address the fleet reads its document from. publish.py already knew it
# under this name; generate.py asked git.hanzo.ai instead, so two files in one
# repo named two sources for one document.
SERVED = os.environ.get("SERVED_DOCUMENT", "https://api.hanzo.ai/v1/openapi.json")


def fetch(spec, dest):
    """The document production is serving, digest-checked against the lock.

    One address, no credential. api.hanzo.ai serves cloud's own emission from
    the process that is actually up, and hanzoai/ci's client lane reads exactly
    this and hands it to the generator as $SPEC — so a hand run and a CI run
    cannot disagree about what they read.

    This asked hanzo-inc/cloud at the locked ref through HANZO_GIT_TOKEN. That
    name no longer exists in the lane (the job carries its org's IAM identity
    now), and it was a private read a contributor could not make at all, so the
    documented way to regenerate by hand ended at a credential nobody could get.

    `.spec-lock` still records WHICH document this tree was generated from. A
    digest that differs means cloud has shipped since — said, not refused, because
    regenerating onto what production serves is the reason this function runs.
    Pass --spec to generate against a document by value instead.
    """
    with urllib.request.urlopen(SERVED, timeout=120) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f)
    got = hashlib.sha256(open(dest, "rb").read()).hexdigest()
    want = spec.get("sha256")
    if want and got != want:
        print(f"generate: {SERVED} hashes to {got}; .spec-lock records {want} — "
              f"cloud has shipped since this projection was generated",
              file=sys.stderr)
    return dest


ONE_DOCUMENT = threading.Lock()


def document(repo, given, cache):
    """THE document this client is a projection of, as a path to JSON.

    TWO sources, one order, and both name a hanzo-inc/cloud release. `given` is
    `--spec`: the document by value, already fetched and digest-checked by
    hanzoai/ci's lane. Otherwise the client's own `.spec-lock` names it, which is
    how a release pins every language to one digest.

    There was a third, this checkout's `hanzo.yaml`, and it had to go: that file
    is a projection of cloud's document with codegen rules applied, so falling
    back to it made a client the projection of a projection — a document one step
    stale whenever the middle step had not run, and stale silently, since nothing
    downstream can tell which of the two it read.

    Cached per distinct document rather than per language: `--all` projects ONE
    release into every client, which is G2 (one release, one document) and not
    an optimisation.
    """
    if given:
        key, spec = ("given", os.path.abspath(given)), given
    else:
        spec = lock(repo)
        if not spec or not spec.get("ref"):
            sys.exit(f"generate: {repo} has no .spec-lock and no --spec was given, "
                     "so this client names no document. hanzoai/ci's client lane "
                     "passes one by value; by hand, pass --spec.")
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


MANIFEST = ".generated"


def owned(repo):
    """Every path this driver last wrote into `repo`, repo-relative, as a set.

    THE GENERATOR OWNS THE FILES IT WROTE — not a directory. That is the whole
    of the ownership rule, and it is one rule because it holds for every row.

    `take` used to mean "the generator owns this DIRECTORY", implemented as
    rmtree-then-copy. Four languages could say that; Go could not, because
    `package hanzoai` sits at the module root beside go.mod, LICENSE, examples/
    and .git — `take: {.: .}` under that rule deletes the repository. So Go grew
    a second driver, 196 lines of bash re-deriving the jar, the lock, the digest
    check, the YAML-to-JSON conversion and the diff, and the two drifted.

    Owning a SET is strictly stronger and has no such edge: a stale file is one
    this manifest names and the fresh emission does not, so it is removed; a file
    nothing here names is the repo's own and is never touched, whatever directory
    it happens to sit in. For a wholly-owned directory the manifest covers
    everything under it, so the four rows behave exactly as they did.

    Written by every write run, read by the next one and by `--check`. Absent, it
    reads as "this driver has written nothing here", which is true of a repo it
    has never touched and makes the first run add-only.
    """
    path = os.path.join(repo, MANIFEST)
    if not os.path.exists(path):
        return set()
    return {line.strip() for line in open(path) if line.strip()}


def place(dst, rel):
    """Where a file `rel` of the staged tree lands, relative to the repo."""
    return os.path.normpath(os.path.join(dst, rel)) if rel else os.path.normpath(dst)


def under(path, dst):
    """Is a repo-relative path inside this take's destination?"""
    dst = os.path.normpath(dst)
    return dst == "." or path == dst or path.startswith(dst + os.sep)


def diff(fresh, here):
    """(added, removed, changed) going from what is committed to what is fresh."""
    return (
        sorted(set(fresh) - set(here)),
        sorted(set(here) - set(fresh)),
        sorted(k for k in set(fresh) & set(here) if fresh[k] != here[k]),
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
        # measured on hanzo-inc/cloud's openapi.yaml, where 684 of 1636 operations
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
    # Overrides for the generator's own mustache, resolved against THIS repo.
    # The generator reads each file from here first and falls back to the ones
    # inside the jar, so a row overrides the templates it corrects and no more.
    #
    # It lives here because the INVOCATION lives here. sdks.yaml used to say a
    # language needing a template must own its whole invocation elsewhere, on
    # the grounds that a template is a file and has to sit beside the call — and
    # that is right, but the call is this function, not the one-line call site
    # in an SDK repo. Templates beside generate.py and their flags beside them
    # in sdks.yaml are ONE home; a template in the client and its flags here
    # would be the two that drift.
    if cfg.get("templates"):
        cmd += ["-t", os.path.join(ROOT, cfg["templates"])]
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


def shape(name, cfg, stage):
    """The language's own formatter over the staged tree, where it has one.

    The generator's Go output is not gofmt'd — 2655 of 2656 files at this
    document's size — and a Go source file that is not gofmt'd reformats itself
    in every contributor's editor, so committing it makes the client drift on
    save. Nothing in `properties` or `flags` reaches this: it is a step AFTER the
    generator, which is why it is its own key and why the shape of the key is a
    command with no shell (a list, so nothing is parsed or expanded).

    Absent for python, typescript, java and kotlin — their committed trees are
    byte-for-byte what the generator emits, measured, so a formatter there would
    only add a tool their CI does not need.
    """
    cmd = cfg.get("format")
    if not cmd:
        return True
    r = subprocess.run([*cmd, stage], capture_output=True, text=True)
    if r.returncode:
        sys.stderr.write(f"[{name}] {cmd[0]} failed\n{r.stderr[-4000:]}\n")
    return r.returncode == 0


def sdk(name, cfg, spec, version, drops, repo, check):
    with tempfile.TemporaryDirectory(prefix=f"sdkgen-{name}-", dir=os.environ.get("TMPDIR")) as stage:
        if not emit(name, cfg, spec, version, stage):
            return False
        if not shape(name, cfg, stage):
            return False
        prune(stage, drops)
        was, now, ok = owned(repo), {}, True
        for src_rel, dst_rel in cfg["take"].items():
            src = os.path.join(stage, src_rel)
            if not os.path.exists(src):
                sys.stderr.write(f"[{name}] generator emitted no {src_rel}\n")
                return False
            fresh = {place(dst_rel, rel): (os.path.join(src, rel) if rel else src, sha)
                     for rel, sha in digest(src).items()}
            now.update(fresh)
            # What the repo holds of what this driver owns HERE. A file the
            # manifest does not name is the repo's own and is not compared.
            here = {p: hashlib.sha256(open(os.path.join(repo, p), "rb").read()).hexdigest()
                    for p in was
                    if under(p, dst_rel) and os.path.isfile(os.path.join(repo, p))}
            added, removed, changed = diff({k: v[1] for k, v in fresh.items()}, here)
            if check:
                if added or removed or changed:
                    ok = False
                    print(f"[{name}] {dst_rel} DRIFTED: "
                          f"+{len(added)} -{len(removed)} ~{len(changed)}")
                    for k in (added[:5] + removed[:5] + changed[:5]):
                        print(f"          {k}")
                continue
            for p in removed:
                os.remove(os.path.join(repo, p))
            for p, (s, _) in fresh.items():
                d = os.path.join(repo, p)
                os.makedirs(os.path.dirname(d), exist_ok=True)
                shutil.copy2(s, d)
            sweep(repo, removed)
            print(f"[{name}] {dst_rel}: +{len(added)} -{len(removed)} ~{len(changed)}")
        if not check:
            with open(os.path.join(repo, MANIFEST), "w") as f:
                f.write("".join(f"{p}\n" for p in sorted(now)))
            stamp(repo, spec)
        if check and ok:
            print(f"[{name}] clean")
        return ok


METHODS = {"get", "put", "post", "delete", "patch", "head", "options", "trace"}


def scale(spec):
    """(operations, paths, services) of the document a client was cut from.

    PARSED, not pattern-matched. The first version counted `^      operationId:`
    and `^  /`, which is true of cloud's YAML and of nothing else — this driver
    hands the generator a JSON copy, so every count came out zero and stamped
    "0 operations over 0 paths" into the README it was added to fix.
    """
    doc = as_json(spec) if str(spec).endswith((".yaml", ".yml")) else spec
    with open(doc, encoding="utf-8") as f:
        d = json.load(f)
    paths = d.get("paths") or {}
    ops = [op for item in paths.values() for m, op in (item or {}).items()
           if m in METHODS and isinstance(op, dict)]
    tags = {t for op in ops for t in (op.get("tags") or [])}
    return len(ops), len(paths), len(tags)


# The counts a README quotes, stamped rather than typed.
#
# Seven READMEs said "2479 operations over 1814 paths, grouped into 192
# services". The document served 2259 over 1620 in 148 — every number wrong, on
# the first paragraph of the page a developer lands on. Nobody mistyped them:
# they were true once and the document moved, which is what a hand-written count
# does. cloud's own notes call this out ("a count quoted in prose is stale the
# next week") and the fix there is the same as here — say how to re-measure it,
# or measure it for them.
#
# The span is delimited so the sentence around it stays the client's own voice;
# only the numbers are ours. A README with no markers is left alone, so adopting
# this is per-repo and never a surprise rewrite.
COUNTS = re.compile(r"(<!--counts-->)(.*?)(<!--/counts-->)", re.S)


def stamp(repo, spec):
    """Rewrite the marked counts in README.md from the spec actually used."""
    path = os.path.join(repo, "README.md")
    if not os.path.isfile(path):
        return
    text = open(path, encoding="utf-8").read()
    if not COUNTS.search(text):
        return
    ops, paths, svcs = scale(spec)
    said = f"{ops:,} operations over {paths:,} paths, grouped into {svcs} services"
    out = COUNTS.sub(lambda m: m.group(1) + said + m.group(3), text)
    if out != text:
        open(path, "w", encoding="utf-8").write(out)
        print(f"[readme] {os.path.basename(repo)}: {said}")


def sweep(repo, removed):
    """Drop the directories a removal emptied, never one that holds anything."""
    for p in sorted({os.path.dirname(p) for p in removed}, key=len, reverse=True):
        while p:
            d = os.path.join(repo, p)
            if not os.path.isdir(d) or os.listdir(d):
                break
            os.rmdir(d)
            p = os.path.dirname(p)


def main():
    conf = yaml.safe_load(open(os.path.join(ROOT, "sdks.yaml")))
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("langs", nargs="*", choices=sorted(conf["sdks"]) + [[]], help="languages; default --all")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--check", action="store_true", help="diff only; non-zero if a client drifted")
    ap.add_argument("--repo", help="SDK repo path (single language only)")
    # THE DOCUMENT IS AN ARGUMENT, not a fact about this checkout. hanzo-inc/cloud's
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
        # ONE generator for the fleet, and a language may pin PAST it when the
        # shared version cannot emit that language at all. dart is the instance:
        # 7.14.0 dies in AbstractDartCodegen.fromProperty with
        # `JsonSchema cannot be cast to ComposedSchema` on our polymorphic request
        # bodies, so dart emitted nothing and sat four releases behind while every
        # other language regenerated fine. 7.19.0 emits it cleanly (measured: 117
        # api files). Pinning the fleet forward for one language would regenerate
        # twelve working clients to fix one, so the pin is where the defect is.
        # Delete `generator` from that SDK's row when the fleet moves past it.
        return sdk(name, cfg, document(repo, a.spec, docs),
                   str(cfg.get("generator_version", version)),
                   conf["drop"], repo, a.check)

    with futures.ThreadPoolExecutor(max_workers=a.j) as pool:
        results = list(pool.map(one, langs))
    if not all(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
