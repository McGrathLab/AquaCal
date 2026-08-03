# Evidence carried over from phase 19.2's session

These files were produced during the 2026-08-01 session that found the scenario-geometry defect.
They lived in a session-scoped scratchpad that does not survive a context clear, so the ones the
analysis actually rests on are preserved here.

| file | what it proves |
|---|---|
| `e6_sweep_2026-07-31_pre-optimality.log` | E6 before plan 27's optimality capture |
| `e6_rerun_2026-08-01_with-optimality.log` | E6 after. **Diff the `Function evaluations` lines against the file above: they are byte-identical (`32 4 60 4 73 4 27 4 29 4 19 4 26 4 20 4 20 5 24 6 32 12 29 4`), and every `initial cost`/`final cost` matches to all printed digits — while first-order optimality differs by up to 2x.** That pairing is the whole argument that the solver walks the same path and lands a hair away, so a ~1e-6 difference in the final iterate is invisible in cost and loud in the gradient. Also the source of the per-configuration degenerate-observation counts (3–38). |
| `determinism_probe.log` | The decisive run: the SAME configuration twice on IDENTICAL code, differing at rel 7.2e-8 (rms) and 6.5e-6 (focal) for `scale_half_scale`, and 6.7e-9 / 4.9e-5 for `index_1.36`. No code change can explain that. Note run 2 landed EXACTLY on the committed values for BOTH configurations while run 1 did not — results settle onto a few discrete points, so a single "it reproduced" observation is weak evidence. |
| `e5_rerun_2026-08-01.log` | E5's four `DegenerateObservationWarning`s, all with exactly 3 observations and optimality 7.8e-4–1.3e-2, on the points where `n_assumed` departs from `n_true`. Shows E5 is affected but far less severely, and by a different mechanism. |
| `generalization_sweep_pre-optimality.csv` | The pre-re-run E6 table, for the 63/308-cell movement comparison. |

`../determinism_probe.py` is the probe script itself — re-runnable.

## Added 2026-08-03 (phase 19.3 plan 10 verification)

| file | what it proves |
|---|---|
| `water_z_null_direction_probe.py` | `water_z` is an EXACT null direction at `n_water=1.0`: sweeping it 0.53-2.03 m leaves the cost constant to 13 significant figures (rel. variation 2.6e-15) while the guard count climbs 0 -> 14,949. The n=1.333 control moves the cost five orders of magnitude, proving the probe is not blind. This is why E1's 14,949 degenerate observations are bookkeeping and do not contaminate the paper's refractive-vs-non-refractive comparison. |
| `e1_pinned_water_z.py` | End-to-end confirmation via a `build_bounds` monkeypatch: pinning `water_z` at ground truth reproduces every non-refractive reconstruction number to ~4 s.f. (2.5 m Z-RMSE 248.267 -> 248.221 mm) while driving the guard count 14,949 -> 0 and optimality 874 -> 0.525. Also shows the refractive arm MUST NOT be pinned -- doing so inflates the ratio to a flattering 168x. |

Both write only to temp/scratch locations and never touch `experiments/results/`.
Run with `PYTHONPATH="$(pwd)/src:$(pwd)"`.
