# Phase 18: Documentation Corrections & Stage-Model Reconciliation - Pattern Map

**Mapped:** 2026-07-24
**Files analyzed:** 13 (2 new, 11 existing-edited)
**Analogs found:** 13 / 13 (existing-edited files are their own analog — this is a correction pass)

This phase mostly **edits existing files in place**; the "analog" for those is the file's own
current text at the touched sites (extracted below verbatim so the planner can write
exact-target-state diffs). Two files are genuinely new.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `docs/guide/configuration.md` (NEW) | doc page (config reference) | request-response (static site page) | `docs/guide/troubleshooting.md`, `docs/guide/cli.md`, `docs/guide/glossary.md` | role-match (composite) |
| `docs/_static/scripts/pose_graph.py` (NEW, replaces `bfs_pose_graph.py`) | utility (diagram generator) | batch/transform (matplotlib PNG emit) | `docs/_static/scripts/bfs_pose_graph.py`, `docs/_static/scripts/sparsity_pattern.py` | exact (same script family) |
| `src/aquacal/calibration/extrinsics.py` | service (docstrings/comments only) | — | itself | exact |
| `src/aquacal/calibration/pipeline.py` | service (stage keys/strings/filenames) | — | itself | exact |
| `src/aquacal/config/schema.py` | model (dataclass docstring) | — | itself | exact |
| `src/aquacal/calibration/refinement.py` | service (module/docstring "Stage 4") | — | itself | exact |
| `src/aquacal/calibration/_optim_common.py` | utility (module docstring "Stage 4") | — | itself | exact |
| `src/aquacal/calibration/_observability.py` | service (docstring stage examples) | — | itself | exact |
| `src/aquacal/validation/conditioning.py` | utility (docstring stage examples) | — | itself | exact |
| `src/aquacal/cli.py` | CLI/config-template generator (comment strings) | — | itself | exact |
| `src/aquacal/config/example_config.yaml` | config template | — | itself | exact |
| `docs/guide/optimizer.md` | doc page | — | itself | exact |
| `docs/guide/glossary.md`, `docs/guide/index.md`, `docs/guide/troubleshooting.md` | doc pages | — | themselves | exact |
| `tests/unit/test_pipeline.py`, `test_refinement.py`, `test_observability.py`, `test_diagnostics.py`, `test_internals.py`, `test_interface_estimation.py` | test | — | themselves | exact |

---

## Pattern Assignments

### 1. NEW: `docs/guide/configuration.md`

**Analogs:** `docs/guide/troubleshooting.md` (structure/admonitions), `docs/guide/cli.md` (table conventions, cross-link footer), `docs/guide/glossary.md` (terse definition style), `docs/api/config.rst` (autodoc target to link into).

**Page frontmatter / heading convention** (from `docs/guide/cli.md:1-3` and `docs/guide/troubleshooting.md:1-3`):
```markdown
# CLI Reference

AquaCal provides three command-line tools for calibration workflows. All values are in meters.
```
No YAML frontmatter is used on any guide page — just an H1, then a one/two-sentence orienting paragraph.

**Section anchors for cross-referencing** (from `docs/guide/troubleshooting.md:103,136,169`):
```markdown
(camera-layout-looks-wrong)=
## Camera Layout Looks Wrong Despite Low Errors
```
`{ref}` targets are declared with `(slug)=` immediately above the heading, then referenced elsewhere as `` {ref}`Label <slug>` `` (see `docs/guide/optimizer.md:366` and `docs/guide/troubleshooting.md:209`).

**Autodoc cross-link into `docs/api/`** (from `docs/guide/optimizer.md:48,75,135,171,208,232,264`):
```markdown
See {func}`aquacal.calibration.intrinsics.calibrate_intrinsics_all` for implementation.
See {mod}`aquacal.calibration._optim_common` for shared optimization utilities.
```
`docs/api/config.rst` is a bare `automodule` on `aquacal.config.schema` — the new page should link `{class}`aquacal.config.schema.CalibrationConfig`` / `{func}` refs into it rather than restating the field table (per CONTEXT D-14/D-15 and Integration Points note).

