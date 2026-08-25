# 28-RUN-RECORD — the v2.1 full-suite production run, attempt 2

**This is the document Phase 29 opens first.** Everything in it was measured during Phase 28 and
recorded in `28-03-SUMMARY.md`, `28-04-SUMMARY.md` and `28-05-SUMMARY.md`. Nothing here is
recalled.

---

## Header

| | |
|---|---|
| **Attempt** | 2 (attempt 1 was 2026-08-20 at `rerun-freeze-01` / `3ab9c13`) |
| **Run** | 2026-08-25T00:47:07.773Z → 2026-08-25T06:48:28.378Z |
| **Tag** | `rerun-freeze-02` (annotated, `533f79fb`), pushed to `origin` |
| **Sha** | `7005a2771aa115e4f4c1284cec7e145739586a4a` (`v2.0.1-346-g7005a27`) |
| **Clone** | `/home/tlancaster/aquacal-frozen-rerun-freeze-02-prod` — fresh clone at the tag, detached HEAD |
| **Environment** | `aquacal-freeze02-prod` (conda) |
| **Machine** | `EBB-MCGRATH-D04`, Linux 6.8.0-136-generic, 32 logical CPUs, 31.06 GiB RAM |
| **Profile** | `full` (production). Concurrency pooled, 4 wide (D-52) |

The clone is a **fresh** one, not `~/aquacal-frozen-rerun-freeze-02` — that working copy carries a
`--smoke` state file at this same sha from plan 29.1-08's own verification, and a real run there
would have skipped all 20 stages and produced nothing (D5).

---

## The invocation, verbatim

    source /home/tlancaster/anaconda3/etc/profile.d/conda.sh
    conda activate aquacal-freeze02-prod
    cd /home/tlancaster/aquacal-frozen-rerun-freeze-02-prod

    export PRELAUNCH_GATE_PYTHON="/home/tlancaster/anaconda3/envs/aquacal-freeze02-prod/bin/python"

    nohup bash experiments/run_experiment_suite.sh \
      > "/home/tlancaster/suite_run_freeze02.log" 2>&1 &
    disown

The log lands **outside the clone and outside the output tree** — writing it into
`experiments/results/` before launch would trip the driver's own non-empty-tree refusal.

The operator issued this through `/home/tlancaster/launch_freeze02.sh`, a fail-closed wrapper that
re-checks six preconditions (tracked tree clean, no real state file, output trees absent, `SUITE_`
namespace empty, `which python` identical to the production env interpreter, `aquacal.__file__`
inside the clone), refuses to launch if any fails, refuses to overwrite an existing log, exports
`PRELAUNCH_GATE_PYTHON`, and then issues the identical `nohup` line. **No check was overridden and
no flag was added** — the wrapper strengthens the precondition rather than relaxing it.

### Deliberately left unset

| Variable / flag | Ruling | Consequence |
|---|---|---|
| `SUITE_E2_RELEASE_CONFIG` | D-12 | driver resolved the in-repo default `experiments/configs/e2_release_linux.yaml` |
| `SUITE_DISPATCH_LOG` | B1 | criterion 3 is a *derived* argument — see below |
| `SUITE_SERIAL` | — | pooled 4-wide |
| `SUITE_OUT_DIR`, `SUITE_STATE_DIR` | — | real output and state paths, not `.dryrun.*` |
| `SUITE_STAGE_PYTHON` | — | stage interpreter from the activated env |
| `RUN_EXPERIMENT_SUITE_DRY_RUN` | — | real run, not a dry run |
| `--allow-nonempty-out`, `--skip-e2`, `--allow-frameset-mismatch` | 28-CONTEXT | **none used** — `grep -cE` over the log returns 0. The pre-flight was satisfied, not bypassed. |

`PRELAUNCH_GATE_PYTHON` **was** set explicitly (D-28). The log records
`gate=…/envs/aquacal-freeze02-prod/bin/python (rung: PRELAUNCH_GATE_PYTHON override)`.

