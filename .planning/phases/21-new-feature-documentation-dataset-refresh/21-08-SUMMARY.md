---
phase: 21-new-feature-documentation-dataset-refresh
plan: 08
status: blocked
completed: 2026-08-10
requirements: [DATA-01, DATA-01a, DATA-02]
---

# 21-08: D-15 Gates 1 and 3 — BLOCKED on a manuscript decision

The archive is **verified faithful**. Gate 1 as written cannot be satisfied by any correct
archive on the current library, because it compares against output from a superseded one.
No DOI has been minted and plan 21-09 was not started.

## Task 1 — the runs

Interpreter confirmed: `C:\Users\tucke\anaconda3\envs\AquaCal\python.exe`, cv2 4.13.0.
Both runs executed outside any executor subagent, from `gate1_scratch/real-rig/` — the zip's
exact bytes, freshly extracted, **not** plan 21-07's staging tree.

`git log --oneline -1` returned `71d1145` both before and after; no commit landed mid-run, so
`benchmark.json`'s recorded sha is coherent.

| Run | Command | Exit | Wall clock |
|---|---|---|---|
| Gate 3a quickstart | `python -u -m aquacal calibrate config_quickstart_not_paper.yaml -v` | 0 | ~10 min |
| Gate 1 paper | `python -u -m aquacal calibrate config_paper.yaml -v` | 0 | **53 min** (15:44:13 -> 16:37:13) |

Per D-12 the quickstart's numbers are deliberately **not** recorded anywhere.

Tutorial text vs command run, character for character:

```
tutorial:  aquacal calibrate config_paper.yaml -v
run:       python -u -m aquacal calibrate config_paper.yaml -v
```

The `python -u -m` prefix is the tutorial's own documented form for piping to a log ("`python -u`
is only needed when piping output to a file or log"); the argument text matches exactly.

Both runtimes are reported as measured. No runtime is attributed to any code change.

`output/diagnostics.json` and `output/benchmark.json` exist and parse;
`problem_shape.n_frames_holdout` == **52**.

## Task 2 — the nine §3 quantities: initially FAIL, then correctly diagnosed

`num_comparisons` is **exactly 7762** (§3's value; the previously published archive gave
1,817). Eight of nine other quantities missed the >= 4 significant figure bar by 1.8–13.6%.
The full table is in `21-ARCHIVE-MANIFEST.md`.

Per D-16 the tolerance was **not** widened, §3 was **not** edited, and 21-09 was **not**
started. A `## HALT` was written and committed.

### The comparison used the wrong control

The plan's three hypotheses were ruled out by evidence: `frame_step` correct in both
extractions (7860/30 = 262; intrinsic counts equal source/30), camera order equal to the
release config element-for-element, no missing or extra frames.

The user then identified the actual error in the comparison: this phase varies exactly one
thing, video -> image set, so the control must hold the **library** fixed.
`release_calibration/diagnostics.json` (2026-02-19, ~`v1.4.2`) varies both.

`experiments/results/benchmark.json` is a real-rig run from **2026-07-31**, `git_sha 6c7f930`,
`aquacal 1.8.0` — same library era as this run — read from **videos**, identical
`problem_shape`.

| Quantity | Archive (images) | Experiments (video) | Delta |
|---|---:|---:|---:|
| `reprojection_rms` | 0.927660749239 | 0.927660733039 | 1e-6 % |
| `validation_3d_error_mean` | 0.000258177176 | 0.000258177176 | 0 % |
| `validation_3d_error_std` | 0.000572627835 | 0.000572627822 | 1e-6 % |

**The video -> image conversion is faithful. The archive is correct.** The proposed ~50 minute
`v1.4.2` re-run was cancelled as unnecessary.

Recorded as **MF-19** in `.planning/MANUSCRIPT-FINDINGS.md`.

## Task 3 — gate 3, tutorial reconciliation

Every fenced block on `docs/tutorials/03_cli_walkthrough.md`:

| Block | Result |
|---|---|
| `load_example('real-rig')` (§1) | **deferred to plan 21-10 (post-publish)** — the new version is not downloadable until minted |
| `aquacal calibrate config_quickstart_not_paper.yaml -v` | PASS, exit 0 |
| `aquacal calibrate config_paper.yaml -v` | PASS, exit 0 |
| `python -c "... num_comparisons ..."` | PASS — prints `7762 7762`, exactly as the page promises |
| `aquacal compare output/ reference_outputs/ -o comparison_output/` | exit 0, **but wrote different filenames than documented — page corrected** |
| `aquacal init --intrinsic-dir ... --extrinsic-dir ...` | illustrative, for the reader's own rig; takes videos, so not runnable against an image archive. Correct as written. |

### Tutorial correction (commit `57976b9`)

`aquacal compare` exits 0 but writes:

| Page claimed | Actually written |
|---|---|
| `metrics.csv` | `metrics_summary.csv` |
| `per_camera.csv` | `per_camera_metrics.csv` |
| `depth_error_plot.png` | `depth_error_comparison.png` |
| `depth_binned.csv` | `depth_binned_errors.csv` |
| — | `xy_error_heatmaps.png` (undocumented) |

The page's precondition was also wrong: the depth outputs appeared with no
`spatial_measurements.csv` in either directory. Reworded. `sphinx-build -W` exits 0.

## What is blocked, and on what

1. **Gate 1** — needs a manuscript decision (MF-19): update §3 to current-library numbers, or
   state the reproduction version explicitly. Not an archive defect.
2. **`reference_outputs/` internal inconsistency** — the archive ships `calibration.json` from
   the Jul-31 run and `diagnostics.json` from the Feb-19 run. A reader gets a close match from
   `aquacal compare` and a 2–14% divergence from the tutorial's `diagnostics.json` check. Fixing
   this rebuilds the zip and therefore changes `size_bytes` and the md5 in the manifest.

Both must be resolved before plan 21-09.

## State left on disk

- `C:/Users/tucke/Desktop/Aqua/AquaCal/real-rig-calib.zip` — 4,350,417,815 B, md5
  `729f002c132f88e10224146e5b407a57`. **Stale if reference_outputs is fixed.**
- `archive_staging/real-rig/` — the source tree, intact
- `gate1_scratch/real-rig/` — extracted archive plus `output/` (gate-1 run),
  `output_quickstart/`, `comparison_output/`. **Left in place**; `output/diagnostics.json` is
  the current-library diagnostics that would resolve the inconsistency above.
- Repo clean; nothing moved out of `experiments/results/` (that is plan 21-11, gated on publish)

## Self-Check: PARTIAL — blocked, not failed

- Both calibrations exited 0 from the zipped bytes; diagnostics and benchmark present; holdout 52
- No commit landed mid-run
- Every tutorial block has a recorded status; one page defect found and fixed
- Gate 1 not passed: blocked on a manuscript decision, with the archive itself proven faithful
- 21-09 not started; no DOI minted
