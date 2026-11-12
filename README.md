# behold — read-only derive-on-demand fleet roster (P1+P2 foundation)

This tree is the **FT-21 P1+P2 foundation**: a single-process, no-daemon, no-database CLI
that derives a fleet roster from stores that already exist, on demand, with every value
carrying its class, source, observation time and reason. It is authored inside the
Yellowstone worktree under an isolated FT-21 staging tree so it can be reviewed and tested
without touching canonical Yellowstone, `~/Code/behold`, or any live lane.

**Status:** V4 — repairs the one binding residual the V3 review reopened (the global
`M-4` reader listed the instances root and opened a held/foreign instance's
`pi-profile-state.json`), plus five claim-accuracy corrections. V3's adopted repairs are kept
unchanged. Not installed, published or bootstrapped; no live read. **Not
installed, not published, not propagated, not bootstrapped, no live read.** See
`FIELD-LEDGER.md` for per-field state and `TRANSFER.md` + `MANIFEST.sha256` for the
(separately authorized) bootstrap into the behold repo.

V3 removes capability rather than disclosing it: there is **no external execution at all**
(no git/jj/herdr adapter, no child process, no argv allowlist to bypass), repo-derived fields
are typed `unknown(repo-adapter-not-isolated)`, held workspace/reserved tab/reserved pane are
denied before any read, an ownership disagreement blocks every preload and join, the active
branch is labelled `DISK_RECONSTRUCTED` rather than "current", and a composed mode definition
is `unverifiable` instead of false drift.

## What it is not

- No daemon, no service, no socket, no port, no database, no cache file.
- **No file output at all.** The CLI writes only to stdout; there is no `--output` flag, so
  a symlink planted at a would-be output path has no surface to exploit. Redirect stdout if
  you want a file.
- No write to any fleet store; no herdr/pi reporter; nothing is pushed to `herdr`.
- **No external programs at all.** The git/jj adapters are gone and `--herdr` is refused with
  an explanation: a child is not confined by the in-process guard, and repository config can
  make even a read-only git argv execute a helper. Repo fields are typed
  `unknown(repo-adapter-not-isolated)`. Host `/proc` is not read unless `--root` or
  `--proc-root` names a tree. There is no live snapshot read.
- No live fleet discovery. A run needs `--snapshot FILE` (fixture or captured) or an
  explicit `--herdr`; "scan every session dir and pick the newest" is deliberately absent.
- No `--include-*` export of goal text, TODO subjects, cron prompts, bead notes/titles,
  dagr titles, room bodies, message content, tool arguments, skill or prompt bodies.
- No jj invocation unless `--jj`, and then always with `--ignore-working-copy`.
- TTFT, monitor/job live state, exact loaded-extension attribution and rooms presence depth
  are **not invented**; they are reported as unknown/last-observed with a reason.

## Run it

```sh
# from this directory
python3 fixtures/make_fixtures.py /tmp/behold-fix --lanes 61   # synthetic fleet, 61 lanes
./bin/behold roster --root /tmp/behold-fix --as-of 2026-11-11T03:00:00Z > out.json # JSON
./bin/behold roster --root /tmp/behold-fix --markdown                             # Markdown
./bin/behold roster --root /tmp/behold-fix --markdown --lane w1A:p1               # one lane, all fields
./bin/behold roster --root /tmp/behold-fix --filter 'H-5.value.status=working' \
                                        --sort 'T-3.value:desc'
./bin/behold roster --root /tmp/behold-fix --watch --watch-iterations 3 --watch-interval 0.5
./bin/behold roster --root /tmp/behold-fix --jj --stash-count                     # opt-ins
```

Exit codes: `0` rendered, `2` usage error (including an unknown private-export flag),
`3` source error (missing snapshot / unsupported herdr protocol), `4` guard violation.

## Read the output

Every field is `{state, class, value, source, observed_at, age_s, method, reason, note,
unit, privacy}`.

