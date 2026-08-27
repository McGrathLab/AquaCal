---
phase: 25
slug: degeneracy-classification-claim-licensing
status: approved
nyquist_compliant: true
wave_0_complete: false
created: 2026-08-18
---

# Phase 25 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `25-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (via the AquaCal conda env — Git Bash `python` is Anaconda base and will produce collection errors) |
| **Config file** | `pyproject.toml` (markers: `slow`) |
| **Quick run command** | `python -m pytest tests/unit/<the touched file> -q` |
| **Full suite command** | `python -m pytest tests/` — **orchestrator only**, 56–88 min measured |
| **Estimated runtime** | quick: seconds · full: 56–88 min |

**`-m "not slow"` is ~26 min and does NOT fit under the 600 s tool ceiling.** Never give it, or the
full suite, to an executor. See CLAUDE.md § "Never let a subagent background a long run and return".

---

## Sampling Rate

- **After every task commit:** the one targeted `python -m pytest tests/unit/<file>.py -q` for the
  files that task touched.
- **After every plan wave:** the union of the wave's targeted files — run by the **orchestrator**.
- **Before `/gsd:verify-work`:** full `python -m pytest tests/` green — **orchestrator, detached**.
- **Max feedback latency:** ~60 s per task commit.

---

## Per-Task Verification Map

Task IDs are assigned by the planner. Every task below must be bound to a task ID in the PLAN.md
files; the requirement → automated-command mapping is fixed here.

