"""behold CLI — ``behold roster``.

Exit codes
----------
0   roster rendered
2   usage error (argparse; also an unknown flag such as ``--include-todo-subjects``)
3   source error (snapshot missing/unreadable/unsupported protocol)
4   guard violation (a write or network attempt was refused)

The guard is installed for the whole run. There is no default live discovery: a run needs
``--snapshot FILE`` (fixture or captured) or an explicit ``--herdr``. That is deliberate —
"read every session directory and pick the newest" is exactly the fleet-discovery shortcut
the approved decision forbids.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from typing import Any, Sequence

from . import field as F
from . import guard, identity, lane as lane_mod, render, util, watch
from .sources import Paths, SourceError, fleet_state, herdr, pi_state

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_SOURCE = 3
EXIT_GUARD = 4


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="behold",
        description="Read-only, derive-on-demand fleet roster (P1+P2 foundation).",
    )
    parser.add_argument("--version", action="version", version=f"behold {render.VERSION}")
    sub = parser.add_subparsers(dest="command")

    roster = sub.add_parser("roster", help="derive the roster and print it")
    roster.add_argument("--snapshot", help="herdr snapshot JSON (fixture or captured)")
    # No live snapshot: reading one needs a herdr child, and V3 has no external execution.
    roster.add_argument("--herdr", action="store_true",
                        help="refused: reading a live snapshot needs a child process (use --snapshot FILE)")
    roster.add_argument("--root", help="data root containing herdr/, proc/, pil/, instances/, state/")
    roster.add_argument("--live", action="store_true", help="use the real store paths (requires --snapshot or --herdr)")
    roster.add_argument("--markdown", action="store_true", help="render Markdown instead of JSON")
    roster.add_argument("--full", action="store_true", help="with --markdown: every field for every lane")
    roster.add_argument("--lane", help="single lane by pane id")
    roster.add_argument("--filter", action="append", default=[], metavar="KEY=OP",
                        help="repeatable, e.g. --filter 'H-5.value.status=working'")
    roster.add_argument("--sort", action="append", default=[], metavar="KEY[:desc]",
                        help="repeatable; default lane key")
    roster.add_argument("--proc-root", help="explicit /proc tree to read (default: disabled; host /proc is not read)")

    roster.add_argument("--as-of", help="evaluate ages at this ISO timestamp instead of now (single-run only)")
    roster.add_argument("--watch", action="store_true", help="re-derive on input change (bounded)")
    roster.add_argument("--watch-iterations", type=int, default=2)
    roster.add_argument("--watch-interval", type=float, default=0.5)
    roster.add_argument("--watch-max-seconds", type=float, default=30.0)
    roster.add_argument("--events-file", help="herdr events file to watch (snapshot fields only)")
    roster.add_argument("--verbose", action="store_true", help="include per-source timings in stderr")
    # Deny lists are fixed by the decision; the flags exist so a test can *tighten* them.
    roster.add_argument("--deny-workspace", action="append", default=[],
                        help="additional held workspace id (never removes a default)")
    roster.add_argument("--deny-pane", action="append", default=[],
                        help="additional reserved pane id (never removes a default)")
    return parser


def _paths_from_args(args: argparse.Namespace) -> Paths:
    if args.root:
        paths = Paths.for_root(args.root)
        if args.proc_root:
            paths.proc_root = args.proc_root
        return paths
    if args.live:
        paths = Paths.for_live()
        if args.snapshot:
            paths.snapshot = args.snapshot
        if args.proc_root:
            paths.proc_root = args.proc_root
        return paths
    # A bare --snapshot run reads the snapshot and nothing from the host: no /proc, no pil
    # records, no agent dir. Host inputs are opt-in, and /proc is only read when a root or
    # --proc-root names it.
    paths = Paths(root=None)
    paths.snapshot = args.snapshot
    paths.proc_root = args.proc_root or ""
    return paths


class Runner:
    """One derivation run: snapshot + caches + lanes. Reusable by ``--watch``."""

    def __init__(self, args: argparse.Namespace, policy: guard.Policy):
        self.args = args
        self.policy = policy
        self.paths = _paths_from_args(args)
        # A watched document must age: with --watch the clock is live on every iteration, so
        # a fixed as_of is refused rather than silently frozen.
        self.as_of = util.parse_iso(args.as_of) if args.as_of else time.time()
        self.as_of_iso = util.iso(self.as_of)
        self.snapshot = self._load_snapshot()
        # Admission-gated pil access: no directory walk, one candidate file per admitted lane,
        # and a denied lane never reaches the open at all.
        self.pil = identity.PilAccess(self.paths.pil_dir or None, policy)
        self.models = pi_state.model_catalog(self.paths.models_store, policy)
        recent = str(self.paths.state_dir) + "/dagr/recent" if self.paths.state_dir else None
        self.dagr = fleet_state.load_dagr_runs(recent, policy)
        self.beads = fleet_state.load_beads(self.paths.beads_file, policy)

    def _load_snapshot(self) -> herdr.Snapshot:
        if self.args.herdr:
            # V3: no child process, so no live read. A typed, explained refusal.
            raise SourceError(
                "--herdr needs a herdr child process, and P1/P2 has no external execution; "
                "capture the snapshot to a file and pass --snapshot FILE")
        if not self.paths.snapshot:
            raise SourceError(
                "no snapshot: pass --snapshot FILE (captured/fixture) or --herdr (explicit live read)"
            )
        if not os.path.exists(self.paths.snapshot):
            raise SourceError(f"snapshot not found: {self.paths.snapshot}")
        return herdr.load(self.paths.snapshot, self.policy)

    def context(self) -> lane_mod.Context:
        return lane_mod.Context(
            paths=self.paths,
            policy=self.policy,
            snapshot=self.snapshot,
            as_of=self.as_of,
            as_of_iso=self.as_of_iso,
            pil=self.pil,
            models=self.models,
            dagr=self.dagr,
            beads=self.beads,
        )

    def dependency_paths(self, built: list[Any]) -> list[str]:
        """Every store this derivation actually read, so watch can invalidate per source.

        V2 returned only the snapshot and session paths, so a profile/todos/settings/models/
        beads/cron/dagr-only change produced no new document. These are the same paths the
        adapters open, derived per lane from the admitted instance.
        """
        paths: list[str] = []
        if self.paths.snapshot:
            paths.append(self.paths.snapshot)
        if self.paths.beads_file:
            paths.append(self.paths.beads_file)
        if self.paths.models_store:
            paths.append(self.paths.models_store)
        if self.paths.state_dir:
            paths.append(os.path.join(self.paths.state_dir, "cron", "tasks.json"))
            paths.append(os.path.join(self.paths.state_dir, "dagr", "recent"))
        for built_lane in built:
            ident = built_lane.identity
            if ident is None or ident.session is None:
                continue
            paths.append(ident.session.path)
            if ident.pil and ident.pil.get("file"):
                paths.append(ident.pil["file"])
            if not ident.trusted:
                continue
            instance = pi_state.instance_from_agent_dir(
                ident.env.get("PI_CODING_AGENT_DIR"), self.paths.instances_dir)
            if instance and self.paths.instances_dir:
                base = os.path.join(self.paths.instances_dir, instance)
                paths.extend([
                    os.path.join(base, "pi-profile.json"),
                    os.path.join(base, "pi-profile-state.json"),
                    os.path.join(base, "pi-todo-state.json"),
                    os.path.join(base, "settings.json"),
                ])
            if self.paths.profiles_dir:
                for name in ("leader", "worker", "ask"):
                    paths.append(os.path.join(self.paths.profiles_dir, f"{name}.json"))
            if self.paths.global_mode_dir:
                paths.append(os.path.join(self.paths.global_mode_dir, "leader.json"))
                paths.append(os.path.join(self.paths.global_mode_dir, "worker.json"))
        # dedupe, keep order
        seen: set[str] = set()
        unique = []
        for path in paths:
            if path and path not in seen:
                seen.add(path)
                unique.append(path)
        return unique

    def lanes_and_inputs(self) -> tuple[list[dict[str, Any]], list[str], dict[str, str]]:
        started = time.perf_counter()
        ctx = self.context()
        agents = self.snapshot.agents
        if self.args.lane:
            agents = [a for a in agents if a.get("pane_id") == self.args.lane]
        built = [lane_mod.build_lane(agent, ctx) for agent in agents]
        lanes = [b.to_dict() for b in built]
        lanes = render.apply_filters(lanes, self.args.filter)
        lanes = render.apply_sort(lanes, self.args.sort)
        ctx.state_only_wall_ms = (time.perf_counter() - started) * 1000.0
        self.last_ctx = ctx
        inputs = self.dependency_paths(built)
        sessions: dict[str, str] = {}
        for b in built:
            if b.identity and b.identity.session:
                sessions[b.pane_id or ""] = b.identity.session.path
        return lanes, inputs, sessions

    def document(self, lanes: list[dict[str, Any]], ctx: lane_mod.Context) -> dict[str, Any]:
        # Role/global/profile aggregates are derived ONLY from lanes that were admitted and
        # whose ownership is verified. With none, the answer is a typed noaccess — never a
        # directory scan of every instance (which V2 did, reading held state).
        admitted_trusted = []
        for lane in lanes:
            ident = lane.get("identity") or {}
            if lane["admission"]["admitted"] and ident.get("trusted"):
                m3 = lane["fields"].get("M-3") or {}
                inst = (m3.get("value") or {}).get("instance") if isinstance(m3.get("value"), dict) else None
                if inst:
                    admitted_trusted.append(inst)
        trusted_instances = sorted(set(admitted_trusted))
        if trusted_instances:
            # Handles are derived from admitted+verified lanes FIRST; the reader is given that
            # list and constructs one path per name. It never lists the instances root, so a
            # held or foreign instance is never opened.
            global_profile = pi_state.global_profile_active(
                self.paths.instances_dir, trusted_instances, self.policy)
            global_profile["derived_from"] = {
                "lanes": "admitted+verified only",
                "instances": trusted_instances,
                "handle_source": "verified process agent-dir basename; no directory listing",
            }
            m4_state = global_profile.get("state", "present")
        else:
            global_profile = {
                "activeProfile": None,
                "state": "unknown",
                "reason": "noaccess: no admitted+trusted lane to attribute a global setting from",
                "scope": "global_file",
            }
            m4_state = "unknown"
        global_block = {
            "M-4": {
                "key": "M-4",
                "state": m4_state,
                "class": "authoritative",
                "scope": "global_file",
                "value": global_profile,
                "note": ("pi-profile-state.json is ONE global file for the machine; it is never a "
                         "lane field, and it is only read when an admitted, verified lane "
                         "attributes it"),
                "privacy": 1,
            },
            "goal_config": fleet_state.goals_file(self.paths.agent_dir, self.policy),
            "beads_export": {"path": self.paths.beads_file,
                             "issues": len(self.beads)},
            "dagr_index": {"runs": len(self.dagr)},
        }
        generated = util.iso(time.time())
        return render.document(
            lanes=lanes,
            ctx=ctx,
            guard_receipt=self.policy.receipt(),
            diagnostics=ctx.diagnostics,
            generated_at=generated,
            filters=self.args.filter,
            sorts=self.args.sort or ["key"],
            global_block=global_block,
            wall_ms=getattr(ctx, "state_only_wall_ms", 0.0),
        )


def _emit(text: str) -> None:
    """stdout only. behold never writes a file: the shell redirects if the operator wants one.

    The earlier ``--output`` flag was removed because a writable path inside the guarded
    process is a symlink/sibling-escape surface, and no in-process write is needed to produce
    the deliverable.
    """
    sys.stdout.write(text)
    if not text.endswith("\n"):
        sys.stdout.write("\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    raw = list(sys.argv[1:] if argv is None else argv)
    if not raw:
        raw = ["roster"]
    elif raw[0] not in ("roster", "--version", "-h", "--help"):
        raw = ["roster", *raw]
    args = parser.parse_args(raw)
    if args.command in (None, "roster"):
        try:
            return _run_roster(args)
        except guard.ReadOnlyViolation as exc:
            sys.stderr.write(f"behold: read-only guard refused an action: {exc}\n")
            return EXIT_GUARD
        except guard.NetworkViolation as exc:
            sys.stderr.write(f"behold: network guard refused an action: {exc}\n")
            return EXIT_GUARD
        except SourceError as exc:
            sys.stderr.write(f"behold: {exc}\n")
            return EXIT_SOURCE
        except guard.DeniedRead as exc:
            sys.stderr.write(f"behold: denied read: {exc}\n")
            return EXIT_GUARD
        except ValueError as exc:
            # A malformed --filter / --sort expression is a usage error, not a crash.
            sys.stderr.write(f"behold: {exc}\n")
            return EXIT_USAGE
    return EXIT_USAGE


def _run_roster(args: argparse.Namespace) -> int:
    if args.watch and args.as_of:
        sys.stderr.write(
            "behold: --as-of is a single-run override and cannot be combined with --watch "
            "(a watched document must age)\n")
        return EXIT_USAGE
    policy = guard.Policy(
        denied_workspaces=guard.DENIED_WORKSPACES | frozenset(args.deny_workspace),
        denied_panes=guard.DENIED_PANES | frozenset(args.deny_pane),
    )
    with guard.enforce():
        runner = Runner(args, policy)
        if not args.watch:
            lanes, _inputs, _sessions = runner.lanes_and_inputs()
            ctx = runner.last_ctx
            doc = runner.document(lanes, ctx)
            _emit(render.to_markdown(doc, full=args.full, lane_key=args.lane) if args.markdown
                  else render.to_json(doc))
            return EXIT_OK

        def derive() -> tuple[dict[str, Any], list[str], dict[str, str]]:
            # A fresh Runner per iteration: every cached source (snapshot, models, settings,
            # dagr index, beads export, runs, task files) is re-materialized, and the clock is
            # read again, so both the data and the ages in the document are current.
            fresh = Runner(args, policy)
            lanes, inputs, sessions = fresh.lanes_and_inputs()
            ctx = fresh.last_ctx
            return fresh.document(lanes, ctx), inputs, sessions

        def emit(doc: dict[str, Any], step: watch.WatchStep) -> None:
            doc["behold"]["watch"] = step.to_dict()
            text = render.to_markdown(doc, full=args.full, lane_key=args.lane) if args.markdown \
                else render.to_json(doc)
            _emit(text)

        steps = watch.run_watch(
            derive=derive,
            emit=emit,
            config=watch.WatchConfig(
                iterations=args.watch_iterations,
                interval_s=args.watch_interval,
                max_seconds=args.watch_max_seconds,
                events_file=args.events_file,
            ),
        )
        if args.verbose:
            for step in steps:
                sys.stderr.write(f"behold: watch {step.to_dict()}\n")
        return EXIT_OK
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
