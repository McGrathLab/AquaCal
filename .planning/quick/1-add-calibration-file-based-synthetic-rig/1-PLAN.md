---
phase: quick
plan: 1
type: execute
wave: 1
depends_on: []
files_modified:
  - src/aquacal/datasets/synthetic.py
  - src/aquacal/datasets/__init__.py
  - tests/synthetic/ground_truth.py
  - docs/tutorials/02_synthetic_validation.ipynb
autonomous: true
requirements: [QUICK-1]

must_haves:
  truths:
    - "User can set RIG_SIZE = 'calibration' with a path to a calibration.json and the notebook runs all 3 experiments using that rig's geometry"
    - "Existing RIG_SIZE = 'small' and 'large' presets still work identically"
    - "The new rig_from_calibration function is available from the public API"
  artifacts:
    - path: "src/aquacal/datasets/synthetic.py"
      provides: "rig_from_calibration() function"
      contains: "def rig_from_calibration"
    - path: "docs/tutorials/02_synthetic_validation.ipynb"
      provides: "Updated notebook with calibration file support"
      contains: "calibration"
  key_links:
    - from: "docs/tutorials/02_synthetic_validation.ipynb"
      to: "src/aquacal/datasets/synthetic.py"
      via: "rig_from_calibration import"
      pattern: "rig_from_calibration"
    - from: "src/aquacal/datasets/synthetic.py"
      to: "src/aquacal/io/serialization.py"
      via: "load_calibration import"
      pattern: "load_calibration"
---

<objective>
Add the ability to create a synthetic camera rig from a real calibration.json file
in the 02_synthetic_validation.ipynb notebook, alongside existing "small"/"large" presets.

Purpose: Let users validate refractive vs non-refractive calibration using their own
real rig geometry instead of only synthetic presets.

Output: Updated notebook with 3-way RIG_SIZE toggle, new `rig_from_calibration()`
function in the public datasets API.
</objective>

<execution_context>
@C:/Users/tucke/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/tucke/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@src/aquacal/datasets/synthetic.py
@src/aquacal/datasets/__init__.py
@src/aquacal/io/serialization.py
@src/aquacal/config/schema.py
@tests/synthetic/ground_truth.py
@docs/tutorials/02_synthetic_validation.ipynb
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add rig_from_calibration() to datasets/synthetic.py and export it</name>
  <files>
    src/aquacal/datasets/synthetic.py
    src/aquacal/datasets/__init__.py
    tests/synthetic/ground_truth.py
  </files>
  <action>
Add a new function `rig_from_calibration()` to `src/aquacal/datasets/synthetic.py` that:

```python
def rig_from_calibration(
    calibration_path: str | Path,
) -> tuple[dict[str, CameraIntrinsics], dict[str, CameraExtrinsics], dict[str, float]]:
```

- Accepts a path to a calibration.json file
- Uses `load_calibration()` from `aquacal.io.serialization` to load it
- Extracts and returns `(intrinsics, extrinsics, water_zs)` dicts keyed by camera name, matching the same return signature as `generate_real_rig_array()` and `generate_camera_array()`
- For each camera in the CalibrationResult: pull `cam.intrinsics`, `cam.extrinsics`, and `cam.water_z`
- Add `from pathlib import Path` import at top (already has `from __future__ import annotations`)
- Add `from aquacal.io.serialization import load_calibration` import

Also extract the `BoardConfig` from the calibration file and return it. Change the return type to a 4-tuple:
```python
) -> tuple[dict[str, CameraIntrinsics], dict[str, CameraExtrinsics], dict[str, float], BoardConfig]:
```
This way the notebook can use the real board config too. The last element is the board config from the calibration file.

Add Google-style docstring with Args/Returns/Raises/Example sections.

Then update `src/aquacal/datasets/__init__.py`:
- Add `rig_from_calibration` to the import from `aquacal.datasets.synthetic`
- Add `"rig_from_calibration"` to `__all__`

