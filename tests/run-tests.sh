#!/usr/bin/env bash
# run-tests.sh — behold P1+P2 test suite (stdlib only, no network, no fleet access).
#
# Usage: tests/run-tests.sh [--keep] [--lanes N]
# Exits non-zero on the first failing suite. Every suite prints its own PASS/FAIL counts,
# and the bench suite prints p50/p95 numbers against the budget targets (numbers, not vibes).
set -uo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(dirname "$here")"
cd "$root"

python="${PYTHON:-python3}"
lanes=61
keep=0
while [ $# -gt 0 ]; do
  case "$1" in
    --keep) keep=1 ;;
    --lanes) lanes="$2"; shift ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done

workdir="$(mktemp -d "${TMPDIR:-/tmp}/behold-tests.XXXXXX")"
cleanup() { [ "$keep" -eq 1 ] || rm -rf "$workdir"; }
trap cleanup EXIT

export BEHOLD_FIXTURE_ROOT="$workdir/fixtures"
export BEHOLD_SANDBOX="$workdir/sandbox"
export BEHOLD_AS_OF="2026-11-11T03:00:00Z"
mkdir -p "$BEHOLD_SANDBOX"

echo "== fixtures =="
"$python" fixtures/make_fixtures.py "$BEHOLD_FIXTURE_ROOT" --lanes "$lanes" || exit 1

echo
echo "== unit + integration + negative + guard + watch =="
"$python" -m unittest discover -s tests -t . -v 2>&1 | tail -40
status=${PIPESTATUS[0]}
echo
if [ "$status" -ne 0 ]; then
  echo "FAILED (exit $status)"
  [ "$keep" -eq 1 ] && echo "sandbox kept at $workdir"
  exit "$status"
fi
echo "PASSED"
[ "$keep" -eq 1 ] && echo "sandbox kept at $workdir"
exit 0
