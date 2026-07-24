# Phase 18: Documentation Corrections & Stage-Model Reconciliation - Research

**Researched:** 2026-07-24
**Domain:** Documentation correction / terminology reconciliation in a mature Python library (no new code behavior)
**Confidence:** HIGH for Q1 (numbers re-derived live against shipped code); MEDIUM-LOW for Q2/Q3 (manuscript found, but it contradicts the locked vocabulary — see below); HIGH for Q4 (negative-result search) and Q5 (build mechanics confirmed by reading conf.py/Makefile/CI)

## Summary

This is a quick, tightly-scoped research pass answering five specific questions, not a
domain survey. The headline result: **Q1's numbers are fully CONFIRMED** by running the
actual shipped `build_jacobian_sparsity` + `build_structural_column_groups` functions
against a real 13-camera/100-frame synthetic scenario — every digit in D-20/D-22/D-08
checks out exactly. **Q2 surfaces a genuine contradiction the planner must carry forward**:
the one manuscript file findable on disk (`C:\Users\tucke\Desktop\main.pdf`) explicitly
describes a **four**-stage pipeline and uses **BFS** terminology throughout (abstract,
Figure 1 caption, Figure 2 title "Stage 2: BFS Pose Graph", body prose) — the *opposite* of
what CONTEXT.md's D-04/D-05/D-02 lock in. This PDF is dated 2026-06-15 and its metadata
table still says code version `v1.6.0`, so it is almost certainly the pre-revision
submission, not the in-progress revision the milestone's worklists describe — but no
newer draft exists anywhere on disk to confirm that. Q3 has a concrete recommendation
(collapse "Stage 4b" into "Stage 3b" unconditionally, move the DOF distinction into the
print body). Q4 is a clean negative result — no supplement pose-graph generator exists on
disk anywhere searched; the in-repo fallback is sketched in detail, including which real
`extrinsics.py` functions to replay and why the manuscript's own 4-camera/3-frame example
is the correct reference case. Q5 confirms CI already runs `sphinx-build -W --keep-going`,
so a broken image reference from the figure rename **will** fail CI, not just warn.

**Primary recommendation:** Proceed with the CONTEXT.md-locked vocabulary (three-stage
model, `stage3_intrinsic_pass`, best-first terminology) as planned — it is a locked
decision from `/gsd:discuss-phase` and this research does not have standing to override
it. But surface the main.pdf contradiction to the user as an explicit, blocking
confirmation step before the terminology rename lands (this sharpens D-07's existing
"surface as a confirmation item" instruction — it is no longer hypothetical, there is now
a concrete conflicting source).

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01**: The rename cuts through to machine-readable surfaces (timing keys, console
  output, docstrings, CLI comments, `internals/` filenames, JSON `stage` tags), not just
  prose. Reason: Phases 16-17 are unreleased, so this is the last free-change window.
- **D-02**: `internals/` artifact filenames and conditioning `stage` tags included even
  though DOCS-06's literal requirement text doesn't name them — flagged as a deliberate
  extension.
- **D-03**: No backward-compat shim for old keys — clean cut, recorded via conventional
  commit.
- **D-04**: Three stages — (1) in-air intrinsics, (2) extrinsic init, (3) joint refractive
  BA. Intrinsic refinement is a mode/pass of Stage 3, not a fourth stage.
- **D-05**: Ex-Stage-4 is called **"Stage 3's optional intrinsic pass"** in prose/console
  (worklist wording, `aquacal-post-review-milestone.md:52`).
- **D-06**: Machine key form is `stage3_intrinsic_pass`. `timings["stage4_joint_refinement"]`
  → `timings["stage3_intrinsic_pass"]`; `internals/calibration_stage4.json` →
  `internals/calibration_stage3_intrinsic_pass.json`; `internals/trace_stage4.csv` →
  `internals/trace_stage3_intrinsic_pass.csv`; conditioning `stage` tag `"stage4"` →
  `"stage3_intrinsic_pass"`. `"stage3_rerun"` is unaffected.
- **D-07 ⚠**: The exact stage names must be confirmed against the manuscript before the
  rename lands — the paper is not in this repo and the worklist infers wording without
  quoting the paper verbatim. **This research found a manuscript on disk that contradicts
  the inferred wording — see the Answers section, Q2.** Do not silently proceed if the
  manuscript is reachable; it was reached, and it disagrees.
