"""COV-08 (E7 half): the focal/standoff degeneracy WP6 planned and MF-05 never reported.

`experiments/results/interface_ablation_band.csv` (committed at `0ffbe15`) already carries
`focal_drift_pct` and `standoff_m` per camera, per arm, per seed across ten seeds
(`seed` in 42..51, `arm` in `{shared,percamera}_x_{fixed,refined}`). WP6 planned the
focal-length/standoff pairing as the refine-ON deliverable; MF-05 analyzed only
`camera_height_drift_mm` and never reported this column pair.

This module is pure re-analysis. Every function here takes an already-loaded `DataFrame`
-- no file paths inside the analysis functions (mirrors
`.planning/phases/19.2-experiment-execution-and-provenance/analyze_e7_spread.py`'s
reasoning: read the input once at the CLI boundary, keep the statistics testable on
tiny hand-built frames). It never opens, regenerates, or overwrites
`interface_ablation_band.csv`.

**Paired, not marginal (T-19.5-03-01).** Both `focal_drift_pct` and `standoff_m` are
evaluated on the same seed's scenario across all twelve cameras. The correct question is
the per-seed correlation between the two columns, not a comparison of their marginal
spreads -- the same reasoning `analyze_e7_spread.py` applies to the shared-vs-per-camera
arm comparison, one level down (within-seed cross-column association instead of
between-arm difference).

**One-sided p-value convention (T-19.5-03-02).** `focal_standoff_association`'s
`p_one_sided` field is named to make the convention unambiguous downstream: MF-05's own
p-values are one-sided (0.00098 = 2^-10 at ten unanimous seeds), and a prior reading of
that entry conflated one-sided and two-sided once already.

Usage:
    python -m experiments.e7_focal_standoff_analysis --out experiments/results
"""

from __future__ import annotations

import argparse
import logging
import sys
from math import comb
from pathlib import Path

import pandas as pd

from experiments._io import (
    build_experiment_arg_parser,
    resolve_out_dir,
    validate_args,
    write_experiment_csv,
)

logger = logging.getLogger(__name__)

BAND_CSV_NAME = "interface_ablation_band.csv"
OUTPUT_CSV_NAME = "e7_focal_standoff.csv"
ARMS = ("shared_fixed", "percamera_fixed", "shared_refined", "percamera_refined")
SCOPE_TEXT = (
    "Re-analysis of the ten committed seeds (42-51) of "
    f"experiments/results/{BAND_CSV_NAME} at the 'realistic' scenario. Bounds the "
    "focal-length/standoff association within that band only; not a re-run and not a "
    "new calibration (D-19.5-05)."
)


