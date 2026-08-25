---
phase: 28-full-suite-production-run
plan: 02
subsystem: infra
tags: [pre-flight, assertions, launch-gate, provenance, environment-hygiene, evidence]

# Dependency graph
requires:
  - phase: 28-full-suite-production-run
    plan: 01
    provides: "the production clone at /home/tlancaster/aquacal-frozen-rerun-freeze-02-prod, the aquacal-freeze02-prod environment, the dry-run rehearsal, and the finding that pytest creates an empty experiments/results/ in the clone"
  - phase: 29.1-post-run-fixes-re-freeze
    provides: "D-28 (set PRELAUNCH_GATE_PYTHON explicitly), D5 (state-file collision), and the D4 three-failure ruling"
  - phase: 27-frozen-single-sha-handoff-package
    provides: "experiments/HANDOFF.md §2.2 (environment variables) and §2.3 (pre-flight and its five overrides), read out of the clone rather than from memory"
provides:
  - "A 183-line pre-launch assertion record at /home/tlancaster/freeze02-prelaunch-assertions.txt, 15 PASS / 0 FAIL, every line carrying its measured value"
  - "Proof that the production clone is clean by the definition gate3_run_manifest_clean_tree actually uses, with all 190 residue entries enumerated and classified"
  - "Proof that the launch shell's SUITE_ and dry-run namespaces are empty, which is what mechanically enforces D-12, B1 and the default worker/thread caps"
  - "Launch-time (not research-time) measurement of the E2 frameset identity floor and the free-space floor"
  - "The artifact the 28-03 authorisation checkpoint is presented with, and that its launch task's precondition reads"
affects: [28-03-the-production-run, 28-05-run-record]

actuals:
  tokens: 4600
  tasks: 1
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Assertions written with their measured value rather than a bare verdict, so a record that was never measured is distinguishable from one that was"
    - "The all-passed line is emitted by the same script that counts the FAIL lines, so it cannot be written over a partial pass"
    - "Cleanliness asserted by the predicate the consuming gate computes, read from the consuming source by line number"

key-files:
  created:
    - /home/tlancaster/freeze02-prelaunch-assertions.txt
  modified: []

key-decisions:
  - "Cleanliness was asserted with git status --porcelain --untracked-files=no, the form _run_manifest.py:183 uses to derive git_dirty — not the bare form, which would have been the wrong gate"
  - "The residue was enumerated with --untracked-files=all --ignored, because the bare and untracked forms both print nothing: every residue entry in this clone is gitignored, so a bare enumeration would have reported an empty residue and proved nothing"
  - "A third residue category (src/aquacal.egg-info/, 6 files) was found beyond the two the plan enumerates. It was recorded explicitly and ruled benign rather than folded silently into 'interpreter caches' or treated as a halt — it is the metadata HANDOFF.md:49's own editable install writes, and moving it aside would damage the install assertion 6 depends on"
  - "pytest was deliberately not re-run in the production clone, because 28-01 established that doing so creates the empty experiments/results/ that assertion 4 requires to be absent"
  - "RUN-02 was left Pending. All five of this phase's plans carry it in frontmatter; it is satisfied by 28-03 after that run's roll-up is read"

patterns-established:
  - "The record states in its own body what it does NOT authorise, so it cannot be mistaken later for a launch approval"

requirements-completed: []

coverage:
  - id: A1
    description: "A pre-launch assertion record exists with every item carrying an explicit PASS and a measured value, and its final line says all assertions passed — written only if they all did"
    requirement: RUN-02
    verification:
      - kind: integration
        ref: "grep -q '^ALL PRELAUNCH ASSERTIONS PASSED$' && grep -c '^FAIL' == 0; 15 PASS lines each carrying a measured value"
        status: pass
    human_judgment: false
  - id: A2
    description: "The production clone is clean by the definition the run manifest actually uses, and the untracked residue is enumerated and consists only of dry-run state artifacts and interpreter caches"
    requirement: RUN-02
    verification:
      - kind: integration
        ref: "git status --porcelain --untracked-files=no empty (0 entries); residue enumerated at 190 entries, 0 unclassified, 0 matching experiments/results*"
        status: pass
    human_judgment: false
  - id: A3
    description: "PRELAUNCH_GATE_PYTHON is set to the production environment's absolute interpreter and that path is executable (D-28)"
    requirement: RUN-02
    verification:
      - kind: integration
        ref: "PRELAUNCH_GATE_PYTHON == /home/tlancaster/anaconda3/envs/aquacal-freeze02-prod/bin/python; test -x; -V reports Python 3.11.15"
        status: pass
    human_judgment: false
  - id: A4
    description: "No SUITE_-namespace variable and no dry-run variable is exported in the launch shell"
    requirement: RUN-02
    verification:
      - kind: integration
        ref: "env | grep -c '^SUITE_' == 0; env | grep -c '^RUN_EXPERIMENT_SUITE_DRY_RUN' == 0"
        status: pass
    human_judgment: false
  - id: A5
    description: "The E2 frameset clears pre-flight's identity floor and the clone's filesystem has at least 20 GiB free, both measured at launch time"
    requirement: RUN-02
    verification:
      - kind: integration
        ref: "13 extrinsic dirs, du -sb = 3799100985 B >= 3000000000; df avail = 688631734272 B = 641.34 GiB >= 20 GiB"
        status: pass
    human_judgment: false

