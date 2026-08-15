---
created: 2026-08-15T00:00:00.000Z
title: Extend rerun_19_3.sh into the full-suite driver — the band runs and E2 sit outside it, which is exactly where the six-sha provenance spine fractured
area: experiments
resolves_phase: 26
files:
  - experiments/rerun_19_3.sh
  - experiments/check_rerun_gates.py
  - experiments/README.md
---

## The finding that reframes this

**Do not write a run-book document. One already exists as code, and its coverage gap is the
root cause of an audit finding.**

`experiments/rerun_19_3.sh` (290 lines) is a mature, battle-tested queue driver. It already
handles serial shortest-first execution, stage state where start and completion are distinct (a
stage that started and died re-runs from scratch rather than counting as done), resume, a gate
check after every stage, unbuffered output, E3's load-bearing `--check`-then-`--force` ordering,
E6's isolated repeat-2 directory with a positive re-solve signal, partial-checkpoint clearing, a
guarantee that it performs no tree-mutating git operation, and the detached-launch instruction
naming the three sweeps this project lost to `run_in_background`.

`check_rerun_gates.py` complements it with four post-run gates, including **Gate 3: every
`git_sha` found across the whole run must be IDENTICAL** — "a split sha means something was
committed while a stage was still running."

**Now look at what the queue actually invokes:**

```
run_stage_e1  ->  e1_refractive_comparison --force --out
run_stage_e5  ->  e5_index_sensitivity     --force --out
run_stage_e6  ->  e6_generalization_sweep  --force --out
run_stage_e7  ->  e7_interface_ablation    --force --out
```

**No `--seeds` anywhere. E2 is not a stage at all.** Neither is `reconstruction_bootstrap`,
`e7_focal_standoff_analysis`, or `fd_jacobian_accuracy`. Seven stages, five experiments, and only
the single-seed artifacts.

The band artifacts — the ones every accuracy claim in the paper rests on — came from **separate
ad-hoc invocations**, which is why `e1_band_rerun.log` and `e7_band_rerun.log` sit loose in
`experiments/`. And the shas confirm it: the queue froze `22e75ef` across its seven stages, while
`e5_seed_band_provenance.json` records `2a2f0fa`, `e7_seed_band_provenance.json` records
`b13a3e0`, and `e1_seed_band_provenance.json` records `3eb1f4a` — three later, unrelated commits.

**This is the mechanism behind audit finding F-001.** Gate 3 enforced one sha across everything
the queue covered. The provenance spine fractured exactly at the boundary of what it did not.
Fixing the coverage is what retires F-001/F-002 — not a discipline reminder, not a document.

## Rename it — it is the suite's entry point, not a phase artifact

**Author decision 2026-08-15.** `rerun_19_3.sh` is named for a phase that is over, and the thing it
names is the canonical way to run the entire experimental suite. Rename it (`git mv`, so the
history follows) to something that says what it is — `run_suite.sh` or equivalent — and let its
header claim that role explicitly.

**⚠ The state file is a live footgun during the rename.** `is_stage_complete()` reads
`experiments/rerun_19_3_state.tsv`, which currently carries `complete` lines for **all seven
stages** of the 2026-08-02 run. Rename the script, keep the state file, and every stage is skipped:
the suite does nothing and **exits 0**. Rename or reset the state file and
`rerun_19_3_frozen_sha.txt` in the same commit, and have the driver refuse to start when the state
file's frozen sha does not match current `HEAD` — a stale state file is indistinguishable from a
completed run, and that is precisely the class of silent no-op this milestone exists to eliminate.

**Two inherited stages need a decision, not a rename.**

- **`e6_repeat2` should become a flag.** It exists for D-19.3-13/D-19.3-20's determinism
  measurement and costs a second full E6 pass — ~107 min on every run, forever. Determinism is a
  standing claim (16 of 308 cells), so keep the capability, but gate it behind an explicit flag so
  the default suite does not pay 1.8 h for a measurement nobody asked for that night.
- **E3's `--check`-then-`--force` ordering means something different now.** It is load-bearing
  *because* `--check` captured the pre-regeneration state before `--force` destroyed it. With prior
  outputs archived aside and `--check` suspended for reshaped artifacts, re-read whether the first
  invocation still earns its place. Decide deliberately; do not inherit it by default.

**Open design question — data-dependent stages.** E2 needs the 4.35 GB Zenodo archive or the local
frameset; the synthetic stages need nothing. If the entry point hard-requires E2's data, "run the
suite" becomes impossible for anyone who lacks it — which matters, because a reviewer being able to
run this is part of the paper's claim. Prefer a precondition check that **skips with a loud
announcement** over a hard failure, and make the skip visible in the completeness gate rather than
silently reducing the expected artifact list.

**Do not rewrite it in Python for this run.** A Python entry point is the better long-term shape —
cross-platform, testable, able to emit the manifest directly — but the bash script encodes details
that are easy to lose in translation: the `tee` / `PIPESTATUS` exit capture, the resumability
skip-line grep, the started-versus-completed distinction, `disown` semantics. Rewriting a proven
overnight driver under a six-day deadline is the wrong bet. Rename, extend, revisit the language
after submission.

## Solution

**Extend the driver, and let the existing gate do the enforcing for the first time.**

- **Add the four `--seeds` stages** (E1, E5, E6, E7). Band mode and default mode write disjoint
  artifact sets — E1's docstring: *"A `--seeds` run NEVER writes `exp1_parameter_errors.csv` …
  those remain exclusively the single-seed run's artifacts"* — so these are additional stages, not
  substitutions.