**Admonition pattern** (from `docs/guide/optimizer.md:137-149,210-216`):
```markdown
:::{admonition} Gotcha: water_z is unobservable in non-refractive mode
:class: warning

...body...
:::
```
Use `:class: warning` for pitfalls, `:class: tip` for advanced/optional notes.

**Config YAML snippet convention** (from `docs/guide/troubleshooting.md:42-46,88-95,148-161`):
```markdown
Edit your config:
```yaml
detection:
  frame_step: 5  # Change to 2 or 1 for more frames
```
```
Snippets are always fenced ` ```yaml ` blocks showing the relevant top-level section (`detection:`, `optimization:`, `interface:`), inline-commented, never a full config dump.

**"See Also" footer convention** (from all three analogs, e.g. `docs/guide/troubleshooting.md:305-309`):
```markdown
## See Also

- [CLI Reference](cli.md) — Command-line usage and options
- [Optimizer Pipeline](optimizer.md) — Understanding the calibration stages
- [Glossary](glossary.md) — Definitions of key terms
```

**Registration in `docs/guide/index.md`** — the page must be added to both the bulleted list and the hidden toctree (`docs/guide/index.md:11-27`, full file already reproduced above in this map's source read):
```markdown
## Practical Guides

- [CLI Reference](cli.md) — ...
- [Troubleshooting](troubleshooting.md) — ...
- [Glossary](glossary.md) — ...

:::{toctree}
:hidden:
:maxdepth: 2

refractive_geometry
coordinates
optimizer
cli
troubleshooting
glossary
:::
```
Insert `configuration` as a new bullet + new toctree entry (order: likely after `cli`, before `troubleshooting`, since it's a reference page like `cli.md`). Also fix `index.md:9`'s "Four-stage calibration pipeline" line in the same edit (D-16).

---

### 2. NEW: `docs/_static/scripts/pose_graph.py` (replaces `bfs_pose_graph.py`)

**Analog:** `docs/_static/scripts/bfs_pose_graph.py` (full file read above — 276 lines) and `docs/_static/scripts/sparsity_pattern.py` (same skeleton). Both follow an identical generator contract; extract that contract verbatim:

**Module docstring + import block** (`bfs_pose_graph.py:1-31`):
```python
"""BFS pose graph diagram for AquaCal documentation.
...
"""

import sys
from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np

# Ensure palette.py is importable regardless of working directory
sys.path.insert(0, str(Path(__file__).parent))
from palette import (  # noqa: E402
    BOARD_COLOR,
    CAMERA_COLOR,
    GRID_COLOR,
    LABEL_COLOR,
    RAY_AIR,
    WATER_SURFACE,
)
```
Per D-09, the new generator "replays the library's own heap logic" — i.e. it should import/call the real `estimate_extrinsics` heap traversal (or a faithful re-implementation of it) rather than hand-authoring a fixed edge list like the current script's `EDGES`/`BFS_EDGES` constants. If porting the user's supplement generator, preserve this palette-import block unchanged; if writing in-repo (fallback), replay `estimate_extrinsics`'s priority-heap logic directly (`src/aquacal/calibration/extrinsics.py:583-644`, read above) — the heap is a **priority queue by corner count, not FIFO/BFS**, which is exactly the terminology fix (D-10/D-13: "finalised on first discovery" invariant).

**`generate(output_dir)` entry-point contract** (`bfs_pose_graph.py:167-266`):
```python
def generate(output_dir: Path) -> None:
    """Generate and save the ... diagram.

    Args:
        output_dir: Directory where the PNG will be saved.
    """
    fig, ax = plt.subplots(figsize=(8, 5.5))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ...
    plt.tight_layout()
    output_path = Path(output_dir) / "bfs_pose_graph.png"   # -> rename to "pose_graph.png"
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Saved: {output_path}")
```
Figure sizing/DPI convention: `figsize=(8, 5.5)`, `dpi=150`, `bbox_inches="tight"`, `facecolor="white"`. `sparsity_pattern.py` uses the same `generate(output_dir)` signature and save convention (confirmed at `sparsity_pattern.py:251`: `output_path = Path(output_dir) / "sparsity_pattern.png"`).

**Standalone-run entry point** (`bfs_pose_graph.py:269-276`):
```python
if __name__ == "__main__":
    import matplotlib

    matplotlib.use("Agg")
    output_dir = Path(__file__).parent.parent / "diagrams"
    output_dir.mkdir(parents=True, exist_ok=True)
    generate(output_dir)
