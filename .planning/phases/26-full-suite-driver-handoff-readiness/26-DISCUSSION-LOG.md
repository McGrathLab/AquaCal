# Phase 26: Full-Suite Driver & Handoff Readiness - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-18
**Phase:** 26-full-suite-driver-handoff-readiness
**Areas discussed:** Completeness gate class, Expectation sheet form, Inherited stages, E2 preflight
& data, Manifest & version truth, Driver safety rails, Archive & purge boundary, Phase 26
acceptance, plus a residuals round

---

## Completeness gate class

| Option | Description | Selected |
|--------|-------------|----------|
| Sticky non-zero exit | Never abort mid-queue; sticky flag makes the driver's final exit non-zero with a loud terminal summary | ✓ |
| Abort on completeness | Missing artifact aborts the queue immediately | |
| Abort only for downstream-coupled | Abort only when the missing artifact feeds a later stage | |

| Option | Description | Selected |
|--------|-------------|----------|
| Pre-flight, before stage 1 | Preconditions asserted cheaply before any hours are spent | ✓ |
| After each stage | Stage N's own artifacts and row counts at the existing gate invocation point | ✓ |
| End-of-run roll-up | One final pass over the whole tree — the check whose absence produced F-001 | ✓ |

| Option | Description | Selected |
|--------|-------------|----------|
| New gate in `check_rerun_gates.py` | One tool owns "was this run good" | ✓ |
| Separate `check_suite_completeness.py` | Separate tools for content vs existence gates | |
| You decide | Coupled to the Area 2 outcome | |

**User's choice:** Sticky non-zero exit; all three timings; gate inside `check_rerun_gates.py`.
**Notes:** Framing raised during discussion — the project's actual injury has never been "we kept
running after a gate failed" but "a run exited 0 and looked green while a band CSV was never
produced." Derived without asking: **pre-flight failure aborts**, since nothing is lost before
stage 1; recorded as D-03 with the instruction to state both halves together in the driver header.

---

## Expectation sheet form

| Option | Description | Selected |
|--------|-------------|----------|
| Machine-readable manifest, prose rendered from it | One declarative source; the hand-verification sheet is generated | ✓ |
| Prose sheet primary, gate list by hand | Markdown is primary, gate list is a Python constant | |
| Gate constant primary, no prose sheet | The Python table IS the sheet | |

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit run profiles | Expectations per profile; the gate asserts only that profile's numbers | ✓ |
| Derivations, not literals | Row counts as expressions over declared axes | |
| Both — derivations, profiles select axes | Strictly more work; catches both a forgotten `--seeds` and a wrong axis set | |

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — a test that fails on unregistered artifacts | Cross-reference declared column constants against the manifest | ✓ |
| No — document the obligation | Written rule in the driver header and each todo | |
| You decide | | |

| Option | Description | Selected |
|--------|-------------|----------|
| `smoke` + `full` | Two profiles only | ✓ |
| `smoke` + `full` + `probe` | Adds a reduced-axis probe profile | |
| `full` only, smoke checked loosely | One profile of record | |

| Option | Description | Selected |
|--------|-------------|----------|
| Committed and regenerated, with an up-to-date test | Reviewable in a diff | ✓ |
| Committed but hand-refreshed | | |
| Render on demand | | |

**User's choice:** manifest is the source of truth; explicit `smoke`/`full` profiles; a coupling
test that fails on unregistered artifacts; rendered sheet committed and tested.
**Notes:** The binding constraint surfaced here is Phase 25's D-21 — a gate asserting 640/960 rows
or requiring `noise_std` in `experiments/results/` would fail every run until Phase 28. Profiles are
what make the gate runnable in the phase that writes it. The coupling test was flagged as the
single highest-leverage item in the phase for Phases 28–30, since the registration obligation has
already failed twice (Phases 24 and 25 each hand-appended a `## Phase N additions` section
retroactively).

---

## Inherited stages

| Option | Description | Selected |
|--------|-------------|----------|
| ON for `full`, off by default | Determinism gets fresh evidence at the frozen sha; ~107 min cost | ✓ |
| OFF — determinism keeps its old citation | Saves 1.8 h; the number stays attributed to the 2026-08-02 run | |
| Defer to Phase 28 launch | Decide under time pressure at launch | |

| Option | Description | Selected |
|--------|-------------|----------|
| Keep E3's `--check` first, and re-document why | Same code, honest reason | ✓ |
| Keep it unchanged | Inherits a rationale that is no longer operative | |
| Drop the `--check` invocation | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit `--baseline-dir`, driver points it at the archive | Makes the comparison basis inspectable in the invocation | ✓ |
| Copy baselines into a read-only snapshot | Fewer code changes, third copy of the data | |
| Run the comparisons post-run, outside the driver | | |