Then update `tests/synthetic/ground_truth.py`:
- Add `rig_from_calibration` to the re-export imports from `aquacal.datasets.synthetic` (with `# noqa: F401` since it's a re-export)
  </action>
  <verify>
Run `python -c "from aquacal.datasets import rig_from_calibration; print('OK')"` to confirm import works.
Run `python -c "from tests.synthetic.ground_truth import rig_from_calibration; print('OK')"` to confirm re-export works.
  </verify>
  <done>
`rig_from_calibration()` is importable from both `aquacal.datasets` and `tests.synthetic.ground_truth`, accepts a calibration.json path, and returns (intrinsics, extrinsics, water_zs, board_config) matching the same dict structure as existing rig generators.
  </done>
</task>

<task type="auto">
  <name>Task 2: Update 02_synthetic_validation.ipynb to support calibration file rig</name>
  <files>docs/tutorials/02_synthetic_validation.ipynb</files>
  <action>
Modify the notebook to support a third RIG_SIZE option. The changes are surgical -- only
the config/setup cells change; experiment logic cells remain untouched.

**Cell "cell-rig-size"** -- Change to:
```python
# Toggle rig size:
#   "small" — 4 cameras, 20 frames, ideal conditions. Fast, ~2 min total.
#   "large" — 13 cameras, 30 frames, realistic noise. Compelling results, ~60 min total.
#   "calibration" — Use geometry from a real calibration.json file.
RIG_SIZE = "large"

# Only used when RIG_SIZE = "calibration":
CALIBRATION_PATH = r"C:\Users\tucke\Desktop\Aqua\AquaCal\release_calibration\calibration.json"
```

**Cell "cell-imports"** -- Add `rig_from_calibration` to the import from `tests.synthetic.ground_truth`:
```python
from tests.synthetic.ground_truth import (
    SyntheticScenario,
    create_scenario,
    generate_dense_xy_grid,
    generate_real_rig_array,
    generate_real_rig_trajectory,
    generate_synthetic_detections,
    rig_from_calibration,
)
```

**Cell "cell-preset-heading"** markdown -- Add a paragraph about the "calibration" option:
Append: 'The `"calibration"` option loads camera geometry from an existing calibration.json
file, letting you run the same experiments with your real rig layout.'

**Cell "cell-preset-config"** -- Add an `elif RIG_SIZE == "calibration"` branch. This needs to:
1. Call `rig_from_calibration(CALIBRATION_PATH)` to get `(intrinsics, extrinsics, water_zs, board_config)`
2. Set `SCENARIO_NAME = "calibration"` (will be handled specially below)
3. Compute reasonable experiment parameters from the rig geometry:
   - Determine water surface Z from `water_zs` (use mean)
   - Set `EXP2_CALIB_RANGE` to a narrow band centered ~0.3m below water (e.g., `(water_z + 0.20, water_z + 0.40)`)
   - Set `EXP2_TEST_DEPTHS` spanning from just below water to ~1.5m below
   - Set `EXP2_N_CALIB_FRAMES = 50`
   - Set `EXP3_SWEEP_DEPTHS` spanning same range
   - Set `EXP3_N_CALIB_FRAMES = 30`
4. Print the loaded camera count and derived depths

**Cell "cell-exp1-run"** -- Currently calls `create_scenario(SCENARIO_NAME, ...)`. For
the calibration path, we need a SyntheticScenario. Add logic: if `SCENARIO_NAME == "calibration"`,
build a SyntheticScenario manually from the loaded rig (similar to how the "realistic" preset
works but using the loaded intrinsics/extrinsics/water_zs). Use `generate_real_rig_trajectory()`
for board poses since the real rig has similar geometry. Specifically:
```python
if SCENARIO_NAME == "calibration":
    _cal_intr, _cal_extr, _cal_wz, _cal_board = rig_from_calibration(CALIBRATION_PATH)
    _cal_poses = generate_real_rig_trajectory(n_frames=30, depth_range=(EXP2_CALIB_RANGE[0], EXP3_SWEEP_DEPTHS[-1]), seed=42)
    scenario = SyntheticScenario(
        name="calibration",
        board_config=_cal_board,
        intrinsics=_cal_intr,
        extrinsics=_cal_extr,
        water_zs=_cal_wz,
        board_poses=_cal_poses,
        noise_std=0.5,
        description=f"Real rig from {Path(CALIBRATION_PATH).name}: {len(_cal_intr)} cameras",
    )
else:
    scenario = create_scenario(SCENARIO_NAME, seed=42)
```

**Cell "cell-exp2-setup"** -- Add an `elif RIG_SIZE == "calibration"` branch alongside the
existing `if RIG_SIZE == "small"` / `else` (which handles "large"). This branch should:
1. Load rig via `rig_from_calibration(CALIBRATION_PATH)` (or reuse from cell-preset-config if variables are in scope -- they are since notebooks share state, but the existing pattern re-creates the rig in each experiment cell, so follow the same pattern for consistency)
2. Actually, looking at the notebook more carefully: the `else` branch (large preset) calls
   `generate_real_rig_array()` directly. For calibration, replace with `rig_from_calibration()`.
   The cleanest approach: change the `if/else` to `if/elif/else` with a `"calibration"` branch.
   The calibration branch sets `intrinsics_exp2`, `extrinsics_exp2`, `water_zs_exp2`,
   `board_config_exp2` from the loaded calibration, and uses the same `noise_std_exp2 = 0.5`,
   `n_grid_exp2 = 7`, `xy_extent_exp2 = 0.5`, `tilt_deg_exp2 = 3.0` as the large preset.
3. For trajectory generation: use `generate_real_rig_trajectory()` (same as large preset).

**Cell "cell-exp3-run"** -- Same pattern: add `elif RIG_SIZE == "calibration"` that mirrors
the large preset but uses `rig_from_calibration()` for rig geometry.

IMPORTANT: Do NOT change any experiment logic, plotting cells, or analysis cells. Only
the rig initialization and config cells change. The notebook's experiment cells work on
generic `intrinsics_expN`, `extrinsics_expN`, `water_zs_expN` variables regardless of source.

Also add `from pathlib import Path` to the imports cell (needed for the `Path(CALIBRATION_PATH).name` in the description). Check if it's already imported -- yes it is (`from pathlib import Path`).
  </action>
  <verify>
Open the notebook and verify:
1. The cell structure is intact (all cell IDs preserved)
2. `RIG_SIZE = "small"` still follows the same code path as before
3. `RIG_SIZE = "large"` still follows the same code path as before
4. `RIG_SIZE = "calibration"` follows the new code path
5. No syntax errors: `python -c "import json; json.load(open('docs/tutorials/02_synthetic_validation.ipynb'))"`
  </verify>
  <done>
The notebook supports three RIG_SIZE options: "small", "large", and "calibration". Setting
RIG_SIZE = "calibration" with a valid CALIBRATION_PATH runs all three experiments using the
real rig geometry. Existing presets are unchanged.
  </done>
</task>

</tasks>

<verification>
- `python -c "from aquacal.datasets import rig_from_calibration; print('import OK')"` succeeds
- `python -c "import json; json.load(open('docs/tutorials/02_synthetic_validation.ipynb')); print('valid JSON')"` succeeds
- `python -m pytest tests/ -m "not slow" -x -q` passes (no regressions)
</verification>

<success_criteria>
1. `rig_from_calibration()` is in the public API and returns (intrinsics, extrinsics, water_zs, board_config) from a calibration.json
2. The notebook supports RIG_SIZE = "calibration" with a file path, running all 3 experiments with real rig geometry
3. Existing "small" and "large" presets are completely unchanged in behavior
4. All existing tests pass
</success_criteria>

<output>
After completion, create `.planning/quick/1-add-calibration-file-based-synthetic-rig/1-SUMMARY.md`
</output>
