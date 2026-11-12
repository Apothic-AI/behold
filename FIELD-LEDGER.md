# FT-21 field ledger — every operator field, its state in this tranche, and its remaining gate

**V4.** Repairs the reopened binding residual: the global `M-4` reader no longer lists the
instances root or opens a held/foreign instance's state file — allowed handles are derived from
admitted+verified lanes first (see `V4` in `README.md` and the mutant probe receipt). Accuracy
corrections: the inert `--jj`/`--stash-count` flags are **removed**; the audit-hook claim is
narrowed to the CPython spawn event family (including `os.posix_spawn`, not `subprocess.Popen`
alone) with no OS-sandbox claim; the suite is genuinely git-free (fixtures no longer run git),
needing only a POSIX shell, coreutils and python3; per-suite counts corrected; performance is
reported as a **target, not validated**.

**V3.** Defensive simplification after the independent review rejected V2 `616a3540`: the
git/jj/herdr adapters are **removed** (typed `repo-adapter-not-isolated`), externals are not
opt-in-able, held/reserved **tab** topology is denied before any read, an ownership
disagreement blocks every preload/join, the leaf is labelled `DISK_RECONSTRUCTED`, and a
composed mode definition is `unverifiable` rather than false drift.

**Identity count (corrected).** There are **57 unique field ids** in this ledger: **56
per-lane** ids plus `M-4`, which is global-only and never a lane field. The earlier
"58 / 51 emitted / 5 unknown / 4 P3 / 6 withheld" figures were an overlapping set of
observations, not a partition, and are withdrawn. Per-lane states in one run depend on the
lane (a held lane has 56 held fields; a verified lane has values), so the only stable counts
are the id counts and per-state tallies printed in `behold.lanes.by_field_state`.

**V2.** Prior repairs after SI rejected `f8d01da`: externals (git/jj/herdr) are opt-in because a
child process is not covered by the in-process guard; there is no writable output path; held
and reserved lanes render no value at all; a process/reporter/pil disagreement is UNTRUSTED
and is never joined on; the instance comes only from the verified process's
`PI_CODING_AGENT_DIR`; and beads session metadata must match exactly.

Companion to `README.md` and to `/home/bitnom/.local/state/ft21-plan/result.md` §4.
Field ids are the plan's. "State here" is what the committed code actually emits for the
synthetic fixture fleet; "gate" is what is still needed before the value is true of a live
fleet or before the field may be published wider.

Legend — state: **A** authoritative read · **D** derived with a method · **I** inferred
(labelled) · **LO** last-observed · **U** explicitly unknown (reason given) · **W** withheld
(class 2) · **H** held before read · **P3** deferred to the runtime-assist phase.

Privacy: 0 public metadata · 1 operator-sensitive (counts/paths only) · 2 never emitted.

## herdr layer

| # | Field | Output key | Priv | State here | Source / method | Gate |
|---|---|---|---|---|---|---|
| H-1 | workspace name | `H-1` | 0 | A / absent | `snapshot workspaces[].label` | live snapshot read |
| H-2 | workspace id | `H-2` | 0 | A | `workspaces[].workspace_id` | — |
| H-3 | pane id | `H-3` | 0 | A | `agents[].pane_id` | — |
| H-4 | pane name + winning layer | `H-4` (`note` = layer) | 0 | A / absent | tab label → agent name → display_agent → pane label → terminal title | live check of the precedence chain |
| H-5 | status + seq + failure states | `H-5` | 0 | A | `panes/agents[].agent_status`, `state_change_seq`, `completion_seq`, `interactive_ready`, `restore_error`; `done` kept verbatim | — |
| H-6 | cwd vs foreground_cwd | `H-6` | 0 | A / divergent | `agents[].cwd`, `foreground_cwd` | — |

## pi session / model