def focal_standoff_association(df: pd.DataFrame, arm: str) -> dict:
    """Per-seed correlation between `focal_drift_pct` and `standoff_m`, one arm.

    For each seed present for `arm`, computes the Pearson correlation of
    `focal_drift_pct` against `standoff_m` across that seed's cameras. The
    per-seed correlations (not a pooled/marginal correlation across all
    seed-camera rows at once) are the unit of evidence, because pooling would
    mix within-seed association with between-seed scenario-difficulty
    variation that both columns share.

    Args:
        df: A DataFrame with at least columns `arm`, `seed`, `focal_drift_pct`,
            `standoff_m`.
        arm: The `arm` value to filter to (e.g. `"shared_refined"`).

    Returns:
        A dict with keys:
          - `arm`: the arm analyzed.
          - `n_seeds`: number of seeds with a computable per-seed correlation.
          - `per_seed_correlation`: dict of `{seed: correlation}` (NaN dropped).
          - `n_seeds_negative` / `n_seeds_positive`: sign counts of the
            per-seed correlations (a NaN correlation, e.g. from constant
            `standoff_m` within a seed, counts toward neither).
          - `mean_within_seed_correlation`: mean of the per-seed correlations
            (NaN-dropped).
          - `p_one_sided`: exact one-sided sign-test p-value. `2 ** -n_seeds`
            when every counted seed's sign agrees; the exact upper-tail
            binomial otherwise. Field is named `p_one_sided` -- never read it
            as two-sided (T-19.5-03-02).
    """
    arm_df = df[df["arm"] == arm]
    per_seed_corr: dict[int, float] = {}
    for seed, group in arm_df.groupby("seed"):
        corr = group["focal_drift_pct"].corr(group["standoff_m"])
        if pd.notna(corr):
            per_seed_corr[int(seed)] = float(corr)

    n_seeds = len(per_seed_corr)
    n_pos = sum(1 for c in per_seed_corr.values() if c > 0)
    n_neg = sum(1 for c in per_seed_corr.values() if c < 0)
    mean_corr = sum(per_seed_corr.values()) / n_seeds if n_seeds > 0 else float("nan")

    if n_seeds == 0:
        p_one_sided = float("nan")
    else:
        n_agree = max(n_pos, n_neg)
        if n_agree == n_seeds:
            p_one_sided = 2.0**-n_seeds
        else:
            p_one_sided = (
                sum(comb(n_seeds, k) for k in range(n_agree, n_seeds + 1)) / 2**n_seeds
            )

    return {
        "arm": arm,
        "n_seeds": n_seeds,
        "per_seed_correlation": per_seed_corr,
        "n_seeds_negative": n_neg,
        "n_seeds_positive": n_pos,
        "mean_within_seed_correlation": mean_corr,
        "p_one_sided": p_one_sided,
    }


def paired_arm_difference(
    df: pd.DataFrame, arm_a: str, arm_b: str, column: str
) -> dict:
    """Per-seed paired difference in `column` between two arms.

    Both arms are evaluated on the same seed's scenario, so the comparison
    that matters is the within-seed difference, never a comparison of the two
    arms' marginal spreads (T-19.5-03-01). Rejects, rather than silently
    degrades to an unpaired comparison, when the two arms do not share an
    identical seed set.

    Args:
        df: A DataFrame with at least columns `arm`, `seed`, and `column`.
        arm_a: First arm (difference is `arm_b - arm_a`... see `diff` below).
        arm_b: Second arm.
        column: Numeric column to difference, aggregated per seed via mean
            across cameras (matching `analyze_e7_spread.py`'s per-seed mean).

    Returns:
        A dict with `arm_a`, `arm_b`, `column`, `n_seeds`, `per_seed_diff`
        (dict of `{seed: arm_b_value - arm_a_value}`), `mean_diff`.

    Raises:
        ValueError: If `arm_a` or `arm_b` is absent from `df`, or if the two
            arms' seed sets are not identical.
    """
    df_a = df[df["arm"] == arm_a]
    df_b = df[df["arm"] == arm_b]
    if df_a.empty:
        raise ValueError(f"paired_arm_difference: arm {arm_a!r} not present in df")
    if df_b.empty:
        raise ValueError(f"paired_arm_difference: arm {arm_b!r} not present in df")

    seeds_a = set(df_a["seed"].unique())
    seeds_b = set(df_b["seed"].unique())
    if seeds_a != seeds_b:
        raise ValueError(
            f"paired_arm_difference: arm {arm_a!r} seeds {sorted(seeds_a)} != "
            f"arm {arm_b!r} seeds {sorted(seeds_b)}; pairing requires an "
            "identical seed set and must not silently degrade to an unpaired "
            "comparison"
        )

    mean_a = df_a.groupby("seed")[column].mean()
    mean_b = df_b.groupby("seed")[column].mean()
    diff = mean_b - mean_a

    per_seed_diff = {int(seed): float(value) for seed, value in diff.items()}
    n_seeds = len(per_seed_diff)
    mean_diff = diff.mean() if n_seeds > 0 else float("nan")

    return {
        "arm_a": arm_a,
        "arm_b": arm_b,
        "column": column,
        "n_seeds": n_seeds,
        "per_seed_diff": per_seed_diff,
        "mean_diff": float(mean_diff),
    }


