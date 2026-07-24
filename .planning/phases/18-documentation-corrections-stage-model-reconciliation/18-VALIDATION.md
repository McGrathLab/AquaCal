---
phase: 18
slug: documentation-corrections-stage-model-reconciliation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-24
---

# Phase 18 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `18-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (`[tool.pytest.ini_options]` in `pyproject.toml`; `slow` marker for optimization-heavy tests) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `python -m pytest tests/unit/test_optim_common.py -v` |
| **Full suite command** | `python -m pytest tests/ -m "not slow"` |
| **Docs build command** | `python docs/guide/_diagrams/generate_all.py && sphinx-build -W --keep-going -b html docs docs/_build/html` |
| **Estimated runtime** | ~5 s quick · ~90 s fast suite · ~40 min full suite (slow tests included) |

**Note on the docs build:** `docs/conf.py`'s diagram-generation hook swallows subprocess
crashes, so `generate_all.py` MUST be run standalone first — otherwise a generator failure
surfaces only as a missing-image warning. CI runs `sphinx-build -W --keep-going`, so
warnings are fatal there.

---

## Sampling Rate

- **After every task commit:** the unit test file covering whatever was touched
  (`test_optim_common.py` for the DOCS-01 assertion; `test_pipeline.py` /
  `test_refinement.py` / `test_observability.py` for the stage-key rename), plus both grep
  guards for any docs-touching task.
- **After every plan wave:** `python -m pytest tests/ -m "not slow"` plus the docs build command.
- **Before `/gsd:verify-work`:** full suite green (`python -m pytest tests/`) AND docs build
  exits 0 AND both grep guards return zero matches.
- **Max feedback latency:** ~90 seconds (fast suite).

---

## Per-Task Verification Map

Task IDs are filled in after planning completes. Requirement-level coverage is fixed now:

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | DOCS-01 | — | N/A (docs-only, no attack surface) | unit | `pytest tests/unit/test_optim_common.py -v -k grouping_numbers` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | DOCS-02 | — | N/A | grep guard | `grep -rn "BFS\|breadth.first" src/ docs/ README.md \| grep -v "_find_connected_components"` (expect only the two legitimate `extrinsics.py` sites) | N/A shell | ⬜ pending |
| TBD | TBD | TBD | DOCS-03 | — | N/A | smoke | `python docs/guide/_diagrams/generate_all.py && test -f docs/_static/diagrams/pose_graph.png && test ! -f docs/_static/diagrams/bfs_pose_graph.png` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | DOCS-04 | — | N/A | build check | `sphinx-build -W --keep-going -b html docs docs/_build/html` (new `configuration.md` must be in the toctree or `-W` fails) | ✅ existing | ⬜ pending |
| TBD | TBD | TBD | DOCS-06 | — | N/A | grep guard | `grep -rn "\"stage4\"\|stage4_joint_refinement\|trace_stage4\|calibration_stage4" src/` (expect zero matches) | N/A shell | ⬜ pending |
| TBD | TBD | TBD | DOCS-06 | — | N/A | unit | `pytest tests/unit/test_pipeline.py tests/unit/test_refinement.py tests/unit/test_observability.py tests/unit/test_diagnostics.py tests/unit/test_internals.py tests/unit/test_interface_estimation.py -v` | ✅ existing | ⬜ pending |
| TBD | TBD | TBD | phase gate | — | N/A | build check | `python docs/guide/_diagrams/generate_all.py && sphinx-build -W --keep-going -b html docs docs/_build/html` | ✅ existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_optim_common.py` — new file covering DOCS-01. Asserts, against the
      **shipped** `build_jacobian_sparsity` + `build_structural_column_groups` path (not
      `scipy.optimize._numdiff.group_columns`), for a 13-camera / 100-frame configuration:
      P = 673 (base) / 675 (tilt) / 727 (tilt + intrinsics); group count = 13 / 13 / 17;
      and that the group count is invariant in rig size. See `18-RESEARCH.md` § DOCS-01
      Numbers for the exact assertion spec — every figure was measured and confirmed
      during research (51.8× / 51.9× / 42.8×).
- [ ] No fixture or framework gaps — pytest and the `slow` marker are configured, and the
      synthetic helpers the new test needs (`generate_camera_array`,
      `generate_board_trajectory`, `generate_synthetic_detections`) already exist and were
      exercised successfully during research.
- [ ] The DOCS-02 / DOCS-06 grep guards are deliberately **not** pytest tests — they assert
      the *absence* of a stale string across three directories, which is cheaper and more
      direct as a shell one-liner. They must still be recorded as explicit verification
      steps in the plans rather than left to manual review.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| The three-stage vocabulary matches the **revised** manuscript | DOCS-06 | The only manuscript on disk (`Desktop\main.pdf`, 2026-06-15, C1 = v1.6.0) describes a **four**-stage pipeline and uses BFS throughout — contradicting D-02/D-04/D-05. It is almost certainly the pre-revision submission (it still carries the ~685→~50 grouping claim this milestone is fixing), but no newer draft exists on disk. | Before the rename lands, confirm against the revision draft that (a) the pipeline is presented as three stages with intrinsic refinement as a mode of Stage 3, and (b) the traversal is described as best-first. If the revision keeps four stages / BFS, DOCS-02 and DOCS-06 must be re-scoped — DOCS-01, DOCS-03, DOCS-04 are unaffected either way. |
| Regenerated pose-graph figure is visually correct | DOCS-03 | Edge direction and the single redundant undirected edge are semantic properties a file-existence check cannot assert. | Open `docs/_static/diagrams/pose_graph.png`. Confirm: exactly 6 directed discovery edges over 4 cameras + 3 frames, each pointing from the known pose to the one it determines; exactly 1 grey undirected redundant observation edge; legend keys all correspond to a drawn element; title no longer says "BFS". |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (`tests/unit/test_optim_common.py`)
- [ ] No watch-mode flags
- [ ] Feedback latency < 90 s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
