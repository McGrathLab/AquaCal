# 26-12 SUMMARY — e3's missing dependency edge

**Status:** COMPLETE. Two commits, one per task.
**Executed by:** the orchestrator, inline (not dispatched to an executor).

| Task | Commit | Subject |
|------|--------|---------|
| 1 | `2f76efb` | `fix(26-12): schedule e3 after the stage that writes the record it reads` |
| 2 | `a033726` | `fix(26-12): record an absent E2 record instead of crashing on it` |

## What was wrong

`e3` reads E2's `benchmark.json` through a hardcoded, cwd-relative path
(`e3_derived_quantities.py:173`) that `--out` does not redirect, but declared
`depends_on: ["preflight"]` and therefore ran at **stage 3** — five stages before
`e2_production` (stage 8) writes that file.

The failure was masked for as long as `experiments/results` still held a previous run's copy.
26-09's archive-aside emptied the tree (contents now under `experiments/pre_rerun_baseline/`),
pre-flight refuses a non-empty tree with no state file, and the 26-10 smoke pass then died on
`ValueError: cannot convert float NaN to integer` — **twice, in two independent runs**, losing
`structural_scaling.csv`, `cpr_grouping.tex` and `cpr_derived_values.tex` each time.

In the frozen run this is a stage-3 crash whose recovery protocol is restart-from-stage-1.

## Task 1 — the dependency edge

- `experiments/suite_expectations.json`: `e3.depends_on` `["preflight"]` → `["e2_production"]`.
  The diff is exactly one array; no `est_hours`, `rows`, `produces` or artifact entry moved.
- `experiments/run_experiment_suite.sh`: `e3` moved from index 2 to index 8 in `STAGES=(...)`,
  first within its new level (0.005 h, the cheapest stage in the suite).
- The ordering comment was rewritten to show `e3` in level 2 and to say why the edge exists.
- **A pre-existing deliberate inversion is now gone rather than resolved.** The old comment
  recorded that `prelaunch_probe` (0.01 h) was hand-placed before `e3` (0.005 h) so a hard abort
  could never land after `e3 --force` rewrote committed tier CSVs. The dependency edge now
  enforces that ordering structurally, so the exception was removed and the comment says so.

`experiments/EXPECTATIONS.md` needed no regeneration — `render_expectation_sheet --write`
reported "already up to date", because the sheet does not render `depends_on`. The plan's
instruction to regenerate was followed; it was a no-op.

**No 26-08 rail needed updating.** The plan anticipated a byte-identity or hash assertion on the
manifest's `stages` array. None exists in that form: `test_suite_stage_list.py` asserts the
*relationship* (both directions of stage-list ↔ manifest, plus topological order) rather than a
frozen order, and the dry-run snapshot in `test_run_experiment_suite_dryrun.py` compares
per-stage content rather than sequence. All 35 dry-run tests passed unmodified.

## Task 2 — the NaN guard

`build_derived_values_latex_content` cast `n_params` with a bare `int()`. When E2's record is
absent, the CPR path already degrades that row to nulls and stamps
`record_source=missing_e2_benchmark`; only this cast was unguarded, so the whole stage died and
took `structural_scaling.csv` with it.

The guard renders **`N/A (benchmark record absent)`** — deliberately non-numeric, so no
placeholder can be read as a measurement if the fragment reaches the manuscript. Not a zero, not
a stale count. Exit stays 0, because `--skip-e2` declares a legitimately synthetic-only run and
failing the stage there would cost e3's four other artifacts for no gain.

The marker also contains **no digits at all** — the test asserts `not any(ch.isdigit())` on the
aside. This is why the wording is "benchmark record absent" rather than the more natural "E2
benchmark record absent": the "2" would have satisfied a digit check that exists precisely to
make a numeric placeholder impossible.

### TDD gate

RED was genuine and is quoted here:

```
>       total_params = int(row_13_200["n_params"])
E       ValueError: cannot convert float NaN to integer
experiments\e3_derived_quantities.py:861: ValueError
```

The companion `test_present_record_is_unchanged` passed at RED, which is what makes it a rail
rather than a restatement of the change.

**One deviation:** after the guard landed, `test_absent_record_renders_a_non_numeric_marker`
failed again on an `IndexError` — my split token was `\CPRParamsAside}}{`, transcribed from the
f-string's escaped braces rather than the rendered output (`\CPRParamsAside}{`). A test bug, not
a production one; fixed in the test. Worth recording because the first RED and the second failure
look alike in a log and are not.

### Byte-identity

Regenerating the fragment from the committed `pre_rerun_baseline/results/cpr_grouping.csv`
produces output byte-identical to the committed
`pre_rerun_baseline/results/cpr_derived_values.tex`. The present-record path did not move.

## Verification

| Check | Result |
|---|---|
| `bash -n experiments/run_experiment_suite.sh` | exit 0 |
| `pytest tests/unit/test_suite_stage_list.py tests/unit/test_expectations.py` | 102 passed |
| `pytest tests/unit/test_run_experiment_suite_dryrun.py` | 35 passed |
| `pytest tests/unit/test_experiments_e3.py` | 34 passed |
| `STAGES` index of `e3` (8) > `e2_production` (6) | asserted by reading the array |
| `git diff experiments/suite_expectations.json` | one array, quoted in the commit |

## Not in scope, deliberately

`reconstruction_bootstrap.py:56` hardcodes `experiments/results/real_rig_metrics.json` instead of
using `--out`. It is correctly ordered (it already declares `depends_on: ["e2_production"]`) and
works in production because `OUT_DIR == experiments/results`; it breaks only under `--smoke`,
where it is a coverage gap rather than a run risk. Left out so this plan stayed one defect wide.
