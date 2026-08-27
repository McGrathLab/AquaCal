# MORNING HANDOFF — 2026-08-20

**Written 2026-08-20T00:20Z, right after the overnight production run launched.**

Your job this morning: work out whether the overnight run succeeded, and if so move Phase 29
forward. Read this before running anything.

---

## Where things stand

- **Phase 27 is COMPLETE (13/13).** The freeze is cut, published, and verified on the Linux run
  machine.
- **Phase 28 is EXECUTING** — the full-suite production run started on the Linux box at
  **2026-08-20T00:14:10Z**, expected ~15-16 h, so expect it to finish around **15:15-16:15Z**
  (11:15-12:15 EDT).
- **Frozen sha:** `3ab9c13723202a58bb50e351b0b6bc0c0ffcd59c`, tag `rerun-freeze-01`.
- **SoftwareX submission is 2026-08-21** — one day out.

The run is on the **Linux machine**, not this Windows box. You cannot inspect it directly; the
user has to paste output. Everything below is written as commands for them to run.

---

## THE ONE THING YOU MUST NOT GET WRONG

**The driver exits NON-ZERO on a completely healthy run. Do not report the run as failed because
of its exit code.**

Acceptance is read at the **end-of-run completeness roll-up**, never `$?`. On a passing run,
~17-19 per-stage `GATE FAIL` findings survive, because gates 1-4 judge the whole output tree at a
moment when it is still filling, and are applied to the auxiliary `e2_band` / `e2_timing` /
`e2_memory` / `e4_repeat` trees they do not own. This was ruled by the author on 2026-08-19 and
is documented in `experiments/HANDOFF.md` §2.8 and `27-PREPUSH-AUDIT.md`.

**What DOES matter, and always matters:**

1. A `STAGE FAILED` line in the failures file — a stage that *ran and failed*. Distinct from
   `GATE FAIL`.
2. Any stage carrying a non-zero exit in the state TSV.
3. `gate3_run_manifest_clean_tree` failing — means the tree was dirty at launch.
4. The roll-up not reaching `0 FAIL`.

---

## Ask the user for exactly this

```bash
cd ~/aquacal-frozen-rerun-freeze-01
awk '/END-OF-RUN COMPLETENESS ROLL-UP/,0' ~/suite_run_freeze01.log | grep -E "^\[FAIL\]|TOTAL:"
grep -E "STAGE FAILED" experiments/run_experiment_suite_state.3ab9c13.failures.txt || echo "NO STAGE FAILED LINES"
awk -F'\t' '$3=="complete" && $5!=0 {print "NONZERO:",$1,$5}' experiments/run_experiment_suite_state.3ab9c13.tsv
awk -F'\t' '$3=="complete"' experiments/run_experiment_suite_state.3ab9c13.tsv | wc -l
tail -3 ~/suite_run_freeze01.log
```

**Green looks like:** roll-up `0 FAIL`, no `STAGE FAILED`, no non-zero exits, **20** completed
stages.

**If it is still running**, the last command shows live progress; the state TSV shows which stages
have completed. Do not conclude it is hung from a quiet log — check the process:
`ps -o pid,etime,stat,cmd -p <pid>`, or that `experiments/results/` is still gaining files.

**If it died overnight**, re-launching the identical command **resumes**: a stage is skipped only
if it completed *and* exited 0, so anything that died mid-flight re-runs. The launch command is:

```bash
export PRELAUNCH_GATE_PYTHON="$HOME/anaconda3/envs/aquacal-freeze01/bin/python"
nohup bash experiments/run_experiment_suite.sh > "$HOME/suite_run_freeze01.log" 2>&1 &
disown
```

Note that re-launching **appends** to the same log path only if they use `>>`; the command above
truncates. Have them use a new log name for a resume so the first log survives.

---

## Terminal formatting note

The user's terminal mangles multi-line pasted blocks — a bash heredoc (`python - <<'PY'`) failed
because the closing marker came through indented. **Give single-line commands.** If you need
multi-line Python, write it to a file first.

Also `awk -F'\t' '…'file` (missing space before the filename) has already bitten once. Keep a
space.

---

## If the run is green — Phase 29

