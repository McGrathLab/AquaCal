---
status: diagnosed
trigger: "E6 generalization sweep fails at every seed except 42; two open questions from Phase 19.3's .continue-here.md remain undiagnosed"
created: 2026-08-03
updated: 2026-08-03
goal: find_root_cause_only
phase: 19.3
---

# Debug: E6 is seed-locked to 42 via the frozen clearance floor

## Scope

**Diagnose only.** No code changes, no commits to experiment code. Phase 19.3 is parked
at plan 10's Task 3 human checkpoint; the fix will land in a **new phase created after
19.3 closes**. This report is the input to that phase's planning.

## Symptoms

**Expected:** `e6_generalization_sweep.py` runs all 14 configurations at any seed, as E1
and E7 do (both swept x10 successfully).

**Actual:** only seed 42 completes. Six other seeds produce 14/14 `status=failed` rows.
All of them **exit 0** — E6 records a per-configuration failure as a row rather than
raising, so the process reports success. Failure is only visible by checking `status`
counts or noticing the wall clock.

| seed | outcome | wall clock | required floor in error |
|---|---|---|---|
| 42 | `{'ok': 14}` | 96.6 min | — (passes) |
| 43 | `{'failed': 14}` | ~1 s | 1.1823 |
| 44 | `{'failed': 14}` | ~1 s | (not captured) |
| 45 | `{'failed': 14}` | ~1 s | (not captured) |
| 46 | `{'failed': 14}` | ~1 s | (not captured) |
| 47 | `{'failed': 14}` | 74 min | 1.1830 |
| 50 | `{'failed': 14}` | 84 min | 1.1839 |

**Error (identical text at every failing seed and configuration):**

```
ValueError: depth_range[0]=1.181852154281008 is below the derived clearance floor
1.1823 m (board=BoardConfig(squares_x=12, squares_y=9, square_size=0.06,
marker_size=0.045, dictionary='DICT_5X5_100', legacy_pattern=False),
rotation_range_deg=15.0). A board centre shallower than 1.1823 m can raise a corner
above the deepest interface (D-19.3-01). Either raise depth_range[0] to at least the
derived floor, or pass depth_range=None to use the derived default.
```

**Timeline:** never worked at any seed but 42. The frozen constant was derived *from*
seed 42, which is why it sits at exactly zero margin there. Surfaced 2026-08-03 during
the Phase 19.3 seed sweeps.

**Reproduction:** `python -u experiments/e6_generalization_sweep.py` with any seed != 42.
Do NOT use this to diagnose — 74-96 min per seed. Diagnose from code plus cheap
standalone reproductions of scenario construction.

## Open questions (the actual objective)

**Q1. Why do 43-46 fail in ~1 second while 47 and 50 burn 74-84 minutes before also
failing all 14?** Both paths end at 14/14 failed; one does substantial real computation
first, the other does none. No hypothesis has been tested.

**Q2. Why were the predicted-legal seeds not legal?** A per-seed slack calculation
predicted 42/47/50 would pass; 47 and 50 did not. The prediction used a standalone
`generate_camera_array` call that is known not to reproduce E6's real scenario
construction — but the actual mechanism has not been verified.

## Leading hypothesis (from the orchestrator, untested)

There are **two distinct scenario-construction call sites** in the E6 path, each building
its own camera array with its own `max(water_zs)` and therefore its own required floor.

Evidence: in `seed_sweep_19_3/e6/seed_43/stdout.log` there is **no `Stage 2:` line at
all** — the guard rejects before any calibration. In `seed_47` and `seed_50` each
configuration prints `Stage 2:`, `Stage 3:`, and converged first-order optimality, and
*then* raises. The required floors also differ per seed (1.1823 / 1.1830 / 1.1839),
which a single frozen consumer would not produce.

If true, this answers Q1 (43-46 trip the early call site, 47/50 clear it and trip a later
one) and Q2 (the standalone reproduction modelled only the early/baseline array).

## Established mechanism (from F12, partially verified)

