# FT-21 field ledger — every operator field, its state in this tranche, and its remaining gate

**Ledger revision V5 · code under test `behold 0.1.0-p1p2` (tree status V4).**

This revision aligns the ledger with the code that actually ships and with `README.md`:

* the `--git`, `--jj` and `--stash-count` opt-ins that earlier revisions described **no
  longer exist** — the git/jj/herdr adapters were removed in V3 and **no flag re-enables
  them**; `argparse` rejects those names with exit code 2;
* the coverage tally is re-derived from `behold/lane.py::_ALL_FIELD_KEYS` and
  `behold/render.py::field_order()` instead of a hand-kept count;
* the remaining gates name the gates the **shipped CLI** implies — the CLI *refuses*
  `--herdr`, so a live snapshot is captured to a file out of band and passed as
  `--snapshot FILE`;
* every "state here" cell below was read off a real run of the shipped code over the
  shipped **synthetic** fixture fleet. That is offline, synthetic evidence. **Nothing here
  has been measured against a live fleet**, and no live measurement is claimed.

**V4 (code).** Repairs the reopened binding residual: the global `M-4` reader no longer
lists the instances root or opens a held/foreign instance's state file — allowed handles
are derived from admitted+verified lanes first (see `V4` in `README.md` and the mutant
probe receipt).

**V3 (code).** The git/jj/herdr adapters are **removed** (typed
`repo-adapter-not-isolated`), externals are not opt-in-able, held/reserved **tab**
topology is denied before any read, an ownership disagreement blocks every preload/join,
the leaf is labelled `DISK_RECONSTRUCTED`, and a composed mode definition is
`unverifiable` rather than false drift.

## Evidence base for the "state here" cells

| Item | Value |
|---|---|
| Fixture fleet | `python3 fixtures/make_fixtures.py /tmp/behold-ledger-fix --lanes 61` → "fixtures at /tmp/behold-ledger-fix with 61 lanes" (exit 0) |
| Derivation | `./bin/behold roster --root /tmp/behold-ledger-fix --as-of 2026-11-11T03:00:00Z` (exit 0, 61 lanes) |
| Field coverage | every one of the 61 lanes carries **exactly the same 56 field ids**; one id-set, 56 ids, no lane missing a field |
| Denied lanes | 3 lanes are `held` before any read (held workspace `w2`, reserved tab / pane `wE:t19`), so 58 lanes are admitted; `behold.privacy.denials` = `held_workspace:w2 1, reserved_pane:wE:t19 1, reserved_tab:wE:t19 1` |
| External execution | `behold.guard.spawns` = `{}` — no child process was spawned during the run; `behold.guard.open_attempts` = 489 admitted reads |
| Per-field states | `behold.lanes.by_field_state` = `absent 594, conflict 1, divergent 2, held 168, inferred 57, present 1492, stale 114, unknown 701, withheld 287` |
| Suite | `tests/run-tests.sh` → `Ran 178 tests in 9.081s` / `OK` / `PASSED` (exit 0) |

"State here" therefore means **what the committed code emits for the synthetic fixture
fleet**. It is not a statement about a live fleet. A live fleet can produce different
states per lane (`absent`, `conflict`, `divergent`, `stale`, `error`, `held`); the only
counts that are stable across runs are the **id counts** and the per-state tallies printed
in `behold.lanes.by_field_state`.

## Identity count (re-derived, not hand-kept)

There are **57 unique field ids** in this ledger: **56 per-lane** ids plus `M-4`, which is
global-only and never a lane field. The two code-side lists agree exactly and are the
source of truth:

* `behold/lane.py::_ALL_FIELD_KEYS` — the 56 ids a lane must carry;
* `behold/render.py::field_order()` — the same 56 ids, in render order;
* `behold/cli.py` `Runner.document()` — emits `global["M-4"]` **once**, outside the lane
  list.

