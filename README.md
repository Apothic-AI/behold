# behold

> **A read-only, derive-on-demand fleet roster.**
> One command reads the stores that already exist and prints what it found, with every value
> carrying its state, its source, when it was observed and why it is missing.

`behold` answers the question *"what is this fleet actually doing right now, and how do I
know?"* without becoming part of the fleet. It is a single process with no daemon, no
database, no cache file and no network access. It derives the roster on demand, prints it to
stdout, and exits.

```sh
behold roster --root /path/to/fixture-tree --markdown
```

---

## Contents

| Section | What is in it |
|---|---|
| [What behold is](#what-behold-is) | The one idea, and the long list of things it deliberately is not |
| [Install](#install) | Clone, optional venv, a PATH-friendly symlink, and why `pip install` is not an option |
| [Quick start](#quick-start) | Fixture mode, captured-snapshot mode, live mode, and the exact CLI |
| [Reading the output](#reading-the-output) | The JSON document, the lane envelope, field anatomy, states and classes |
| [The field ledger](#the-field-ledger) | Every family and every field code the tool returns |
| [Filtering and sorting](#filtering-and-sorting) | Flattened keys, operators, worked examples |
| [Safety boundaries](#safety-boundaries) | The two real mechanisms, and what they do not cover |
| [Known limitations](#known-limitations) | The honest list, including what will never be available from disk |
| [Troubleshooting](#troubleshooting) | Every error message the tool can print, and what to do |
| [Tests](#tests) | The offline suite and the measured numbers |
| [Layout](#layout) | What each file does |

---

## What behold is

`behold` derives a **roster** of fleet lanes (a terminal pane running an agent) from stores
that already exist on disk:

* a **herdr snapshot** (the workspace / pane / agent topology),
* the **pi session JSONL** of each lane,
* per-instance **profile, TODO and settings** stores,
* the **rooms** pin registry and room files,
* the **cron** task file,
* the **dagr** run index,
* the **beads** issue export.

Three properties hold for every value it prints.

**1. Every value is typed.** A field is never just a value. It is a record with a `state`,
a `class`, a `source`, an `observed_at`, a `method` (for derived numbers), a `reason` (for
every non-present state) and a `privacy` class. "No value" is never written as `0` or `-`;
it is `unknown` or `absent` with a stated reason.

**2. Every value is traceable.** `source` names the file or the record the value came from.
`method` carries the exact expression for anything computed, so you can recompute it by
hand. If two authoritative sources disagree, both are shown and the state is `divergent` or
`conflict` rather than a silent pick.

**3. Nothing is invented.** Where the data does not exist, the tool says so and says why.
Time-to-first-token is not persisted by pi, so `T-8` is `unknown` forever in this tranche.
The runtime-selected session branch is not persisted either, so `P-4` labels the leaf
`DISK_RECONSTRUCTED` rather than calling it current.

### Privacy and read-only design

The design is **counts and paths only**. Free text is never exported, and there is no flag
that turns it on:

| Never exported | Why |
|---|---|
| goal text | class 2 |
| TODO subjects | class 2 |
| cron prompt bodies | class 2 |
| room bodies and receipts | class 2 |
| bead descriptions and notes | class 2 |
| bead titles, dagr run titles | class 1 free text, withheld under the "counts and paths only" rule |
| session message content, tool arguments | class 2 |
| skill bodies, prompt bodies | class 2 |
| environment values other than the single allowlisted `PI_PROFILE` key | class 2 |

Read-only is enforced, not promised. Two independent mechanisms are active for the whole
run, and both are covered by tests:

1. **Deny before read.** Held workspaces and reserved tabs/panes are refused *before* any
   session, state or process path for that lane is opened. Denied path markers
   (`/secrets/`, `/.ssh/`, `/auth.json`, `/.credentials/`, `/keyring`) are refused at the
   single read funnel every adapter must use.
2. **Fail-closed read-only and network guard.** A CPython audit hook raises on any
   write-intent `open`, any filesystem mutation, any socket or urllib operation, and any
   spawn event (`subprocess.Popen`, `os.posix_spawn`, `os.exec*`, `os.system`). There is no
   write exception, not even for output. A write attempt inside the process crashes the run
   rather than succeeding.

`behold` also never writes a file. There is no `--output` flag, so a symlink planted at a
would-be output path has no surface to exploit. Redirect stdout if you want a file.

### What it is not

* No daemon, no service, no socket, no port, no database, no cache file.
* No write to any fleet store. No herdr or pi reporter. Nothing is pushed back.
* **No external programs at all.** The git, jj and herdr adapters were removed in V3. A
  child process is not confined by an in-process audit hook, and repository config can make
  even a read-only `git` argv run a helper writer, so the capability was removed rather
  than shipped behind an opt-in flag. Repo fields are typed
  `unknown(repo-adapter-not-isolated)`.
* No live fleet discovery. A run needs `--snapshot FILE` or an explicit `--herdr`.
  "Scan every session directory and pick the newest" is deliberately absent.
* No message bodies, prompts, secrets, TODO subjects, bead notes or room receipts.
* No exact proof of which extensions were loaded. An inert extension registers no tool, so
  the tool list cannot prove the inventory. `E-1` is `inferred` and says so.
* No claim that the roster knows whether a lane is making progress. `H-5` is the status
  string herdr reported, verbatim.

---

## Install

### Requirements

| Item | Requirement |
|---|---|
| Python | **CPython 3.10 or newer** |
| Dependencies | **none**. Standard library only |
| Shell | a POSIX shell and `coreutils` for the test suite only |
| Network | never used, at install time or at run time |

Verified by running the CLI and the full suite on CPython 3.10, 3.11, 3.12, 3.13 and 3.14.

### There is no `pip install`

This tree ships **no packaging metadata**: no `pyproject.toml`, no `setup.py`, no
`setup.cfg`, no entry points. `pip install .` and `pip install git+...` therefore do not
work, and pretending otherwise would send you down a dead end.

What ships instead is a **script plus a package**:

```
bin/behold      the entry point (executable, shebang python3)
behold/         the importable package
```

`bin/behold` puts the repository root on `sys.path` itself, so it works from any working
directory and through a symlink. Pick whichever of the following fits.

### Step 1: clone the published repository

```sh
git clone https://github.com/Apothic-AI/behold.git
cd behold
```

### Step 2 (optional): a virtual environment

There is nothing to install, so a venv is optional. It is still the tidiest way to pin an
interpreter for a fleet tool.

```sh
python3.10 -m venv ~/.venvs/behold
source ~/.venvs/behold/bin/activate
behold --version          # -> behold 0.1.0-p1p2
```

Deactivate with `deactivate`. The venv holds no packages; it only pins the interpreter.

### Step 3 (optional): put it on your PATH

**Symlink** (recommended). The target must be the `bin/behold` script, not the package
directory. `bin/behold` resolves its own realpath, so the symlink resolves the package
correctly from anywhere:

```sh
mkdir -p ~/.local/bin
ln -s "$HOME/Code/behold/bin/behold" ~/.local/bin/behold
hash -r
behold --version          # -> behold 0.1.0-p1p2
```

Make sure `~/.local/bin` is on your `PATH`:

```sh
export PATH="$HOME/.local/bin:$PATH"
```

**Shell alias or function**, if you would rather not touch `PATH`:

```sh
# bash / zsh
alias behold="$HOME/Code/behold/bin/behold"
```

### No install needed at all

Three other invocations that work as-is:

```sh
./bin/behold roster --root /path/to/tree      # from the repository root
python3 -m behold roster --root /path/to/tree # from the repository root
python3 /any/where/behold/bin/behold roster --root /path/to/tree
```

---

## Quick start

### Mode 1: a synthetic fixture fleet (fully offline)

The repository ships a fixture generator that builds a synthetic fleet with sentinels: a
held lane, a reserved tab, a lane with no session, a stale session pin, a TODO conflict, a
virtual model, a jj workspace, a partial session tail and more. It touches nothing real.

```sh
# 1. build a synthetic fleet (default 61 lanes; the generator never emits fewer than 16)
python3 fixtures/make_fixtures.py /tmp/behold-fix --lanes 61

# 2. derive the roster as JSON
./bin/behold roster --root /tmp/behold-fix --as-of 2026-11-11T03:00:00Z > out.json

# 3. derive the roster as Markdown
./bin/behold roster --root /tmp/behold-fix --markdown

# 4. one lane, every field
./bin/behold roster --root /tmp/behold-fix --markdown --lane w1A:p1

# 5. filter and sort
./bin/behold roster --root /tmp/behold-fix --filter 'H-5.value.status=working' \
                                        --sort 'T-3.value:desc'

# 6. bounded watch: re-derive when an input changes
./bin/behold roster --root /tmp/behold-fix --watch --watch-iterations 3 --watch-interval 0.5
```

`--as-of` freezes the clock so ages and staleness are reproducible. It is a single-run
override and is refused together with `--watch`.

### Mode 2: a captured snapshot

`--snapshot FILE` reads **one** file and nothing else. With no `--root` and no `--live`,
the host `/proc`, the pil records and the agent directory are never opened.

```sh
behold roster --snapshot /path/to/snapshot.json
```

The snapshot must be a herdr snapshot document with an integer `protocol` field. Protocol
`22` is the only supported one; an unknown protocol is a loud error, never a silent
mis-parse. Unknown *keys* inside a known protocol are tolerated, because herdr adds them.

### Mode 3: the real store paths (`--live`)

`--live` points the adapters at the real stores under your home directory:

```
~/.local/state/pil/sessions        ~/.pi-profile-switch/instances
~/.pi-profile-switch/profiles      ~/.pi/agent
~/.pi/modes                        ~/.local/state/pi-bg
```

```sh
behold roster --live --snapshot /path/to/captured/snapshot.json
```

`--live` still needs a snapshot: `--herdr` is refused because reading a live snapshot
would need a herdr child process. The live path reads real private stores, so use it
knowingly. This tranche has not been exercised against a live fleet.

Two stores are not reachable in live mode. The **beads export** is unset there, because
reading it live means running `bd` as a subprocess, which this tranche does not do. The
**models catalogue** path is unset at the top level and is resolved per instance instead.
Both are listed as remaining gates in `FIELD-LEDGER.md`.

### CLI reference

```
usage: behold [-h] [--version] {roster} ...

usage: behold roster [-h] [--snapshot SNAPSHOT] [--herdr] [--root ROOT]
                     [--live] [--markdown] [--full] [--lane LANE]
                     [--filter KEY=OP] [--sort KEY[:desc]]
                     [--proc-root PROC_ROOT] [--as-of AS_OF] [--watch]
                     [--watch-iterations WATCH_ITERATIONS]
                     [--watch-interval WATCH_INTERVAL]
                     [--watch-max-seconds WATCH_MAX_SECONDS]
                     [--events-file EVENTS_FILE] [--verbose]
                     [--deny-workspace DENY_WORKSPACE] [--deny-pane DENY_PANE]
```

The first line is `behold --help`, the second is `behold roster --help`, both verbatim.

| Option | Meaning |
|---|---|
| `--snapshot FILE` | herdr snapshot JSON (fixture or captured). Required unless `--herdr` is used |
| `--herdr` | **refused** with an explanation. A live snapshot read needs a child process, and P1/P2 has no external execution. Capture the snapshot to a file and pass `--snapshot FILE` |
| `--root DIR` | data root containing `herdr/`, `proc/`, `pil/`, `instances/`, `state/` |
| `--live` | use the real store paths. Requires `--snapshot` (or `--herdr`, which is refused) |
| `--markdown` | render Markdown instead of JSON |
| `--full` | with `--markdown`: emit every field for every lane, not just the summary table |
| `--lane PANE_ID` | restrict to one lane, by pane id such as `w1A:p1` |
| `--filter KEY=OP` | repeatable. Keeps lanes whose flattened `KEY` satisfies the operator |
| `--sort KEY[:desc]` | repeatable. Defaults to `key` (the pane id) |
| `--proc-root DIR` | an explicit `/proc` tree to read. The host `/proc` is never read unless you name it |
| `--as-of ISO8601` | evaluate ages at this timestamp instead of now. Single-run only |
| `--watch` | re-derive on input change, bounded by iterations and by wall clock |
| `--watch-iterations N` | maximum number of rendered documents (default 2) |
| `--watch-interval S` | seconds between polls (default 0.5). Below 0.05 s is refused as a spin loop |
| `--watch-max-seconds S` | hard wall-clock bound for the whole loop (default 30) |
| `--events-file FILE` | a herdr events file to watch. Changes to it do not refresh session fields |
| `--verbose` | per-source timings and watch steps on **stderr** |
| `--deny-workspace ID` | add a held workspace. Defaults are never removed |
| `--deny-pane ID` | add a reserved pane. Defaults are never removed |

`behold --version` prints `behold 0.1.0-p1p2`.

### Exit codes

| Code | Meaning | Example message |
|---|---|---|
| `0` | the roster rendered | (no message) |
| `2` | usage error | `behold: filter 'H-5.value.status' needs one of = != ~ !~` |
| `3` | source error | `behold: snapshot not found: /tmp/nope.json` |
| `4` | guard violation | `behold: read-only guard refused an action: ...` |

An unknown flag is a usage error (`argparse` prints the usage line and exits 2), so
`--include-todo-subjects` and friends fail loudly instead of appearing to work.

---

## Reading the output

### The JSON document: top-level keys

```jsonc
{
  "behold": { /* run metadata, privacy rules, counts, timings */ },
  "global": { /* M-4 plus three machine-level summaries */ },
  "lanes":  [ /* one envelope per lane */ ],
  "diagnostics": [ /* per-lane notices about damaged or disagreed data */ ]
}
```

#### The `behold` block

| Key | What it holds |
|---|---|
| `version` | the tool version, here `0.1.0-p1p2` |
| `generated_at` | when this document was produced |
| `as_of` | the clock the ages were evaluated against (`--as-of`, or now) |
| `mode` | always `derive-on-demand-read-only` |
| `snapshot` | `{protocol, agents, panes, workspaces, tabs, source, bytes, duration_ms}` |
| `paths` | every directory the run was allowed to read, and the ones it was given |
| `guard` | the safety receipt: spawn counts, deny lists, denial counts, `open_attempts`, `events` |
| `privacy` | the effective rules (`held_workspaces`, `reserved_panes`, `denied_path_markers`, `counts_and_paths_only`, `no_private_exports`) plus the denial tally |
| `runtime_only_pending` | the six things that can only come from a live runtime (see [Runtime-only pending](#runtime-only-pending)) |
| `budget_targets` | the performance targets. **Targets, not a measured whole-fleet proof** |
| `lanes` | `{total, by_field_state}`: the lane count and a tally of every field state |
| `timings_ms` | per-source `{count, p50, max}` timings |
| `wall_ms` | total wall time of the derivation |
| `filters`, `sort` | the filters and sorts that were applied, echoed back |
| `watch` | present only under `--watch`: `{iteration, changed_sources, refreshed_lanes, stale_lanes, rotated, process_exits, elapsed_s}` |

#### The `global` block

| Key | What it holds |
|---|---|
| `M-4` | the machine-wide active profile. **Global only.** It is never a lane field, and it is read only when an admitted, verified lane attributes it |
| `goal_config` | the goal *config* file: its path, its top-level key names, and whether it carries goal text. It carries no goal text and no queue |
| `beads_export` | `{path, issues}`: where the beads export was read from and how many issues it holds |
| `dagr_index` | `{runs}`: how many dagr runs the index points at |

#### `diagnostics`

A flat array of notices about data that was damaged, disagreed or was skipped:

```json
[
  {"lane": "w1B:p1", "code": "identity_untrusted", "state": "session_pin_stale_used_pil_record",
   "disagreements": ["pin_session=... != record_session=..."]},
  {"lane": "w1D:p2", "code": "session", "detail": "partial_final_line_ignored",
   "session": "/path/to/session.jsonl"}
]
```

Codes you will see: `identity_untrusted` (the witnesses disagreed, so no join was performed)
and `session` (the session file had a partial final line, a duplicate id, a malformed line
or a chain problem).

### The lane envelope

```jsonc
{
  "key": "w1A:p1",                  // the pane id, and the lane's sort key
  "handles": { ... },               // ids and names only, never content
  "admission": { "admitted": true, "reason": null },
  "identity": { ... },              // how "this session belongs to this lane" was proven
  "fields": { "H-1": { ... }, ... } // every field, keyed by its code
}
```

`handles` holds `pane_id`, `workspace_id`, `tab_id`, `workspace_label`, `name`,
`name_layer` and `agent_status`.

`identity` is the trust record, and it is the part worth reading before you trust anything
else in the lane:

| Key | What it holds |
|---|---|
| `state` | the resolution outcome (see the table below) |
| `trusted` | `true` only when every witness agrees |
| `session_id` | the validated session UUID |
| `session_source` | where the session came from (the pin, the pil record, ...) |
| `pin_path`, `pin_reporter_pid` | the herdr reporter's pin and the pid that wrote it |
| `pil_record` | the pane-matched lane record, including how it was looked up |
| `proc` | the `/proc` observation: pid, comm, state, starttime, boot_id, the pid triple |
| `process_tuple` | `verified`, `unrecorded` or `mismatch` |
| `checks` | the named checks that were run, each with `ok` and `detail` |
| `disagreements` | the specific disagreements, when there are any |
| `untrusted_because` | why the lane is untrusted, in one phrase |
| `note` | free-form note, when there is one |

Identity states:

| State | Meaning |
|---|---|
| `verified` | the pin, the pane-matched lane record and the `/proc` pid triple all agree |
| `session_pin_stale_used_pil_record` | the herdr pin was stale (it lags after `/new` and `/resume`); the lane record was used instead |
| `session_pin_stale_no_fallback` | the pin was stale and no lane record could stand in |
| `reporter_pin_missing_used_pil_record` | no pin at all; the lane record was used |
| `pin_only_unverified` | a pin existed and nothing else did. **Not trusted.** A pin alone proves nothing |
| `no_session_source` | no session file could be located for this lane |
| `pid_disagreement` | the reporter pid and the lane record pid differ |
| `pane_disagreement` | the recorded pane id differs from the snapshot pane id |
| `process_tuple_disagreement` | the recorded boot id / starttime do not match the observed process |
| `envpane_disagreement` | the process's own `HERDR_PANE_ID` is not this pane |

Only `verified` is **trusted**. An untrusted lane is still shown, with every witness
visible, but no explicit join (beads) and no profile or instance resolution happen on it.

### Field anatomy

Every field is the same shape. This is a real `P-7` record from the fixture fleet:

```json
{
  "state": "present",
  "class": "derived",
  "value": 3600.0,
  "source": "session header + last entry",
  "observed_at": "2026-11-11T02:11:00Z",
  "age_s": 2940.0,
  "method": "observed_now - header.timestamp (lane process present)",
  "reason": null,
  "note": null,
  "unit": "s",
  "privacy": 0
}
```

| Key | Meaning |
|---|---|
| `state` | one of the eleven states below |
| `class` | `authoritative`, `derived`, `inferred` or `last_observed` |
| `value` | the value itself, or `null` when the state carries no value |
| `source` | the file or record the value came from. Paths only, never content |
| `observed_at` | when the value was observed (ISO 8601, UTC) |
| `age_s` | seconds between `observed_at` and the `as_of` clock |
| `method` | the exact expression for a derived value. **Required** for every derived value, enforced in code |
| `reason` | why there is no value. Required for every non-value state |
| `note` | a limitation, a caveat, or extra detail that does not fit in `reason` |
| `unit` | `s`, `tokens` or `%` where it applies |
| `privacy` | `0` public metadata, `1` operator-sensitive, `2` never emitted |

### Field states

| State | Meaning | Has a value? |
|---|---|---|
| `present` | read or computed, with its source | yes |
| `divergent` | two authoritative sources disagree; both values are shown | yes |
| `conflict` | two stores disagree (for example the session TODOs and the instance TODO mirror) | yes |
| `inferred` | a heuristic, labelled with its limitation | yes |
| `stale` / `last_observed` | a past observation that cannot be confirmed current; the age is shown | yes |
| `expired` | a TTL-bounded value whose deadline passed | yes |
| `unknown` | the data does not exist here; `reason` says why | no |
| `absent` | the source is legitimately missing. Expected, not an error | no |
| `error` | a source failed; the roster still renders | no |
| `held` | refused before any path was opened (held workspace, reserved tab, reserved pane) | no |
| `withheld` | class-2 content exists and is deliberately not exported | no |

A field is never silently dropped. Every one of the 56 per-lane codes is always present in
`fields`, either with a value or with a state and a reason.

### Field classes

| Class | Meaning |
|---|---|
| `authoritative` | read verbatim from a store |
| `derived` | computed, and carrying the exact `method` that produced it |
| `inferred` | a heuristic that may be wrong, labelled with its limitation |
| `last_observed` | a past observation that cannot be confirmed current |

### Privacy classes

| Class | Meaning |
|---|---|
| `0` | public fleet metadata |
| `1` | operator-sensitive: counts, paths and handles only |
| `2` | never emitted. The field appears with `withheld` and no value |

### JSON example

A trimmed but real lane, from the fixture fleet:

```json
{
  "behold": {
    "version": "0.1.0-p1p2",
    "generated_at": "2026-11-12T04:03:05Z",
    "as_of": "2026-11-11T03:00:00Z",
    "mode": "derive-on-demand-read-only",
    "lanes": { "total": 1, "by_field_state": { "absent": 2, "inferred": 1, "present": 38, "stale": 2, "unknown": 8, "withheld": 5 } }
  },
  "global": {
    "M-4": {
      "key": "M-4",
      "state": "present",
      "class": "authoritative",
      "scope": "global_file",
      "value": { "activeProfile": "worker", "state": "present" },
      "privacy": 1
    }
  },
  "lanes": [
    {
      "key": "w1A:p1",
      "handles": {
        "pane_id": "w1A:p1",
        "workspace_id": "w1A",
        "tab_id": "w1A:t1",
        "workspace_label": "alpha-workspace",
        "name": "alpha-leader",
        "name_layer": "tabs[].label",
        "agent_status": "working"
      },
      "admission": { "admitted": true, "reason": null },
      "identity": {
        "state": "verified",
        "trusted": true,
        "session_id": "aaaaaaaa-0000-4000-8000-000000000001",
        "session_source": "herdr agent_session pin (validated, agrees with the lane record)",
        "process_tuple": "verified",
        "disagreements": [],
        "untrusted_because": null
      },
      "fields": {
        "H-5": {
          "state": "present",
          "class": "authoritative",
          "value": {
            "status": "working",
            "state_change_seq": 7,
            "completion_seq": null,
            "interactive_ready": null,
            "restore_error": null
          },
          "source": "panes[].agent_status",
          "observed_at": "2026-11-11T03:00:00Z",
          "age_s": null,
          "method": null,
          "reason": null,
          "note": "herdr-observed status value, not a conclusion about progress; not reported by herdr for this lane: completion_seq, interactive_ready, restore_error",
          "unit": null,
          "privacy": 0
        },
        "T-3": {
          "state": "present",
          "class": "derived",
          "value": 15.75,
          "source": "T-1 + T-2",
          "observed_at": "2026-11-11T02:07:00Z",
          "age_s": 3180.0,
          "method": "T-1 / T-2 * 100",
          "reason": null,
          "note": null,
          "unit": "%",
          "privacy": 0
        },
        "R-1": {
          "state": "unknown",
          "class": "authoritative",
          "value": null,
          "source": "git branch + oid: adapter removed in V3",
          "observed_at": null,
          "age_s": null,
          "method": null,
          "reason": "repo-adapter-not-isolated",
          "note": "requires a separately reviewed isolated execution boundary",
          "unit": null,
          "privacy": 0
        }
      }
    }
  ],
  "diagnostics": []
}
```

### Markdown example

`--markdown` renders a summary table, the pending runtime-only metrics, the budget targets
and, with `--full` or `--lane`, a per-field section for every lane:

```markdown
# behold roster

derived on demand · read-only · 16 lanes · generated 2026-11-12T04:03:48Z · as-of 2026-11-11T03:00:00Z

snapshot: protocol 22 · agents 16 · panes 16 · workspaces 11
privacy: counts and paths only · held workspaces w2 · reserved panes wE:t19 · denials {"held_workspace:w2": 1, "reserved_pane:wE:t19": 1, "reserved_tab:wE:t19": 1}

| lane | workspace | pane | status | model | ctx% | branch | dirty | todos | beads | identity |
|---|---|---|---|---|---|---|---|---|---|---|
| alpha-leader | alpha-workspace | w1A:p1 | working | acme-large-1 | 15.75 | unknown: repo-adapter-not-isolated | unknown: repo-adapter-not-isolated | 3 | 2 | verified · aaaaaaaa-0000-4000… |
| alpha-worker | alpha-workspace | w1A:p2 | idle | acme-fast-1 | 1.52 | unknown: repo-adapter-not-isolated | unknown: repo-adapter-not-isolated | absent: no todo state in session or instance store | 0 | verified · aaaaaaaa-0000-4000… |

## pending runtime-only metrics

- T-8 ttft_ms: pi does not persist time-to-first-token
- J-1 background job live exit state: only log files and last tool calls exist
- J-2 monitor exit state: runtime-only
- J-3 bizzy monitor registry: no persistable state
- E-1 exact loaded extension list: tools alone cannot prove it (inert extensions register nothing); needs loader/registration evidence, not the tool list
- M-7 rooms presence/inbox depth: deferred to P3
```

And the per-lane detail section (`--full` or `--lane`):

```markdown
## w1A:p1 — alpha-leader

- **H-5** `present`/authoritative: {"completion_seq":null,"interactive_ready":null,"restore_error":null,"state_change_seq":7,"status":"working"}
  - source `panes[].agent_status` · note herdr-observed status value, not a conclusion about progress; not reported by herdr for this lane: completion_seq, interactive_ready, restore_error
- **T-3** `present`/derived: 15.75
  - source `T-1 + T-2` · method `T-1 / T-2 * 100` · age 3180.0s
- **D-2** `withheld`/authoritative: withheld (class 2)
- **J-1** `stale`/last_observed: stale: {"log_count":2,"log_files":[{"job_id":"bg-0001",…}]}
  - source `pi-bg/*.log stats + session bash_bg calls`
```

---

## The field ledger

**57 unique field ids**: 56 per lane, plus `M-4`, which is global only and is never a lane
field. The tables below cover every one of them.

### Coverage at a glance

| Family | Lane ids | Emitted with a value | Always `unknown` | Always `withheld` (class 2) | Runtime-only / deferred |
|---|---|---|---|---|---|
| H herdr topology | 6 | 6 | none | none | none |
| P pi session and model | 10 | 10 | none | none | none |
| T tokens, context, performance | 8 | 7 | `T-8` | none | `T-8` |
| R repository | 7 | 2 (`R-5`, `R-7`) | `R-1` `R-2` `R-3` `R-4` `R-6` | none | none |
| M mode, profile, rooms | 6 | 5 | `M-7` | none | `M-7` |
| G goals and dagr | 4 | 4 | none | none | none |
| D TODOs | 2 | 1 (`D-1`) | none | `D-2` | none |
| C crons | 2 | 1 (`C-1`) | none | `C-2` | none |
| E extensions | 2 | 2 | none | none | `E-1` (exact list) |
| S skills and prompts | 4 | 2 (`S-1`, `S-3`) | none | `S-2` `S-4` | none |
| J monitors and jobs | 3 | 2, last-observed only | `J-3` | none | `J-1` `J-2` `J-3` |
| B beads | 2 | 1 (`B-1`) | none | `B-2` | none |
| **Total** | **56 lane ids + `M-4` = 57** | **45** | **8** | **5** | **6 items** |

"Always unknown" means the field can never carry a value in this tranche. "Emitted" means
the field carries a value under normal conditions; every field can also be `absent`,
`conflict`, `divergent`, `stale` or `error` depending on what the stores actually hold.
No field is silently dropped.

`FIELD-LEDGER.md` in this repository tracks each field's source, its state in the tranche
and the gate that still has to be closed before the value is true of a live fleet. Its
repository rows still describe the `--git` and `--jj` opt-ins that V3 removed; the tables
below describe what the code returns today.

### H: herdr topology

All six come from the one snapshot read the whole roster is built on.

| Code | Field | What it means | Source | States |
|---|---|---|---|---|
| `H-1` | workspace label | The human name of the workspace the pane lives in | `snapshot workspaces[].label` | `present`, `absent` |
| `H-2` | workspace id | The workspace handle, for example `w1A` | `snapshot workspaces[].workspace_id` | `present`, `absent` |
| `H-3` | pane id | The pane handle, for example `w1A:p1` | `snapshot agents[].pane_id` | `present`, `absent` |
| `H-4` | pane name + winning layer | The name of the lane, and which snapshot layer produced it | `tabs[].label` → `agents[].name` → `agents[].display_agent` → `panes[].label` → `agents[].terminal_title_stripped` | `present`, `absent` |
| `H-5` | status + sequence numbers | The status string herdr reported, verbatim, plus `state_change_seq`, `completion_seq`, `interactive_ready` and `restore_error` | `panes[].agent_status` then `agents[].agent_status` | `present`, `unknown` |
| `H-6` | cwd vs foreground cwd | The lane's working directory and the shell's foreground directory | `snapshot agents[].cwd`, `foreground_cwd` | `present`, `divergent`, `absent` |

`H-4` names its winner: the `source` is the layer that answered and the `note` repeats it
as `winning layer: <layer>`. `H-5` keeps `done` as a legitimate herdr value rather than
reading it as a claim that the work finished, and its `note` lists the sub-values herdr did
not report. `H-6` is `divergent` when the two realpaths differ.

### P: pi session and model

| Code | Field | What it means | Source / method | States |
|---|---|---|---|---|
| `P-1` | provider | The selected provider and the physical provider behind it | `model_change.provider` vs the last assistant `provider` | `present`, `divergent`, `absent` |
| `P-2` | model | The selected model and the physical model behind it | `model_change.modelId` vs the last assistant `model` | `present`, `divergent`, `absent` |
| `P-3` | reasoning effort | The thinking level in force | `thinking_level_change`, else the assistant `thinkingLevel` | `present`, `absent` |
| `P-4` | session id + leaf + chain | The validated session UUID, the leaf, the chain state and the entry counts | session header + the `id`/`parentId` tree, read from disk | `present` |
| `P-5` | session path | The session file, realpath-normalized, with the reported spelling and how many spellings exist | the pin or the pane-matched lane record | `present` |
| `P-6` | session start | When the session opened | session header `timestamp` | `present`, `absent` |
| `P-7` | session duration | How long the session has been open | `observed_now - header.timestamp` when the lane process is present, else `last_entry_timestamp - header.timestamp`. The `method` says which | `present`, `unknown` |
| `P-8` | last observed turn span | The span of the last user to assistant turn seen on disk | `last_assistant_or_user_ts - last_user_ts` | `present`, `absent` |
| `P-9` | session name | The session's own name. Privacy 1 | the latest `session_info.name` | `present`, `absent` |
| `P-10` | fork lineage | The parent session path. Privacy 1 | session header `parentSession` | `present`, `absent` |

`P-1` and `P-2` are `divergent` when the selected model differs from the physical one,
which is the normal case for a virtual-model lane. `P-4` carries
`leaf_authority: "DISK_RECONSTRUCTED"` and `runtime_leaf: null`: pi keeps the selected leaf
in memory only, so the file can show the last entry but cannot prove which branch is
current. `P-8` is explicitly the last observed span, never a live "still running" timer.

### T: tokens, context and performance

| Code | Field | What it means | Method | States |
|---|---|---|---|---|
| `T-1` | context used | Tokens used by the last assistant message | the message's `usage.totalTokens`, else `usage.input + output + cacheRead + cacheWrite` | `present`, `absent` |
| `T-2` | context max | The context window of the **physical** model | `models-store.json` `contextWindow` | `present`, `unknown` |
| `T-3` | context % | How full the context window is | `T-1 / T-2 * 100` | `present`, `unknown` |
| `T-4` | session tokens | Tokens used by the session on the active branch, broken down into `input`, `output`, `cacheRead`, `cacheWrite`, `reasoning`, `totalTokens`, `cost`, `cost_estimated`, `usage_kinds`, `usage_entries`, `cache_warm_entries` and `compaction_usage_entries` | the sum over assistant usage, `usage` entries and compaction / branch-summary usage | `present`, `unknown` |
| `T-5` | cache counts + hit rate | Cache reads, cache writes, input tokens, and the hit rate as a ratio and a percentage | `ΣcacheRead / (ΣcacheRead + Σinput)` | `present`, `absent` |
| `T-6` | cost (estimated flag) | Accumulated cost, flagged `estimated` when any total was not provider-reported. Privacy 1 | `Σ usage.cost{...}` | `present`, `absent` |
| `T-7` | TPS | Output tokens per second, from persisted timings | `Σ output tokens / Σ durationMs` over the last 20 assistant messages that carry a duration | `present`, `unknown` |
| `T-8` | TTFT | Time to first token | none | **`unknown`, always** |

`T-2` never assumes a default window. If the catalogue has no `contextWindow` for the
physical model, `T-2` and `T-3` are `unknown` with the reason
`no contextWindow: <detail>` and `T-1 or T-2 unknown; refusing to assume a context size`.

`T-4` sums **on the active branch only**, so abandoned branches are excluded by design. When
that differs from a branch-blind file sum, the difference is reported in the `note`, with
both numbers.

`T-8` is `unknown` in every lane, forever, in this tranche: pi persists total `durationMs`
but not time-to-first-token. It is listed under
[Runtime-only pending](#runtime-only-pending) and needs a separately reviewed live
extension.

**Honesty note.** `T-1`, `T-3`, `T-4` and `T-5` are *derived*. They are not proven to equal
what pi's own footer prints: pi may add estimates or compaction adjustments that a raw
usage sum does not reproduce. Each field carries its `method` string so the comparison is
mechanical, and footer equivalence remains an open gate.

### R: repository state

The git and jj adapters were **removed** in V3. A child process is not constrained by an
in-process audit hook, and repository configuration can make even a read-only git argv run
a helper writer, so the capability was removed rather than shipped behind an opt-in flag.
Detection by `stat` is pure and stays.

| Code | Field | What it means | Source | States |
|---|---|---|---|---|
| `R-1` | git branch + oid | The branch and commit the lane is on | *(adapter removed)* | **`unknown`, always** |
| `R-2` | worktree identity | The repository the workspace is bound to | herdr's `workspaces[].worktree` only; the git cross-check is disabled | **`unknown`, always** |
| `R-3` | dirty counts | Modified, staged, untracked and conflicted counts | *(adapter removed)* | **`unknown`, always** |
| `R-4` | ahead / behind / stash | How far the branch has diverged, and the stash count | *(adapter removed)* | **`unknown`, always** |
| `R-5` | jj detected | Whether the lane sits in a jj workspace, and its bookmark token | `.jj` presence by `stat`, plus the snapshot's `tokens.jj_bookmark` | `present`, `absent`, `expired` |
| `R-6` | jj bookmark, change, status | The jj working-copy state | *(adapter removed)* | **`unknown`, always** |
| `R-7` | non-repo lane | Whether the lane is in a repository at all | `.git` / `.jj` presence by `stat` | `present` |

The reason string is the same for all five removed fields:
`repo-adapter-not-isolated`. `R-5` needs no jj binary, and its bookmark token is
TTL-aware: a token whose expiry has passed yields `expired`. `R-7` reads `NO_REPO`, `git`
or `jj`, and the absence of a repository is an expected state, not an error.

### M: mode, profile and rooms

| Code | Field | What it means | Source | States |
|---|---|---|---|---|
| `M-1` | active mode + metadata | The mode key in force, the overlay keys, the drift policy, when it was activated, and the definition paths, digests, scopes and labels. Privacy 1, no prompt body | the session's `custom pi-mode-state.v3` entry, plus the definition files for their label only | `present`, `absent` |
| `M-2` | mode drift | Whether the recorded digest still matches the file on disk | the digest recomputed with pi-modes' own fingerprint algorithm | `present`, `unknown` |
| `M-3` | profile with provenance | The declared profile, the selected profile, the resolved skills and tools, the instance and the catalogue label. Privacy 1 | the process env key `PI_PROFILE`, plus `instances/<instance>/pi-profile.json` | `present`, `unknown` |
| `M-4` | global active profile | The machine-wide active profile. **Global only, in `global`, never a lane field** | `pi-profile-state.json`, read only for instances attributed by an admitted, verified lane | `present`, `conflict`, `unknown` |
| `M-5` | rooms lane name | The rooms name pinned to this pane | `rooms/names.json` `pins["pane:<id>"]` | `present`, `absent` |
| `M-6` | rooms membership | Which rooms the lane is listed in, and the registry count. Privacy 1, names only | `rooms/registry/` plus the `rooms/rooms/` files | `present`, `unknown` |
| `M-7` | presence / inbox depth | How present the lane is and how deep its inbox is. Privacy 1 | *(deferred to P3)* | **`unknown`, always** |

`M-2` recomputes the digest byte-for-byte the way pi-modes does. A **composed** definition
(any overlay, or a project scope) is reported as `unverifiable`, not as drift: the accepted
digest covers the composed result, so hashing the wrong object would be a false alarm.

`M-3` keeps three profiles apart and never conflates them:

* **declared**: the single allowlisted environment key `PI_PROFILE`, read at process start.
  It can be stale after a `/profile` switch, and the field says so.
* **selected**: the per-instance `pi-profile.json`. The instance comes **only** from the
  verified process's own `PI_CODING_AGENT_DIR`, never from path containment of the session
  file.
* **resolved**: the saved skill and tool references, plus the catalogue label.

No other environment variable value is ever emitted.

`M-4` is the one global file on the machine. The instances root is never listed: the reader
is handed the instance names already established from admitted and verified lanes and
constructs one path per name. A held or foreign instance's copy is therefore never opened,
and with no admitted and verified lane the answer is `unknown(noaccess)`.

### G: goals and dagr

| Code | Field | What it means | Source | States |
|---|---|---|---|---|
| `G-1` | goals count + statuses | How many goals the lane has and their status breakdown. Privacy 1, counts only | the per-session goal `custom` entry | `present`, `absent`, `unknown` |
| `G-2` | goals queue depth | How deep the goal queue is. Privacy 1 | the same entry | `present`, `absent`, `unknown` |
| `G-3` | dagr runs for the lane | The dagr runs that name this pane, with task state counts and owner counts. Privacy 1, **title withheld** | the `recent` index, then each `run.json` | `present`, `absent`, `unknown` |
| `G-4` | dagr staleness | How old the run snapshot is, and whether the run's own events are newer than it | `observed_at - run.generated_at` compared with `run.events` | `present`, `absent`, `unknown` |

`G-1` and `G-2` are `unknown` when the goal store is text-only: the count is withheld
because the goal text is class 2. `G-3` maps a run to a pane by the orchestrator pane or by
any task attempt's locator pane. That is a **mapping, not progress**: task `state` values
are reported exactly as recorded.

### D: TODOs

| Code | Field | What it means | Source | States |
|---|---|---|---|---|
| `D-1` | TODO counts + conflict | Open, completed and total counts, with the by-status breakdown. Privacy 1 | the session's `pi-core-todo-state` on the active branch, cross-checked against the instance's `pi-todo-state.json` for the same session UUID | `present`, `conflict`, `absent` |
| `D-2` | TODO subjects | The text of the TODOs | *(never exported)* | **`withheld`, always** |

`D-1` is `conflict` when the session store and the instance mirror disagree about the
total. Both numbers are in the value and the `reason` spells the conflict out.

### C: crons

| Code | Field | What it means | Source | States |
|---|---|---|---|---|
| `C-1` | crons for the lane | The cron tasks whose `projectDir` is this lane's cwd: `id`, `name`, `schedule`, `cron`, `kind`, `projectDir`. Privacy 1 | the cron `tasks.json` | `present`, `unknown` |
| `C-2` | cron prompt | The prompt body of a cron task | *(never read into output)* | **`withheld`, always** |

A task that carries a `prompt` field increments a `prompt_field_skipped` counter. The
prompt is skipped, not read and then redacted.

### E: extensions

| Code | Field | What it means | Source | States |
|---|---|---|---|---|
| `E-1` | extensions loaded | Which extensions the session appears to have loaded | the session system-message replay: `toolsAdded` / `toolsRemoved` and the skills section | **`inferred`, always** |
| `E-2` | installed package pins | The packages configured for this lane: name and ref only | the instance `settings.json` package entries | `present`, `absent` |

`E-1` is the weakest field in the ledger and says so in its own `reason`: an **inert
extension registers no tool**, so the tool list cannot prove the extension inventory. The
field is a lower bound on what was loaded, never a proof. Exact attribution needs loader or
registration evidence from a live runtime, which is listed under
[Runtime-only pending](#runtime-only-pending). `E-2` is what is *configured*, which is not
the same thing as what is loaded.

### S: skills and prompts

| Code | Field | What it means | Source | States |
|---|---|---|---|---|
| `S-1` | skills loaded | The skills named in the session, with their paths, plus the names the profile resolved | the session skills section, cross-checked against `pi-profile.json` `resolved.skills` | `present`, `conflict`, `absent` |
| `S-2` | skill text | The body of a skill | *(never emitted)* | **`withheld`, always** |
| `S-3` | prompts (configured vs loaded) | The configured prompt paths and the names of the sections that were loaded | `settings.json` prompt sources plus the session system-message section names | `present` |
| `S-4` | prompt text | The body of a prompt | *(never emitted)* | **`withheld`, always** |

`S-1` is `conflict` when the session's skills section and the profile's resolved skills
disagree. `S-3` carries `loaded_is_not_proof_of_bodies: true`: a section name proves the
section was present, not what was in it.

### J: monitors and background jobs

| Code | Field | What it means | Source | States |
|---|---|---|---|---|
| `J-1` | background tasks | The `bash_bg` calls seen in the session and the `pi-bg/*.log` files with their sizes and mtimes. Privacy 1 | session tool calls plus log file stats | `stale` (last observed) |
| `J-2` | monitors set | The `monitor` tool calls seen in the session. Privacy 1 | session tool calls | `stale` (last observed) |
| `J-3` | bizzy monitors | The bizzy monitor registry. Privacy 1 | `bizzy.json` | **`unknown`, always** |

`J-1` and `J-2` are **not** running states. A log file's size and mtime are evidence that
something was logged, not that a process is alive, and a later monitor exit cannot be seen
in session data at all. Their `reason` says this. `J-3` is `unknown` because `bizzy.json`
holds only `disabledTools`: there is no monitor registry to read.

### B: beads

| Code | Field | What it means | Source | States |
|---|---|---|---|---|
| `B-1` | beads for the lane | The issues attributed to this lane: ids, statuses, priorities and types, with a by-status breakdown. Privacy 1, **title withheld** | the beads export, joined on `metadata.agent_pane` **and** `metadata.agent_session` | `present`, `unknown` |
| `B-2` | bead description and notes | The body of a bead | *(never emitted)* | **`withheld`, always** |

The join is deliberately strict, and the field says how strict it was:

* `metadata.agent_pane` must equal the pane, and `metadata.agent_session` must equal the
  **validated** session id **exactly**. A suffix match is forgeable and a path-shaped value
  must equal the realpath, not merely contain it.
* A matching `owner`, a `project:<workspace>` label, or a bead id quoted in prompt text is
  **not** a join. Those are counted in `rejected` as `owner_only`, `label_only` and
  `incomplete_metadata`. A label scopes the project, nothing more.
* Without a validated session identity the join refuses outright, with
  `identity_untrusted:<reason>` or `session_identity_not_validated`. An unvalidated
  attribution is worse than a count of zero with a reason.

### Runtime-only pending

These six items appear verbatim in `behold.runtime_only_pending` and in the Markdown
footer. They are not bugs and they are not failures: the data simply does not exist on
disk.

| Field | What is missing | Why |
|---|---|---|
| `T-8` | TTFT | pi persists total `durationMs`, not time-to-first-token |
| `J-1` | live exit state of a background job | only log files and last tool calls exist |
| `J-2` | monitor exit state | runtime-only |
| `J-3` | bizzy monitor registry | no persistable state |
| `E-1` | the exact loaded extension list | tools alone cannot prove it. An inert extension registers nothing; it needs loader or registration evidence |
| `M-7` | rooms presence and inbox depth | deferred to a separately approved P3 phase |

Closing any of these needs a new extension, its own approval gate, and a rollout. It is
not a flag flip.

---

## Filtering and sorting

Filtering and sorting operate on **flattened field paths**, so any property the JSON exposes
is reachable without a second schema. There is no query language and no expression parser:
four operators, and the key is a dotted path.

### Flattened keys

| Pattern | Example | Meaning |
|---|---|---|
| `key` | `key` | the pane id |
| `admitted` | `admitted` | `true` or `false` |
| `handles` | `handles` | the whole handle map |
| `<CODE>` | `T-3` | the whole field record |
| `<CODE>.state` | `T-3.state` | the field's state, for example `present` |
| `<CODE>.value` | `T-3.value` | the value itself |
| `<CODE>.value.<path>` | `H-5.value.status` | a path inside the value |
| `identity.state` | `identity.state` | the identity resolution state |
| `identity.session_id` | `identity.session_id` | the validated session UUID |

Two things are **not** flattened: `identity.trusted` (only `identity.state` and
`identity.session_id` are reachable), and anything nested deeper than the JSON actually
goes. Lists are indexed as `key[0]`, `key[1]`, and so on.

### Operators

| Operator | Syntax | Meaning |
|---|---|---|
| `=` | `KEY=VALUE` | exact string equality |
| `!=` | `KEY!=VALUE` | not equal |
| `~` | `KEY~GLOB` | shell glob match (`*`, `?`, `[seq]`), case-sensitive |
| `!~` | `KEY!~GLOB` | not a glob match |

There is no `>` or `<`. Numbers compare as strings, so `T-3.value=15.75` works but
`T-3.value>10` does not exist. For a numeric range, sort instead.

Note the glob operator takes **no `=`**: it is `KEY~GLOB`, not `KEY=~GLOB`. The parser
splits on the operator it finds first, so `KEY=~GLOB` parses the key as `KEY=`, which
matches nothing.

### Examples

```sh
# only lanes herdr reports as working
behold roster --root /tmp/behold-fix --filter 'H-5.value.status=working'

# every lane that is not working (glob negation, no '=' sign)
behold roster --root /tmp/behold-fix --filter 'H-5.value.status!~w*'

# lanes whose context percentage string starts with a 1
behold roster --root /tmp/behold-fix --filter 'T-3.value~1*'

# only lanes with a verified identity
behold roster --root /tmp/behold-fix --filter 'identity.state=verified'

# repeat the flag to AND the conditions together
behold roster --root /tmp/behold-fix --filter 'H-5.value.status=working' \
                              --filter 'admitted=true'

# sort by context usage, highest first, then by lane key
behold roster --root /tmp/behold-fix --sort 'T-3.value:desc' --sort 'key'
```

A filter that matches nothing is **not** an error. The result is an empty lane list, which
is visible as `lanes.total: 0` in the JSON and as `_no lanes matched_` in the Markdown.

Sorting is a stable multi-key sort. Numbers sort numerically, text sorts case-insensitively,
and **missing or unknown values always sort last, in both directions**: the unknown
partition is never reversed. The default sort key is `key` (the pane id).

---

## Safety boundaries

Both mechanisms are real and both are tested.

### 1. Deny before read (`behold/guard.py`, `Policy`)

* Held workspace `w2` and reserved tab / pane `wE:t19` are refused **before** that lane's
  process, session or state path is touched. The refusal reason is a stable code:
  `held_workspace:w2`, `reserved_tab:wE:t19`, `reserved_pane:wE:t19`.
* Denied path markers (`/secrets/`, `/.ssh/`, `/auth.json`, `/.credentials/`, `/keyring`)
  are refused at the single read funnel every adapter must use.
* A held lane produces **no value at all**, not even its snapshot label or status. The
  handles that name the refusal are what remain.
* The lane-record directory is the one pre-admission listing, and it is opened one candidate
  file at a time, by pane-matched lookup only. Denied records are discarded on sight and
  their session paths are never opened.

The audit hook, not an mtime comparison, is the boundary.

### 2. Fail-closed read-only and network guard (`guard.enforce()`)

A CPython audit hook refuses:

* any `open` with write intent (`w`, `a`, `x`, `+`, or `O_WRONLY` / `O_RDWR` / `O_CREAT` /
  `O_TRUNC` / `O_APPEND`),
* any filesystem mutation (`os.remove`, `os.rename`, `os.mkdir`, `os.symlink`,
  `shutil.rmtree`, ...),
* any network operation (`socket.connect`, `urllib.Request`, `http.client.connect`, ...),
* any spawn event (`subprocess.Popen`, `os.posix_spawn`, `os.exec*`, `os.system`). There is
  **no allowlist**, because behold has no legitimate child.

There is **no write exception**, not even for output.

### 3. Ownership is witness agreement

A validated pin *alone* is `pin_only_unverified` and not trusted. Trust requires the pin,
the pane-matched lane record and the `/proc` pid triple to agree, with no disagreement, and
the process tuple either verified or explicitly unrecorded. A disagreement is untrusted: no
beads join, no profile resolution, no instance resolution.

### 4. Global state is read by handle, not by scanning

`global.M-4` is given the instance names already established from admitted and verified
lanes and constructs one path per name. It never lists the instances root, so a held or
foreign instance's `pi-profile-state.json` is never opened. A full-roster negative test
plants such files and asserts the attempted-open list is empty, with a trusted positive
control, so "nothing opened" cannot mean "the reader never ran".

### What the guard does not cover

The audit hook covers the audit events CPython itself emits. It is **not** an OS-level
sandbox, and it cannot constrain a program that was started before the hook was installed.
Since V3 removed all external execution, there is no child to constrain, and the hook
refuses the attempt as defence in depth.

---

## Known limitations

These are limits of the design, stated so nobody has to discover them the hard way.

**Content that will never be in the output.**

* No message bodies, prompt bodies, skill bodies, TODO subjects, cron prompts, bead
  descriptions or notes, room bodies or receipts.
* Bead **titles** and dagr run **titles** are withheld even though the plan placed them at
  privacy 1, because this tranche is restricted to counts and paths only. Re-enabling them
  is a separate, reviewed decision, not a flag flip.
* No tool arguments, no environment values other than the single allowlisted `PI_PROFILE`
  key.

**Proof that does not exist.**

* `E-1` cannot prove which extensions were loaded. An inert extension registers no tool, so
  the tool list is a lower bound, not an inventory.
* `T-8` (TTFT) is `unknown` in every lane, forever, in this tranche.
* `J-1` and `J-2` are last-observed, not running states. `J-3` has no registry to read.
* `M-7` (rooms presence and inbox depth) is deferred to P3.
* `P-4`'s leaf is `DISK_RECONSTRUCTED`. pi does not persist the selected leaf, so the
  runtime branch cannot be proven from disk.
* `M-2` cannot re-check a composed mode definition; it reports `unverifiable` rather than
  a false drift.

**Repository fields.**

* `R-1`, `R-2`, `R-3`, `R-4` and `R-6` are `unknown(repo-adapter-not-isolated)` in every
  lane. The `--git` and `--jj` opt-ins that an earlier draft described **no longer
  exist**: the adapters were removed because a child process is not contained by an
  in-process audit hook and repository config can make a read-only git argv run a helper
  writer. `--herdr` is refused for the same reason.
* `R-5` detects a jj workspace by `stat` and reads the snapshot's bookmark token. It never
  runs jj, and it says so in its `note`.

**Target versus measured.**

* `behold.budget_targets` is a set of **targets**, and the document says so in its own
  `note` field: `"targets, not measured whole-fleet proof"`. They are measured on
  synthetic fixtures only (see [Tests](#tests)). Nothing here has been validated against a
  live 61-lane fleet.
* `T-1`, `T-3`, `T-4` and `T-5` are derived. Equivalence with pi's own footer is an open
  gate, not a proven fact.

**Trust and attribution.**

* The active branch is `DISK_RECONSTRUCTED`, so per-branch sums exclude abandoned
  branches by design.
* The beads join requires exact metadata. A lane whose beads lack
  `metadata.agent_pane` and `metadata.agent_session` will show zero, with the rejections
  counted.
* A lane whose identity is untrusted gets no profile, no instance and no beads join. That
  is the intended behaviour, not a bug.

**Operational.**

* `--herdr` is refused. A live snapshot read needs a herdr child process, and this tranche
  has no external execution. Capture the snapshot to a file and pass `--snapshot FILE`.
* `--live` points at the real stores and reads private data. It has not been exercised
  against a live fleet.
* `--as-of` cannot be combined with `--watch`: a watched document has to age.
* The host `/proc` is never read unless `--root` or `--proc-root` names a tree.
* `--filter` and `--sort` compare as strings. There is no numeric comparison operator.
* Only `identity.state` and `identity.session_id` are reachable from the flattened key
  space. `identity.trusted` is not.
* For a lane with no validated session, every path-derived field is `unknown` with the
  reason `no validated session: <identity state>`, except the always-withheld class-2
  fields `C-2` and `B-2`.

---

## Troubleshooting

Every error the tool can print, and what to do about it.

| Message | Exit | Cause and fix |
|---|---|---|
| `behold: no snapshot: pass --snapshot FILE (captured/fixture) or --herdr (explicit live read)` | 3 | No input. Give `--snapshot FILE`, or `--root DIR` for a fixture tree |
| `behold: snapshot not found: /path` | 3 | The path does not exist. Check the path, or use `--root DIR`, where the snapshot is expected at `DIR/herdr/snapshot.json` |
| `behold: snapshot unreadable: JSONDecodeError` | 3 | The file is not JSON. It is probably a log or a truncated capture |
| `behold: snapshot has no integer protocol field; refusing to guess` | 3 | Not a herdr snapshot document. `behold` will not guess the format |
| `behold: unsupported herdr protocol 21; supported: [22]` | 3 | The snapshot is from another herdr protocol version. Capture a protocol-22 snapshot |
| `behold: --herdr needs a herdr child process, and P1/P2 has no external execution; capture the snapshot to a file and pass --snapshot FILE` | 3 | You asked for a live read. Capture the snapshot externally and pass `--snapshot FILE` |
| `behold: filter 'H-5.value.status' needs one of = != ~ !~` | 2 | The filter expression has no operator. Use `H-5.value.status=working` |
| `behold: --as-of is a single-run override and cannot be combined with --watch (a watched document must age)` | 2 | Drop one of the two flags |
| `behold: error: unrecognized arguments: --include-todo-subjects` | 2 | Unknown flag. There is no private-export flag, by design |
| `behold: read-only guard refused an action: ...` | 4 | Something tried to write or spawn inside the process. This is the guard working; it is a defect in an adapter, not in your command |
| `behold: network guard refused an action: ...` | 4 | A socket or URL fetch was attempted. Same as above |
| `behold: denied read: ...` | 4 | A denied path marker was reached. The read was refused before it happened |

**Common non-errors.**

* *Everything is `unknown`.* The lane has no validated session. Look at
  `identity.state` and `identity.untrusted_because` first: the usual causes are a stale
  herdr pin after a `/new` or `/resume`, a pid that no longer matches, or a lane whose
  process has exited.
* *Every field is `held`.* The lane is in a held workspace or a reserved tab or pane. That
  is the deny policy working. `--deny-workspace` and `--deny-pane` only ever add to the
  list, never remove from it.
* *`T-3` is `unknown`.* Either `T-1` (no assistant usage on the active branch) or `T-2`
  (no `contextWindow` for the physical model in the catalogue) is unknown. The reason
  field says which. `behold` will not assume a default window.
* *`B-1` is `unknown` with `identity_untrusted:...`.* The identity witnesses disagreed, so
  the join refused. Check `identity.disagreements`.
* *The Markdown table shows long `unknown: ...` strings.* The summary columns show the
  reason when there is no value. Use `--full` or `--lane` for the per-field section.
* *A filter returns nothing.* The expression may be parsing differently from what you
  meant. In particular the glob operator takes no `=`: `KEY~GLOB`, not `KEY=~GLOB`. A filter
  that matches nothing is not an error; it is an empty lane list.
* *`watch` prints one document and stops.* That is correct. `behold` re-renders only when an
  input actually changed or a process exited, up to `--watch-iterations` renders or
  `--watch-max-seconds`.

---

## Tests

The suite is offline, standard library only, and needs no network, no git, no jj and no
herdr. It needs a POSIX shell, `coreutils` and `python3`.

```sh
tests/run-tests.sh                 # fixtures + 178 tests, about 8 s
tests/run-tests.sh --lanes 8       # a smaller synthetic fleet (the generator never
                                   # emits fewer than 16 lanes)
tests/run-tests.sh --keep          # keep the sandbox for inspection
```

Suites and their sizes:

| Suite | Tests | Covers |
|---|---|---|
| `test_acceptance` | 51 | fields, identity, active branch, honesty, privacy |
| `test_v3_residuals` | 28 | the independent review's remaining expectations, including the global-handle probe |
| `test_units` | 25 | leaf semantics, damaged JSONL, rotation, mode digest |
| `test_guard` | 23 | read-only / network / deny / no-service scans, fixture-tree immutability |
| `test_si_regressions` | 20 | the defects the fleet lead found |
| `test_render` | 17 | JSON and Markdown, filter and sort, no progress claims |
| `test_watch` | 8 | bounded invalidation, rotation, process exit, events-only semantics |
| `test_bench` | 6 | measured p50/p95 against the budget targets |
| **Total** | **178** | |

The bench suite prints real numbers. Measured here on a synthetic 61-lane fixture fleet:

| Measurement | p50 | p95 | Target |
|---|---|---|---|
| snapshot load | 0.16 ms | 0.18 ms | ≤ 40 ms |
| single lane | 1.97 ms | 2.29 ms | ≤ 80 ms |
| multi-MB session parse (4.43 MB) | 29.88 ms | 34.85 ms | ≤ 120 ms |
| warm roster, 61 lanes (no child) | 108.28 ms | 121.04 ms | ≤ 250 ms |
| full roster (no child) | 113.64 ms | 117.72 ms | ≤ 1500 ms |

These are synthetic-fixture numbers. They are **not** a measured whole-fleet proof, and
the document says the same thing in `budget_targets.note`.

---

## Layout

```
bin/behold                  entry point (stdlib only)
behold/cli.py               argument parsing, the run, exit codes
behold/field.py             the Field type: state / class / source / method / age / reason
behold/guard.py             pre-read deny policy + the audit-hook read-only and network guard
behold/identity.py          pin + pane-matched lane record + the /proc cross-check
behold/session.py           JSONL tree, active-branch chain, derived aggregates
behold/procfs.py            pid triple, allowlisted environment read
behold/lane.py              one lane record: every operator field id
behold/render.py            JSON and Markdown, filter and sort, budget targets
behold/watch.py             bounded re-derive on input change (no daemon)
behold/util.py              time, JSONL and path helpers
behold/sources/__init__.py  the Paths object and the source-error type
behold/sources/herdr.py     the snapshot adapter
behold/sources/pi_state.py  profile, mode, settings, model catalogue, todo mirror
behold/sources/fleet_state.py rooms, crons, dagr, beads, background-job logs
behold/sources/repo.py      repository detection by stat (no child process)
fixtures/make_fixtures.py   the synthetic fleet generator
tests/                      the eight suites above
FIELD-LEDGER.md             per-field source, state and remaining gate
```

---

## Status

**V4.** This is the FT-21 P1+P2 foundation: a single-process, no-daemon, no-database CLI
that derives a fleet roster from stores that already exist, on demand, with every value
carrying its class, source, observation time and reason.

The V4 change repaired the one binding residual the V3 review reopened: the global `M-4`
reader now derives its handles from admitted and verified lanes instead of listing the
instances root, so a held or foreign instance's `pi-profile-state.json` is never opened. A
full-roster negative test plants such files and asserts the attempted-open list is empty,
with a trusted positive control, so "nothing opened" cannot mean "the reader never ran".

V3 removed capability rather than disclosing it: there is **no external execution at all**,
repo-derived fields are typed `unknown(repo-adapter-not-isolated)`, held workspace and
reserved tab and pane are denied before any read, an ownership disagreement blocks every
preload and join, the active branch is labelled `DISK_RECONSTRUCTED` rather than "current",
and a composed mode definition is `unverifiable` instead of false drift.

**Not installed, not published, not propagated, not bootstrapped, no live read.** The
`--live` path has not been exercised against a real fleet, and the remaining gates are
listed in `FIELD-LEDGER.md`: the live-fleet read, the live beads join, footer equivalence
for the derived token fields, the P3 runtime assist for the six runtime-only items, the
publication of a packaged install artifact and the fleet skill propagation.