`GRID_DEPTH_RANGE[0] = board_clearance_floor(GRID_BOARD_CONFIG, _grid_baseline_water_zs,
15.0)` at `experiments/e4_benchmark_grid.py:258` is evaluated **once at import**, from
the baseline camera array. Camera heights are seed-dependent, so `max(water_zs)` — and
the required clearance floor — varies per seed and per configuration. The frozen constant
is legal only where the array's max water_z does not exceed the baseline's.

`build_grid_scenario:589` falls back to the frozen constant when `depth_range=None`, so
the guard's own suggested remedy **does not work** — that line itself must change.

## Constraints binding this investigation

- **Do not re-run a full E6 sweep** to diagnose. 74-96 min per seed.
- **Anti-pattern 7 (blocking):** do not treat a single-seed observation as a general
  effect. Every mechanism claim must be demonstrated across enough seeds/configurations
  to distinguish it from a coincidence. Seven errors of exactly this class were made on
  2026-08-03.
- **The F12 slack table is WITHDRAWN as wrong.** Do not reuse its numbers. It is retained
  in `19.3-CODE-TRACE-FINDINGS.md` only as a record of the error.
- The published seed-42 E6 results are **not in question** and must not be re-litigated.
- Fix inertness at seed 42 is **already verified** (derived floor is bit-identical to the
  frozen constant; `generate_board_trajectory(depth_range=None)` reproduces
  `depth_range=GRID_DEPTH_RANGE` on all 100 frames, rvec and tvec).

## Reference material

- `.planning/phases/19.3-scenario-geometry-and-convergence/.continue-here.md` — START HERE section
- `.planning/phases/19.3-scenario-geometry-and-convergence/19.3-CODE-TRACE-FINDINGS.md` — F12, "F12 SHARPENED", "F12 FINAL"
- `seed_sweep_19_3/e6/seed_{42,43,44,45,46,47,50}/` — raw sweep output, gitignored
- `experiments/e6_generalization_sweep.py`, `experiments/e4_benchmark_grid.py`

## Current Focus

- hypothesis: CONFIRMED (with a correction). The two call sites are `run_configuration`'s
  own two `build_grid_scenario` calls — the calibration scenario at `seed` (line 759) and
  the held-out scenario at `seed + 1_000_000` (line 787). Each draws its own camera array
  with its own `max(water_zs)`, hence its own derived floor; both are checked against the
  same frozen `GRID_DEPTH_RANGE[0]`.
- test: computed `board_clearance_floor` for both arrays at every swept seed and compared
  to the floor printed in each of the 72 per-configuration failure records.
- expecting: 43–46's printed floor == floor(seed); 47/50's printed floor == floor(seed+1e6).
- result: exact match at 4 dp for all 6 failing seeds x 12 configurations. Investigation
  complete; Resolution written.
- next_action: none — report delivered. Fix lands in a new phase after 19.3 closes.

## Evidence

- timestamp: 2026-08-03 (orchestrator, pre-session)
  observation: `seed_43/stdout.log` contains zero `Stage 2:` lines; `seed_47` and `seed_50` print `Stage 2:`, `Stage 3:`, and converged optimality for every one of the 14 configurations before each raises.
  source: `seed_sweep_19_3/e6/seed_{43,47,50}/stdout.log`
  implication: the fast and slow failures raise from different points in the E6 path, not the same one.

- timestamp: 2026-08-03 (orchestrator, pre-session)
  observation: the required floor in the error text differs per seed — 1.1823 (43), 1.1830 (47), 1.1839 (50) — while the rejected value is the same frozen 1.181852154281008 everywhere.
  source: same logs
  implication: the floor is being derived per-run from seed-dependent geometry, while the value it is compared against is frozen at import.

- timestamp: 2026-08-03 (session)
  checked: `status_reason` in all 72 per-configuration checkpoints under
  `seed_sweep_19_3/e6/seed_{43,44,45,46,47,50}/e6_configs/*.json`.
  found: within a seed, all 12 configurations report an IDENTICAL required floor
  (43→1.1823, 44→1.1819, 45→1.1850, 46→1.1848, 47→1.1830, 50→1.1839), and all 12 report
  the same rejected value 1.181852154281008.
  implication: the derived floor does not vary with layout, spacing, or index — only with
  seed. Rules out any per-configuration geometry explanation.