E2 ran against the real rig, not synthetic-only: `preflight: E2 frameset identity check PASSED`.

---

## The three hard signals

| # | Signal | Required | Measured | |
|---|---|---|---|---|
| 1 | End-of-run completeness roll-up | `0 FAIL` | **`TOTAL: 176 PASS, 7 N/A, 0 FAIL`** | **GREEN** |
| 2 | `STAGE FAILED` lines | 0 | **0** | **GREEN** |
| 3 | State file `complete` at exit 0 | 20, none non-zero | **20**, non-zero filter empty | **GREEN** |

**The exit code was not used as the verdict.** The driver exited non-zero, which is the designed
behaviour of a *healthy* run under D-01: the queue continues past a per-stage gate finding so
every stage's measurements are still taken, and the non-zero exit exists precisely so the run
cannot be mistaken for green. F-001 — the failure this convention was built against — was a run
that **exited 0** while a band CSV was never produced.

Zero `NOT FOUND` lines in the roll-up.

### The 17 `GATE FAIL` findings

One per stage from 3 to 20, excluding `e4` (stage 17):

    fd_jacobian(3)  e1(4)  e7(5)  e5(6)  e2_production(7)  e6_repeat1(8)  e3(9)
    reconstruction_bootstrap(10)  e2_timing(11)  e2_memory(12)  e7_band(13)
    e5_band(14)  e2_band(15)  e1_band(16)  e6_band(18)  e7_focal_standoff(19)
    e4_repeat(20)

`check_rerun_gates.py` evaluates every experiment against whichever out-dir the invoking stage
used, so a stage finishing early necessarily sees artifacts later stages have not written yet, and
the four stages writing to sibling trees see trees holding only their own output. The mechanism is
visible in the log as a monotonic decline in the per-stage FAIL count over `experiments/results`:
**89 → 31 → 25 → 13 → 8 → 8 → 8 → 8 → 7 → 7 → … → 0.** Stage 17 (`e4`), the last gate to run
against that tree, reports `TOTAL: 112 PASS, 8 N/A, 0 FAIL` and is for that reason the one stage
with no finding.

Attempt 1 produced 18 findings: the same 17 plus `e4`, plus a `ROLL-UP FAIL`.

Nothing in `check_rerun_gates.py`, `suite_expectations.json` or the driver was edited.

---

## Roll-up and post-run gate totals

| Source | Total |
|---|---|
| The run's own end-of-run roll-up (`freeze02-rollup.txt`) | `TOTAL: 176 PASS, 7 N/A, 0 FAIL` |
| Post-run re-run of the gate over the returned tree (`freeze02-gates-full.txt`) | `TOTAL: 176 PASS, 7 N/A, 0 FAIL` |
| Reference | `176 PASS, 7 N/A, 0 FAIL` |

**The two agree exactly.** The post-run capture contains **zero** `[FAIL]` lines, and the gate
script itself exited 0.

The reference figure was measured by phase 29.1 over the **freeze-01 output tree** with the
freeze-02 gate script — it is a reference, not a target. **Nothing was tuned toward it.** No gate,
manifest, expectation or driver file was edited between the tag being cut and this run, and the
production clone's tracked tree is byte-identical to `rerun-freeze-02` (`git diff --stat HEAD`
over `src/` and the driver scripts prints nothing).

Attempt 1's roll-up read `175 PASS, 7 N/A, 2 FAIL`.

---

## The 20-stage timing table

Derived from the state TSV's ISO stamps — the only per-stage timing record this run has. Full
version at `freeze02-stage-timing.txt`.

