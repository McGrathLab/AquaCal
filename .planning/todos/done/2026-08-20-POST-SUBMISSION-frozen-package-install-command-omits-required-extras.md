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

---

## Resolved 2026-08-24 — OPTION 1 TAKEN, options 2 and 3 deliberately left open (D-11)

Phase 29.1, plan `29.1-04`. The deferral recorded above ("record, do not refreeze", author's
ruling 2026-08-19, with the SoftwareX submission at 2026-08-21 and the production run needing to
start that night) is **discharged here**: this phase cuts `rerun-freeze-02`, so the freeze is no
longer in the way.

**Option 1 taken in full.** `experiments/HANDOFF.md` §1.2 now instructs:

```bash
python -m pip install -e ".[dev,bench]"
```

with a sentence per extra naming what breaks without it — `dev` because a §3-facing artifact
generator imports `DECLARED_CONSTANTS` from a test module which imports the test runner, so e3
exits 1 on both passes and takes five artifacts with it; `bench` because two
`REQUIRED_MANIFEST_FIELDS` are populated from `psutil` inside a `try/except` and go null without
it, failing `gate3_run_manifest_fields` for a reason that has nothing to do with the run. The
dependency table in the same section was extended so the table and the command agree, and the
section now records that this was found on the Linux run machine on 2026-08-19 and why it was
invisible on Windows.

**Every other install site in the shipped tree was ruled on, not just §1.2** — the second half of
D-11. 26 sites across 17 files, each with an audience, a ruling and a reason, in
`.planning/phases/29.1-post-run-fixes-re-freeze/29.1-INSTALL-SITES.md`. One `corrected` (this
defect). Five ruled `correct as-is — not a first install`: the `--no-deps` metadata-refresh
commands in `experiments/README.md` and `experiments/prelaunch_gate.sh`, and the prose references
in `_run_manifest.py`, `benchmark.py` and `test_benchmark.py`. **Those must not gain extras** —
`--no-deps` is the whole point of those commands, and adding extras would change what they do.
The rest are CI, contributor and PyPI end-user installs whose extra sets are right for their
audience. A "no change" ruling carries its reason so nobody re-opens the question.

**Verified by execution, not by a diff on a string** (D-11's own standard). A fresh conda
environment `aquacal-freeze02-cleanenv` (Python 3.11.15) was built and installed using the command
read *out of the corrected file*: pytest 9.1.1 and psutil 7.2.2 both arrived,
`capture_environment()` returned `cpu_count_logical=32` and `ram_total_bytes=33351241728` instead
of two `None`s, and e3 exited **0** on both `--check` (against `experiments/results`) and
`--force` (into a scratch directory outside `experiments/`), producing all five artifacts. The
negative half — that a runtime-only environment fails — is not re-created here; it was measured on
the run machine itself on 2026-08-19 and is cited from `27-ONTARGET-VERIFICATION.md` §6. Full
transcript in `29.1-INSTALL-SITES.md` § Execution record.

### Options 2 and 3 remain OPEN, by decision

They were not taken, and their absence is a choice rather than an oversight:

- **Option 2** (move `DECLARED_CONSTANTS` into a non-test module so a production stage no longer
  needs a test runner) touches the source of §3-facing constants and requires the full suite to be
  re-run behind it. Out of scope for a phase whose hard constraint is that `src/` does not move.
- **Option 3** (promote `psutil` into runtime dependencies, or add an
  `os.cpu_count()` / `/proc/meminfo` fallback so the two required fields are never null on Linux)
  changes the shipped package's dependency contract for every pip user. Also out of scope.

Both are correct long-term and both are still worth doing post-submission. **The body of this todo
above is left intact** so whoever picks them up has the full diagnosis; nothing new was filed.

And, unchanged: do **not** weaken `gate3_run_manifest_fields` to tolerate the nulls. The gate was
right — it is the only reason this was visible at all.