- timestamp: 2026-08-03 (session)
  checked: standalone probe computing `board_clearance_floor(GRID_BOARD_CONFIG,
  generate_camera_array(12, layout, spacing, GRID_HEIGHT_ABOVE_WATER, seed).water_zs, 15.0)`
  for seeds 42–50 and for their holdout counterparts seed+1_000_000.
  found:
  | seed | floor(seed) | legal | floor(seed+1e6) | legal | observed failing floor | site |
  |---|---|---|---|---|---|---|
  | 42 | 1.181852 | yes | 1.181380 | yes | — (14/14 ok) | — |
  | 43 | 1.182348 | NO | 1.185809 | NO | 1.1823 | calibration |
  | 44 | 1.181898 | NO | 1.184115 | NO | 1.1819 | calibration |
  | 45 | 1.184952 | NO | 1.181454 | yes | 1.1850 | calibration |
  | 46 | 1.184808 | NO | 1.184259 | NO | 1.1848 | calibration |
  | 47 | 1.181261 | yes | 1.182966 | NO | 1.1830 | HOLDOUT |
  | 50 | 1.180099 | yes | 1.183873 | NO | 1.1839 | HOLDOUT |
  implication: every observed failing floor matches, to all 4 printed decimals, the floor
  of exactly one of the two arrays `run_configuration` builds. 6/6 seeds, 72/72
  configurations. The mechanism is established, not inferred.

- timestamp: 2026-08-03 (session)
  checked: `seed_sweep_19_3/e6/seed_47/stdout.log` and `seed_43/stdout.log` line ordering.
  found: seed 43 contains zero `Stage 2:` lines. Seed 47 emits `Stage 2:` then `Stage 3:`
  immediately BEFORE each of the 11 non-cached `Configuration ... failed` lines; the 12th
  (`axis=layout axis_value=grid`) is the cached `baseline` config_key re-read, so it
  correctly has no solve of its own.
  implication: confirms the fast path raises at `build_grid_scenario` line 759 (before
  `calibrate_synthetic`) and the slow path raises at line 787 (after a completed Stage 2 +
  Stage 3), whose result is then discarded by the blanket `except Exception`.

- timestamp: 2026-08-03 (session)
  checked: sensitivity of the derived floor to layout and spacing — 20 seeds x 3 layouts
  x 3 spacings = 180 camera arrays.
  found: 20/20 seeds produce ONE floor across all 9 layout/spacing combinations.
  implication: `max(water_zs)` is set entirely by `generate_camera_array`'s per-camera
  height_variation draw, which is a pure function of (seed, n_cameras). Layout and spacing
  move XY only. This is what makes the sweep's all-14-fail pattern possible and satisfies
  anti-pattern 7: the claim is demonstrated across all three swept axes, not one.

- timestamp: 2026-08-03 (session)
  checked: sensitivity of the derived floor to `n_cameras` ∈ {8, 12, 16}, 23 seeds.
  found: 11/23 seeds give a DIFFERENT floor per camera count (e.g. seed 47: 1.180622 /
  1.181261 / 1.183805; seed 58: 1.176778 / 1.177042 / 1.187173).
  implication: E4, which sweeps `n_cameras`, has up to SIX independent legality draws per
  seed (3 camera counts x calibration/holdout), not two. Any fix must be per-scenario, not
  per-seed.

- timestamp: 2026-08-03 (session)
  checked: legality statistics over seeds 0–499 at E6's fixed n_cameras=12.
  found: calibration array legal in 114/500 (22.8%); holdout array legal in 117/500
  (23.4%); BOTH legal in 29/500 (5.8%). The frozen constant sits at the 22.8th percentile
  of the derived-floor distribution over 400 arrays (min 1.177042, mean 1.183974,
  max 1.193777). Fully-legal seeds below 100: 28, 42, 52, 62, 72, 75, 94.
  implication: seed 42 is not special beyond being the seed the constant was derived from
  — its calibration floor equals the constant by construction, and its holdout floor
  (1.181380) clears it by luck. ~94% of seeds cannot run E6 at all.

