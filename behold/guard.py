"""The safety boundary: privacy deny-before-read, and a fail-closed read-only/network guard.

Two independent mechanisms, both real (not an mtime comparison):

1. ``Policy`` — a *pre-read* deny list. Held workspaces (``w2``) and reserved panes
   (``wE:t19``) are refused before any session, state or process path is opened for that
   lane, and denied path markers (``secrets/``, ``auth.json``) are refused at the single
   read funnel every adapter must use. The refusal is recorded in the policy event log,
   so a test can prove the order: verdict first, zero opens after.

2. ``enforce()`` — a CPython audit hook (``sys.addaudithook``) that raises on any file
   open with write intent, on any filesystem mutation, on the spawn event family CPython
   raises (``subprocess.Popen``, ``os.posix_spawn``, ``os.exec*``, ``os.system``), and on any
   socket/urllib operation. It covers the audit events CPython itself emits; it is not an
   OS-level sandbox, and it cannot bind a program that was started before it was installed. This is fail-closed inside the behold process: an adapter that
   tried to write despite the design would crash instead of succeeding.

   V3 removes external execution completely (see ``EXTERNAL_EXECUTION``): a child process is
   not constrained by this hook, and an exact argv is not containment, so there is no
   subprocess API left to bypass. The hook still refuses the attempt.

Neither mechanism is optional in ``cli.main``; tests turn ``enforce()`` on and assert that
a write and a network connect both raise.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from dataclasses import dataclass, field as dc_field
from typing import Any, Iterable, Sequence

# --- deny lists -------------------------------------------------------------------------

#: Held workspaces: no process, session or state path for a lane in these is opened.
#: Path markers refused at the read funnel regardless of lane.
DENIED_PATH_MARKERS: tuple[str, ...] = (
    "/secrets/",
    "/.ssh/",
    "/auth.json",
    "auth.json",
    "/.credentials/",
    "/keyring",
)

#: **V3: behold executes nothing.** The V1/V2 external git/jj/herdr adapters were an
#: unproven boundary (a child is not constrained by this process's audit hook, and an exact
#: argv is not containment: repository config can make `git status` spawn a helper). Rather
#: than disclose that and ship it behind opt-in flags, the capability is removed. There is no
#: subprocess API in this module, no argv allowlist to bypass, and the audit hook still
#: refuses any spawn attempt as defence in depth.
EXTERNAL_EXECUTION = False

#: Repo-shaped fields are typed unknown with this reason: the adapter is intentionally absent.
REPO_ADAPTER_NOT_ISOLATED = "repo-adapter-not-isolated"

#: Held workspace, reserved tab and reserved pane. A real topology is
#: (workspace, tab, pane), so the tab is denied as well: `wE:t19` is a tab, not a pane id,
#: and a pane inside it must be refused even though its own id looks unrelated.
DENIED_WORKSPACES: frozenset[str] = frozenset({"w2"})
DENIED_TABS: frozenset[str] = frozenset({"wE:t19"})
DENIED_PANES: frozenset[str] = frozenset({"wE:t19"})

#: A pane id is a handle shaped like `w1K:p37`. Anything else is not a pane id and must not
#: be treated as one (the V2 check admitted `NOT_A_PANE`).
PANE_ID_RE = re.compile(r"^w[0-9A-Za-z]+:p[0-9A-Za-z]+$")
#: An instance directory name is one path component with no traversal or separators.
INSTANCE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
TAB_ID_RE = re.compile(r"^w[0-9A-Za-z]+:t[0-9A-Za-z]+$")
WORKSPACE_ID_RE = re.compile(r"^w[0-9A-Za-z]+$")


def is_pane_id(value: object) -> bool:
    return isinstance(value, str) and bool(PANE_ID_RE.match(value))


def is_tab_id(value: object) -> bool:
    return isinstance(value, str) and bool(TAB_ID_RE.match(value))


def is_workspace_id(value: object) -> bool:
    return isinstance(value, str) and bool(WORKSPACE_ID_RE.match(value))


class DeniedRead(PermissionError):
    """A pre-read policy refusal. Raised before the path is opened."""


class ReadOnlyViolation(PermissionError):
    """A write attempt inside the read-only guard."""


class NetworkViolation(PermissionError):
    """A network attempt inside the read-only guard."""


class NotAllowed(Exception):
    """Raised by the sole external-execution stub: behold never runs a program."""


@dataclass
class Policy:
    """Pre-read privacy policy plus an ordered event log for tests and receipts."""

    denied_workspaces: frozenset[str] = DENIED_WORKSPACES
    denied_tabs: frozenset[str] = DENIED_TABS
    denied_panes: frozenset[str] = DENIED_PANES
    denied_path_markers: tuple[str, ...] = DENIED_PATH_MARKERS
    events: list[tuple[str, str]] = dc_field(default_factory=list)
    #: every path the funnel attempted, so a test can assert zero attempts for a denial
    open_attempts: list[str] = dc_field(default_factory=list)
    denial_counts: dict[str, int] = dc_field(default_factory=dict)

    # -- lane admission ----------------------------------------------------------------
    def admit_lane(
        self,
        workspace_id: str | None,
        pane_id: str | None,
        tab_id: str | None = None,
    ) -> tuple[bool, str | None]:
        """Decide admission *before* any lane path is touched, over the real topology.

        A pane lives in a tab which lives in a workspace, so all three are checked. In V2 only
        workspace and pane were compared, which admitted a pane inside the reserved tab
        ``wE:t19``. The reason is a stable code, not prose:
        ``held_workspace:w2`` / ``reserved_tab:wE:t19`` / ``reserved_pane:wE:t19``.
        """
        candidates = (
            ("held_workspace", workspace_id, self.denied_workspaces),
            ("reserved_tab", tab_id, self.denied_tabs),
            ("reserved_pane", pane_id, self.denied_panes),
        )
        for label, value, denied in candidates:
            if value is None:
                continue
            if value in denied:
                reason = f"{label}:{value}"
                self._record(
                    "deny",
                    f"{reason} workspace={workspace_id} tab={tab_id} pane={pane_id}")
                return False, reason
        return True, None

    # -- path admission ----------------------------------------------------------------
    def check_path(self, path: str, purpose: str = "read") -> None:
        """Refuse a denied path *before* it is opened."""
        normalized = path.replace("//", "/")
        lowered = normalized.lower()
        for marker in self.denied_path_markers:
            if marker.lower() in lowered:
                self._record("deny_path", f"purpose={purpose} marker={marker}")
                raise DeniedRead(f"denied path marker {marker!r} (purpose={purpose})")
        self.open_attempts.append(path)

    def spawn_counts(self) -> list[tuple[str, int]]:
        counts: dict[str, int] = {}
        for kind, detail in self.events:
            if kind == "spawn":
                key = detail.split(" ")[0]
                counts[key] = counts.get(key, 0) + 1
        return sorted(counts.items())

    def _record(self, kind: str, detail: str) -> None:
        self.events.append((kind, detail))
        if kind.startswith("deny"):
            key = detail.split(" ")[0]
            self.denial_counts[key] = self.denial_counts.get(key, 0) + 1

    def receipt(self) -> dict[str, Any]:
        return {
            "spawns": dict(self.spawn_counts()),
            "denied_workspaces": sorted(self.denied_workspaces),
            "denied_tabs": sorted(self.denied_tabs),
            "denied_panes": sorted(self.denied_panes),
            "denied_path_markers": list(self.denied_path_markers),
            "denials": dict(sorted(self.denial_counts.items())),
            "open_attempts": len(self.open_attempts),
            "events": len(self.events),
        }


# --- the single read funnel -------------------------------------------------------------

def read_bytes(path: str, policy: Policy, purpose: str = "read") -> bytes:
    policy.check_path(path, purpose)
    with open(path, "rb") as fh:
        return fh.read()


def read_text(path: str, policy: Policy, purpose: str = "read", *, limit: int | None = None) -> str:
    policy.check_path(path, purpose)
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read() if limit is None else fh.read(limit)


def read_json(path: str, policy: Policy, purpose: str = "read") -> Any:
    return json.loads(read_text(path, policy, purpose))


def exists(path: str, policy: Policy) -> bool:
    """Existence probe through the funnel: a denied path is refused, not silently False."""
    policy.check_path(path, "stat")
    return os.path.exists(path)


# --- read-only / network guard ----------------------------------------------------------

_AUDIT_STATE = {
    "installed": False,
    "enforcing": False,
    "violations": [],
}

_WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
#: Every way CPython can start a program. ``subprocess.Popen`` is one; ``os.posix_spawn``,
#: ``os.exec*`` and ``os.system`` are others, and the V3 hook only knew the first. With no
#: execution API in the package this is defence in depth, but the hook must not be narrower
#: than the claim.
_SPAWN_EVENTS = {"subprocess.Popen", "os.posix_spawn", "os.exec", "os.spawn", "os.system"}

_WRITE_EVENTS = {
    "os.remove",
    "os.unlink",
    "os.rename",
    "os.replace",
    "os.mkdir",
    "os.rmdir",
    "os.symlink",
    "os.link",
    "os.truncate",
    "os.chmod",
    "os.chown",
    "os.utime",
    "shutil.copyfile",
    "shutil.copymode",
    "shutil.copystat",
    "shutil.move",
    "shutil.rmtree",
}
_NETWORK_EVENTS = {
    "socket.connect",
    "socket.bind",
    "socket.sendto",
    "socket.getaddrinfo",
    "socket.gethostbyname",
    "socket.gethostbyaddr",
    "urllib.Request",
    "http.client.connect",
    "ftplib.connect",
    "smtplib.connect",
}


def _audit(event: str, args: tuple[Any, ...]) -> None:
    state = _AUDIT_STATE
    if not state["enforcing"]:
        return
    if event == "open":
        path, mode, flags = (list(args) + [None, None, None])[:3]
        if isinstance(path, int):
            return
        write = False
        if isinstance(mode, str) and any(ch in mode for ch in "wax+"):
            write = True
        if isinstance(flags, int) and (flags & _WRITE_FLAGS):
            write = True
        if write:
            # The null device is the discard device: CPython opens it O_RDWR for
            # ``subprocess`` stdin=DEVNULL. Nothing is stored anywhere by that open.
            if isinstance(path, str) and os.path.realpath(path) == os.path.realpath(os.devnull):
                return
            state["violations"].append(("open", str(path)))
            raise ReadOnlyViolation(f"read-only guard: write open refused: {path} mode={mode}")
        return
    if event in _WRITE_EVENTS:
        state["violations"].append((event, repr(args[:1])))
        raise ReadOnlyViolation(f"read-only guard: {event} refused ({args[:1]!r})")
    if event in _NETWORK_EVENTS:
        state["violations"].append((event, repr(args[:1])))
        raise NetworkViolation(f"network guard: {event} refused ({args[:1]!r})")
    if event in _SPAWN_EVENTS:
        first = args[0] if args else None
        name = os.path.basename(str(first)) if isinstance(first, (str, bytes, os.PathLike)) else repr(first)
        state["violations"].append((event, name))
        # No allowlist: behold has no legitimate child, so every spawn event is a defect.
        raise ReadOnlyViolation(
            f"read-only guard: {event} {name} is refused (no child execution in P1/P2)")


def install_audit_hook() -> None:
    if not _AUDIT_STATE["installed"]:
        sys.addaudithook(_audit)  # cannot be removed, only gated by ``enforcing``
        _AUDIT_STATE["installed"] = True


class enforce:  # noqa: N801 - used as a context manager, lower-case reads as the guard
    """Turn the process-wide guard on for the duration of a behold run."""

    def __enter__(self) -> None:
        install_audit_hook()
        _AUDIT_STATE["enforcing"] = True
        return None

    def __exit__(self, *exc: Any) -> bool:
        _AUDIT_STATE["enforcing"] = False
        return False


def guard_state() -> dict[str, Any]:
    return {
        "installed": _AUDIT_STATE["installed"],
        "enforcing": _AUDIT_STATE["enforcing"],
        "violations": list(_AUDIT_STATE["violations"]),
    }


# --- no external execution ----------------------------------------------------------

class NotAllowed(Exception):
    """The only answer to a request to run a program: refuse, loudly and typed."""


def refuse_external(reason: str = "external execution is not available in P1/P2") -> None:
    """The single answer to any request to run a program: refuse, loudly and typed."""
    raise NotAllowed(reason)


# --- process environment, allowlisted ---------------------------------------------------

def read_env_allowlist(
    path: str, keys: Iterable[str], policy: Policy, purpose: str = "proc-environ"
) -> dict[str, str]:
    """Read a ``/proc/<pid>/environ`` blob and keep only allowlisted keys.

    Everything else is dropped before the caller sees anything: the roster never
    materializes a lane's environment, not even to redact it afterwards.
    """
    raw = read_bytes(path, policy, purpose)
    wanted = set(keys)
    found: dict[str, str] = {}
    for chunk in raw.split(b"\0"):
        if not chunk or b"=" not in chunk:
            continue
        name_b, _, value_b = chunk.partition(b"=")
        try:
            name = name_b.decode("utf-8", "strict")
        except UnicodeDecodeError:
            continue
        if name in wanted:
            found[name] = value_b.decode("utf-8", "replace")
    return found


def open_local_url_blocked(url: str) -> None:
    """Explicit belt-and-braces: no adapter may construct a URL fetch call."""
    raise NetworkViolation(f"network guard: refusing to fetch {url!r}")


_ = urllib.request  # imported only so the module is audited at import time, never used
