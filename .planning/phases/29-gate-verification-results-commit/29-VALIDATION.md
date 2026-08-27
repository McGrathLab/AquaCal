---
phase: 29
slug: gate-verification-results-commit
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-26
---

# Phase 29 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Seeded from `29-RESEARCH.md` § Validation Architecture, whose numbers were **measured**
> this session in a disposable probe clone, not inferred.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (markers only: `slow`) |
| **Quick run command** | `python -m pytest tests/unit/test_experiments_provenance.py -q` |
| **Full suite command** | `python -m pytest tests/` |
| **Estimated runtime** | ~23 s quick · ~28 min full |
| **Interpreter** | `~/anaconda3/envs/aquacal-freeze02-cleanenv/bin/python` (working clone) |

---

## Sampling Rate

- **After every task commit:** `python -m pytest tests/unit/test_experiments_provenance.py -q` — the only module this phase's changes can move.
- **After every plan wave:** `python -m pytest tests/unit/test_baseline_paths.py tests/unit/test_expectations.py tests/unit/test_experiments_e3.py tests/unit/test_experiments_e5.py tests/unit/test_experiments_io.py tests/unit/test_experiments_provenance.py -q` (~54 s combined).
- **Before `/gsd-verify-work`:** full `pytest tests/` once, expecting **exactly 3 failures** (D4 anchors, ruled in the `rerun-freeze-02` tag annotation — D-29-15). Zero or four are both anomalies. Plus a final gate re-run over the committed tree at `176 PASS, 7 N/A, 0 FAIL`.
- **Max feedback latency:** 60 seconds.

---

## Per-Task Verification Map

*Populated by `/gsd-validate-phase` once PLAN.md task IDs exist. Requirement-level map below is the seed.*

| Requirement | Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|----------|-----------|-------------------|-------------|--------|
| RUN-03 | Gate passes over the complete returned tree | integration (script) | `python experiments/check_rerun_gates.py experiments/results --profile full` → `TOTAL: 176 PASS, 7 N/A, 0 FAIL`, zero `^\[FAIL` | ✅ verified reproducing | ⬜ pending |
| RUN-03 | `gate3_git_sha_consistency` holds on the committed tree | integration (script) | same command; grep `gate3_git_sha_consistency.*PASS` | ✅ | ⬜ pending |
| RUN-03 | Provenance rails green after D-29-13 repairs | unit | `python -m pytest tests/unit/test_experiments_provenance.py -q` → `0 failed` (baseline: 8 failed) | ✅ module exists, assertions need repair | ⬜ pending |
| RUN-03 | No new failures from repopulation | unit | the five tree-keyed modules → `245 passed` | ✅ verified | ⬜ pending |
| RUN-03 | Full suite at the ruled count | unit (slow) | `python -m pytest tests/` → `3 failed` after repairs (`11 failed` before) | ✅ | ⬜ pending |
| ROADMAP c2 | E2 same-seed control, seed 42 vs seed 42 | analysis + evidence | `29-e2-control.txt`; max relative drift `< 1e-6`, **seed printed in the output** | ❌ **Wave 0** | ⬜ pending |
| ROADMAP c3 | E7 before/after sign test, both pairings | analysis + evidence | `29-e7-before-after.txt` against `pre_rerun_baseline/` and the committed tree | ❌ **Wave 0** | ⬜ pending |
| RUN-04 | Admitted commit set is exactly 227 files | integration (git) | `git show --name-only --format="" <sha> \| wc -l` → `227`; `\| grep -c '^experiments/results/'` → `147` | ❌ **Wave 0** (plan verification step) | ⬜ pending |
| RUN-04 | Artifacts unmodified by the commit | integration (hash) | `md5sum experiments/results/real_rig_metrics.json` → `57279708f6106f411d1fe03ed2698291` | ✅ baselines recorded in RESEARCH.md | ⬜ pending |
| RUN-05 | Upload round-trips | integration (API) | response `checksum` equals `md5:` + locally computed md5, per record | ❌ **Wave 0** (tooling does not exist) | ⬜ pending |
| RUN-05 | Both drafts render correctly | manual | author opens both drafts in the Zenodo UI | manual-only **by decision** (D-29-01/D-29-06) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] E2 same-seed control script + `29-e2-control.txt` evidence file — ROADMAP c2 / D-29-10 stop-list item 1. **Must print the seed** so the comparison cannot be misread later.
- [ ] E7 before/after script + `29-e7-before-after.txt` evidence file — ROADMAP c3 / D-29-16. Must report **both** pairings across **both** trees (`analyze_e7_spread.py` has a Windows-only hard-coded `ROOT` and is not runnable as-is).
- [ ] Zenodo tooling with a draft/upload/verify surface — RUN-05. Suggested home `scripts/`, which is **not packaged** (`[tool.setuptools.packages.find] where = ["src"]`, `pyproject.toml:80-82`), so nothing there ships to PyPI or touches the frozen `experiments/` tree.
- [ ] No new framework install needed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Zenodo Publish (DOI minting) | RUN-05 | **Deliberately manual.** `PROJECT.md`'s locked decision keeps the irreversible act a human one; D-29-01 preserves it by automating only up to an unpublished draft. Research recommends minting the token with `deposit:write` only (omitting `deposit:actions`) so this is enforced by the credential, not by code review. | Author opens both drafts in the Zenodo web UI, checks metadata and file lists, presses Publish on each. |
| Paper submission ordering | RUN-05 | Phase 29 cannot observe the submission event. Criterion 6 is closable only on the author's confirmation. | Author confirms the results package was published before submitting. |
| E7 conclusion move → author | ROADMAP c3 | §3 edits stay the author's (D-29-16). | Report both numbers; flag explicitly if the conclusion moved. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
