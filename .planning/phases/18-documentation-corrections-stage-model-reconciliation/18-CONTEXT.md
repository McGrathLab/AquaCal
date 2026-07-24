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
- **D-05: The ex-Stage-4 is called "Stage 3's optional intrinsic pass"** in prose and
  console output. This is the worklist's own wording
  (`aquacal-post-review-milestone.md:52` — "Stage 3, the optional intrinsic pass"), so it
  is already the vocabulary the paper-side work uses.
- **D-06: Machine key form is `stage3_intrinsic_pass`.** Concretely:
  `timings["stage4_joint_refinement"]` → `timings["stage3_intrinsic_pass"]`;
  `internals/calibration_stage4.json` → `internals/calibration_stage3_intrinsic_pass.json`;
  `internals/trace_stage4.csv` → `internals/trace_stage3_intrinsic_pass.csv`;
  conditioning/dump `stage` tag `"stage4"` → `"stage3_intrinsic_pass"`.
  `"stage3_rerun"` (the post-outlier-rejection re-solve) is unaffected and keeps its name.
- **D-07: ⚠ The exact stage names must be confirmed against the manuscript before the
  rename lands.** The paper is not in this repo, and the worklist describes the model
  without quoting the paper's stage labels verbatim. Naming that diverges from the paper
  recreates the divergence this phase exists to close. **Researcher/planner: surface this
  as an explicit confirmation item; do not silently proceed on the inferred wording if
  the manuscript is reachable.**

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
  **Input dependency:** the supplement generator has to come from the user.
  **Fallback if unavailable:** write the generator in-repo, replaying
  `estimate_extrinsics`'s heap directly, to the same non-drift standard. Do not hand-patch
  the existing PNG.
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
- **D-21: ⚠ Re-derive the numbers against the *shipped structural grouping path*, not
  `scipy.optimize._numdiff.group_columns`.** The fixes doc's measurements predate quick
  task 3 (`3c8685c`), which replaced `group_columns` with
  `build_structural_column_groups`. Phase 17's notes confirm the counts still land at
  13 / 17-with-intrinsics, but the planner must verify rather than inherit — including
  P = 673 (base) / 675 (tilt) / 727 (tilt + intrinsics) and the 43–52× reduction.
- **D-22: Fix all four `optimizer.md` numeric errors together**, not just the headline:
  the `~12×` claim (`:202-205`), "at most 14-17 columns" → **13–17** (`:186`),
  "~630 parameters" → 673/675/727 (`:190-192`), and keep the adjacent "98% sparse" claim
  (it is correct: 13/673 = 1.9% nonzero). Also state that the group count is **fixed by
  the structure of a single observation and does not grow with the rig** — that invariant
  is the actual point, and its absence is what let "~50 groups" look plausible.

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

### Source worklists (outside the repo — read from disk)
- `C:\Users\tucke\Desktop\aquacal-docs-accuracy-fixes.md` — **the primary spec for this
  phase.** Line-level findings with suggested replacement text for `extrinsics.py`
  (§1.1–1.4) and Read the Docs (§2.1–2.6), plus the "also spotted" items that became
  DOCS-06. Every number in it was verified by calling `build_jacobian_sparsity` +
  `group_columns` directly — but *before* quick task 3 (see D-21).
- `C:\Users\tucke\Desktop\aquacal-post-review-milestone.md` §Task Group E (lines ~260–310)
  — E2 (BFS→best-first sites), E3 (pose-graph figure), E4 (v1.7–v1.8 feature homes),
  E6 (loss default + three-stage reconciliation). Line 52 is the source of the
  "optional intrinsic pass" wording locked in D-05.

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
