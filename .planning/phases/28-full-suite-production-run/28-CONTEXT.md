# Phase 28: Suite Execution on Linux Machine - Context

**Gathered:** 2026-08-24
**Status:** Ready for planning
**Attempt:** 2 (attempt 1 ran 2026-08-20 at `rerun-freeze-01` and was superseded by Phase 29.1)

<domain>
## Phase Boundary

This phase executes the full experiment suite **once, end to end, off-repo**, on the Linux run
machine, at the frozen sha `rerun-freeze-02`. Phase 28 was never closed: attempt 1 surfaced four
defects, Phase 29.1 fixed them and cut a new frozen sha, and this is the re-execution the new
tag was cut for. The phase's success criteria in ROADMAP.md are deliberately freeze-agnostic —
they name "the frozen sha", not freeze-01 — so they apply unchanged to this attempt.

**The frozen sha:**

    tag object   533f79fbe1bf7022466e341cb4a4921f1e2575a5
    commit       7005a2771aa115e4f4c1284cec7e145739586a4a
    tag name     rerun-freeze-02

**In scope:** building the environment from the tag's own corrected install command, launching
the suite, and returning the artifacts with provenance intact.

**Not in scope:** grading the returned run (`check_rerun_gates.py`, the E2 sanity control, the
E7 before/after comparison) — that is Phase 29. Publishing the Zenodo results package — that is
Phase 29's RUN-05. Any source change: this phase runs a frozen tag and must not modify it.
</domain>

<decisions>
## Operational Decisions

These are rulings already made and recorded during Phase 29.1. They are not open questions.
A plan that contradicts one of them is wrong.

### Clone fresh — do not reuse the working copy (D5)

The run MUST start from a clean clone:

    git clone --branch rerun-freeze-02 https://github.com/McGrathLab/AquaCal.git

**Do NOT reuse `~/aquacal-frozen-rerun-freeze-02`.** Plan 29.1-08's `--smoke` verification ran
in that tree. `STATE_FILE` is derived from `RUN_EXPERIMENT_SUITE_DRY_RUN` and the short sha only
(`run_experiment_suite.sh:288-292`); `--smoke` does not enter it. A completed rehearsal therefore
leaves `run_experiment_suite_state.<sha>.tsv` holding 20 `complete … 0` lines, and **a real run
at that same sha would skip all 20 stages and produce nothing.** The dry-run path has an explicit
`.dryrun.tsv` separation for exactly this failure mode; `--smoke` has none.

A second reason the fresh clone matters: `experiments/results_e2_band` holds zero tracked files
at HEAD, and git does not track empty directories, so a fresh clone does not contain it at all.
That *absent* state is what the tag ships and what the gate expects (single `N/A`). A working
copy left in the *present-and-empty* state turns that one `N/A` into two `FAIL`s.

### Expect exactly three test failures — do not treat them as a regression (D4)

The tag was deliberately cut with a known, ruled-on 3-test failure. `pytest tests/` at this sha
reports:

    2407 passed, 26 skipped, 3 failed

    FAILED tests/unit/test_discard_accounting.py::test_matches_frozen_anchor
    FAILED tests/unit/test_optim_common.py::TestPerObservationDetailSinks::test_detail_sink_recomputed_geometry_matches_projector
    FAILED tests/unit/test_pipeline.py::TestSolverConfigSeedIsInert::test_matches_pre_change_anchor

All three are exact-equality anchor comparisons disagreeing at float noise — 1 ULP on a
`sqrt(dx²+dy²)`, rel. 1.4e-9 on a reprojection RMS, and 2.4e-16 on the off-diagonal *zeros* of an
identity rotation. They are deterministic (bit-for-bit reproducible in isolation) and are not a
threading artifact (unchanged under `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`).
Independently confirmed 2026-08-24 by the Phase 29.1 verification: same 3 failures, same node ids.

**No artifact of this phase may claim the suite is clean.** A run reporting 0 failures here is
the anomaly and must be investigated, not celebrated.

### Expect D1's eight provenance failures to return

`tests/unit/test_experiments_provenance.py` carries 8 pre-existing failures that reappear once
`experiments/results/` is repopulated by this run. They are parametrized over the artifacts
actually present in the committed results tree and assert provenance properties of the *previous*
run's output. Verified byte-for-byte identical at the branch base `89c2092`. Expected; not caused
by this phase.