| # | Field | Output key | Priv | State here | Source / method | Gate |
|---|---|---|---|---|---|---|
| P-1 | provider (selected + physical) | `P-1` | 0 | A / divergent | `model_change.provider` vs last assistant `provider` | live virtual-model lanes |
| P-2 | model (selected + physical) | `P-2` | 0 | A / divergent | `model_change.modelId` vs last assistant `model` | — |
| P-3 | reasoning effort | `P-3` | 0 | A | `thinking_level_change`, else assistant `thinkingLevel` | — |
| P-4 | session id + validated leaf/chain | `P-4` | 0 | A | header `id` vs filename UUID; leaf + `chain_state` + counts | — |
| P-5 | session path (realpath + spellings) | `P-5` | 0 | A | `agent_session` pin or pane-matched pil record, realpath-normalized | — |
| P-6 | session start | `P-6` | 0 | A | header `timestamp` | — |
| P-7 | session duration | `P-7` | 0 | D | `observed_now - header.timestamp` (live) or `last_entry - header` (frozen); method states which | — |
| P-8 | last observed turn span | `P-8` | 0 | D | last user → last assistant/user timestamp; labelled "last observed", never "running" | live cross-check against a real turn |
| P-9 | session name | `P-9` | 1 | A / absent | latest `session_info.name` | — |
| P-10 | fork lineage | `P-10` | 1 | A / absent | header `parentSession` (path only) | — |

## tokens / context / performance

| # | Field | Output key | Priv | State here | Source / method | Gate |
|---|---|---|---|---|---|---|
| T-1 | context used | `T-1` | 0 | D | last assistant `usage.input+output+cacheRead+cacheWrite` | exact footer equivalence (see note) |
| T-2 | context max | `T-2` | 0 | A / U | `models-store.json` `contextWindow` for the **physical** model; unknown if absent (never assume 200k) | live catalogue check |
| T-3 | context % | `T-3` | 0 | D / U | `T-1 / T-2 * 100`; unknown if either side unknown | exact footer equivalence |
| T-4 | session tokens | `T-4` | 0 | D | Σ assistant usage + `usage` entries + compaction/branch-summary usage **on the active branch**; `usage_kinds` shown; a branch-blind total is reported in `note` when it differs | compare with pi footer on a live lane |
| T-5 | cache counts + rate | `T-5` | 0 | D | `ΣcacheRead`, `ΣcacheWrite`, `cacheRead/(cacheRead+input)` as ratio and % | compare with footer |
| T-6 | cost (estimated flag) | `T-6` | 1 | D / absent | Σ `usage.cost`; `estimated: true` when any `totalFromProvider` is false | provider-reported totals |
| T-7 | TPS | `T-7` | 0 | D / U | Σ output / Σ `durationMs` over last 20 assistant messages; unknown when no `durationMs` (legacy) | validate against stream timings |
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
| R-1 | git branch + oid | `R-1` | 0 | A / **U by default** | exact argv `git --no-optional-locks status --porcelain=v2 --branch`; **off unless `--git`** (a git child is not covered by the guard) | live git with `--git` |
| R-2 | worktree identity | `R-2` | 0 | A / divergent / **U by default** | herdr `worktree` vs exact argv `git rev-parse --show-toplevel --git-common-dir` | same |
| R-3 | dirty counts | `R-3` | 0 | A / **U by default** | porcelain v2 XY line counts | same |
| R-4 | ahead/behind/stash | `R-4` | 0 | A / **U by default** | `branch.ab`; stash count only with `--stash-count` | same |
| R-5 | jj detected | `R-5` | 0 | A / absent / expired | `.jj` presence + `tokens.jj_bookmark` (TTL-aware); needs no jj binary | — |
| R-6 | jj bookmark/change/status | `R-6` | 0 | A / **U** / error | opt-in `--jj` only, exact argv, always `--ignore-working-copy`; a missing jj binary is a per-field error | live jj workspace, opt-in; never run mid-operation |
| R-7 | non-repo lane | `R-7` | 0 | A | `.git`/`.jj` presence → `NO_REPO` | — |

No fleet-wide jj claim is made: jj is opt-in per run, and a working copy is never snapshotted
by a roster read (the argv allowlist rejects any jj command without the flag).

## mode / profile / rooms / goals / todos / crons