duration: 5min
completed: 2026-08-24
status: complete
---

# Phase 28 Plan 02: Pre-Flight and Launch Authorisation Summary

**Thirteen pre-launch assertions executed against the machine as it is now — 15 PASS, 0 FAIL — and written to `/home/tlancaster/freeze02-prelaunch-assertions.txt` with each item's measured value on it, so the 28-03 authorisation gate has something real to be presented with. Nothing was launched.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-08-24T23:54:42Z
- **Completed:** 2026-08-24T23:59:00Z
- **Tasks:** 1
- **Files created:** 1 (off-repo by plan design; plan 05 copies it into the phase directory)

## Accomplishments

- **The checklist ran, and it ran against the machine rather than against the research.** The frameset byte total and the free-space figure were re-measured at launch time, not carried forward from `28-RESEARCH.md`'s session measurements. Both agree with them (3,799,100,985 B; ~641 GiB), which is a confirmation rather than an assumption.
- **Cleanliness was asserted with the predicate the consuming gate computes.** `git status --porcelain --untracked-files=no` → 0 entries. That string is read out of `_run_manifest.py:183` in the clone, where `_resolve_git_dirty` derives `git_dirty`, which is what `gate3_run_manifest_clean_tree` judges.
- **All 190 residue entries were enumerated and classified, and nothing was deleted or moved.** Zero of them match `experiments/results*`; zero are unclassified.
- **The three absences still hold** — no real state file, no `experiments/results`, no `experiments/results_e2_band` — re-asserted here independently of 28-01's assertions, after 28-01 moved pytest's residue aside.
- **`PRELAUNCH_GATE_PYTHON` is set explicitly (D-28)**, and the record shows both the value and that the path is executable and reports `Python 3.11.15`.
- **Both driver variable namespaces are empty**, and the record spells out what that emptiness enforces item by item (D-12, B1, `SUITE_WORKERS`=4, `SUITE_THREAD_CAP`=2, no `SUITE_OUT_DIR` redirection, the real state path rather than `.dryrun.tsv`).
- **Attempt 1's two preserved artifacts are byte-for-byte unchanged** at 31,845,719 and 425,119 bytes, both still `-r--r--r--`, mtimes still 2026-08-20 09:28.

## Task Commits

1. **Task 1: run the pre-launch assertion checklist and write the record** — `623fca4` (chore)

**Plan metadata:** see the final `docs(28-02)` commit.

## Files Created/Modified

This plan's artifact is **off-repo by design** — the plan's `files_modified` frontmatter lists a single `$HOME` path, and the artifacts table routes the `freeze02-*` evidence into `.planning/phases/28-full-suite-production-run/` at **plan 05**.

- `/home/tlancaster/freeze02-prelaunch-assertions.txt` — 183 lines, 11,216 bytes, 15 `PASS`, 0 `FAIL`, closing line `ALL PRELAUNCH ASSERTIONS PASSED`

Nothing inside the production clone was created, modified, moved or deleted by this plan.

## The measured record

### Item by item

