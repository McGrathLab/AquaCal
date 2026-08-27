# 27-PREPUSH-AUDIT — the smoke acceptance pass and the public-exposure scan

Two gates that had to clear before the tag. Both are recorded here with the author's rulings.

**Verdict: PASS.** The local `--smoke` acceptance pass reports **0 FAIL** in the end-of-run
roll-up with all 20 stages at exit 0, and the author approved the public exposure on 2026-08-19.

---

## Task 1 — the local `--smoke` acceptance pass

### Result

| | 26-10 baseline (`88512b7`) | This pass (`9ac6a6d`) |
|---|---|---|
| Roll-up PASS | 71 | **72** |
| Roll-up N/A | 9 | **18** |
| Roll-up **FAIL** | **12** | **0** |
| Stages exiting non-zero | 1 (`reconstruction_bootstrap`) | **0** |
| `STAGE FAILED` lines | 1 | **0** |
| Wall clock | 11 min 05 s | 10 min 56 s |

All 12 pre-existing FAILs are cleared and **no new FAIL appeared**. The N/A count rises 9 to 18
because 27-03 retagged smoke-unwritable artifacts as full-only and suppressed four E6
`gate4_optimality` checks plus the E6 seed-band axis at the smoke profile — these are *declared*
non-judgements, each carrying a rationale string, not silent omissions.

### Invocation

    PATH="<aquacal env>:...:$PATH" \
    PRELAUNCH_GATE_PYTHON="<aquacal env>/python.exe" \
    SUITE_E2_RELEASE_CONFIG="C:/Users/tucke/Desktop/Aqua/AquaCal/release_calibration/config.yaml" \
    nohup bash experiments/run_experiment_suite.sh --smoke > <log outside the tree> 2>&1 &
    disown

**No pre-flight override flag was used.** `SUITE_E2_RELEASE_CONFIG` is the documented Windows
escape hatch (D-12), not an override — 27-08 changed the default to the in-repo Linux config,
whose absolute target paths do not resolve on this box.

### Other acceptance criteria

- `experiments/results/` — **untouched**; the pass wrote only to `experiments/results_smoke*`.
- `run_manifest.json` and `environment_lock.txt` — both present in the smoke out dir.
- Manifest carries `blas_thread_cap: 2`, 16 capped stages and the 4 unpinned `serial_alone`
  timing stages, and `git_sha 9ac6a6dc...`.
- `gate3_run_manifest_clean_tree` — **PASS** (the tree was clean at launch).

### RULING — the roll-up is the acceptance condition, not the driver's exit code

**The driver exits NON-ZERO on this passing run, and that is expected.** The plan's criterion
"the driver's final exit code is 0" is not satisfiable as written, and its intent — all 12 FAILs
cleared, none new — is fully met. Author's ruling, 2026-08-19: **read acceptance at the roll-up.**

17 `GATE FAIL` findings remain. Every one is a *per-stage* gate, and they are structurally red
for two reasons unrelated to the run's health:

1. **The per-stage gate judges the whole tree.** `run_gate_check` passes `--stage`
   (`run_experiment_suite.sh:885`), but that scopes only the *completeness* checks; gates 1-4
   (guard count, status, provenance, optimality) run the full E1/E4/E6/E7 battery over whatever
   the tree holds at that moment. `fd_jacobian` at stage 3 therefore FAILs on E1 and E7
   benchmarks that stages 4-18 have not written yet. The totals climb from 19 PASS at the first
   gate to 72 PASS at the roll-up over the *same* artifacts — the artifacts were never missing,
   they were merely not written yet.
2. **The auxiliary trees get the battery too.** `e2_band`, `e2_timing`, `e2_memory` and
   `e4_repeat` each hold one stage's output and no run manifest, so the E1/E4/E6/E7 gates and
   `gate3_run_manifest_present` FAIL there by construction — each scored `1 PASS / 18 N/A /
   28 FAIL`.

Each finding is sticky and any finding forces a non-zero exit. That is D-01 working as designed
(the queue continues; the exit code makes a partial run impossible to mistake for green) — it is
simply not a per-run health signal.

**This is pre-existing, not a wave-1/2 regression:** `88512b7` produced the same findings of the
same shape.

**The alternative was declined.** Scoping gates 1-4 per stage, or exempting the auxiliary trees,
means editing the script that judges every artifact, inside the freeze window, to fix a number
rather than evidence. Reasonable post-submission cleanup; not a freeze-window change.

**What this ruling does NOT relax.** Three signals stay hard, and were promoted to explicit
acceptance criteria in 27-13 so that relaxing the exit code did not quietly relax them:

