#!/usr/bin/env bash
# Run every generated client against a REAL cloud and report per language.
#
# A compile proves a client is well-formed; it does not prove the client can
# reach a server, decode a body, or turn a refusal into an error rather than an
# empty success. That last one is the trap — an SDK that swallows a 403 and
# returns a zero value looks identical to one that works, until production.
#
# Default target is the local cloud. HANZO_BASE_URL points it anywhere.
set -uo pipefail
export HANZO_BASE_URL="${HANZO_BASE_URL:-http://127.0.0.1:8899}"
HERE=$(cd "$(dirname "$0")" && pwd)
export PATH="$HOME/.cargo/bin:$PATH"
pass=0; fail=0; skip=0
run() { # name, command...
  local n=$1; shift
  if ! command -v "${2:-$1}" >/dev/null 2>&1 && [ "${SKIPCHECK:-1}" = "0" ]; then
    printf '%-12s SKIP (no toolchain)\n' "$n"; skip=$((skip+1)); return
  fi
  local out; out=$("$@" 2>&1)
  if printf '%s' "$out" | grep -q "^PASS"; then
    printf '%-12s PASS\n' "$n"; pass=$((pass+1))
  else
    printf '%-12s FAIL\n' "$n"; printf '%s\n' "$out" | tail -3 | sed 's/^/    /'; fail=$((fail+1))
  fi
}
echo "target: $HANZO_BASE_URL"
command -v go   >/dev/null && run go     sh -c "cd $HERE/go && go mod tidy >/dev/null 2>&1; go run ."                       || skip=$((skip+1))
command -v uv   >/dev/null && run python sh -c "uv run -q --with pydantic --with urllib3 --with python-dateutil python3 $HERE/py.py" || skip=$((skip+1))
command -v node >/dev/null && run typescript sh -c "cd $HERE/ts && npm install --silent --no-audit --no-fund >/dev/null 2>&1 && node main.js" || skip=$((skip+1))
command -v dart >/dev/null && run dart   sh -c "cd $HERE/dart && dart pub get >/dev/null 2>&1 && dart run bin/main.dart" || skip=$((skip+1))
command -v php  >/dev/null && run php    sh -c "php $HERE/php.php"                             || skip=$((skip+1))
command -v ruby >/dev/null && run ruby   sh -c "ruby $HERE/rb.rb"                              || skip=$((skip+1))
command -v cargo >/dev/null && run rust  sh -c "cd $HERE/rs && cargo run --quiet"              || skip=$((skip+1))
echo
echo "pass=$pass fail=$fail skip=$skip"
[ "$fail" -eq 0 ]