- timestamp: 2026-08-03 (session)
  checked: candidate-fix inertness at seed 42, comparing all 100 poses' `rvec`/`tvec`
  bit-for-bit against what shipped (`depth_range=GRID_DEPTH_RANGE`).
  found: Fix A (`depth_range=None`, i.e. derive per scenario) is inert for the CALIBRATION
  scenario but NOT for the holdout scenario — it shifts board depths by up to 0.469 mm.
  Fix B (`depth_range=(max(GRID_DEPTH_RANGE[0], derived_floor), 2.0)`) is bit-inert for
  BOTH.
  implication: the guard's own suggested remedy would silently change every published E4
  and E6 held-out accuracy number. The prior "fix inertness at seed 42 is already
  verified" note covered only the calibration scenario.

- timestamp: 2026-08-03 (session)
  checked: every other `generate_board_trajectory` / `generate_real_rig_trajectory` call
  site in `experiments/` and `src/aquacal/datasets/synthetic.py`.
  found: E3 (`e3_derived_quantities.py:331`), E5 (`e5_index_sensitivity.py:211,495`, via
  `_e5_real_rig_depth_range(water_zs)`), and all three library presets (`synthetic.py`
  `ideal`:1063, `minimal`:1105, `realistic`:1137) either pass `depth_range=None` or derive
  it from the SAME `water_zs` the scenario was built with. `generate_real_rig_array()`
  additionally takes no seed at all, so E3/E5's `water_zs` are seed-invariant.
  implication: the defect is confined to the grid family and its one frozen constant. This
  independently explains why E1 and E7 swept x10 without incident.

- timestamp: 2026-08-03 (orchestrator, post-session verification)
  checked: re-derived the legality table independently of the session agent, at E6's own
  `GRID_SPACING` and `GRID_HEIGHT_ABOVE_WATER`, for seeds 0-499.
  found: 29/500 legal, matching the session's count exactly. Named legal seeds below 100
  reproduce: 28, 42, 52, 62, 72, 75, 94. Seeds 43 (calib BAD, hold BAD), 47 and 50 (calib
  ok, hold BAD) reproduce the calibration-vs-holdout split that answers Q1.
  implication: the session's central numbers are confirmed by an independent computation,
  not taken on its return text.

- timestamp: 2026-08-03 (orchestrator, post-session)
  checked: every consumer of `generalization_sweep.csv` and of the `depth_range_min` /
  `depth_range_max` columns across `*.py`, `*.tex`, `*.ipynb`.
  found: the columns appear only in the producing module, the committed CSVs themselves,
  and planning documents. CSV consumers are `experiments/check_rerun_gates.py`,
  `determinism_probe.py`, and four unit test modules -- none of which reads either
  `depth_range_*` column. No figure or LaTeX consumer exists.
  implication: closes the report's "whether any figure/LaTeX consumer reads the
  depth_range_* columns" gap. Changing those columns' semantics is confined to the two
  experiment modules and their tests; it has no reach into the manuscript.

## Eliminated

- hypothesis: the required floor differs per seed because different configurations
  (layout/spacing/index) build different-footprint arrays.
  evidence: all 12 configurations within each of the 6 failing seeds print an identical
  floor; a 180-array probe shows 20/20 seeds give one floor across 3 layouts x 3 spacings.
  timestamp: 2026-08-03

- hypothesis: the standalone `generate_camera_array` slack prediction "does not reproduce
  E6's real scenario construction".
  evidence: it reproduces it EXACTLY — floor(43)=1.182348 → printed 1.1823, floor(45)=
  1.184952 → 1.1850, etc., matching all 6 failing seeds at 4 dp. The prediction method was
  correct; it was incomplete, modelling only the calibration array and not the holdout one.
  timestamp: 2026-08-03