```

**Batch regeneration wiring — must be updated, not just the new file dropped in.** `docs/guide/_diagrams/generate_all.py` (full file, 60 lines, read above) is the single entry point Sphinx calls via `conf.py`'s setup hook. It currently does:
```python
_scripts_dir = Path(__file__).parent.parent.parent / "_static" / "scripts"
...
from bfs_pose_graph import generate as generate_bfs_pose_graph
...
print("Generating BFS pose graph diagram...")
generate_bfs_pose_graph(diagrams_dir)
```
This must become (module renamed to `pose_graph`, import/call renamed, and per D-10 the print string's "BFS" wording corrected too):
```python
from pose_graph import generate as generate_pose_graph
...
print("Generating pose graph diagram...")
generate_pose_graph(diagrams_dir)
```

**Filename/reference sweep required (D-10 — delete old, no dual-file period):**
- `docs/_static/scripts/bfs_pose_graph.py` → delete (replaced by `pose_graph.py`)
- `docs/_static/diagrams/bfs_pose_graph.png` → delete; regenerate `pose_graph.png` by running `python docs/guide/_diagrams/generate_all.py` (or the script standalone)
- `docs/guide/optimizer.md:73`: `![BFS pose graph](../_static/diagrams/bfs_pose_graph.png)` → update path **and** alt text (D-10: "including alt text")
- `docs/_build/html/_static/scripts/bfs_pose_graph.py` is a **build artifact** (under `_build/`), not source — do not hand-edit; it regenerates on next Sphinx build. Flagging so the planner doesn't waste a plan step on it.

---

### 3. `src/aquacal/calibration/extrinsics.py` — docstring/comment corrections only

**Current text at each touched site** (all read from a single pass, lines 480-680; no re-reads needed):

- **`:513-514`** (BFS → best-first framing, function docstring intro):
```python
    Uses BFS traversal from reference camera, computing each camera's
    pose relative to world frame (centered at reference camera).
```
- **`:517`** (second BFS mention in the same docstring):
```python
    then runs BFS through the pose graph. When visiting a frame node from
```
- **`:535`** (`progress_callback` arg doc):
```python
        progress_callback: Optional callback(camera_name, cameras_located, total_cameras)
            called after each camera is located during BFS traversal
```
- **`:583`** (inline comment above the heap-seed line):
```python
    # Priority BFS to propagate poses, ordered by corner count (highest first)
    # Heap entries: (-num_corners, node_name) — negative for max-heap behavior
```
  Note: line 583 is the first of a two-line comment; the second line (`# Heap entries: ...`) is accurate and does not need correction — only the "Priority BFS" phrase does.
