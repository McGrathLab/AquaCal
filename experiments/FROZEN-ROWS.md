# The v2.1 full-suite re-run: rows this run will NOT regenerate

**Read this before treating any citation below as stale.** It is written *before* the run and
*before* the archive purge, on purpose. A reference whose provenance is stated is not a stale
reference — it is a frozen one, and the difference is entirely whether anybody wrote down the sha
and the machine while the tree still existed. This note writes them down.

Every row here is a `numbers-ledger.tsv` row (cited by its `id`) whose cited artifact the Phase 28
run will **not** re-source. Four distinct causes produce that outcome, and they are not
interchangeable — §1 through §4 below are the four, one section each.

**This note reads the ledger; it never writes it.** The ledger lives in the author's manuscript
tree and is read-only from this repo. Rows are cited by `id` for exactly that reason.

## 0. How to read the table

| Column | Meaning |
|---|---|
| `ledger id` | The `id` column of `numbers-ledger.tsv`. The join key; nothing else here is stable. |
| `artifact` | The ledger's own `artifact` cell, verbatim. Where the bytes actually live in this repo is given in the section prose, because for three of the four groups **the ledger's path and the repo's path are not the same string** — which is the whole reason Phase 30 needs this note. |
| `recorded sha` | Read from the artifact's **own provenance block** (`benchmark.json` / `e6_provenance.json` `environment.git_sha`), never from the commit that landed the file in git. Where no provenance block exists anywhere, the cell reads `not recorded` and no sha is guessed. |
| `machine` | Machine **class**, per the two classes defined below. Hostnames and user paths are deliberately omitted — this file becomes public. |
| `why this run will not regenerate it` | The cause, specific to the row. |

**Exactly one data cell below carries the `not recorded` marker: `RL-guard-frac` in §4.** The other
22 rows' sha and machine were recovered from an artifact's own provenance block. `RL-guard-frac`
has no artifact and no provenance block anywhere — the ledger's own `artifact` and `derivation`
cells are empty and its note reads *"no committed artifact -- pre-fix state"* — so its sha and
machine are marked `not recorded` rather than inferred from the campaign around it. **An invented
sha is worse than an absent one** — it is precisely the F-001 shape this milestone exists to close.

**Two machine classes are referenced throughout:**

- **W16** — the 16 GiB Windows box. `os: Windows 11`, `cpu_model: Intel64 Family 6 Model 154
  Stepping 3`, `cpu_count_logical: 20`, `ram_total_bytes: 16857190400` (15.70 GiB). Every
  pre-2026-08-12 artifact in this repo was measured here.
- **L32** — the 32 GiB Linux box. `os: Linux 6.8.0-136-generic`, `cpu_description: Intel
  i9-13900KF, 32 logical cores`, `ram_total_bytes: 33351241728` (31.06 GiB). Source:
  `experiments/pre_rerun_baseline/results_linux32gb/linux32gb_scope.json` `machine` block.

**L32 is, to every recorded detail, the Phase 28 target.** 27-CONTEXT's D-25 records the target as
Ubuntu 22.04.4, kernel **6.8.0-136**, **32** logical cores, **31 GiB** — the same kernel build, core
count and RAM as the `linux32gb` runs. **So "the earlier machine" in §2 is a misnomer if read as
"different hardware".** What actually separates §2's rows from the coming run is the *software* at
which they were measured and the *directory* they were written to, not the box. Stating that
plainly here is the point: a Phase 30 reader who assumes a hardware difference will re-point those
citations for the wrong reason.

---

## 1. Pre-fix archive trees

Five rows, all in `response-letter.md`, all citing `experiments/archive/`. These are deliberately
preserved **pre-fix** snapshots: the response letter quotes them *as* the pre-fix state, so
regenerating them is not merely unnecessary, it would destroy what they are for. A re-run at the
frozen sha produces post-fix numbers by construction.

