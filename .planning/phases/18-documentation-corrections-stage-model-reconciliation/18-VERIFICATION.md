---
phase: 18-documentation-corrections-stage-model-reconciliation
verified: 2026-07-24T00:00:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
---

# Phase 18: Documentation Corrections & Stage-Model Reconciliation Verification Report

**Phase Goal:** Fix live factual errors in published docs and reconcile the paper's
three-stage model across both code and documentation surfaces, so the stage keys are
settled before benchmark instrumentation writes them into `benchmark.json`.

**Verified:** 2026-07-24
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `docs/guide/optimizer.md` states 13/17 groups, P=673/675/727, 43-52x reduction | VERIFIED | `grep` confirms `docs/guide/optimizer.md:186,192-195,206-212` state 13-17 columns, 673/675/727 parameters, 43-52x reduction, 98% sparse (exactly 1 occurrence). `tests/unit/test_optim_common.py::TestDocumentedGroupingNumbers` (7 tests) derives every number live from `build_jacobian_sparsity` + `build_structural_column_groups` — ran directly, all 7 pass. Numbers are NOT restated constants; they come from executing the shipped code against a 13-camera/100-frame fixture. |
| 2 | Every doc/`extrinsics.py` BFS site now reads "best-first" except `_find_connected_components` | VERIFIED | DOCS-02 guard run directly: `grep -rniE "\bBFS\b\|breadth.first" src/ docs/ README.md --include=*.py --include=*.md --include=*.rst --include=*.yaml \| grep -v _build` returns EXACTLY `extrinsics.py:200` and `:208`, both inside `_find_connected_components` (genuine FIFO BFS, untouched per D-11). `estimate_extrinsics` docstring/comments, `optimizer.md`, `glossary.md`, `README.md` all confirmed to read "best-first". |
| 3 | Glossary bipartite pose-graph definition + figure regenerated from heap-replaying script | VERIFIED | `docs/guide/glossary.md:35` reads "Bipartite graph with two node types — camera nodes and frame (board-pose) nodes..." `docs/_static/scripts/pose_graph.py` imports `aquacal.calibration.extrinsics.build_pose_graph` and replays the real heap loop (`heapq.heappush`/`heappop` present, no hardcoded `EDGES`/`BFS_EDGES` constant). Regenerated `docs/_static/diagrams/pose_graph.png` viewed directly: 4 camera nodes, 3 frame nodes, exactly 6 directed discovery edges (correct arrow direction — cam0→F1, cam0→F2, F2→cam1, cam1→F3, F3→cam2, F3→cam3), exactly 1 undirected grey redundant edge (cam2–F1, no arrowhead), title "Stage 2: Pose Graph", no "BFS" text, legend keys all correspond to drawn elements. This matches the human-verify gate's round-2 approval recorded in 18-04-SUMMARY.md, independently re-confirmed by viewing the actual PNG in this verification pass. |
| 4 | `reject_outlier_frames`, `start_frame`/`stop_frame`, intrinsics seeding, fronto-parallel warning documented in config reference + guide, not only troubleshooting | VERIFIED | `docs/guide/configuration.md` exists (created by 18-03), contains substantive sections for all four features: `reject_outlier_frames` with `frame_rejection_k`/`frame_rejection_floor_px`/`frame_rejection_max_fraction`, `start_frame`/`stop_frame` with the `extrinsic_start_frame`/`extrinsic_stop_frame` dataclass-field mapping, `CALIB_USE_INTRINSIC_GUESS` seeding rationale, and the fronto-parallel `validate_view_diversity` warning (with admonition). Page is registered in `docs/guide/index.md`'s toctree and Practical Guides list (both confirmed present) and troubleshooting.md links forward to it (>= 2 references confirmed). Sphinx build renders `docs/_build/html/guide/configuration.html`. |
| 5 | Console output, timing keys, docstrings, CLI comments present three-stage model; documented loss default reads `huber` | VERIFIED | DOCS-06 guard run directly: `grep -rn '"stage4"\|stage4_joint_refinement\|trace_stage4\|calibration_stage4' src/` returns zero matches. `grep -rnE "Stage 4" src/ --include=*.py --include=*.yaml` returns zero matches. `pipeline.py` uses `stage3_intrinsic_pass` at all chokepoints (timing key, observer tag, trace/calibration filenames, console `[Auxiliary camera registration]` label). `_observability.py`/`conditioning.py` docstring enumerations list `stage3_intrinsic_pass`. `docs/guide/optimizer.md:118` names Huber loss explicitly and states the piecewise quadratic/linear formula with `loss_scale=1.0px` as the transition, matching `schema.py:315`'s `robust_loss: str = "huber"` default. Full four-stage sweep (`grep -riE "four.stage\|four calibration stages\|Stages 2-4" docs/ README.md`) returns zero matches. |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/unit/test_optim_common.py::TestDocumentedGroupingNumbers` | Live-derived P/group/reduction assertions | VERIFIED | 7 tests, all pass, derive numbers from shipped `build_structural_column_groups` |
| `docs/guide/optimizer.md` | Corrected numbers, three-stage model, Huber loss | VERIFIED | All numeric/vocabulary/loss corrections present and cross-checked |
| `docs/_static/scripts/pose_graph.py` | Heap-replaying generator | VERIFIED | Imports `aquacal`, replays heapq logic, no hardcoded edge list, 310 lines |
| `docs/_static/diagrams/pose_graph.png` | Corrected figure | VERIFIED | Visually confirmed: correct node/edge counts, correct arrow direction, correct title/legend |
| `docs/guide/glossary.md` | Bipartite pose-graph definition | VERIFIED | Contains "Bipartite graph with two node types..." |
| `docs/guide/configuration.md` | New configuration reference page | VERIFIED | 300+ lines, all four DOCS-04 features documented substantively |
| `src/aquacal/calibration/extrinsics.py` | best-first terminology, D-11 carve-out intact | VERIFIED | Exactly 2 BFS occurrences remain, both in `_find_connected_components` |
| `src/aquacal/calibration/pipeline.py` | `stage3_intrinsic_pass` machine surface | VERIFIED | All chokepoints renamed, no `stage4` residue |
| `src/aquacal/config/schema.py`, `cli.py`, `example_config.yaml` | Three-stage docstrings/comments | VERIFIED | Zero `Stage 4` matches; `stage3_intrinsic_pass` named for on-disk artifact tags |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `tests/unit/test_optim_common.py` | `_optim_common.build_structural_column_groups` | direct call | WIRED | Test imports and calls the live function; verified by running the tests |
| `docs/_static/scripts/pose_graph.py` | `aquacal.calibration.extrinsics` | `from aquacal...import build_pose_graph` | WIRED | `grep -c "from aquacal"` >= 1; heap logic replayed |
| `docs/guide/index.md` | `docs/guide/configuration.md` | toctree + bullet | WIRED | Both entries present; Sphinx build resolves the page (no toctree warning) |
| `docs/guide/troubleshooting.md` | `docs/guide/configuration.md` | inline `{ref}` links | WIRED | >= 2 references confirmed, Sphinx build resolves refs |
| `pipeline.py` | `internals/calibration_stage3_intrinsic_pass.json` / `trace_stage3_intrinsic_pass.csv` | `_dump_stage_calibration` / `write_trace_csv` | WIRED | Confirmed via grep of the renamed call sites |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full non-slow suite green | `python -m pytest tests/ -m "not slow"` | 775 passed, 31 deselected | PASS |
| Docs build (CI-equivalent) | `python -m sphinx -W --keep-going -b html docs docs/_build/html` | build succeeded, exit 0 | PASS |
| DOCS-01 live test | `pytest tests/unit/test_optim_common.py -v -k DocumentedGroupingNumbers` | 7 passed | PASS |
| DOCS-02 BFS guard | `grep -rniE "\bBFS\b\|breadth.first" src/ docs/ README.md ... \| grep -v _build` | exactly the 2 legitimate `extrinsics.py` sites | PASS |
| DOCS-06 stage4 guard | `grep -rn '"stage4"\|stage4_joint_refinement\|trace_stage4\|calibration_stage4' src/` | zero matches | PASS |
| Four-stage sweep | `grep -riE "four.stage\|four calibration stages\|Stages 2-4" docs/ README.md` | zero matches | PASS |
| ruff | `ruff check src/ docs/_static/scripts/` | All checks passed | PASS |

