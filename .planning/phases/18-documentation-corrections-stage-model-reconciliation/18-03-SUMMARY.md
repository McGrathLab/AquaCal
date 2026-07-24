---
phase: 18-documentation-corrections-stage-model-reconciliation
plan: 03
subsystem: docs
tags: [docs, configuration, sphinx, docs-04]
requires: []
provides:
  - docs/guide/configuration.md (new configuration reference page)
  - configuration.md registered in docs/guide/index.md toctree
  - troubleshooting.md forward links into configuration.md
affects:
  - docs/guide/index.md
  - docs/guide/troubleshooting.md
tech-stack:
  added: []
  patterns:
    - "Sphinx MyST doc-page skeleton: no frontmatter, H1 + orienting paragraph, {ref}/{func}/{class} cross-refs, admonitions (:class: tip / :class: warning), ## See Also footer"
key-files:
  created:
    - docs/guide/configuration.md
  modified:
    - docs/guide/index.md
    - docs/guide/troubleshooting.md
decisions:
  - "Gave shared_interface an explicit ablation-warning admonition in the new page, matching the framing already used in schema.py and 17-02's docstring, rather than a plain table row alone"
  - "Fixed a broken cross-doc anchor (markdown fragment link into optimizer.md#camera-models) discovered by the CI-equivalent sphinx-build -W verification; replaced with a proper {ref} to the existing (camera-models)= anchor (Rule 1)"
metrics:
  duration: "~40 minutes"
  completed: "2026-07-24"
---

# Phase 18 Plan 03: Configuration Reference Page (DOCS-04) Summary

Created `docs/guide/configuration.md` — AquaCal's first configuration reference page — and
gave the v1.7/v1.8 features (`reject_outlier_frames`, `start_frame`/`stop_frame`, seeded
`cv2.calibrateCamera` intrinsics initialization, fronto-parallel view-diversity warning) a
proper documented home outside of troubleshooting.

## What Was Built

**Task 1 — `docs/guide/configuration.md` (new, 316 lines).** Organized by YAML top-level
section in `example_config.yaml` order: `board`, `cameras`, `paths`, `interface`,
`optimization`, `detection`, `validation`, `internals`, `seed`, plus a closing "In-air
intrinsic calibration behavior" section for the two always-on, no-config-key v1.8 behaviors.
Each section has a key/type/default/meaning table and a fenced `yaml` snippet mirroring the
shipped example config's own inline comments. All defaults were read directly from
`src/aquacal/config/schema.py`'s `CalibrationConfig` field initializers (not from YAML
comments), matching the plan's threat-mitigation requirement (T-18-03-DEFAULT). Cross-links
into `{class}`aquacal.config.schema.CalibrationConfig`` and `docs/api/config.rst` rather than
restating the exhaustive field list. Two anchors, `(configuration-frame-trimming)=` and
`(configuration-frame-rejection)=`, were added above the relevant subsections for
troubleshooting to reference in Task 3. No "Stage 4" phrasing and no Phase 21 (DOCS-05)
material (`calc-index`, `benchmark.json`, trace/conditioning walkthroughs, `shared_interface`
worked example) appears anywhere on the page, per the scope fence.

**Task 2 — Registration in `docs/guide/index.md`.** Added a `[Configuration
Reference](configuration.md)` bullet to the Practical Guides list (between CLI Reference and
Troubleshooting) and a bare `configuration` entry to the hidden toctree in the same relative
position. Line 9's "Four-stage calibration pipeline" wording was left untouched, as required
(that edit belongs to plan 18-08's checkpoint-gated vocabulary pass).

**Task 3 — Cross-links from `docs/guide/troubleshooting.md`.** Added two inline "Full key
reference" links inside the Contaminated Frames section — one after the `start_frame`/
`stop_frame` snippet pointing at `{ref}`Manual frame trimming <configuration-frame-trimming>``,
one after the `reject_outlier_frames` tuning snippet pointing at `{ref}`Automatic
outlier-frame rejection <configuration-frame-rejection>`` — plus a new Configuration Reference
entry in the file's `## See Also` footer. All eleven pre-existing "Stage 3/4" phrasings and
the existing diagnostic prose were left byte-for-byte unchanged.

## Verification

- `sphinx-build -W --keep-going -b html docs docs/_build/html` exits 0 (warnings-as-errors);
  `docs/_build/html/guide/configuration.html` exists after the build.
- All plan-specified grep assertions pass: `reject_outlier_frames` (3), `frame_rejection_k`
  (3), `frame_rejection_floor_px` (3), `frame_rejection_max_fraction` (3), `start_frame` (6),
  `stop_frame` (6), `extrinsic_start_frame` (1), `CALIB_USE_INTRINSIC_GUESS` (1),
  `fronto-parallel` (case-insensitive, 3), `validate_view_diversity` (1), `CalibrationConfig`
  (5), `## See Also` (exactly 1), `Stage 4` (0), `calc-index|benchmark\.json` (0) — all in
  `configuration.md`.
- `docs/guide/index.md`: `(configuration.md)` bullet present (1), bare `configuration`
  toctree line present (1), `Four-stage` count unchanged (1, confirming line 9 untouched).
- `docs/guide/troubleshooting.md`: `configuration.md` occurrences = 3 (>= 2 required); at
  least 2 fall between the `## Contaminated Frames` heading and the next `##` heading;
  `Stage 3/4` count unchanged at 9; `start_frame` count unchanged at 3.
- Spot-checked documented defaults against `schema.py`: `robust_loss` = `"huber"`,
  `loss_scale` = `1.0`, `min_corners_per_frame` = `8` (documented as `min_corners`),
  `holdout_fraction` = `0.2`, `reject_outlier_frames` = `true` — all match.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed a broken cross-doc anchor link in configuration.md**
- **Found during:** Task 2's `sphinx-build -W --keep-going` verification run (the build failed
  with `WARNING: local id not found in doc 'guide/optimizer': 'camera-models'
  [myst.xref_missing]`, which `-W` turns into a build failure).
- **Issue:** Task 1's `cameras` section used a plain markdown fragment link,
  `[Optimizer Pipeline](optimizer.md#camera-models)`, to point at the `(camera-models)=`
  anchor in `optimizer.md`. MyST does not resolve markdown-link URL fragments into named
  anchors across documents; only `{ref}` targets do.
- **Fix:** Replaced the markdown fragment link with `` {ref}`Camera Models <camera-models>` ``
  referencing the existing anchor.
- **Files modified:** `docs/guide/configuration.md`
- **Commit:** `07818ce` (folded into the Task 2 commit since it was found while running that
  task's mandated verification command)

No other deviations. The plan's scope fences (no stage-vocabulary edits, no Phase 21
material, no touching of `index.md` line 9 or the eleven "Stage 3/4" phrasings) were held
exactly as specified.

## Known Stubs

None.

## Threat Flags

None — this plan added only documentation prose; no new network endpoints, auth paths, file
access patterns, or schema changes at trust boundaries were introduced.

## TDD Gate Compliance

Not applicable — this plan's frontmatter type is `execute`, not `tdd`.

## Self-Check: PASSED

- FOUND: `docs/guide/configuration.md`
- FOUND: `docs/guide/index.md` (modified, contains `configuration.md` bullet + toctree entry)
- FOUND: `docs/guide/troubleshooting.md` (modified, contains 3 `configuration.md` references)
- FOUND commit `6c94edf` (Task 1: create configuration.md)
- FOUND commit `07818ce` (Task 2: register in guide index + xref fix)
- FOUND commit `1dd5b95` (Task 3: cross-link troubleshooting)