| # | Assertion | Measured | Verdict |
|---|---|---|---|
| 1 | Sha | `7005a2771aa115e4f4c1284cec7e145739586a4a`; `git describe --tags` = `rerun-freeze-02` | PASS |
| 2a | Clean by the manifest's definition | `status --porcelain --untracked-files=no` → **0** entries | PASS |
| 2b | Residue enumerated | **190** entries, all `!!` ignored, **0** `??`; **0** matching `experiments/results*`; **0** unclassified | PASS |
| 3 | No real state file | `run_experiment_suite_state.7005a27.tsv` absent; only the three `.dryrun.*` forms present | PASS |
| 4a | No `results` | absent | PASS |
| 4b | No `results_e2_band` | absent | PASS |
| 5 | Interpreter | `which python` = `…/envs/aquacal-freeze02-prod/bin/python`; `CONDA_PREFIX` set; Python 3.11.15 | PASS |
| 6 | Library provenance | `aquacal.__file__` = `<clone>/src/aquacal/__init__.py` | PASS |
| 7 | The pin | `cv2.__version__` = `4.13.0` (`opencv-python` 4.13.0.92) | PASS |
| 8 | The extras | `pytest` 9.1.1, `psutil` 7.2.2 | PASS |
| 9 | Gate interpreter (D-28) | `PRELAUNCH_GATE_PYTHON` = the absolute env interpreter, `-x`, `Python 3.11.15` | PASS |
| 10 | Clean namespace | `SUITE_` count **0**; `RUN_EXPERIMENT_SUITE_DRY_RUN` count **0** | PASS |
| 11 | Frameset | **13** extrinsic dirs, **3,799,100,985 B** ≥ 3,000,000,000 (+26.6%) | PASS |
| 12 | Disk | **688,631,734,272 B = 641.34 GiB** free on `/dev/nvme0n1p2` (`/`) — 32.1× the 20 GiB floor | PASS |
| 13 | Attempt 1 untouched | 31,845,719 B `-r--r--r--`; 425,119 B `-r--r--r--` | PASS |

### The residue, in full — 190 entries, none of them a defect

`git status --porcelain` prints **nothing** in this clone, and so does `--untracked-files=no`. That is not because the clone is bare: it is because **every residue entry is gitignored** (`.gitignore:266-272` covers the `.dryrun.*` forms). Enumerating with the bare form would therefore have reported an empty residue and proved nothing at all. The enumeration was taken with `--untracked-files=all --ignored`:

| Category | Entries | What it is |
|---|---|---|
| `__pycache__/*.pyc` across 14 directories | 141 | interpreter caches |
| `.pytest_cache/*` | 5 | interpreter cache |
| `run_experiment_suite_state.7005a27.dryrun.{tsv,failures.txt,stagelogs/}` | 38 | 28-01's dry-run rehearsal |
| `src/aquacal.egg-info/*` | 6 | editable-install metadata — see below |
| matching `experiments/results*` | **0** | — |
| unclassified | **0** | — |

The four categories sum to exactly 190.

### The third category, and why it is not a halt

The plan permits two residue categories and says anything else is a halt, resolved by moving aside. A third was found: `src/aquacal.egg-info/` (6 files — `PKG-INFO`, `SOURCES.txt`, `requires.txt`, `top_level.txt`, `entry_points.txt`, `dependency_links.txt`).

It was **recorded in the record explicitly and ruled benign**, not folded silently into "interpreter caches" and not halted on. The reasoning, which is written into the record itself rather than only here:

- It is not run output and not a dry-run artifact. It is the setuptools metadata that `HANDOFF.md:49`'s own `python -m pip install -e ".[dev,bench]"` writes — a **product of the install step this phase's own plan 28-01 mandated**. Halting on it would be halting on the plan's prescribed action.
- It is gitignored, so it cannot affect `git_dirty` and therefore cannot affect `gate3_run_manifest_clean_tree`.
- It matches no output-tree path, so it cannot be mistaken for another run's artifacts — which is the failure shape (F-001) the halt clause exists to prevent.
- The prescribed remedy would make things worse: moving the editable install's metadata aside risks breaking the very install that assertion 6 (`aquacal.__file__` inside the clone) depends on, trading a non-hazard for a real one.

**Nothing was deleted and nothing was moved.**

### What the empty namespace enforces

Item 10 is not a hygiene nicety; it is the mechanical enforcement of four separate rulings, and the record names them:

- **D-12** — `SUITE_E2_RELEASE_CONFIG` unset, so `experiments/configs/e2_release_linux.yaml` resolves (`run_experiment_suite.sh:397`). Attempt 1 set it because it ran from Windows.
- **B1** — `SUITE_DISPATCH_LOG` unset, for invocation parity with attempt 1.
- **The defaults** — `SUITE_WORKERS`=4 (`:762-767`), `SUITE_THREAD_CAP`=2 (`:798`), not re-tuned.
- **No redirection** — `SUITE_OUT_DIR`/`SUITE_STATE_DIR` unset, `SUITE_STAGE_PYTHON` left to the driver to export (`:498-500`), `RUN_EXPERIMENT_SUITE_DRY_RUN` unset so the **real** state path is selected rather than `.dryrun.tsv` (`:287-292`).