Phase 29 is **RUN-03/04/05**: gates pass, the E2 sanity control and E7 before/after clear, results
committed, Zenodo results package published pre-submission. Do not start executing it blind —
`/gsd:plan-phase 29` or read `.planning/ROADMAP.md` § Phase Details first.

Two things Phase 29 specifically owes, per the roadmap:

- **The E2 sanity control.** E2's schema does not change, so it should reproduce to ~1e-8. This is
  also what proves DEGEN-02's instrumentation of `_optim_common.py` did not perturb the solve. Note
  the working mechanism is `check_e2_band`'s numeric `real_rig_metrics.json` comparison at
  `_E2_METRICS_RTOL = 1e-6` (`check_rerun_gates.py:1340`) — E2's own `--check` compares only
  `camera_parameters.csv`, because `reprojection_residuals.csv` and `reconstruction_errors.csv` are
  DATA-01b-gitignored and ship only in Zenodo. `e2_real_rig.py:538-552` states this honestly; do not
  "fix" it by trusting E2's `--check` alone.
- **An explicit E7 before/after comparison** — FIX-02's two extra free parameters could soften a
  published 10-of-10 result.

---

## If the run is NOT green

Diagnose before re-running anything. The per-stage logs are at
`experiments/run_experiment_suite_state.3ab9c13.stagelogs/<stage>.log` and are the fastest route
to a root cause — that is how the e3 failure was diagnosed last night in one read.

**Do not add a pre-flight override flag to get past a refusal.** `--skip-e2` in particular
silently makes the run synthetic-only and would waste the whole night. A refusal is information.

**Do not edit anything in the clone.** The run machine's tree must not move — no pull, no
checkout, no commit there (D-27). A stage that ran at a different commit than the rest makes the
whole run unreportable. If a code fix turns out to be needed, it is made *here*, committed, and a
new `rerun-freeze-02` tag is cut; tags are never moved.

---

## Known, already-decided, do not re-litigate

- **The install-command deviation.** The frozen `HANDOFF.md` §1.2 says `pip install -e .`, which
  omits `pytest` (`dev`) and `psutil` (`bench`). Without them e3 dies outright and two required
  manifest fields go null. The target env was corrected with `pip install -e ".[dev,bench]"`
  before the run. Author ruled **record, do not refreeze**. Filed at
  `.planning/todos/pending/2026-08-20-POST-SUBMISSION-frozen-package-install-command-omits-required-extras.md`.
- **`e7_focal_standoff` and `e4_repeat` have never been rehearsed at any scale** (D-21) — they
  have no `--smoke` form. The production run is the first time their invocation lines execute. If
  anything fails, suspect these two first.
- **A fresh clone's *smoke* pass downloads 4.35 GB** from Zenodo record 21889922. The production
  run does not, because `e2_production` writes `reconstruction_errors.csv` first. Not a defect.
- **Do not attribute runtime differences to code.** The Linux smoke pass was 3.6x faster than the
  Windows one; that tracks the machine. The ~15-16 h estimate came from Windows measurements and
  may be well off.

---

## Context files, in the order worth reading

1. `.planning/phases/27-frozen-single-sha-handoff-package/27-ONTARGET-VERIFICATION.md` — what was
   verified on the target, the deviation, and what it explicitly does **not** prove.
2. `.planning/phases/27-frozen-single-sha-handoff-package/27-FREEZE-RECORD.md` — the frozen sha,
   the tag, the attempt log.
3. `experiments/HANDOFF.md` §2.8 — how to read the exit code. **Read this before judging the run.**
4. `.planning/phases/27-frozen-single-sha-handoff-package/27-PREPUSH-AUDIT.md` — the roll-up
   ruling and the exposure audit.
5. `.planning/STATE.md` — current position.

## Repository state

Local `main`-line branch is `experiments/full-suite-rerun`, synced with origin as of the last
push. The tag `rerun-freeze-01` is on origin and **must never be moved**. Pushing from this
Windows box runs a pre-push hook that executes the test suite (~50 min) with bare `python` — put
the env on PATH first or it fails with ~62 collection errors:

```bash
E=/c/Users/tucke/anaconda3/envs/aquacal; PATH="$E:$E/Library/bin:$E/Scripts:$PATH" git push …
```

Launch it detached (`nohup … & disown`) and watch `git ls-remote` for the ref, because the tool
harness kills long background waiters at ~35-50 min while the push itself survives.
