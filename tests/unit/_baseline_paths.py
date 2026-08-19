"""Where the committed-baseline rails read from, decided in one place.

DRIVER-04 (plan 26-09) moved the committed experiment artifacts out of
`experiments/results/` and into `experiments/pre_rerun_baseline/results/`, so the frozen
sha would ship with an empty output tree. Plan 26-01 (`e3a7bf3`) then repointed four test
modules at the archive, correctly: with the live tree empty, the archive IS the subject of
any statement about committed baselines.

What nothing did was point them back. Phase 28 repopulates `experiments/results/` with the
frozen run's output, and at that moment every provenance, schema and exhaustiveness rail in
those four modules would still be validating the archive -- passing green regardless of what
the run produced. 26-01's own commit message saw one instance of this coming
(`TestDefaultMetricsPathAnchoring` "re-tightens once Phase 28 repopulates"); this module makes
the re-tightening automatic instead of something a person has to remember.

The rule: prefer the live tree once it holds files, fall back to the archive otherwise.

`archive_results_dir` exists for the callers that genuinely mean the archive and must NOT
follow the live tree -- `SEEDLESS_LEGACY_RECORDS` and its tests, which are statements about
six specific Phase-19.1 files. Those same six filenames, written by today's code, DO carry a
seed (plan 26-13), so a carve-out that followed the live tree would invert into a false
failure.
"""

from __future__ import annotations

import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

LIVE = ("experiments", "results")
ARCHIVE = ("experiments", "pre_rerun_baseline", "results")


def live_results_dir(repo_root: pathlib.Path | None = None) -> pathlib.Path:
    """The tree a fresh run writes into. May exist and be empty."""
    return (repo_root or REPO_ROOT).joinpath(*LIVE)


def archive_results_dir(repo_root: pathlib.Path | None = None) -> pathlib.Path:
    """The pre-re-run archive, unconditionally -- never follows the live tree."""
    return (repo_root or REPO_ROOT).joinpath(*ARCHIVE)


def _holds_a_file(directory: pathlib.Path) -> bool:
    """True when `directory` contains at least one file, at any depth.

    Existence alone is the wrong test: 26-09's move leaves `experiments/results/` PRESENT
    and EMPTY, and an empty live tree must resolve to the archive. `rglob` rather than
    `iterdir` because E4's records live one level down, in `e4_cells/<cell>/benchmark.json`.
    """
    if not directory.is_dir():
        return False
    return any(path.is_file() for path in directory.rglob("*"))


def resolve_results_dir(
    repo_root: pathlib.Path | None = None,
) -> tuple[pathlib.Path, str]:
    """Return `(directory, which)` where `which` is "live" or "archive".

    `which` is returned rather than inferred by the caller so a skip reason can name the
    resolved subject: a test that silently switched what it validates is no better than one
    that silently validates nothing.
    """
    live = live_results_dir(repo_root)
    if _holds_a_file(live):
        return live, "live"
    return archive_results_dir(repo_root), "archive"


def baseline_file(*parts: str, repo_root: pathlib.Path | None = None) -> pathlib.Path:
    """Resolve one committed artifact by the same rule as `resolve_results_dir`.

    Per-file rather than per-tree, so a caller reading a single artifact does not
    re-implement the directory rule. Falls back to the archive when the live tree has no
    copy of that particular file, which also covers a partial run.
    """
    live = live_results_dir(repo_root).joinpath(*parts)
    if live.is_file():
        return live
    return archive_results_dir(repo_root).joinpath(*parts)
