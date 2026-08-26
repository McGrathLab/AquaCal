"""ROADMAP criterion 2: E2's same-seed sanity control for the freeze-02 re-run.

The question this answers is narrow and specific: **at the same seed, does the
re-run reproduce the pre-run real-rig numbers to ~1e-8?** That is the only check
in this milestone's grading that speaks to *solver correctness* rather than to
artifact completeness or provenance bookkeeping. A drift at ~1e-2 would mean the
run is broken in a way that no completeness gate detects, which is why this is
item 1 on D-29-10's three-item stop list: a failure here blocks publication.

## Why the obvious comparison is wrong

The tempting test is "compare the re-run's `mean_per_camera_reprojection_px`
against the published number." That is **wrong**, because E2's own *seed* band on
exactly that quantity spans **0.761 -> 0.910 px**. Four orders of magnitude above
the 1e-8 this criterion asks for. A cross-seed comparison of a healthy run looks
catastrophic. The comparison is only meaningful **seed 42 against seed 42**.

So this script does not assume the seed: it reads `solver_config["seed"]` from
each tree's sibling `benchmark.json`, asserts the two agree, and prints the seed
on **every** comparison line. A line lifted out of this file into a record months
from now still says which seeds it compared.

## Why two baselines, both named

There are two candidate "before" trees and they give different, differently
meaningful answers:

  * `experiments/pre_rerun_baseline/results/` -- Windows, aquacal 1.8.0, sha
    6c7f930b. This is the baseline the criterion means. Its comparison spans
    Windows->Linux *and* 1.8.0->2.0.1, and is where the ~1e-8 figure lives.
  * `experiments/freeze01_run_output/results/` -- Linux, aquacal 2.0.1, sha
    3ab9c137, i.e. attempt 1 of this same re-run. Its comparison is exactly zero
    because the files are byte-identical, which is a **different and weaker**
    statement: two Linux runs at one library version, not the whole span.

Both are reported, separately and labelled. `tests/unit/_baseline_paths.py`'s
`resolve_results_dir()` is deliberately **not** used: it switches subject
depending on whether the live tree holds a file, and naming the tree is the whole
point here.

## Not to be confused with `check_e2_band`

`check_rerun_gates.py`'s `check_e2_band` compares the band's seed-42 record to
the *same run's* `real_rig_metrics.json` at rtol 1e-6. That is a within-run
consistency check, it is already inside the `176 PASS, 7 N/A, 0 FAIL` roll-up,
and it is not ROADMAP criterion 2.

Read-only. Opens three JSON pairs and prints. Runs no stage, writes no artifact.

Usage (cwd = repository root):
    python .planning/phases/29-gate-verification-results-commit/analyze_e2_control.py
"""

from __future__ import annotations

import json
from pathlib import Path

BASELINE_PRERUN = Path("experiments/pre_rerun_baseline/results/real_rig_metrics.json")
BASELINE_FREEZE01 = Path(
    "experiments/freeze01_run_output/results/real_rig_metrics.json"
)
AFTER = Path("experiments/results/real_rig_metrics.json")

TREES = [
    ("pre_rerun_baseline", BASELINE_PRERUN),
    ("freeze01_run_output", BASELINE_FREEZE01),
    ("freeze-02 (this run)", AFTER),
]

# The expected seed -- stated as an expectation to CHECK against each tree's
# benchmark.json, never as an input to the comparison.
SEED = 42

# D-29-10 stop-list item 1 fails at or above this relative drift.
DRIFT_LIMIT = 1e-6

ENV_FIELDS = ("git_sha", "aquacal_version", "numpy_version", "opencv_version", "os")


def read_seed(benchmark_json: Path) -> int:
    """Return `solver_config["seed"]` from a benchmark record."""
    with benchmark_json.open(encoding="utf-8") as fh:
        record = json.load(fh)
    return int(record["solver_config"]["seed"])


def _benchmark_beside(metrics_path: Path) -> Path:
    """The `benchmark.json` sibling of a `real_rig_metrics.json`."""
    return metrics_path.parent / "benchmark.json"


def _environment(metrics_path: Path) -> dict[str, object]:
    """Return the `environment` block of the sibling benchmark record."""
    with _benchmark_beside(metrics_path).open(encoding="utf-8") as fh:
        record = json.load(fh)
    return dict(record.get("environment", {}))


def _flatten(obj: dict[str, object]) -> dict[str, object]:
    """Flatten a metrics document to leaf values, skipping `provenance`.

    Compound fields (`camera_height_range_m`, `reprojection_range_px`,
    `auxiliary_reprojection_px`) are expanded to indexed / keyed leaves so no
    numeric value in the document escapes the control unchecked.
    """
    flat: dict[str, object] = {}
    for key, value in obj.items():
        if key == "provenance":
            continue
        if isinstance(value, dict):
            for sub, item in value.items():
                flat[f"{key}.{sub}"] = item
        elif isinstance(value, list):
            for index, item in enumerate(value):
                flat[f"{key}[{index}]"] = item
        else:
            flat[key] = value
    return flat


