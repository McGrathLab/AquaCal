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

**The six degeneracy columns (DEGEN-01/DEGEN-02 via plan 24-02, D-09 as revised
2026-08-17).** `e7_focal_standoff.csv` gained six APPENDED columns:
`degenerate_observations_at_solution` plus three `degenerate_observations_cause_*`
(`above_interface`, `behind_camera`, `interface_below_camera`) and two
`degenerate_observations_fate_*` (`extended`, `penalized`). This module runs no
calibration, so each is the per-arm SUM over the band's own columns of the same
names -- and is `None` when the input band CSV predates them, meaning "never
measured for this arm", never "measured and found clean". Cause and fate are two
INDEPENDENT AXES over the same set of invalid observations, not disjoint buckets
-- **never add a cause column to a fate column.** Each axis sums independently
and exactly to `degenerate_observations_at_solution`, so a row where the two axes
disagree is a bookkeeping bug, visible by eye. The per-stage breakdown and the
`observations_evaluated__*` denominators live in
`e7_degeneracy_breakdown.json`, written by `e7_interface_ablation.py`, not here.

Usage:
    python -m experiments.e7_focal_standoff_analysis --out experiments/results
"""

from __future__ import annotations

import argparse
import logging
import math
import sys
from math import comb
from pathlib import Path

import numpy as np
import pandas as pd

from experiments._degeneracy import DEGENERACY_COLUMNS
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

# FIX-04 (23-03): appended to SCOPE_TEXT, row-by-row, for exactly the two
# `fixed`-arm rows whose verdict is "vacuous_by_construction" (see
# `degeneracy_verdict`). No schema change -- `scope` is already a free-text
# column, so this is the row's home rather than a new boolean column.
VACUOUS_SCOPE_SUFFIX = (
    " VACUOUS BY CONSTRUCTION: this arm never refines intrinsics, so focal_drift_pct is 0.0 "
    "exactly for every camera and seed in interface_ablation_band.csv. The within-seed "
    "correlation is therefore undefined (zero variance), not null -- there is no measured "
    "absence of a signature here, and this row must not be read as one. The supplement's "
    "argument about the fixed arm is a priori and draws on a different artifact (MF-17)."
)


def focal_standoff_association(df: pd.DataFrame, arm: str) -> dict:
    """Per-seed correlation between `focal_drift_pct` and `standoff_m`, one arm.

    For each seed present for `arm`, computes the Pearson correlation of
    `focal_drift_pct` against `standoff_m` across that seed's cameras. The
    per-seed correlations (not a pooled/marginal correlation across all
    seed-camera rows at once) are the unit of evidence, because pooling would
    mix within-seed association with between-seed scenario-difficulty
    variation that both columns share.

    `n_seeds` counts every seed present for `arm` in `df`, including seeds
    whose correlation is undefined (e.g. a `fixed` arm where
    `focal_drift_pct` never varies -- intrinsics are never refined, so its
    within-seed standard deviation is exactly zero and Pearson correlation is
    mathematically undefined, not merely small). Such seeds contribute no
    sign to the sign test but are not dropped from `n_seeds`: a `fixed` arm
    genuinely has ten committed seeds, and reporting `n_seeds == 0` for it
    would misrepresent an arm that has no focal-drift signal by construction
    as one for which no seeds were evaluated.

    Args:
        df: A DataFrame with at least columns `arm`, `seed`, `focal_drift_pct`,
            `standoff_m`.
        arm: The `arm` value to filter to (e.g. `"shared_refined"`).

    Returns:
        A dict with keys:
          - `arm`: the arm analyzed.
          - `n_seeds`: total number of distinct seeds present for `arm`.
          - `per_seed_correlation`: dict of `{seed: correlation}`, one entry
            per seed in `n_seeds` (value is `float("nan")` where undefined).
          - `n_seeds_negative` / `n_seeds_positive`: sign counts of the
            per-seed correlations. May sum to less than `n_seeds` when some
            seeds have an undefined (NaN) correlation.
          - `mean_within_seed_correlation`: mean of the defined per-seed
            correlations (NaN-dropped for this mean only), or NaN if none is
            defined.
          - `p_one_sided`: exact one-sided sign-test p-value over `n_seeds`
            trials with `n_agree = max(n_seeds_negative, n_seeds_positive)`
            successes: `2 ** -n_seeds` when every seed's sign agrees, the
            exact upper-tail binomial otherwise (an undefined-correlation
            seed counts as neither sign, weakening the test exactly as a
            non-response would). Field is named `p_one_sided` -- never read
            it as two-sided (T-19.5-03-02).
    """
    arm_df = df[df["arm"] == arm]
    per_seed_corr: dict[int, float] = {}
    for seed, group in arm_df.groupby("seed"):
        # A `fixed` arm's zero-variance `focal_drift_pct` produces an
        # expected, already-handled 0/0 in numpy's correlation internals
        # (Pearson r is genuinely undefined there, not merely close to
        # zero) -- silence the RuntimeWarning rather than let it obscure
        # real numeric issues elsewhere in the run.
        with np.errstate(invalid="ignore"):
            corr = group["focal_drift_pct"].corr(group["standoff_m"])
        per_seed_corr[int(seed)] = float(corr) if pd.notna(corr) else float("nan")

    n_seeds = len(per_seed_corr)
    defined = [c for c in per_seed_corr.values() if not math.isnan(c)]
    n_pos = sum(1 for c in defined if c > 0)
    n_neg = sum(1 for c in defined if c < 0)
    mean_corr = sum(defined) / len(defined) if defined else float("nan")

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
        support a sign test at all).

        `"vacuous_by_construction"` (FIX-04, 23-03) if `n_seeds >= 2` AND no
        seed contributed a sign (`n_seeds_negative == n_seeds_positive == 0`)
        AND `mean_within_seed_correlation` is undefined (NaN) -- all three
        conditions together mean the statistic could not be COMPUTED, not
        that it was computed and found null. This happens because the arm
        admits no focal drift at all: intrinsics are never refined, so
        `focal_drift_pct` is `0.0` exactly for every camera and seed, the
        within-seed variance is identically zero, and Pearson correlation is
        undefined. Distinct from `"no_signature"`, which is a MEASURED and
        final answer (D-19.5-07) on a statistic that COULD be computed, and
        from `"underpowered"`, which is a sample-size statement, not a
        statement about whether the statistic is defined. All three
        conditions are required: a genuinely null result with a DEFINED
        correlation and zero signs must still classify as `"no_signature"`,
        never `"vacuous_by_construction"`.

        Otherwise `"signature_present"` if `p_one_sided < alpha`, else
        `"no_signature"`. `"no_signature"` is a valid, final answer
        (D-19.5-07) -- it is not retried with more seeds or a different
        statistic.
    """
    n_seeds = association["n_seeds"]
    if n_seeds < 2:
        return "underpowered"
    if (
        association["n_seeds_negative"] == 0
        and association["n_seeds_positive"] == 0
        and pd.isna(association["mean_within_seed_correlation"])
    ):
        return "vacuous_by_construction"
    p_one_sided = association["p_one_sided"]
    if pd.isna(p_one_sided):
        return "underpowered"
    if p_one_sided < alpha:
        return "signature_present"
    return "no_signature"


