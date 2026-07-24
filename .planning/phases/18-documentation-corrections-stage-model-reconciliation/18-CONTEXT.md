# Phase 18: Documentation Corrections & Stage-Model Reconciliation - Context

**Gathered:** 2026-07-24
**Status:** Ready for planning
**Mode:** `--auto` (all gray areas auto-resolved to the recommended option; see the
`[auto]` log lines in `18-DISCUSSION-LOG.md`)

<domain>
## Phase Boundary

Fix live factual errors in published documentation (DOCS-01, DOCS-02, DOCS-03), give the
v1.7–v1.8 features a proper documented home (DOCS-04), and reconcile the paper's
**three-stage** pipeline model across **both docs and code surfaces** (DOCS-06) — so the
stage vocabulary is settled before Phase 19 writes it into `benchmark.json`.

This is a **correction pass, not an expansion**. DOCS-04 is the one place new text is
written for features that have no proper home today.

**In scope:** DOCS-01, DOCS-02, DOCS-03, DOCS-04, DOCS-06.

**Out of scope:**
- DOCS-05 (documenting what *this milestone* adds — `calc-index`, `benchmark.json`
  schema, trace/conditioning flags, `shared_interface` write-up) → **Phase 21**
- DOCS-07 (release cut, C1 metadata, Zenodo reference) → **Phase 22**
- Dataset regeneration and notebook re-execution (DATA-01/02/03) → **Phase 21**
- Any behavioral change. The stage rename touches *strings, keys, filenames, and
  docstrings only* — no numerics, no control flow.

</domain>

<decisions>
## Implementation Decisions

### Stage-model reconciliation depth (DOCS-06)

- **D-01: The rename cuts all the way through to machine-readable surfaces**, not just
  prose. Timing keys, console output, module/schema docstrings, CLI config comments,
  **and** the `internals/` stage-tagged artifact filenames and JSON `stage` tags all move
  to the three-stage vocabulary in this phase.
  **Why now:** Phases 16–17 are unreleased on local `main`. This is the last moment the
  schema is free to change without breaking a published artifact or forcing an experiment
  re-run — which is precisely the reason DOCS-06 gates BENCH-04.
- **D-02: The `internals/` artifact filenames and conditioning `stage` tags are included**
  even though DOCS-06's requirement text names only "console output, timing keys,
  `benchmark.json` keys, module and schema docstrings, and CLI config comments". Leaving
  `trace_stage4.csv` sitting beside a `stage3_*` timing key reintroduces exactly the
  inconsistency the requirement exists to close. **Flagged for the planner as a
  deliberate extension one step past the literal requirement list** — if it is split out,
  split it into its own plan rather than dropping it.
- **D-03: No backward-compatibility shim for the old keys.** Nothing outside the repo
  consumes them (unreleased), and a compat alias would recreate the two-vocabularies
  problem. The rename is a clean cut, recorded in the changelog by the conventional
  commit.

### The three-stage vocabulary (DOCS-06)

- **D-04: Three stages — (1) in-air intrinsics, (2) extrinsic initialization,
  (3) joint refractive bundle adjustment.** Intrinsic refinement is a **mode/pass of
  Stage 3**, not a fourth stage.
- **D-05 (REVISED 2026-07-24): The ex-Stage-4 is described as "Stage 3's second pass, with
  intrinsics unlocked"** in prose and console output. Superseding the earlier inferred
  "optional intrinsic pass" wording: the live manuscript's own words are
  "**Stage~3 runs a second time**, warm-started with each camera's focal length and
  principal point unlocked" and "**The second pass is optional**"
  (`main.tex:215,218`). Match the paper's framing — a *second run of Stage 3*, not a
  differently-named stage.
- **D-06: Machine key form is `stage3_intrinsic_pass`.** Concretely:
  `timings["stage4_joint_refinement"]` → `timings["stage3_intrinsic_pass"]`;
  `internals/calibration_stage4.json` → `internals/calibration_stage3_intrinsic_pass.json`;
  `internals/trace_stage4.csv` → `internals/trace_stage3_intrinsic_pass.csv`;
  conditioning/dump `stage` tag `"stage4"` → `"stage3_intrinsic_pass"`.
  `"stage3_rerun"` (the post-outlier-rejection re-solve) is unaffected and keeps its name.