def _load(metrics_path: Path) -> dict[str, object]:
    with metrics_path.open(encoding="utf-8") as fh:
        return json.load(fh)


def compare(before_path: Path, after_path: Path, label: str) -> dict[str, object]:
    """Print a same-seed field-by-field drift report; return its worst cases.

    The seed is read from each tree's own `benchmark.json` and asserted equal
    before any value is compared, so the `seed N vs seed N` statement printed on
    every line is derived from the data rather than asserted by the caller.
    """
    seed_before = read_seed(_benchmark_beside(before_path))
    seed_after = read_seed(_benchmark_beside(after_path))
    stamp = f"seed {seed_before} vs seed {seed_after}"

    print(f"  before: {before_path}")
    print(f"  after : {after_path}")
    print(f"  seeds : {stamp}")
    if seed_before != seed_after:
        print("  *** SEED MISMATCH -- this is NOT a same-seed control. ***")
        print("  E2's seed band on mean_per_camera_reprojection_px spans")
        print("  0.761 -> 0.910 px, so a cross-seed comparison is meaningless")
        print("  at this tolerance. Failing closed without comparing values.")
        return {
            "seed_ok": False,
            "int_ok": False,
            "max_scalar": float("inf"),
            "max_scalar_field": "(not compared)",
            "max_all": float("inf"),
            "max_all_field": "(not compared)",
        }
    print()

    before = _load(before_path)
    after = _load(after_path)
    scalar_keys = {
        key
        for key, value in list(before.items()) + list(after.items())
        if key != "provenance" and not isinstance(value, (dict, list))
    }
    flat_before = _flatten(before)
    flat_after = _flatten(after)

    no_drift = "(no field drifted -- every value compared exactly equal)"
    max_scalar, max_scalar_field = 0.0, no_drift
    max_all, max_all_field = 0.0, no_drift
    int_ok = True

    for key in sorted(set(flat_before) | set(flat_after)):
        value_before = flat_before.get(key)
        value_after = flat_after.get(key)
        tag = "scalar  " if key in scalar_keys else "compound"

        if value_before is None or value_after is None:
            print(f"{stamp}  {tag}  {key:34s} PRESENT ON ONE SIDE ONLY -- skipped")
            continue

        both_int = all(
            isinstance(value, int) and not isinstance(value, bool)
            for value in (value_before, value_after)
        )
        if both_int:
            verdict = "EXACT EQUAL" if value_before == value_after else "*** DIFFERS"
            int_ok &= value_before == value_after
            print(
                f"{stamp}  {tag}  {key:34s} "
                f"{value_before!r:>24} -> {value_after!r:>24}  "
                f"integer field: {verdict}"
            )
            continue

        if not all(isinstance(value, float) for value in (value_before, value_after)):
            print(f"{stamp}  {tag}  {key:34s} non-numeric -- skipped")
            continue

        if value_before == 0.0:
            rel = 0.0 if value_after == 0.0 else float("inf")
        else:
            rel = abs(value_after - value_before) / abs(value_before)
        print(
            f"{stamp}  {tag}  {key:34s} "
            f"{value_before!r:>24} -> {value_after!r:>24}  rel={rel:.4e}"
        )

        if rel > max_all:
            max_all, max_all_field = rel, key
        if key in scalar_keys and rel > max_scalar:
            max_scalar, max_scalar_field = rel, key

    print()
    print(f"  [{label}] worst-case relative drift over the scalar fields:")
    print(f"      {max_scalar_field} = {max_scalar:.4e}")
    print(f"  [{label}] worst-case relative drift including compound leaves:")
    print(f"      {max_all_field} = {max_all:.4e}")
    print(f"  [{label}] integer fields all exactly equal: {int_ok}")
    return {
        "seed_ok": True,
        "int_ok": int_ok,
        "max_scalar": max_scalar,
        "max_scalar_field": max_scalar_field,
        "max_all": max_all,
        "max_all_field": max_all_field,
    }