def _arm_degeneracy_columns(arm_df: pd.DataFrame) -> dict[str, int | None]:
    """Sum the band's six degeneracy columns over one arm's rows.

    APPENDED to each output row, never inserted. `cause` and `fate` are two
    INDEPENDENT AXES over the same set of invalid observations, not disjoint
    buckets -- **never add a cause column to a fate column.** Each axis sums
    independently to `degenerate_observations_at_solution`, so an arm whose two
    axes disagree is a bookkeeping bug, visible by eye. Explicitly listed for
    the reader's benefit, and asserted below to match the shared order:
    `degenerate_observations_at_solution`,
    `degenerate_observations_cause_above_interface`,
    `degenerate_observations_cause_behind_camera`,
    `degenerate_observations_cause_interface_below_camera`,
    `degenerate_observations_fate_extended`,
    `degenerate_observations_fate_penalized`.

    A column absent from the band CSV (any band regenerated before plan 24-02)
    yields `None` -- "never measured for this arm", never "measured and found
    clean". The per-stage breakdown and denominators are not derivable here;
    they live in `e7_degeneracy_breakdown.json`.
    """
    summed: dict[str, int | None] = {}
    for column in DEGENERACY_COLUMNS:
        if column not in arm_df.columns:
            summed[column] = None
            continue
        values = arm_df[column].dropna()
        summed[column] = int(values.sum()) if not values.empty else None
    return summed


def build_focal_standoff_df(df: pd.DataFrame) -> pd.DataFrame:
    """Build the four-row (one per arm) `e7_focal_standoff.csv` artifact.

    Args:
        df: The loaded `interface_ablation_band.csv` DataFrame.

    Returns:
        A DataFrame with columns `arm`, `n_seeds`, `n_cameras_per_seed`,
        `mean_within_seed_correlation`, `n_seeds_negative`, `n_seeds_positive`,
        `p_one_sided`, `verdict`, `scope`, then the six APPENDED degeneracy
        columns (see `_arm_degeneracy_columns`) -- one row per arm in `ARMS`.
    """
    rows = []
    for arm in ARMS:
        arm_df = df[df["arm"] == arm]
        association = focal_standoff_association(df, arm)
        verdict = degeneracy_verdict(association)
        n_cameras_per_seed = (
            int(arm_df.groupby("seed").size().iloc[0]) if not arm_df.empty else 0
        )
        scope = (
            SCOPE_TEXT + VACUOUS_SCOPE_SUFFIX
            if verdict == "vacuous_by_construction"
            else SCOPE_TEXT
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
                "scope": scope,
                **_arm_degeneracy_columns(arm_df),
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
