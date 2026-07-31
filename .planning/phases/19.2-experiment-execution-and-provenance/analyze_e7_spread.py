"""D-36: does E7's shared-vs-per-camera conclusion survive its own seed variation?

E7 compares a shared interface against per-camera interfaces. Its refined arms were
measured swinging >10 mm across seeds (`shared_refined` 0.483 -> 11.550 mm), larger
than the gap the experiment is trying to resolve -- which is why D-36 requires a
spread rather than a single-seed point estimate.

## The criterion this script uses, and why the obvious one is wrong

The tempting test is "is the gap between the two arms' MEANS larger than their
marginal spreads?" That test is **wrong here, and it answers NOT SUPPORTED on data
that in fact supports the conclusion 5 times out of 5.**

The seeds are **paired**: one seed builds one scenario, and both arms are evaluated
on it. Marginal spreads therefore contain seed-to-seed scenario variation that is
COMMON to both arms and cancels in the comparison. Measured here: for the refined
pairing the two arms correlate at r = +0.98 across seeds -- a bad seed makes both
arms bad together. Comparing marginal ranges throws that structure away and asks a
question about independent samples that were never independent.

The correct test is on the **per-seed difference**. If the paired difference never
changes sign, the ordering is consistent regardless of how far the levels wander.

## What this reports

  1. Per-arm mean and full range across seeds -- D-36's literal requirement, and what
     bounds any ABSOLUTE claim.
  2. The paired per-seed difference, its range, and whether it crosses zero.
  3. An exact sign test (one-tailed) on the paired differences.
  4. The between-arm correlation, which is the evidence that the spread is common-mode.

An absolute value and a comparison have different evidence requirements, and this
script deliberately reports both: the comparison can be safe while the absolute
numbers are not.

Usage:
    python .planning/phases/19.2-experiment-execution-and-provenance/analyze_e7_spread.py
"""

from __future__ import annotations

import sys
from math import comb
from pathlib import Path

import pandas as pd

ROOT = Path("C:/Users/tucke/Desktop/Aqua/AquaCal/seed_sweep_19_2/e7_interface_ablation")
METRIC = "camera_height_drift_mm"
PAIRS = [("shared_fixed", "percamera_fixed"), ("shared_refined", "percamera_refined")]


def load() -> pd.DataFrame:
    rows = []
    for d in sorted(ROOT.glob("seed_*")):
        csv = d / "interface_ablation.csv"
        if not csv.is_file():
            print(f"  MISSING {csv}", file=sys.stderr)
            continue
        df = pd.read_csv(csv)
        df["seed"] = int(d.name.split("_")[1])
        rows.append(df)
    if not rows:
        sys.exit("no seed CSVs found -- has the sweep produced E7 output yet?")
    return pd.concat(rows, ignore_index=True)


def main() -> int:
    df = load()
    per = (
        df.assign(a=df[METRIC].abs())
        .groupby(["arm", "seed"])["a"]
        .mean()
        .unstack("seed")
    )
    seeds = sorted(per.columns)
    n = len(seeds)
    print(f"seeds present: {seeds}  ({n} of 5)")
    if n < 5:
        print("  ⚠ PARTIAL SWEEP — report as partial, not as five-seed evidence.")
    print()

    stats = per.copy()
    stats["mean"] = per[seeds].mean(axis=1)
    stats["min"] = per[seeds].min(axis=1)
    stats["max"] = per[seeds].max(axis=1)
    stats["range"] = stats["max"] - stats["min"]
    print(f"=== (1) mean |{METRIC}| per arm, by seed — bounds any ABSOLUTE claim ===")
    print(stats.to_string(float_format=lambda v: f"{v:10.5f}"))
    print()

    print("=== (2-4) PAIRED comparison — the directional question ===")
    all_consistent = True
    for shared, percam in PAIRS:
        if shared not in per.index or percam not in per.index:
            print(f"  {shared} / {percam}: arm missing, skipped")
            continue
        diff = per.loc[percam] - per.loc[shared]  # >0 means shared is better
        n_pos = int((diff > 0).sum())
        crosses = bool(diff.min() < 0 < diff.max())
        p_one = sum(comb(n, k) for k in range(n_pos, n + 1)) / 2**n
        r = per.loc[shared].corr(per.loc[percam])
        all_consistent &= not crosses and n_pos == n
        print(f"  {shared} vs {percam}")
        for s in seeds:
            print(
                f"     seed {s}: percamera {per.loc[percam, s]:8.4f}  "
                f"shared {per.loc[shared, s]:8.4f}  diff {diff[s]:+8.4f}"
            )
        print(f"     shared better in {n_pos}/{n} seeds; diff crosses zero: {crosses}")
        print(
            f"     paired diff: mean {diff.mean():+.4f}  "
            f"range [{diff.min():+.4f}, {diff.max():+.4f}]"
        )
        print(f"     exact sign test (one-tailed): p = {p_one:.4f}")
        print(f"     between-arm correlation across seeds: r = {r:+.4f}")
        if abs(r) > 0.8:
            print("       -> spread is largely COMMON-MODE; marginal ranges overstate")
            print("          the uncertainty in the DIFFERENCE.")
        print()

    print("=== VERDICT ===")
    if all_consistent:
        print("The paired difference never changes sign: the DIRECTIONAL conclusion is")
        print(
            "supported. Quote the comparison with its paired range, not a single seed."
        )
        print()
        print(
            "BUT the absolute values remain seed-dependent — see table (1). Any claim"
        )
        print(
            "about an arm's absolute drift must carry its full range, and the refined"
        )
        print("arms in particular must NOT be quoted as point estimates.")
    else:
        print("The paired difference changes sign across seeds: E7 does NOT support a")
        print(
            "directional conclusion, and the manuscript must not state one. This is a"
        )
        print("result, not a failure of the run.")
    print()
    print(
        f"CAVEAT: n = {n} seeds. 5/5 gives an exact one-tailed p of 0.031 — suggestive,"
    )
    print("not decisive. This measures scenario-generator seed variation only, on one")
    print("metric. It is not a bound on real-data variation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