| ledger id | artifact | recorded sha | machine | why this run will not regenerate it |
|---|---|---|---|---|
| `RL-prefix-affected` | `archive/e6-2026-08-02-pre-depth-fix/generalization_sweep.csv` | `74e75a7b33d4d9be1467f5806e76d1e77604e047` | W16 | Quoted **as** the pre-depth-fix state (mean 0.59377 mm over the high-optimality group). The frozen sha is post-fix; no run at it can produce a pre-fix number. |
| `RL-prefix-healthy` | `archive/e6-2026-08-02-pre-depth-fix/generalization_sweep.csv` | `74e75a7b33d4d9be1467f5806e76d1e77604e047` | W16 | Same table, remaining 11 rows (mean 0.56224 mm). Same reason. |
| `RL-prefix-best` | `archive/e6-2026-08-02-pre-depth-fix/generalization_sweep.csv` | `74e75a7b33d4d9be1467f5806e76d1e77604e047` | W16 | Same table, minimum cell `scale_half_scale` 0.4934642 mm. Same reason. |
| `RL-opt-submitted` | `archive/e2-2026-07-30-pre-pnp-guard/` | `77a1026adae2e7e3f6857f424c829ed762628975` | W16 | The **submitted record's** stage-3 intrinsic optimality, 20813.59 (quoted 2.08e4). Quoted as the state at submission, before the degenerate-PnP guard. Not reproducible post-guard, and not intended to be. |
| `RL-rms-submitted` | `archive/e2-2026-07-30-pre-pnp-guard/` | `77a1026adae2e7e3f6857f424c829ed762628975` | W16 | The submitted record's **pooled** reprojection RMS, `mean_reprojection_px` = 1.019136 px. Same reason. **Not** the 0.879 px per-camera mean in the same file. |

**How those two shas were recovered, because the method matters for Phase 30.** Neither archive
directory carries a provenance sidecar of its own — the E6 copy is a bare CSV and the E2 copy is
`real_rig_metrics.json` plus `camera_parameters.csv`, none of which has an `environment` block.
The recorded sha is therefore read from the **contemporaneous** sidecar in `experiments/results/`
at the archiving commit's parent:

```bash
git show 8a90ea3^:experiments/results/e6_provenance.json   # -> environment.git_sha 74e75a7b...
git show 117bad7^:experiments/results/benchmark.json       # -> environment.git_sha 77a1026a...
```

and the copies were confirmed byte-identical to those trees (`md5sum` after `tr -d '\r'`).

**Do not read the sha out of `experiments/results/` at the commit the archive README names.** For
E6 that gives a *different, older generation* of `generalization_sweep.csv` with a different column
layout — the results tree lagged the sidecar. The archive README (`experiments/archive/README.md`)
already states the rule this repeats: the producing commit is the one in the sidecar's
`environment.git_sha`, never the archiving commit's `HEAD`.

**The bulk E2 artifacts are not copied into the archive at all.** `benchmark.json`,
`calibration.json`, `reprojection_residuals.csv` and `reconstruction_errors.csv` trip
`check-added-large-files` / `detect-secrets`, so `RL-opt-submitted`'s optimality lives only in git
history and is retrieved with `git show 35d76a6:experiments/results/benchmark.json`. **A Phase 30
purge of `experiments/archive/` would not touch those bytes — but a `git` history rewrite would.**

---

## 2. The earlier Linux measurement campaign

Nine rows citing `results_linux32gb/...`. All nine were measured on **L32**, in a one-off
second-machine study whose scope, confound controls and limits are recorded in
`experiments/pre_rerun_baseline/results_linux32gb/linux32gb_scope.json`. In this repo they live
under `experiments/pre_rerun_baseline/results_linux32gb/`; the ledger cites them without that
prefix.

**The re-run writes to different directories, so it cannot refresh these paths.** Per
`experiments/suite_expectations.json`, the frozen run's `e2_timing` stage writes
`experiments/results_e2_timing/`, `e2_memory` writes `experiments/results_e2_memory/`, and `e4`
writes `experiments/results/`. Nothing in the manifest ever writes `results_linux32gb/`. The run
will produce *new, differently located* timing and memory measurements; **it will not update the
artifact these rows point at.** Whether the manuscript re-points is Phase 30's question, not this
note's.

