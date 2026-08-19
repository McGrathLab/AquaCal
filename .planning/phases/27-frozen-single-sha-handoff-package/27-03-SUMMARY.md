---
phase: 27-frozen-single-sha-handoff-package
plan: 03
subsystem: experiment-suite-gates
tags: [smoke-profile, gates, expectations-manifest, D-20, D-24]
requires:
  - experiments/suite_expectations.json (the expectation manifest)
  - experiments/_expectations.py (PROFILES, check_completeness -- the profile-aware shape)
  - experiments/results_smoke (the preserved 26-10 acceptance tree; gitignored, read-only)
provides:
  - a truthful `smoke` profile: the gate roll-up exits 0 over the preserved smoke tree
  - profile-aware check_e4 / check_e5 / check_e6 / check_e6_seed_band
  - the D-24 confirmation that Phase 25's outputs are registered with the driver
affects:
  - plan 27-10 (the --smoke pass it owns now has a green baseline to compare against)
  - plan 27-12 (D-05's on-target verification: a Linux-specific red is now visible)
  - plan 27-08 (also edits suite_expectations.json and EXPECTATIONS.md -- edits here are surgical)
tech-stack:
  added: []
  patterns:
    - "keyword-only `profile`, validated against PROFILES, ValueError naming the offender"
    - "a suppressed gate becomes a VISIBLE N/A, never absent"
    - "every manifest tag carries its reason as a file:line"
key-files:
  created: []
  modified:
    - experiments/suite_expectations.json
    - experiments/check_rerun_gates.py
    - tests/unit/test_expectations.py
    - tests/unit/test_rerun_gates.py
decisions:
  - "The relaxation is keyed on ABSENCE only: a present-but-malformed artifact still FAILs at every profile."
  - "E6's gate4_optimality is suppressed UNCONDITIONALLY at smoke, even on a record carrying a good number -- a collapsed solve's optimality is not evidence."
  - "_E6_EXPECTED_CAMERA_VALUES is untouched; the EXPECTATION is profile-dependent, not the constant."
  - "EXPECTATIONS.md did not change: the renderer counts only `full`-profile artifacts, and all three retagged entries stay in `full`."
metrics:
  duration: ~35 min
  completed: 2026-08-19
---

# Phase 27 Plan 03: Make the Smoke Profile Truthful Summary

The `smoke` gate roll-up over the preserved 26-10 tree went from **12 FAIL to 0 FAIL (exit 0)**
without deleting a single assertion: three manifest tags now match what the smoke code paths
actually write, and four checkers learned the profile so a collapsed-scale artifact yields a
visible `N/A` instead of a meaningless FAIL. Profile-free output is **byte-identical**.

## Tasks Completed

| Task | Name | Commit |
| --- | --- | --- |
| 1 | Retag the three smoke-unwritable artifacts (D-20 class 1) | `090244e` |
| 2 (RED) | Failing tests for the profile-aware checkers | `2582ec7` |
| 2 (GREEN) | Thread profile into E4/E5/E6 checkers (D-20 classes 2, 3) | `cd7c658` |
| 3 | Verify and record Phase 25's driver registration (D-24) | this SUMMARY |

## The before/after the plan asked for

Over `C:/Users/tucke/PycharmProjects/AquaCal/experiments/results_smoke` (the gitignored,
preserved 26-10 acceptance tree, read-only):

| Invocation | Before | After | Exit |
| --- | --- | --- | --- |
| `check_rerun_gates.py <tree> --profile smoke` | 71 PASS, 9 N/A, **12 FAIL** | 71 PASS, 18 N/A, **0 FAIL** | 1 -> **0** |
| `check_rerun_gates.py <tree>` (no profile) | 52 PASS, 9 N/A, 9 FAIL | 52 PASS, 9 N/A, 9 FAIL | 1 -> 1 |

The profile-free run's stdout is **byte-identical before and after** (`diff` clean) — the
regression that mattered most.

### Nothing that fails at `full` stopped failing at `full`

- Every FAIL the plan enumerated was converted to `N/A`, not removed. Comparing the pre- and
  post-edit smoke verdict blocks by gate name: **no per-experiment gate name disappeared**, and
  none was added.
- The only three names absent from the smoke block are the completeness gates on the three
  retagged artifacts — that is the manifest's own profile filter
  (`_expectations.py:191-196`) doing its designed job, not a deleted assertion. Confirmed
  directly: `--profile full` over the same tree still emits all three, all FAIL.
- A regression test pins each relaxed case at `profile="full"` and at `profile=None`.

## Task 1 — the three retags (D-20 class 1)

Each retag names the code location that makes it `full`-only, in the manifest's own
`rows_rationale` house style (a changed tag with an unchanged reason is the FIX-06 shape):

| Artifact | Stage | Why no smoke path writes it |
| --- | --- | --- |
| `structural_scaling.csv` | `e3` | `e3_derived_quantities.py:1106-1126` — the `--smoke` branch writes tiers 1-3 and returns without calling `_write_tier4`, this file's only writer |
| `e5_provenance.json` | `e5` | `e5_index_sensitivity.py:871-889` (`_run_smoke_at`) writes `index_sensitivity.csv` and returns; the sidecar write at `:725` is on the full `run_band` path |
| `fd_jacobian_accuracy.json` | `fd_jacobian` | `fd_jacobian_accuracy.py:652-666` (`_run_smoke`) writes the CSV and returns; the sidecar write at `:631` is full-only |

`fd_jacobian_accuracy.csv` **is** written under smoke and stays `["smoke","full"]` — only the
`.json` sidecar moved. The manifest still lists **62 artifacts** and **5** `preflight.overrides`.

Two `TestProfiles` cases now guard the retag (and the CSV's smoke tag) against a silent revert.

## Task 2 — profile threading (D-20 classes 2 and 3)

`check_e4`, `check_e5`, `check_e6` and `check_e6_seed_band` gained a keyword-only
`profile: str | None = None`, validated by a new `_validate_profile` helper that mirrors
`check_completeness`'s shape exactly (raises `ValueError` naming the offender; `None` is always
legal and preserves the strictest behaviour). `run_all_gates` threads it; its docstring now says
so.

| Checker | At `smoke` | Still FAILs at `smoke` |
| --- | --- | --- |
| `check_e4` | absent `benchmark_grid.csv` -> `N/A` on both column gates | a grid that is present but malformed |
| `check_e5` | absent `e5_provenance.json` -> `N/A` on `gate1_guard_count` + `gate3_provenance` | a sidecar that is present but bad |
| `check_e6` | `gate4_optimality` on `e6_configs/*.json` -> `N/A`, still emitted | gates 1 and 3 on the same record are untouched |
| `check_e6_seed_band` | a short `cameras` axis -> `N/A` naming the collapsed scale | an absent `axis`/`axis_value` column pair, at every profile |

Two judgement calls worth recording:

1. **The relaxation is keyed on ABSENCE, not on the profile alone.** E4's and E5's `N/A` fires
   only when the file does not exist. If a smoke run somehow writes a malformed grid or a bad
   sidecar, it still FAILs — a smoke pass cannot launder a corrupt artifact.
2. **E6's gate 4 is suppressed unconditionally at smoke**, even when the collapsed solve happened
   to record a non-null optimality. Gate 4 asks whether the number is *meaningful*, and at smoke
   scale it is not; reading it as evidence would be the weaker gate. The same record still PASSes
   under `full`. A test pins both halves of that.

`_E6_EXPECTED_CAMERA_VALUES = (8, 12, 16)` is untouched (`grep -c` returns 1) — the constant
records that the axis survives P26-D-40, and it still governs at `full`.

## Task 3 — D-24: Phase 25's outputs are registered (ROADMAP criterion 6)

**Verified, not built. No manifest edit was required.** All eight artifacts are present in
`artifacts`, all tagged to the stage that writes them, all `["full"]`:

| Artifact | In manifest? | Stage | Profiles | Conditional | Rule honoured? |
| --- | --- | --- | --- | --- | --- |
| `degenerate_observations.csv` | yes | `e2_production` | `["full"]` | **true** | **yes** — rationale states Phase 25 D-08's rule verbatim ("written ONLY when at least one flagged row exists... absence is PASS, not FAIL"), and warns that a stage-agnostic `len()` double-counts rows flagged in both stage-3 passes |
| `all_observation_depths.csv` | yes | `e2_production` | `["full"]` | **true** | **yes** — rationale ties emission to `internals.log_all_observation_depths` and states absence is PASS |
| `e1_degeneracy_breakdown.json` | yes | `e1` | `["full"]` | false | **yes** — unconditional Phase 24 sidecar, written by `e1_refractive_comparison.py:882` on every full run |
| `e1_seed_band_degeneracy_breakdown.json` | yes | `e1_band` | `["full"]` | false | **yes** — band-owned, keyed by seed |
| `e5_degeneracy_breakdown.json` | yes | `e5` | `["full"]` | false | **yes** — written at `e5_index_sensitivity.py:719` |
| `e5_seed_band_degeneracy_breakdown.json` | yes | `e5_band` | `["full"]` | false | **yes** — written at `:826` |
| `e7_degeneracy_breakdown.json` | yes | `e7` | `["full"]` | false | **yes** — written by `e7_interface_ablation.py`, keyed by arm |
| `e7_seed_band_degeneracy_breakdown.json` | yes | `e7_band` | `["full"]` | false | **yes** — band-owned, keyed by seed then arm |

All eight also appear in their stage's `produces` list, so the driver's per-stage completeness
call sees them. `conditional: true` routes absence to the PASS path at
`_expectations.py:212-222`; the six Phase 24 sidecars are correctly `false` because their
emitters are unconditional.

**The E2 `h_q` flag half of criterion 6 is confirmed.** `E2_INVOCATION_VARIANTS`
(`e2_real_rig.py:931-973`) sets `internals.log_all_observation_depths: true` on the
`classification` variant only; `timing` and `memory` both set it `false`, each with a stated
reason (a flag that perturbs the quantity being measured cannot ride along with it). That is why
`all_observation_depths.csv` is written by exactly one of E2's four invocations, and why the
manifest attaches it to `e2_production` — whose `invocation` uses `${E2_PRODUCTION_CONFIG}` and
whose `description` names the flag explicitly.

**Criterion 6 verdict: already satisfied. No gap found, no entry added.**

## Deviations from Plan

### [Finding, no action] D-20's class 3 is satisfied at the manifest, as the plan predicted

`benchmark_grid.csv` was **already** `["full"]` with its reason in `rows_rationale`. It was left
untouched. Its two residual smoke FAILs came entirely from `check_e4` not being profile-aware,
and Task 2 fixed them there. This confirms the plan's own reading rather than contradicting it.

### [Finding, no action] EXPECTATIONS.md did not move

The plan expected the rendered §7 counts to shift. They did not:
`render_expectation_sheet.py:120` computes `full_artifacts` as those with `"full"` in `profiles`,
and the artifact table renders `rows["full"]` only — so **removing `smoke` from an entry that
keeps `full` changes nothing the sheet renders**. `--write` reported "already up to date" and
`--check` exits 0, which is the acceptance criterion. Recorded because a future manifest edit
that moves an artifact *out of* `full` WILL move the counts, and the `--write`/`--check` pair is
still mandatory after every manifest edit.

### [Rule 1 - Bug] Two of my own RED tests encoded the wrong expectation

Both were corrected during GREEN, and both corrections tightened the assertion:

1. `test_present_but_malformed_grid_still_fails_at_smoke` asserted FAIL on *both* E4 grid gates.
   A grid missing a `status` column is a **pre-existing** record-only `N/A`
   (`_check_status_column:637-644`, plan 19.3-07's harness-gating split), not a FAIL. Rewritten
   as `test_present_but_malformed_grid_is_judged_identically_at_every_profile`, which now asserts
   the same verdicts at `None`, `smoke` and `full` — a stronger claim than the original.
2. `test_good_optimality_still_passes_at_smoke` assumed gate 4 would pass at smoke on a good
   record. The plan specifies `check_optimality=(profile != "smoke")`, i.e. unconditional
   suppression. Rewritten as `test_gate4_is_suppressed_at_smoke_even_on_a_good_record`, asserting
   `N/A` at smoke **and** `PASS` at full on the identical record, with the reasoning in the
   docstring.

No production behaviour changed as a result; the plan's `<behavior>` block was the authority in
both cases.

### [Startup] The worktree forked from a stale base

`git merge-base` returned `d27bda7`, not the required `4f6e1f5`. Corrected by the mandated
`git reset --hard` before any work. This is the known phase-26 failure mode firing again.

## Verification

Targeted, per the parallel-execution constraint — the full suite is the orchestrator's post-merge
gate:

```
python -m pytest tests/unit/test_expectations.py tests/unit/test_rerun_gates.py -q
  -> 186 passed
python -m experiments.render_expectation_sheet --check    -> exit 0
python experiments/check_rerun_gates.py <preserved smoke tree> --profile smoke -> exit 0, 0 FAIL
grep -c '_E6_EXPECTED_CAMERA_VALUES = (8, 12, 16)' experiments/check_rerun_gates.py -> 1
```

Interpreter: `~/anaconda3/envs/AquaCal/python.exe` with `PYTHONPATH=$(pwd)/src`, so the worktree
tested its own source and not `main`'s.

## Known Stubs

None.

## Threat Flags

None. This plan touched JSON, Markdown and Python in a local scientific pipeline — no network
surface, no secrets, no new trust boundary (T-27-03-03 was dispositioned `accept` for exactly
this reason).

Both mitigated threats hold:

- **T-27-03-01 (tampering with gate assertions):** verified by gate-name-set comparison across
  the pre/post smoke verdict blocks, by the byte-identical profile-free output, and by a
  `profile="full"` / `profile=None` regression test on every relaxed case.
- **T-27-03-02 (manifest edits without reasons):** each of the three retags carries a
  `file:line` rationale, and `test_smoke_unwritable_artifacts_are_full_only` asserts the
  rationale is present, not just the tag.

## Handoff Notes

- **For 27-08 (also edits `suite_expectations.json` / `EXPECTATIONS.md`):** the edits here are
  three `profiles` arrays and three `rows_rationale` strings. `EXPECTATIONS.md` is unchanged,
  so there is no generated-region conflict to resolve — but run `--write` then `--check` after
  your own manifest edit regardless.
- **For 27-10 / 27-12:** `--profile smoke` is now a clean signal. Any FAIL from the on-target
  smoke pass is new, and therefore Linux-specific. That is the whole point of D-20.
- Two smoke reductions remain **declared, not fixed** (D-21): `e7_focal_standoff` and
  `e4_repeat` are never rehearsed under `--smoke`. The handoff note owes that statement.

## Self-Check: PASSED

All five modified/created files exist on disk; all three task commits (`090244e`, `2582ec7`,
`cd7c658`) are present in `git log`. STATE.md and ROADMAP.md were not touched — the orchestrator
owns those writes.