| Stage | idx | Duration | Exit | Attempt 1 | Delta |
|---|---:|---:|---:|---:|---:|
| `preflight` | 1 | 0 m 01 s | 0 | 0 m 01 s | −0 s |
| `prelaunch_probe` | 2 | 0 m 00 s | 0 | 0 m 00 s | +0 s |
| `fd_jacobian` | 3 | 0 m 02 s | 0 | 0 m 02 s | +0 s |
| `e1` | 4 | 1 m 51 s | 0 | 1 m 47 s | +4 s |
| `e7` | 5 | 2 m 09 s | 0 | 2 m 11 s | −1 s |
| `e5` | 6 | 8 m 34 s | 0 | 8 m 34 s | −0 s |
| `e2_production` | 7 | 25 m 55 s | 0 | 25 m 53 s | +1 s |
| `e6_repeat1` | 8 | 36 m 51 s | 0 | 36 m 48 s | +3 s |
| `e3` | 9 | 0 m 07 s | 0 | 0 m 07 s | −0 s |
| `reconstruction_bootstrap` | 10 | 0 m 11 s | 0 | 0 m 11 s | −0 s |
| `e2_timing` | 11 | 20 m 11 s | 0 | 19 m 44 s | +27 s |
| `e2_memory` | 12 | 19 m 24 s | 0 | 20 m 05 s | −41 s |
| `e7_band` | 13 | 21 m 52 s | 0 | 21 m 46 s | +6 s |
| `e5_band` | 14 | 52 m 56 s | 0 | 53 m 00 s | −4 s |
| `e2_band` | 15 | 1 h 13 m 10 s | 0 | 1 h 12 m 40 s | +30 s |
| `e1_band` | 16 | 33 m 08 s | 0 | 34 m 20 s | −1 m 12 s |
| `e4` | 17 | 44 m 07 s | 0 | 42 m 58 s | +1 m 09 s |
| `e6_band` | 18 | **3 h 36 m 01 s** | 0 | **3 h 35 m 24 s** | +37 s |
| `e7_focal_standoff` | 19 | 0 m 00 s | 0 | 0 m 00 s | −0 s |
| `e4_repeat` | 20 | 22 m 52 s | 0 | 23 m 32 s | −40 s |
| **TOTAL** | | **6 h 01 m 21 s** | | **6 h 00 m 21 s** | **+1 m 00 s** |

No material divergence. Largest single-stage deltas are `e1_band` at −1 m 12 s and `e4` at
+1 m 09 s; every other stage is within ±41 s. `e6_band` remains the critical path at 60% of the
run. The two stages no rehearsal at any scale exercises — `e7_focal_standoff` and `e4_repeat` —
both completed at exit 0.

### Three published estimates that are Windows-derived upper bounds

**None of these may be used as a timeout, or as evidence that a faster finish skipped work:**

- `experiments/HANDOFF.md` §1.6's **15–16 h** for the whole suite (measured here: 6 h 01 m).
- `e6_band`'s **8.9 h** estimate (measured here: 3 h 36 m).
- E2's ***48–87 min per seed*** calibration (measured here: ≈24 min/seed).

All three are labelled as Windows-box figures in `suite_expectations.json → wall_clock_summary`.

---

## ROADMAP success criteria, mapped to returned artifacts

### Criterion 1 — *"Returned artifacts include a result file for every experiment … with none missing"*

**Evidenced by** the `0 FAIL` completeness roll-up at `--profile full`
(`freeze02-rollup.txt`, and independently re-measured in `freeze02-gates-full.txt`). `--profile
full` asserts **row counts**, not merely existence. Zero `NOT FOUND` lines.

### Criterion 2 — *"The returned run manifest records exactly one `aquacal_version`/git sha across all artifacts"*

**Evidenced by** `gate3_git_sha_consistency` PASS —
*"every artifact carries the same git_sha (7005a2771aa115e4f4c1284cec7e145739586a4a)"* — plus
`experiments/results/run_manifest.json`:

| Field | Value |
|---|---|
| `git_sha` | `7005a2771aa115e4f4c1284cec7e145739586a4a` |
| `git_describe` | `v2.0.1-346-g7005a27` |
| `aquacal_version_declared` | `2.0.1` |
| `installed_distribution_version` | `2.0.1` — agrees with the declared version, so the run did not import from a stale editable install elsewhere |
| `cpu_count_logical` | `32` |
| `ram_total_bytes` | `33351241728` |

Also PASS: `gate3_run_manifest_fields` (*"all 17 required environment fields are present and
non-null"*) and `gate3_run_manifest_clean_tree` (*"the working tree was clean when this run
started"*).

**Note the field name.** It is `aquacal_version_declared`, not `aquacal_version`; a literal
lookup of the latter returns `None` and must not be read as a null field.

`cpu_count_logical` and `ram_total_bytes` are the two fields the `bench` extra populates, and the
two that came back **null** on attempt 1 before 29.1-04 corrected `HANDOFF.md` §1.2 to install
`.[dev,bench]`. Both are populated here.

### Criterion 3 — *"The set of returned invocations matches the driver's coverage from Phase 26 one for one"*

Copied in full from `28-03-PLAN.md` so this record stands alone.

With `SUITE_DISPATCH_LOG` deliberately unset (**B1** — invocation parity with the run whose
evidence was accepted), **no returned artifact enumerates argv directly.** Phase 29's verifier
should grade this criterion on the argument that actually exists rather than hunting for a
dispatch record.

*What is not available:* the run log does not echo stage argv — measured over attempt 1's
preserved 425 KB log, `python -u -m` occurs exactly **twice**, both inside the INTERPRETERS
banner. The per-stage logs open with the driver's banner (`>>> STAGE 16/20: e1_band starting`)
then carry the stage's stdout; they do not echo argv either.

The criterion is established by a **two-part argument**, both parts resting on returned artifacts:

1. **Coverage of the stage set.** `run_experiment_suite.sh:541-562` defines a 20-element `STAGES`
   array. `experiments/suite_expectations.json` carries the same 20 ids, and
   `tests/unit/test_suite_stage_list.py` asserts both directions and proves the array is a
   topological order of the manifest's `depends_on` edges. The returned state TSV carries a
   `start` and a `complete` line for each of those 20 names, with exit column `0`. The driver
   dispatches each stage exactly once from that array, so **20 completions at exit 0 means every
   stage in the driver's coverage ran, once.**
2. **Coverage of what those stages emit.** The completeness roll-up at `--profile full` reaches
   `0 FAIL`. Every artifact entry in `suite_expectations.json` is attributed to the stage that
   writes it, and `full` asserts row counts, not merely existence. An invocation that was skipped,
   truncated or silently redirected cannot leave a complete, correctly-sized artifact set behind —
   and the roll-up is the only check that judges what is **absent**, which is exactly what F-001
   lacked.

Taken together, (1) proves every stage in Phase 26's driver coverage was dispatched and returned
success, and (2) proves each stage's declared outputs landed with the declared shapes. Both parts
read the same manifest that *defines* Phase 26's coverage, so the "one for one" comparison is
against the right set by construction.

**The residual gap, stated honestly.** Neither part observes the argv of a *sub-invocation within*
a stage — E3's `--check` then `--force`, `e2_band`'s config emit plus its three per-seed
calibrations, `e4_repeat`'s per-cell loop and its splice. Those are evidenced indirectly, by the
artifacts they produce with their asserted row counts (`benchmark_grid_repeat.csv` at 6 rows,
`exp1_band.csv` at 256, `interface_ablation_band.csv` at 480) and by the stage's exit code.
`SUITE_DISPATCH_LOG` is the one mechanism that would close this gap directly; it was left unset by
the locked decision **B1**, on the reasoning that provenance parity with attempt 1 is worth more
than upgrading one criterion from derived to direct. **This paragraph is the record of that
trade.**

---

## The environment record

| | Attempt 2 | Attempt 1 |
|---|---|---|
| Interpreter | `/home/tlancaster/anaconda3/envs/aquacal-freeze02-prod/bin/python` | `…/envs/aquacal-freeze01/bin/python` |
| `aquacal.__file__` | `/home/tlancaster/aquacal-frozen-rerun-freeze-02-prod/src/aquacal/__init__.py` | `…/aquacal-frozen-rerun-freeze-01/src/aquacal/__init__.py` |
| Python | 3.11.15 | 3.11.15 |
| `cv2` | **4.13.0** (`opencv-python` 4.13.0.92) | **4.13.0** (4.13.0.92) |
| `numpy` | **2.4.6** | **2.4.6** |
| `scipy` | **1.17.1** | **1.17.1** |
| Machine | `EBB-MCGRATH-D04`, Linux 6.8.0-136-generic | same box, same kernel |

Install command, read out of the tag (`freeze02-install-command.txt`):

    python -m pip install -e ".[dev,bench]"

**`pip freeze` taken after the run is byte-identical to the pre-launch capture** — the environment
did not move under the run, which is what makes `freeze02-pip-freeze.txt` a valid record of what
actually executed.

### The two attempts' environments are NOT byte-identical — and this matters

`diff freeze01-pip-freeze.txt freeze02-pip-freeze.txt` reports six changed entries. One is the
editable `aquacal` sha, as expected. **The other five are dev tooling that drifted because attempt
2's environment was built by a fresh resolve:**

| Package | Attempt 1 | Attempt 2 |
|---|---|---|
| `filelock` | 3.32.3 | 3.32.4 |
| `packaging` | 26.2 | 26.3 |
| `platformdirs` | 4.11.3 | 4.11.4 |
| `python-discovery` | 1.5.2 | 1.5.3 |
| `ruff` | 0.16.3 | 0.16.4 |

**None is in the numerical stack.** `numpy`, `scipy` and `opencv-python` are identical to the
patch level across both attempts, which is the property that licenses comparing the two runs'
numbers at all. Recorded here so Phase 29 does not have to rediscover it, and so nobody claims the
environments were identical when they were not.

---

## Test-suite caveat (D4) — stated, not softened

**The full test suite is NOT clean at this sha.** Measured on this machine before launch
(`freeze02-pytest-prelaunch.txt`, `PYTEST_EXIT=1`):

    3 failed, 2407 passed, 26 skipped, 30 warnings in 1638.58s (0:27:18)

    FAILED tests/unit/test_discard_accounting.py::test_matches_frozen_anchor
    FAILED tests/unit/test_optim_common.py::TestPerObservationDetailSinks::test_detail_sink_recomputed_geometry_matches_projector
    FAILED tests/unit/test_pipeline.py::TestSolverConfigSeedIsInert::test_matches_pre_change_anchor

**Three is the expected, ruled-on state. Zero or four would both be anomalies.**

All three are exact-equality comparisons (`==` / `assert_array_equal`, never `pytest.approx`)
against anchors captured on Windows, missing by 1 ULP to rel. 1.4e-9. They are byte-identical to
`rerun-freeze-01` and fail there too — this is the first `pytest` evaluation of those anchors on
Linux, not a regression of this phase or this run. Nothing was deselected, xfailed, skipped,
regenerated or loosened. Ruled on explicitly in the `rerun-freeze-02` tag annotation and in
`29.1-PREPUSH-AUDIT.md` §1; diagnosed in `29.1-VERIFICATION-BAR.md`.

### D1 — eight provenance failures are expected to reappear

`tests/unit/test_experiments_provenance.py` reported 8 failures under D1. They did not appear in
the 29.1-07 verification bar, and **they were not fixed — they went dormant.** Plan 29.1-06 moved
the 2026-08-20 output to `experiments/freeze01_run_output/`, so
`tests/unit/_baseline_paths.resolve_results_dir()` — which prefers the live tree only while it
holds a file — fell back to `experiments/pre_rerun_baseline/`.

`experiments/results/` **is repopulated as of this run**, so the fallback no longer applies.
29.1-VERIFICATION-BAR predicted this in terms: *"the 8 failures return the moment a re-run
repopulates `experiments/results/`, which is the next thing that happens after the tag."*

**They are not caused by this run.** Phase 29's business.

---

## Returned-artifact index

### Preserved outside the repository

| Artifact | Bytes | Mode | sha256 |
|---|---:|---|---|
| `/home/tlancaster/rerun-freeze-02-output.tar.gz` | 31,838,334 | `r--r--r--` | `3b21b88323bd7c04e9712ae2742cc09d423f925620e729ea7bbe2d391c9f030e` |
| `/home/tlancaster/suite_run_freeze02.log.preserved` | 430,438 | `r--r--r--` | `5bdc6090df5741c86c225a1a14a4eee05f344a71f5d39ade7e50bd9dcf46915e` |

Attempt 1's counterparts are 31,845,719 B and 425,119 B, still `r--r--r--`, and were **re-hashed
during Phase 28 and proven unmodified** against `rerun-freeze-01-output.sha256`.

### The nine paths in the archive

| Path | Files |
|---|---:|
| `experiments/results` | 152 |
| `experiments/results_e2_band` | 136 |
| `experiments/results_e2_invocations` | 119 |
| `experiments/results_e2_timing` | 6 |
| `experiments/results_e2_memory` | 6 |
| `experiments/results_e4_repeat` | 4 |
| `experiments/run_experiment_suite_state.7005a27.tsv` | 1 |
| `experiments/run_experiment_suite_state.7005a27.failures.txt` | 1 |
| `experiments/run_experiment_suite_state.7005a27.stagelogs` | 36 |
| **Total** | **461** |

Completeness proven by count: `tar tzf … | grep -v '/$' | wc -l` = `find <nine paths> -type f |
wc -l` = **461**, with exactly **9** distinct top-level `experiments/<name>` entries.

**A large share of this bulk is gitignored under DATA-01b and lives only in the archive** —
`reconstruction_errors.csv`, `reprojection_residuals.csv`, `all_observation_depths.csv` (≈11 MB)
and the per-invocation trees are never committed. A clone of the results branch will not contain
them.

**507 vs 461, reconciled.** Attempt 1's archive held 507 files. The 46-file difference is entirely
rehearsal residue attempt 1 swept in and this corrected nine-path list excludes by construction:
`results_smoke_e2_band` (4), `results_smoke_e2_invocations` (4), and the three
`…3ab9c13.dryrun.*` artifacts (38). 507 − 46 = 461, and **every one of the six output trees and
three state artifacts has an identical file count in both attempts, path for path.**

### The `freeze02-*` evidence set, in this directory

| File | Producer |
|---|---|
| `freeze02-install-command.txt` | 28-01 |
| `freeze02-env.txt` | 28-01 |
| `freeze02-pip-freeze.txt` | 28-01 |
| `freeze02-pytest-prelaunch.txt` | 28-01 (D4 confirmation) |
| `freeze02-prelaunch-assertions.txt` | 28-02 |
| `freeze02-rollup.txt` | 28-03 |
| `freeze02-stage-timing.txt` | 28-03 |
| `freeze02-tree-state-at-handoff.txt` | 28-04 |
| `freeze02-archive-manifest.txt` | 28-04 |
| `rerun-freeze-02-output.sha256` | 28-04 |
| `freeze02-gates-full.txt` | 28-05 |

Attempt 1's `freeze01-*` set sits beside it, unmodified, so the two attempts compare line for
line.

---

## Differences from attempt 1

| Attempt 1 (`rerun-freeze-01`) | Attempt 2 (`rerun-freeze-02`) | Why |
|---|---|---|
| `HANDOFF.md` §1.2 said `pip install -e .` | `pip install -e ".[dev,bench]"` | **29.1-04.** The omission killed e3 outright and nulled two required manifest fields on attempt 1. Both are populated here. |
| E4's real-rig row published a null guard count → `gate1_guard_count` FAIL | Publishes the **198** above-water corners E2 measured; the gate exempts `record_source="pipeline"` rows and names the exemption in its own PASS line | 29.1-01 / 29.1-05 |
| `e1_seed_band_degeneracy_breakdown.json` expected by three manifests, produced by nothing → completeness FAIL | Unclaimed from all three manifests; the expectation no longer generates a result line | 29.1-02 |
| `degenerate_observations.csv` / `all_observation_depths.csv` PASS-by-absence at the wrong `dir` | Machine-evaluated predicate at `results_e2_invocations/e2_classification` | 29.1-09 |
| `experiments/results/` shipped populated in the tag | Moved to `experiments/freeze01_run_output/`; the tag ships an empty output tree | 29.1-06 — the pre-flight requires it |
| Windows-shaped invocation (`SUITE_E2_RELEASE_CONFIG` set, `PRELAUNCH_GATE_PYTHON` at a `.exe`) | Linux-native: config default resolves, gate interpreter an absolute conda path | D-12 / D-28 |
| Gate roll-up: **175 PASS / 7 N/A / 2 FAIL** | **176 PASS / 7 N/A / 0 FAIL** | 29.1-GATE-BEFORE-AFTER.md |

### Still open and deliberately unfixed inside the freeze

- **D6** — `check_e2_band`'s sibling-directory resolution ignores `--smoke`. Irrelevant to a
  production run, which writes to `experiments/results` and `experiments/results_e2_band` anyway.
- **E7 band overwrite hazard** — `e7_interface_ablation.py`'s band carries the same hazard 29.1-02
  fixed at E1. Measured 2026-08-24: it does **not** fire in the production run, because
  `run_stage_e7_band` (`run_experiment_suite.sh:1522`) passes no `--force` and `force=False`
  reaches the call. **Residual risk: one manual `--force` band run at E7 fires it — do not run
  E7's band by hand.**
- **D5** — `HANDOFF.md` still carries no warning about rehearsing with `--smoke` at the sha you
  are about to run for real. That is why the fresh-clone rule is carried by the plan rather than
  by the tag.

---

## The Phase 28 / Phase 29 boundary (A1)

This phase **preserved, captured and checksummed**. It did **not**:

- create or push a `results/rerun-freeze-02` branch — the production clone has **no** branch
  matching `results/*` and is still on a detached HEAD;
- commit the output tree;
- **grade** the run;
- run the E2 sanity control (seed 42 vs seed 42, ~1e-8) or the E7 before/after ablation
  comparison;
- touch Zenodo.

RUN-03, RUN-04 and RUN-05 all map to **Phase 29** in `REQUIREMENTS.md`, and `28-CONTEXT.md`'s
in-scope list stops at *returning the artifacts with provenance intact*. The evidence capture, by
contrast, could not be deferred — it had to be read while the tree was still pristine.

Nothing was pushed from the production clone.

---

## Open items handed forward

1. **D1's eight `test_experiments_provenance.py` failures are expected to reappear** now that
   `experiments/results/` is repopulated. Predicted, diagnosed, and not caused by this run.
2. **D4's three exact-equality anchor failures** remain as ruled on. Three is the expected count.
3. **Phase 29's success criterion 6 is unsatisfiable as written.** It requires the Zenodo results
   package to be published *"before the 2026-08-21 submission"* (RUN-05). **That date has
   passed** — this run finished 2026-08-25. The criterion needs re-dating or re-scoping by the
   author before Phase 29 can close against it. Flagged upward here rather than silently failed.
4. **The E7 before/after ablation comparison** (Phase 29 criterion 3 / attempt 1's open
   success criterion 3) is still outstanding and is now unblocked — this run produced the "after"
   side.
5. **The Zenodo results package (RUN-05)** was deliberately deferred until after the re-freeze and
   re-run so the archive is built from clean output. That precondition is now met.
