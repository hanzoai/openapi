#!/usr/bin/env python3
"""Pull hanzoai/cloud's woven document into this repo and re-merge.

    python3 sync.py                       # resync, then run merge.py
    python3 sync.py --check               # fail if cloud/openapi.yaml is stale
    python3 sync.py --cloud ~/work/hanzo/cloud

`cloud/openapi.yaml` is the ONE spec here that is not authored here. hanzoai/cloud
weaves it from its own router — every app projects itself, the weave composes the
projections, and a drift gate there regenerates from source and fails on any diff
— so it cannot describe a route the binary does not serve. That is the property
no hand-written spec has, and it is why `merge.py` lets this file win wherever it
and an authored spec describe the same route.

A copy is only true at the moment it is made, so making it is a command and not a
procedure: this reads `origin/main:openapi.yaml` out of a cloud checkout (after
fetching, so a stale worktree cannot be mistaken for the branch) and writes it
here byte-for-byte. A resync that changes nothing produces no diff; the one that
does shows exactly what the binary started or stopped serving.

Nothing is ever written back to hanzoai/cloud. The traffic is one-way by
construction: this repo reads a ref, and the SDKs read `hanzo.yaml`.
"""
import argparse
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SOURCE = "openapi.yaml"                        # the path inside hanzoai/cloud
TARGET = os.path.join(ROOT, "cloud", "openapi.yaml")
REF = "origin/main"
CLOUD = os.environ.get("CLOUD_DIR") or os.path.join(os.path.dirname(ROOT), "cloud")


def git(repo, *args):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"sync: git {' '.join(args)} failed in {repo}\n{r.stderr.strip()}")
    return r.stdout


def repository(path):
    """A git checkout, worktrees included — where `.git` is a file, not a dir."""
    return subprocess.run(["git", "-C", path, "rev-parse", "--git-dir"],
                          capture_output=True).returncode == 0


def woven(repo):
    """`origin/main:openapi.yaml` from a hanzoai/cloud checkout, and its commit."""
    if not repository(repo):
        sys.exit(f"sync: no hanzoai/cloud checkout at {repo}\n"
                 f"      git clone git@github.com:hanzoai/cloud {repo}\n"
                 f"      (or point --cloud / CLOUD_DIR at one)")
    git(repo, "fetch", "--quiet", "origin", "main")
    return git(repo, "show", f"{REF}:{SOURCE}"), git(repo, "rev-parse", "--short", REF).strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cloud", default=CLOUD, help=f"hanzoai/cloud checkout (default {CLOUD})")
    ap.add_argument("--check", action="store_true",
                    help="report drift and exit non-zero; write nothing")
    a = ap.parse_args()

    spec, commit = woven(a.cloud)
    have = open(TARGET).read() if os.path.exists(TARGET) else ""
    if spec == have:
        print(f"cloud/openapi.yaml is {REF} ({commit}) — nothing to sync")
        return 0
    if a.check:
        print(f"cloud/openapi.yaml differs from {REF} ({commit}) — run `python3 sync.py`")
        return 1

    open(TARGET, "w").write(spec)
    print(f"cloud/openapi.yaml <- hanzoai/cloud {REF} ({commit})", flush=True)
    return subprocess.call([sys.executable, os.path.join(ROOT, "merge.py")])


if __name__ == "__main__":
    sys.exit(main())
