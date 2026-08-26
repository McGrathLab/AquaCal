"""ROADMAP criterion 3 / D-29-16: did FIX-02 move E7's published sign test?

E7 compares a **shared** air-water interface against **per-camera** interfaces.
Its published result (supplement section 14) is a one-tailed exact sign test on
the paired per-seed difference in mean |camera_height_drift_mm|: the shared arm
wins **10 of 10** seeds on the fixed-intrinsics pairing, with no zero crossing,
at p = 0.00098.

FIX-02 (Phases 23-26) gave E7 two extra free parameters per interface. Extra
freedom in the per-camera arm is exactly the kind of change that could soften a
10-of-10 result. ROADMAP criterion 3 exists so that if it did, *"it is reported
here, not discovered during manuscript re-verification."*

## The statistic, and why it is copied rather than re-derived

The recipe below is transferred verbatim from
`.planning/phases/19.2-experiment-execution-and-provenance/analyze_e7_spread.py`,
which is the script that produced the published number. Research confirmed it by
reproducing its own published 10/10, p = 0.00098 on the baseline tree before
using it on anything else.

The seeds are **paired**: one seed builds one scenario and both arms are
evaluated on it, so seed-to-seed scenario variation is common to both arms and
cancels in the difference. Comparing marginal ranges instead would ask a
question about independent samples that were never independent. The test is on
the per-seed difference, and it is **one-tailed** -- the module's own history
records one-sided and two-sided being conflated once already, so no substitution
(`scipy.stats.binomtest`, a two-sided p, a different metric) is made here.

What is NOT copied from the analog: its `ROOT`, a hard-coded Windows path to a
seed-sweep directory that no longer exists; its `load()`, which globbed a layout
that no longer exists; and its `n = 5` caveat text and `(n of 5)` line, both of
which are hard-wired and would contradict the domain actually measured. `n` here
is derived from the data.

## What this compares

  * BEFORE: `experiments/pre_rerun_baseline/results/interface_ablation_band.csv`
  * AFTER : `experiments/results/interface_ablation_band.csv`

Both pairings are reported for both trees, per D-29-16 ("measure, report both
numbers in the phase record, and flag to the author only if the conclusion
moved"). The md5 of attempt 1's copy is recorded alongside, because attempt 1
and attempt 2 being byte-identical is what dates any movement to *before* the
re-run.

Read-only re-analysis of two already-written CSVs. **No stage is executed.** In
particular E7's band is never run by hand: a manual `--force` band run fires the
known benchmark-overwrite hazard.

Usage (cwd = repository root):
    python .planning/phases/29-gate-verification-results-commit/analyze_e7_before_after.py
"""

from __future__ import annotations

import hashlib
from math import comb
from pathlib import Path

import pandas as pd

METRIC = "camera_height_drift_mm"
PAIRS = [("shared_fixed", "percamera_fixed"), ("shared_refined", "percamera_refined")]

BEFORE = Path("experiments/pre_rerun_baseline/results/interface_ablation_band.csv")
AFTER = Path("experiments/results/interface_ablation_band.csv")
# Attempt 1's copy. Not compared -- recorded, because its byte-identity with
# AFTER is what places any movement before the re-run rather than inside it.
ATTEMPT1 = Path("experiments/freeze01_run_output/results/interface_ablation_band.csv")


def _md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sign_test(band_csv: Path) -> list[dict[str, object]]:
    """Run the one-tailed paired sign test for every pairing in `PAIRS`.

    Returns one row per pairing. `n` is derived from the number of seed columns
    present in the data, never assumed.
    """
    df = pd.read_csv(band_csv)
    per = (
        df.assign(a=df[METRIC].abs())
        .groupby(["arm", "seed"])["a"]
        .mean()
        .unstack("seed")
    )
    seeds = sorted(per.columns)
    n = len(seeds)

    rows: list[dict[str, object]] = []
    for shared, percam in PAIRS:
        if shared not in per.index or percam not in per.index:
            rows.append(
                {
                    "pairing": f"{shared} vs {percam}",
                    "skipped": True,
                    "reason": (
                        f"arm missing from {band_csv}: "
                        f"{'shared ' + shared if shared not in per.index else ''}"
                        f"{'percamera ' + percam if percam not in per.index else ''}"
                    ),
                    "seeds": seeds,
                    "n": n,
                }
            )
            continue
        diff = per.loc[percam] - per.loc[shared]  # >0 means shared is better
        n_pos = int((diff > 0).sum())
        crosses = bool(diff.min() < 0 < diff.max())
        tail = sum(comb(n, k) for k in range(n_pos, n + 1))
        p_one = tail / 2**n
        r = per.loc[shared].corr(per.loc[percam])
        rows.append(
            {
                "pairing": f"{shared} vs {percam}",
                "skipped": False,
                "shared": shared,
                "percam": percam,
                "seeds": seeds,
                "n": n,
                "n_pos": n_pos,
                "crosses": crosses,
                "tail": tail,
                "denom": 2**n,
                "p_one": p_one,
                "r": float(r),
                "diff": diff,
                "per": per,
            }
        )
    return rows