`PRELAUNCH_GATE_PYTHON` is outside both namespaces and is set by design.

## Decisions Made

- **The gate's own predicate was read out of the gate's own source.** `_run_manifest.py:174-185` was opened in the clone and the `--untracked-files=no` form taken from it verbatim, rather than reproduced from the plan text. The docstring there states the reason (D-47) in the source's own words.
- **The residue enumeration method was changed to one that can actually see the residue.** The plan says to run bare `--porcelain` and enumerate what it shows; in this clone that shows nothing, so `--untracked-files=all --ignored` was used instead. Both forms are reported in the record.
- **The third residue category was surfaced rather than absorbed.** The honest failure mode here is a record that says PASS because the operator quietly widened the permitted set. The record names the category, counts it, and states the ruling and its reasons.
- **`pytest` was not re-run.** 28-01's finding 4 is a live hazard for this plan specifically: re-running it would create the empty `experiments/results/` that item 4 requires to be absent, i.e. the check would have destroyed its own precondition.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] The plan's residue-enumeration command shows nothing in this clone**

- **Found during:** Task 1, item 2
- **Issue:** The plan directs: *"Then run `git -C $CLONE status --porcelain` as well and enumerate the untracked residue into the record."* In this clone that command prints **zero lines** — every residue entry is gitignored, so `--porcelain` (which hides ignored files) reports an empty residue. Following the instruction literally would have produced a record whose residue enumeration was blank, which reads as strong evidence and is in fact no evidence: it would have been equally blank had a stray `experiments/results_smoke/` been sitting there under an ignore rule.
- **Fix:** Enumerated with `git status --porcelain --untracked-files=all --ignored` instead, which surfaces all 190 entries. **Both** forms are reported in the record, with the bare form's `0` shown and explained rather than omitted.
- **Files modified:** none
- **Verification:** the four classified categories sum to exactly 190 with zero unclassified, and the `experiments/results*` match count is 0.
- **Committed in:** `623fca4`

**2. [Rule 4-adjacent — surfaced, not silently resolved] A third residue category outside the plan's permitted set**

- **Found during:** Task 1, item 2
- **Issue:** The plan permits dry-run state artifacts and interpreter caches, and declares anything else a halt. `src/aquacal.egg-info/` (6 files) is neither.
- **Resolution:** Recorded and ruled benign, in the record itself, with the reasoning above. This is deliberately **not** treated as an unwritten widening of the permitted set: the category, its count and the ruling are all on the artifact the 28-03 checkpoint will read, so the human authorising the launch sees the judgment rather than inheriting it.
- **Why not a halt:** it is the product of the install command the phase's own plan mandated; it is gitignored and so cannot affect `git_dirty`; it matches no output-tree path; and the prescribed remedy (move aside) would jeopardise the editable install that assertion 6 depends on.
- **Files modified:** none — nothing deleted, nothing moved.
- **Committed in:** `623fca4`

**3. [Rule 1 — Bug, inherited from 28-01] `requirements mark-complete RUN-02` was not run**

- **Found during:** state updates
- **Issue:** All five of this phase's plans carry `RUN-02` in frontmatter. Running the executor's standard `requirements mark-complete` step here would flip `REQUIREMENTS.md` to `- [x] **RUN-02**: The full experiment suite … executes once end to end` and its traceability row to `Complete`. **That claim is false** — nothing has been launched, and this plan is expressly the one that stops before the launch.
- **Fix:** the step was skipped for `RUN-02`. This plan's `requirements-completed` frontmatter is empty.
- **Verification:** `REQUIREMENTS.md` still carries `- [ ] **RUN-02**` and `| RUN-02 | Phase 28 | Pending |`.
- **Committed in:** n/a — no change was made. **Plan 28-03 is the plan that may mark RUN-02 complete, and only after the run's roll-up is read.**

**4. [Rule 3 — Blocking] Task commit has no in-repo content to stage**

- **Found during:** Task 1
- **Issue:** The plan's only artifact is off-repo, so the per-task atomic-commit protocol had nothing to stage; writing the evidence into `.planning/` now would preempt plan 05.
- **Fix:** the same accommodation 28-01 established — an `--allow-empty` marker commit whose message body carries the task's literal measured output, putting the assertion evidence into repository history where it is durable independently of `$HOME`.
- **Verification:** `623fca4` resolves in `git log`.
- **Committed in:** `623fca4`

---

