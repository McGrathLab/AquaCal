"""Discriminator for plan 28's hard stop, plus phase 19.3's cell-reproduction report.

Original purpose (plan 19.2-28)
-------------------------------
The E6 re-run moved 63 of 308 cells (worst rel 6.1e-5). Two candidate causes:
  (a) plan 27's diagnostics_out/discard_stats_out sinks are not inert, or
  (b) E6 is simply not bit-reproducible run-to-run.

This runs the SAME configuration TWICE on IDENTICAL code. If the two runs differ,
(b) is proven and plan 27 is exonerated -- no code change can explain a difference
between two runs of the same code.

Writes only to temp dirs; never touches experiments/results/.

Added in phase 19.3 (plan 10 Task 1): ``--report``
--------------------------------------------------
Computes the cell-reproduction count between two E6 sweep CSVs using the SAME
definition that produced the 63/308 pre-fix baseline, so the two numbers are
comparable. The definition is not re-invented here -- it is pinned by a
self-test: ``--report`` first re-derives the pre-fix pair and asserts it
reproduces exactly 63 of 308 before reporting any post-fix number. If that
self-test fails, the definition has drifted and the post-fix figure is not
comparable, so nothing is reported.

Definition (recovered by reproducing 63/308 exactly): compare the two CSVs
row-wise keyed on (axis, axis_value), over every column the two files share
EXCEPT the six identity fields below. Comparison is exact string equality on the
serialized cell -- there is no tolerance in this measurement and nothing to
loosen. 14 rows x 22 comparable columns = 308 cells.

This is a REPORTED STATISTIC, not a gate (D-19.3-14).
"""

import argparse
import csv
import sys
import tempfile
from pathlib import Path

import experiments.e6_generalization_sweep as m

CONFIGS_TO_PROBE = ["scale_half_scale", "index_1.36"]

#: Columns excluded from the cell comparison: they identify WHICH configuration a
#: row is, not what the run measured. Every other shared column participates,
#: including constant ones -- that is what makes the denominator 308 rather than
#: 280, and it is how the pre-fix baseline was counted.
IDENTITY_COLUMNS = {
    "axis",
    "axis_value",
    "model",
    "config_key",
    "is_baseline",
    "seed",
}

#: The pre-fix pair, preserved because the 2026-08-01 session's scratchpad did
#: not survive a context clear. See evidence/README.md.
PRE_FIX_A = Path(
    ".planning/phases/19.3-scenario-geometry-and-convergence/evidence/"
    "generalization_sweep_pre-optimality.csv"
)
PRE_FIX_B = Path(
    "experiments/archive/e6-2026-08-02-pre-depth-fix/generalization_sweep.csv"
)
PRE_FIX_EXPECTED_MOVED = 63
PRE_FIX_EXPECTED_CELLS = 308

#: The post-fix pair produced by plan 09's queue: repeat 1 into the shared output
#: directory, repeat 2 into an isolated one (D-19.3-20).
POST_FIX_A = Path("experiments/results/generalization_sweep.csv")
POST_FIX_B = Path("experiments/results_e6_repeat2/generalization_sweep.csv")


def _rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def compare_cells(path_a, path_b, restrict_to=None):
    """Count cells that differ between two E6 sweep CSVs.

    Args:
        restrict_to: If given, compare only these columns. Needed because the
            pre-fix pair shares 22 comparable columns (one member predates the
            optimality capture) while the post-fix pair shares 25. Comparing
            "N of 350" against "63 of 308" would be comparing different
            measurements; restricting the post-fix pair to the pre-fix column
            set is what makes the two numbers like-for-like.

    Returns (moved, total, columns, per_row) where per_row maps
    (axis, axis_value) -> number of moved cells in that row.
    """
    a, b = _rows(path_a), _rows(path_b)
    columns = sorted((set(a[0]) & set(b[0])) - IDENTITY_COLUMNS)
    if restrict_to is not None:
        columns = sorted(set(columns) & set(restrict_to))

    def key(r):
        return (r["axis"], r["axis_value"])

    am = {key(r): r for r in a}
    bm = {key(r): r for r in b}
    common = [k for k in am if k in bm]

    per_row = {}
    moved = 0
    for k in common:
        n = sum(1 for c in columns if am[k].get(c) != bm[k].get(c))
        per_row[k] = n
        moved += n
    return moved, len(common) * len(columns), columns, per_row


def _degenerate_by_row(path):
    """Per-configuration guard count, for the movement cross-tabulation."""
    out = {}
    for r in _rows(path):
        raw = r.get("degenerate_observations_at_solution", "")
        try:
            out[(r["axis"], r["axis_value"])] = int(float(raw)) if raw != "" else None
        except ValueError:
            out[(r["axis"], r["axis_value"])] = None
    return out


