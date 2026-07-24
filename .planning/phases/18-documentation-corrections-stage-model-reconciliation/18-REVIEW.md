---
phase: 18-documentation-corrections-stage-model-reconciliation
reviewed: 2026-07-24T16:45:07Z
depth: standard
files_reviewed: 15
files_reviewed_list:
  - src/aquacal/calibration/pipeline.py
  - src/aquacal/calibration/extrinsics.py
  - src/aquacal/calibration/refinement.py
  - src/aquacal/calibration/_optim_common.py
  - src/aquacal/calibration/_observability.py
  - src/aquacal/calibration/intrinsics.py
  - src/aquacal/validation/conditioning.py
  - src/aquacal/config/schema.py
  - src/aquacal/config/example_config.yaml
  - src/aquacal/cli.py
  - docs/_static/scripts/pose_graph.py
  - docs/guide/_diagrams/generate_all.py
  - tests/unit/test_optim_common.py
  - tests/unit/test_pipeline.py
  - tests/unit/test_refinement.py
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
status: issues_found
---

# Phase 18: Code Review Report

**Reviewed:** 2026-07-24T16:45:07Z
**Depth:** standard
**Files Reviewed:** 15
**Status:** issues_found

## Summary

This phase's stated intent was purely cosmetic: rename the "stage4" vocabulary to
"stage3_intrinsic_pass" across code, and correct documentation numbers. I traced every
non-test `src/` diff line-by-line against the pre-phase baseline (`5f24d71`) and confirmed
no executable statement changed in `extrinsics.py`, `intrinsics.py`, `_optim_common.py`,
`_observability.py`, `refinement.py`, or `conditioning.py` — every hunk there is a
docstring, comment, or module-docstring edit. `schema.py`, `cli.py`, and
`example_config.yaml` changes are comment-only and the generated-config template still
matches the shipped example config for the renamed fields.

`pipeline.py` carries the only file with real rename surface area (dict keys, filenames,
console strings). I verified every constructed string (`timings[...]`, `trace_*.csv`,
`calibration_*.json`, the `stage3_intrinsic_pass`/`stage3_rerun`/`stage3` tag literals used
for conditioning/spread selection) is consistent end-to-end: no dangling `stage4` key is
written or read anywhere in `src/`, `tests/`, or docs guide pages (confirmed by a
whole-tree grep). `tests/unit/test_pipeline.py` was updated in lockstep with the renamed
literals it asserts against.

Two issues are worth flagging. First, one of the three new
`TestDocumentedGroupingNumbers` tests in `test_optim_common.py` doesn't actually derive
its assertion from the live code path it claims to guard — it recomputes the FD-reduction
ratio from the hardcoded parametrize table instead of from the values `build_structural_
column_groups` just produced in the sibling test. Second, `docs/_static/scripts/
pose_graph.py`'s hand-replayed traversal duplicates the production heap logic from
`estimate_extrinsics` with no test tying the two together, so a future algorithm change
could silently make the figure misrepresent the traversal it claims to illustrate.

## Warnings

### WR-01: `test_fd_reduction_matches_optimizer_md` doesn't test the live derivation it claims to

**File:** `tests/unit/test_optim_common.py:253-266`

**Issue:** The docstring for `TestDocumentedGroupingNumbers` states "Derived live from
`build_jacobian_sparsity` + `build_structural_column_groups`" and the class comment says
"if a test here changes, `docs/guide/optimizer.md` must change in the same commit." That
claim holds for `test_parameter_and_group_counts_match_optimizer_md` (which does call
`_make_pattern` + `build_structural_column_groups` and asserts against the live
`S.shape[1]` / `groups.max() + 1`). It does **not** hold for
`test_fd_reduction_matches_optimizer_md`:

```python
def test_fd_reduction_matches_optimizer_md(
    self, normal_fixed, refine_intrinsics, expected_P, expected_groups
):
    reduction = expected_P / expected_groups
    assert 43 <= round(reduction) <= 52
```

`expected_P` and `expected_groups` here are the hardcoded constants from
`_DOCUMENTED_CONFIGS`, not the values just computed by calling
`build_structural_column_groups`. This test only checks that the parametrize table's own
numbers divide out to something between 43 and 52 — it passes even if
`build_structural_column_groups`'s real output has drifted arbitrarily from
`_DOCUMENTED_CONFIGS`, because it never calls the function under test. If someone changes
the sparsity/grouping code such that the real reduction moves outside 43–52x while
forgetting to update `_DOCUMENTED_CONFIGS`, `test_parameter_and_group_counts_match_
optimizer_md` would catch the P/groups drift, but this test contributes nothing beyond
that — it is redundant arithmetic on a constant, not a second live check, despite reading
as one.