- hypothesis: the fast (~1 s) and slow (74–84 min) failures have different root causes.
  evidence: both are the same guard, the same frozen constant, and the same missing
  per-scenario derivation. Only WHICH of `run_configuration`'s two `build_grid_scenario`
  calls trips first differs.
  timestamp: 2026-08-03

- hypothesis: `build_grid_scenario:589` is the only line that must change.
  evidence: `_scaled_depth_range` (e6:160) bakes the frozen floor into the scale axis's
  import-time constant table, and `run_grid_cell` (e4:744, 806) plus `run_configuration`
  (e6:759, 787) are four independent construction sites. Fixing 589 alone leaves the scale
  axis passing an explicit illegal minimum.
  timestamp: 2026-08-03

## Resolution

### root_cause

**A per-scenario geometric constraint is enforced against an import-time constant derived
from one particular scenario.**

`experiments/e4_benchmark_grid.py:258` freezes

```python
GRID_DEPTH_RANGE = (board_clearance_floor(GRID_BOARD_CONFIG, _grid_baseline_water_zs, 15.0), 2.0)
```

where `_grid_baseline_water_zs` comes from a `generate_camera_array(..., seed=42)` call at
line 251. `max(water_zs)` — the quantity the clearance floor is anchored on — is a pure
function of `(seed, n_cameras)` via `generate_camera_array`'s per-camera `height_variation`
draw. It is **independent of layout and spacing** (verified over 180 arrays) and **does
vary with `n_cameras`** (11 of 23 seeds differ across {8, 12, 16}).

Every grid-family scenario then passes that frozen value back into
`generate_board_trajectory`, whose guard (`synthetic.py:593`) re-derives the floor from the
scenario's *own* `water_zs` and raises if the supplied minimum is below it. So the check is
correct and the constant is stale for any array that is not the seed-42 12-camera one.

**Q1 — why 43–46 fail in ~1 s but 47 and 50 burn 74–84 min:**
`run_configuration` builds **two** grid scenarios: the calibration scene at `seed`
(e6:759) and the held-out scene at `seed + 1_000_000` (e6:787). These are two independent
camera-array draws with two independent `max(water_zs)`, each checked against the same
frozen constant. Both are inside one `try` with a blanket `except Exception`.

- Seeds 43, 44, 45, 46: `floor(seed) > frozen` → the **calibration** call raises before
  `calibrate_synthetic` is ever reached. 12 scenes x ~0.1 s ≈ 1 s total, zero `Stage 2:`
  lines in the log.
- Seeds 47, 50: `floor(seed) <= frozen` (1.181261 and 1.180099) → the calibration scene is
  built and **Stage 2 + Stage 3 run to convergence**. Then the **holdout** call raises
  because `floor(seed+1_000_000) > frozen` (1.182966 and 1.183873). The completed
  calibration is discarded by the `except`, the row is recorded `status="failed"`, and the
  full solve cost — 12 scenes x ~6 min — is paid for nothing.

The printed floor identifies the site unambiguously and matches at 4 dp for all 6 failing
seeds x 12 configurations (72/72). See the Evidence table.

**Q2 — why the predicted-legal seeds were not legal:**
The prediction was not wrong about the method — a standalone `generate_camera_array` call
reproduces E6's array *exactly* (it is literally the same call `build_grid_scenario` makes).
It was **incomplete**: it evaluated only the calibration array. Seeds 47 and 50 are
genuinely legal for calibration and illegal for holdout. Legality requires **both** draws
to clear the constant, and over seeds 0–499 that is true for only **29/500 (5.8%)** —
22.8% for the calibration array and 23.4% for the holdout array, near-independently. The
frozen constant sits at the **22.8th percentile** of the derived-floor distribution.

Seed 42 is not robust, it is the anchor: its calibration floor equals the constant *by
construction* (zero margin), and its holdout floor (1.181380) clears it by ~0.5 mm of luck.