def report():
    """Report the post-fix cell reproduction count against the 63/308 baseline."""
    # Self-test first: the definition must reproduce the pre-fix number exactly,
    # or the post-fix figure is not comparable and is not reported.
    if not (PRE_FIX_A.exists() and PRE_FIX_B.exists()):
        print(
            f"ERROR: pre-fix pair missing ({PRE_FIX_A}, {PRE_FIX_B})", file=sys.stderr
        )
        return 1
    pre_moved, pre_total, pre_columns, _ = compare_cells(PRE_FIX_A, PRE_FIX_B)
    print("--- definition self-test (pre-fix pair) ---")
    print(
        f"  {pre_moved} of {pre_total} cells moved   "
        f"(expected {PRE_FIX_EXPECTED_MOVED} of {PRE_FIX_EXPECTED_CELLS})"
    )
    if (pre_moved, pre_total) != (PRE_FIX_EXPECTED_MOVED, PRE_FIX_EXPECTED_CELLS):
        print(
            "  FAIL: definition has drifted; post-fix count would not be "
            "comparable. Nothing reported.",
            file=sys.stderr,
        )
        return 1
    print("  PASS: definition reproduces the pre-fix baseline exactly.\n")

    if not (POST_FIX_A.exists() and POST_FIX_B.exists()):
        print(
            f"ERROR: post-fix pair missing ({POST_FIX_A}, {POST_FIX_B})",
            file=sys.stderr,
        )
        return 1
    # Like-for-like: restrict to the pre-fix pair's column set so the
    # denominator is the same 308 the baseline was counted over.
    moved, total, columns, per_row = compare_cells(
        POST_FIX_A, POST_FIX_B, restrict_to=pre_columns
    )
    full_moved, full_total, full_columns, _ = compare_cells(POST_FIX_A, POST_FIX_B)

    print("--- post-fix cell reproduction ---")
    print(
        f"  {moved} of {total} cells moved between repeats, "
        f"before {PRE_FIX_EXPECTED_MOVED} of {PRE_FIX_EXPECTED_CELLS}"
    )
    print(
        f"  ({len(per_row)} rows x {len(columns)} comparable columns, "
        f"exact equality, no tolerance)"
    )
    print(
        f"  On the full post-fix schema ({len(full_columns)} columns, including "
        f"the optimality and guard columns the"
    )
    print(f"  pre-fix pair could not carry): {full_moved} of {full_total}.\n")

    deg = _degenerate_by_row(POST_FIX_A)
    print("--- movement vs per-configuration degenerate-observation count ---")
    print(f"  {'axis':<8} {'value':<14} {'guard':>7} {'cells moved':>12}")
    for k in sorted(per_row, key=lambda x: (str(x[0]), str(x[1]))):
        g = deg.get(k)
        print(
            f"  {str(k[0]):<8} {str(k[1]):<14} "
            f"{('-' if g is None else g):>7} {per_row[k]:>12}"
        )

    guards = [deg.get(k) for k in per_row]
    movements = [per_row[k] for k in per_row]
    if all(g is not None for g in guards) and len(set(guards)) > 1:
        n = len(guards)
        mg, mm = sum(guards) / n, sum(movements) / n
        cov = sum((g - mg) * (v - mm) for g, v in zip(guards, movements))
        vg = sum((g - mg) ** 2 for g in guards) ** 0.5
        vv = sum((v - mm) ** 2 for v in movements) ** 0.5
        corr = cov / (vg * vv) if vg and vv else float("nan")
        print(f"\n  corr(guard count, cells moved) = {corr:.2f}")
    else:
        print(
            "\n  corr(guard count, cells moved) = undefined "
            "(guard count is constant across configurations)"
        )
    return 0


def run_twice_probe():
    """The original plan 19.2-28 discriminator, unchanged."""
    for key in CONFIGS_TO_PROBE:
        cfg = next(c for c in m.build_axis_configurations() if c["config_key"] == key)
        print(f"\n=== {key} (n_frames={m.BASELINE_N_FRAMES}, seed=42) ===", flush=True)
        vals = []
        for i in (1, 2):
            with tempfile.TemporaryDirectory() as td:
                rec = m.run_configuration(
                    cfg, 42, m.BASELINE_N_FRAMES, Path(td), force=True
                )
                met = rec.get("metrics") or {}
                rms = met.get("reprojection_rms_px")
                focal = met.get("focal_error_pct_mean")
                vals.append((rms, focal))
                print(f"  run {i}: rms={rms!r}  focal_err_pct={focal!r}", flush=True)

        (r1, f1), (r2, f2) = vals
        print(f"  rms identical  : {r1 == r2}", flush=True)
        print(f"  focal identical: {f1 == f2}", flush=True)
        if r1 != r2:
            print(
                f"  rms delta={r2 - r1:+.6e} rel={abs(r2 - r1) / abs(r1):.3e}",
                flush=True,
            )
        if f1 is not None and f2 is not None and f1 != f2:
            print(
                f"  focal delta={f2 - f1:+.6e} rel={abs(f2 - f1) / abs(f1):.3e}",
                flush=True,
            )

    print("\n=== PROBE COMPLETE ===", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--report",
        action="store_true",
        help="Report the cell-reproduction statistic instead of running the "
        "two-run probe (which re-solves and is slow).",
    )
    args = ap.parse_args()
    sys.exit(report() if args.report else (run_twice_probe() or 0))
