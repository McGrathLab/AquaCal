---
phase: 21-new-feature-documentation-dataset-refresh
plan: 04
subsystem: docs
tags: [jupyter, nbconvert, nbformat, tutorials, synthetic-data]

# Dependency graph
requires: []
provides:
  - "Notebook 01 (docs/tutorials/01_full_pipeline.ipynb) is synthetic-only, defaults to DATA_SOURCE=\"synthetic-small\", no Zenodo branch/prose anywhere"
  - "Notebook 02 (docs/tutorials/02_synthetic_validation.ipynb) defaults to RIG_SIZE=\"small\" (4 cameras, ~2 min)"
  - "Both notebooks carry fresh, error-free, monotonically-numbered committed outputs from a single clean AquaCal-env run"
  - "warnings.formatwarning override in notebook 02 preventing local filesystem paths from leaking into committed output on future re-executions"
affects: [21-03-cli-tutorial, 22-release-cut]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "warnings.formatwarning override in a notebook's imports cell to strip absolute file paths/line numbers from displayed warnings before they're committed to cell output"

key-files:
  created: []
  modified:
    - docs/tutorials/01_full_pipeline.ipynb
    - docs/tutorials/02_synthetic_validation.ipynb

key-decisions:
  - "Notebook prose points real-hardware readers at the CLI tutorial (03_cli_walkthrough.md) without ever naming \"Zenodo\", to satisfy the acceptance gate's zero-case-insensitive-mentions requirement while still honoring D-05/D-06's real-data-lives-in-the-CLI-tutorial direction"
  - "Simplified notebook 01 cell 21 (3D Reconstruction Error) to drop the dead pipeline_output_dir/real-data branches after removing the zenodo elif branch in cell 7, rather than leaving unreachable code that referenced a variable no longer defined"
  - "Left notebook 02's \"~2 min\"/\"~60 min\" RIG_SIZE comment unchanged -- measured wall-clock for the small preset was 2m14s-2m25s across two runs, close enough to the existing estimate that a re-run to correct the comment wasn't warranted; the large-preset ~60 min estimate is carried forward unverified since running it (~60 min) was out of scope for this plan"

requirements-completed: [DATA-03]

# Metrics
duration: 45min
completed: 2026-08-10
---

# Phase 21 Plan 04: Notebook Refresh (Zenodo Deletion + RIG_SIZE Demotion + Re-execution) Summary

**Deleted notebook 01's Zenodo data-source branch entirely, demoted notebook 02's default RIG_SIZE from "large" (12 cam, ~60 min) to "small" (4 cam, ~2 min), and re-executed both end-to-end in the AquaCal conda env with fresh, error-free, monotonically-numbered committed outputs.**

## Performance

- **Duration:** ~45 min
- **Tasks:** 3
- **Files modified:** 2 (`docs/tutorials/01_full_pipeline.ipynb`, `docs/tutorials/02_synthetic_validation.ipynb`)

## Accomplishments