- **`:601`** (misleading "score" comment #1 — corrected per D-12):
```python
            # Score each neighboring frame by corner count, pick best first
            frame_neighbors = []
            for neighbor in pose_graph.adjacency.get(cam_name, []):
```
  What it actually does: it just filters unvisited neighbors into a list in adjacency order and pushes each onto the shared heap — no scoring/sorting happens in this loop; the heap ordering is what does the prioritization globally. D-13 wants the docstring to also state the "finalised on first discovery" invariant (a node popped from the heap resolves every unvisited neighbor in one pass; it is never revisited even if a later-discovered edge would have been better) — that belongs in the function docstring near `:513-521`, not this loop comment.
- **`:654`** (misleading "score" comment #2, same shape, frame→camera direction):
```python
            # Score each neighboring camera by corner count
            cam_neighbors = []
            for neighbor in sorted(pose_graph.adjacency.get(node, [])):
```

**Explicit carve-out (D-11) — do NOT touch:**
```python
# lines 196-214, function _find_connected_components
def _find_connected_components(
    adjacency: dict[str, set[str]],
    camera_names: list[str],
) -> list[set[str]]:
    """Find connected components in the pose graph using BFS."""
    ...
        # BFS from this camera
        component: set[str] = set()
        queue = deque([start])
```
This really is FIFO BFS (`deque` + `popleft`), correctly named. A blind "BFS→best-first" find-and-replace over the file would wrongly touch this — the planner must scope the edit to the named line numbers, not a file-wide regex.

---

### 4. `src/aquacal/calibration/pipeline.py` — stage-key rename (D-06)

**Established chokepoint pattern** (per CONTEXT "Established Patterns" — confirmed by reading): every stage-tagged artifact flows through one of three call shapes, all present in the 700-1400 range read above:

```python
# 1. Wall-clock timing accumulator (dict key)
with _time_stage(timings, "stage1_intrinsics"):   # pattern; stage3/4 use direct assignment below
    ...
timings["stage4_joint_refinement"] = elapsed          # :1272 -> rename to "stage3_intrinsic_pass"

# 2. Observer / stage tag (constructor kwarg, also flows into conditioning JSON "stage" field)
stage4_observer = (
    OptimizerObserver(stage="stage4", conditioning=config.save_conditioning)   # :1243
    if observe else None
)

# 3. Trace CSV filename (derived from the same observer)
stage4_observer.write_trace_csv(
    ensure_internals_dir(config.output_dir) / "trace_stage4.csv"               # :1277
)

# 4. Stage-tagged calibration JSON dump filename (via _dump_stage_calibration)
_dump_stage_calibration(
    "stage4",                                                                   # :1299
    config, final_intrinsics, final_extrinsics, final_distances, interface_normal,
)
```

**Every "stage4" / "stage4_joint_refinement" call site found in `src/`** (grep across the whole tree, not just the CONTEXT-enumerated lines — this is the true blast radius per D-17's "floor, not ceiling"):

| File:Line | Current text | Category |
|---|---|---|
| `pipeline.py:623` | `stage4_obs: OptimizerObserver | None,` (param name) | function signature |
| `pipeline.py:630-631` | `Exactly one report is selected per run: Stage 4's when intrinsics are\n    refined (Stage 4 is the final reported result), else the Stage-3` | docstring prose |
| `pipeline.py:635` | `stage4_obs: Observer for Stage 4, or ``None`` if Stage 4 was skipped or` | docstring (Args) |
| `pipeline.py:641` | `refine_intrinsics: Whether Stage 4 ran.` | docstring (Args) |
| `pipeline.py:649` | `obs = stage4_obs` | code (var alias, param name only — not the string key) |
| `pipeline.py:729` | `stage: Producing-stage tag ("stage3", "stage3_rerun", or "stage4"),` | docstring |
| `pipeline.py:766-767` | `6. Run Stage 3: Interface and pose optimization\n    7. Optionally run Stage 4: Joint refinement` | module/function docstring (the "four-stage" list — becomes 3 items with intrinsic pass folded under item 6, or an explicit "6a" sub-bullet) |
| `pipeline.py:1235` | `# --- Stage 4: Optional Joint Refinement ---` | section comment |
| `pipeline.py:1237` | `stage4_observer = None` | code (var name — cosmetic, not a string key; low priority) |
| `pipeline.py:1240` | `print("\n[Stage 4] Joint refinement with intrinsics...")` | **console output — machine-adjacent, D-01 in scope** |
| `pipeline.py:1242-1243` | `stage4_observer = (\n    OptimizerObserver(stage="stage4", conditioning=config.save_conditioning)` | **stage tag string — rename to `"stage3_intrinsic_pass"`** |
| `pipeline.py:1272` | `timings["stage4_joint_refinement"] = elapsed` | **timing key — rename to `timings["stage3_intrinsic_pass"]`** |
| `pipeline.py:1273` | `print(f"  Stage 4 RMS: {final_rms:.3f} pixels ({elapsed:.1f}s)")` | **console output** |
| `pipeline.py:1277,1279` | `... / "trace_stage4.csv"` / `print("  Saved internals/trace_stage4.csv")` | **filename — rename to `trace_stage3_intrinsic_pass.csv`** |
| `pipeline.py:1299,1306` | `_dump_stage_calibration("stage4", ...)` / `print("  Saved internals/calibration_stage4.json")` | **stage tag + filename — rename to `"stage3_intrinsic_pass"` / `calibration_stage3_intrinsic_pass.json`** |
| `pipeline.py:1308` | `print("\n[Stage 4] Skipped (refine_intrinsics=False)")` | **console output** |
| `pipeline.py:1321,1347` | `"stage4" if refine_intrinsics else (...)` (×2, conditioning + spread report stage selection) | **stage tag string, both occurrences** |
| `pipeline.py:1373` | `stage_label = "Stage 4b" if config.refine_auxiliary_intrinsics else "Stage 3b"` | **ambiguous — see Open Question below** |
| `pipeline.py:1774` | `stage: Stage label used in the output filename, e.g. "stage3",\n            "stage3_rerun", "stage4".` (docstring of `_dump_stage_calibration`) | docstring |
| `src/aquacal/calibration/_observability.py:178` | `stage: Human-readable stage name (e.g. "stage3", "stage3_rerun", "stage4"),` | docstring (`OptimizerObserver`) |
| `src/aquacal/validation/conditioning.py:204` | `this report (e.g. "stage3", "stage4"), recorded in the JSON payload` | docstring (`save_conditioning_report`) |
| `src/aquacal/calibration/refinement.py:1` | `"""Stage 4 joint refinement with optional intrinsics optimization.` | module docstring |
| `src/aquacal/calibration/refinement.py:65` | `This is Stage 4 of the calibration pipeline. It takes the output of Stage 3` | function docstring |
| `src/aquacal/calibration/_optim_common.py:5` | `used by both interface_estimation (Stage 3) and refinement (Stage 4).` | module docstring |
| `src/aquacal/config/schema.py:242,245,261,264,269,284,328` | `refine_intrinsics: If True, Stage 4 jointly refines ...` (×7 occurrences, see §5 below) | field docstrings + inline comment |
| `src/aquacal/cli.py:602-603` | `"  # refine_intrinsics: false  # Stage 4: refine focal lengths and principal points",`<br>`"  # refine_auxiliary_intrinsics: false  # Stage 4b: refine auxiliary camera intrinsics",` | generated-config comment strings (emitted by `aquacal init`) |
| `src/aquacal/config/example_config.yaml:78,80` | `# refine_intrinsics: false  # Stage 4: also optimize focal lengths and principal points`<br>`# refine_auxiliary_intrinsics: false  # Stage 4b: also optimize auxiliary camera` | shipped example config comments |

**Open question for the planner (not resolved by CONTEXT.md):** `"Stage 4b"` / `"Stage 3b"` (`pipeline.py:1373`, `refine_auxiliary_intrinsics` docstrings) refers to **auxiliary-camera** registration/intrinsics refinement — a different concept from the ex-Stage-4 *primary-camera* intrinsic pass that D-06 renames. CONTEXT.md's D-06/D-22 vocabulary (`stage3_intrinsic_pass`) is defined only for the primary pass. The `4b`/`3b` suffix pattern likely wants to become `3b`/`3c` or similar once "Stage 4" no longer exists as a numeral to suffix off of — but this is not spelled out in the decisions and should be confirmed against the manuscript alongside D-07, not silently inferred.

**Test files that consume these strings and must move in lockstep (D-03: no compat shim, so tests break otherwise):**

| File:Line | What it asserts |
|---|---|
| `tests/unit/test_pipeline.py:844,860,864,872,881,891,900,909,916-926,955,969,981-983,1009-1011,1015-1020,1059,1066` | `_dump_stage_calibration("stage3"/"stage3_rerun"/"stage4", ...)`, filename assertions (`calibration_stage3.json`, `calibration_stage3_rerun.json`, `calibration_stage4.json`), trace CSV filename source-text assertions (`"trace_stage3.csv"`, `"trace_stage3_rerun.csv"`, `"trace_stage4.csv"`), `_observer_with_report("stage4", ...)`, `_select_conditioning_report(...)`, `save_conditioning_report(..., stage="stage3")` / `payload["stage"]`, `_build_interface_spread_report(distances, "stage3"/"stage4")` |
| `tests/unit/test_refinement.py:612,654` | `OptimizerObserver(stage="stage4")` |
| `tests/unit/test_observability.py:375,392` | `OptimizerObserver(stage="stage3", conditioning=True)` (unaffected — "stage3" stays), error-message substring check |
| `tests/unit/test_diagnostics.py:739,760` | `"stage3_interface_optimization": 4.0` timing-key literal (this key is **not** part of D-06's rename — Stage 3 itself keeps its name — but confirm no adjacent `stage4_joint_refinement` key appears in the same fixture) |
| `tests/unit/test_internals.py:42,49` | `calibration_stage3.json` overwrite-warning path/message (unaffected — stage3, not stage4) |
| `tests/unit/test_interface_estimation.py:881,922,957,972` | `OptimizerObserver(stage="stage3")` (unaffected) |

None of the `_dump_stage_calibration`/`OptimizerObserver`/`save_conditioning_report`/`_build_interface_spread_report` call sites take an old-vocabulary default — every stage string is passed explicitly at the call site, so **the rename touches every literal listed above and nothing is inferred by a default parameter**.

---

### 5. `src/aquacal/config/schema.py` — `robust_loss` field + Stage-4 docstring mentions

**`robust_loss` field, current text** (`:314`, ground truth for D-08's loss-formula fix in `optimizer.md`):
```python
    robust_loss: str = "huber"  # "huber", "soft_l1", "linear"
```
No docstring paragraph currently exists for `robust_loss` in the `Args:` block read (lines 295-323 span other fields); if CONTEXT expects the class docstring to also carry loss guidance, add an `Args:` entry following the style of the adjacent `shared_interface` entry (`:297-302`, read above):
```python
        shared_interface: Analysis/ablation option, NOT a recommended setting.
            When True (default) all cameras share a single global water_z (the
            shared-interface assumption that underlies the paper's central
            claim). When False, each optimized camera solves its own water_z;
            this exists only for degeneracy/ablation analysis (e.g. the WP6
            experiment) and is not recommended for production calibration.
```

**Stage-4 references inside `schema.py`'s docstrings/comments (`:242,245,261,264,269,284,328`)** — all `refine_intrinsics` / `refine_auxiliary_intrinsics` field docs; read via grep context above, worth a full targeted read before editing since they interlock (`refine_auxiliary_intrinsics`'s docstring explicitly cross-references `refine_intrinsics`'s "Stage 4").

---

### 6. `docs/guide/optimizer.md` — numeric + terminology corrections (D-08, D-09/10, D-22)

Full file already read (374 lines). Key excerpts the planner needs verbatim:

**Four-stage mermaid diagram (`:3,7,9-28`)** — the whole `S4` node and `S3 --> S4` / `S4 --> O` edges need folding into `S3`, and prose at `:3,7` ("four sequential stages") → three:
```
S3["**Stage 3**<br/>Joint Refractive BA<br/><small>(nonlinear)</small>"]
S4["**Stage 4**<br/>Intrinsic Refinement<br/><small>(optional)</small>"]
S1 --> S2
S2 --> S3
S3 --> S4
S4 --> O["Refined K, R, t<br/>water_z, boards"]
```

**BFS section header + prose (`:50-75`)** — heading `## Stage 2: Extrinsic Initialization` stays; body text `**Method:** ... 3. **BFS traversal**: ...` (`:57`) and the `**Why BFS?**` sub-heading (`:71`) are the two terminology sites; per "Specifics" in CONTEXT, the `Why BFS?` **paragraph body is correct** (explains the non-overlapping-FOV chaining rationale) — only the heading word and the figure need to change, not the explanation.

**Loss function, current (wrong) text (`:120-126`, D-08 target)**:
```markdown
**Loss function:** Soft-L1 (Huber-like) loss for robustness to outliers:

$$
\rho(r) = 2 \left( \sqrt{1 + r^2} - 1 \right)
$$

This down-weights large residuals (e.g., detection errors, board motion blur) while preserving gradient information.
```
Replace with Huber ρ and `loss_scale` (1.0 px) as the transition point — code ground truth: `config/schema.py:314` (`robust_loss: str = "huber"`) and `interface_estimation.py:134` (per CONTEXT, not yet read but cited as second confirmation site).

**Stage 4 section to fold into Stage 3 (`:151-171`)** — heading `## Stage 4: Intrinsic Refinement (Optional)` and its body become a subsection of Stage 3 (D-04/D-05 wording: "Stage 3's optional intrinsic pass").

**Sparse Jacobian numbers, current (wrong) text (`:185-206`, D-22 targets)**:
```markdown
Total: at most **14-17 columns** touched per residual row.
...
For a 13-camera, 100-frame rig:
- Parameters: ~630 (extrinsics + water_z + board poses)
- Each row touches ~13 columns → **98% sparse**
...
**Column grouping** reduces the number of function evaluations: independent columns can be finite-differenced simultaneously. For the 630-parameter rig:
- Without grouping: 630 evaluations
- With grouping: ~50 groups → **~12× fewer evaluations**
```
Target values per D-21/D-22: **13-17** columns (not "14-17"); P = 673 (base) / 675 (tilt) / 727 (tilt + intrinsics) (not "~630"); 13/17 groups → **43-52×** reduction (not "~12×"); "98% sparse" (13/673 = 1.9% nonzero) is already correct and must survive untouched. Source of truth to re-derive against: `build_jacobian_sparsity` / `build_structural_column_groups` in `src/aquacal/calibration/_optim_common.py` (per CONTEXT, callable directly — not re-read here per phase scope, planner/implementer should call it live for the D-20 assertion test).

**Numbers appear a second time in prose (`:98-102`)** — the "Example: For a 3-camera rig with 50 frames" walkthrough uses small numbers consistent with the toy example and is **not** one of the wrong headline claims; do not conflate it with the 673/675/727 rig-scale figures.

---

### 7. `docs/guide/glossary.md` — pose-graph definition + BFS mention

Full file already read (71 lines). Single target line:
```markdown
**Pose graph**
: Graph structure where nodes represent camera-frame observations and edges connect observations of the same board pose. Used in Stage 2 for extrinsic initialization via BFS traversal.
```
CONTEXT flags this definition as "(backwards)" — nodes are described as "camera-frame observations" (singular merged concept) but the actual pose graph (per `extrinsics.py` and `optimizer.md:56`) is **bipartite**: camera nodes and frame/board nodes are separate node types, with edges connecting a camera to each frame it observes — not "edges connect observations of the same board pose" (which describes a different, frame-clique graph). Also swap "BFS traversal" → "best-first traversal" (or the D-07-confirmed manuscript term).

Also touches **Bundle adjustment** (`:13-14`, "Stage 3" — unaffected, correct already) and **Auxiliary camera** (`:7-8`, "Stages 2-4" — becomes "Stages 2-3" per the three-stage model) and the footer `## See Also` (`:70`, "The four calibration stages" → "The three calibration stages").

---

### 8. `docs/guide/index.md` — stage-count line + new page registration

Full file already read (28 lines). Target line (`:9`):
```markdown
- [Optimizer Pipeline](optimizer.md) — Four-stage calibration pipeline, bundle adjustment structure, and camera models
```
→ "Three-stage calibration pipeline...". Registration of the new `configuration.md` page covered in §1 above (bullet + toctree entry).

---

### 9. `docs/guide/troubleshooting.md` — "Stage 3/4" phrasings + v1.7-v1.8 feature cross-links

Full file already read (309 lines). All "Stage 3/4" or "Stage 3 or 4" occurrences found at: `:7` ("Stage 3/4 optimization converges..."), `:61` ("Stage 1 is good but Stage 3/4 are slow"), `:64` (`max_calibration_frames: 150  # Use subset for faster Stage 3/4`), `:72` ("Stage 3 or 4 fails to converge"), `:106` ("Stage 3/4 reprojection RMS is low"), `:117` ("Stage 3/4 RMS is low"), `:154` (not a stage mention — frame rejection description, skip), `:172` ("Stage 3/4 validation errors are high"), `:202` ("Validation RMS >> training RMS in Stage 3/4"), `:263` ("Limit the number of frames used in Stage 3/4"), `:271` ("**Stage 3/4** can be limited to a random subset"). Given D-04 (intrinsic refinement is a *mode* of Stage 3, not a numbered stage), these collapse to "Stage 3" throughout (dropping "/4"), since the optional intrinsic pass is still Stage 3.

**D-15 (feature home migration)** — the `reject_outlier_frames`/`start_frame`/`stop_frame` material (headed `## Contaminated Frames (Board Near the Surface, Ripples)`, `:136-165`) **stays in place** but should gain a forward link to the new `configuration.md` reference page — follow the existing cross-link idiom used in this same file's `## See Also` footer (`:305-309`) and inline `{ref}` pattern (`:124`, `:132`):
```markdown
For the underlying theory, see the [Refractive Geometry](refractive_geometry.md) and [Optimizer Pipeline](optimizer.md) guides.
```

---

## Shared Patterns

### Stage-tag chokepoints (D-01/D-06)
**Source:** `src/aquacal/calibration/pipeline.py` (four call shapes: `timings[...]`, `OptimizerObserver(stage=...)`, `.write_trace_csv(.../"trace_stage*.csv")`, `_dump_stage_calibration("stage*", ...)`)
**Apply to:** Any plan touching pipeline.py's stage-4 machinery, plus `_observability.py`, `validation/conditioning.py` docstrings, and every test file listed in §4's table.
```python
stage4_observer = (
    OptimizerObserver(stage="stage4", conditioning=config.save_conditioning)
    if observe else None
)
timings["stage4_joint_refinement"] = elapsed
...
_dump_stage_calibration("stage4", config, final_intrinsics, final_extrinsics, final_distances, interface_normal)
...
stage4_observer.write_trace_csv(ensure_internals_dir(config.output_dir) / "trace_stage4.csv")
```
Rename the four `"stage4"` string literals (and derived filenames) to `"stage3_intrinsic_pass"` uniformly; leave `"stage3"` and `"stage3_rerun"` untouched.

### Doc-page skeleton (frontmatter-free, admonition + `{func}`/`{mod}` cross-refs, `## See Also` footer)
**Source:** `docs/guide/optimizer.md`, `docs/guide/troubleshooting.md`, `docs/guide/cli.md` (all read in full above)
**Apply to:** `docs/guide/configuration.md` (new)

### Diagram-generator contract (`generate(output_dir)` + palette import + `docs/guide/_diagrams/generate_all.py` wiring)
**Source:** `docs/_static/scripts/bfs_pose_graph.py`, `docs/_static/scripts/sparsity_pattern.py`, `docs/_static/scripts/palette.py`, `docs/guide/_diagrams/generate_all.py` (all read in full above)
**Apply to:** `docs/_static/scripts/pose_graph.py` (new)

### BFS→best-first terminology sweep scope (D-17)
**Source:** grep results across `src/`, `docs/`, `README.md` for `BFS`/`bfs`
**Apply to:** `extrinsics.py:513,517,535,583` (best-first, in scope) vs. `extrinsics.py:200,208` (`_find_connected_components`, genuinely BFS, **out of scope** — D-11); `optimizer.md:57,71,73` and `optimizer.md`'s figure alt text; `glossary.md:35`. No other `BFS`/`bfs` occurrences exist in `src/` (confirmed by full-tree grep — the two `extrinsics.py` sites are the entire code-side footprint).

---

## No Analog Found

None — every touched file already exists with a clear current-state read, or (for the two new files) has a strong same-family analog. No file in this phase requires inventing a pattern from RESEARCH.md, since RESEARCH.md does not exist for this phase.

---

## Metadata

**Analog search scope:** `src/aquacal/calibration/`, `src/aquacal/config/`, `src/aquacal/validation/`, `src/aquacal/cli.py`, `docs/guide/`, `docs/_static/scripts/`, `docs/guide/_diagrams/`, `docs/api/`, `tests/unit/`, `README.md`, `CLAUDE.md`
**Files scanned (read or grepped):** `extrinsics.py`, `pipeline.py`, `schema.py`, `refinement.py`, `_optim_common.py`, `_observability.py`, `conditioning.py`, `cli.py`, `example_config.yaml`, `optimizer.md`, `glossary.md`, `index.md`, `troubleshooting.md`, `cli.md`, `config.rst`, `bfs_pose_graph.py`, `sparsity_pattern.py`, `palette.py`, `generate_all.py`, `test_pipeline.py`, `test_refinement.py`, `test_observability.py`, `test_diagnostics.py`, `test_internals.py`, `test_interface_estimation.py`, `README.md`, `CLAUDE.md`
**Pattern extraction date:** 2026-07-24
