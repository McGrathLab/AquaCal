# 26-10 SUMMARY — the `--smoke` acceptance pass (D-33 form 1)

**Status:** COMPLETE. Evidence recorded below; no source file changed by this plan.
**Run by:** the orchestrator, per D-34. Never dispatched to an executor.

## Headline

One `--smoke` pass ran **all 20 stages end to end** at sha `88512b7`, over the real stage list,
with real invocations, real per-stage gate calls, a real run manifest and the real end-of-run
completeness roll-up at the `smoke` profile.

**The driver exits non-zero, and that is the correct outcome.** Every remaining failure is a
pre-existing, diagnosed mismatch between the `smoke` profile's expectations and what the smoke code
paths actually write — not a driver defect. The list is enumerated below; none is new.

## Run identity

| | |
|---|---|
| Sha | `88512b7` (`v2.0.1-218-g88512b7`), clean tree |
| Wall clock | 03:22:41 → 03:33:46 UTC, **11 min 05 s** |
| Out dir | `experiments/results_smoke` (never `experiments/results`) |
| State | `experiments/run_experiment_suite_state.88512b7.tsv` |
| Findings | `experiments/run_experiment_suite_state.88512b7.failures.txt` |
| Stage logs | `experiments/run_experiment_suite_state.88512b7.stagelogs/` |
| Environment | Windows 11, Python 3.12.12, numpy 2.4.2, scipy 1.17.0, OpenCV 4.13.0, 20 logical CPUs, 16.9 GB RAM |

All 17 required manifest fields present and non-null; `git_dirty: false`; every artifact carries
the same `git_sha` as the manifest.

## Stage outcomes: 19 of 20 exit 0

The one non-zero is **`reconstruction_bootstrap` (exit 1)** — `FileNotFoundError` on
`experiments/results/real_rig_metrics.json`, a path hardcoded at `reconstruction_bootstrap.py:56`
instead of using `--out`. This is **smoke-only**: in production `OUT_DIR == experiments/results`, so
the file its `depends_on: ["e2_production"]` edge guarantees is exactly where it looks. Deliberately
left out of 26-12's scope and recorded there.

`e3` now exits 0. In the two pre-fix passes it died on `int(NaN)`.

## Roll-up: 71 PASS, 9 N/A, 12 FAIL

Against the pre-fix pass (65 PASS / 18 FAIL), **six FAILs cleared and none appeared.** The six were
exactly `gate3_provenance` on E1's two and E7's four benchmark records — plan 26-13.

The remaining 12, all pre-existing:

| Count | Lines | Cause |
|---|---|---|
| 4 | `structural_scaling.csv`, `e5_provenance.json` (×2 + completeness), `fd_jacobian_accuracy.json` | the `smoke` profile expects artifacts the smoke code paths never write |
| 4 | E6 `gate4_optimality` on four `e6_configs/*.json` | collapsed smoke solve |
| 2 | E4 `benchmark_grid.csv not found` | E4's smoke path writes no grid CSV |
| 1 | E6 `cameras axis missing [12, 16]; found [8]` | collapsed smoke axis |
| 1 | roll-up FAIL (the aggregate of the above) | — |

### The profile mismatch, now precisely located

`structural_scaling.csv` is written by `_write_tier4`, which e3's `--smoke` branch never calls —
it runs tiers 1-3 and returns (`e3_derived_quantities.py:1106-1126`). The manifest nonetheless
lists that artifact under `profiles: ["smoke", "full"]`. Same for `e5_provenance.json` and
`fd_jacobian_accuracy.json`, whose `_run_smoke` paths return before their sidecar writes.

**This corrects a claim made earlier in the session.** The pre-fix passes lost
`structural_scaling.csv` when e3 crashed, and that was read as collateral of the crash. Under
`--smoke` it was never going to be written at all. The crash genuinely does cost that artifact on
the **full** path — which is the case that matters for the frozen run — but the smoke evidence
never showed it.

## What this pass does and does not prove

**Proves:** every stage's invocation line is correct at reduced scale. A mistyped flag or an import
error surfaces in 11 minutes instead of hours into a 22-31 hour run. It also exercised sequencing,
the pooled 4-wide scheduler, per-stage and roll-up gate wiring, the manifest write, and the state
and failure-log rails.

**Does not prove — and this one matters:** it cannot demonstrate 26-12's dependency edge. Under
`--smoke`, `OUT_DIR` is `experiments/results_smoke`, while e3's hardcoded read points at
`experiments/results/benchmark.json` — a path outside the smoke tree that `e2_production` never
writes under smoke. The log still shows `E2 benchmark record not found ... emitting null CPR
metrics`, and e3 exits 0 only because of 26-12's NaN guard. **The ordering fix's evidence is
`test_order_is_topological_over_depends_on` plus the manifest diff, not this pass.**

Also unproven by design: `--smoke` cannot catch a wrong `--config` path or a bad production YAML.
Pre-flight's frameset-identity check covers that.

Two stages are skipped rather than reduced, as documented: `e7_focal_standoff` (no `--smoke`, reads
a hardcoded path) and `e4_repeat` (`--cell` and `--splice-repeat` both refuse `--smoke`). Both were
announced as DECLARED REDUCTIONs.

## Run history

Three passes were needed; the first two are preserved for comparison.

1. **19:12 EDT** — killed at 19:20 when the machine bugchecked (`0x10E`
   VIDEO_MEMORY_MANAGEMENT_INTERNAL, unrelated to the suite; the box has a standing GPU-driver
   instability). 13 of 20 stages reached. Preserved at `scratchpad/smoke-crashed-1912/`.
2. **20:42 EDT** — completed all 20 stages, 11 min 20 s, 21 findings. This is the pass that
   surfaced the two defects closed by 26-12 and 26-13. Preserved at `scratchpad/smoke-prefix-1942/`.
3. **23:22 EDT** — the pass recorded above, at the post-fix sha.

Each pass ran into a **fresh** out dir with the prior state files moved aside, so no result was
carried forward by resume. Worth noting: the driver's automatic resume would have skipped the
failed `e3` in pass 2, because `is_stage_complete` (`:669`) matches on a completion line and ignores
the exit-code column. That gap is known and, per the user's 2026-08-18 direction, deliberately left
open.
