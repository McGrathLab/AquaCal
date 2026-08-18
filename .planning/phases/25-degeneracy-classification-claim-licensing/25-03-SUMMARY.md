---
phase: 25-degeneracy-classification-claim-licensing
plan: 03
subsystem: experiments
tags: [degeneracy, classification, taxonomy, provenance, pandas]

# Dependency graph
requires:
  - phase: 25
    plan: 01
    provides: "`degeneracy_details_out` per-observation rows carrying `nan_reason` int8 codes, `stage`, `n_flagged_at_stage` and `truncated`"
  - phase: 24
    provides: "the `NAN_REASON_*` constants and the `experiments/_degeneracy.py` module they are classified in"
provides:
  - "`OBSERVATION_BUCKETS` — the closed code-to-bucket vocabulary, keyed by the imported `NAN_REASON_*` constants"
  - "`observation_bucket(code)` — raising accessor over that vocabulary"
  - "`classify_degenerate_observations(rows) -> pd.DataFrame` — adds a `bucket` column derived from the code alone"
  - "`write_degeneracy_classification(path, df, *, provenance, force=False)` — the table writer with its in-body FIX-04 stamp"
affects: [25-06, 29]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Closed vocabulary keyed by IMPORTED library constants, never hardcoded integers"
    - "Discriminator-column guard before any per-row read (extends `summarize_degeneracy_columns`' guard to a row-wise classifier)"
    - "FIX-04 free-text provenance column carried in the artifact's own body"

key-files:
  created:
    - .planning/phases/25-degeneracy-classification-claim-licensing/25-03-SUMMARY.md
  modified:
    - experiments/_degeneracy.py
    - tests/unit/test_discard_accounting.py

key-decisions:
  - "The bucket is derived from `nan_reason` ONLY. No predicate on `h_q_m` appears anywhere in the classifier — a second derivation can disagree with the projector's, which already assigns exactly one cause per point."
  - "`unflagged` (code 0) is in the vocabulary even though the flagged sink never emits it, so the mapping is total over the code space and an unexpected 0 is classified rather than crashing."
  - "The discriminator is the ABSENCE of the `nan_reason` column, which raises; zero rows does not raise, because for the flagged sink zero rows is a genuine measured-and-clean result."
  - "`rows=None` raises rather than returning an empty frame: 'never computed' has no honest DataFrame representation."

patterns-established:
  - "Raising accessor over an experiments-side vocabulary, mirroring `_observability.degeneracy_cause_key` on the library side."

requirements-completed: [DEGEN-04]

# Metrics
duration: 40min
completed: 2026-08-18
---

# Phase 25 Plan 03: Offline Bucket Classifier and Stamped Table Writer Summary

**`experiments/_degeneracy.py` now owns the whole per-observation taxonomy: four named buckets keyed by the library's imported `NAN_REASON_*` codes, a classifier that derives the bucket from the code and nothing else, and a table writer that carries its provisional/truncation stamp as an ordinary CSV column.**

## Performance

- **Duration:** ~40 min
- **Tasks:** 2 of 2
- **Files modified:** 2 (1 experiments module, 1 test file)
- **Commits:** 2 task commits + this docs commit

## Accomplishments

### Task 1 — vocabulary and classifier (`56bfbfe`)

- `OBSERVATION_BUCKETS: dict[int, str]` maps code 2 → `above_interface` (a), code 3 →
  `camera_model_failure` (b), code 1 → `interface_below_camera` (c), code 0 → `unflagged`.
  The keys are the constants **imported from `aquacal.core`**, so a code renumbered in the
  library cannot silently re-point a bucket here.
- `observation_bucket(nan_reason)` raises `ValueError` on any code outside the vocabulary,
  following `_observability.degeneracy_cause_key`'s raising-accessor shape.
- `classify_degenerate_observations(rows)` accepts a `list[dict]` or a `pd.DataFrame`, returns
  every input column plus `bucket`. Guards, in order: `None` raises; zero rows returns an empty
  frame that still carries `bucket`; a non-empty frame missing `nan_reason` raises, naming the
  columns it did find.