### Probe Execution

Not applicable — this phase has no `scripts/*/tests/probe-*.sh` convention; the phase's own
gate commands (grep guards, pytest, sphinx-build) were run directly above and constitute the
phase's validation contract per `18-VALIDATION.md`.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| DOCS-01 | 18-01 | optimizer.md column-grouping numbers corrected | SATISFIED | Numbers verified live; test class passes |
| DOCS-02 | 18-02, 18-05, 18-08 | BFS → best-first across doc + code sites | SATISFIED | Guard returns exactly the 2 legitimate sites |
| DOCS-03 | 18-04 | Bipartite glossary + regenerated pose-graph figure | SATISFIED | Figure visually confirmed correct; generator replays real heap logic |
| DOCS-04 | 18-03 | v1.7-v1.8 features documented outside troubleshooting | SATISFIED | `configuration.md` created, registered, cross-linked |
| DOCS-06 | 18-02, 18-06, 18-07, 18-08 | Three-stage model across docs+code; loss default `huber` | SATISFIED | Guard returns zero; Huber formula matches schema default |

No orphaned requirements: DOCS-05 and DOCS-07 are correctly mapped to Phase 21/22 in
`REQUIREMENTS.md`, not this phase.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `docs/tutorials/01_full_pipeline.ipynb`, `02_synthetic_validation.ipynb` | captured output cells | Stale "Stage 4" console strings in committed notebook OUTPUT (not source narration) | INFO (NOTE, not a gap) | Explicitly out of scope for this phase per 18-CONTEXT.md/18-08-SUMMARY.md; `nbsphinx_execute = "never"` means notebooks don't re-execute during docs build; escalated to Phase 21/DATA-03, which requires a real 48-87 min calibration re-run. Confirmed present (`grep -c "Stage 4"` = 2 in each notebook) but this is a known, deliberately deferred item, not a phase-18 must-have. |
| `git log` (repo-wide, not a file) | commit `34497f9` | `fix(18): repair run_calibration_from_config docstring RST after wave 2` — a `fix:`-typed commit, which every plan's own threat-mitigation table (T-18-06-REL, T-18-08-REL) explicitly requires never happen for this phase ("commit as docs:/refactor:/test: — never feat:/fix:") | WARNING | This commit sits within `git log --oneline -20` at the time of 18-08's own gate check. 18-08-SUMMARY.md explicitly claims "No `feat:` or `fix:` commit appears in this phase — every Phase 18 commit is `docs:`/`refactor:`/`test:`, confirmed by `git log --oneline -20`" — this claim is factually false; the commit is a genuine `fix:` type and is present in the log window. Per this project's release automation (python-semantic-release: `fix:` → patch bump), this will cut an unintended patch release on the next push to `main`, which is exactly the failure mode the plan's own STRIDE register (T-18-06-REL/T-18-08-REL) was written to prevent. The change itself is a legitimate, narrowly-scoped docstring-only RST fix (verified: no numeric/behavioral change, `git show 34497f9` confirms 3 lines changed, all inside a docstring), so it does not threaten documentation/content correctness. It is flagged because the SUMMARY's self-reported verification claim does not match the actual git history — exactly the class of discrepancy this verification pass exists to catch. |

