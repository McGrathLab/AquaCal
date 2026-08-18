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

Per-observation classification (DEGEN-04, plan 25-03)
-----------------------------------------------------

Plan 25-01 gave `compute_residuals` a per-observation sink that emits RAW
geometry and an int8 `nan_reason` code for every flagged observation. The
library spells no bucket name (D-06); this module owns the whole taxonomy,
which is what let it be revised twice in two days -- obliquity retired,
camera-model failure added -- without touching the solver.

`OBSERVATION_BUCKETS` maps each `NAN_REASON_*` code to exactly one bucket, and
`classify_degenerate_observations` derives the bucket **from the code alone**.

**What `h_q` is.** `h_q = Q_z - z_int` is the corner's depth below the
*estimated* water surface in the +Z-down world frame, in meters. Positive means
submerged. `h_q <= 0` means the corner is at or above the interface, so no
refracted path exists and the projector returns NaN tagged
`NAN_REASON_ABOVE_INTERFACE`. It is a statement about the **estimate**, not
about reality -- both `Q_z` and `z_int` are free parameters, so solver excursion
reaches it too -- and it is evaluated **at the solution**.

*Falsification note.* `19.3-ORCHESTRATOR-NOTES.md` s4 misread the `ideal`
preset precisely by comparing a solution-state count against a ground-truth
statement. That reading must not be restored: a non-zero count at the solution
is not a claim that the authored scenario placed a corner above the water.

**Pre-registered expectation** (recorded here so the eventual finding is
falsifiable rather than post-hoc):

* bucket (a) `above_interface` should dominate;
* bucket (c) `interface_below_camera` is dead for E2 by measurement --
  `h_c` = 1.0472-1.1125 m across all 13 cameras;
* obliquity / total internal reflection is retired, not merely unobserved:
  `refract_ray` holds the only `sin_t_sq > 1` check and has zero callers in
  `src/`, and the Newton solve gives theta_w < 48.61 deg by construction for
  this direction of travel.

`chord_incidence_deg` in these rows is a straight-chord surrogate, **not** the
refracted exit angle: the Newton loop never runs for a flagged observation, so
no refraction point exists to take an angle at.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd

from aquacal.core import (
    NAN_REASON_ABOVE_INTERFACE,
    NAN_REASON_BEHIND_CAMERA,
    NAN_REASON_INTERFACE_BELOW_CAMERA,
    NAN_REASON_NONE,
)

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

#: The closed per-observation bucket vocabulary (D-06). One bucket per
#: `NAN_REASON_*` code, and the codes are IMPORTED from `aquacal.core` rather
#: than hardcoded as integers: a code renumbered in the library must not
#: silently re-point a bucket here. The library spells none of these names --
#: it emits the int8 code and nothing else -- which is why the taxonomy could
#: be revised twice in two days without a solver edit.
#:
#: (a) `above_interface`      -- the corner is at or above the ESTIMATED water
#:     surface at the solution, so no refracted path exists.
#: (b) `camera_model_failure` -- the D-04 tripwire. The geometry was fine and
#:     the pixel was not.
#: (c) `interface_below_camera` -- the estimated interface fell below an
#:     estimated camera center. A convergence diagnostic of solver excursion,
#:     NEVER a claim that hardware was submerged.
#:     `unflagged`            -- code 0, a clean observation. Present so the
#:     mapping is total over the code space; the flagged sink never emits it.
OBSERVATION_BUCKETS: dict[int, str] = {
    NAN_REASON_NONE: "unflagged",
    NAN_REASON_INTERFACE_BELOW_CAMERA: "interface_below_camera",
    NAN_REASON_ABOVE_INTERFACE: "above_interface",
    NAN_REASON_BEHIND_CAMERA: "camera_model_failure",
}

#: The discriminator column. Its ABSENCE means "never computed for these rows",
#: never "computed and found clean" -- the same trap `summarize_degeneracy_
#: columns` guards against before its `.get(..., 0)` calls.
NAN_REASON_COLUMN = "nan_reason"

#: The column `classify_degenerate_observations` appends.
BUCKET_COLUMN = "bucket"

#: The free-text provenance column the classification table carries in its own
#: body (D-03, D-10), following the FIX-04 `scope` precedent in
#: `e7_focal_standoff.csv`: one identical sentence on every row. A leading `#`
#: comment line was rejected -- it breaks `pd.read_csv` and every downstream
#: consumer -- and a separate `*_provenance.json` fails D-10's "a reader of the
#: file alone" requirement.
PROVENANCE_COLUMN = "provenance"