| # | Field | Output key | Priv | State here | Source / method | Gate |
|---|---|---|---|---|---|---|
| M-1 | active mode + metadata | `M-1` | 1 | A / absent | session `custom pi-mode-state.v3`; definition path/digest/scope/label only, no prompt body | — |
| M-2 | mode drift | `M-2` | 1 | A / U | digest recomputed with pi-modes' own `modeDefinitionFingerprint` (replicated byte-for-byte); `unverifiable` when the path/scope cannot be reconstructed | confirm equality on a live project mode |
| M-3 | profile with provenance | `M-3` | 1 | A / U | **declared** = the single allowlisted env key `PI_PROFILE` (process-start, may be stale after `/profile`); **selected** = per-instance `pi-profile.json` `{profile, source}` where the instance comes **only** from the verified process's `PI_CODING_AGENT_DIR`; **resolved** = saved skills/tool references; catalog label. No env value other than that one profile name is emitted | never conflated; `/profile` staleness surfaced as a note |
| M-4 | global activeProfile | `global.M-4` (**not a lane field**) | 1 | A / conflict / unknown | `pi-profile-state.json` read **only** from instances already established by admitted+verified lanes; the instances root is never listed, and a held/foreign instance's copy is never opened. Disagreeing *allowed* copies ⇒ `conflict`; no admitted+verified instance ⇒ `unknown(noaccess)` | live read (not implemented); the deny lists cover only `w2`/`wE:t19` |
| M-5 | rooms lane name | `M-5` | 0 | A / absent | `rooms/names.json` `pins["pane:<id>"]` | — |
| M-6 | rooms membership | `M-6` | 1 | A / U | `registry/` count + `rooms/*` membership, **names only** | — |
| M-7 | presence / inbox depth | `M-7` | 1 | **U** (P3) | deferred by the plan to P3 | P3 |
| G-1 | goals count + statuses | `G-1` | 1 | A / U | per-session goal `custom` entry, structured counts only; a text-only store ⇒ `unknown(withheld)` | confirm the live goal entry's shape |
| G-2 | goals queue depth | `G-2` | 1 | A / U | same entry, depth only | same |
| D-1 | TODO counts + conflict | `D-1` | 1 | A / conflict | session `pi-core-todo-state` (active branch) vs instance `pi-todo-state.json` for the same session UUID | — |
| D-2 | TODO subjects | `D-2` | 2 | **W** | never exported; no opt-in flag exists | — |
| C-1 | crons for the lane | `C-1` | 1 | A / U | `tasks.json` filtered by `projectDir`; `id`/`name`/`schedule` only; prompt fields counted as skipped | live cron file |
| C-2 | cron prompt | `C-2` | 2 | **W** | never read into output | — |

## extensions / skills / prompts

| # | Field | Output key | Priv | State here | Source / method | Gate |
|---|---|---|---|---|---|---|
| E-1 | extensions loaded | `E-1` | 0 | **I** | session system-message replay (`toolsAdded`/`toolsRemoved`, skills section); limitation text states that inert extensions are invisible | **P3 exact** via `pi.getAllTools().sourceInfo` |
| E-2 | installed package pins | `E-2` | 0 | A / absent | `settings.json` package entries (name + ref) | — |
| S-1 | skills loaded | `S-1` | 0 | A / conflict | skills section names+paths, cross-checked against `pi-profile.json resolved.skills` | — |
| S-2 | skill text | `S-2` | 2 | **W** | never emitted | — |
| S-3 | prompts (configured vs loaded) | `S-3` | 0 | A | configured prompt paths from settings + loaded section **names**; `loaded_is_not_proof_of_bodies: true` | — |
| S-4 | prompt text | `S-4` | 2 | **W** | never emitted | — |

## monitors / background jobs

| # | Field | Output key | Priv | State here | Source / method | Gate |
|---|---|---|---|---|---|---|
| J-1 | background tasks | `J-1` | 1 | **LO** | session `bash_bg` calls + `pi-bg/*.log` size/mtime; explicitly "not a running state" | P3 live |
| J-2 | monitors set | `J-2` | 1 | **LO** | session `monitor` tool calls; exit state unknowable | P3 live |
| J-3 | bizzy monitors | `J-3` | 1 | **U** | `bizzy.json` holds only `disabledTools` | P3 live |

## dagr / beads

| # | Field | Output key | Priv | State here | Source / method | Gate |
|---|---|---|---|---|---|---|
| G-3 | dagr runs for the lane | `G-3` | 1 | A / absent | `recent` index → `run.json` matched on `orchestrator.pane` or any `attempts[].locator.pane`; task state counts by owner; run **title withheld** | live dagr tree |
| G-4 | dagr staleness | `G-4` | 1 | A | `observed_at - generated_at`, and `stale` when a run event is newer than `generated_at` | — |
| B-1 | beads for the lane | `B-1` | 1 | A / U | **explicit metadata join**: `metadata.agent_pane` + `metadata.agent_session`, where the session value must match the validated id **exactly** (no suffix, no path containment) and the identity must be *trusted* (a pid/reporter/pil disagreement refuses the join). `owner`, `project:` label and prompt-text bead ids are counted as **rejected**. Labels scope the project only | live `bd` export; requires the metadata keys to be set at task creation |
| B-2 | bead description/notes | `B-2` | 2 | **W** | never emitted; titles also withheld (see below) | — |

