# RETURN HANDOFF — bringing the freeze-01 production run home

**Written 2026-08-20 on the Windows box, for an agent working on the LINUX RUN MACHINE.**

`experiments/HANDOFF.md` sent the package *out*. This document brings it *back*. Read it
completely before running anything. The run is finished; the output in
`~/aquacal-frozen-rerun-freeze-01` is a **15-hour artifact that exists in exactly one place**
and cannot be casually regenerated. SoftwareX submission is **2026-08-21** — one day out.

Your job: preserve the output, verify it, commit it with provenance intact, close Phase 29, and
file (do not fix) any bugs the run surfaced.

---

## 0. Prime directives

These are not style preferences. Each one has already cost this project time.

1. **The driver exits NON-ZERO on a healthy run.** Acceptance is the end-of-run completeness
   roll-up, never `$?`. ~17-19 per-stage `GATE FAIL` findings survive a passing run by
   construction. See `experiments/HANDOFF.md` §2.8. Do not report the run as failed on exit code.
2. **Never modify anything under `src/` on this machine.** Not a typo fix, not a lint fix. The
   committed results must correspond to the sha the manifest records. Code fixes are made on the
   Windows box per `experiments/HANDOFF.md` §2.7.
3. **Tags are never moved.** `rerun-freeze-01` stays where it is.
4. **Merge, never checkout.** Some files under `experiments/results/` are *tracked* and currently
   hold the fresh run's output. `git checkout` of another commit can clobber them. See §5.
5. **Delete nothing.** Not stale trees, not smoke outputs, not `results_smoke*`. Moving aside is
   fine; deleting is not.
6. **Do not add pre-flight override flags.** `--skip-e2` in particular silently makes a run
   synthetic-only. A refusal is information.
7. **You may not push to `main`.** You push exactly one branch: `results/rerun-freeze-01`.

---

## 1. Orientation

- **Clone:** `~/aquacal-frozen-rerun-freeze-01`
- **Frozen sha:** `3ab9c13723202a58bb50e351b0b6bc0c0ffcd59c`, tag `rerun-freeze-01`
- **Run log:** `~/suite_run_freeze01.log`
- **Run started:** 2026-08-20T00:14:10Z
- **Origin:** `github.com/McGrathLab/AquaCal`; the live branch is `experiments/full-suite-rerun`
- **Env:** conda env `aquacal-freeze01`; `cv2` must be 4.13.x

The clone's `.planning/` is at the **frozen sha**, which predates the Phase 27 closure. Do not
trust `.planning/STATE.md` in the working tree until after the merge in §5. To read current
planning docs before then, without touching the tree:

```
git fetch origin
git show origin/experiments/full-suite-rerun:.planning/STATE.md
git show origin/experiments/full-suite-rerun:.planning/MORNING-HANDOFF-2026-08-20.md
```

`git fetch` is safe at any point — it updates refs only, never the working tree.

---

## 2. PHASE A — preserve, before anything else

Do this first. Nothing else in this document is safe until it is done.

```
cd ~/aquacal-frozen-rerun-freeze-01
git rev-parse HEAD
git status --porcelain > ~/freeze01-tree-state-at-handoff.txt
wc -l ~/freeze01-tree-state-at-handoff.txt
```

Record `git rev-parse HEAD`. It must be `3ab9c13...`. If it is not, **stop and report** — the
tree has moved and the provenance question changes completely.

Then snapshot every output tree plus the driver state files to a read-only archive **outside the
clone**:

```
cd ~/aquacal-frozen-rerun-freeze-01
tar czf ~/rerun-freeze-01-output.tar.gz experiments/results experiments/results_e2_band experiments/results_e4_repeat experiments/results_linux32gb experiments/run_experiment_suite_state.3ab9c13.tsv experiments/run_experiment_suite_state.3ab9c13.failures.txt experiments/run_experiment_suite_state.3ab9c13.stagelogs
sha256sum ~/rerun-freeze-01-output.tar.gz | tee ~/rerun-freeze-01-output.sha256
chmod a-w ~/rerun-freeze-01-output.tar.gz
ls -lh ~/rerun-freeze-01-output.tar.gz
```

If any path in that `tar` does not exist, **do not drop it silently** — report which trees are
missing, because that is itself a finding about what the run produced. Re-run `tar` with only the
paths that exist, and say so in your report.

Also preserve the run log itself:

```
cp ~/suite_run_freeze01.log ~/suite_run_freeze01.log.preserved
chmod a-w ~/suite_run_freeze01.log.preserved
```

---

## 3. PHASE B — verify while the tree is still pristine

Gate 3 (`gate3_run_manifest_clean_tree`) judges whether the tree was clean at launch. Once you
start committing, that evidence is gone. So the gates run **now**, and their output goes to files
**outside** the clone.

### 3.1 Re-read the run verdict