- **D-07 (RESOLVED 2026-07-24): the vocabulary is confirmed against the live manuscript.**
  The paper source lives outside this repo at
  `C:\Users\tucke\OneDrive - Georgia Institute of Technology\Thesis\Spinoffs\papers\aquacal\`
  — `main.tex` (2026-06-29) and `supplement.tex` (2026-07-23). Both confirm the locked
  decisions:
  - **Three stages.** `main.tex:208` — `\textbf{Three-stage calibration.}` Stage 1 = in-air
    intrinsics, Stage 2 = extrinsic initialization (seeds the joint solve), Stage 3 = joint
    estimation of extrinsics + `water_z` + board placements.
  - **Best-first.** `main.tex` contains **zero** occurrences of BFS/breadth-first.
    `supplement.tex:483-486` — "a **best-first traversal** alternates between camera and
    frame nodes, expanding next whichever node was reached by the highest-corner-count
    observation (rather than whichever lies fewest hops from the reference, **as a
    breadth-first order would**)".
  - **Bipartite graph.** `supplement.tex:470-473` defines it exactly as DOCS-03 requires —
    "two node types are cameras and board frames, with an edge wherever a camera detects
    the board in a given frame".

  ⚠ **Do not use `C:\Users\tucke\Desktop\main.pdf`.** That is a stale 2026-06-15 export
  which says *four* stages and uses BFS throughout. It was the source of a false alarm
  during this phase's research pass. The OneDrive `.tex` files are authoritative.

- **D-23 (NEW 2026-07-24): auxiliary-camera registration loses its stage number entirely.**
  Superseding the research recommendation to collapse `pipeline.py`'s "Stage 4b"/"Stage 3b"
  to an unconditional "Stage 3b". The paper does not number it: auxiliary cameras are
  "excluded from **Stages~2 and~3**", then "registered post-hoc against the frozen board
  placements and `water_z` via refractive PnP initialization, followed by either a
  **6-DOF refinement** … or a **10-DOF refinement** that adds focal length and principal
  point" (`main.tex:222-224`). Label it **"Auxiliary camera registration"** with the
  DOF distinction in the message body, and keep the existing stage-agnostic timing key
  `auxiliary_registration`.

### Loss-function correction (DOCS-06)

- **D-08: `docs/guide/optimizer.md:120` fixes both the name *and* the formula.** The code
  default is `robust_loss = "huber"` (`config/schema.py:314`,
  `interface_estimation.py:134`), but the page currently prints the **soft-L1** formula
  `ρ(r) = 2(√(1+r²) − 1)` beneath the label. Changing only the word leaves a wrong
  equation on the page. Replace with the Huber ρ, and state `loss_scale` (1.0 px) as the
  transition point.

### Pose-graph figure and terminology (DOCS-02, DOCS-03)

- **D-09: Port the paper supplement's corrected multi-panel generator into
  `docs/_static/scripts/`**, following the existing `bfs_pose_graph.py` /
  `sparsity_pattern.py` + `palette.py` convention, and regenerate the figure from it.
  Its generator replays the library's own heap logic, so the figure cannot drift from the
  code — that property is the reason to reuse rather than redraw.
  **Status 2026-07-24 (generator LOCATED):**
  `C:\Users\tucke\PycharmProjects\DissertationFigures\src\dissertationfigures\figures\aquacal\static.py`
  — `plot_bfs_pose_graph()` (line 390) is the generator that produced the supplement's
  six-panel figure (`save_figure(fig, "aquacal_bfs_pose_graph", …)`, matching
  `…/papers/aquacal/figures/aquacal_bfs_pose_graph.pdf`/`.png`).

  ⚠ **It does not do what its docstring claims.** Lines 13-15 assert the panels are
  "produced by replaying the same priority-queue logic as
  `aquacal.calibration.extrinsics.estimate_extrinsics` … so the diagram cannot drift from
  the library", and the fixes doc §2.6 repeats that claim. **`static.py` never imports
  aquacal.** `_simulate_traversal()` (line 103) reimplements the heap locally — its own
  `heapq`, its own `_ADJ` dict, its own `(-corners, node)` entries. It is a faithful
  *mirror*, not a replay, and it has already drifted slightly: it uses `sorted(_ADJ[node])`
  for both node types, while the library iterates `pose_graph.adjacency` **unsorted** in
  the camera branch (`extrinsics.py:601`) and `sorted(...)` in the frame branch (`:654`).
  Harmless for this figure's output (the heap tie-breaks by name) but it proves the gap is
  real. **Porting `static.py` verbatim would therefore NOT satisfy DOCS-03's "replays the
  library's own heap logic".**

  **Decision: port the rendering, replace the simulation.** The six-panel rendering is the
  expensive, good part and should be reused — panel A (observation graph, edge width ∝
  corners), panels B–E (the four productive pops, with solved / not-yet-solved /
  solved-in-this-panel node states and the per-panel queue caption), panel F (consensus
  pass, badges = estimates entering each average, the never-used edge in coral), and the
  seven-entry figure legend. Replace `_simulate_traversal()` with a real traversal driven
  through `aquacal.calibration.extrinsics` so the non-drift property becomes true rather
  than aspirational — that substitution is the entire reason this file is being rewritten
  rather than copied.

  Three external dependencies must be swapped on the way in:
  1. `dissertationfigures.core.style.COLORS` → `docs/_static/scripts/palette.py`:
     `blue`→`CAMERA_COLOR`, `gold`→`BOARD_COLOR`, `teal`→`WATER_SURFACE`,
     `gray`→`GRID_COLOR`, `coral`→`RAY_AIR`. `olive` (board-patch edge) has no equivalent —
     use `LABEL_COLOR` or a darkened `BOARD_COLOR`.
  2. `dissertation_style()` / `DOUBLE_COL` → AquaCal's `figsize`/`dpi` conventions.
  3. `save_figure(..., extra_artists=[leg])` → the `generate(output_dir) -> None` contract.
     ⚠ The legend is a **figure**-level legend; `static.py:436-438` carries an explicit
     comment that a tight bbox crops it unless the legend artist is named. AquaCal's
     generators use `bbox_inches="tight"`, so the port must pass
     `bbox_extra_artists=[leg]` to `savefig` or the legend silently disappears.

  A single-panel reduction remains acceptable for the docs page (see Claude's Discretion)
  provided both edge types and the direction semantics survive. Do not hand-patch the
  existing PNG.
- **D-10: Rename the figure to `pose_graph.png`** (the filename itself carries the wrong
  "bfs" term) and update every reference including alt text. Delete the old file rather
  than leaving both.
- **D-11: `_find_connected_components` (`extrinsics.py:200,208`) is left untouched** — it
  genuinely is breadth-first and is correctly named. This is a hard carve-out, called out
  in both REQUIREMENTS.md and the success criteria.
- **D-12: The two misleading "score each neighbour" comments
  (`extrinsics.py:601,654`) are corrected in this pass**, per the fixes doc §1.3 — they
  describe a prioritisation that does not exist and invite a wrong "fix". The optional
  `sorted()` consistency nit (§1.4) is **declined** — it is a cosmetic asymmetry with no
  behavioral effect, and this phase is documentation-only.
- **D-13: Add the "finalised on first discovery" invariant to the `estimate_extrinsics`
  docstring** (fixes doc §1.1) — popping a node solves every unvisited neighbour, so a
  node is never re-prioritised if a better edge appears later. This is what distinguishes
  the traversal from Prim's and is the non-obvious thing a reader needs.

### Home for the v1.7–v1.8 feature documentation (DOCS-04)

- **D-14: Create a dedicated `docs/guide/configuration.md` reference page.** There is no
  configuration reference today — config material is split between `docs/guide/cli.md`
  and autodoc'd `docs/api/config.rst`, and neither is a place a user browses for "what
  keys exist". Phase 21's DOCS-05 adds four more surfaces on top of this, so a page that
  can absorb them is worth creating now rather than growing `cli.md` further.
- **D-15: Troubleshooting keeps its entries but stops being the sole home.** The
  `reject_outlier_frames` / `start_frame` / `stop_frame` material in
  `docs/guide/troubleshooting.md` stays where it is (it is genuinely useful there) and
  gains links to the new reference. "Troubleshooting is where you land when something
  breaks, not where features should be introduced."
- **D-16: Link the new page from `docs/guide/index.md`** and fix that file's
  "Four-stage calibration pipeline" line in the same edit.

### Sweep blast radius

- **D-17: In scope for the terminology sweeps — `src/`, `docs/`, `README.md`.** Both the
  BFS→best-first sweep (DOCS-02) and the stage-model sweep (DOCS-06) are
  grep-and-verify passes over these trees, not just the enumerated line numbers; the
  fixes doc's line list is a floor, not a ceiling, and line numbers have moved since it
  was written.
- **D-18: `.planning/` and `CHANGELOG.md` are historical records — untouched.** This
  matches the convention already set when the repo moved to the McGrathLab org (in-repo
  URLs updated; `CHANGELOG.md` and `.planning/` deliberately left as-written).
- **D-19: `CLAUDE.md` says "Four-stage calibration pipeline" and should be corrected, but
  it is gitignored (`.gitignore:216`) — the edit is local-only and cannot be committed.**
  Make the edit; do not attempt to stage it or report it as a committed change.
  `.claude/rules/*.md` *is* tracked, if any stage language turns up there.

### Drift-proofing the corrected numbers (DOCS-01)

- **D-20: The DOCS-01 figures are asserted by a test, not just written into prose.** Add a
  test that derives the group count and parameter count live from
  `build_jacobian_sparsity` + `build_structural_column_groups` for the documented
  configurations and asserts the values the docs quote. The wrong "~12×" claim survived
  because nothing tied the prose to the code; the same silence will rot the corrected
  numbers too.
- **D-21 (VERIFIED 2026-07-24): the numbers were re-derived against the *shipped*
  `build_structural_column_groups` path** (not `scipy.optimize._numdiff.group_columns`,
  which quick task 3 `3c8685c` replaced) on a real 13-camera / 100-frame synthetic
  scenario. **CONFIRMED:** P = 673 (base) / 675 (tilt) / 727 (tilt + intrinsics);
  groups = 13 / 13 / 17; reduction = 51.8× / 51.9× / 42.8×. Write these verbatim; no
  further derivation needed.
- **D-22: Fix all four `optimizer.md` numeric errors together**, not just the headline:
  the `~12×` claim (`:202-205`), "at most 14-17 columns" → **13–17** (`:186`),
  "~630 parameters" → 673/675/727 (`:190-192`), and keep the adjacent "98% sparse" claim
  (it is correct: 13/673 = 1.9% nonzero). Also state that the group count is **fixed by
  the structure of a single observation and does not grow with the rig** — that invariant
  is the actual point, and its absence is what let "~50 groups" look plausible.
- **D-24 (NEW 2026-07-24): keep the docs' 13-camera / 100-frame framing; cite the
  supplement's *invariant*, not one of its table rows.** The success criterion says the
  numbers must "match the paper supplement", but `supplement.tex`'s table `tab:cpr` does
  **not** contain 673/675/727 or 43–52×. It tabulates 3×3 (P=33, 2.5×), 16×200 tilt-only
  (P=1293, 99×), 8×100 (P=677, 40×), **12×100 (P=717, 42×)**, 13×200 (P=1327, 78×), and
  16×200 (P=1357, 80×) — all at 13 or 17 groups. Our 727 / 17 / 42.8× is the 13-camera row
  the supplement simply does not print; it is arithmetically consistent with the same
  formula (`6(N-1) + 1 + 6F + 4N + 2`). Keep 13 cameras — that is the real rig the docs,
  tutorials, and example dataset all describe — and satisfy "matching the supplement" by
  reproducing its **invariant** ("13 with reference tilt alone, and 17 once intrinsic
  refinement adds four columns per camera … a property of one observation rather than of
  the rig", `supplement.tex:408-413`) rather than by copying a row. Optionally cite the
  supplement's range (2.5× → 99×) to show the reduction grows with problem size.

### Claude's Discretion

- Exact prose wording of every replacement string (the fixes doc's suggested replacements
  are a strong starting point, not a mandate).
- How the new `docs/guide/configuration.md` is organised internally (by config section
  vs. by workflow), and how much it duplicates vs. cross-links `docs/api/config.rst`.
- Plan decomposition — whether the stage rename, the terminology sweep, and the new
  config page are one plan or several.
- Whether the DOCS-01 assertion test lives in `tests/unit/` beside the optimizer tests or
  in a small docs-consistency test module.
- Whether the corrected pose-graph figure keeps the multi-panel layout or is reduced to a
  single panel for the docs page.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### The manuscript itself (outside the repo — READ-ONLY, never edit)

**Home of the in-progress paper:**
`C:\Users\tucke\OneDrive - Georgia Institute of Technology\Thesis\Spinoffs\papers\aquacal\`

- `…\papers\aquacal\main.tex` — **authoritative for the stage model.** `:208`
  "Three-stage calibration"; `:214-218` Stage 3 and its optional second pass;
  `:222-224` auxiliary-camera registration as a post-hoc 6-DOF/10-DOF step. Contains no
  BFS/breadth-first anywhere.
- `…\papers\aquacal\supplement.tex` — **authoritative for traversal terminology and the
  grouping numbers.** `:470-486` bipartite pose graph + best-first traversal;
  `:396-424` § Column grouping; `:441-458` table `tab:cpr`; `:499-510` the six-panel
  pose-graph figure caption.
- `…\papers\aquacal\figures\aquacal_bfs_pose_graph.pdf` / `.png` — the corrected figure to
  match (generator not located).
- `…\papers\aquacal\reviewer_response_plan.md`, `reviewer_responses.md` — the reviewer
  responses this milestone serves. Not read during this phase; relevant to Phases 19-22.

⚠ **Editing the manuscript is out of scope for this phase and this repo.** These files are
read-only inputs; the phase makes AquaCal match what they say.
⚠ **`C:\Users\tucke\Desktop\main.pdf` is a stale 2026-06-15 export — do not use it.** It
says four stages and BFS, contradicting the live source. It caused a false alarm in this
phase's research pass.

### Source worklists (outside the repo — read from disk)
- `C:\Users\tucke\Desktop\aquacal-docs-accuracy-fixes.md` — **the primary spec for this
  phase.** Line-level findings with suggested replacement text for `extrinsics.py`
  (§1.1–1.4) and Read the Docs (§2.1–2.6), plus the "also spotted" items that became
  DOCS-06. Every number in it was verified by calling `build_jacobian_sparsity` +
  `group_columns` directly — but *before* quick task 3 (see D-21).
- `C:\Users\tucke\Desktop\aquacal-post-review-milestone.md` §Task Group E (lines ~260–310)
  — E2 (BFS→best-first sites), E3 (pose-graph figure), E4 (v1.7–v1.8 feature homes),
  E6 (loss default + three-stage reconciliation). Line 52 was the source of the original
  "optional intrinsic pass" wording — **superseded by revised D-05**, which follows
  `main.tex:215,218` ("Stage 3 runs a second time" / "the second pass") instead.

### Phase and milestone planning
- `.planning/REQUIREMENTS.md` §Documentation Reconciliation (lines 70–78) — DOCS-01..07
  verbatim; §Sequencing Constraints (lines 92–105) — why DOCS-06 precedes BENCH-04 and
  why DOCS-01 was flagged for early landing.
- `.planning/ROADMAP.md` §Phase 18 (lines 136–158) — goal and the five success criteria
  this phase is verified against.
- `.planning/phases/16-experiment-observability-hooks/16-CONTEXT.md` §Artifact layout —
  why artifacts live in `internals/` and how stage-tagged files are named. The rename in
  D-06 must stay consistent with these conventions.
- `.planning/phases/17-per-camera-interface-ablation-mode/17-CONTEXT.md` §Deferred — the
  full `shared_interface` write-up is Phase 21's, not this phase's.

### Code surfaces being corrected
- `src/aquacal/calibration/extrinsics.py` — docstring sites `:513,517,535,583`; comments
  `:601,654`; **do not touch `:200,208`**.
- `src/aquacal/calibration/pipeline.py` — timing keys `:1064,1183,1272`; console stage
  strings `:1011,1065,1185`; stage tags and dump filenames `:729,1053,1075,1171`;
  four-stage docstring `:766-767`.
- `src/aquacal/config/schema.py:314` — `robust_loss: str = "huber"`, the ground truth
  DOCS-06's loss correction points at.
- `src/aquacal/calibration/_optim_common.py` — `build_jacobian_sparsity` /
  `build_structural_column_groups`, the source of truth for the DOCS-01 numbers.

### Docs surfaces being corrected
- `docs/guide/optimizer.md` — `:3,7` four-stage prose; `:15-17` mermaid nodes; `:57,71,73`
  BFS; `:96,151-165` Stage 4 sections; `:120` loss; `:186,190-192,202-205` numbers.
- `docs/guide/glossary.md:35` — pose-graph definition (backwards) + BFS mention.
- `docs/guide/index.md:9` — "Four-stage calibration pipeline".
- `docs/guide/troubleshooting.md` — the "Stage 3/4" phrasings at `:7,61,64,72,106,117,
  154,172,202,263,271`, and the v1.7–v1.8 feature text being given a proper home.
- `docs/_static/diagrams/bfs_pose_graph.png` + `docs/_static/scripts/bfs_pose_graph.py`
  and `docs/_static/scripts/palette.py` — the figure to replace and the generator
  convention to follow.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `docs/_static/scripts/palette.py` — the centralized diagram palette (a v1.4 decision,
  "✓ Good — consistent visuals" in PROJECT.md). Any regenerated figure goes through it.
- `docs/_static/scripts/sparsity_pattern.py` / `bfs_pose_graph.py` — the established
  "figure has a committed generator script" pattern the new pose-graph generator follows.
- `docs/guide/_diagrams/generate_all.py` — an existing batch regeneration entry point;
  check whether the `_static/scripts/` figures are wired into it or regenerated by hand.
- `build_jacobian_sparsity` + `build_structural_column_groups`
  (`src/aquacal/calibration/_optim_common.py`) — callable directly to derive the DOCS-01
  numbers for the assertion test in D-20.

### Established Patterns
- Stage tags are already a first-class concept: `_dump_stage_calibration(...)` takes a
  stage string, `save_conditioning_report(..., stage=...)` takes one, and trace CSVs are
  named per stage. **The rename therefore has a small number of well-defined chokepoints
  rather than being scattered f-strings** — find them and the rename is mechanical.
- `nbsphinx_execute = "never"` — notebooks do **not** re-execute on docs build. Any
  four-stage narration inside the tutorial notebooks is Phase 21's problem (DATA-03), not
  something this phase can fix as a side effect.
- Conventional commits drive python-semantic-release. `docs:` commits cut no release;
  the code-string renames are `refactor:`/`docs:` and must not be typed as `feat:`/`fix:`.

### Integration Points
- **Phase 19 (BENCH-04) consumes whatever this phase settles.** `benchmark.json`'s
  per-stage keys and `seconds_per_stage` come from `timings`, so D-06's key names are
  the contract Phase 19 builds against.
- `docs/api/config.rst` autodocs `CalibrationConfig`, so schema docstring edits surface on
  the docs site automatically — the new `configuration.md` should cross-link rather than
  restate the field list.
- The tutorials narrate "Stage 3 RMS / Stage 4 RMS" against committed outputs from a real
  run. Renaming console output makes that narration stale — **expected and accepted**;
  Phase 21 re-executes the notebooks after all code phases land.

</code_context>

<specifics>
## Specific Ideas

- The invariant is the point, not the number. `optimizer.md`'s "~50 groups" looked
  plausible because the page never said *why* the group count is what it is. The
  replacement must state that a residual involves exactly one camera and one frame, so
  the group count is fixed by a single observation's structure and does not grow with the
  rig — and that the advantage therefore *widens* as cameras and frames are added.
- Distinguish "wrong" from "differently framed". `_find_connected_components` really is
  BFS; `Why BFS?`'s paragraph body is correct and only its heading is wrong; "98% sparse"
  is correct. A blind find-and-replace over "BFS" or over the numbers breaks all three.
- The fixes doc inherited the wrong grouping claim from the dissertation's
  `appendix-a.tex` ("P → approximately log(P) … ~685 to ~50"). Worth knowing the error has
  a lineage: it may exist in other artifacts the user controls.
- A reviewer following the paper's link to these docs currently meets a *different
  architecture* than the one they just read. That reader is the acceptance test for
  DOCS-06.

</specifics>

<deferred>
## Deferred Ideas

- **`extrinsics.py:602` `sorted()` consistency nit** (fixes doc §1.4) — declined. Cosmetic,
  no behavioral effect, and this phase is documentation-only. Revisit if the branches are
  touched for another reason.
- **Documenting what this milestone adds** — `calc-index`, `benchmark.json` schema,
  trace/conditioning flags, and the full `shared_interface` write-up with worked example
  and WP6 interpretation → **Phase 21 (DOCS-05)**. This phase must not start it, even
  though the new `configuration.md` is the page that will eventually hold it.
- **Notebook re-execution and the stale "Stage 4 RMS" narration** → **Phase 21 (DATA-03)**.
- **The dissertation's `appendix-a.tex` carrying the same wrong grouping claim** — outside
  this repo entirely; flagged for the user, not actionable here.
- **`main.tex` understates its own supplement by ~4×** — found 2026-07-24. Under "Bundle
  adjustment internals" it says column grouping reduces finite-difference evaluations "by
  **roughly an order of magnitude** for a typical **12-camera, 100-frame** problem", but
  `supplement.tex`'s own table `tab:cpr` gives that exact configuration as **42×**. This is
  the same error class as the docs' "~12×" claim that DOCS-01 fixes, sitting in the main
  manuscript text — and no worklist flagged it. **Manuscript-side, explicitly out of scope
  for this repo and this phase.** Recorded here so it is not lost; raise it when the
  manuscript is next edited.

### Reviewed Todos (not folded)

`--auto` folds todos scoring ≥ 0.4, but both matches are explicitly sequenced elsewhere by
locked decisions. Folding them would violate REQUIREMENTS.md §Sequencing Constraints, so
both are recorded as reviewed-and-declined rather than folded:

- **Upload new Zenodo dataset with image-based inputs** (score 0.90, area `docs`) —
  matched on `docs/config/json` keywords only. STATE.md is explicit: "**Now Phase 21
  (DATA-01/02/03)** — do not action standalone", and constraint 4 requires it to run after
  all code work *and* after DOCS-06, before DOCS-07. Belongs to Phase 21.
- **Reduce memory and CPU load during calibration** (score 0.40, area `performance`) —
  matched on `refinement/stage` keywords. PROJECT.md Key Decisions record that v1.9
  *measures and reports* the ~3.6 GB peak but deliberately does not reduce it; it is
  PERF-01 in REQUIREMENTS.md Future. Out of milestone scope, not just out of phase scope.

</deferred>

---

*Phase: 18-documentation-corrections-stage-model-reconciliation*
*Context gathered: 2026-07-24*