| ledger id | artifact | recorded sha | machine | why this run will not regenerate it |
|---|---|---|---|---|
| `M-L156-minutes` | `results_linux32gb/e2_timing/` | `d27bda76fe7c765b3c975b2052ca1f8f7b286068` | L32 | "tens of minutes" — stage seconds 725.68 + 394.96 = 1120.6 s (~18.7 min). Measured under **OpenCV 4.14.0** and unpinned BLAS. The run writes `results_e2_timing/`, not this path. |
| `M-L350-minutes` | `results_linux32gb/e2_timing/` | `d27bda76fe7c765b3c975b2052ca1f8f7b286068` | L32 | Same measurement, conclusions restatement; the ledger marks it lockstep with `M-L156-minutes`. Same reason. |
| `M-perf-peakmem` | `results_linux32gb/e2_memory/benchmark.json` | `d27bda76fe7c765b3c975b2052ca1f8f7b286068` | L32 | `memory.whole_run_peak_bytes` = 11108622336 B = 10.346 GiB, `mode: proc_status_vmhwm`. The run writes `results_e2_memory/`, not this path. |
| `S-perf-peakmem` | `results_linux32gb/e2_memory/benchmark.json` | `d27bda76fe7c765b3c975b2052ca1f8f7b286068` | L32 | The same single measurement, quoted a second time for the GiB/GB bridge. Same reason. |
| `RL-e2-mem` | `results_linux32gb/e2_memory/` | `d27bda76fe7c765b3c975b2052ca1f8f7b286068` | L32 | The **third** site of that same 11108622336 B number, rendered 10.35 GiB. Same reason. |
| `RL-mem-range` | `results_linux32gb/e4/benchmark_grid.csv` | `d27bda76fe7c765b3c975b2052ca1f8f7b286068` | L32 | "0.87 to 11.32 GiB" — reproduced exactly from the nine cells' `peak_bytes_stage3_*` columns. The run's `e4` writes `experiments/results/benchmark_grid.csv`, not this path. Note the L32 grid **carries the nine synthetic cells only**; its real-rig row was dropped deliberately (`linux32gb_scope.json` `e4.real_rig_row_dropped`). |
| `S-repro-cv413` | `linux32gb_scope.json` | `1af06508db120daacce8618b8387c7a7213b1fbe` | L32 | 1.264e-7 worst case over 61 diagnostics, 23028 observations per camera identical. It is the output of the **`e2_cv413` single-variable OpenCV control**, and **no stage in `suite_expectations.json` is that control** — the frozen run has no cloned-env 4.13-vs-4.14 arm. Genuinely unregenerable by this run. |
| `M-perf-cv413` | `linux32gb_scope.json` | `1af06508db120daacce8618b8387c7a7213b1fbe` | L32 | The same 1.264e-7, restated in §3. Same reason. |
| `RL-repro-grid` | `linux32gb_scope.json` | `d27bda76fe7c765b3c975b2052ca1f8f7b286068` | L32 | "1e-13 and 1e-15" final-cost agreement across the nine synthetic cells — a **cross-version comparison** between the committed W16 baseline (aquacal 1.8.0, sha `2a623f9d09bc`) and the L32 re-run (2.0.1). A single run produces one arm of a two-arm comparison; the comparison itself is not an artifact any stage emits. |

**`linux32gb_scope.json`'s top-level `git_sha` is not the sha of every tree beneath it.** The file
records `d27bda76fe7c765b3c975b2052ca1f8f7b286068` at top level, and `e2_timing/`, `e2_memory/`
and the nine `e4` cells each independently confirm it in their own `environment.git_sha`. But
`e2_cv413/benchmark.json` records **`1af06508db120daacce8618b8387c7a7213b1fbe`** — a different
commit. The two `linux32gb_scope.json` rows sourced from the cv413 control (`S-repro-cv413`,
`M-perf-cv413`) are therefore attributed above to `1af0650`, per-artifact, and `RL-repro-grid`
— sourced from the E4 arm — to `d27bda7`. **Prefer the artifact's own block over a tree-level
summary every time.** A tree-level sha that is right for four of five subtrees is the F-001 shape
in miniature.

---

## 3. Frozen behind the OpenCV 4.13 pin