**User's choice:** `e6_repeat2` ON for `full` / off by default; keep E3's ordering with a rewritten
rationale; explicit `--baseline-dir`.
**Notes:** Two findings surfaced during this area. (1) DRIVER-03's own table says `--check` survives
meaningfully on **E3 and E2 only** — so E3's `--check` is not merely a pre-regeneration snapshot,
it is one of the suite's two surviving reproduction signals; its justification changed but its value
went up. (2) An unflagged interaction: DRIVER-04 moves `experiments/results/` aside, and that
directory *is* where the committed baselines live — moving it silently breaks both E3's tier diff
and E2's ~1e-8 control unless a baseline path is threaded through.

---

## E2 preflight & data

| Option | Description | Selected |
|--------|-------------|----------|
| Hard-fail unless the skip is DECLARED | `--skip-e2` makes the omission explicit and gate-visible | ✓ |
| Skip with a loud announcement, always | The todo's literal preference | |
| Hard-fail, no escape hatch | Gives up the "a reviewer can run this" property | |

| Option | Description | Selected |
|--------|-------------|----------|
| Classification run only — never the timing run | Same logic that splits timing from memory | ✓ |
| Production run, accept the timing effect | | |
| A dedicated fifth E2 invocation | Another 48–87 min pass | |

| Option | Description | Selected |
|--------|-------------|----------|
| Identity — assert the known frameset counts | Catches the wrong-archive case at minute zero | ✓ |
| Checksum the archive | Strongest; costs minutes per pre-flight | |
| Presence only | | |