- **D-08**: `docs/guide/optimizer.md:120` fixes both the loss name AND formula — code
  default is `robust_loss = "huber"` (`config/schema.py:314`), page currently shows the
  soft-L1 formula. Replace with Huber ρ, state `loss_scale` (1.0 px) as the transition
  point.
- **D-09**: Port the paper supplement's corrected multi-panel pose-graph generator into
  `docs/_static/scripts/`, following the `bfs_pose_graph.py`/`sparsity_pattern.py` +
  `palette.py` convention. **Fallback if unavailable** (this research confirms it IS
  unavailable — see Q4): write the generator in-repo, replaying `estimate_extrinsics`'s
  heap directly.
- **D-10**: Rename the figure to `pose_graph.png`, update every reference including alt
  text, delete the old file (no dual-file period).
- **D-11**: `_find_connected_components` (`extrinsics.py:200,208`) is left untouched — it
  genuinely is BFS and correctly named. Hard carve-out.
- **D-12**: The two misleading "score each neighbour" comments (`extrinsics.py:601,654`)
  are corrected. The optional `sorted()` consistency nit (§1.4 of the fixes doc) is
  declined — cosmetic, no behavioral effect.
- **D-13**: Add the "finalised on first discovery" invariant to the `estimate_extrinsics`
  docstring — distinguishes the traversal from Prim's algorithm.
- **D-14**: Create a dedicated `docs/guide/configuration.md` reference page.
- **D-15**: Troubleshooting keeps its `reject_outlier_frames`/`start_frame`/`stop_frame`
  entries but stops being the sole home; gains links to the new reference.
- **D-16**: Link the new page from `docs/guide/index.md`; fix that file's "Four-stage
  calibration pipeline" line in the same edit.
- **D-17**: Sweep scope for terminology fixes is `src/`, `docs/`, `README.md` — grep-and-
  verify, not just the enumerated line numbers (line numbers have moved).
- **D-18**: `.planning/` and `CHANGELOG.md` are historical records — untouched.
- **D-19**: `CLAUDE.md` says "Four-stage calibration pipeline" and should be corrected, but
  it is gitignored — edit is local-only, cannot be committed or reported as a committed
  change. `.claude/rules/*.md` IS tracked, if any stage language turns up there (this
  research did not find any).
- **D-20**: DOCS-01 figures are asserted by a test, not just written into prose — derive
  group count and P live from `build_jacobian_sparsity` + `build_structural_column_groups`
  for the documented configurations. **This research prototypes exactly that test — see
  Q1 and Validation Architecture below.**
- **D-21 ⚠**: Re-derive numbers against the shipped structural-grouping path (not
  `scipy.optimize._numdiff.group_columns`, which the fixes doc's numbers predate). **Done
  in this research — see Q1, fully confirmed.**
- **D-22**: Fix all four `optimizer.md` numeric errors together: `~12×` → 43-52×; "at most
  14-17 columns" → 13-17; "~630 parameters" → 673/675/727; keep "98% sparse" (13/673 =
  1.9% nonzero, correct); state the group-count-is-rig-size-invariant point explicitly.

### Claude's Discretion

- Exact prose wording of every replacement string (fixes doc's suggestions are a starting
  point, not a mandate).
- Internal organization of `docs/guide/configuration.md` (by config section vs. workflow),
  and how much it duplicates vs. cross-links `docs/api/config.rst`.
- Plan decomposition — whether the stage rename, terminology sweep, and new config page
  are one plan or several.
- Whether the DOCS-01 assertion test lives in `tests/unit/` beside optimizer tests or in a
  small docs-consistency test module.
- Whether the corrected pose-graph figure keeps the multi-panel layout or is reduced to a
  single panel.

### Deferred Ideas (OUT OF SCOPE)

- `extrinsics.py:602` `sorted()` consistency nit — declined, cosmetic only.
- Documenting what this milestone adds (`calc-index`, `benchmark.json` schema, trace/
  conditioning flags, full `shared_interface` write-up) → Phase 21 (DOCS-05).
- Notebook re-execution and stale "Stage 4 RMS" narration → Phase 21 (DATA-03).
- The dissertation's `appendix-a.tex` carrying the same wrong grouping claim — outside
  this repo, flagged for the user only.
