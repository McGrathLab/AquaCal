---
created: 2026-08-20T00:00:00.000Z
title: The frozen package's own install command omits two extras the suite requires — e3 dies without pytest, and two required manifest fields go null without psutil
area: experiments
resolves_phase: 27
files:
  - experiments/HANDOFF.md
  - experiments/e3_derived_quantities.py
  - tests/unit/test_experiments_e3_constants.py
  - pyproject.toml
---

Found on the Linux run machine on 2026-08-19, by plan 27-13's on-target smoke pass against
`rerun-freeze-01`. **Recorded as a deviation rather than fixed** (author's ruling, same day):
the SoftwareX submission is 2026-08-21 and the production run needed to start that night. The
run itself is unaffected — the environment was corrected on the target before launching.

## The defect

`experiments/HANDOFF.md` §1.2 tells the operator to build the run environment with:

    python -m pip install -e .

That installs **runtime dependencies only**, and the suite needs two packages that are declared
as *extras*:

| Package | Extra | What breaks without it |
|---|---|---|
| `pytest` | `dev` | **e3 dies outright**, both `--check` and `--force` |
| `psutil` | `bench` | `cpu_count_logical` and `ram_total_bytes` are `None` |

The working command is:

    python -m pip install -e ".[dev,bench]"

## Why each one bites

**pytest.** `e3_derived_quantities.py:243` imports `DECLARED_CONSTANTS` from
`tests/unit/test_experiments_e3_constants.py`, and that module does `import pytest` at line 34.
So a **§3-facing artifact generator depends on a test module, which depends on a test runner.**
In a clean runtime-only environment e3 exits 1 on both passes with `ModuleNotFoundError: No
module named 'pytest'`, taking `code_constants.csv`, `newton_iterations.csv`, `cpr_grouping.csv`,
`e3_provenance.json` and the LaTeX fragments with it.

**psutil.** `src/aquacal/io/benchmark.py:152-158` populates `cpu_count_logical` and
`ram_total_bytes` from psutil inside a `try/except`, leaving both `None` when it is absent. Both
are in `REQUIRED_MANIFEST_FIELDS`, so `gate3_run_manifest_fields` FAILs — a Gate 3 failure caused
by a missing optional package rather than by anything about the run.

## Why it did not show up on Windows

The Windows development environment has pytest installed (the suite is run there constantly) and
psutil available, so both dependencies were satisfied invisibly. This is exactly the
Linux-only-failure class D-05 put the verification venue on the target to catch, and it is the
strongest argument for keeping that step.

## The fix, when the freeze is not in the way

1. **Minimum, doc-only:** correct `HANDOFF.md` §1.2 to `pip install -e ".[dev,bench]"`, with a
   sentence saying why each extra is needed. Cut the next `rerun-freeze-NN`. Zero numerical risk.
   *This is the whole fix for reproducibility* — the code works, the instructions do not.
2. **Better, code:** move `DECLARED_CONSTANTS` out of `tests/unit/test_experiments_e3_constants.py`
   into a non-test module (e.g. `experiments/_e3_constants.py`) and have the test import *from*
   there. That inverts the dependency so a production stage no longer needs a test runner. Deferred
   because it touches the source of §3-facing constants, and the full suite must be re-run behind
   it.
3. **Consider:** promoting `psutil` from the `bench` extra into runtime dependencies, since two
   `REQUIRED_MANIFEST_FIELDS` depend on it. The alternative is a non-psutil fallback
   (`os.cpu_count()`, `/proc/meminfo`) so the required fields are never null on Linux.

Do **not** weaken `gate3_run_manifest_fields` to tolerate the nulls — the gate was right.

## Related

- `experiments/HANDOFF.md` §2.8 and `27-PREPUSH-AUDIT.md` — the roll-up-vs-exit-code ruling from
  the same phase.
- `27-ONTARGET-VERIFICATION.md` — the on-target record this was found in.
