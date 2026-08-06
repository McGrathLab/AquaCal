"""COV-08, bootstrap half: a frame-clustered bootstrap CI over the committed
reconstruction inter-corner comparisons (D-19.5-05).

Invoked as `python -m experiments.reconstruction_bootstrap`. Inherits the
shared five-flag CLI contract (`--seed`, `--out`, `--force`, `--smoke`,
`--check`) from `experiments._io.build_experiment_arg_parser` (D-21). This
script performs no calibration and no scenario generation -- it is pure
post-hoc re-analysis of the already-committed
`experiments/results/reconstruction_errors.csv` (7,762 rows across 52
distinct `frame_idx` values).

**The resampling unit is the frame, not the row.** Rows sharing a
`frame_idx` share an estimated board pose and the same camera geometry, so
they are not independent draws; a naive per-row bootstrap understates the
interval (see `cluster_bootstrap`'s docstring and the design decision in
`19.5-04-PLAN.md`).

**Scope, stated once here and required verbatim in the written artifact
(D-19.5-05):** this interval resamples the inter-corner comparisons of ONE
calibration. It bounds metric sampling variance only -- it is NOT a
calibration band and must never be presented as one.

Emits, into `--out` (default `experiments/results/`):
    - `reconstruction_bootstrap.json` -- point estimates, 95% percentile CIs,
      n_frames/n_rows/n_resamples/seed, the scope statement, and a
      `point_estimate_matches_real_rig_metrics` cross-check against the
      published `real_rig_metrics.json` values.
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from aquacal.io import capture_environment
from experiments._io import (
    build_experiment_arg_parser,
    resolve_out_dir,
    validate_args,
)

logger = logging.getLogger(__name__)

RECONSTRUCTION_ERRORS_PATH = Path("experiments/results/reconstruction_errors.csv")
REAL_RIG_METRICS_PATH = Path("experiments/results/real_rig_metrics.json")
CLUSTER_COLUMN = "frame_idx"
FULL_N_RESAMPLES = 10_000
SMOKE_N_RESAMPLES = 200
CI_ALPHA = 0.05
POINT_ESTIMATE_RTOL = 1e-9

SCOPE_STATEMENT = (
    "metric sampling variance only -- this interval resamples the "
    "inter-corner comparisons of ONE calibration; it is not a calibration "
    "band and must never be presented as one (D-19.5-05)."
)

# `real_rig_metrics.json`'s keys, matched against `reconstruction_statistics`'
# own field names (no `signed_mean_mm` is published there -- only the two
# magnitude statistics are cross-checked).
_REAL_RIG_METRICS_MAP = {
    "reconstruction_rmse_mm": "inter_corner_rmse_mm",
    "reconstruction_mae_mm": "inter_corner_mae_mm",
}


def cluster_bootstrap(
    df: pd.DataFrame,
    cluster_column: str,
    statistic: Callable[[pd.DataFrame], float],
    n_resamples: int,
    rng: np.random.Generator,
) -> NDArray:
    """Resample `df` at the cluster level, with replacement, `n_resamples` times.

    The resampling unit is a whole cluster (every row sharing one
    `cluster_column` value), never an individual row -- this is the single
    property that distinguishes a cluster bootstrap from a naive per-row
    bootstrap, and it is what makes the resulting interval honest about
    correlated observations (rows sharing a `frame_idx` share one estimated
    board pose and camera geometry, so they are not independent draws).

    Each resample draws exactly `n_clusters` cluster labels (with
    replacement, so a label may repeat or be absent), concatenates every row
    belonging to each drawn label -- in draw order, so a repeated label
    contributes its rows once per draw -- and applies `statistic` to the
    concatenated frame.

    Args:
        df: The full, un-resampled data.
        cluster_column: Column in `df` naming the resampling unit (e.g.
            `"frame_idx"`).
        statistic: A callable taking one concatenated-resample `DataFrame`
            and returning a single float.
        n_resamples: Number of bootstrap resamples to draw.
        rng: An explicit `np.random.Generator` -- results are reproducible
            from a seed via `np.random.default_rng(seed)`.

    Returns:
        A length-`n_resamples` array of `statistic`'s value on each resample,
        in draw order.
    """
    labels = np.asarray(df[cluster_column].unique())
    n_clusters = len(labels)
    grouped = {label: sub for label, sub in df.groupby(cluster_column)}

    samples = np.empty(n_resamples, dtype=float)
    for i in range(n_resamples):
        drawn_labels = rng.choice(labels, size=n_clusters, replace=True)
        resampled = pd.concat(
            [grouped[label] for label in drawn_labels], ignore_index=True
        )
        samples[i] = statistic(resampled)
    return samples


def reconstruction_statistics(df: pd.DataFrame) -> dict[str, float]:
    """Compute the manuscript's point estimates from `signed_error_m`, in mm.

    Args:
        df: A frame carrying a `signed_error_m` column (metres).

    Returns:
        A dict with `reconstruction_rmse_mm`, `reconstruction_mae_mm`, and
        `signed_mean_mm` -- the same vocabulary already used elsewhere in
        `experiments/results/`.
    """
    signed_error_mm = df["signed_error_m"].to_numpy(dtype=float) * 1000.0
    return {
        "reconstruction_rmse_mm": float(np.sqrt(np.mean(signed_error_mm**2))),
        "reconstruction_mae_mm": float(np.mean(np.abs(signed_error_mm))),
        "signed_mean_mm": float(np.mean(signed_error_mm)),
    }


def percentile_ci(samples: NDArray, alpha: float = 0.05) -> tuple[float, float]:
    """Compute a two-sided percentile confidence interval.

    Args:
        samples: Bootstrap resample statistic values.
        alpha: Interval carries `1 - alpha` coverage (default 0.05 -> 95%).

    Returns:
        `(low, high)`, the `alpha / 2` and `1 - alpha / 2` percentiles.
    """
    low = float(np.percentile(samples, 100 * alpha / 2))
    high = float(np.percentile(samples, 100 * (1 - alpha / 2)))
    return low, high


def _load_reconstruction_errors() -> pd.DataFrame:
    return pd.read_csv(RECONSTRUCTION_ERRORS_PATH)


def _load_real_rig_metrics() -> dict:
    with open(REAL_RIG_METRICS_PATH) as f:
        return json.load(f)


def _run(seed: int, n_resamples: int) -> dict:
    """Load the committed comparisons, bootstrap, and assemble the artifact dict."""
    df = _load_reconstruction_errors()
    n_rows = len(df)
    n_frames = int(df[CLUSTER_COLUMN].nunique())

    point_estimates = reconstruction_statistics(df)

    start = time.monotonic()
    seed_seq = np.random.SeedSequence(seed)
    stat_names = ["reconstruction_rmse_mm", "reconstruction_mae_mm", "signed_mean_mm"]
    ci_95: dict[str, list[float]] = {}
    for stat_name, child_seed in zip(stat_names, seed_seq.spawn(len(stat_names))):
        rng = np.random.default_rng(child_seed)

        def statistic(resampled: pd.DataFrame, _name: str = stat_name) -> float:
            return reconstruction_statistics(resampled)[_name]

        samples = cluster_bootstrap(df, CLUSTER_COLUMN, statistic, n_resamples, rng)
        low, high = percentile_ci(samples, alpha=CI_ALPHA)
        ci_95[stat_name] = [low, high]
    seconds = time.monotonic() - start

    real_rig_metrics = _load_real_rig_metrics()
    point_estimate_matches_real_rig_metrics = all(
        abs(point_estimates[local_key] - real_rig_metrics[remote_key])
        <= POINT_ESTIMATE_RTOL * abs(real_rig_metrics[remote_key])
        for local_key, remote_key in _REAL_RIG_METRICS_MAP.items()
    )

    environment = capture_environment()
    return {
        "experiment": "reconstruction_bootstrap",
        "schema_version": 1,
        "git_sha": environment.get("git_sha"),
        "seconds": seconds,
        "seed": seed,
        "solver_config": {"seed": seed},
        "n_resamples": n_resamples,
        "n_rows": n_rows,
        "n_frames": n_frames,
        "cluster_column": CLUSTER_COLUMN,
        "point_estimates": point_estimates,
        "ci_95": ci_95,
        "point_estimate_matches_real_rig_metrics": point_estimate_matches_real_rig_metrics,
        "scope": SCOPE_STATEMENT,
        "environment": environment,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    """Build this script's CLI parser (the shared five-flag contract, unmodified)."""
    return argparse.ArgumentParser(
        description=__doc__, parents=[build_experiment_arg_parser()]
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for `python -m experiments.reconstruction_bootstrap`."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    validate_args(parser, args)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    out_dir = resolve_out_dir(args.out)
    path = out_dir / "reconstruction_bootstrap.json"
    if path.exists() and not args.force and not args.check:
        logger.info(
            "Skipping write to %s: file already exists and --force was not "
            "given (resumability).",
            path,
        )
        return 0

    n_resamples = SMOKE_N_RESAMPLES if args.smoke else FULL_N_RESAMPLES
    record = _run(seed=args.seed, n_resamples=n_resamples)

    if args.check:
        if not path.exists():
            print(f"No committed baseline at {path} to check against.")
            return 1
        with open(path) as f:
            committed = json.load(f)
        mismatches = []
        if committed.get("n_rows") != record["n_rows"]:
            mismatches.append("n_rows")
        if committed.get("n_frames") != record["n_frames"]:
            mismatches.append("n_frames")
        if not record["point_estimate_matches_real_rig_metrics"]:
            mismatches.append("point_estimate_matches_real_rig_metrics")
        if mismatches:
            print(f"reconstruction_bootstrap.json: mismatched fields {mismatches}")
            return 1
        print("reconstruction_bootstrap.json: matches committed baseline.")
        return 0

    with open(path, "w") as f:
        json.dump(record, f, indent=2, sort_keys=True)
    logger.info("Wrote %s (%.2f s)", path, record["seconds"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
