"""Shared test helpers: one fixture fleet per process, plus CLI invocation in-process.

The fixture root and ``as_of`` come from the environment set by ``tests/run-tests.sh`` so a
suite can also be run by hand after generating fixtures.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from typing import Any

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
FIXTURE_ROOT = os.environ.get("BEHOLD_FIXTURE_ROOT", "/tmp/behold-fix")
AS_OF = os.environ.get("BEHOLD_AS_OF", "2026-11-11T03:00:00Z")
SENTINELS = {
    "goal_text": "SENTINEL_GOAL_TEXT",
    "todo_subject": "SENTINEL_TODO_SUBJECT",
    "cron_prompt": "SENTINEL_CRON_PROMPT",
    "room_body": "SENTINEL_ROOM_BODY",
    "bead_description": "SENTINEL_BEAD_DESCRIPTION",
    "bead_notes": "SENTINEL_BEAD_NOTES",
    "bead_title": "SENTINEL_BEAD_TITLE",
    "dagr_title": "SENTINEL_DAGR_TITLE",
    "session_message": "SENTINEL_SESSION_MESSAGE",
    "tool_arguments": "SENTINEL_TOOL_ARGUMENTS",
    "skill_body": "SENTINEL_SKILL_BODY",
    "prompt_body": "SENTINEL_PROMPT_BODY",
    "api_key": "SENTINEL_API_KEY",
    "env_value": "SENTINEL_ENV_VALUE",
    "monitor_description": "SENTINEL_MONITOR_DESCRIPTION",
}

_cache: dict[str, Any] = {}


#: V3 has no external adapters at all: no --git/--jj flags to pass. Repo-derived fields are
#: typed unknown with `repo-adapter-not-isolated`.
GIT: tuple[str, ...] = ()


def roster(*extra: str, root: str | None = None) -> tuple[int, str, str]:
    """Run the CLI in a subprocess (so the guard/audit hook is a fresh process)."""
    argv = [sys.executable, os.path.join(ROOT, "bin", "behold"), "roster",
            "--root", root or FIXTURE_ROOT, "--as-of", AS_OF, *extra]
    proc = subprocess.run(argv, capture_output=True, text=True, timeout=180,
                          env={**os.environ, "PYTHONPATH": ROOT})
    return proc.returncode, proc.stdout, proc.stderr


def roster_json(*extra: str, root: str | None = None) -> dict[str, Any]:
    key = "|".join(extra) + "|" + (root or FIXTURE_ROOT)
    if key in _cache:
        return _cache[key]
    code, out, err = roster(*extra, root=root)
    if code != 0:
        raise AssertionError(f"roster failed rc={code}\nstdout={out[:2000]}\nstderr={err[:4000]}")
    doc = json.loads(out)
    _cache[key] = doc
    return doc


def lanes(doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {lane["key"]: lane for lane in doc["lanes"]}


def field(lane: dict[str, Any], key: str) -> dict[str, Any]:
    return lane["fields"][key]


def full_text(doc: dict[str, Any]) -> str:
    return json.dumps(doc, ensure_ascii=False)


def generated_root() -> str:
    return FIXTURE_ROOT


def require_fixtures() -> None:
    if not os.path.exists(os.path.join(FIXTURE_ROOT, "herdr", "snapshot.json")):
        raise unittest.SkipTest(
            f"fixtures missing at {FIXTURE_ROOT}; run tests/run-tests.sh or "
            f"python3 fixtures/make_fixtures.py {FIXTURE_ROOT}"
        )