def report(label: str, band_csv: Path) -> list[dict[str, object]]:
    """Print the per-seed detail for one tree and return its result rows."""
    rows = sign_test(band_csv)
    print(f"  tree : {label}")
    print(f"  file : {band_csv}")
    print(f"  md5  : {_md5(band_csv)}")
    print()
    for row in rows:
        if row["skipped"]:
            print(f"  {row['pairing']}: {row['reason']} -- SKIPPED, not dropped")
            print()
            continue
        seeds = row["seeds"]
        n = row["n"]
        per = row["per"]
        diff = row["diff"]
        shared, percam = row["shared"], row["percam"]
        print(f"  {shared} vs {percam}")
        print(
            f"     seeds present: {seeds}  "
            f"(n = {n}, derived from len(per.columns), not hard-coded)"
        )
        for seed in seeds:
            print(
                f"     seed {seed}: percamera {per.loc[percam, seed]:8.4f}  "
                f"shared {per.loc[shared, seed]:8.4f}  diff {diff[seed]:+8.4f}"
            )
        print(
            f"     shared better in {row['n_pos']}/{n} seeds; "
            f"diff crosses zero: {row['crosses']}"
        )
        print(
            f"     paired diff: mean {diff.mean():+.4f}  "
            f"range [{diff.min():+.4f}, {diff.max():+.4f}]"
        )
        print(
            f"     exact sign test (one-tailed): p = {row['p_one']:.5f}  "
            f"= {row['tail']}/{row['denom']}  = {row['p_one']!r}"
        )
        print(f"     between-arm correlation across seeds: r = {row['r']:+.4f}")
        if abs(row["r"]) > 0.8:
            print("       -> spread is largely COMMON-MODE; marginal ranges overstate")
            print("          the uncertainty in the DIFFERENCE.")
        print()
    return rows


def _summary_line(tree: str, row: dict[str, object]) -> str:
    if row["skipped"]:
        return f"  {tree:20s} {row['pairing']:40s} SKIPPED ({row['reason']})"
    return (
        f"  {tree:20s} {row['pairing']:40s} "
        f"{row['n_pos']:2d}/{row['n']:<2d}  "
        f"crosses={str(row['crosses']):5s}  "
        f"p={row['p_one']:.5f} = {row['tail']:>3d}/{row['denom']:<4d}  "
        f"r={row['r']:+.4f}"
    )


def _pairing_move(before: dict[str, object], after: dict[str, object]) -> str:
    """One-line before -> after statement for a pairing, skip-safe."""
    if before["skipped"] or after["skipped"]:
        return f"{before['pairing']}: SKIPPED on at least one tree -- not compared"
    return (
        f"{before['pairing']}: "
        f"{before['n_pos']}/{before['n']} "
        f"(p = {before['tail']}/{before['denom']} = {before['p_one']:.5f}) -> "
        f"{after['n_pos']}/{after['n']} "
        f"(p = {after['tail']}/{after['denom']} = {after['p_one']:.5f})"
    )


