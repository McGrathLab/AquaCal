"""E3: derived quantities and code constants (EXP-07).

Invoked as `python -m experiments.e3_derived_quantities`. Inherits the shared five-flag
CLI contract (`--seed`, `--out`, `--force`, `--smoke`, `--check`) from
`experiments._io.build_experiment_arg_parser` (D-21), plus one script-local flag
(`--include-per-camera-latex`).

Emits, into `--out` (default `experiments/results/`):
    - `code_constants.csv` -- declared-vs-source value, with a pass/fail column (tier 1)
    - `newton_iterations.csv` -- Newton root-find iteration-count distribution over the
      real rig's working volume (tier 2)
    - `cpr_grouping.csv` -- P / groups / fd_reduction for all six `tab:cpr` configurations,
      in both interface modes (tier 3)
    - `cpr_grouping.tex` -- LaTeX fragment of the shared-interface `tab:cpr` rows (default),
      or both interface modes with `--include-per-camera-latex`
    - `cpr_derived_values.tex` -- two regenerated derived prose asides (D-22)
    - `e3_provenance.json` -- minimal environment-only provenance sidecar

**Tier 1 is DECLARED in `tests/unit/test_experiments_e3_constants.py` and only RENDERED
here (D-18).** The inverted import direction (an `experiments/` script importing from
`tests/`) is deliberate: `experiments/` never ships, because `pyproject.toml` scopes
package discovery to `where = ["src"]`, so nothing leaks into the wheel. CI is the gate
that breaks first when a library default changes -- this script only turns the declared
table into a human-readable CSV. This module never re-declares a claim, source, or value.

**Tier 3 owns every `tab:cpr` row (review H1).** The original design split `tab:cpr`
across this file and E4's `benchmark_grid.csv` (D-16). That split does not hold: every
`tab:cpr` row is a tilt-enabled (`normal_fixed=False`) configuration, and the rows
previously assigned to E4 would have been produced by a run whose parameter vector is two
tilt DOF smaller -- a wrong number that looks right. `benchmark_grid.csv` still reports
CPR columns, but they describe E4's OWN configuration and do NOT feed `tab:cpr`.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import tempfile
from pathlib import Path

import pandas as pd

from aquacal.io import capture_environment
from experiments._io import (
    build_experiment_arg_parser,
    resolve_out_dir,
    validate_args,
    write_experiment_csv,
)

logger = logging.getLogger(__name__)

CHECK_RTOL = 1e-6

CODE_CONSTANTS_COLUMNS = [
    "key",
    "claim",
    "source",
    "read_via",
    "declared_value",
    "source_value",
    "pass_fail",
]
CODE_CONSTANTS_KEY_COLUMNS = ["key"]


def _import_declared_constants():
    """Import `DECLARED_CONSTANTS`, bootstrapping `sys.path` from `__file__` (review L2).

    `tests/__init__.py` exists but `tests/unit/__init__.py` does not, so
    `tests.unit.test_experiments_e3_constants` resolves only via PEP 420 namespace-portion
    semantics, and only when the repository root is on `sys.path` -- which today depends on
    the working directory. Deriving the repo root from `__file__` (never the process's
    current working directory) makes this import robust to the caller's working
    directory, including CI's
    `experiments-smoke` job.
    """
    repo_root = Path(__file__).resolve().parents[1]
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)
    try:
        from tests.unit.test_experiments_e3_constants import DECLARED_CONSTANTS
    except ImportError as exc:
        raise ImportError(
            "Could not import DECLARED_CONSTANTS from "
            "tests.unit.test_experiments_e3_constants after inserting repository root "
            f"{repo_root_str!r} at the front of sys.path. This module requires "
            "tests/unit/test_experiments_e3_constants.py to be importable as a PEP 420 "
            "namespace-package member of tests/ from the repository root."
        ) from exc
    return DECLARED_CONSTANTS


def build_code_constants_df() -> pd.DataFrame:
    """Render tier 1: one row per `DECLARED_CONSTANTS` entry, source value read live.

    Does NOT raise on a mismatch -- the CSV is the artifact and CI (via
    `tests/unit/test_experiments_e3_constants.py`) is the gate. A `FAIL` row must be
    visible in the committed file rather than aborting this script's run.
    """
    declared_constants = _import_declared_constants()
    rows = []
    for entry in declared_constants:
        source_value = entry.live()
        rows.append(
            {
                "key": entry.key,
                "claim": entry.claim,
                "source": entry.source,
                "read_via": entry.read_via,
                "declared_value": repr(entry.declared_value),
                "source_value": repr(source_value),
                "pass_fail": "PASS" if source_value == entry.declared_value else "FAIL",
            }
        )
    return pd.DataFrame(rows, columns=CODE_CONSTANTS_COLUMNS)


def build_provenance_sidecar(seed: int) -> dict:
    """Build E3's minimal, environment-only provenance sidecar (Part 4 Rule 2 carve-out).

    Tiers 1 and 2 never run a calibration, so there is no `benchmark.json` to reuse (unlike
    E1/E7's `write_direct_call_benchmark`). This is the only sidecar format E3 uses.
    """
    return {
        "experiment": "e3",
        "schema_version": 1,
        "seed": seed,
        "environment": capture_environment(),
    }


def build_arg_parser() -> argparse.ArgumentParser:
    """Build E3's CLI parser, extending the shared five-flag contract (D-21)."""
    parser = argparse.ArgumentParser(
        description=__doc__, parents=[build_experiment_arg_parser()]
    )
    parser.add_argument(
        "--include-per-camera-latex",
        action="store_true",
        help="Also render shared_interface=False rows into cpr_grouping.tex (default: "
        "off). The supplement's sparsity table describes the production (shared-interface) "
        "configuration; per-camera mode belongs where E7 frames it as a deliberate "
        "ablation (D-21).",
    )
    return parser


def _write_tier1_and_sidecar(out_dir: Path, seed: int, force: bool) -> None:
    code_constants_df = build_code_constants_df()
    write_experiment_csv(
        code_constants_df,
        out_dir / "code_constants.csv",
        key_columns=CODE_CONSTANTS_KEY_COLUMNS,
        force=force,
    )

    sidecar_path = out_dir / "e3_provenance.json"
    if force or not sidecar_path.exists():
        sidecar = build_provenance_sidecar(seed)
        sidecar_path.parent.mkdir(parents=True, exist_ok=True)
        with open(sidecar_path, "w") as f:
            json.dump(sidecar, f, indent=2, sort_keys=True)
    else:
        logger.info(
            "Skipping write to %s: file already exists and --force was not given "
            "(resumability).",
            sidecar_path,
        )


def _run_check(out_dir: Path) -> int:
    """`--check`: compare freshly produced output against committed baselines."""
    # Filled in by Task 2 (newton_iterations.csv) and Task 3 (cpr_grouping.csv).
    print("--check is not yet fully wired (tiers 2/3 pending).")
    return 1


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for `python -m experiments.e3_derived_quantities`."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    validate_args(parser, args)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.check:
        out_dir = resolve_out_dir(args.out)
        return _run_check(out_dir)

    if args.smoke:
        # Honor an explicitly-passed --out; otherwise fall back to a throwaway temp
        # directory so a bare `--smoke` never pollutes experiments/results/.
        if args.out == parser.get_default("out"):
            with tempfile.TemporaryDirectory(prefix="e3_smoke_") as tmp:
                out_dir = resolve_out_dir(Path(tmp))
                _write_tier1_and_sidecar(out_dir, seed=args.seed, force=True)
                # Tier 2 (Task 2) and tier 3 (Task 3) call sites go here.
        else:
            out_dir = resolve_out_dir(args.out)
            _write_tier1_and_sidecar(out_dir, seed=args.seed, force=True)
            # Tier 2 (Task 2) and tier 3 (Task 3) call sites go here.
        return 0

    out_dir = resolve_out_dir(args.out)
    _write_tier1_and_sidecar(out_dir, seed=args.seed, force=args.force)
    # Tier 2 (Task 2) and tier 3 (Task 3) call sites go here.
    return 0


if __name__ == "__main__":
    sys.exit(main())