```
awk '/END-OF-RUN COMPLETENESS ROLL-UP/,0' ~/suite_run_freeze01.log | tee ~/freeze01-rollup.txt
grep -E "STAGE FAILED" experiments/run_experiment_suite_state.3ab9c13.failures.txt || echo "NO STAGE FAILED LINES"
awk -F'\t' '$3=="complete" && $5!=0 {print "NONZERO:",$1,$5}' experiments/run_experiment_suite_state.3ab9c13.tsv
awk -F'\t' '$3=="complete"' experiments/run_experiment_suite_state.3ab9c13.tsv | wc -l
```

Note the space before the filename in those `awk` calls — omitting it has bitten before.

**Green is:** roll-up reaching `0 FAIL`, no `STAGE FAILED` line, no non-zero stage exits, and
**20** completed stages.

### 3.2 Run the gates

```
python experiments/check_rerun_gates.py experiments/results --profile full 2>&1 | tee ~/freeze01-gates-full.txt
tail -5 ~/freeze01-gates-full.txt
```

`--profile full` asserts row counts, not merely artifact existence — that is the one that matters
here. The script exits 1 if any gate FAILs; per directive 1, read the `TOTAL:` line, and classify
each FAIL rather than treating the exit code as a verdict.

For each `FAIL` in that output, decide and write down which it is:

- **Expected-by-construction** — gates 1-4 applied to the auxiliary `e2_band` / `e2_timing` /
  `e2_memory` / `e4_repeat` trees they do not own, or judging a tree mid-fill. ~17-19 of these are
  normal. Ruled by the author 2026-08-19; see `27-PREPUSH-AUDIT.md`.
- **Real** — anything else, and *especially* `gate3_run_manifest_clean_tree`.

Do not "fix" an expected-by-construction FAIL by editing the gate script. That is a `src/`-adjacent
change and directive 2 forbids it.

### 3.3 Capture the environment

```
python -c "import aquacal, sys; print(aquacal.__file__); print(sys.executable)" | tee ~/freeze01-env.txt
python -c "import cv2; print('cv2', cv2.__version__)" | tee -a ~/freeze01-env.txt
uname -a | tee -a ~/freeze01-env.txt
pip freeze | tee ~/freeze01-pip-freeze.txt | wc -l
```

---

## 4. PHASE C — branch and commit the results

Only now. The clone is very likely on a detached HEAD at the tag; creating a branch from it moves
nothing in the working tree.

```
cd ~/aquacal-frozen-rerun-freeze-01
git checkout -b results/rerun-freeze-01
git status --porcelain | wc -l
```

### 4.1 What goes into git, and what does not

A large share of the output is **deliberately gitignored** under policy `DATA-01b` and ships via
Zenodo instead — `calibration.json`, `reprojection_residuals.csv`, `reconstruction_errors.csv`,
`exp2_spatial_errors.csv`, `interface_ablation_conditioning.npz`, and the E2 band's derived bulk.
**Do not force-add any of them.** `git add -A` respects `.gitignore`; that is the intended
behaviour, not a bug to work around. If you find yourself reaching for `git add -f`, stop.

Commit in coherent pieces rather than one giant commit:

```
git add -A experiments/
git status --short | head -40
git commit -m "results(28): full production suite at rerun-freeze-01"
```

Then copy the evidence files you produced outside the clone into the repo and commit them:

```
mkdir -p .planning/phases/28-full-suite-production-run
cp ~/freeze01-rollup.txt ~/freeze01-gates-full.txt ~/freeze01-env.txt ~/freeze01-pip-freeze.txt .planning/phases/28-full-suite-production-run/
git add .planning/phases/28-full-suite-production-run
git commit -m "docs(28): run verdict, gate output, and environment capture"
```

### 4.2 The mechanical gate on this branch

Before pushing, prove you changed no code:

```
git diff --stat rerun-freeze-01..HEAD -- src/
```

**That must print nothing.** If it prints anything at all, stop and report — do not push.

Then push:

```
git push -u origin results/rerun-freeze-01
```

The clone has no git hooks (a fresh clone does not copy `.git/hooks`), so this is fast. If it is
slow, something installed hooks and you should say so.

---

## 5. PHASE D — bring the branch current

Now, and not before, pick up the Phase 27 closure (`d49a837`) so your Phase 29 work is written
against a current `STATE.md` and `ROADMAP.md` rather than the frozen sha's stale copies:

```
git fetch origin
git merge origin/experiments/full-suite-rerun
```

This is a docs-only merge and should be clean. If it conflicts in `.planning/STATE.md` or
`.planning/ROADMAP.md`, resolve by **taking origin's version** and re-applying your Phase 29 edits
on top — those two files are known to corrupt under careless merges. Verify the frontmatter parses
afterwards.

Re-run the `src/` gate from §4.2 after merging, then push again.

---