**User's choice:** declared-skip hard-fail; `log_all_observation_depths` on the classification run
only; frameset identity, not presence.
**Notes:** Argument made for identity over presence — E2's ~1e-8 reproduction only means anything
if the fresh run reads the same frames, and this project has already shipped a frameset mix-up
(FIX-06's "60 → 12 → 1,817" against the verified "262 → 52 → 7,762"). A presence check passes
cleanly on the wrong archive and yields a control that reads red for an unguessable reason.

---

## Manifest & version truth

| Option | Description | Selected |
|--------|-------------|----------|
| `git describe` is the anchor; installed version renamed | Cannot collide across commits | ✓ |
| Resolve from installed distribution and label it | The todo's first option | |
| Drop `aquacal_version` entirely | The todo's second option | |

| Option | Description | Selected |
|--------|-------------|----------|
| Python emitter, invoked once at pre-flight | Importable by the coupling test; survives a mid-run crash | ✓ |
| Python emitter, written at end of run | A crashed run leaves no manifest | |
| Both — pre-flight then amended | Manifest becomes mutable mid-run | |

| Option | Description | Selected |
|--------|-------------|----------|
| Present, complete, sha-agreeing, clean tree — all hard FAIL | | ✓ |
| Same, but dirty-tree is a warning | | |
| Presence and sha agreement only | | |

**User's choice:** `git describe --tags --long --dirty` as the anchor; Python emitter at pre-flight;
Gate 3 extended with all-hard-FAIL semantics.
**Notes:** Correction to the todo's framing raised here — resolving `aquacal_version` from the
installed distribution does **not** fix F-002 for a source checkout, because an editable install
reports the last *built* version (`2.0.1` for every post-tag commit), which is the identical defect.
Consequence recorded: with a pre-flight-only manifest, end-of-run timing stays recoverable from
`*_state.tsv`, which already stamps ISO start and completion per stage.

---

## Driver safety rails

| Option | Description | Selected |
|--------|-------------|----------|
| Sha-derived state path + explicit HEAD check | Makes the stale-state class impossible *and* detected | ✓ |
| Single renamed state file + HEAD refusal | The todo's literal prescription | |
| Sha-derived path only | No loud message on a silent fresh start | |

| Option | Description | Selected |
|--------|-------------|----------|
| Dirty working tree | | ✓ |
| Non-empty output tree with no matching state file | Phrased so a genuine resume proceeds | ✓ |
| Frameset absent / identity mismatch | | ✓ |
| Insufficient disk headroom | | ✓ |

| Option | Description | Selected |
|--------|-------------|----------|
| `run_suite.sh` | The todo's own suggestion | |
| `run_experiment_suite.sh` | Disambiguates from pytest, which "the suite" means in every CLAUDE.md warning | ✓ |
| You decide | | |

**User's choice:** sha-derived state path plus HEAD check; all four refusals including disk
headroom; `run_experiment_suite.sh`.
**Notes:** Structural point raised before the question — refusals must not break resume, so the
non-empty-tree refusal has to be phrased as "non-empty **with no matching state file for this
sha**", or the first crash bricks the recovery path the driver was built around.

---

## Archive & purge boundary

| Option | Description | Selected |
|--------|-------------|----------|
| Committed step in Phase 26, right after the pre-run tag | The frozen sha ships in the correct starting state | ✓ |
| Driver does it automatically at pre-flight | Contradicts the no-tree-mutation guarantee | |
| Committed step plus a driver `--archive-existing` helper | Two paths to the same state | |

| Option | Description | Selected |
|--------|-------------|----------|
| All six tracked results trees | | ✓ |
| The loose stale driver state/logs too | | ✓ |
| The untracked `verify_23*/` probe trees | Local hygiene, not a reviewable commit | ✓ |

| Option | Description | Selected |
|--------|-------------|----------|
| Phase 26 moves only; purge is Phase 30 / POST-03 | Matches the roadmap's phase mapping | ✓ |
| Purge in Phase 29 once gates pass | | |
| Phase 26 also writes the purge checklist | | |

**User's choice:** committed move after the tag; all six tracked trees plus the loose state/logs
plus the untracked probe trees; purge stays in Phase 30.
**Notes:** Scouted before asking — six tracked output directories (~42 MB), three untracked
`verify_23*/` trees at ~12 MB each, and an existing `experiments/archive/` (31 tracked files) the
new directory name must not collide with. Sequencing argument recorded: a committed move means the
frozen sha itself carries an empty `results/` and a populated archive, so the Linux checkout arrives
correct and `--baseline-dir` resolves at that sha.

---

## Phase 26 acceptance

| Option | Description | Selected |
|--------|-------------|----------|
| One full `--smoke` pass, end to end | Real invocations, real gates, real manifest at the `smoke` profile | ✓ |
| Extend the dry-run harness over all new stages | Sequencing, resume, sticky-exit, failure paths | ✓ |
| Unit tests over stage list, manifest and expectations | Runs in CI forever | ✓ |
| A partial real run of the two cheapest stages | Writes real artifacts into a tree meant to start empty | |

| Option | Description | Selected |
|--------|-------------|----------|
| Phase 27 / RUN-01 | Linux-side verification is the freeze phase's stated job | ✓ |
| Phase 26 also does a Linux smoke | | |
| You decide | | |

| Option | Description | Selected |
|--------|-------------|----------|
| In scope, rendered from the stage list | | |
| In scope, hand-written | Keeps the prose natural | ✓ |
| Out of scope — defer to Phase 27 | | |

**User's choice:** all three acceptance forms; Linux smoke belongs to Phase 27; README §2 rewritten
by hand.
**Notes:** Verified before asking that **every** experiment has a `--smoke` path — including E2
(visible SKIPPED when the dataset is absent) and all three orphan scripts — so a full-suite smoke
pass is executable rather than aspirational. CLAUDE.md constraint attached: that pass is the
orchestrator's run, never an executor's.

---

## Residuals round

| Option | Description | Selected |
|--------|-------------|----------|
| Yes to both — budget is a deliverable, shortest-first holds | | ✓ |
| Budget as a deliverable, re-order by criticality | Abandons the fast-failure property | |
| No budget — size it in Phase 28 | | |

| Option | Description | Selected |
|--------|-------------|----------|
| `pre-rerun-baseline` | The todo's own suggested name | ✓ |
| `v2.1-prerun-baseline` | | |
| You decide | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Record as MF-NN in MANUSCRIPT-FINDINGS.md | | ✓ |
| Record it, and pass `--include-per-camera-latex` anyway | | |
| Out of scope — do not record | | |

**User's choice:** wall-clock budget is a deliverable and shortest-first holds; tag is
`pre-rerun-baseline`; the `tab:cpr` finding is recorded as MF-NN.
**Notes:** The `--include-per-camera-latex` question was answered from the manuscript rather than
asked — `tab:cpr` at `supplement.tex:449` carries six shared-interface rows and the generated
`cpr_grouping.tex` is not `\input` anywhere, so the flag stays off. That inspection produced the
hand-transcription finding. Scheduling flag raised: the current queue is ~9 h and the `full` profile
plausibly reaches ~24–30 h against a 2026-08-21 submission from a 2026-08-18 start.

## Claude's Discretion

- Expectation manifest format, location and schema, and how conditional artifacts are expressed.
- The archive directory's exact name (must not collide with `experiments/archive/`).
- Whether `check_rerun_gates.py` is factored before the completeness gate lands in it.
- Stage identifiers and the internal shape of `STAGES=()` under multi-invocation stages.
- Plan decomposition and commit granularity.

## Deferred Ideas

- Rewriting the driver in Python (post-submission).
- The archive purge and its dangling-reference audit (Phase 30 / POST-03).
- Post-run `--check` re-baselining (Phase 29).
- Editing the manuscript to `\input` the generated fragment (manuscript session's call).
- Linux-side portability verification (Phase 27 / RUN-01).