**Why E1/E7 swept x10 cleanly and E6 could not:** every other trajectory call site in the
codebase (E3:331, E5:211 and 495 via `_e5_real_rig_depth_range(water_zs)`, and the
`ideal`/`minimal`/`realistic` presets at synthetic.py:1063/1105/1137) derives its depth
range from the same `water_zs` its own scenario was built with. E5 and E3 additionally use
`generate_real_rig_array()`, which takes no seed. The defect is confined to the grid family.

### fix

The rule: **a scenario's depth range must be derived from that scenario's own `water_zs`,
at the point the scenario is constructed** — never from a module-level constant. E5's
`_e5_real_rig_depth_range` is the pattern to copy.

Constraint that dictates the shape: the naive fix (`depth_range=None` everywhere) is
**not inert at seed 42**. It is bit-identical for the calibration scene, but for the
holdout scene (seed 1000042) the derived floor is 1.181380 vs the frozen 1.181852, which
shifts sampled board depths by up to **0.469 mm** across the 100 frames — silently moving
every published E4 and E6 held-out accuracy number. Measured, not predicted.

The fix that IS bit-inert at seed 42 for both scenes:

```python
effective_floor = max(GRID_DEPTH_RANGE[0], board_clearance_floor(GRID_BOARD_CONFIG, water_zs, 15.0))
```

Legal by construction at every seed (it is never below the derived floor), and equal to the
frozen constant wherever the derived floor is lower — which covers all six seed-42 grid
arrays (12-cam calib, 12-cam holdout, and the 8/16-cam variants E4 uses; all six derived
floors are ≤ the constant). Verified bit-identical on all 100 poses' `rvec` and `tvec`.

**Every call site that must change:**

| # | Site | What is wrong | Required change |
|---|---|---|---|
| 1 | `e4_benchmark_grid.py:589` (`build_grid_scenario`) | `resolved_depth_range = GRID_DEPTH_RANGE if depth_range is None else depth_range` — substitutes the frozen constant for the derived default, defeating the guard's own suggested remedy | Compute `effective_floor` from the `water_zs` built at line 580, and use `(effective_floor, GRID_DEPTH_RANGE[1])` |
| 2 | `e4_benchmark_grid.py:258` (`GRID_DEPTH_RANGE`) | Import-time constant derived from a seed-42 array; also drags the `generate_camera_array` call at 251 into module import | Keep only as the *published-geometry anchor* / lower bound for `max()`. Do not delete — deleting it breaks seed-42 inertness. Rename and re-document so no new consumer reads it as "the floor" |
| 3 | `e6_generalization_sweep.py:160` (`_scaled_depth_range`) | Builds `SCALE_AXIS_VALUES`' absolute `(floor, floor + factor*extent)` tuples at import from the frozen floor, then passes them as an EXPLICIT `depth_range` — so fixing site 1's `None` branch alone leaves the scale axis still illegal | Replace the absolute tuple with a **relative factor** threaded to `build_grid_scenario` (e.g. a new `depth_extent_factor` kwarg, default 1.0), resolved against the per-scenario `effective_floor`. At seed 42 this reproduces the current tuples exactly |
| 4 | `e6_generalization_sweep.py:759` | Calibration scenario | No change if 1+3 land, but its `config["depth_range"]` payload becomes a factor |
| 5 | `e6_generalization_sweep.py:787` | Holdout scenario at `seed + 1_000_000` — the site that cost 74–84 min at seeds 47/50 | Same |
| 6 | `e4_benchmark_grid.py:744` and `:806` (`run_grid_cell`) | Identical two-call calibration/holdout structure, and E4 additionally sweeps `n_cameras` ∈ {8,12,16}, which DOES move the floor — up to **six** independent legality draws per seed | Inherits the fix via site 1; must be re-verified per camera count, not assumed |

**Consequential changes the fix plan must budget for (not optional polish):**

- `e6:_SCENARIO_IDENTITY_KEYS` contains `"depth_range"`. If the payload becomes a factor,
  the checkpoint identity changes shape and **every committed `e6_configs/*.json` will
  mismatch under `--check` (WR-03)** unless the key set and the recorded identity are
  migrated together.
