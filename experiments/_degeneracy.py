"""Shared degeneracy-column and sidecar helpers for E1/E5/E7 (DEGEN-01, plan 24-02).

Plan 24-01 split the merged counter `degenerate_observations_at_solution` into
TWO INDEPENDENT AXES over the same set of invalid observations:

* **cause** -- *why* the refractive projector could not evaluate the
  observation: `above_interface`, `behind_camera`, `interface_below_camera`.
* **fate** -- *what the solver did about it*: `extended` (C0 continuation) or
  `penalized` (flat penalty, zero gradient).

Both are marginals of the same set, so **a cause count and a fate count must
never be added together** -- doing so double-counts. Each axis sums
independently and exactly to `degenerate_observations_at_solution`, which is
why publishing both is safe *and* useful: a row where the two axes disagree is
a bookkeeping bug, visible by eye.

The library records these per stage, as
`degenerate_observations_{axis}_{name}__{stage}` plus an
`observations_evaluated__{stage}` denominator. The CSV columns here are the
CROSS-STAGE SUM of each name; the full per-stage breakdown and the
denominators go to the `e{N}_degeneracy_breakdown.json` sidecar (D-09 as
revised 2026-08-17), never into a CSV.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

MERGED_DEGENERACY_COLUMN = "degenerate_observations_at_solution"

#: The three causes and two fates, in the order their columns appear.
DEGENERACY_CAUSES = ("above_interface", "behind_camera", "interface_below_camera")
DEGENERACY_FATES = ("extended", "penalized")

#: The six append-only CSV columns, in the order every experiment appends them.
#: The `cause_`/`fate_` segment is a double-count mitigation, not decoration --
#: it is what stops a reader summing across the two axes -- and matches the
#: library's own `DISCARD_KEYS` spelling exactly, so the columns sit beside
#: E6's already-committed `degenerate_observations_at_solution` column without
#: a spelling discontinuity.
DEGENERACY_COLUMNS: tuple[str, ...] = (
    MERGED_DEGENERACY_COLUMN,
    "degenerate_observations_cause_above_interface",
    "degenerate_observations_cause_behind_camera",
    "degenerate_observations_cause_interface_below_camera",
    "degenerate_observations_fate_extended",
    "degenerate_observations_fate_penalized",
)


def _cross_stage_sum(discard_stats: dict, prefix: str) -> int:
    """Sum every `<prefix>__<stage>` entry, over whatever stages are present.

    Prefix matching rather than an explicit stage list: a stage added to the
    library's vocabulary later is then summed in automatically, which is the
    same structural argument that made `benchmark.json` carry the whole
    `discard_stats` dict (D-11).
    """
    return sum(
        int(value)
        for key, value in discard_stats.items()
        if key.startswith(prefix + "__")
    )


def summarize_degeneracy_columns(
    discard_stats: dict | None,
) -> dict[str, int | None]:
    """Collapse a raw `discard_stats` dict into the six CSV column values.

    Args:
        discard_stats: The raw counter dict the library filled via a
            `discard_stats_out` sink, or `None`/empty when the counts were
            never computed for this row (a failed, skipped, or
            pre-instrumentation row).

    Returns:
        A dict with exactly `DEGENERACY_COLUMNS` as keys, in that order.
        Every value is `None` when `discard_stats` is `None` or empty --
        `None` means "never computed for this row", never "computed and found
        to be zero" (E6's `_build_row` convention). Otherwise every value is
        an int, and the three `cause_` values and the two `fate_` values each
        sum independently to `degenerate_observations_at_solution`.
    """
    if not discard_stats:
        return {column: None for column in DEGENERACY_COLUMNS}

    summary: dict[str, int | None] = {
        MERGED_DEGENERACY_COLUMN: int(discard_stats.get(MERGED_DEGENERACY_COLUMN, 0))
    }
    for cause in DEGENERACY_CAUSES:
        summary[f"degenerate_observations_cause_{cause}"] = _cross_stage_sum(
            discard_stats, f"degenerate_observations_cause_{cause}"
        )
    for fate in DEGENERACY_FATES:
        summary[f"degenerate_observations_fate_{fate}"] = _cross_stage_sum(
            discard_stats, f"degenerate_observations_fate_{fate}"
        )
    return {column: summary[column] for column in DEGENERACY_COLUMNS}


def write_degeneracy_breakdown(path: Path, breakdown: dict[str, dict]) -> None:
    """Write an `e{N}_degeneracy_breakdown.json` sidecar (D-09).

    The sidecar carries what the CSV deliberately does not: the full
    cause x stage and fate x stage breakdown and the per-stage
    `observations_evaluated__<stage>` denominators -- the denominator that
    retires the hand-reconstructed `198 / 73,975 = 0.268%`, because it is
    produced by the same pass over the same data that produced the counts.

    Args:
        path: Destination path, conventionally
            `<out_dir>/e{N}_degeneracy_breakdown.json`. Deliberately distinct
            from the band-owned `e{N}_seed_band_provenance.json` sidecars.
        breakdown: Top-level object keyed by the run's arm/configuration
            identifier (E1: model label; E5: `n_assumed` or `"band"`; E7: arm
            name), each value the RAW `discard_stats` dict as the library
            returned it, unaggregated. Writing the raw dict rather than a
            curated subset is deliberate and is the same structural argument
            as D-11: a counter added later arrives here without this module
            naming it.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(breakdown, f, indent=2, sort_keys=True)
    logger.info("Wrote degeneracy breakdown sidecar to %s", path)