### Requirements/Success-Criteria Not Blocked

All 5 ROADMAP success criteria verified directly against the codebase (not SUMMARY claims):
numbers derived live by executing shipped code, BFS/four-stage/stage4 sweeps run fresh via
grep, figure viewed directly, full test suite and Sphinx build run fresh (not reused from
SUMMARY claims).

### Human Verification Required

None. The one item that historically required human judgment (pose-graph figure edge
direction, DOCS-03) was already gated through `checkpoint:human-verify` during execution
(18-04, round 1 caught a real bug, round 2 approved), and this verification pass
independently re-viewed the resulting PNG and confirms it matches the approved conditions.

### Gaps Summary

No blocking gaps. All 5 ROADMAP success criteria are independently verified against the
live codebase: numbers are derived from executing shipped code (not restated), the DOCS-02
and DOCS-06 grep guards return exactly their expected results, the regenerated pose-graph
figure was viewed directly and shows correct topology/direction, the configuration reference
page exists with substantive content for all four v1.7/v1.8 features and is properly wired
into the docs site, and the three-stage model with Huber loss is consistent from console
output through to the published `optimizer.md` page.

Two non-blocking notes are recorded above: (1) two tutorial notebooks retain stale "Stage 4"
text in committed OUTPUT cells — this is a known, explicitly deferred item (Phase 21/DATA-03),
not a Phase 18 must-have; (2) one `fix(18):` commit exists in the git history, which contradicts
that plan's own no-fix-commits mitigation and 18-08-SUMMARY.md's explicit (and inaccurate)
claim that no such commit exists — flagged as a WARNING for awareness of the coming
unintended patch-release cut, not because it affects documentation correctness.

---

_Verified: 2026-07-24_
_Verifier: Claude (gsd-verifier)_
