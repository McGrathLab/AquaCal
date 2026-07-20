---
phase: quick-2
plan: 2
subsystem: config
tags: [cli, config, discoverability, frame-rejection]
requires:
  - "reject_outlier_frames feature (shipped v1.7.0)"
provides:
  - "Active reject_outlier_frames line in generated + example configs"
affects:
  - src/aquacal/cli.py
  - src/aquacal/config/example_config.yaml
tech-stack:
  added: []
  patterns:
    - "Emit on-by-default toggles as active lines; keep tuning knobs commented"
key-files:
  created: []
  modified:
    - src/aquacal/cli.py
    - src/aquacal/config/example_config.yaml
    - tests/unit/test_cli.py
decisions:
  - "Only the on/off switch is promoted; the three frame_rejection_* tuning knobs stay commented since their defaults are correct"
  - "Test asserts on parsed YAML, not raw text, since raw-text presence cannot distinguish active from commented"
metrics:
  duration: ~6m
  tasks: 2
  files: 3
  completed: 2026-07-20
---

# Quick Task 2: Explicit reject_outlier_frames Param Summary

Made the frame-rejection feature discoverable by emitting `reject_outlier_frames: true` as an active (uncommented) line in the `optimization:` block of generated and example configs, with zero runtime behavior change.

## Problem

A user's real config contained no visible trace of the frame-rejection feature — the line was commented out in the generated config. Users could not tell the feature existed, nor that it was already enabled by default.

## What Changed

**`src/aquacal/cli.py`** — In `_generate_config_yaml`, the `reject_outlier_frames` entry lost its leading `#`, becoming an active YAML line. It stays positioned directly above its three tuning knobs, mirroring how `robust_loss` / `loss_scale` already sit above commented options.

**`src/aquacal/config/example_config.yaml`** — Same one-character change. The multi-line explanatory comment block below it (lines 84-87) was left intact and remains valid YAML comments.

**`tests/unit/test_cli.py`** — `test_generated_config_has_all_fields` now asserts `config["optimization"]["reject_outlier_frames"] is True` on the parsed YAML. This is the assertion that actually proves the line is active; the pre-existing raw-text assertions only prove textual presence.

## Behavior Verification

`pipeline.py:371` reads the key as `bool(opt.get("reject_outlier_frames", True))`. The `.get()` default was confirmed to still be `True`, so an explicit `true` in the config resolves to exactly the same value as an absent key. Runtime behavior is provably identical.

`schema.py` and `pipeline.py` were not modified, per constraint.

## Generated Output

```yaml
optimization:
  robust_loss: "huber"   # Options: "huber", "soft_l1", "linear"
  loss_scale: 1.0        # Residual scale for robust loss (pixels)
  # max_calibration_frames: 150  # Max frames for Stage 3/4 (null = no limit)
  # refine_intrinsics: false  # Stage 4: refine focal lengths and principal points
  # refine_auxiliary_intrinsics: false  # Stage 4b: refine auxiliary camera intrinsics
  reject_outlier_frames: true  # Auto-drop catastrophic-outlier frames after Stage 3 and re-optimize (no-op on clean data)
  # frame_rejection_k: 5.0         # Reject frames with per-frame RMS > k * median RMS
  # frame_rejection_floor_px: 5.0  # ...and only if RMS also exceeds this absolute pixel floor
  # frame_rejection_max_fraction: 0.25  # Guardrail: suppress rejection + warn if more than this fraction would be dropped
```

Parsed result: `{'robust_loss': 'huber', 'loss_scale': 1.0, 'reject_outlier_frames': True}` — the three `frame_rejection_*` knobs are correctly absent from the parsed dict, confirming they remain commented.

## Test Results

- `python -m pytest tests/unit/test_cli.py -q` — **25 passed** in 2.78s
- `python -m pytest tests/ -m "not slow" -q` — **634 passed, 29 deselected** in 64.97s, no regressions

## Deviations from Plan

None - plan executed exactly as written.

## Commits

| Task | Commit | Message |
| ---- | ------ | ------- |
| 1 | `8b6eb0d` | `feat(config): emit reject_outlier_frames as an active line in generated configs` |
| 2 | `5222a57` | `test(cli): assert generated config exposes reject_outlier_frames as True` |

The `feat:` subject on Task 1 ensures python-semantic-release generates the changelog entry on the next release. CHANGELOG.md and version files were not hand-edited.

## Diff Scope

```
 src/aquacal/cli.py                     | 2 +-
 src/aquacal/config/example_config.yaml | 2 +-
 tests/unit/test_cli.py                 | 2 ++
```

Exactly the three intended files.

## Self-Check: PASSED

- `src/aquacal/cli.py` — FOUND, contains active `reject_outlier_frames: true`
- `src/aquacal/config/example_config.yaml` — FOUND, parses to `True`
- `tests/unit/test_cli.py` — FOUND, contains parsed-YAML assertion
- Commit `8b6eb0d` — FOUND
- Commit `5222a57` — FOUND