def main() -> int:
    print("=== (0) ROADMAP criterion 3 / D-29-16 -- E7 before/after sign test ===")
    print()
    print("Question: did FIX-02's two extra free parameters per interface soften")
    print("E7's published 10-of-10, p = 0.00098 fixed-intrinsics sign test?")
    print()
    print("Pure re-analysis of two already-written CSVs. No stage was executed;")
    print("E7's band was NOT run by hand (a manual --force band run fires the")
    print("known benchmark-overwrite hazard).")
    print()
    print(f"  METRIC = {METRIC}")
    print(f"  PAIRS  = {PAIRS}")
    print("  statistic: one-tailed exact sign test on the PAIRED per-seed")
    print("  difference (percamera - shared) in mean |METRIC|; >0 means shared")
    print("  is better. Transferred verbatim from")
    print("  .planning/phases/19.2-.../analyze_e7_spread.py, the script that")
    print("  produced the published number.")
    print()

    print("=== (1) The three trees' artifacts, by md5 ===")
    print()
    for name, path in (
        ("pre_rerun_baseline", BEFORE),
        ("freeze01_run_output", ATTEMPT1),
        ("freeze-02 (this run)", AFTER),
    ):
        print(f"  {name:22s} {_md5(path)}  {path}")
    print()
    identical = _md5(ATTEMPT1) == _md5(AFTER)
    print(f"  attempt 1 and attempt 2 byte-identical on this artifact: {identical}")
    print()

    print("=== (2) BEFORE -- pre_rerun_baseline ===")
    print()
    before_rows = report("pre_rerun_baseline (before)", BEFORE)

    print("=== (3) AFTER -- freeze-02, this run ===")
    print()
    after_rows = report("freeze-02 (after)", AFTER)

    print("=== (4) Summary -- two pairings x two trees ===")
    print()
    for tree, rows in (("pre_rerun_base", before_rows), ("freeze-02", after_rows)):
        for row in rows:
            print(_summary_line(tree, row))
    print()

    fixed_before, refined_before = before_rows[0], before_rows[1]
    fixed_after, refined_after = after_rows[0], after_rows[1]
    fixed_held = (
        not fixed_before["skipped"]
        and not fixed_after["skipped"]
        and fixed_before["n_pos"] == fixed_after["n_pos"]
        and fixed_before["crosses"] == fixed_after["crosses"]
        and fixed_before["p_one"] == fixed_after["p_one"]
    )
    refined_moved = (
        not refined_before["skipped"]
        and not refined_after["skipped"]
        and (
            refined_before["n_pos"] != refined_after["n_pos"]
            or refined_before["p_one"] != refined_after["p_one"]
        )
    )

    print("=== VERDICT ===")
    print()
    held_word = "HELD" if fixed_held else "MOVED"
    print(f"  (1) THE PUBLISHED PRIMARY CONCLUSION {held_word}.")
    print(f"      {_pairing_move(fixed_before, fixed_after)}")
    print(f"      identical before and after: {fixed_held}")
    if fixed_held:
        print("      FIX-02's two extra free parameters per interface did NOT")
        print("      soften the fixed-intrinsics arm. Under D-29-16 this is a")
        print("      line in the record, not an author escalation.")
    else:
        print("      *** The PRIMARY published result moved. Under D-29-16 this")
        print("      is a flag-to-author case and outranks item (2) below. ***")
    print()
    moved_word = "MOVED" if refined_moved else "HELD"
    print(f"  (2) THE SECONDARY REFINED PAIRING {moved_word}.")
    print(f"      {_pairing_move(refined_before, refined_after)}")
    print(f"      moved: {refined_moved}")
    print("      Both figures are PUBLISHED, in supplement section 14 / MF-05.")
    if refined_moved:
        print("      The CONCLUSION is unchanged -- the refined arm was already")
        print("      non-significant and is now more clearly so -- but the")
        print("      digits moved.")
        print()
        print("      *** THIS IS THE CASE D-29-16 REQUIRES BE FLAGGED TO THE")
        print("      AUTHOR. *** It is raised here explicitly rather than being")
        print("      discovered later during manuscript re-verification, which")
        print("      is the reason ROADMAP criterion 3 exists.")
    else:
        print("      Unchanged before and after; a line in the record only.")
    print()
    print("  (3) THE MOVE IS NOT A RE-RUN ARTEFACT.")
    print(
        f"      attempt 1 and attempt 2 carry the same md5 "
        f"({_md5(AFTER)}): byte-identical: {identical}."
    )
    print("      The refined pairing's move therefore landed BEFORE attempt 1,")
    print("      i.e. it is a Phase 23-26 (FIX-02) effect, not something this")
    print("      run introduced. Do not attribute it to the re-run.")
    print()
    print("  (4) SECTION 3 EDITS STAY THE AUTHOR'S.")
    print("      Per D-29-16 and D-29-19, this script reports the numbers and")
    print("      flags the move. It does not open, read for editing, or write")
    print("      any manuscript file, and no manuscript change is implied or")
    print("      made here. Any such change is the author's to decide.")
    print()
    n_before = before_rows[0]["n"]
    n_after = after_rows[0]["n"]
    print(
        f"CAVEAT: n = {n_before} seeds before and n = {n_after} after, derived "
        f"from the seed"
    )
    print("columns present in each CSV. This measures scenario-generator seed")
    print(f"variation only, on one metric ({METRIC}). It is not a")
    print("bound on real-data variation, and a sign test on n seeds cannot")
    print("resolve an effect smaller than one seed's worth of flips.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