- The bucket line carries the inline comment the plan required: camera-model failure is
  `NAN_REASON_BEHIND_CAMERA` **with `h_q > 0`** — the geometry was fine and the pixel was not —
  and that is the D-04 tripwire condition.
- Module docstring gained a `Per-observation classification` section stating the `h_q` semantics
  verbatim from CONTEXT § Specific Ideas (estimate not reality, evaluated at the solution), the
  `19.3-ORCHESTRATOR-NOTES.md` §4 falsification note, the pre-registered expectation (a dominates;
  c dead by measurement at `h_c` = 1.0472–1.1125 m; obliquity/TIR retired), and the statement that
  `chord_incidence_deg` is a straight-chord surrogate and **not** the refracted exit angle.

### Task 2 — the writer and three tests (`2f07dab`)

- `write_degeneracy_classification(path, df, *, provenance, force=False)` copies
  `write_degeneracy_breakdown`'s five steps exactly: `Path(path)` → refuse-to-overwrite with a
  `logger.warning` naming `--force` → `mkdir(parents=True, exist_ok=True)` → write →
  `logger.info("Wrote ... to %s", path)`.
- The stamp is an ordinary `provenance` column, identical on every row (`PROVENANCE_COLUMN`),
  the FIX-04 `e7_focal_standoff.csv::scope` precedent. No leading `#` line is emitted; the
  docstring states why (it breaks `pd.read_csv` in `compare_experiment_csv` and every downstream
  consumer) and what the caller must put in the string: git sha, the word `provisional` for the
  D-01/D-03 local probe, and `truncated=true|false` with the true aggregate count taken from the
  row's `n_flagged_at_stage` stamp, never from `len(df)`.
- Three tests in a new section F of `tests/unit/test_discard_accounting.py`, built through a
  `_detail_row()` factory in the idiom of the file's existing `_breakdown()` factory — no solve
  required, so they stay off the `slow` path (the three run in ~6 s).

## Verification

| Check | Result |
|---|---|
| `pytest tests/unit/test_discard_accounting.py -k "classif or provenance" -q` | 4 passed, 6.0 s (3 new + 1 pre-existing name match) |
| `pytest tests/unit/test_discard_accounting.py -q` | **39 passed**, 118.8 s |
| `python -c "... print(sorted(OBSERVATION_BUCKETS.values()))"` | `['above_interface', 'camera_model_failure', 'interface_below_camera', 'unflagged']` |
| `grep -c "NAN_REASON_" experiments/_degeneracy.py` | 17 (≥ 4 required); all imported from `aquacal.core`, none redefined |
| `grep -vE '^\s*#' experiments/_degeneracy.py \| grep -c "h_q_m >\|h_q_m <"` | **0** — the bucket is never derived from a geometry predicate |
| `grep -rn "camera_model_failure" src/aquacal/ \| wc -l` | **0** — no bucket name entered the library |
| `git status --porcelain` before each commit | only `experiments/_degeneracy.py` and `tests/unit/test_discard_accounting.py` |
| `ruff check` / `ruff format --check` | clean on both files (also enforced by the pre-commit hooks, which passed on both commits) |

All test runs used `PYTHONPATH="$(pwd)/src"` and were verified to resolve `aquacal` at
`.claude/worktrees/agent-ac769379675e2c53d/src/aquacal/__init__.py` — inside this worktree, not
the main checkout. The full suite was **not** run; that is the orchestrator's post-merge gate.

### The by-code separation, proven

`test_classify_separates_camera_model_failure_by_code_not_geometry` builds two rows with an
**identical, positive** `h_q_m = 0.37` and `nan_reason` 2 and 3. It asserts
`classified["h_q_m"].nunique() == 1` up front, so the premise cannot silently rot, then asserts
the two rows land in different buckets. Any classifier that re-derived the bucket from `h_q_m`
would have to put them in the same bucket and would fail this test.