Seven rows, all `verdict = KEEP-FROZEN-5f`, all naming `real_rig_metrics.json`, all in `main.tex`
§3. In this repo the frozen bytes are `experiments/pre_rerun_baseline/results/real_rig_metrics.json`,
whose sibling `benchmark.json` records `environment.git_sha`
`6c7f930bb56b019067b8eb7ac1f2c84d37be645e`, `aquacal_version 1.8.0`, `opencv_version 4.13.0`,
on **W16**. All seven values reconcile against that file exactly.

**These rows have an emitter, and the run does rewrite the file.** `e2_production` writes
`experiments/results/real_rig_metrics.json`. The distinction that matters, and the reason these are
in this note rather than in `EMITTER-COVERAGE.md`'s regenerated set: **the file is rewritten, the
§3 numbers are not re-sourced from it.** They are frozen against the DOI'd Zenodo archive (record
21889922), and the fresh file's role is the `check_e2_band` numeric control at
`_E2_METRICS_RTOL = 1e-6` (`experiments/check_rerun_gates.py:1378`) — a control, not a new source.

**Why the pin, measured rather than asserted.** `pyproject.toml` hard-pins
`opencv-python==4.13.*` because 4.14.0 detects **1.95% fewer corners** (23028 -> 22578
observations, concentrated -348 in the auxiliary fisheye) and moves the paper's reconstruction
RMSE by **+7.8%**. The `e2_cv413` control closed the attribution: under 4.13 every one of those
450 observations returns, all 13 per-camera counts match the reference exactly, and 61 numeric
diagnostics agree to 1.264e-7. Under 4.14 the same quantities move up to 1.1e-1. So the pin is not
conservatism — **it is the difference between reproducing the archive and silently disagreeing with
it.** 27-CONTEXT's D-26 records that the target's pre-existing conda env holds **4.14.0**, i.e. the
version the pin exists to exclude; that is why the frozen run builds a new environment rather than
reusing it.

| ledger id | artifact | recorded sha | machine | why this run will not regenerate it |
|---|---|---|---|---|
| `M-L300-reproj` | `real_rig_metrics.json` | `6c7f930bb56b019067b8eb7ac1f2c84d37be645e` | W16 | `mean_per_camera_reprojection_px` = 0.8240385 px, quoted 0.82. §5f DOI-frozen; the ledger note records that `--verify` fails if it moves. The re-run's copy is the 1e-6 control, not a re-source. |
| `M-L300-reproj-range` | `real_rig_metrics.json` | `6c7f930bb56b019067b8eb7ac1f2c84d37be645e` | W16 | `reprojection_range_px` = [0.5537183, 2.0815507], quoted 0.55–2.08. Same reason. |
| `M-L301-mae` | `real_rig_metrics.json` | `6c7f930bb56b019067b8eb7ac1f2c84d37be645e` | W16 | `inter_corner_mae_mm` = 0.2581772, quoted 0.258. Same reason. |
| `M-L301-rmse` | `real_rig_metrics.json` | `6c7f930bb56b019067b8eb7ac1f2c84d37be645e` | W16 | `inter_corner_rmse_mm` = 0.6281386, quoted 0.628. Same reason. |
| `M-L301-relerr` | `real_rig_metrics.json` | `6c7f930bb56b019067b8eb7ac1f2c84d37be645e` | W16 | `mean_relative_error_pct` = 0.4302953, quoted 0.43%. The ledger calls this a "§5f DOI-frozen matched set" — it moves only with the four rows above it. |
| `M-L303-aux` | `real_rig_metrics.json` | `6c7f930bb56b019067b8eb7ac1f2c84d37be645e` | W16 | `auxiliary_reprojection_px["e3v8250"]` = 14.856381, quoted 14.9 px. Same reason. **This is the quantity the 4.14 drift hits hardest** — the -348-observation loss is concentrated in this same fisheye. |
| `M-L302-signed` | `real_rig_metrics.json` | `6c7f930bb56b019067b8eb7ac1f2c84d37be645e` | W16 | +0.043 mm signed mean. **Provenance caveat, see below** — the artifact the ledger names does not contain this quantity. |