### Set `PRELAUNCH_GATE_PYTHON` explicitly (D-28)

During 29.1's rehearsal the driver warned about the fallback and resolved `python` on `PATH`,
which *happened* to be the correct interpreter. Do not rely on that. Set it explicitly for the
production run so `interpreters_agree` is true by construction rather than by luck.

### Leave `SUITE_E2_RELEASE_CONFIG` unset (D-12)

That variable is the documented **Windows** escape hatch. On the Linux run machine the in-repo
default `experiments/configs/e2_release_linux.yaml` resolves correctly. Attempt 1 set it because
it ran from Windows; this attempt must not.

### Use no pre-flight override flags

Neither `--allow-nonempty-out` nor `--skip-e2` nor `--allow-frameset-mismatch`, in any form. If
the pre-flight refuses, archive the offending trees aside — as both attempt 1 and 29.1's
rehearsal did — rather than overriding the gate. The pre-flight refusing is a signal, not an
obstacle.

### `check_e2_band`'s `--smoke` quirk is known and NOT fixed (D6)

Its sibling-directory resolution does not honour `--smoke`. Left unfixed deliberately: changing
the script that judges every artifact, inside the freeze window, is a trade attempt 1 declined
and 29.1 declined again. Do not "fix" it during this phase — the tag is frozen.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning.**

### The rulings this phase inherits
- `.planning/phases/29.1-post-run-fixes-re-freeze/29.1-PREPUSH-AUDIT.md` §1 — the D4 ruling.
  The most important single section; it is stated first in that file for that reason.
- `.planning/phases/29.1-post-run-fixes-re-freeze/29.1-VERIFICATION-BAR.md` — the full
  diagnosis, the run A / run B distinction, the invocation-difference table vs attempt 1, and
  the five findings handed to 29.1-08 (D5, D6, D-28 among them).
- `.planning/phases/29.1-post-run-fixes-re-freeze/deferred-items.md` — D1 and D4 entries.
- `.planning/phases/29.1-post-run-fixes-re-freeze/29.1-FREEZE-RECORD.md` — what `rerun-freeze-02`
  is and how it was cut and verified.

### Attempt 1's evidence (do not overwrite)
- `.planning/phases/28-full-suite-production-run/freeze01-*` — attempt 1's returned artifacts.
  Artifacts are freeze-tagged by convention, so this attempt writes `freeze02-*` alongside them.
  Attempt 1's record stays in place; it is the evidence for why 29.1 existed.

### The procedure
- `experiments/HANDOFF.md` at the tag — the operator-facing run procedure, whose install command
  Phase 29.1 corrected to include the `dev` and `bench` extras the suite actually needs.
- `.planning/phases/27-frozen-single-sha-handoff-package/27-CONTEXT.md` — Phase 27 is this
  phase's declared dependency and defines the handoff package this run consumes.
</canonical_refs>

<specifics>
## Specific Ideas

- Build the environment by executing the tag's **own** install command verbatim, not a
  remembered one. 29.1's whole criterion 5 was that this command was wrong; the corrected form
  ships in the tag.
- Record the interpreter path and `pip freeze` into the returned artifacts as `freeze02-*`
  counterparts to attempt 1's files, so the two attempts are comparable line for line.
- The suite's own driver prints *"NOTHING THIS RUN PRODUCES IS EVIDENCE"* during `--smoke`.
  This phase's run is not a smoke run; make sure the distinction is unambiguous in the log
  that gets returned.
</specifics>

<deferred>
## Deferred / Flagged Upward

### Phase 29's success criterion 6 is unsatisfiable as written — needs a ruling

ROADMAP.md Phase 29 criterion 6 requires the Zenodo results package be published *"before the
2026-08-21 submission"* (RUN-05). That date has passed. This does not block Phase 28, but Phase 29
cannot be graded against that criterion as written, and the criterion should be amended — with an
explicit ruling recorded — rather than silently reinterpreted at the gate.

### Phase 29's two open items from attempt 1

Attempt 1 left the E7 before/after comparison (Phase 29 criterion 3) and the Zenodo package
(RUN-05) open, the latter deliberately deferred until after the re-freeze and re-run so the
archive is built from clean output. Both remain Phase 29's work, not this phase's.
</deferred>