**Stricter-than-plan choices (documented, deliberate).** Bead *titles* and dagr *run titles*
are withheld (`title_withheld: class1_free_text`) although the plan put them at privacy 1,
because the binding correction restricts this tranche to "counts and paths only". Monitor
descriptions are likewise not emitted. Re-enabling any of them is a separate, reviewed
decision — not a flag flip.

## Coverage audit

Id counts: 56 per-lane ids + 1 global-only id (`M-4`) = **57 unique**. The table below counts
operator fields, which is a different number from ids and is stated separately.

| Family | Operator fields | Emitted here | Explicitly unknown | Deferred (P3) | Withheld (class 2) |
|---|---|---|---|---|---|
| herdr | 6 | 6 | — | — | — |
| pi model/session | 10 | 10 | — | — | — |
| tokens/context/perf | 8 | 7 | T-8 | T-8 (live only) | — |
| repo (git/jj) | 7 | 6 (+R-6 opt-in) | R-6 without `--jj` | — | — |
| mode/profile/rooms/goals/todos/crons | 13 | 11 | M-7, G-1/G-2 when text-only | M-7 | D-2, C-2 |
| extensions/skills/prompts | 7 | 5 | E-1 exact | E-1 exact | S-2, S-4 |
| monitors/jobs | 3 | 2 as last-observed | J-3 | J-1/J-2/J-3 live | — |
| dagr/beads | 4 | 4 (titles withheld) | — | — | B-2 (+titles) |
| **Total** | **58** | **51 emitted, 0 silently dropped** | 5 explicit unknowns | 4 | 6 |

No operator field is absent from the output. Every one is either emitted with provenance, or
present as a typed `unknown`/`absent`/`held`/`withheld` with a reason.

## Trust rules (V2)

- A lane is `trusted` only when the reporter pin, the pane-matched pil record and the
  `/proc` pid triple **agree**. A pid disagreement, a workspace/pane disagreement or a
  pin/pil session disagreement makes it untrusted; the roster still shows each witness, but
  no explicit join (beads) and no instance/profile resolution happens on it.
- Held workspace `w2` and reserved pane `wE:t19` produce **no value at all** — not even the
  snapshot label or status. Only the handles that name the refusal are emitted.
- The pil record directory is the one pre-admission listing (lane/pane/pid/session-path
  metadata, never session or env content); denied records are discarded on sight and their
  session paths are never opened.

## Remaining gates (each is a separate authorization)

1. **SI source review of this tree** — nothing here is installed, published or propagated.
2. **Live-fleet read** — a first run against a real snapshot (`--herdr`) with the deny
   policy on; measure the §8.3 budgets on a real 61-lane fleet. Budgets here are targets,
   measured only on synthetic fixtures. Note `--herdr` and `--git` spawn children that the
   in-process guard does **not** sandbox; a real-fleet run should be preceded by an explicit
   readonly sandbox decision for children, or accept them as read-only by argv construction.
3. **Beads live join** — `bd list --json` is a subprocess; this tranche reads a synthetic
   export. Live use needs an explicit `bd` allowlist entry and a decision on export scope.
4. **Footer equivalence** (T-1/T-3/T-4/T-5) — compare with pi's footer on lanes known to
   have compaction/branch summaries before claiming equivalence.
5. **P3 runtime assist** — TTFT, live job/monitor state, exact extension attribution,
   rooms presence depth; a *new* extension beside herdr's, never a duplicate reporter, and
   its own approval gate.
6. **Behold bootstrap** — the one-shot first commit into `~/Code/behold` (see `TRANSFER.md`).
7. **Publication / install** — no npm publish, no PATH install, no remote.
8. **P4 propagation** — the `behold-roster` skill belongs in the existing fleet-skills repo
   manifest (`kind = repo`), plus one `home/AGENTS.md` row; deferred, and it must document
   only the shipped CLI. No static roster, no live AGENTS edit in this tranche.
9. **jq/`--as-of` convenience and SQLite cache** — only if measurement at 60+ lanes on a
   real fleet fails the budget; nothing in this tranche writes a cache.
