---
phase: 19
slug: benchmark-instrumentation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-24
---

# Phase 19 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing; `tests/unit/` + `tests/synthetic/`) |
| **Config file** | `pyproject.toml` (pytest config + `slow` marker) |
| **Quick run command** | `python -m pytest tests/unit/ -q` |
| **Full suite command** | `python -m pytest tests/ -m "not slow" -q` |
| **Estimated runtime** | ~65 seconds full (775 passed / 31 deselected as of Phase 18) |

Supplementary gates this phase also needs, because it touches docstrings on autodoc'd
modules and adds an optional dependency:

| Gate | Command | Why this phase needs it |
|------|---------|-------------------------|
| Docs build | `python -m sphinx -W --keep-going -b html docs docs/_build/html` | Phase 18 proved a docstring edit can break `-W` only after merge; BENCH-01 edits docstrings on autodoc'd modules |
| Lint | `ruff check` | Project standard |
| Optional-extra resolution | `python -c "import psutil"` + confirm `[bench]` extra declared in `pyproject.toml` | D-01 adds psutil as an optional extra; it is currently installed but undeclared, so a passing import proves nothing about the extra |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/unit/ -q`
- **After every plan wave:** Run `python -m pytest tests/ -m "not slow" -q` **and** the docs
  build, not just the tests
- **Before `/gsd:verify-work`:** Full suite green, docs build exits 0, `ruff check` clean
- **Max feedback latency:** ~65 seconds

---

## Per-Task Verification Map

Populated by the planner. Every BENCH requirement must appear.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | BENCH-01 | — | N/A (local instrumentation, no attack surface) | unit | asserts `nfev`/`njev`/`cost`/`optimality` are captured (not `None`) from each of the four in-scope sites | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | BENCH-02 | — | N/A | unit | memory block absent when flag off; present with a recognized `memory.mode` when on | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | BENCH-03 | — | N/A | unit | recorded P and group count equal the live `build_structural_column_groups` values, not restated constants | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | BENCH-04 | — | N/A | unit | `benchmark.json` validates against the schema, round-trips through `json.load`, and contains `schema_version` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | BENCH-05 | — | N/A | unit | aggregator emits CSV + LaTeX from ≥2 fixture `benchmark.json` files and **refuses** an unknown `schema_version` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | BENCH-06 | — | N/A | regression | bit-exact: `result.x` identical with explicit vs default tolerances (exact equality, not `allclose`) | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_benchmark_record.py` — schema shape, `schema_version` presence,
      NumPy-scalar JSON serialization, `null`-not-omitted for absent metrics (D-15)
- [ ] `tests/unit/test_solver_diagnostics.py` — terminal-diagnostic capture at the four
      in-scope `least_squares` sites (D-07)
- [ ] `tests/unit/test_explicit_tolerances.py` — the BENCH-06 bit-exactness regression
- [ ] `benchmarks/` fixtures — at least two `benchmark.json` samples plus one with an
      unrecognized `schema_version`, so the aggregator's refusal path is actually exercised
- [ ] No framework install needed — pytest is already configured

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Peak-RSS number is *plausible* on a real run | BENCH-02 | A unit test can prove the field is populated and labelled, but not that the value is physically correct. The known peak is ~3.6 GB on the 13-camera rig; a reading of a few MB would mean the measurement is silently capturing the wrong thing (the exact `tracemalloc` failure mode D-01 exists to avoid). | Run one real 13-camera calibration with the memory flag on. Confirm the reported peak is of order GB, not MB, and that `memory.mode` reads `psutil_peak_wset` on Windows. |
| A real-rig `benchmark.json` is complete | BENCH-04 | Synthetic fixtures cannot prove the real pipeline populates every stage block; BENCH-04 explicitly says "for real-rig runs as well as synthetic". | After a real run, open `output_dir/benchmark.json` and confirm no stage block is unexpectedly `null` and the environment block has a real CPU/RAM. |
| The LaTeX fragment renders | BENCH-05 | Valid-looking LaTeX can still fail to compile inside the manuscript's table environment. | Paste the emitted fragment into the supplement and compile. |

> **Cross-phase note (not a Phase 19 gate).** BENCH-05's actual cameras × frames sweep is a
> multi-hour job — a single 13-camera run takes 48–87 min per `CLAUDE.md`. Phase 19 delivers
> and tests the runner; **executing** the sweep is downstream work and must not be treated as
> a completion criterion for this phase.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 65s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