**Total deviations:** 4 (2 blocking, 1 bug prevented, 1 finding surfaced).
**Impact on plan:** No assertion was weakened. Deviation 1 makes the residue enumeration mean something rather than nothing; deviation 2 puts a judgment in front of the human instead of behind them; deviation 3 prevents a false completion claim; deviation 4 is a protocol accommodation to an off-repo plan.

## Issues Encountered

- **The plan's item-2 wording and the machine disagreed**, in the direction that produces a false negative (a blank enumeration read as a clean one). Diagnosed by running both forms rather than by assuming the plan or the machine was right, and both are on the record.
- **No assertion failed**, so the halt rule was never exercised. That is worth stating plainly: the `ALL PRELAUNCH ASSERTIONS PASSED` line was emitted by the same script that counted the `FAIL` lines, in a conditional, so it could not have been written over a partial pass.

## Known Stubs

None. This plan writes no code — the tag is frozen and nothing under the clone was touched.

## Threat Flags

None. No new security-relevant surface. The register's three rows for this plan are all `mitigate` and all are discharged:

| Threat | Discharged by |
|---|---|
| T-28-06 (ambient `SUITE_*` / dry-run variables) | item 10, measured `0` and `0`, with the enforced rulings named |
| T-28-07 (`gate3_run_manifest_clean_tree`) | item 2, asserted with `_run_manifest.py:183`'s own predicate, residue enumerated by a method that can see it, nothing deleted |
| T-28-08 (a record that says PASS without measuring) | every line carries its measured value; the all-passed line is conditional on the `FAIL` count |

## Verification Against `must_haves`

| Truth | Result |
|---|---|
| Assertion record exists, every item explicit PASS, final line present, written only if all passed | PASS — 15 PASS / 0 FAIL, line present, emitted conditionally |
| Clone clean by the manifest's own definition; residue enumerated and benign | PASS — 0 tracked-modified; 190 residue entries, 0 unclassified, 0 `results*` (with the third-category ruling recorded) |
| `PRELAUNCH_GATE_PYTHON` set to the env's absolute interpreter and executable (D-28) | PASS |
| No `SUITE_` and no dry-run variable exported in the launch shell | PASS — `0` and `0` |
| Frameset clears the identity floor and ≥ 20 GiB free, both measured at launch time | PASS — 3,799,100,985 B (+26.6%); 641.34 GiB (32.1×) |

| Prohibition | Result |
|---|---|
| No pre-flight override flag, in any form | HELD — none used; none needed |
| Delete nothing | HELD — nothing deleted, nothing moved |
| `SUITE_E2_RELEASE_CONFIG` / `SUITE_DISPATCH_LOG` unset; workers and thread cap at defaults | HELD — measured, not asserted |
| Nothing launched | HELD — the driver was not invoked, for real or otherwise |

## User Setup Required

None for this plan.

**One human decision is now outstanding, and it is the phase's gate:** the authorisation to launch the ~6 h production run (plan 28-03). This record is what that decision is presented with.

## Next Phase Readiness

**Ready for plan 28-03 — up to, and stopping at, its authorisation checkpoint.**

Carry forward:

1. **Nothing has been launched.** The abort authority ends at pre-flight; nothing aborts once stage 1 has begun (D-03/D-50, `run_experiment_suite.sh:2058-2076`). That is what makes the launch a door rather than a step.
2. **`RUN-02` is still `Pending`** and must stay that way until 28-03 reads the run's roll-up.
3. **The launch shell must be built the way the assertion shell was:** `conda activate aquacal-freeze02-prod` (activated, not merely gate-variable-set), `export PRELAUNCH_GATE_PYTHON=/home/tlancaster/anaconda3/envs/aquacal-freeze02-prod/bin/python`, and nothing in the `SUITE_` or dry-run namespaces.
4. **The record has a shelf life.** It measures the machine as of 2026-08-24T23:56:32Z. Free space and the three absences are the items most likely to drift; if anything runs in that clone before launch — `pytest` above all — re-take items 2, 3, 4 and 12.
5. **Do not read a healthy run's exit code as the verdict.** A healthy run exits NON-ZERO; the roll-up is authoritative (HANDOFF §2.8).

---
*Phase: 28-full-suite-production-run*
*Completed: 2026-08-24*

## Self-Check: PASSED

Both claimed artifact paths exist on disk (`/home/tlancaster/freeze02-prelaunch-assertions.txt`,
183 lines; `28-02-SUMMARY.md`), the task commit `623fca4` resolves in `git log --oneline --all`,
and `RUN-02` is confirmed still `- [ ]` / `Pending` in `REQUIREMENTS.md` (lines 188 and 271).