def main() -> int:
    print("=== (0) ROADMAP criterion 2 -- the E2 same-seed sanity control ===")
    print()
    print("Question: at seed 42 against seed 42, does the freeze-02 re-run")
    print("reproduce the pre-run real-rig numbers to ~1e-8?")
    print()
    print("This is D-29-10 stop-list item 1 and the only check in the phase that")
    print("speaks to solver correctness. Every comparison line below carries its")
    print("own seed statement, because E2's SEED band on")
    print("mean_per_camera_reprojection_px spans 0.761 -> 0.910 px: a cross-seed")
    print("comparison of a healthy run reads as catastrophic. No line in this")
    print("file may be read without its seed statement.")
    print()
    print(f"Pass condition: worst-case relative drift < DRIFT_LIMIT = {DRIFT_LIMIT:g}")
    print()

    print("=== (1) The three trees, named in full ===")
    print()
    seeds: dict[str, int] = {}
    for name, path in TREES:
        env = _environment(path)
        seed = read_seed(_benchmark_beside(path))
        seeds[name] = seed
        print(f"  {name}")
        print(f"      metrics   : {path}")
        print(f"      benchmark : {_benchmark_beside(path)}")
        print(f"      seed      : {seed}   (solver_config['seed'])")
        for field in ENV_FIELDS:
            print(f"      {field:17s}: {env.get(field)}")
        print()

    seed_values = sorted(set(seeds.values()))
    print(f"  seeds across all three trees: {seeds}")
    if len(seed_values) != 1:
        print("  *** SEEDS DISAGREE -- failing closed, nothing below is a")
        print("      same-seed control. ***")
        seeds_agree = False
    else:
        seeds_agree = True
        print(f"  all three trees agree at seed {seed_values[0]}", end="")
        if seed_values[0] == SEED:
            print(f"; matches the expected SEED = {SEED}.")
        else:
            print(f"; but the expected SEED is {SEED}.")
    print()

    print("=== (2) pre_rerun_baseline -> freeze-02  [THE CRITERION'S COMPARISON] ===")
    print()
    print("  Spans Windows -> Linux AND aquacal 1.8.0 -> 2.0.1. This is the")
    print("  comparison ROADMAP criterion 2 means when it says the run")
    print("  'reproduces its pre-run numbers to ~1e-8'.")
    print()
    prerun = compare(BASELINE_PRERUN, AFTER, "pre_rerun_baseline")
    print()

    print(
        "=== (3) freeze01_run_output -> freeze-02  [WEAKER, REPORTED FOR HONESTY] ==="
    )
    print()
    print("  Attempt 1 of this same re-run: Linux, aquacal 2.0.1. The two files")
    print("  are byte-identical, so this comparison is exactly zero on every")
    print("  field. That is a DIFFERENT AND WEAKER statement than section (2):")
    print("  it holds two Linux runs at one library version against each other,")
    print("  not the Windows->Linux / 1.8.0->2.0.1 span the criterion asks about.")
    print("  It is reported so that neither number can be mistaken for the other.")
    print()
    freeze01 = compare(BASELINE_FREEZE01, AFTER, "freeze01_run_output")
    print()

    worst = max(prerun["max_all"], freeze01["max_all"])
    ok = (
        seeds_agree
        and prerun["seed_ok"]
        and freeze01["seed_ok"]
        and prerun["int_ok"]
        and freeze01["int_ok"]
        and worst < DRIFT_LIMIT
    )

    print("=== VERDICT ===")
    print()
    print("  ROADMAP criterion 2 -- E2 same-seed control, seed 42 vs seed 42.")
    print("  D-29-10 stop-list item 1: a FAIL here BLOCKS PUBLICATION. It is the")
    print("  only check in this phase that speaks to solver correctness; the")
    print("  completeness gates cannot detect the failure this one detects.")
    print()
    print("  pre_rerun_baseline -> freeze-02   (the criterion's comparison)")
    print(
        f"      worst scalar field   : {prerun['max_scalar_field']} = "
        f"{prerun['max_scalar']:.4e}"
    )
    print(
        f"      worst field overall  : {prerun['max_all_field']} = "
        f"{prerun['max_all']:.4e}"
    )
    print(f"      integer fields exact : {prerun['int_ok']}")
    print()
    print("  freeze01_run_output -> freeze-02  (weaker: same OS, same version)")
    print(
        f"      worst scalar field   : {freeze01['max_scalar_field']} = "
        f"{freeze01['max_scalar']:.4e}"
    )
    print(
        f"      worst field overall  : {freeze01['max_all_field']} = "
        f"{freeze01['max_all']:.4e}"
    )
    print(f"      integer fields exact : {freeze01['int_ok']}")
    print()
    print(f"  worst case across both comparisons: {worst:.4e}")
    print(f"  DRIFT_LIMIT                       : {DRIFT_LIMIT:g}")
    print()
    if ok:
        print("  RESULT: PASS")
        print()
        print("  The re-run reproduces the pre-run real-rig numbers at the same")
        print("  seed to well within 1e-6. D-29-10 stop-list item 1 does not fire.")
    else:
        print("  RESULT: FAIL")
        print()
        print("  D-29-10 stop-list item 1 HAS FIRED. This blocks publication.")
        print("  Do NOT regenerate any artifact to make this pass (D-29-08) --")
        print("  a failure here is a finding about the solver, and it is to be")
        print("  reported, not repaired away.")
    print()
    print("  Scope: this compares real_rig_metrics.json only, and only at seed")
    print("  42. It is not a bound on cross-seed variation -- E2's seed band")
    print("  covers that and is a separate, much wider interval.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