**Fix:** Compute the ratio from the same live call the first test makes, e.g. thread the
computed `S.shape[1]` / `groups.max() + 1` through (or just call
`build_structural_column_groups` again inside this test) rather than reusing the
parametrize literals:

```python
def test_fd_reduction_matches_optimizer_md(
    self, normal_fixed, refine_intrinsics, expected_P, expected_groups
):
    S = _make_pattern(13, 100, 1.0, refine_intrinsics, normal_fixed)
    groups = build_structural_column_groups(
        S, 13, 100, refine_intrinsics=refine_intrinsics, normal_fixed=normal_fixed
    )
    reduction = S.shape[1] / (groups.max() + 1)
    assert 43 <= round(reduction) <= 52
```

### WR-02: `pose_graph.py`'s hand-replayed traversal can silently drift from `estimate_extrinsics`

**File:** `docs/_static/scripts/pose_graph.py:81-113`

**Issue:** `_replay_traversal` is a hand-maintained copy of the priority-heap loop inside
`estimate_extrinsics` (`src/aquacal/calibration/extrinsics.py:596-680`), reimplemented to
classify pose-graph edges as "discovery" vs "redundant" for the figure. The module
docstring's claim that "the figure therefore cannot drift from the library's actual
traversal" is not backed by any test — there is no assertion anywhere (grepped
`tests/` and `docs/guide/_diagrams`) that `_replay_traversal`'s discovery-edge set matches
what `estimate_extrinsics` itself would compute for the same fixture. Today the two loops
are equivalent for the toy fixture (both seed `[(0, reference_camera)]`, mark visited
before pushing, and process all unvisited neighbours of a popped node in one pass), but
the replay never calls `estimate_extrinsics` or `refractive_solve_pnp`/`estimate_board_
pose` — it assumes PnP always succeeds and skips the `result is None: continue` failure
path present in production. If `estimate_extrinsics`'s heap logic, tie-breaking, or
failure handling changes in a future edit (a highly plausible target, since it is the
project's most algorithmically nontrivial function), this script's copy will not be
touched by that change and the generated figure will keep depicting the old algorithm
without any signal that it needs regenerating.

**Fix:** Add a regression test (in `tests/unit/` or alongside the script) that runs the
same fixture through both `_replay_traversal` and the real `estimate_extrinsics`
(inspecting which camera/frame each PnP call resolved, e.g. via a spy on
`refractive_solve_pnp`/`estimate_board_pose`, or by comparing the visitation order) and
fails if they diverge. At minimum, add a code comment pointing at the specific line range
in `extrinsics.py` this replay must be kept in sync with, so a future editor of
`estimate_extrinsics` knows to check this file.

## Info

### IN-01: Redundant phrase in `refinement.py` module docstring

**File:** `src/aquacal/calibration/refinement.py:1`

**Issue:** The rename produced an awkward doubled clause:

```python
"""Stage 3's second pass, with intrinsics unlocked, with optional intrinsics optimization.
```

"with intrinsics unlocked" and "with optional intrinsics optimization" say the same thing
twice in one sentence, a leftover of mechanically inserting the new stage name in front of
the pre-existing tail.

**Fix:**

```python
"""Stage 3's second pass, with intrinsics unlocked (optional)."""
```

### IN-02: Tutorial notebook's cached cell output still shows the retired "Stage 3b" label

**File:** `docs/tutorials/01_full_pipeline.ipynb:293`

**Issue:** `pipeline.py`'s auxiliary-registration console string was changed from
`[Stage 3b]`/`[Stage 4b]` to `[Auxiliary camera registration]` (D-23). The tutorial
notebook's saved cell output was not regenerated and still shows the old string:
`"[Stage 3b] Registering 1 auxiliary camera(s)...\n"`. This isn't executed code, but a
reader running the notebook fresh will see console output that no longer matches the
saved example output right next to it, which undercuts the "generated diagram/output
matches the library" intent of this phase.

**Fix:** Re-execute `docs/tutorials/01_full_pipeline.ipynb` (or at least patch the stale
cell output) so the saved output matches the current console string.

---

_Reviewed: 2026-07-24T16:45:07Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