- **Add E2 as a stage**, with its separate invocations: the production run against
  `config_paper.yaml`, the band runs (`--band-dir` / `--band-seeds` / `--emit-band-configs`), and
  **timing and memory as two distinct runs**. `internals.benchmark_memory` is a config flag
  defaulting to `False` (`pipeline.py:389`) that costs 2.7–5.5% wall clock, so one run cannot
  produce both numbers honestly.
- **Add the three orphan scripts with their ordering constraints made structural**:
  `e7_focal_standoff_analysis` after E7's `--seeds` stage (it reads the band CSV at `:299`),
  `reconstruction_bootstrap` after E2 (it consumes `--reconstruction-errors` from E2's output),
  and `fd_jacobian_accuracy` anywhere. Ordering encoded in `STAGES=()` is enforced; ordering
  described in a README is not.
- **Pass E3's `--include-per-camera-latex`** if the manuscript renders that fragment. It is off by
  default and the current stage does not pass it.
- **Add a completeness gate** — the one thing neither existing tool does. `check_rerun_gates.py`
  validates the *content* of artifacts it finds; nothing asserts that every artifact the suite
  should have produced *exists* and carries its expected row count. A forgotten `--seeds` currently
  produces a clean green run with no band CSV in it. Expected row counts are derivable from the
  design (seeds × depths × models = 640 for the new E1 band; 4 arms × 10 seeds × 12 cameras = 480
  for E7's) and are cheap to assert.
- **Update `experiments/README.md` §2** to one row per *invocation*, not per experiment. As written
  it lists `python -m experiments.e1_refractive_comparison` with no `--seeds` row anywhere, so an
  operator following it produces no seed bands at all.

## Stress test — where this still does not save you

Recorded so the driver is not over-trusted.

- **The smoke pre-flight validates wiring, not config content.** `--smoke` runs
  `create_scenario("ideal")` — different geometry, 4 cameras, and it deliberately reports a
  non-zero degenerate count. It will catch a flag typo or an import error in minutes. It will
  **not** catch a wrong `--config` path or a bad production YAML, which is the failure that costs
  the most.
- **Existence and row count are not correctness.** A gauge-corrected column populated with
  uncorrected values passes every check here. That is the expectation sheet's job
  (`2026-08-15-suspend-programmatic-check-for-reshaped-artifacts.md`), not this one's.
- **The coupling is unenforced.** Every schema-changing fix in this milestone adds an artifact the
  completeness gate must know about — the noise-axis band, the per-camera gauge table, the split
  degeneracy columns, the 198 classification log. Nothing makes those TODOs update the expected
  list, so **the last step of each fix must be to add its outputs to the driver and the gate.**
  Say so in each one.
- **A gate FAIL does not abort the queue**, by design (D-19.3-18) — verdicts are read afterwards.
  That is right for measurement gates and wrong for a completeness gate that fires on stage 2 of
  fifteen. Decide deliberately which class the new gate is in.

## Do not

- Do not write a parallel run-book document. A second description of the run drifts from the
  script; the script is the description.
- Do not fold the band runs into the default stages as a substitution. The two modes write
  disjoint artifacts and both sets are cited.
- Do not merge E2's timing and memory runs. The flag perturbs the quantity being measured.
- Do not weaken Gate 3 to accommodate a stage that runs at a different commit. Gate 3 failing is
  the system working — it means the run really did fracture, and the answer is to re-run the stage
  inside the frozen window, not to relax the gate.
- Do not mutate the **run machine's** checkout while the queue is in flight — no pull, no checkout,
  no commit there. The script guarantees it performs no tree-mutating operation of its own; the
  operator has to match that on the box the queue is running on.

## Two-machine operation — plan here, run on Linux

**Author decision 2026-08-15:** milestone planning and the code fixes happen on the Windows box;
the suite itself is pushed to the larger Linux machine and runs there.

Two consequences the driver work should account for:

- **Confirm the Linux box already holds the input frames before pushing.** Pushing code is cheap;
  discovering that 4.35 GB of frames is missing after you have committed to the launch is not. The
  earlier Linux re-run executed E2 three times (`e2_timing`, `e2_memory`, `e2_cv413`), so they are
  almost certainly still there — verify anyway. This belongs in the pre-flight, alongside the smoke
  stages.
- **D-19.3-18's commit rule relaxes, and should be restated precisely in the driver's header.** It
  was written for a single machine, where per-stage `git rev-parse HEAD` could capture two shas
  if anything landed mid-run. With the run isolated, the real constraint is *the run machine's tree
  must not move* — pull, checkout or commit **there**. Work on the planning box, including commits
  and pushes, is safe and is expected to continue during the run (see
  `2026-08-15-repackage-and-reupload-the-zenodo-archive.md`, which is scheduled to happen
  concurrently). Stating the narrow rule matters: the over-broad version would idle the planning
  box for the whole window for no reason.

## Related

- Audit **F-001** and **F-002** (`Spinoffs/papers/aquacal/AUDIT-goal4.md` Pass A) — this todo is
  their root cause and their fix.
- `2026-08-15-emit-a-single-run-manifest-for-the-full-suite.md` — narrower than first written,
  since Gate 3 already enforces sha identity; what remains there is the environment capture and
  the `aquacal_version` / OpenCV-build defects.
- `2026-08-15-suspend-programmatic-check-for-reshaped-artifacts.md` — owns content verification;
  this owns "did every run happen, with the right flags".
- `2026-08-15-archive-stale-outputs-before-the-run-purge-them-after.md` — with the tree emptied
  first, a missing artifact is unambiguous instead of masked by a stale file of the same name.

## Scope boundary — artifacts, not prose

Library and experiment work only. The manuscript tree (`Spinoffs/papers/aquacal/`) is read-only
from this repo.