The earlier "58 / 51 emitted / 5 unknown / 4 P3 / 6 withheld" figures were an overlapping
set of observations, not a partition, and are withdrawn. They are replaced by the
[coverage audit](#coverage-audit), whose partition is exact.

## What the shipped CLI accepts

Verified against the shipped parser (`./bin/behold roster --help`) and by running the
rejected names. This table is the CLI's real surface, not an aspiration.

| Option | Shipped behaviour | Verified |
|---|---|---|
| `--snapshot FILE` | reads **one** file; with no `--root` and no `--live` the host `/proc`, the pil records and the agent dir are never opened | exit 0 on a fixture snapshot |
| `--root DIR` | fixture/data root containing `herdr/`, `proc/`, `pil/`, `instances/`, `state/` | exit 0 |
| `--live` | real store paths; **still needs `--snapshot`** because `--herdr` is refused | exit 3 without `--snapshot` |
| `--herdr` | **refused**, exit 3: `behold: --herdr needs a herdr child process, and P1/P2 has no external execution; capture the snapshot to a file and pass --snapshot FILE` | exit 3 |
| `--markdown`, `--full`, `--lane`, `--filter`, `--sort` | as documented in `README.md` | exit 0 |
| `--proc-root`, `--as-of`, `--watch`, `--watch-iterations`, `--watch-interval`, `--watch-max-seconds`, `--events-file`, `--verbose` | as documented in `README.md`; `--as-of` with `--watch` is refused (exit 2) | exit 0 / 2 |
| `--deny-workspace`, `--deny-pane` | only ever **add** to the fixed deny lists (`w2`, `wE:t19`) | exit 0 |
| `--git` | **does not exist** — `behold: error: unrecognized arguments: --git` | exit 2 |
| `--jj` | **does not exist** — `behold: error: unrecognized arguments: --jj` | exit 2 |
| `--stash-count` | **does not exist** — `behold: error: unrecognized arguments: --stash-count` | exit 2 |
| `--output` | **does not exist** — `behold: error: unrecognized arguments: --output` | exit 2 |

There is no `--include-todo-subjects` or any other private-export flag, by design: the
tool has no write path and no free-text export.

Companion to `README.md` and to `/home/bitnom/.local/state/ft21-plan/result.md` §4.
Field ids are the plan's. "State here" is what the committed code actually emits for the
synthetic fixture fleet; "gate" is what is still needed before the value is true of a live
fleet or before the field may be published wider.

Legend — state: **A** authoritative read · **D** derived with a method · **I** inferred
(labelled) · **LO** last-observed · **U** explicitly unknown (reason given) · **W** withheld
(class 2) · **H** held before read · **P3** deferred to the runtime-assist phase.
`divergent`, `conflict`, `absent`, `stale` and `error` are also emitted states; they are
listed beside the letter where they are reachable.

Privacy: 0 public metadata · 1 operator-sensitive (counts/paths only) · 2 never emitted.

## herdr layer

| # | Field | Output key | Priv | State here | Source / method | Gate |
|---|---|---|---|---|---|---|
| H-1 | workspace name | `H-1` | 0 | A / absent | `snapshot workspaces[].label` | live snapshot read |
| H-2 | workspace id | `H-2` | 0 | A | `snapshot workspaces[].workspace_id` | — |
| H-3 | pane id | `H-3` | 0 | A | `snapshot agents[].pane_id` | — |
| H-4 | pane name + winning layer | `H-4` (`note` = `winning layer: <layer>`) | 0 | A / absent | `tabs[].label` → `agents[].name` → `display_agent` → `panes[].label` → `terminal_title_stripped` | live check of the precedence chain |
| H-5 | status + seq + failure states | `H-5` | 0 | A | `panes[].agent_status` else `agents[].agent_status`; `state_change_seq`, `completion_seq`, `interactive_ready`, `restore_error`; `done` kept verbatim | — |
| H-6 | cwd vs foreground_cwd | `H-6` | 0 | A / divergent | `snapshot agents[].cwd`, `foreground_cwd` | — |

All six come from the one snapshot read the whole roster is built on. A denied lane
carries none of them: a held lane emits **no** snapshot label, status or cwd.

## pi session / model

| # | Field | Output key | Priv | State here | Source / method | Gate |
|---|---|---|---|---|---|---|
| P-1 | provider (selected + physical) | `P-1` | 0 | A / divergent | `model_change.provider` vs last assistant `provider` | live virtual-model lanes |
| P-2 | model (selected + physical) | `P-2` | 0 | A / divergent | `model_change.modelId` vs last assistant `model` | — |
| P-3 | reasoning effort | `P-3` | 0 | A / absent | `thinking_level_change`, else assistant `thinkingLevel` | — |
| P-4 | session id + validated leaf/chain | `P-4` | 0 | A | header `id` vs filename UUID; leaf + `chain_state` + counts; `leaf_authority: DISK_RECONSTRUCTED`, `runtime_leaf: null` | — |
| P-5 | session path (realpath + spellings) | `P-5` | 0 | A | `agent_session` pin or pane-matched pil record, realpath-normalized | — |
| P-6 | session start | `P-6` | 0 | A / absent | header `timestamp` | — |
| P-7 | session duration | `P-7` | 0 | D | `observed_now - header.timestamp` (lane process present) or `last_entry_timestamp - header.timestamp` (frozen); the `method` states which | — |
| P-8 | last observed turn span | `P-8` | 0 | D / absent | last user → last assistant/user timestamp; labelled "last observed", never "running" | live cross-check against a real turn |
| P-9 | session name | `P-9` | 1 | A / absent | latest `session_info.name` | — |
| P-10 | fork lineage | `P-10` | 1 | A / absent | header `parentSession` (path only) | — |

`P-4`'s leaf is a **disk reconstruction**, not proof of the runtime-selected branch: pi
keeps the selected leaf in memory, so the field says `DISK_RECONSTRUCTED` and carries
`runtime_leaf: null` rather than calling the branch current.

## tokens / context / performance

| # | Field | Output key | Priv | State here | Source / method | Gate |
|---|---|---|---|---|---|---|
| T-1 | context used | `T-1` | 0 | D | last assistant `usage.totalTokens`, else `input+output+cacheRead+cacheWrite` | exact footer equivalence (see note) |
| T-2 | context max | `T-2` | 0 | A / U | `models-store.json` `contextWindow` for the **physical** model; unknown if absent (never assume 200k) | live catalogue check |
| T-3 | context % | `T-3` | 0 | D / U | `T-1 / T-2 * 100`; unknown if either side unknown | exact footer equivalence |
| T-4 | session tokens | `T-4` | 0 | D | Σ assistant usage + `usage` entries + compaction/branch-summary usage **on the active branch**; `usage_kinds` shown; a branch-blind total is reported in `note` when it differs | compare with pi footer on a live lane |
| T-5 | cache counts + rate | `T-5` | 0 | D / absent | `ΣcacheRead`, `ΣcacheWrite`, hit rate as ratio and % | compare with footer |
| T-6 | cost (estimated flag) | `T-6` | 1 | D / absent | Σ `usage.cost`; `estimated: true` when any `totalFromProvider` is false | provider-reported totals |
| T-7 | TPS | `T-7` | 0 | D / U | Σ output / Σ `durationMs` over the last 20 assistant messages that carry a duration; unknown when none do (legacy session) | validate against stream timings |
| T-8 | TTFT | `T-8` | 0 | **U** | `unknown(reason: pi persists total durationMs, not time-to-first-token)` | **P3 only**, separately reviewed |

**Honesty note (binding correction #4).** T-1/T-3/T-4/T-5 are *derived* and the plan's
claim of exact footer equivalence is **not** proven by this tranche: pi may add estimates or
compaction adjustments that raw usage sums do not reproduce. The fields carry their method
string so the comparison is mechanical, and "footer equivalence" stays an open gate. P-8 is
the last observed span, not the current active turn duration. T-7 is derived from persisted
per-message durations, not a live stream rate.

## repo state

| # | Field | Output key | Priv | State here | Source / method | Gate |
|---|---|---|---|---|---|---|
| R-1 | git branch + oid | `R-1` | 0 | **U** (always) | `unknown(repo-adapter-not-isolated)`; source `git branch + oid: adapter removed in V3`; note: requires a separately reviewed isolated execution boundary | a reviewed isolated execution boundary — **there is no `--git` flag** |
| R-2 | worktree identity | `R-2` | 0 | **U** (always) | herdr's `workspaces[].worktree` half only; `unknown(repo-adapter-not-isolated)` when a worktree is reported, `unknown(no worktree record and no git adapter)` otherwise | same |
| R-3 | dirty counts | `R-3` | 0 | **U** (always) | `unknown(repo-adapter-not-isolated)`; source `git dirty counts: adapter removed in V3` | same |
| R-4 | ahead/behind/stash | `R-4` | 0 | **U** (always) | `unknown(repo-adapter-not-isolated)`; source `git ahead/behind/stash: adapter removed in V3` | same — **there is no `--stash-count` flag** |
| R-5 | jj detected | `R-5` | 0 | A / absent / expired | `.jj` presence by `stat` plus `tokens.jj_bookmark` (TTL-aware); **no jj binary is ever run**; note: detection only | — |
| R-6 | jj bookmark/change/status | `R-6` | 0 | **U** (always) | `unknown(repo-adapter-not-isolated)`; source `jj bookmark/change/status: adapter removed in V3` | same — **there is no `--jj` flag** |
| R-7 | non-repo lane | `R-7` | 0 | A | `.git`/`.jj` presence by `stat` → `NO_REPO` / `git` / `jj` / `git+jj`; note: absence of a repository is an expected state, not an error | — |

The git and jj adapters were **removed** in V3, not gated behind a flag: a child process is
not contained by the in-process audit hook, and repository config can make even a
read-only `git` argv run a helper writer. `R-1`, `R-2`, `R-3`, `R-4` and `R-6` are
therefore `unknown` in **every** lane, with the stable reason
`repo-adapter-not-isolated`. Re-enabling them is a capability decision with its own
review, **not** a flag flip — and today `argparse` rejects `--git`, `--jj` and
`--stash-count` outright (exit 2). Detection by `stat` (`R-5`, `R-7`) is pure and stays.

## mode / profile / rooms / goals / todos / crons

| # | Field | Output key | Priv | State here | Source / method | Gate |
|---|---|---|---|---|---|---|
| M-1 | active mode + metadata | `M-1` | 1 | A / absent | session `custom pi-mode-state.v3`; definition path/digest/scope/label only, no prompt body | — |
| M-2 | mode drift | `M-2` | 1 | A / U | digest recomputed with pi-modes' own `modeDefinitionFingerprint` (replicated byte-for-byte); a **project-scope** (composed) definition is `unverifiable` (`composed_definition_unsupported`), never false drift; `matched` / `drift` / `partial` / `unverifiable` are the reported sub-states | needs the pi-modes loader to recompose a project definition, or an owner-side digest comparison |
| M-3 | profile with provenance | `M-3` | 1 | A / U | **declared** = the single allowlisted env key `PI_PROFILE` (process-start, may be stale after `/profile`); **selected** = per-instance `pi-profile.json` `{profile, source}` where the instance comes **only** from the verified process's `PI_CODING_AGENT_DIR`; **resolved** = saved skills/tool references; catalog label. No env value other than that one profile name is emitted | never conflated; `/profile` staleness surfaced as a note |
| M-4 | global activeProfile | `global.M-4` (**not a lane field**) | 1 | A / conflict / unknown | `pi-profile-state.json` read **only** from instances already established by admitted+verified lanes; the instances root is never listed, and a held/foreign instance's copy is never opened. Disagreeing *allowed* copies ⇒ `conflict`; no admitted+verified instance ⇒ `unknown(noaccess)` | live read (never exercised); the deny lists cover only `w2`/`wE:t19` |
| M-5 | rooms lane name | `M-5` | 0 | A / absent | `rooms/names.json` `pins["pane:<id>"]` | — |
| M-6 | rooms membership | `M-6` | 1 | A / U | `registry/` count + `rooms/*` membership, **names only** | — |
| M-7 | presence / inbox depth | `M-7` | 1 | **U** (always) | deferred by the plan to P3 | P3 |
| G-1 | goals count + statuses | `G-1` | 1 | A / absent / U | per-session goal `custom` entry, structured counts only; a text-only store ⇒ `unknown(goal state is text-only; count withheld)` | confirm the live goal entry's shape |
| G-2 | goals queue depth | `G-2` | 1 | A / absent / U | same entry, depth only | same |
| D-1 | TODO counts + conflict | `D-1` | 1 | A / conflict / absent | session `pi-core-todo-state` (active branch) vs instance `pi-todo-state.json` for the same session UUID | — |
| D-2 | TODO subjects | `D-2` | 2 | **W** | never exported; no opt-in flag exists | — |
| C-1 | crons for the lane | `C-1` | 1 | A / U | `tasks.json` filtered by `projectDir`; `id`/`name`/`projectDir`/`schedule`/`cron`/`kind` only; a task's `prompt` field is counted as skipped, never read into output | live cron file |
| C-2 | cron prompt | `C-2` | 2 | **W** | never read into output | — |

## extensions / skills / prompts

| # | Field | Output key | Priv | State here | Source / method | Gate |
|---|---|---|---|---|---|---|
| E-1 | extensions loaded | `E-1` | 0 | **I** (always) | session system-message replay (`toolsAdded`/`toolsRemoved`, skills section); the field's own `reason` states that an inert extension registers no tool, so the tool list cannot prove the inventory | **P3 exact** via loader/registration evidence, not the tool list |
| E-2 | installed package pins | `E-2` | 0 | A / absent | `settings.json` package entries (name + ref, plus the settings path it came from); the agent dir's and the instance's `settings.json` are both candidates | — |
| S-1 | skills loaded | `S-1` | 0 | A / conflict / absent | skills section names+paths, cross-checked against `pi-profile.json resolved.skills` | — |
| S-2 | skill text | `S-2` | 2 | **W** | never emitted | — |
| S-3 | prompts (configured vs loaded) | `S-3` | 0 | A | configured prompt paths from settings + loaded section **names**; `loaded_is_not_proof_of_bodies: true` | — |
| S-4 | prompt text | `S-4` | 2 | **W** | never emitted | — |

`E-2` is what is *configured*, which is not the same thing as what is *loaded*. `E-1` is
the weakest field in the ledger and says so in its own `reason`.

## monitors / background jobs

| # | Field | Output key | Priv | State here | Source / method | Gate |
|---|---|---|---|---|---|---|
| J-1 | background tasks | `J-1` | 1 | **LO** | session `bash_bg` calls + `pi-bg/*.log` size/mtime; explicitly "not a running state" | P3 live |
| J-2 | monitors set | `J-2` | 1 | **LO** | session `monitor` tool calls; exit state unknowable | P3 live |
| J-3 | bizzy monitors | `J-3` | 1 | **U** (always) | `bizzy.json` holds only `disabledTools`; there is no persistable monitor registry | P3 live |

## dagr / beads

| # | Field | Output key | Priv | State here | Source / method | Gate |
|---|---|---|---|---|---|---|
| G-3 | dagr runs for the lane | `G-3` | 1 | A / absent / U | `recent` index → `run.json` matched on `orchestrator.pane` or any `attempts[].locator.pane`; task state counts by owner; run **title withheld**; task states are reported as recorded, never as progress | live dagr tree |
| G-4 | dagr staleness | `G-4` | 1 | A / absent / U | `observed_at - generated_at`, and `stale` when a run event is newer than `generated_at` | — |
| B-1 | beads for the lane | `B-1` | 1 | A / U | **explicit metadata join**: `metadata.agent_pane` + `metadata.agent_session`, where the session value must match the validated id **exactly** (no suffix, no path containment) and the identity must be *trusted* (a pid/reporter/pil disagreement refuses the join). `owner`, `project:` label and prompt-text bead ids are counted as **rejected**. Labels scope the project only | live `bd` export; requires the metadata keys to be set at task creation |
| B-2 | bead description/notes | `B-2` | 2 | **W** | never emitted; titles also withheld (see below) | — |

**Stricter-than-plan choices (documented, deliberate).** Bead *titles* and dagr *run
titles* are withheld (`title_withheld: class1_free_text`) although the plan put them at
privacy 1, because the binding correction restricts this tranche to "counts and paths only".
Monitor descriptions are likewise not emitted. Re-enabling any of them is a separate,
reviewed decision — not a flag flip.

## Coverage audit

The partition below is exact and re-derivable from the code, not hand-kept. "Lane ids" are
the ids a lane's `fields` map must contain (`behold/lane.py::_ALL_FIELD_KEYS`, 56 ids);
`M-4` is the single global id and is **not** a lane id, so the two id counts are stated
separately and never mixed.

| Family | Lane ids | Always `unknown` | Always `withheld` (class 2) | Runtime-only / deferred | Carries a value under normal conditions |
|---|---|---|---|---|---|
| H herdr | 6 | — | — | — | `H-1` `H-2` `H-3` `H-4` `H-5` `H-6` (6) |
| P pi session / model | 10 | — | — | — | `P-1` `P-2` `P-3` `P-4` `P-5` `P-6` `P-7` `P-8` `P-9` `P-10` (10) |
| T tokens / context / perf | 8 | `T-8` | — | `T-8` | `T-1` `T-2` `T-3` `T-4` `T-5` `T-6` `T-7` (7) |
| R repository | 7 | `R-1` `R-2` `R-3` `R-4` `R-6` | — | — | `R-5` `R-7` (2) |
| M mode / profile / rooms | 6 | `M-7` | — | `M-7` | `M-1` `M-2` `M-3` `M-5` `M-6` (5) |
| G goals / dagr | 4 | — | — | — | `G-1` `G-2` `G-3` `G-4` (4) |
| D TODOs | 2 | — | `D-2` | — | `D-1` (1) |
| C crons | 2 | — | `C-2` | — | `C-1` (1) |
| E extensions | 2 | — | — | `E-1` (exact list) | `E-1` `E-2` (2) |
| S skills / prompts | 4 | — | `S-2` `S-4` | — | `S-1` `S-3` (2) |
| J monitors / jobs | 3 | `J-3` | — | `J-1` `J-2` `J-3` | `J-1` `J-2` (2, last-observed only) |
| B beads | 2 | — | `B-2` | — | `B-1` (1) |
| **Total (lane ids)** | **56** | **8** | **5** | **6 items** | **43** |

* **56 lane ids + 1 global-only id (`M-4`) = 57 unique ids.** `M-4` appears in the
  `global` block, never in a lane's `fields`.
* **43 + 8 + 5 = 56.** The three columns partition the lane ids with nothing left over.
* The **6 runtime-only items** are exactly `behold.runtime_only_pending`: `T-8`, `J-1`,
  `J-2`, `J-3`, `E-1` (exact list) and `M-7`.
* No operator field is absent from the output. Every one is either emitted with
  provenance, or present as a typed `unknown`/`absent`/`held`/`withheld`/`conflict`/
  `divergent`/`stale`/`error` with a reason.
* **Discrepancy to flag for the owner (not changed here).** `README.md`'s coverage table
  prints **45** in the "Emitted with a value" total, while its own family rows sum to
  **43** — the same 43 this ledger states, since its 8 always-unknown and 5
  always-withheld rows are correct. `README.md` is out of scope for this revision, so the
  arithmetic slip is recorded here rather than silently propagated or silently fixed.

## Trust rules (V4)

- A lane is `trusted` only when the reporter pin, the pane-matched pil record and the
  `/proc` pid triple **agree**. A pid disagreement, a workspace/pane disagreement, a
  boot-id or starttime mismatch, or a pin/pil session disagreement makes it untrusted; the
  roster still shows each witness, but no explicit join (beads) and no instance or
  profile resolution happens on it. A pin alone is `pin_only_unverified` and is **not**
  trusted.
- Held workspace `w2` and reserved tab / pane `wE:t19` produce **no value at all** — not
  even the snapshot label or status. The reason is a stable code
  (`held_workspace:w2` / `reserved_tab:wE:t19` / `reserved_pane:wE:t19`). Only the
  handles that name the refusal are emitted.
- The pil record directory is the one pre-admission listing (lane/pane/pid/session-path
  metadata, never session or env content); denied records are discarded on sight and their
  session paths are never opened.
- `global.M-4` is derived from **admitted + verified** lanes only. The instances root is
  never listed, so a held or foreign instance's `pi-profile-state.json` is never opened.

## Remaining gates (each is a separate authorization)

1. **SI source review of this tree** — nothing here is installed, published or propagated.
2. **Live-fleet read** — the shipped CLI has **no live-discovery path**: `--herdr` is
   refused (exit 3), so the operator captures a protocol-22 herdr snapshot to a file out of
   band and passes `--snapshot FILE` (with `--live` for the real store paths). The first
   run against a real fleet must then measure the budget targets on that fleet; the
   numbers in `README.md` and in `behold.budget_targets` are **targets measured on
   synthetic fixtures only** and are explicitly "not a measured whole-fleet proof".
   `--live` reads real private stores and has never been exercised against a live fleet.
3. **Repository fields (R-1, R-2, R-3, R-4, R-6)** — these need a separately reviewed
   isolated execution boundary. There is no opt-in flag today (`--git`, `--jj` and
   `--stash-count` are rejected by `argparse`), so this gate is a capability decision, not
   a configuration one.
4. **Beads live join** — `bd list --json` is a subprocess; this tranche reads a synthetic
   export (`Paths.for_live()` leaves the beads path unset). Live use needs an explicit
   isolated-execution decision and a decision on export scope.
5. **Footer equivalence** (T-1/T-3/T-4/T-5) — compare with pi's footer on lanes known to
   have compaction/branch summaries before claiming equivalence.
6. **P3 runtime assist** — TTFT, live job/monitor state, exact extension attribution,
   rooms presence depth: a *new* extension beside herdr's, never a duplicate reporter, and
   its own approval gate.
7. **Manifest re-stamping** — `MANIFEST.sha256` records the transferred bytes of
   `FIELD-LEDGER.md`. This revision changes that file, so its manifest line no longer
   verifies (all other lines still do). The manifest is out of scope for this revision and
   was deliberately left untouched; re-stamping it is a separate, authorized operation.
8. **Publication / install** — no npm publish and no PATH install; the tree ships no
   packaging metadata, so `pip install` is not an option (see `README.md` §Install). The
   `behold-roster` fleet skill and its `home/AGENTS.md` row are a separate, deferred
   propagation step that must document only the shipped CLI.
9. **jq / `--as-of` convenience and SQLite cache** — only if measurement at 60+ lanes on a
   real fleet fails the budget; nothing in this tranche writes a cache.