- Notebook 01: `DATA_SOURCE` now defaults to `"synthetic-small"`; the entire `elif DATA_SOURCE == "zenodo":` branch (download, `run_calibration`, chdir logic) is gone; every remaining Zenodo/`load_example`/"~164 MB"/"Stages 1-4" mention was removed or rewritten across cells 0, 2, 3, 5, 6, 7, 16, 17, 21, 26.
- Notebook 02: `RIG_SIZE` now defaults to `"small"`; the branch logic in cell 6 required no change (already handles both values); D-20's full editorial pass found no other narration assuming the 12-camera/realistic-noise/~60-min default.
- Both notebooks re-executed top-to-bottom in the AquaCal conda env after edits: notebook 01 (`synthetic-small`) ~60s, notebook 02 (`RIG_SIZE="small"`) ~2m14s-2m25s. Every code cell in both has a non-null, strictly increasing `execution_count`; no `output_type == "error"` outputs anywhere.
- Fixed an information-disclosure defect (threat T-21-04-01) found during the first execution of notebook 02: a `DegenerateObservationWarning` raised inside `aquacal.datasets.pipelines` used Python's default warning format, which embeds the emitting module's full absolute path -- committing the local worktree path (including the machine's username) into the notebook's tracked output. Added a `warnings.formatwarning` override in notebook 02's imports cell (cell 4) that strips filename/lineno, then re-ran. Post-fix grep for `C:\Users`, `C:/Users`, and the username across both notebooks returns zero hits.

## Task Commits

Each task was committed atomically:

1. **Task 1: Notebook 01 -- delete the Zenodo path and do the full editorial pass** - `f062a43` (feat)
2. **Task 2: Notebook 02 -- demote RIG_SIZE and do the full editorial pass** - `143b7c9` (feat)
3. **Task 3: Re-execute both notebooks and commit fresh outputs** - `c3a22cc` (feat)

**Plan metadata:** this SUMMARY's commit (docs, to follow)

## Files Created/Modified

- `docs/tutorials/01_full_pipeline.ipynb` - Zenodo branch and all Zenodo/real-hardware prose deleted; defaults to `synthetic-small`; three-stage framing; fresh outputs
- `docs/tutorials/02_synthetic_validation.ipynb` - defaults to `RIG_SIZE = "small"`; added a warning-format sanitizer; fresh outputs

## Cell-by-Cell Edit Log

### Notebook 01 (`docs/tutorials/01_full_pipeline.ipynb`)

| Cell | Old | New |
|------|-----|-----|
| 0 (markdown, title) | "Run all four calibration stages (or load a previous calibration)" | Three-stage framing (in-air intrinsics, extrinsic init via best-first pose-graph traversal, joint refractive bundle adjustment); dropped "or load a previous calibration" (no longer offered); added a pointer to `03_cli_walkthrough.md` for real-hardware readers |
| 2 (markdown, Data Source Selection) | Included a `zenodo` bullet: "Downloads a real hardware dataset from Zenodo (~164 MB, 13 cameras)..." | Bullet deleted; replaced with a generic pointer to the CLI tutorial for real-hardware walkthroughs (no "Zenodo" wording, per the zero-mentions acceptance gate) |
| 3 (code) | `DATA_SOURCE = "zenodo"  # Options: "synthetic-small", "synthetic-large", "zenodo"` | `DATA_SOURCE = "synthetic-small"  # Options: "synthetic-small", "synthetic-large"` |
| 5 (code, imports) | `from aquacal.datasets import create_scenario, generate_synthetic_detections, load_example` | Dropped unused `load_example` import |
| 6 (markdown, Load Data and Calibrate) | "- **Zenodo (real rig)**: download the dataset and run the complete pipeline (Stages 1-4, ~15-20 min)" | Bullet deleted; rewritten to describe only the synthetic path |
| 7 (code) | `elif DATA_SOURCE == "zenodo": ...` full branch (download, chdir, `run_calibration`, `pipeline_output_dir` assignment) | Branch deleted entirely; kept the `if DATA_SOURCE in ("synthetic-small", "synthetic-large"):` branch; `else: raise ValueError(...)` message updated to list only the two surviving options; `pipeline_output_dir = None` removed (no longer referenced anywhere) |
| 16 (markdown) | "For synthetic data, residuals come from recomputing... For the Zenodo dataset, residuals are loaded from the saved calibration file..." | Reduced to "Residuals come from recomputing projections against detections." |
| 17 (code, comment) | `# Build a ReprojectionErrors from the saved residuals (e.g. Zenodo reference calibration)` | `# Build a ReprojectionErrors from saved residuals (e.g. a saved calibration.json -- see the CLI tutorial's save_detailed_residuals option)` |
| 21 (code, 3D Reconstruction Error) | Three-way `if detections is not None / elif pipeline_output_dir is not None / else` structure, the last two branches reading real-hardware pipeline output | Simplified to the single surviving path (`detections` is now always set by the synthetic-only cell 7), since the removed `pipeline_output_dir` variable was no longer defined and the other branches were dead code |
| 26 (markdown, Summary) | "1. Load calibration data (synthetic or real hardware from Zenodo)" / "2. Run the calibration pipeline (Stages 2-3 for synthetic, Stages 1-4 for real data)" | "1. Load synthetic calibration data" / "2. Run the calibration pipeline (extrinsic initialization and joint refractive bundle adjustment)"; added a "Next" pointer to the CLI tutorial |

No other cells required edits under the D-20 full pass -- cells 8-15, 18-20, 22-25 contain no Zenodo/real-hardware/stage-count/runtime claims.

### Notebook 02 (`docs/tutorials/02_synthetic_validation.ipynb`)

| Cell | Old | New |
|------|-----|-----|
| 2 (code) | `RIG_SIZE = "large"` | `RIG_SIZE = "small"` |
| 4 (code, imports) | No warning-format handling | Added `import warnings` and a `warnings.formatwarning` override stripping filename/lineno from any displayed warning (T-21-04-01 mitigation) |

Cell 6's `if RIG_SIZE == "small": ... else: ...` branch was read and confirmed to require no change -- it already handles both values. Cell 5's explanatory comment already described `"small"` before `"large"`, matching notebook 01's recommended-option-leads convention, so no reordering was needed. The rest of the D-20 full pass (cells 0, 3, 7, 9, 11, 13, 15-38) found no narration hardcoding the 12-camera/30-frame/realistic-noise/~60-minute case as the default experience -- all Experiment 1-3 prose is generic to whichever preset the reader chose, and neither "Stage 4" nor "four stages" framing appears anywhere in this notebook.

## Manual Re-execution Recipe (D-21)

Run from the repo root, in the AquaCal conda env, with `PYTHONPATH` pointed at the worktree's `src/` (per the editable-install-resolves-to-main trap):

```bash
export PYTHONPATH="$(pwd)/src"
jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=900 docs/tutorials/01_full_pipeline.ipynb
jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=900 docs/tutorials/02_synthetic_validation.ipynb
```

Measured wall-clock this session:

- Notebook 01 (`synthetic-small`): **~60 s**
- Notebook 02 (`RIG_SIZE="small"`): **~2m14s** (first successful run) / ~2m25s (initial run before the warning-format fix) -- consistent with the existing "~2 min total" comment, no correction needed
- Notebook 02's `"large"` (12-camera) preset was **not** re-run this session (out of scope, ~60 min); its "~60 min total" comment is carried forward from the prior committed value, unverified in this session

No Makefile target, CI job, or committed re-execution script was added -- D-21 keeps this manual by design.

## Decisions Made

- Real-hardware prose in notebook 01 points to `03_cli_walkthrough.md` (relative sibling-document link, per the plan's instruction) without ever using the word "Zenodo" in any cell -- the acceptance criterion is a case-insensitive substring check across the entire concatenated notebook source, which a "downloads the full Zenodo dataset" sentence would have failed. The link's destination and existing D-05/D-06 framing already establish that page as the real-data home.
- Simplified notebook 01 cell 21 rather than leaving a dead `elif pipeline_output_dir is not None:` branch referencing a variable removed from cell 7 -- keeping it would have been silently correct only because `detections` is now unconditionally set, which is fragile and confusing for a reader.
- Left notebook 02's `"~2 min"` / `"~60 min"` comment as-is; measured small-preset wall-clock (2m14s-2m25s) is close enough to the existing "~2 min" claim that a correcting re-run (which the plan explicitly permits but does not require unless the comment changes) was not warranted.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Local filesystem path leaking into committed notebook output (T-21-04-01)**
- **Found during:** Task 3, first execution of notebook 02
- **Issue:** A `DegenerateObservationWarning` raised by `aquacal.datasets.pipelines` (line 140) used Python's default warning format, which includes the emitting module's full absolute path. Because AquaCal is installed editable from this worktree, the committed cell output contained `C:\Users\tucke\PycharmProjects\AquaCal\.claude\worktrees\agent-ab183f57453a582ab\src\aquacal\datasets\pipelines.py:140`, disclosing the local username and worktree layout -- exactly the disclosure threat T-21-04-01 in the plan's threat model calls out and requires mitigating.
- **Fix:** Added a `warnings.formatwarning` override in notebook 02's imports cell (cell 4) that renders only `{category.__name__}: {message}`, dropping filename/lineno entirely. Re-executed the notebook; the same warning now displays with no path.
- **Files modified:** `docs/tutorials/02_synthetic_validation.ipynb`
- **Verification:** Post-fix grep for `C:\Users`, `C:/Users`, and the local username across both notebooks returns zero hits; the mitigation grep specified in the threat model was run explicitly.
- **Committed in:** `c3a22cc` (Task 3 commit)

**2. [Rule 1 - Bug] Broken f-string in the warning-format override during authoring**
- **Found during:** Task 3, first attempt to re-execute notebook 02 after the fix above
- **Issue:** A heredoc-based JSON edit to insert the `warnings.formatwarning` override lost an escaped `\n` inside the f-string body, producing `f"{category.__name__}: {message}<literal newline>"` -- an unterminated f-string that failed at notebook-execution time with `SyntaxError`.
- **Fix:** Rewrote the cell's source with the correct two-character `\n` escape (built via `chr(92) + "n"` to avoid the same escaping pitfall) and verified with `compile()` before re-running `nbconvert`.
- **Files modified:** `docs/tutorials/02_synthetic_validation.ipynb`
- **Verification:** `compile(cell_source, "<cell4>", "exec")` succeeded; subsequent `nbconvert --execute` completed with zero errors.
- **Committed in:** `c3a22cc` (Task 3 commit, folded into the same fix as item 1 -- both edits landed in one re-execution cycle)

---

**Total deviations:** 2 auto-fixed (1 missing critical / information disclosure, 1 bug introduced and caught during this plan's own authoring)
**Impact on plan:** Both fixes were necessary for correctness and for the threat model's explicit mitigation requirement. No scope creep -- both are confined to notebook 02's imports cell.

## Issues Encountered

- `sphinx-build -W --keep-going -b html docs docs/_build/html` (the plan's final acceptance check) was **not run** this session. `docs/tutorials/03_cli_walkthrough.md` (created by the parallel plan 21-03, in a separate worktree) does not exist yet here, so the toctree reference notebook 01 now makes to `03_cli_walkthrough.md` would currently 404/warn in a full docs build. Per the plan's explicit allowance ("if `03_cli_walkthrough` is not yet present, record that the build was deferred to the post-merge gate and say so in the SUMMARY"), this check is **deferred to the post-merge gate**, once plan 21-03's page has landed on the integration branch.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Both notebooks are ready for the docs site; nothing further is required within this plan's scope.
- **Blocker for the post-merge gate:** `sphinx-build -W --keep-going -b html docs docs/_build/html` must be run once plan 21-03's `03_cli_walkthrough.md` has merged, to confirm notebook 01's new cross-reference resolves cleanly.
- No stubs: both notebooks execute cleanly end-to-end with real (synthetic) computed outputs; nothing hardcoded or placeholder.

---
*Phase: 21-new-feature-documentation-dataset-refresh*
*Completed: 2026-08-10*

## Self-Check: PASSED

- FOUND: docs/tutorials/01_full_pipeline.ipynb
- FOUND: docs/tutorials/02_synthetic_validation.ipynb
- FOUND: .planning/phases/21-new-feature-documentation-dataset-refresh/21-04-SUMMARY.md
- FOUND: f062a43 (Task 1 commit)
- FOUND: 143b7c9 (Task 2 commit)
- FOUND: c3a22cc (Task 3 commit)