| state | meaning |
|---|---|
| `present` | read or computed, with its source |
| `divergent` | two authoritative sources disagree; both values are shown |
| `conflict` | two stores disagree (e.g. session TODOs vs instance TODO mirror) |
| `inferred` | a heuristic, labelled with its limitation |
| `stale` / `last_observed` | a past observation that cannot be confirmed current; age shown |
| `expired` | a TTL-bounded value whose deadline passed |
| `unknown` | the data does not exist here; `reason` says why |
| `absent` | the source is legitimately missing (expected, not an error) |
| `error` | a source failed; the roster still renders |
| `held` | refused before any path was opened (held workspace / reserved pane) |
| `withheld` | class-2 content exists and is deliberately not exported |

`class` is `authoritative`, `derived` (always carries the exact `method`), `inferred`, or
`last_observed`. `privacy` is `0` public metadata, `1` operator-sensitive (counts/paths
only), `2` never emitted.

## Safety design (both mechanisms are real)

1. **Deny before read** (`behold/guard.py`, `Policy`). Workspace `w2` and pane `wE:t19` are
   refused *before* that lane's process/session/state paths are touched; `secrets/`,
   `auth.json`, `~/.ssh/` are refused at the single read funnel. Tests assert the deny event
   precedes per-lane opens and that the held lane's session file is never opened.
2. **Fail-closed read-only/network guard** (`guard.enforce()`). A CPython audit hook refuses
   any write-intent `open`, any filesystem mutation, any non-allowlisted subprocess, and any
   socket/urllib operation. There is **no write exception** — not even for output.
3. **No child, therefore no child boundary to argue about.** `EXTERNAL_EXECUTION = False`;
   `guard.run` no longer exists, and the audit hook refuses *any* spawn. `R-1..R-4`/`R-6` are
   typed unknowns with `repo-adapter-not-isolated`; `R-5`/`R-7` use `stat` only.
4. **Global state is read by handle, not by scanning.** `global.M-4` is given the instance
   names already established from admitted + verified lanes and constructs one path per name;
   it never lists the instances root, so a held or foreign instance's
   `pi-profile-state.json` is never opened. A full-roster negative plants such files and
   asserts the attempted-open list is empty — with a trusted positive control, so "nothing
   opened" cannot mean "reader never ran".
5. **Ownership is witness agreement.** A validated pin *alone* is `pin_only_unverified`; the
   pid triple, the process `HERDR_PANE_ID`/workspace/tab and the lane record must agree, and a
   disagreement is untrusted — no beads join, no profile, no instance resolution.

An mtime comparison is used only as a supplementary receipt; the audit hook is the boundary.

## Tests

```sh
tests/run-tests.sh                 # fixtures + 178 tests, ~8 s, stdlib only, no network
                                   # needs a POSIX shell, coreutils (dirname/mktemp) and
                                   # python3; needs no git, no jj, no herdr
tests/run-tests.sh --lanes 8       # smaller fleet
```

Suites: `test_v3_residuals` (the independent review's remaining expectations),
`test_si_regressions` (the defects SI found), `test_acceptance` (fields,
identity, active branch, honesty, privacy),
`test_guard` (read-only/network/deny/no-service scans, fixture-tree immutability),
`test_units` (leaf semantics, damaged JSONL, rotation, mode digest),
`test_watch` (bounded invalidation, rotation, process exit, events-only semantics),
`test_render` (JSON/Markdown, filter/sort, no progress claims),
`test_bench` (measured p50/p95 against the budget targets).

## Layout

```
bin/behold                  entry point (stdlib only)
behold/field.py             Field type: state/class/source/method/age/reason
behold/guard.py             pre-read deny policy + audit-hook read-only/network guard
behold/identity.py          pin + pane-matched pil record + /proc cross-check
behold/session.py           JSONL tree, active-branch chain, derived aggregates
behold/procfs.py            pid triple, allowlisted env read
behold/lane.py              one lane record: every operator field id
behold/render.py            JSON + Markdown, filter/sort, budget targets
behold/watch.py             bounded re-derive on input change (no daemon)
behold/sources/             herdr, git+jj, pi state (profile/mode/models/todos), fleet
                           state (rooms/cron/dagr/beads/jobs)
fixtures/make_fixtures.py  synthetic 61-lane fleet with sentinels and a real throwaway repo
tests/                     the six suites above
```