- Zenodo dataset upload, memory/CPU reduction — reviewed and explicitly declined for this
  phase, sequenced elsewhere.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DOCS-01 | `optimizer.md` column-grouping numbers corrected (13/17 groups, P=673/675/727, 43-52× reduction) | Q1 — every figure re-derived live and CONFIRMED against the shipped `build_structural_column_groups` path (not the stale `group_columns` measurement); see table below |
| DOCS-02 | BFS → best-first terminology corrected across doc + code sites, `_find_connected_components` untouched | Pattern map (18-PATTERNS.md) already has exact line numbers; this research adds the Q2 caveat that the manuscript on disk still says "BFS" |
| DOCS-03 | Glossary pose-graph definition corrected (bipartite), figure regenerated from a heap-replaying script | Q4 — confirms no external generator exists; sketches the in-repo fallback contract against real `extrinsics.py` functions |
| DOCS-04 | v1.7-v1.8 features documented in configuration reference + guide pages | Not separately researched here — pattern map already has the page skeleton and cross-link conventions; no open technical question |
| DOCS-06 | Three-stage model + `huber` loss correction across docs and code | Q1 confirms the loss default (`huber`, `config/schema.py:314`); Q2/Q3 are the open items — manuscript contradiction and the Stage-4b/3b naming decision |

## Answers