- `E6_COLUMNS`' `depth_range_min` / `depth_range_max` currently read the config payload
  directly and are null on baseline rows. They must be populated from the *resolved*
  per-scenario range, or the CSV loses the ability to say what depth range was actually
  used — which is precisely the information whose absence caused this bug.
- `tests/unit/test_experiments_e4.py:425–469` asserts `GRID_DEPTH_RANGE[0] ==
  board_clearance_floor(...)` at seed 42, and `test_experiments_e6.py:178–192` asserts
  `_scaled_depth_range(1.0) == GRID_DEPTH_RANGE`. Both encode the current design and will
  need rewriting as part of the fix, not after it.
- Do **not** treat E4's committed nine-cell grid as automatically safe at other seeds. It
  is safe at seed 42 (all six draws clear), but has the same ~6% legality if re-seeded.

**Do NOT** adjust `board_clearance_floor`'s `margin_factor` — its own docstring forbids
moving it in response to a failing run, and the failing thing here is not the margin.

### verification

Cheap, run first (seconds to minutes, no calibration):

1. Bit-inertness at seed 42: assert all 100 `rvec`/`tvec` from `build_grid_scenario(12,
   100, 42)` and `build_grid_scenario(12, 100, 1_000_042)` are unchanged, and the same for
   E4's `{8,12,16} x {50,100,200}` cells and both E6 scale values. 30 scenarios, ~10 s.
   This is the gate that protects the published numbers.
2. Legality by construction: for 500 seeds x {8,12,16} cameras x {grid,ring,line} x 3
   spacings, assert `build_grid_scenario` never raises. ~1–2 min. Should go **into the test
   suite** — its absence is why this shipped.
3. Full unit suite (`pytest tests/`), with the four test rewrites above. ~existing cost.

Real runs, foreground, `python -u`, `nohup`+`disown` (the harness kills backgrounded jobs
at ~35–50 min — see `.planning/knowledge-base.md`):

4. `python -u -m experiments.e6_generalization_sweep --smoke` — **~5–10 min**.
5. E6 at seed 42 with `--force`, byte-compared against the committed
   `generalization_sweep.csv`. **~95–100 min** (measured: 96.6 min). This is the real
   inertness proof; step 1 only proves the scenes match, not the solves.
6. E6 at **two or three** previously-failing seeds — 43 (fast-path failure) and 47
   (slow-path failure) at minimum, ideally 45 (whose holdout was already legal, so it
   isolates the calibration-side fix). **~75–100 min each → 2.5–5 h.**
7. E4 nine-cell grid at one non-42 seed, to exercise the `n_cameras` axis the E6 sweep
   cannot reach. Optimization-only time for the committed grid is 1.55 h; budget
   **~2–2.5 h** wall clock.

**Total: roughly 6–9 h of unattended wall clock**, of which ~10 minutes is the cheap gate
that catches a wrong fix. Steps 1–4 should all pass before any of 5–7 is launched.

### what could NOT be established