## Deviations from Plan

**None of substance.** Two small judgement calls, both inside the plan's stated intent:

**1. [Rule 2 — missing critical functionality] `rows=None` raises rather than returning an empty frame**

- **Found during:** Task 1, writing the discriminator guard.
- **Issue:** The plan asked that "an empty or column-missing input must be distinguishable from a
  measured-and-clean input". A `DataFrame` return type has no `None` channel the way
  `summarize_degeneracy_columns`' dict does, so "never computed" cannot be encoded in the value.
- **Fix:** Three distinct behaviours instead of two — `None` raises (never computed, cannot be
  represented); a missing `nan_reason` column raises (never computed for these rows); zero rows
  returns an empty frame carrying `bucket` (genuinely clean, since the flagged sink emits only
  flagged rows). Both raise paths are asserted in the mapping test.
- **Files modified:** `experiments/_degeneracy.py`
- **Commit:** `56bfbfe`

**2. [Rule 2] `unflagged` is kept in the vocabulary though the flagged sink never emits code 0**

- The mapping is total over the code space, so an unexpected 0 arriving from a future caller is
  classified and visible rather than raising in the middle of a table write. The comment block
  says so explicitly.

### Not deviations

- **STATE.md and ROADMAP.md were deliberately not touched** — the orchestrator owns those writes
  after the wave merges.
- **Nothing under `src/aquacal/` was modified**, and no bucket name entered the library (D-06).
- No package was installed.
- No experiment, calibration or full-suite run was launched.

## Interfaces Delivered (for plan 25-06)

```python
from experiments._degeneracy import (
    OBSERVATION_BUCKETS,          # dict[int, str], keyed by NAN_REASON_* constants
    observation_bucket,           # (int) -> str, raises on an unknown code
    classify_degenerate_observations,   # (list[dict] | pd.DataFrame) -> pd.DataFrame
    write_degeneracy_classification,    # (path, df, *, provenance: str, force: bool = False)
)
```

Plan 25-06 is expected to compose the `provenance` string as, for example:

```
PROVISIONAL local probe (D-01/D-03), git_sha=<sha>, truncated=false,
n_flagged_at_stage=<from the row stamp, not len(df)>; not a Phase 29 frozen
table and no count from it reaches any manuscript-facing number (D-02).
```

…and to point `--out` at `.planning/probes/2026-08-17-degeneracy-classification/`, never at
`experiments/results/`.

## Known Stubs

None. No hardcoded empty value, placeholder string or unwired data path was introduced.

## Threat Flags

None. This plan adds no network endpoint, auth path, file-access pattern or schema at a trust
boundary. The single boundary in the register (self-produced CSV → `pd.read_csv`) is unchanged,
and T-25-07/08/09 are all mitigated as planned: the stamp is in-body, `truncated` comes from the
independent counter by contract, and the bucket has exactly one derivation.

## Notes for the Next Plan

- **The stamp's truthfulness is the caller's job.** `write_degeneracy_classification` writes the
  string it is given; it cannot verify that `truncated=` matches the rows. Take the value from
  `n_flagged_at_stage` on the rows, which the library computed independently — deriving it from
  `len(df)` is precisely the bug D-10 exists to prevent.
- **`camera_model_failure` is the tripwire name.** A materially populated bucket (b) in Phase 29's
  frozen table re-opens the degeneracy-gate scope decision (D-04). It is not re-opened by the
  provisional local run.

## Self-Check: PASSED

- `experiments/_degeneracy.py`, `tests/unit/test_discard_accounting.py` and this SUMMARY all exist
  on disk.
- Both task commits exist in `git log`: `56bfbfe`, `2f07dab`.
- Neither commit deleted a tracked file.
- `git status --porcelain` showed only the two intended files before each commit.
- STATE.md and ROADMAP.md are untouched; nothing under `src/aquacal/` is modified.