def observation_bucket(nan_reason: int) -> str:
    """Map one `NAN_REASON_*` code to its bucket name.

    Args:
        nan_reason: An int8 code as the library's `nan_reason_out` sink wrote
            it. Must be a key of `OBSERVATION_BUCKETS`.

    Returns:
        The bucket name.

    Raises:
        ValueError: If the code is outside the closed vocabulary. Catching that
            is what the closed vocabulary is for -- a code added to the library
            without a bucket here must fail loudly, not land in a silent
            default bucket.
    """
    try:
        return OBSERVATION_BUCKETS[int(nan_reason)]
    except (KeyError, TypeError, ValueError):
        raise ValueError(
            f"unrecognized nan_reason code {nan_reason!r}; legal codes are "
            f"{sorted(OBSERVATION_BUCKETS)}"
        ) from None


def classify_degenerate_observations(rows) -> pd.DataFrame:
    """Name every flagged observation's bucket, offline, from its code alone.

    Args:
        rows: The per-observation detail rows plan 25-01's
            `degeneracy_details_out` sink produced -- either the raw
            `list[dict]` or a `pd.DataFrame` read back from
            `degenerate_observations.csv`. Must carry a `nan_reason` column.

    Returns:
        A `pd.DataFrame` with every input column plus `bucket`. Zero input rows
        returns an empty frame that still carries `bucket`: for the flagged
        sink, zero rows is a genuine measured-and-clean result.

    Raises:
        ValueError: If `rows` is `None`, or if non-empty input lacks the
            `nan_reason` discriminator column, or if any code is outside
            `OBSERVATION_BUCKETS`.
    """
    if rows is None:
        raise ValueError(
            "rows is None: 'never computed' cannot be represented as a "
            "classification frame. Pass an empty list for a clean run."
        )

    df = rows.copy() if isinstance(rows, pd.DataFrame) else pd.DataFrame(list(rows))

    if df.empty:
        # A clean run genuinely flags nothing. Distinguished from the
        # column-missing case below, which raises: an empty frame here must not
        # be produced by a missing column silently flooring to zero rows.
        empty = df.copy()
        empty[BUCKET_COLUMN] = pd.Series(dtype=object)
        return empty

    # Discriminator guard BEFORE any per-row read, mirroring
    # `summarize_degeneracy_columns`: absence of the code column means the
    # instrumentation never ran for these rows, which must never read as
    # "measured and found clean".
    if NAN_REASON_COLUMN not in df.columns:
        raise ValueError(
            f"input rows carry no {NAN_REASON_COLUMN!r} column, so the bucket "
            "was never computed for them; refusing to classify. Columns "
            f"present: {list(df.columns)}"
        )

    # The bucket is derived from `nan_reason` ONLY. Bucket (b)
    # `camera_model_failure` is NAN_REASON_BEHIND_CAMERA *with h_q > 0*: the
    # geometry was fine and the pixel was not, and that is the D-04 tripwire
    # condition. Re-deriving a predicate on `h_q_m` here would be a second
    # derivation that can disagree with the projector's -- the projector
    # already assigns exactly one cause per point, and that assignment is the
    # record.
    df[BUCKET_COLUMN] = [observation_bucket(code) for code in df[NAN_REASON_COLUMN]]
    return df


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
    # A NON-EMPTY dict from before this phase (a run that recorded e.g.
    # `pnp_guard_rejected` but none of the split keys) would otherwise floor to
    # 0 on every column via `.get(..., 0)`, reading as "measured and found
    # clean" for precisely the artifact class this convention protects. Absence
    # of the merged key is the discriminator: the library always seeds it when
    # the instrumentation ran, so missing means never computed.
    if not discard_stats or MERGED_DEGENERACY_COLUMN not in discard_stats:
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


def write_degeneracy_breakdown(
    path: Path, breakdown: dict[str, dict], force: bool = False
) -> None:
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
        force: Overwrite an existing sidecar. Defaults to `False`, matching the
            `write_experiment_csv(..., force=args.force)` convention every
            sibling artifact in these scripts already follows. Without it a bare
            re-run silently clobbers a committed sidecar.
    """
    path = Path(path)
    if path.exists() and not force:
        logger.warning(
            "Refusing to overwrite existing degeneracy breakdown sidecar %s "
            "-- re-run with --force to replace it.",
            path,
        )
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(breakdown, f, indent=2, sort_keys=True)
    logger.info("Wrote degeneracy breakdown sidecar to %s", path)