## 6. PHASE E — Phase 29

Phase 29 is **Gate Verification & Results Commit** (RUN-03 / RUN-04 / RUN-05). Read
`.planning/ROADMAP.md` § Phase Details for the authoritative success criteria before executing.
Its four deliverables:

### 6.1 Gates pass

Done in §3.2 — write it up with the FAIL classification.

### 6.2 The E2 sanity control

E2's schema does not change across this re-base, so E2 should reproduce to ~1e-8. This is also
what proves DEGEN-02's instrumentation of `_optim_common.py` did not perturb the solve.

The working mechanism is `check_e2_band`'s numeric comparison of `real_rig_metrics.json` at
`_E2_METRICS_RTOL = 1e-6` (`experiments/check_rerun_gates.py:1511`). **E2's own `--check` is not
sufficient** — it compares only `camera_parameters.csv`, because `reprojection_residuals.csv` and
`reconstruction_errors.csv` are `DATA-01b`-gitignored and ship only in Zenodo.
`experiments/e2_real_rig.py:538-552` states this honestly. Do not "fix" it by trusting E2's
`--check` alone, and do not report the control as clear on that basis.

### 6.3 The E7 before/after comparison

FIX-02 added two free parameters, which could soften the published 10-of-10 E7 result. Produce an
explicit before/after. Two things constrain how you report it:

- E7's published p-values are **one-sided**. Two-sided they are 0.00195 (`fixed`) and 0.109
  (`refined`) — `refined` clears 0.05 under neither convention. State which convention you use.
- E7's `refined` arms are **seed-unstable at >10 mm**. A single-seed directional conclusion is not
  safe. Say so rather than reporting a direction.

If the comparison weakens the result, that is a finding to report, not a problem to solve.

### 6.4 The Zenodo results package

Build it here — this is the machine that holds the `DATA-01b` bulk, which is the whole reason
Phase 29 moved to this box. Produce the archive and its checksum.

**Do not publish it.** The author publishes Zenodo records personally through the web UI. Hand
back transcribable values — file list, sizes, sha256, proposed description — and stop. "Keep
going" is not publish authorization.

### 6.5 File the bugs — do not fix them

The run surfaced some largely-cosmetic warnings and errors. For each one, write a TODO at
`.planning/todos/pending/YYYY-MM-DD-<slug>.md`, following the format of the existing
`2026-08-20-POST-SUBMISSION-frozen-package-install-command-omits-required-extras.md`. Include the
stage, the exact message, the stage log path, and your read of severity.

If a bug looks like it needs a code change, that is a **proposed insert phase**, written as a
planning document — not an edit. Directive 2 is absolute. Suspect `e7_focal_standoff` and
`e4_repeat` first for anything odd: per D-21 neither has ever been rehearsed at any scale, and the
production run is the first time their invocation lines ever executed.

The per-stage logs are the fastest route to a root cause:
`experiments/run_experiment_suite_state.3ab9c13.stagelogs/<stage>.log`.

---

## 7. Known and already decided — do not re-litigate

- **The install-command deviation.** The frozen `HANDOFF.md` §1.2 says `pip install -e .`, omitting
  the `dev` and `bench` extras. Without `pytest`, e3 dies outright; without `psutil`, two required
  manifest fields go null. The target env was corrected with `pip install -e ".[dev,bench]"` before
  the run. The author ruled **record, do not refreeze**. Already filed.
- **A fresh clone's *smoke* pass downloads 4.35 GB** from Zenodo record 21889922. The production run
  does not. Not a defect.
- **Do not attribute runtime differences to code.** The Linux smoke pass was 3.6x faster than the
  Windows one; that tracks the machine. Never write "the fix made calibration faster/slower."
- **Which experiments carry an accuracy claim:** E5, E6, E7 have seed bands. E1 has a regenerable
  ratio band (97–178x) but no accuracy claim. **E3 and E4 have no band at all** and cannot carry one.
- **E1's 97–178x band is a banded claim and is publishable as such.** Do not "correct" it to a
  point estimate; ~135x is within noise.

---

## 8. What to report back

A single summary containing:

1. The run verdict — roll-up totals, `STAGE FAILED` presence, non-zero exits, completed stage count.
2. The gate `TOTAL:` line, plus every FAIL classified expected-by-construction or real.
3. Confirmation that `git diff --stat rerun-freeze-01..HEAD -- src/` is empty.
4. The pushed branch name and its head sha.
5. The archive path, size, and sha256 for both the output tarball and the Zenodo package.
6. The E2 sanity control result and the E7 before/after, with the caveats in §6.2-6.3 attached.
7. Every TODO you filed, by path, one line each.
8. Anything you chose not to do, and why.

If you hit something this document does not cover and the safe move is unclear, **stop and ask**
rather than improvising. One day before submission, a paused agent costs minutes; a wrong
irreversible move costs the run.
