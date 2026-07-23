---
phase: 17
phase_name: per-camera-interface-ablation-mode
status: passed
verified: 2026-07-23
requirements: [IFACE-01, IFACE-02, IFACE-03, IFACE-04, IFACE-05]
---

# Phase 17 Verification: Per-Camera Interface Ablation Mode

**Goal:** A per-camera `water_z` ablation is available for the WP6 experiment and is
provably correct, without disturbing the default shared-interface behavior the paper's
central claim rests on.

**Result: PASSED.** All 5 requirements verified against the codebase; full test suite
799 passed / 0 failed (including all slow synthetic tests).

## Requirement Traceability

| Req | Status | Evidence |
|-----|--------|----------|
| IFACE-01 | ✓ | `CalibrationConfig.shared_interface: bool = True` (schema.py) with analysis/ablation docstring; `load_config` pass-through; `aquacal init` commented line (cli.py); ablation stub in docs/guide/refractive_geometry.md; single reason-bearing WARNING at pipeline start (pipeline.py). |
| IFACE-02 | ✓ | `pack_params`/`unpack_params`/`build_jacobian_sparsity`/`build_bounds` handle N per-camera water_z (the dense column becomes N sparse columns) — 25 shared_interface references in _optim_common.py; end-to-end through both BA stages. |
| IFACE-03 | ✓ | `build_structural_column_groups` valid in all 8 mode combinations (shared/per-camera × intrinsics on/off × tilt on/off), asserted by `TestPerCameraInterface::test_grouping_valid_all_modes`; group count stays 13/17. |
| IFACE-04 | ✓ | Individual per-camera seeding via `water_z_per_camera` (never a mean); `_resolve_per_camera_water_z_seeds` (None/partial/unknown/auxiliary rules); always-on `internals/interface_spread.json` (meters) + mm console summary. |
| IFACE-05 | ✓ | Packing-layer bit-identity (rtol=0/atol=0) + end-to-end shared-mode determinism + equal-seed per-camera recovery to machine precision on shared ground truth. |

## Must-Haves Verified

1. **Shared path bit-unchanged (IFACE-05).** `TestSharedModeBitIdentityIFACE05` asserts
   exact equality between the default and `shared_interface=True` for pack/bounds/sparsity/
   groups; `test_shared_mode_end_to_end_bit_exact` proves Stage 3 determinism. Confirmed.
2. **Per-camera parameterization correct (IFACE-02/03).** N per-camera water_z columns,
   each nonzero only in its camera's rows; valid grouping in all 8 modes; group count
   invariant. Confirmed.
3. **Individual seeding + spread report (IFACE-04).** Seeds resolved per camera (not
   collapsed); spread report always written in per-camera mode. Confirmed.
4. **Equal-seed recovery (IFACE-05).** Per-camera mode with equal seeds on shared-interface
   ground truth recovers the shared solution to ~1e-15 (water_z spread, mean, extrinsics,
   RMS all match). Confirmed.
5. **Default pipeline path unchanged.** Shared mode never routes through the per-camera
   seed resolver, spread report, or per-camera packing; the ablation is guarded behind
   `if not config.shared_interface`. Confirmed.

## Notable Finding (resolved within the phase)

Plan 17-05's recovery test exposed a Rule-1 bug that plans 17-01/17-03 missed: `compute_residuals`
unpacked parameters in shared mode unconditionally, so per-camera mode read a single water_z and
misaligned every later block — the optimizer diverged (RMS ~148 even from the noiseless optimum).
Fixed by threading `shared_interface` through `compute_residuals` → `unpack_params` and into
`cost_args` for both optimizers. Post-fix, per-camera mode recovers the shared solution to machine
precision. The fast-suite guard (`test_per_camera_interface_runs_end_to_end`, RMS < 5.0) now prevents
regression. This is exactly the failure the IFACE-05 safety net exists to catch.

## Test Evidence

- Full suite: **799 passed, 0 failed** (40 min, all slow tests included).
- Fast suite: 768 passed / 31 deselected.
- Per-plan verify commands all pass (test_optim_common, test_observability, test_interface_estimation,
  test_refinement, test_pipeline, test_per_camera_interface).

## Deferred (out of scope, intentional)

- Full new-feature documentation (worked example, WP6 interpretation) — deferred to Phase 21 per CONTEXT.
- Per-camera tilt / interface normal — explicitly out of scope; only water_z becomes per-camera.

---
*Phase 17 verified 2026-07-23 — PASSED.*