- a `STAGE FAILED` line in the sticky failures file — a stage that **ran and failed**, distinct
  from a `GATE FAIL` line;
- any stage carrying a non-zero exit in the state TSV;
- `gate3_run_manifest_clean_tree` — a dirty tree means the recorded `git_sha` does not fully
  describe the code that ran.

**Propagated to:** `experiments/HANDOFF.md` section 2.8 (new, with the `awk` recipe for pulling
the roll-up out of a 15-hour log, and pointers from 2.1 and 2.6), `27-13-PLAN.md` acceptance
criteria, and `ROADMAP.md` lines 409 and 421.

### Two earlier attempts, recorded because each found something real

1. **Pre-flight refused** (`d0dd8c6`): `experiments/results_smoke` still held the 2026-08-18
   `88512b7` artifacts with no state file for the new sha. The guard was right — a fresh run into
   a populated tree lets the completeness gate report someone else's artifacts as this run's.
   Resolved by archiving to `../AquaCal_smoke_aside/2026-08-19-88512b7/`, **not** by
   `--allow-nonempty-out`, which would have poisoned exactly the before/after comparison this
   task needs.
2. **One roll-up FAIL** (`d0dd8c6`): `gate3_run_manifest_clean_tree` — an uncommitted `STATE.md`
   left the tree dirty. Committed as `9ac6a6d`; the gate now passes. **The frozen run has the
   same requirement**, and section 2.8 says so.

### Portability note for the target (D-30)

The manifest records `gate_interpreter: ...\envs\aquacal\python.exe` and
`stage_interpreter: ...\envs\AquaCal\python.exe` — differing in case — with
`interpreters_agree: True`. Correct here: Windows is case-insensitive, and there is one env on
disk (`AquaCal`), carrying OpenCV **4.13.0** as required. **Linux is case-sensitive.** On the
target the two must match exactly or `interpreters_agree` will read `False` (or
`stage_interpreter` will be `None`), and that is the field to check before trusting the recorded
versions.

---

## Task 2 — the public-exposure scan

### Size of the exposure

| | Recorded at planning | Measured now |
|---|---|---|
| Commits ahead of `origin/main` | 218 | **273** |
| Files changed | — | 498 |
| Insertions | — | 69,169 |

**Drift noted:** 273, not 218. The difference is waves 1 and 2 of this phase landing after the
count was recorded. Not a discrepancy to resolve — the number simply moved.

`experiments/full-suite-rerun` has **no upstream configured**; nothing about this work is on
GitHub yet.

### Credentials — CLEAN

A scan of tracked content at HEAD for API keys, tokens, passwords, private-key headers, GitHub
PATs (`ghp_`, `github_pat_`) and AWS access keys (`AKIA...`) returned **no literal secrets**.
Every hit is a GitHub Actions secrets reference (`RELEASE_TOKEN`, `CODECOV_TOKEN`) or an
`id-token: write` OIDC permission — the correct pattern, which is the absence of a secret rather
than one. `detect-secrets` also runs as a pre-commit hook and passed on every commit in this
phase.

### Personal absolute paths — DISCLOSED, APPROVED

| Location | Count | Content |
|---|---|---|
| `.planning/**` | 120 files | `C:\Users\tucke\...` in planning prose and captured logs |
| `experiments/**` | 9 files | incl. `pre_rerun_baseline/driver_state/rerun_19_4.log`, `e6_legal_seed_probe.sh:23`, `e2_real_rig.py:27,925` |
| `tests/**` | 2 files | |
| `experiments/configs/e2_release_linux.yaml` | 26 paths | `/home/tlancaster/PycharmProjects/AquaCal/...` |

Two home-directory usernames become public: `tucke` (Windows dev box) and `tlancaster` (Linux run
machine). Neither is a credential; the author's GitHub identity is already public on this repo.

`e2_release_linux.yaml` embeds the operator's home directory **deliberately** — its own header
argues the case: the paths must resolve on the target, and "a sanitised path that does not resolve
on the target would be strictly worse than a published directory name." `27-TARGET-FACTS.md`,
the other file flagged by its plan's threat model, contains **zero** Windows paths.

### RULING — approved

**Author approved the exposure and authorised the push and tag on 2026-08-19**, having been shown:
the 273-commit count, the clean credential result, the 131 files carrying `C:\Users\tucke\`, and
the 26 `/home/tlancaster/` paths in the release config. Scrubbing the `.planning` paths was
offered and declined in favour of proceeding.

---

## Outcome

Both gates clear. Plan 27-11 (push plus an annotated `rerun-freeze-NN` tag, non-`v*` so no CI
workflow fires) is authorised to proceed.
