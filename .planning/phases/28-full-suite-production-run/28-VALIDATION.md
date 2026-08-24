---
phase: 28
slug: full-suite-production-run
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-24
---

# Phase 28 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

**Scope caveat, and it governs everything below.** This phase writes no code. It executes a
frozen tag off-repo and returns artifacts. There is therefore nothing for a unit test to cover,
and **no test file may be added** — the tag is frozen and must not be modified. The "tests" here
are *assertions about a run*: pre-launch refusals, in-tree gates, and post-run roll-ups that all
already ship inside `rerun-freeze-02`.

Derived from `28-RESEARCH.md` § *Validation Architecture*.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (via the `dev` extra); `[tool.pytest.ini_options]` in `pyproject.toml` |
| **Config file** | `pyproject.toml` (inside the clone, frozen) |
| **Quick run command** | `pytest tests/unit/test_run_experiment_suite_dryrun.py -q` (67 tests — the driver's own wiring harness) |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | quick ~seconds; full ~28 min on the run machine |

**D4 caveat — carry this into every reading of the full suite.** The tag was deliberately cut
with a known, ruled-on 3-test failure. `pytest tests/ -q` is *expected* to report
`2407 passed, 26 skipped, 3 failed`. Three failures is the pass condition; zero failures or four
failures both mean something is wrong. Node ids must match the three registered in
`.planning/phases/29.1-post-run-fixes-re-freeze/29.1-PREPUSH-AUDIT.md` §1.

---

## Sampling Rate

This phase has no task-commit cadence to sample — it is one long unattended run.

- **Pre-launch:** the 10-item assertion checklist in `28-RESEARCH.md` § *Architecture Patterns*,
  ordered so the cheapest check fails first. Minutes.
- **Pre-launch, recommended:** the driver's own dry run —
  `RUN_EXPERIMENT_SUITE_DRY_RUN=1 bash experiments/run_experiment_suite.sh` — exits 0, walks all
  20 stages in ~1 s, and writes only to the `.dryrun.tsv` path, so it cannot poison the real
  state file. Cheap insurance before an overnight commitment.
- **Pre-launch:** `pytest tests/ -q` for the D4 confirmation. **Before launch or after the run,
  never during** — it competes for the same cores the suite needs.
- **During the run:** `tail` the log and confirm the stage index advances. Nothing else to sample.
- **At completion:** the three hard signals (below).
- **Max feedback latency:** effectively the run length (~6 h measured, see below). This is
  inherent to the phase, not a gap.

---

## Per-Task Verification Map

Task IDs are assigned when PLAN.md files are written; the rows below are the requirement-level
contract every plan must land against.

| Req / criterion | Behavior | Test Type | Automated Command | File Exists |
|---|---|---|---|---|
| RUN-02 / SC-1 | Every expected artifact produced (62 files, all `full`) | roll-up | `awk '/END-OF-RUN COMPLETENESS ROLL-UP/,0' <log> \| grep -E '^\[FAIL\]\|TOTAL:'` | ✅ in-tree |
| RUN-02 / SC-1 | Re-verifiable after the run | gate | `python experiments/check_rerun_gates.py experiments/results --profile full` | ✅ in-tree |
| RUN-02 / SC-2 | One sha across all artifacts | gate | `gate3_git_sha_consistency` line in the roll-up | ✅ in-tree |
| RUN-02 / SC-2 | Manifest fields all non-null | gate | `gate3_run_manifest_fields` line | ✅ in-tree |
| RUN-02 / SC-3 | 20 stages, all at exit 0 | state file | `awk -F'\t' '$3=="complete" && $5!=0' …tsv` and `… \| wc -l` = 20 | ✅ in-tree |
| Env correctness | Library imported from the fresh clone, not an editable elsewhere | assertion | `python -c "import aquacal, sys; print(aquacal.__file__); print(sys.executable)"` | ✅ in-tree |
| Env correctness | OpenCV pin holds | assertion | `python -c "import cv2; print(cv2.__version__)"` | ✅ in-tree |
| D4 caveat | 3 known failures still exactly 3, same node ids | pytest | `pytest tests/ -q` | ✅ in-tree |
| Clean launch | Tree clean at launch | gate | `gate3_run_manifest_clean_tree` line | ✅ in-tree |

---

## Wave 0 Requirements

**None.** Every check above already exists inside the frozen tag. This phase adds no test file,
and must not.

---

## Manual-Only Verifications

This phase is human-operated off-repo, so several checks are necessarily manual.

| Behavior | Requirement | Why Manual | Test Instructions |
|---|---|---|---|
| Fresh clone at the right tag | D5 | Operator action before any automation exists | `git clone --branch rerun-freeze-02 …` into a path **not** already used by the rehearsal; confirm `git rev-parse HEAD` = `7005a277…` |
| No stale driver state file | D5 | Absence cannot be asserted by a gate that never runs | Confirm no `run_experiment_suite_state.<sha>.tsv` exists in the fresh clone before launch |
| Env built from the tag's own install command | §1.2 provenance | Command must be read out of the clone, not retyped | Build a **new** env; never reuse the machine's existing four |
| Artifacts returned with provenance intact | RUN-02 | Physical transfer off the run machine | Preserve the nine-path list in `28-RESEARCH.md` § *Pitfall 6* — **not** attempt 1's documented `tar` line, which is wrong |

---

## Acceptance: the three hard signals

1. Completeness roll-up reports every expected artifact present at `full`, zero `[FAIL]`.
2. `gate3_git_sha_consistency` and `gate3_run_manifest_fields` pass — one sha, no null fields.
3. The state file shows 20 stages `complete` at exit 0.

**Do not read `$?` as the verdict.** A healthy run exits NON-ZERO — see `28-RESEARCH.md`
§ *Pitfall 1*. Reading the shell exit code as pass/fail is the single most likely way to
misjudge a good run as a failure.

---

## Validation Sign-Off

- [ ] Pre-launch assertion checklist executed and recorded
- [ ] Dry run walked all 20 stages at exit 0
- [ ] `pytest tests/ -q` reported exactly 3 failures, node ids matching the D4 register
- [ ] Three hard signals all green at completion
- [ ] Preserve list captured from the driver's own `OUT_DIR*`/`STATE_FILE` variables
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