def degeneracy_verdict(association: dict, alpha: float = 0.05) -> str:
    """Classify a `focal_standoff_association` result into a final verdict.

    Args:
        association: The dict returned by `focal_standoff_association`.
        alpha: Significance threshold for `p_one_sided`. Default 0.05.

    Returns:
        `"underpowered"` if `n_seeds < 2` (a single seed, or zero, cannot
        support a sign test at all). Otherwise `"signature_present"` if
        `p_one_sided < alpha`, else `"no_signature"`. `"no_signature"` is a
        valid, final answer (D-19.5-07) -- it is not retried with more seeds
        or a different statistic.
    """
    n_seeds = association["n_seeds"]
    if n_seeds < 2:
        return "underpowered"
    p_one_sided = association["p_one_sided"]
    if pd.isna(p_one_sided):
        return "underpowered"
    if p_one_sided < alpha:
        return "signature_present"
    return "no_signature"


def build_focal_standoff_df(df: pd.DataFrame) -> pd.DataFrame:
    """Build the four-row (one per arm) `e7_focal_standoff.csv` artifact.

    Args:
        df: The loaded `interface_ablation_band.csv` DataFrame.

    Returns:
        A DataFrame with columns `arm`, `n_seeds`, `n_cameras_per_seed`,
        `mean_within_seed_correlation`, `n_seeds_negative`, `n_seeds_positive`,
        `p_one_sided`, `verdict`, `scope` -- one row per arm in `ARMS`.
    """
    rows = []
    for arm in ARMS:
        arm_df = df[df["arm"] == arm]
        association = focal_standoff_association(df, arm)
        verdict = degeneracy_verdict(association)
        n_cameras_per_seed = (
            int(arm_df.groupby("seed").size().iloc[0]) if not arm_df.empty else 0
        )
        rows.append(
            {
                "arm": arm,
                "n_seeds": association["n_seeds"],
                "n_cameras_per_seed": n_cameras_per_seed,
                "mean_within_seed_correlation": association[
                    "mean_within_seed_correlation"
                ],
                "n_seeds_negative": association["n_seeds_negative"],
                "n_seeds_positive": association["n_seeds_positive"],
                "p_one_sided": association["p_one_sided"],
                "verdict": verdict,
                "scope": SCOPE_TEXT,
            }
        )
    return pd.DataFrame(rows)


def build_arg_parser() -> argparse.ArgumentParser:
    """Build this script's CLI parser: the shared five-flag contract, no extras."""
    parser = argparse.ArgumentParser(
        description=__doc__, parents=[build_experiment_arg_parser()]
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for `python -m experiments.e7_focal_standoff_analysis`.

    Reads `experiments/results/interface_ablation_band.csv` (read-only, never
    the `--out` directory -- the input is a fixed, already-committed
    artifact) and writes `e7_focal_standoff.csv` into `--out`
    (`resolve_out_dir`-resolved, default `experiments/results`).
    """
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    validate_args(parser, args)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    band_path = Path("experiments/results") / BAND_CSV_NAME
    if not band_path.is_file():
        print(f"ERROR: {band_path} not found -- nothing to analyze.", file=sys.stderr)
        return 1

    band_df = pd.read_csv(band_path)
    result_df = build_focal_standoff_df(band_df)

    out_dir = resolve_out_dir(args.out)
    write_experiment_csv(
        result_df,
        out_dir / OUTPUT_CSV_NAME,
        key_columns=["arm"],
        # Always overwrite: this is a deterministic re-analysis of a fixed
        # committed input, the same "regenerating IS the point" posture as
        # the `exp1_band.csv` / `interface_ablation_band.csv` band writers.
        force=True,
    )
    print(result_df.to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