**`M-L302-signed`'s artifact attribution is one level off, and Phase 30 must know it.**
`real_rig_metrics.json` has no signed-mean field: its keys are `auxiliary_reprojection_px`,
`camera_height_range_m`, `inter_corner_mae_mm`, `inter_corner_rmse_mm`,
`mean_per_camera_reprojection_px`, `mean_relative_error_pct`, `mean_reprojection_px`,
`n_comparisons`, `provenance`, `reprojection_range_px`, `water_z_m`. Its two inter-corner figures
are computed from `signed_errors` (`experiments/e2_real_rig.py:252-254`) but only as
`mean(abs(...))` and RMS — **the sign is averaged away before the file is written.** The +0.043 mm
figure is derivable from the `signed_error_m` column of `reconstruction_errors.csv`
(`experiments/e2_real_rig.py:82,217`), which is **gitignored under DATA-01b** (`.gitignore:239`)
and ships only in the Zenodo archive. The sha and machine above are still correct — same run, same
solve — but the bytes are not in this repo. This row is the one in this note whose citation cannot
be checked without the archive.

---

## 4. Unregenerable by construction

Two rows. They reach the same category by different routes: one is unregenerable because the
**schedule** cannot produce it, the other because the **code** cannot.

| ledger id | artifact | recorded sha | machine | why this run will not regenerate it |
|---|---|---|---|---|
| `RL-determinism` | *(empty in the ledger)* | `2a623f9d09bc77bbbb1cfbd3188075bc8b8b4395` | W16 | **P26-D-42 turned `e6_repeat2` OFF, under both profiles.** The quantity is a *paired-repeat* statistic — 16 differing cells of 308 between two independent E6 runs at one sha — so it needs both arms. The frozen manifest schedules `e6_repeat1` and never a second arm, so no run at this freeze can produce it. |
| `RL-guard-frac` | *(empty in the ledger)* | `not recorded` | `not recorded` | **The fixed code cannot produce the state being measured.** The quantity is the fraction of board corners sitting **at or above the water interface** in the pre-fix baseline scenario — 61 of 8800, 0.69%, worst protrusion 66.1 mm. Phase 19.3's depth-clearance fix removed that state: post-fix, **zero corners sit at or above the interface in any scenario**. The frozen sha is post-fix, so any run at it returns 0.00% by construction — not a reproduction of 0.69%, and not a refutation of it either. |

### `RL-determinism` — the schedule cannot produce it

**Both arms are provenanced, which is why this row is frozen rather than lost.** The post-fix pair
is `experiments/pre_rerun_baseline/results/e6_provenance.json` and
`experiments/pre_rerun_baseline/results_e6_repeat2/e6_provenance.json`; both record
`environment.git_sha` `2a623f9d09bc77bbbb1cfbd3188075bc8b8b4395`, `aquacal_version 1.8.0`,
`opencv_version 4.13.0`, on W16. The pre-fix arm (63/308) is §1's
`archive/e6-2026-08-02-pre-depth-fix/` tree at `74e75a7b`. The probe that produced the comparison
is `.planning/phases/19.3-scenario-geometry-and-convergence/determinism_probe.py --report`, re-run
2026-08-14.

**The manifest pins `e6_repeat2`'s absence positively — as an assertion, not an omission.**
`tests/unit/test_expectations.py::test_no_expectation_names_results_e6_repeat2` (`:353`) asserts
`"results_e6_repeat2" not in MANIFEST_TEXT`, `"e6_repeat2" not in STAGES`, and that no artifact
names it as its stage. So this is not a stage that fell out of the manifest by accident and could
quietly return; adding it back would fail a test. **Read that as the guarantee it is:** the
unregenerability is intentional and enforced, which is exactly what makes stating it here safe.

**The ledger's `artifact` cell for this row is empty**, and correctly so — it is a two-run
comparison, not a file. Its note also records that MF-09's "8 of 308 / index 1.48" is **stale**,
superseded when Phase 19.4's interface fix requeued both repeats.

### `RL-guard-frac` — the code cannot produce it

Added on the author's ruling after plan 27-06's coverage walk surfaced it; D-19 did not name it.
Its ledger note reads *"no committed artifact -- pre-fix state"*, and both its `artifact` and
`derivation` cells are empty.