- **Whether a fixed sweep produces *good* results at non-42 seeds.** Everything here shows
  the sweep becomes *legal*. Legality is not convergence. Seeds 43–50 have never completed
  a single E6 configuration, so there is zero evidence about their reprojection RMS,
  reconstruction error, or `degenerate_observations_at_solution` counts. A fix could make
  all 14 rows run and some of them diverge. Budget for that outcome.

  **→ ANSWERED 2026-08-03: yes, E6 converges off seed 42 — with two seed-fragile spots.**
  Seeds **62** (85 min) and **28** (83 min) both returned `{'ok': 14}` with
  `degenerate_observations_at_solution == 0` on all 14 configurations. No source change was
  needed; both are naturally legal.

  **Accuracy is highly reproducible.** `reconstruction_rmse_mm` agrees across all three
  seeds to within ~5% on every configuration (e.g. baseline 0.4869 / 0.4689 / 0.4762;
  half_scale 0.3596 / 0.3380 / 0.3435). `reprojection_rms_px` agrees to 3 decimals. The fix
  phase does **not** need to budget for accuracy work.

  **Fragile spot 1 — `scale/double_scale` optimality (diagnostic only).**
  `optimality_stage3_intrinsic_pass`: seed 42 = 0.00166, seed 62 = **1.139**, seed 28 =
  **0.2241** (686x and 135x). `optimality_stage3_interface_optimization`: 0.00853 / **2.511**
  / 0.00174. **Both** non-42 seeds are elevated on the intrinsic pass (2/2). This is the
  exact configuration whose outlier collapse (5e+01 → 1e-02) was credited to the 19.3 fix.
  It did **not** degrade accuracy — seed 62's double_scale `reconstruction_rmse_mm` is
  0.6619 against seed 42's 0.7244, slightly *better*. So the collapse claim is seed-fragile
  as a *convergence-diagnostic* statement, not an accuracy one.

  **Fragile spot 2 — `layout/line` parameter recovery.** `xy_position_error_mm_mean`:
  2.231 / 1.565 / **6.152** mm. `water_z_error_mm_mean`: 3.452 / 8.251 / **11.76** mm. Both
  ~4x spread, both far above every other configuration, while that row's
  `reconstruction_rmse_mm` (0.4886 / 0.4660 / 0.4463) and `reprojection_rms_px` stay normal.
  That divergence — bad parameter recovery, clean reconstruction — is this project's
  documented weak-observability signature. It was invisible while E6 was single-seed.

  **n = 3 (one published + two independent).** Enough to establish that both spots are real
  rather than one unlucky seed, and enough to bound the accuracy risk. **Not** enough to
  quote a band from. Raw output in `seed_sweep_19_3/e6/seed_{62,28}/`; harness and timings
  in `experiments/e6_legal_seed_probe.sh` and `e6_legal_seed_probe_state.tsv`.

  **Superseded plan (retained for the record):** 29 of seeds 0–499 are *naturally* legal —
  both draws already clear the frozen constant — so E6 can be run at a non-42 seed today.
  `experiments/e6_legal_seed_probe.sh` is running seeds **62** and **28** sequentially
  (~96 min each, launched 2026-08-03 07:35, PID 26066, `nohup`+`disown`). Two seeds rather
  than one because anti-pattern 7 is blocking: n=1 cannot separate "E6 converges off 42"
  from a coincidence. Seed 62 reached `Stage 2:` within 25 s, which already confirms the
  legality result holds in E6's real construction path and not merely in the standalone
  probe. Results land in `seed_sweep_19_3/e6/seed_{62,28}/` and
  `experiments/e6_legal_seed_probe_state.tsv`. **Read the `status` counts, not the exit
  code.** If both seeds return `{'ok': 14}` with zero guard counts, the fix phase can treat
  divergence as unlikely; if either shows failures or degenerate observations, the fix phase
  must budget for convergence work on top of the legality fix.
  n=2 is still small — it bounds the risk, it does not establish a band.
- **Whether the ~0.5 mm holdout depth shift under the naive fix would materially move the
  published accuracy numbers.** Measured that it moves the *poses*; did not run a
  calibration to see whether the reported millimetre-scale errors change. This is only
  relevant if the fix plan rejects the `max()` form.
- **The exact `n_cameras` dependence structure.** Established that the floor differs across
  {8,12,16} for 11 of 23 seeds, which is enough to require per-scenario derivation. Did not
  characterise it further (e.g. whether it is monotone), because the fix does not need it.
- **Whether any figure/LaTeX consumer downstream of `generalization_sweep.csv` reads
  `depth_range_min`/`depth_range_max`.** Not traced. If one does, changing those columns'
  semantics has reach beyond the two experiment modules.
- **Nothing was run for seed 48, 49, or any seed outside the sweep set at the full-pipeline
  level.** Their floors are computed above from camera-array construction only.

### files_changed

None. Diagnose-only, per the session Scope. Probe scripts were written to the scratchpad
and are not part of the repository.