| Requirement | Behavior | Test Type | Automated Command | File Exists |
|-------------|----------|-----------|-------------------|-------------|
| DEGEN-04 | Detail sink appends exactly one row per flagged observation, keyed `(camera, frame_idx, corner_id)` | unit | `pytest tests/unit/test_optim_common.py -k detail_sink -x` | ❌ W0 |
| DEGEN-04 | Zero-cost discipline: with `degeneracy_details_out=None`, residuals are bit-identical and nothing is allocated | unit | `pytest tests/unit/test_optim_common.py -k inert -x` | ❌ W0 |
| DEGEN-04 | Non-contiguous flagged indices map `unextendable[k]` ↔ `nan_reason[i]` correctly (**highest-value test in the phase**) | unit | `pytest tests/unit/test_optim_common.py -k index_spaces -x` | ❌ W0 |
| DEGEN-04 | Recomputed `h_q`/`h_c`/`r_q` equal the projector's, bit-for-bit | unit | `pytest tests/unit/test_optim_common.py -k recomputed_geometry -x` | ❌ W0 |
| DEGEN-04 | `stage` present and legal on every emitted row (D-07) | unit | `pytest tests/unit/test_discard_accounting.py -k stage_stamped -x` | ❌ W0 |
| DEGEN-04 | Row cap truncates rows but the aggregate count stays exact; `truncated` stamp present (D-10) | unit | `pytest tests/unit/test_discard_accounting.py -k row_cap -x` | ❌ W0 |
| DEGEN-04 | Classifier buckets each `nan_reason` code correctly; (b) separated from (a) **by code, not by `h_q`** | unit | `pytest tests/unit/test_discard_accounting.py -k classify -x` | ❌ W0 |
| DEGEN-04 | Sidecar not written when zero flagged rows (D-08); written when ≥1 | unit | `pytest tests/unit/test_diagnostics.py -k degenerate_sidecar -x` | ❌ W0 |
| DEGEN-04 | Config flag defaults **off** and round-trips through `load_config` (D-09) | unit | `pytest tests/unit/test_pipeline.py -k "load_config or internals" -x` | ❌ W0 |
| DEGEN-04 | The 198 classify to named buckets; bucket (a) dominates | **artifact inspection** | the E2 probe run + `FINDINGS.md` | orchestrator |
| BAND-01 | `exp1_band.csv` has 640 rows, a `noise_std` column, 4 distinct values | unit (monkeypatched `_run_one_model`) | `pytest tests/unit/test_e1_band_mode.py -k noise_axis_shape -x` | ❌ W0 |
| BAND-01 | **No duplicate keys** in either band CSV under the new key lists (PITFALL B1) | unit | `pytest tests/unit/test_e1_band_mode.py -k no_duplicate_keys -x` | ❌ W0 |
| BAND-01 | `_run_smoke` / `_run_check` / single-seed paths write no `noise_std` and are unchanged (D-12) | unit | `pytest tests/unit/test_e1_band_mode.py tests/unit/test_experiments_e1.py -k "smoke or check" -x` | partial ✓ |
| BAND-01 | The three fixed-contract CSVs' headers are byte-unchanged | unit | `pytest tests/unit/test_experiments_e1.py -k columns -x` | ❌ W0 |
| BAND-01 | The D-14 stated-domain sentence is present beside the demotion note | unit (source-text assertion, FIX-06 precedent) | `pytest tests/unit/test_experiment_inertness.py -k stated_domain -x` | ❌ W0 |
| BAND-01 | The probe's shape and directional read at 4 noise levels (128/192 rows, no duplicate keys) | **artifact inspection** | the ≈1.5 h two-seed probe under `.planning/probes/2026-08-18-e1-noise-axis/` (D-21) | orchestrator |
| DEGEN-05 | D-18's four correction headers exist | **verification command** | `grep -c "CORRECTED 2026-08-17" <4 files>` | ✓ at `02fe224` |
| DEGEN-05 | The `optimality` caveat ships in `benchmark_grid.tex` | unit (source/output-text assertion, FIX-04 precedent) | `pytest tests/unit/test_experiments_e4.py -k optimality_caveat -x` | ❌ W0 |
| DEGEN-05 | Verdict sentence (Huber knee closed, sign + magnitude, probe cited) | **recorded decision — no test** | SUMMARY + MF-21 | — |
| D-04 | Gate-scope rationale present at all three sites | unit (source-text assertion) | `pytest tests/unit/test_experiment_inertness.py -k gate_rationale -x` | ❌ W0 |
| D-05 | Synthetic gate predicate is still exactly `count > 0` | unit | `pytest tests/unit/test_experiments_e4.py tests/unit/test_experiments_e6.py -k degenerate_gate -x` | likely ✓ |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_optim_common.py` — 4 new tests for the detail sink (DEGEN-04)
- [ ] `tests/unit/test_discard_accounting.py` — 3 new tests: stage stamping, row cap, classifier (DEGEN-04)
- [ ] `tests/unit/test_diagnostics.py` — 2 new tests for the D-08 sidecar
- [ ] `tests/unit/test_e1_band_mode.py` — 3 new tests, all with `_run_one_model` monkeypatched so no real solve runs (BAND-01)
- [ ] `tests/unit/test_experiments_e4.py` — 1 new test for the D-17 caveat
- [ ] `tests/unit/test_experiment_inertness.py` — 2 new source-text assertions (D-14, D-04)
- [ ] `tests/unit/test_experiments_e1.py` — 1 new test asserting `EXP1/EXP2/EXP3_COLUMNS` are unchanged
      (**correction, 2026-08-18:** no such assertion exists today — this row was wrongly marked
      "likely ✓"; the only column assertions are `>=` subset checks on the *band* CSVs in
      `test_e1_band_mode.py:143,151,167`)
- [ ] `tests/unit/test_pipeline.py` — 1 new test for the D-09 flag, alongside
      `test_load_config_with_internals_and_seed` (`:300-316`) and the defaults block (`:160-171`)
      (**correction, 2026-08-18:** `tests/unit/test_internals.py` covers `io/internals.py`, not
      config — it is the wrong home for this test)
- [ ] No framework install needed — pytest and the env are present.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| The 198 unprojectable observations classify to named buckets | DEGEN-04 | One-off instrumented E2 run against the archive's `config_paper.yaml` under OpenCV 4.13 (48–87 min, ~10.26 GiB) | Orchestrator runs detached with `python -u`; read the sidecar, record in `FINDINGS.md` |
| E1 noise-axis probe at 4 noise levels, 2 seeds | BAND-01 | ≈1.5 h run, and it must not be dispatched to an executor | Orchestrator runs detached with `nohup python -u … & disown`, `--out` at the probe dir; `experiments/results/` must stay byte-unchanged. **The band of record is Phase 28's frozen run (D-21)** — 640/960 is not asserted here |
| DEGEN-05 verdict sentence | DEGEN-05 | Recorded decision (D-19: no measurement, no artifact, no verification criterion) | Written into SUMMARY + MF-21 |
| Gate-scope decision | D-04 | Policy call conditioned on the run's dominant bucket | Only checkable artifact is that the rationale text exists at the three named sites |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references — the Wave 0 tests are created inline within each
      wave-1 task rather than by a separate Wave 0 plan
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-08-18 (gsd-plan-checker: VERIFICATION PASSED, no blockers)