**What it measures, stated from the ledger rather than from memory.** The `quantity` cell reads
*"corner fraction at or above the interface, pre-fix baseline scenario"*, the `locator` is *"a small
fraction of target corners"*, and `current_text` is **0.69%**. It is a *scenario-geometry* fraction —
how much of the synthetic board protruded through the modelled water surface — **not** a
solver-guard rejection rate. The distinction matters for Phase 30: a reader who files it as a guard
statistic will look for it in the wrong emitter and conclude the row is merely uncited.

**Why the frozen sha cannot produce it.** Phase 19.3's depth-clearance fix derives a depth floor and
re-centres board poses on the board centre rather than a corner. Measured after that fix, **zero
corners sit at or above the interface in any scenario**, checked directly against each scenario's
own corner cloud (MF-08). So the frozen, post-fix code returns 0.00% — a *different, correct*
measurement of a scenario that no longer has the defect, not a failed reproduction of 0.69%. This is
the same category as `RL-determinism` reached from the other direction: there the schedule omits an
arm, here the code has removed the state.

**Why sha and machine are `not recorded`.** The figure came from an ad-hoc probe during Phase 19.2
plan 28 / the 19.3 seed work, which wrote no artifact and therefore no `environment` block. The
closest contemporaneous anchor is §1's `archive/e6-2026-08-02-pre-depth-fix/` tree at `74e75a7b` on
W16, measured on the same baseline scenario (12 cameras, 100 frames, seed 42) — **but that is
campaign context, not this measurement's own record, and it is not written into the table as
though it were.**

**One of the ledger note's three cross-references does not hold at this sha.** The note says the
figure is *"recorded identically in 19.3-SEED.md, REQUIREMENTS.md and MF-07/MF-08"*. Two check out:
`.planning/phases/19.3-scenario-geometry-and-convergence/19.3-SEED.md:53` (61 / 8800, 0.69%, worst
protrusion 66.1 mm, with the full clearance derivation) and `.planning/MANUSCRIPT-FINDINGS.md:640`
(MF-07) and `:686` (MF-08). `.planning/REQUIREMENTS.md` exists but contains neither the figure nor
the protrusion language. **The 0.69% is well-sourced twice over; the third pointer is stale.**

---

## 5. What Phase 30 inherits

**This table IS the dangling-reference list.** POST-03's archive purge must, for each of the 23
rows above, either preserve the cited bytes or re-point the citation. The four groups need four
different decisions, and conflating them is the failure mode:

| Group | Rows | What the purge must not break |
|---|---|---|
| §1 pre-fix archives | 5 | `experiments/archive/e6-2026-08-02-pre-depth-fix/` and `.../e2-2026-07-30-pre-pnp-guard/`. **Plus** the four uncopied E2 bulk artifacts reachable only as `git show 35d76a6:experiments/results/...` — a directory purge leaves them; a history rewrite does not. `experiments/archive/README.md` states the standing rule: do not delete a generation until the manuscript's numbers are reconciled against the corresponding re-run (MF-08). |
| §2 earlier campaign | 9 | `experiments/pre_rerun_baseline/results_linux32gb/`, **including `linux32gb_scope.json` itself** — three rows cite the scope file directly, and it is the only record of the `e2_cv413` control. Two of those three carry sha `1af0650`, not the tree-level `d27bda7`. |
| §3 OpenCV-pinned | 7 | `experiments/pre_rerun_baseline/results/real_rig_metrics.json` **and** its sibling `benchmark.json` (the only place the sha and machine are recorded). `M-L302-signed` additionally depends on Zenodo record 21889922's `reconstruction_errors.csv`, which is not in the repo at all. |
| §4 by construction | 2 | `RL-determinism`: `experiments/pre_rerun_baseline/results/e6_provenance.json` **and** `results_e6_repeat2/e6_provenance.json` — both arms, or the paired statistic loses its provenance. Also `.planning/phases/19.3-.../determinism_probe.py`. `RL-guard-frac`: **planning documents are its only source** — `19.3-SEED.md:53` and `.planning/MANUSCRIPT-FINDINGS.md` MF-07/MF-08. There is no artifact to purge and nothing to re-point; the exposure is that `.planning/` is treated as disposable. |

Three items need a decision the purge cannot make mechanically:

1. **`M-L302-signed`** — its ledger `artifact` cell names a file that does not contain the
   quantity. Re-point it at `reconstruction_errors.csv` (archive-only) or accept that it is
   uncheckable in-repo. **Do not "fix" it by inventing a field in `real_rig_metrics.json`.**
2. **§2's six timing/memory rows** — the frozen run *does* produce fresh timing and memory numbers,
   into `results_e2_timing/` and `results_e2_memory/`. Re-pointing them is a real option, but it is
   a **manuscript decision with a measurement consequence**, not a path edit: the frozen run is at
   OpenCV 4.13 and a different sha, and per D-14 the timing stages stay BLAS-unpinned precisely so
   the comparison remains meaningful. Re-point deliberately or not at all.
3. **`RL-guard-frac`'s third cross-reference is stale.** Its ledger note names `REQUIREMENTS.md`
   as one of three places the 0.69% is "recorded identically"; that file exists at this sha and
   contains neither the figure nor the protrusion language. Drop the pointer or restore the text —
   **but note the figure itself is not at risk**: `19.3-SEED.md:53` and MF-07/MF-08 both carry it
   with the full derivation. This is a bad pointer, not a missing number.

### How this note joins to `EMITTER-COVERAGE.md`

The two reports **partition the ledger** between them, and the join is by ledger `id`:

- `experiments/EMITTER-COVERAGE.md` (D-16) walks every ledger row for an emitter in the frozen
  code. Rows it marks **NOT REGENERATED** are rows whose artifact has an emitter but which this run
  will not re-source — and every one of those must appear in a section above, with a sha, a machine
  and a cause.
- §3's seven rows are the sharp case: they are **NOT REGENERATED** *and* emitter-backed. An emitter
  existing does not make a number current, and a rewritten file is not a re-sourced number. That
  distinction is the entire reason both reports exist instead of one.
- §2 is graded **EMITTER-BACKED / NOT REGENERATED** too, `linux32gb_scope.json` included — that
  grading is 27-06's and the author has accepted it. Nothing here disputes it: an emitter for the
  *class* of artifact does not put anything back into `results_linux32gb/`, which is the path these
  rows cite. Where the two documents both attribute a sha, the agreed treatment in each is
  **per-artifact** — hence `1af0650` for the two cv413-sourced rows.
- §1 and §4's seven rows have no emitter at this freeze — pre-fix snapshots, an absent control arm,
  a paired statistic with only one arm scheduled, and one quantity whose underlying *state* the
  fixed code no longer produces.

A ledger `id` appearing in neither report, or as regenerated in one and frozen in the other, is a
defect in the partition — not a judgement about the number.

## 6. What this note does NOT do

Stated so nobody over-reads it.

- **It does not license the numbers.** A stated provenance makes a number *interpretable*, not
  *current*. Knowing that 10.35 GiB was measured on L32 at `d27bda7` under OpenCV 4.14 tells you
  what it means; it does not tell you it is the right number to publish today. Which numbers may be
  cited, and with what error bars, is `.planning/MANUSCRIPT-FINDINGS.md`'s question.
- **It does not make a frozen row correct.** Every value above was reconciled against the artifact
  it names — but reconciling a quoted number against the file it came from proves transcription,
  not measurement. Two of these groups exist *because* the underlying measurement is known to have
  moved.
- **It does not certify that the four causes are exhaustive for a future run.** They are exhaustive
  for **this** freeze and **this** manifest. A stage added later, or a manifest retag, changes which
  rows regenerate. This note is dated to the freeze for that reason.
- **It does not authorise the purge.** It is POST-03's input, not its verdict. Nothing here says any
  tree may be deleted; it says what would break if one were.
- **It is not a gate, and deliberately so.** Its input is the author's off-repo ledger, so a gate
  over it would be a gate that cannot pass — the shape plan 23-02 warned about, and the reason D-16
  is a report too.

---

*Written for Phase 27 (D-19), before the Phase 28 run and before Phase 30's purge.*
*23 rows: 5 pre-fix archive, 9 earlier campaign, 7 OpenCV-pinned, 2 by construction.*
*Companion: `experiments/EMITTER-COVERAGE.md` (D-16) covers the ledger rows this note does not —
between them the two reports partition the ledger.*
