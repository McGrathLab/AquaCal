---
created: 2026-08-15T00:00:00.000Z
title: No artifact records the environment a run happened in, and two provenance fields actively misreport it — aquacal_version and the OpenCV build
area: experiments
files:
  - experiments/_io.py
  - experiments/check_rerun_gates.py
  - src/aquacal/io/benchmark.py
---

> **Narrowed 2026-08-15 after stress-testing the run-book todo.** The original framing here —
> "nothing enforces one sha" — was **wrong**. `check_rerun_gates.py` **Gate 3** already asserts that
> every `git_sha` across a run is identical, and `experiments/rerun_19_3.sh` already freezes one
> commit across every stage it covers. The real defect is *coverage*: the band runs and E2 sit
> outside the queue, so Gate 3 never saw them. That is owned by
> `2026-08-15-make-the-suite-driver-cover-every-invocation.md`.
>
> **What remains here is narrower and still real:** the environment capture, and two recording
> defects Gate 3 does not look at. Do not re-implement sha enforcement.

## Problem

The milestone's premise is a single source of truth: every experiment from one library build on
one machine under one OpenCV, retiring the six-sha provenance spine the goal-4 audit found
(F-001, F-002). Sha *identity* is enforced where the queue reaches. **What is nowhere recorded is
the environment that produced the run, and two fields actively misreport it.**

For reference, the spine the audit found — note that the three band records are the ones outside
the queue's coverage:

| artifact | recorded sha | date |
|---|---|---|
| `benchmark.json` (E2 real rig) | `6c7f930` | 2026-07-31 |
| E1/E3/E5/E6 provenance | `2a623f9` | 2026-08-04 |
| `e5_seed_band_provenance.json` | `2a2f0fa` | 2026-08-06 |
| `e7_seed_band_provenance.json` | `b13a3e0` | 2026-08-07 |
| `reconstruction_bootstrap.json` | `72dbc36` | 2026-08-05 |
| `linux32gb_scope.json` | `d27bda7` | 2026-08-11 |

Nothing detected that at run time. It took an audit.

**Two related defects the same fix should close.**

1. **`aquacal_version` is a stale tag string, not the code that ran.** Every pre-2.0.0 artifact
   records `1.8.0` — the last released tag at run time — for commits 11 and 15 days *after* that
   tag. Two different commits carry the same version string (F-002). `git_sha` is the only usable
   anchor, and the version field actively misleads.
2. **The OpenCV build is under-recorded.** PyPI ships `4.13.0.90` and `4.13.0.92`; both report
   `cv2.__version__ == "4.13.0"`, which is all the Windows record stored. Any difference between
   those builds is unaccounted for.

## Solution

- **Emit one suite-level manifest**, once per full-suite run: git sha, `git describe`, whether the
  tree was dirty, OS and kernel, Python, NumPy, SciPy, OpenCV **including the PyPI build suffix**,
  machine identifier, and the UTC start time.
- **Do not re-implement sha agreement** — Gate 3 in `check_rerun_gates.py` already does it, and
  does it better than a per-experiment assertion would, because it compares across the whole run
  rather than each script against a file. Extend Gate 3 to cover the environment fields too, so one
  gate owns "was this one run on one machine".
- **Record the dirty-tree state.** A sha is not provenance if the tree had uncommitted changes;
  the previous convention ("commit nothing while a run is in flight") is a rule with no check
  behind it.
- **Stop recording `aquacal_version` as the last released tag.** Either resolve it from the
  installed distribution and label it as such, or drop it in favour of the sha. Two commits must
  never share a version string again.
- Extend `check_rerun_gates.py` to verify the manifest is present and internally consistent
  before the suite's results are treated as publishable.

**Tag the pre-run commit before starting** (`pre-rerun-baseline` or similar). The re-run replaces
committed artifacts; without a tag on the prior state, no movement can be explained afterwards.
This costs one command and is the difference between "numbers moved and we understand why" and
"numbers moved".

## Do not

- Do not build a full orchestrator. The queue script already exists as a pattern; this is a
  manifest plus an assertion, not a workflow engine.
- Do not make the assertion a warning. A provenance mismatch that only warns is a provenance
  mismatch that ships — that is precisely what happened last time.
- Do not retrofit the manifest onto the committed artifacts. They record what they record; the
  audit has already mapped them. This is for the new suite.

## Related

- Audit findings **F-001** (six shas, not one anchor) and **F-002** (two commits sharing
  "1.8.0"), `Spinoffs/papers/aquacal/AUDIT-goal4.md` Pass A.
- **Sole owner** of the `.90` vs `.92` OpenCV build ambiguity. Its source todo,
  `2026-08-12-isolate-opencv-detection-drift-4-13-vs-4-14.md`, was **closed 2026-08-15** (moved to
  `todos/done/`) — the drift question is moot while the library is pinned to `opencv-python==4.13.*`,
  and this was the only live remnant. Recording the PyPI build suffix here is what keeps it closed.
- `2026-08-15-suspend-programmatic-check-for-reshaped-artifacts.md` — the manifest is what makes
  a hand-verified run auditable later.

## Scope boundary — artifacts, not prose

Library and experiment work only. The manuscript tree (`Spinoffs/papers/aquacal/`) is read-only
from this repo. Where a fix has a manuscript consequence, emit the artifact and record the
derivation in `.planning/MANUSCRIPT-FINDINGS.md`; the prose is the manuscript session's.