**Q1 — CONFIRMED, no changes needed to the D-20/D-22 numbers.** Ran
`build_jacobian_sparsity` + `build_structural_column_groups` directly (the shipped
post-quick-task-3 path) against a real synthetic 13-camera/100-frame scenario generated
via `generate_camera_array` + `generate_board_trajectory` +
`generate_synthetic_detections`. Every claimed figure reproduces exactly: P = 673 (base) /
675 (tilt) / 727 (tilt+intrinsics); groups = 13 / 13 / 17; reduction = 51.8× / 51.9× /
42.8× (rounds to the doc's 52×/52×/43×, inside the stated 43-52× range); max nonzeros per
residual row = 13 / 13 / 17, matching the "13-17 columns" claim exactly. The analytic
formula `P = tilt(0|2) + 6·(n_cams-1) + 1 + 6·n_frames + (4·n_cams if intrinsics)` also
reproduces all three P values with no synthetic data needed at all — useful for the D-20
assertion test, which does not need to construct real detections for the P/group-count
half of the claim (only the max-row-nonzeros half needs a `DetectionResult`, and even that
is deterministic/mode-only, not visibility-dependent, once at least one full-visibility
row exists).

**Q2 — NOT confirmable as written; a conflicting manuscript was found.**
`C:\Users\tucke\Desktop\main.pdf` (dated 2026-06-15, C1 metadata cell says code version
`v1.6.0`) is titled "AquaCal: refraction-aware multi-camera calibration for planar
air-water interfaces" and is unambiguously the AquaCal SoftwareX paper. It explicitly
describes a **"Four-stage calibration pipeline"** (verbatim subsection heading, p.7),
with "Stage 4 is an optional refinement that re-introduces the per-camera focal length and
principal point into the joint optimization... It is offered as an optional pass because
Stage 1 already constrains the intrinsics tightly in air." It uses **"BFS"** throughout,
including in the abstract ("BFS-initialized extrinsics"), the intro ("breadth-first search
over the camera-frame bipartite graph"), and Figure 2's own title, "Stage 2: BFS Pose
Graph" with a legend entry "BFS discovery edge (directed)". It also states the *old,
wrong* grouping numbers this milestone exists to fix: "reducing the number of finite-
difference evaluations from ∼685 to ∼50 for a 12-camera, 100-frame problem" (p.8) — the
same figure DOCS-01 is correcting in the docs. No other file on the Desktop or in the
searched folders (`Aqua/`, `Calibration/`, `WhiteMatter/`) contains a newer draft, a
reviewer-response letter, or any alternate stage/BFS vocabulary. **Recommendation:**
do not treat this PDF as ground truth for the rename (it predates the milestone's own
worklists by 5+ weeks and every internal signal — the C1 version, the wrong grouping
number, the "four-stage" heading — points to it being the pre-revision submission). But
this is exactly the scenario D-07 anticipated ("do not silently proceed... if the
manuscript is reachable") — except here proceeding silently is *worse* than D-07 assumed,
because the reachable manuscript actively disagrees rather than being merely absent. The
planner should keep the CONTEXT.md-locked vocabulary (it is what the worklist authors —
presumably working from a revision draft not present on disk — specified), but insert an
explicit `checkpoint:human-verify` task before the stage-rename plan lands, asking the
user to confirm the revised manuscript's stage vocabulary and BFS/best-first wording
against a source newer than `main.pdf`.

**Q3 — Concrete recommendation: collapse to `"Stage 3b"` unconditionally.**
`pipeline.py:1373`'s `"Stage 4b"`/`"Stage 3b"` labels the **auxiliary**-camera
registration sub-step, which always runs *after* whichever primary path just finished
(Stage 3 alone, or Stage 3 + its intrinsic pass) — it is a post-hoc step against frozen
board poses, not a numbered pipeline stage of its own (confirmed by
`pipeline.py:1381-1409`: it is timed as `"auxiliary_registration"`, already a
stage-agnostic key that needs no rename). The manuscript itself (main.pdf, p.8,
"Auxiliary camera registration" paragraph) frames it the same way: "Once the primary
cameras converge, auxiliary cameras are registered post-hoc... via refractive PnP
initialization, followed by either a 6-DOF refinement (extrinsics only) or a 10-DOF
refinement (extrinsics, focal length, and principal point)" — no "3b/4b" distinction
appears there at all; the DOF count is what actually varies, driven by
`refine_auxiliary_intrinsics`, which is an independent flag from whether the *primary*
intrinsic pass ran. Under the three-stage model there is no "Stage 4" numeral left to
suffix, so the "4b" branch stops making sense. Recommended change:
```python
stage_label = "Stage 3b"  # always — auxiliary registration follows Stage 3 either way
dof_desc = (
    "10-DOF: extrinsics + intrinsics"
    if config.refine_auxiliary_intrinsics
    else "6-DOF: extrinsics only"
)
print(f"\n[{stage_label}] Registering {len(config.auxiliary_cameras)} "
      f"auxiliary camera(s) ({dof_desc})...")
```
This preserves the useful information (which refinement depth ran) without resurrecting a
stage number that no longer exists. Also update the two adjacent code comments at
`pipeline.py:1369` (`# --- Stage 3b/4b: Register Auxiliary Cameras ---` → `# --- Stage 3b:
Register Auxiliary Cameras ---`).

**Q4 — Not found; in-repo fallback is required (D-09's fallback path).**
Searched all Desktop locations named in the phase brief plus a full-tree grep for
`pose_graph`/`pose-graph`/`BFS`/`supplement` across the Desktop: no standalone pose-graph
figure generator script, notebook, or supplement PDF/zip exists anywhere on disk outside
this repo's own `docs/_static/scripts/bfs_pose_graph.py`. The fallback generator must
replay `estimate_extrinsics`'s actual heap traversal
(`src/aquacal/calibration/extrinsics.py:583-680`, the priority-queue loop keyed by
`(-num_corners, node)`, per the pattern map's already-extracted excerpts) rather than
hand-authoring a fixed edge list — importing and instrumenting the real function (e.g. via
a debug/observer hook, or by re-running the same heap logic inline against a small
synthetic pose graph) is the only way to satisfy success criterion 3's "cannot drift from
the code." **Use the manuscript's own Figure 2 example as the reference case**: 4 cameras
+ 3 frames, spanning tree of exactly 6 directed discovery edges (teal in the manuscript),
1 redundant grey undirected observation edge left over (matches both the fixes doc §2.6
and the manuscript's actual rendered figure, which the planner can treat as a visual
reference for what "correct" looks like — though note the manuscript figure omits the
undirected redundant edge is drawn as directed too, a defect the fixes doc calls out
independently). Concretely, the fallback generator should: build a small synthetic
`camera_positions`/`board_poses` fixture with exactly this 4-camera/3-frame topology
(one observation edge deliberately redundant, i.e. one frame observed by two already-
resolved cameras), call `estimate_extrinsics` (or the internal pose-graph-construction +
heap-traversal helpers it composes) with instrumentation to record pop order and
discovery edges, then render camera nodes (left column), frame nodes (right column),
grey undirected edges for all observations, teal directed edges only for the edges that
were the actual discovery edge in the traversal, and numeric badges showing discovery
order — mirroring the existing `bfs_pose_graph.py`'s visual style but sourcing edges from
a live traversal rather than a hardcoded `EDGES`/`BFS_EDGES` list.

**Q5 — Exact commands and mechanics confirmed by reading `conf.py`, the `Makefile`, and
CI.** (a) CI (`.github/workflows/docs.yml:30`) runs
`sphinx-build -W --keep-going -b html docs docs/_build/html` — `-W` turns *all* Sphinx
warnings into build failures, `--keep-going` just collects them all before exiting
nonzero. There is no separate `nitpick_ignore`/nitpicky setting in `conf.py`. This means a
dangling reference to the old `bfs_pose_graph.png` filename (in `optimizer.md`'s image
directive or alt text) — or a `generate_all.py` that still imports the deleted
`bfs_pose_graph` module — **will fail CI**, not just print a warning; the local
`make html` build with default `SPHINXOPTS` (empty, no `-W`) would only warn, so testing
locally with plain `make html` is not sufficient — must use the `-W` form to match CI.
Separately, `conf.py`'s `run_diagram_generation` hook (a `config-inited` callback) wraps
the `generate_all.py` subprocess call in a bare `except subprocess.CalledProcessError:
print(...)` — a crash inside the new `pose_graph.py` generator is **swallowed silently**
at that point and the build continues; it only surfaces later as a missing-image warning
(which `-W` then turns into a failure), so a plan task must actually run
`python docs/guide/_diagrams/generate_all.py` standalone first to see generator errors
directly rather than relying on the Sphinx build to surface them clearly. (b) New pages
register in two places in `docs/guide/index.md`: the bulleted "Practical Guides" list
*and* the hidden `:::{toctree}` block (`:hidden:` `:maxdepth: 2`) — both are shown
verbatim in the pattern map (18-PATTERNS.md §1); omitting the toctree entry produces a
"document isn't included in any toctree" warning, which `-W` also turns into a failure.
(c) Cheapest proof commands for a plan task, in order of cost:
```bash
python docs/guide/_diagrams/generate_all.py        # fast: catches generator crashes directly
sphinx-build -W --keep-going -b html docs docs/_build/html   # matches CI exactly
```
No `make`-wrapper equivalent is needed since the Makefile just forwards to
`sphinx-build -M html . _build` without `-W` by default — the explicit `sphinx-build -W`
invocation above is what actually matches CI and should be the command the plan's
verification step runs, not `make html`.

## DOCS-01 Numbers — Measured (this session) vs. Claimed

| Configuration | P (claimed) | P (measured) | Groups (claimed) | Groups (measured) | Max row nnz (measured) | Reduction (claimed) | Reduction (measured) |
|---|---|---|---|---|---|---|---|
| base (`shared_interface=True`, `normal_fixed=True`, `refine_intrinsics=False`) | 673 | **673** ✓ | 13 | **13** ✓ | 13 | 52× | **51.8×** ✓ |
| tilt (`normal_fixed=False`) | 675 | **675** ✓ | 13 | **13** ✓ | 13 | 52× | **51.9×** ✓ |
| tilt + intrinsic refinement | 727 | **727** ✓ | 17 | **17** ✓ | 17 | 43× | **42.8×** ✓ |

**Method:** synthetic 13-camera / 100-board-pose scenario built with
`generate_camera_array(n_cameras=13, layout="grid", spacing=0.15, height_above_water=0.2,
height_variation=0.02, seed=1)` + `generate_board_trajectory(n_frames=100, ..., seed=1)` +
`generate_synthetic_detections(..., noise_std=0.3, min_corners=8, seed=1)`; `frame_order`
built from all 100 generated board poses (not just the ~77 that ended up with detections
above `min_corners` in every camera — the parameter count is driven by the frame *order*
passed to `build_jacobian_sparsity`/`build_structural_column_groups`, i.e. by how many
board placements are being optimized, not by per-camera visibility). Confirmed against
scipy 1.17.0 (project floor `>=1.7`, HOOK-02 raised the effective floor to `>=1.16` for
`least_squares(callback=...)`, unrelated to this path). `build_structural_column_groups`'s
own module docstring already states the same 13/17 lower-bound claim
(`_optim_common.py:388-394`) — this research is independent confirmation via direct
execution, not just reading the docstring's assertion.

Also cross-checked analytically (no synthetic data at all, using
`P = tilt(0|2) + 6*(n_cams-1) + 1 + 6*n_frames + (4*n_cams if refine_intrinsics)`): 673 /
675 / 727 for n_cams=13, n_frames=100 — identical to the measured values, confirming the
formula in D-20's future assertion test can validate P without constructing a
`DetectionResult` at all (only the max-row-nonzeros / group-count claim needs a live
sparsity pattern, and that pattern's row-nonzero-count is mode-determined, not
detection-count-determined, once at least one row of each observation-type exists).

**Where the D-20 assertion test should live and what it should assert:** Recommend
`tests/unit/test_optim_common.py` (create if it does not exist — `_optim_common.py`
currently has no dedicated unit test file per the pattern map's file inventory; existing
coverage of these functions lives inside `test_pipeline.py`/`test_interface_estimation.py`
end-to-end tests, not as isolated grouping-count assertions) — this keeps it beside the
functions it is testing rather than a separate docs-consistency module, since the
assertion is really "these production functions produce these numbers," not "this doc
page's prose matches some independent oracle." Assert, parametrized over the three
configurations in the table above, using a small but non-trivial synthetic detection set
(the `create_scenario('realistic')` 12-camera/30-frame preset is close but not
13/100 — recommend a custom `generate_camera_array(n_cameras=13, ...)` +
`generate_board_trajectory(n_frames=100, ...)` fixture matching the docs' own worked
example so the test and the prose describe literally the same scenario):
1. `sparsity.shape[1] == P` for each of the three P values quoted in the docs (673/675/727)
2. `groups.max() + 1 == group_count` for each of the three group counts (13/13/17)
3. `int(sparsity.sum(axis=1).max()) == group_count` (the "max columns touched per row"
   claim, which is what the "13-17 columns" doc language actually describes)
This directly guards against the exact failure mode that produced the original error: a
future change to `_optim_common.py`'s parameter layout silently invalidating the prose
without any test failing.

## Package Legitimacy Audit

Not applicable — this phase installs no new external packages (documentation, string
renames, and one new pure-Python diagram-generator script using already-installed
`matplotlib`/`numpy`).

## Common Pitfalls

### Pitfall 1: Testing the docs build with `make html` instead of the CI-equivalent command
**What goes wrong:** `make html` uses empty `SPHINXOPTS` by default, so warnings (broken
image references, missing toctree entries) print but do not fail the build locally, then
fail in CI.
**Why it happens:** The Makefile's default target doesn't encode `-W`; only the CI
workflow file does.
**How to avoid:** Always verify with `sphinx-build -W --keep-going -b html docs
docs/_build/html` (see Q5), matching `.github/workflows/docs.yml:30` exactly.
**Warning signs:** A green local `make html` run followed by a red CI docs job on the PR.

### Pitfall 2: Diagram-generation subprocess failures are swallowed
**What goes wrong:** `conf.py`'s `run_diagram_generation` catches
`CalledProcessError` and only prints a warning; a broken `pose_graph.py` generator does
not stop the Sphinx build at the point it fails.
**Why it happens:** The hook is designed to tolerate missing/optional diagram scripts
gracefully, but this also hides real bugs in the new generator until later, less legible
failure output (a missing-image warning far from the actual stack trace).
**How to avoid:** Run `python docs/guide/_diagrams/generate_all.py` standalone as a first
verification step before the full Sphinx build.
**Warning signs:** Sphinx build fails with "image file not readable: pose_graph.png" but
no Python traceback is visible anywhere in the build log.

### Pitfall 3: Blind find-and-replace over "BFS", "Stage 4", or the grouping numbers
**What goes wrong:** `_find_connected_components` genuinely is BFS (D-11); the "Why BFS?"
paragraph body (not just its heading) is factually correct and only the heading word is
wrong; "98% sparse" is already correct math and must not be touched by a numbers sweep.
**Why it happens:** A regex-driven sweep can't distinguish "this instance is wrong" from
"this instance happens to contain the same substring and is correct."
**How to avoid:** Scope every edit to the specific line numbers already extracted verbatim
in `18-PATTERNS.md`, using D-17's grep sweep only to find candidates beyond that floor,
not as the edit mechanism itself.
**Warning signs:** A diff that touches `extrinsics.py:200-214` or the "98% sparse" line.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (project-wide; `[tool.pytest.ini_options]` in `pyproject.toml`, `slow` marker for optimization-heavy tests) |
| Config file | `pyproject.toml` |
| Quick run command | `python -m pytest tests/unit/test_optim_common.py -v` (new file, per Q1/D-20 recommendation) |
| Full suite command | `python -m pytest tests/ -m "not slow"` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DOCS-01 | Group count / P / reduction numbers stay correct as `_optim_common.py` evolves | unit | `pytest tests/unit/test_optim_common.py -v -k grouping_numbers` | ❌ Wave 0 (create `tests/unit/test_optim_common.py`) |
| DOCS-02 | No remaining "BFS" outside `_find_connected_components` in `src/`, `docs/`, `README.md` | grep guard (not pytest — see below) | `grep -rn "BFS\|breadth.first" src/ docs/ README.md \| grep -v "_find_connected_components\|extrinsics.py:20[08]"` | N/A — shell-level guard, document as a manual/CI grep step rather than a pytest test |
| DOCS-03 | Regenerated `pose_graph.png` exists, old `bfs_pose_graph.png` deleted, generator runs cleanly | smoke | `python docs/guide/_diagrams/generate_all.py && test -f docs/_static/diagrams/pose_graph.png && test ! -f docs/_static/diagrams/bfs_pose_graph.png` | ❌ Wave 0 (shell smoke check, not a pytest file) |
| DOCS-06 | Stage-tag rename is consistent — no stray `"stage4"` literal anywhere in `src/` | grep guard | `grep -rn "\"stage4\"\|stage4_joint_refinement\|trace_stage4\|calibration_stage4" src/` (expect zero matches) | N/A — shell-level guard |
| DOCS-06 | Pipeline tests assert the new stage-key literals, not the old ones | unit (existing files, edited in place) | `pytest tests/unit/test_pipeline.py tests/unit/test_refinement.py tests/unit/test_observability.py -v` | ✅ existing — literals inside them are what changes (see 18-PATTERNS.md §4 table) |
| Docs build | Full site builds warning-free after all edits | build check | `python docs/guide/_diagrams/generate_all.py && sphinx-build -W --keep-going -b html docs docs/_build/html` | ✅ existing tooling — this is the phase-gate check, not a new test file |

### Sampling Rate
- **Per task commit:** the relevant unit test file for whatever code was touched
  (`test_optim_common.py` for the DOCS-01 assertion; `test_pipeline.py` et al. for the
  stage-key rename) plus, for any docs-touching task, the two grep guards above.
- **Per wave merge:** `python -m pytest tests/ -m "not slow"` plus the full docs build
  command from Q5.
- **Phase gate:** full suite green (`python -m pytest tests/`) AND the docs build command
  exits 0 AND both grep guards return zero matches, before `/gsd:verify-work`.

### Wave 0 Gaps
- [ ] `tests/unit/test_optim_common.py` — new file, covers DOCS-01 (see the assertion
  spec in the "DOCS-01 Numbers" section above)
- [ ] No fixture/framework gaps — pytest and the `slow` marker are already configured;
  the synthetic-scenario helpers this test needs (`generate_camera_array`,
  `generate_board_trajectory`, `generate_synthetic_detections`) already exist and are
  demonstrated working in this research session's script.
- [ ] The DOCS-02/DOCS-06 grep guards are not pytest tests by design (they check for the
  *absence* of a stale string across three directories, which is cheaper and more direct
  as a shell one-liner than a Python test walking the filesystem) — the plan should still
  record them as an explicit verification step, e.g. as a documented command in the
  phase's VERIFICATION notes, not silently rely on manual review.

## Sources

### Primary (HIGH confidence — direct execution / direct file reads)
- `src/aquacal/calibration/_optim_common.py` — read in full; `build_jacobian_sparsity`,
  `build_structural_column_groups`, `pack_params`/`unpack_params` executed directly this
  session against scipy 1.17.0
- `src/aquacal/datasets/synthetic.py` — `generate_camera_array`, `generate_board_trajectory`,
  `generate_synthetic_detections`, `generate_real_rig_array`, `create_scenario` read and
  exercised
- `src/aquacal/calibration/pipeline.py:1330-1420` — read directly for the Q3 answer
- `docs/conf.py`, `docs/Makefile`, `.github/workflows/docs.yml`,
  `docs/guide/_diagrams/generate_all.py` — read in full for Q5
- `C:\Users\tucke\Desktop\main.pdf` (pages 1-8) — read directly for Q2/Q3; this IS the
  AquaCal SoftwareX manuscript (title, author, abstract match), dated 2026-06-15
- `C:\Users\tucke\Desktop\aquacal-post-review-milestone.md`,
  `C:\Users\tucke\Desktop\aquacal-docs-accuracy-fixes.md` — read in full

### Secondary (MEDIUM confidence)
- `.planning/phases/18-documentation-corrections-stage-model-reconciliation/18-PATTERNS.md`
  and `18-CONTEXT.md` — treated as authoritative for locked decisions and exact line
  numbers (already independently verified by the pattern-mapping agent's own file reads),
  not re-verified line-by-line in this session except where directly relevant to the five
  research questions

### Tertiary (LOW confidence / explicitly unresolved)
- Whether the *current, in-revision* manuscript draft (as opposed to the `main.pdf` found
  on disk) actually uses the three-stage/best-first vocabulary the worklists claim — **not
  verified**, and the one available data point (main.pdf) contradicts it. Flagged as an
  open question below, not papered over.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The worklist's assertion that "the SoftwareX paper uses a code-grounded three-stage model" and "best-first" wording refers to a revision draft not present on disk, rather than being simply incorrect | Q2 | If wrong, the entire stage-rename (D-01 through D-08) and BFS->best-first sweep (D-02, D-09-D-13) would need to be reverted to match the actually-submitted paper, after already touching machine-readable keys per D-01 — expensive to unwind post-hoc |
| A2 | The manuscript's Figure 2 (4 cameras, 3 frames) is an appropriate reference topology for the D-09 fallback generator, even though its own rendering has the redundant-edge defect the fixes doc flags | Q4 | Low risk — this is about topology (node/edge counts), not about copying the manuscript figure's rendering choices, which are explicitly called out as needing correction |

**If this table is empty:** N/A — see above.

## Open Questions

1. **Does the manuscript draft actually being revised for the 2026-08-21 deadline use the
   three-stage / best-first vocabulary the worklists assume?**
   - What we know: the only manuscript file reachable on disk (`main.pdf`) uses four
     stages and BFS terminology, and is dated/versioned as a pre-revision snapshot.
   - What's unclear: whether a newer draft exists (e.g. in an Overleaf project, a
     reviewer-response letter, or local files not on the Desktop) that actually confirms
     the target vocabulary.
   - Recommendation: insert a `checkpoint:human-verify` task early in the phase's plan,
     before any stage-rename or BFS-rename edits land, asking the user to either (a) point
     at the current revision draft so it can be checked, or (b) explicitly confirm
     proceeding on the CONTEXT.md-locked vocabulary regardless. Do not block the whole
     phase on this — DOCS-01 (the numeric fix) and DOCS-04 (the new config page) do not
     depend on the answer and can proceed immediately.

2. **Should the DOCS-02 BFS sweep also touch `main.pdf`'s own source (if the user
   controls a `.tex`/Overleaf source for the paper)?**
   - What we know: the paper source is outside this repo and explicitly out of scope
     ("Manuscript prose and figures... written outside the repo" per REQUIREMENTS.md Out
     of Scope table).
   - What's unclear: nothing technically — this is a scope reminder, not a gap.
   - Recommendation: no action in this phase; flagged only so the confirmation task in
     Open Question 1 doesn't accidentally scope-creep into editing the manuscript itself.

## Metadata

**Confidence breakdown:**
- Q1 (DOCS-01 numbers): HIGH — measured via direct execution against the shipped code
  path, cross-checked analytically, matches claimed values exactly
- Q2 (manuscript stage/BFS vocabulary): MEDIUM confidence that main.pdf is stale/pre-
  revision (supported by version metadata + date), but LOW confidence on what the actual
  current draft says, because no current draft was found
- Q3 (Stage 4b/3b): HIGH — read the actual code and the manuscript's own description of
  the same mechanism, they agree with each other
- Q4 (supplement generator search): HIGH confidence in the negative result (thorough
  search of all named + reasonable candidate locations); the fallback sketch is a design
  recommendation, not a verified fact
- Q5 (docs build mechanics): HIGH — read `conf.py`, `Makefile`, and the CI workflow file
  directly, no inference involved

**Research date:** 2026-07-24
**Valid until:** Effectively indefinite for Q1/Q5 (stable code paths); Q2/Q3 should be
re-checked the moment a newer manuscript draft becomes available, since they gate the
rename this phase performs
