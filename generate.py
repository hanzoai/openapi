#!/usr/bin/env python3
"""Generate every language SDK from hanzo.yaml — one spec, N projections.

    python3 generate.py --all              # regenerate every client in place
    python3 generate.py python go          # just these
    python3 generate.py --all --check      # fail if a committed client drifted
    python3 generate.py python --repo DIR  # the SDK repo is somewhere else

merge.py produces the spec; this produces the clients. Both live here so that a
client cannot be written by hand and cannot describe a route the spec does not
have. Every per-language knob is data in sdks.yaml and every SDK repo carries
only a call site (scripts/generate.sh), so there is nothing in a client repo
that can drift on its own — `--check` is what makes that a fact rather than a
convention.
"""
import argparse
import concurrent.futures as futures
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from fnmatch import fnmatch

import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.dirname(ROOT)  # sibling checkouts: ~/work/hanzo/<repo>
CACHE = os.path.expanduser("~/.cache/openapi-generator")
MAVEN = "https://repo1.maven.org/maven2/org/openapitools/openapi-generator-cli"


def jar(version):
    """The pinned generator, fetched once. A version is a version everywhere."""
    path = os.path.join(CACHE, f"openapi-generator-cli-{version}.jar")
    if not os.path.exists(path):
        os.makedirs(CACHE, exist_ok=True)
        url = f"{MAVEN}/{version}/openapi-generator-cli-{version}.jar"
        print(f"fetching {url}", flush=True)
        with urllib.request.urlopen(url) as r, open(path + ".part", "wb") as f:
            shutil.copyfileobj(r, f)
        os.replace(path + ".part", path)
    return path


# Written INTO a client tree by the language runtime, never by the generator, so
# they are not evidence of drift. Importing the Python client once is enough to
# make --check report 2142 phantom deletions, and a check that cries wolf is one
# nobody runs. Every one of these is already gitignored in its repo.
ARTIFACTS = ("__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache", "node_modules")


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
        # -DmaxYamlCodePoints: swagger-parser hands the document to snakeyaml,
        # which refuses anything over 3 * 1024 * 1024 = 3145728 code points.
        # hanzo.yaml passed that mark at 1bac13f (3,654,449) and the parser does
        # not say so plainly — it logs SnakeException, silently falls through to
        # the Swagger 2.0 compat reader, and dies with "Issues with the OpenAPI
        # input", which reads like a malformed spec. It is not: the document
        # validates at 0 errors and 0 warnings. A parser default, nothing else,
        # and it stops EVERY language at once — so it is set here, once, rather
        # than discovered separately in seven repos.
        "java", "-Xmx2g", "-DmaxYamlCodePoints=99999999", "-jar", jar(version), "generate",
        "-g", cfg["generator"],
        "-i", spec,
        "-o", out,
        "--global-property", ",".join(glob),
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
    # java -Xmx2g per worker, and this box has been OOMed by less.
    ap.add_argument("-j", type=int, default=2, help="parallel generators")
    a = ap.parse_args()

    langs = sorted(conf["sdks"]) if (a.all or not a.langs) else a.langs
    if a.repo and len(langs) != 1:
        ap.error("--repo takes exactly one language")
    spec = os.path.join(ROOT, conf["spec"])
    version = str(conf["generator"])

    def one(name):
        cfg = conf["sdks"][name]
        repo = a.repo or os.path.join(WORK, cfg["repo"])
        if not os.path.isdir(repo):
            sys.stderr.write(f"[{name}] no checkout at {repo}\n")
            return False
        return sdk(name, cfg, spec, version, conf["drop"], repo, a.check)

    with futures.ThreadPoolExecutor(max_workers=a.j) as pool:
        results = list(pool.map(one, langs))
    if not all(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
