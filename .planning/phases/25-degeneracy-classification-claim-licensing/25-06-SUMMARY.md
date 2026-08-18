# Plan 25-06 Summary — Instrumented E2 classification run

**Requirement:** DEGEN-04 · **Wave:** 3 · **Executed by:** orchestrator (autonomous: false)
**Completed:** 2026-08-18 · **Tasks:** 3/3

## What happened

**Task 1 — instrumented config.** `config_paper_instrumented.yaml` created as a named copy inside
the archive root (relative `intrinsic/`/`extrinsic/` paths would break from the probe directory),
differing from `config_paper.yaml` in exactly one key: `internals.log_all_observation_depths: true`.
The archive's own config was not edited in place; `git status --porcelain aquacal_data/` empty.
Verified `cv2.__version__ == 4.13.0` — the pin that yields 198 rather than 194 (D-01). An identical
copy is committed to the probe directory as provenance. Committed at `7118e0b` **before** launch.

**Task 2 — the run.** Launched detached and unbuffered at sha `7118e0b`, tree clean.
**Wall clock 53 min** (10:40–11:33), inside the 48–87 min estimate. Clean exit, no traceback.
Accuracy healthy: **3D error MAE 0.26 mm, RMSE 0.63 mm**. Nothing committed while in flight — the
run's own `benchmark.json` records `git_sha = 7118e0b`, matching the launch sha exactly, which is
independent confirmation the SHA was not split. `git status --porcelain experiments/results/` empty.
`degenerate_observations.csv` copied out of the archive cache (it does not land in `--out`).

**Task 3 — classification.** 198 rows through `classify_degenerate_observations`, written to
`degeneracy_classification.csv` with the in-body `provenance` stamp (sha, `provisional`,
`truncated=false`, `n_flagged_at_stage=198`, `opencv=4.13.0`, probe path). `FINDINGS.md` written
mirroring the two existing probe documents.

## The finding

**All 198 are one bucket: `above_interface` (`nan_reason = 2`)** — board corners sitting 1.3 mm to
64 mm *above* the water surface, where refractive projection is undefined by construction. The
other two buckets are **empty, not small**. 198 / 73,975 = **0.27%** of observations evaluated at
`stage3_intrinsic_pass`; **zero** flagged at `stage3_interface_optimization`. All 198 **extended**,
none penalized. Confined to **8 frames in two bursts** (22–26, 102–105) across 8 cameras.

Three counters agree independently: sidecar row count (198), the sidecar's own
`n_flagged_at_stage` stamp (198, `truncated=false`), and Phase 24's separate aggregate counter
(`cause_above_interface__stage3_intrinsic_pass = 198`).

## Deviations

1. **`all_observation_depths.csv` left in the archive cache** — 11 MB, over the plan's "a few MB"
   threshold. The plan's stated alternative was taken and the reason recorded in FINDINGS.md.
   Nothing in the finding depends on it; it is regenerable.
2. **`benchmark.json` left untracked** — the repo's `detect-secrets` hook flags its `git_sha` as a
   hex high-entropy string. Rather than edit a generated artifact or bypass the hook, the file
   stays untracked and its numbers are reproduced in FINDINGS.md. (A surgical baseline allowlist
   was later used for plan 25-08's provenance sidecar; the same could be applied here if the file
   is ever needed in git.)
3. Three further ordinary E2 outputs (`calibration.json`, `reprojection_residuals.csv`,
   `reconstruction_errors.csv`) left untracked as bulk, not evidence.

## For downstream phases

The sidecar carries a `stage` column and a stage-agnostic `len()` **would** double-count an
observation flagged in both stage-3 passes. This run happens to flag in one stage only, so its 198
is a distinct count — that is a property of this run, not a guarantee.

**Everything here is PROVISIONAL (D-02).** No count reaches `MANUSCRIPT-FINDINGS.md`, the
disclosure, or any §3 number. Phase 29's frozen table is the sole source.
