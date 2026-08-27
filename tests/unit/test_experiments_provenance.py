"""EXP-11's mechanical provenance gate (19.2-12 provenance close-out).

Every committed result under `experiments/results/` must carry its seed, AquaCal
version, git SHA, and environment. A new artifact committed without provenance
must fail CI rather than be noticed in review -- that is the whole point of this
file existing instead of a checklist in a summary someone reads once.

Discovers files by globbing `experiments/results/` at collection time and
parametrizes over what it finds, so a failure names the offending file rather
than reporting a bare boolean. Skips cleanly when `experiments/results/` is
absent or empty (a fresh clone without the committed artifacts), but does NOT
skip when the directory exists and merely lacks a particular file -- that gap
is exactly what this file exists to catch.

Never re-runs a calibration: E1's and E7's Phase-19.1 records are verified
where they sit (`SEEDLESS_LEGACY_RECORDS`), not regenerated.
"""

from __future__ import annotations

import ast
import json
import pathlib
import subprocess

import pandas as pd
import pytest

from tests.unit._baseline_paths import archive_results_dir, resolve_results_dir

# Anchored to the repository root via this file's own location, not the
# process working directory -- a gate that resolves relative to cwd can
# vanish from a run silently just because pytest was invoked from elsewhere
# (WR-06). tests/unit/test_experiments_provenance.py -> parents[2] == repo root.
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

# Phase 26 / DRIVER-04 (D-28): the committed baselines this whole module asserts
# about MOVED to experiments/pre_rerun_baseline/ so the frozen sha ships with an
# empty experiments/results/ for the v2.1 re-run to write into. This module's
# subject is the COMMITTED BASELINE SET, not whatever a fresh run happens to
# have produced, so the archive is its correct target -- pointing it at the
# now-empty experiments/results/ would make every assertion here vacuous.
#
# ⚠ Phase 30 / POST-03 PURGES the archive. At that point this constant needs a
# DELIBERATE decision -- repoint at the re-baselined experiments/results/, or
# retire the module's exhaustiveness gates with it -- not a silent edit.
# Plan 26-14: resolved, not hardcoded. While `experiments/results/` is empty this IS the
# archive, so today's subject is unchanged; the moment Phase 28 repopulates the live tree,
# every rail below re-aims at the frozen run's own output instead of passing green against
# history. `RESULTS_TREE` is "archive" or "live" and appears in skip reasons so a skip can
# never be ambiguous about what it was checking.
RESULTS_DIR, RESULTS_TREE = resolve_results_dir()

# The subset of capture_environment()'s live key names (src/aquacal/io/
# benchmark.py) covering library version, git SHA, and the Python/NumPy/SciPy
# versions -- derived by reading capture_environment's body, not copied from
# prose. cpu_model/cpu_count_logical/ram_total_bytes/os/git_sha_source are
# real keys too but are not what EXP-11/ROADMAP SC5 name as required.
REQUIRED_ENVIRONMENT_KEYS = frozenset(
    {
        "aquacal_version",
        "git_sha",
        "python_version",
        "numpy_version",
        "scipy_version",
    }
)

# Committed JSON files that carry their OWN schema rather than
# assemble_benchmark_record's (no `schema_version` key at all), each with a
# one-line comment naming what covers its provenance instead. All three are
# excluded from the schema_version-keyed checks below by construction (they
# have no schema_version to trigger those checks on) -- listed here so a
# reader can see the full set of exceptions in one place rather than
# inferring it from what the glob happens not to catch. This set is verified
# to be exact (not just a superset) by
# TestSelfDescribingJson.test_schema_versionless_json_set_equals_self_describing_json.
SELF_DESCRIBING_JSON = frozenset(
    {
        # real_rig_metrics.json: E2's own schema, carries a `provenance` dict
        # naming exactly how each field was derived from the pipeline run
        # that also wrote the sibling benchmark.json (same directory, same
        # run) -- that sibling file is this one's provenance record.
        "real_rig_metrics.json",
        # interface_ablation_conditioning.json: E7's conditioning report
        # (`per_arm` singular-value/correlation data), covered by the four
        # e7_benchmark_*.json records produced by the same E7 run.
        "interface_ablation_conditioning.json",
        # ADDED 2026-08-26 (plan 29-06). The five e{N}_degeneracy_breakdown
        # sidecars below are DEGEN-01/DEGEN-02 artifacts (Phase 24), all
        # written by experiments/_degeneracy.py::write_degeneracy_breakdown.
        # Each carries the raw cause x stage / fate x stage counts and the
        # per-stage `observations_evaluated__*` denominators that D-09
        # deliberately keeps OUT of the CSVs. None is an
        # assemble_benchmark_record and none publishes a schema_version, which
        # is exactly why they belong here. They were absent from this set only
        # because they postdate its last review and `experiments/results/` was
        # empty from DRIVER-04 until the v2.1 re-run was committed, so the
        # exactness rail below had nothing to discover them in.
        #
        # e1_degeneracy_breakdown.json: E1's breakdown, keyed by model label,
        # written by experiments/e1_refractive_comparison.py:908 in the same
        # run that wrote e1_benchmark_refractive.json and
        # e1_benchmark_nonrefractive.json -- those two records cover it.
        "e1_degeneracy_breakdown.json",
        # e5_degeneracy_breakdown.json: E5's single-seed breakdown
        # (e5_index_sensitivity.py:719, keyed "band" after the n_assumed sweep
        # it aggregates), covered by experiments/results/e5_provenance.json,
        # written by the same run a few lines later.
        "e5_degeneracy_breakdown.json",
        # e5_seed_band_degeneracy_breakdown.json: E5's BAND-owned breakdown,
        # keyed by seed (e5_index_sensitivity.py:826), covered by
        # experiments/results/e5_seed_band_provenance.json. A separate filename
        # from the single-seed one above by design, so a `--seeds` run never
        # overwrites a single-seed artifact (T-19.5-05-01) -- the same
        # separation the two provenance sidecars already keep.
        "e5_seed_band_degeneracy_breakdown.json",
        # e7_degeneracy_breakdown.json: E7's breakdown keyed by arm
        # (experiments/e7_interface_ablation.py:656), covered by the four
        # e7_benchmark_{shared,percamera}_{fixed,refined}.json records written
        # by the same single-seed E7 run.
        "e7_degeneracy_breakdown.json",
        # e7_seed_band_degeneracy_breakdown.json: E7's band-owned breakdown,
        # keyed by seed then arm, covered by
        # experiments/results/e7_seed_band_provenance.json -- the band's own
        # sidecar, which exists precisely because those four arm records are
        # SEEDLESS_LEGACY_RECORDS that band mode must never overwrite.
        "e7_seed_band_degeneracy_breakdown.json",
        # NOTE: calibration.json was removed from this set by DATA-01b (plan
        # 21-11). E2's raw calibration artifact left the repository once the
        # Zenodo real-rig archive was published and now ships there under
        # reference_outputs/. The archive's copy is the 2026-08-10
        # image-source run, not the byte-identical 2026-07-31 video-source
        # file removed here -- same library, agreeing to ~1.5e-8 on water_z.
        # The exact bytes remain in git history at 25655f7.
        #
        # NOTE 2026-08-26 (plan 29-06): calibration.json is written by E2 on
        # every run and is gitignored (.gitignore), so it sits in the working
        # tree at 2.1 MB without ever being committed. It reappeared in this
        # rail's discovered set the moment the live tree was repopulated --
        # not because the DATA-01b decision changed, but because
        # `_discover_json_files()` globbed the working tree with no
        # tracked-file filter while its CSV sibling had one. That asymmetry was
        # fixed at the helper (see `_discover_json_files` below); re-admitting
        # the file here would have papered over it, since an uncommitted file
        # has no business in a carve-out whose stated scope is committed
        # artifacts.
    }
)

# Committed JSON that DOES carry a `schema_version` but is not an
# assemble_benchmark_record, so the record-shaped rails below (an
# `environment` block, a `solver_config` seed) do not apply to it and must not
# sweep it in. Kept as a named, per-member-commented set rather than an
# inline `!=` in the discovery helper so the full set of exclusions stays
# readable in one place, exactly as SELF_DESCRIBING_JSON above.
#
# Verified not to be a hiding place by
# TestSuiteLevelManifestCarveOut.test_carve_out_members_are_flat_manifests:
# a member that grows an `environment` block or a `solver_config` fails there
# and has to be moved back into the general checks deliberately.
SUITE_LEVEL_MANIFEST_JSON = frozenset(
    {
        # run_manifest.json: DRIVER-02's SUITE-level manifest. Its schema owner
        # is experiments/_run_manifest.py:82 (REQUIRED_MANIFEST_FIELDS, with
        # MANIFEST_SCHEMA_VERSION at :71), NOT
        # aquacal.io.assemble_benchmark_record. The file is FLAT: git_sha,
        # git_describe, git_dirty, os, kernel, machine, python_version,
        # numpy_version, scipy_version, opencv_version, cpu_model,
        # ram_total_bytes, utc_start and the rest sit at the top level, so it
        # publishes the same environment provenance the rails ask for -- just
        # not nested under an `environment` key. It also carries no
        # `solver_config`, and correctly so: a suite-level manifest describes a
        # RUN, not a solve, and REQUIRED_MANIFEST_FIELDS deliberately names no
        # seed. `check_rerun_gates.py` imports REQUIRED_MANIFEST_FIELDS rather
        # than keeping a second copy, so this file's own gate is gate 3's
        # manifest check, not the two rails below.
        #
        # It became visible to those rails only in Phase 29: the driver writes
        # this manifest, and experiments/pre_rerun_baseline/results/ has none,
        # so while the rails were aimed at the archive there was nothing to
        # sweep in.
        "run_manifest.json",
    }
)

# The six benchmark records written in Phase 19.1, before solver_config["seed"]
# existed: E1's two and E7's four. Plan 19.2-02 added the seed PARAMETER to the
# direct-call writer (write_direct_call_benchmark) and plan 19.2-14 added it to
# the pipeline entry point's solver_config -- both additive, landing AFTER these
# six records were written.
#
# CORRECTED 2026-08-18 (plan 26-13). This comment used to say the exemption was
# "removed the moment any of these six is regenerated". That was false: 19.2-02
# added the writer's parameter but NOT E1's or E7's call sites, so regenerating
# these six never stamped a seed -- the 26-10 smoke pass wrote all six fresh,
# with current code, and check_rerun_gates reported six gate3_provenance FAILs
# on them. Plan 26-13 fixed the five call sites. The six files NAMED here are
# the archived Phase-19.1 artifacts under experiments/pre_rerun_baseline/results/
# (see RESULTS_DIR above); they are exempt because they will never be rewritten,
# not because a rewrite would fix them. Records written by today's code carry a
# seed and are covered by TestE1AndE7BenchmarkRecordsCarryASeed.
#
# Re-running the originals would cost roughly 90 minutes for records the
# manuscript already cites and produce no new information (19.2-CONTEXT.md
# Claude's Discretion item 1). test_seedless_carve_out_is_exact still fails the
# instant a member stops lacking a seed, so the set cannot silently become a
# blanket exemption.
SEEDLESS_LEGACY_RECORDS = frozenset(
    {
        "e1_benchmark_refractive.json",
        "e1_benchmark_nonrefractive.json",
        "e7_benchmark_shared_fixed.json",
        "e7_benchmark_shared_refined.json",
        "e7_benchmark_percamera_fixed.json",
        "e7_benchmark_percamera_refined.json",
    }
)

# Every committed CSV under experiments/results/, mapped to the provenance
# record that covers it. A CSV present on disk but absent from this mapping
# fails test_all_committed_csvs_have_a_named_record -- the tripwire that
# catches a future artifact committed without provenance (T-19.2-50).
CSV_TO_RECORD: dict[str, str] = {
    "benchmark_grid.csv": (
        "experiments/results/e4_cells/*/benchmark.json (nine per-cell records) "
        "for the nine synthetic rows, plus experiments/results/benchmark.json "
        "(E2's pipeline record) for the real_rig_13cam_200fr row; also carries "
        "its own seed column"
    ),
    "benchmark_grid_repeat.csv": (
        "experiments/results/e4_cells/*/benchmark.json for the repeat cells "
        "(plan 19.5-10, COV-06) -- three 100-frame cells at two repeats each, "
        "single-seed by design so it is not a band; its point is run-to-run "
        "wall-clock spread at fixed work, which is why every row carries "
        "nfev_stage3_interface_optimization beside seconds_total (MF-03)"
    ),
    "camera_parameters.csv": "experiments/results/benchmark.json (E2, same run)",
    "code_constants.csv": "experiments/results/e3_provenance.json (E3 tier 1)",
    "cpr_grouping.csv": (
        "experiments/results/e3_provenance.json (E3 tier 3) for eleven of "
        "twelve rows; the twelfth (13cam_200frame_tilt_intrinsics_shared) is "
        "copied verbatim from experiments/results/benchmark.json (E2)"
    ),
    "e7_trace_percamera_fixed.csv": (
        "experiments/results/e7_benchmark_percamera_fixed.json"
    ),
    "e7_trace_percamera_refined.csv": (
        "experiments/results/e7_benchmark_percamera_refined.json"
    ),
    "e7_trace_shared_fixed.csv": "experiments/results/e7_benchmark_shared_fixed.json",
    "e7_trace_shared_refined.csv": (
        "experiments/results/e7_benchmark_shared_refined.json"
    ),
    # CORRECTED 2026-08-26 (plan 29-06). Both E1 band entries below used to
    # declare their span as `seeds 42-51`, and that claim is preserved here
    # rather than deleted because it was true of the artifacts it was written
    # against: E1's band ran ten seeds when quick task 260813-clj registered
    # these CSVs. Ruling A1 of 2026-08-15 (run_experiment_suite.sh:1452) then
    # cut E1's band from ten seeds to FOUR, and the v2.1 re-run's artifacts
    # carry four -- exp1_band.csv has 256 rows over seeds [42, 43, 44, 45] and
    # exp1_parameter_band.csv 384 rows over the same four, with
    # experiments/results/e1_seed_band_provenance.json recording
    # solver_config['seeds'] == [42, 43, 44, 45] in agreement. So the span text
    # is corrected to `seeds 42-45`. It is the ARTIFACTS that moved, by
    # decision; the assertion was left behind. This field's whole job is
    # stating what a published number may be quoted over, so a stale span here
    # is a stale claim about the manuscript, not a cosmetic drift.
    #
    # `test_multi_seed_band_declares_its_seed_coverage` computes the expected
    # span FROM the CSV on every run, so it is the rail -- not this comment --
    # that keeps the two in step if E1's band is ever re-cut again.
    "exp1_band.csv": (
        "experiments/results/e1_seed_band_provenance.json (the band-owned "
        "sidecar, quick task 260807-dcv), which records solver_config['seeds'] "
        "matching this CSV's own seed column across seeds 42-45 (four seeds "
        "since Ruling A1 of 2026-08-15 cut the band from ten); "
        "experiments/results/e1_benchmark_refractive.json + "
        "e1_benchmark_nonrefractive.json supply version/git_sha/environment "
        "but NOT this band's seeds -- both are SEEDLESS_LEGACY_RECORDS and "
        "carry no seed key at all, and band mode deliberately does not "
        "overwrite them (doing so would replace the single-seed production "
        "record with the last band seed's values), which is precisely why the "
        "band needed a sidecar of its own. This CSV also carries EXP3's "
        "xy_rmse_mm/z_rmse_mm/anisotropy_ratio/n_points: z_rmse_mm at the "
        "deepest test point is the manuscript's headline ratio (main.tex L68, "
        "L281) and previously existed per-seed only in gitignored sweep output"
    ),
    "exp1_parameter_band.csv": (
        "experiments/results/e1_seed_band_provenance.json (the same band-owned "
        "sidecar that covers exp1_band.csv), which records "
        "solver_config['seeds'] matching this CSV's own seed column across "
        "seeds 42-45 (four seeds since Ruling A1 of 2026-08-15 cut the band "
        "from ten); "
        "experiments/results/e1_benchmark_refractive.json + "
        "e1_benchmark_nonrefractive.json supply version/git_sha/environment "
        "but NOT this band's seeds -- both are SEEDLESS_LEGACY_RECORDS and "
        "carry no seed key at all, and band mode deliberately does not "
        "overwrite them. This is E1's SECOND band artifact rather than extra "
        "columns on exp1_band.csv because EXP1's rows are keyed "
        "(camera, model) with no depth axis, so merging them onto the depth-"
        "keyed band would fabricate a depth dependence the parameter errors do "
        "not have. It carries EXP1's focal_length_error_pct and "
        "reprojection_rms_px -- the columns behind the manuscript's focal-drift "
        "and reprojection-RMS sentences (main.tex L270, L271) -- plus the "
        "per-camera position errors; all of them previously existed per-seed "
        "only in gitignored sweep output"
    ),
    "exp1_parameter_errors.csv": (
        "experiments/results/e1_benchmark_refractive.json + "
        "e1_benchmark_nonrefractive.json (E1 calibrates both models)"
    ),
    "e7_focal_standoff.csv": (
        "no record of its own: a zero-solve re-analysis (plan 19.5-03) of the "
        "ten committed seeds in experiments/results/interface_ablation_band.csv, "
        "whose four arms are covered by experiments/results/"
        "e7_benchmark_{shared,percamera}_{fixed,refined}.json; each row also "
        "carries its own scope column naming the band it re-reads"
    ),
    "fd_jacobian_accuracy.csv": (
        "experiments/results/fd_jacobian_accuracy.json (its own run-level "
        "sidecar, plan 19.5-02)"
    ),
    "exp2_depth_generalization.csv": (
        "experiments/results/e1_benchmark_refractive.json + "
        "e1_benchmark_nonrefractive.json (same E1 run)"
    ),
    "exp3_xy_vs_z_anisotropy.csv": (
        "experiments/results/e1_benchmark_refractive.json + "
        "e1_benchmark_nonrefractive.json (same E1 run)"
    ),
    "generalization_sweep.csv": (
        "experiments/results/e6_provenance.json (E6's run-level sidecar, "
        "plan 19.2-16) -- also carries its own seed column; the twelve "
        "experiments/results/e6_configs/*.json are per-configuration "
        "checkpoints with their own schema_version and provenance"
    ),
    "generalization_sweep_band.csv": (
        "experiments/results/e6_seed_band_provenance.json (plan 19.5-10, "
        "COV-03 + COV-04), which records solver_config['seeds'] matching this "
        "CSV's own seed column across seeds 42-47 -- 17 configurations per "
        "seed, 102 rows, including the cameras axis at 8/12/16; unlike E1's "
        "and E7's bands the sidecar here DOES cover the whole span, so the "
        "seed column and the sidecar corroborate each other"
    ),
    # ADDED 2026-08-26 (plan 29-06). Both per-camera CSVs are FIX-03
    # artifacts (plan 23-03), written by
    # experiments/e6_generalization_sweep.py at :1746 (_run_full) and :1511
    # (_run_seed_band). They postdate this map's last review and were
    # unregistered until the v2.1 re-run committed them, at which point
    # test_all_committed_csvs_have_a_named_record did exactly its job.
    "generalization_sweep_per_camera.csv": (
        "experiments/results/e6_provenance.json (the SAME E6 run-level sidecar "
        "that covers generalization_sweep.csv -- both CSVs are written by one "
        "_run_full pass over the same twelve configurations, so one record "
        "covers both) -- also carries its own seed column, single-seed at 42, "
        "which is why it is not a band. FIX-03 (plan 23-03) added this "
        "per-camera decomposition beside the configuration-level sweep: it "
        "reports z_position_error_mm_raw against "
        "z_position_error_mm_gauge_corrected per camera, plus the signed "
        "water_z and h_c errors, none of which survive the configuration-level "
        "aggregation in generalization_sweep.csv"
    ),
    "generalization_sweep_per_camera_band.csv": (
        "experiments/results/e6_seed_band_provenance.json (the SAME band-owned "
        "sidecar that covers generalization_sweep_band.csv, written by one "
        "_run_seed_band pass, plan 19.5-10 COV-03 + COV-04), which records "
        "solver_config['seeds'] matching this CSV's own seed column across "
        "seeds 42-47 -- the per-camera half of E6's band, 864 rows, added by "
        "FIX-03 (plan 23-03); as with E6's other band artifact the sidecar "
        "DOES cover the whole span, unlike E1's and E7's, so the seed column "
        "and the sidecar corroborate each other rather than the column "
        "standing alone"
    ),
    "index_sensitivity.csv": (
        "experiments/results/e5_provenance.json (E5's run-level sidecar, "
        "plan 19.2-19) -- also carries its own seed column"
    ),
    "index_sensitivity_seed_band.csv": (
        "experiments/results/e5_seed_band_provenance.json (plan 19.5-10, "
        "COV-05), which records solver_config['seeds'] matching this CSV's "
        "own seed column across seeds 42-47 -- eleven n_assumed values per "
        "seed, 66 rows; the sidecar's scope distinguishes this seed band from "
        "n_assumed_band, which varies the assumed index at ONE seed and bounds "
        "nothing about seed noise (D-19.5-05)"
    ),
    "interface_ablation.csv": (
        "experiments/results/e7_benchmark_shared_fixed.json + "
        "e7_benchmark_shared_refined.json + e7_benchmark_percamera_fixed.json "
        "+ e7_benchmark_percamera_refined.json (four arms)"
    ),
    "interface_ablation_band.csv": (
        "its own seed column is its ONLY seed provenance, spanning seeds "
        "42-51; the four experiments/results/e7_benchmark_{shared,percamera}_"
        "{fixed,refined}.json supply version/git_sha/environment but NOT this "
        "band's seeds -- all four are SEEDLESS_LEGACY_RECORDS and carry no "
        "seed key at all, and band mode deliberately does not overwrite them "
        "(doing so would replace the single-seed production record with the "
        "last band seed's values)"
    ),
    "newton_iterations.csv": "experiments/results/e3_provenance.json (E3 tier 2)",
    "structural_scaling.csv": (
        "no calibration record exists or could exist: every row is closed-form "
        "structure (plan 19.5-01, COV-01) with no solve anywhere in its path, "
        "so there is no seed, no runtime and no environment to record; each row "
        "carries its own record_source column marking it computed (sparsity "
        "built directly) or predicted (closed form)"
    ),
}

# CSV_TO_RECORD keys whose artifact is not on disk YET -- registered ahead of
# the run that produces it, because an unregistered CSV fails
# test_all_committed_csvs_have_a_named_record the moment it appears.
# Deliberately per-file and expected to shrink to empty:
# test_pending_csvs_are_still_pending fails as soon as one lands.
#
# Currently EMPTY, and that is the resting state. exp1_parameter_band.csv --
# the entry this list was introduced for (quick task 260813-clj) -- landed with
# the seeds 42-51 band re-run and was removed here, so the stale-entry gate
# covers it again. Add a name only for the window between registering a CSV and
# committing the run that produces it.
PENDING_CSVS: frozenset[str] = frozenset()


def _read_csv_columns(path: pathlib.Path) -> list[str]:
    """Column names of ``path``, read without loading the whole frame."""
    return list(pd.read_csv(path, nrows=0).columns)


def _seed_span(seeds: "pd.Series") -> str:
    """Render a band's seed coverage as the string its map entry must contain.

    Contiguous runs collapse to ``"seeds 42-51"``; anything else is listed in
    full as ``"seeds 42, 44, 47"``. Derived from the data on every call so the
    expected text cannot drift from the artifact it describes.
    """
    unique = sorted(int(s) for s in seeds.dropna().unique())
    contiguous = unique == list(range(unique[0], unique[-1] + 1))
    if contiguous:
        return f"seeds {unique[0]}-{unique[-1]}"
    return "seeds " + ", ".join(str(s) for s in unique)


def _discover_json_files() -> list[pathlib.Path]:
    """Every git-TRACKED `*.json` under the resolved results tree.

    `rglob`, not `glob`, and deliberately so: E4's records live one level down
    in `e4_cells/<cell>/benchmark.json` and E6's checkpoints in
    `e6_configs/*.json`, so a top-level walk would silently drop them. Only the
    filter was added 2026-08-26 (plan 29-06), never the walk.

    The `_is_tracked` filter matches the one `_discover_csv_files` below has
    always had; see that helper's docstring for the reasoning, which applies to
    JSON word for word.
    """
    if not RESULTS_DIR.exists():
        return []
    return sorted(p for p in RESULTS_DIR.rglob("*.json") if _is_tracked(p))


def _is_tracked(path: pathlib.Path) -> bool:
    """True if git tracks ``path``.

    The CSV suite documents its scope as files "committed under
    experiments/results/", but discovers them by globbing the working tree. Those
    two sets diverge whenever an experiment writes an output that is
    deliberately excluded from the repository -- E1's
    ``exp2_spatial_errors.csv`` is 11.6 MB and gitignored (``.gitignore:231``),
    so it appears on disk after any E1 run but is never committed. Globbing
    alone made the tripwire fire on exactly the files it was never meant to
    cover. Filtering to tracked files narrows the suite to its own stated scope;
    it does not weaken any assertion about artifacts that ARE committed.

    EXTENDED 2026-08-26 (plan 29-06) to the JSON rails, which had the identical
    problem and no filter. The text above applies word for word: E2 writes a
    2.1 MB ``calibration.json`` on every run and it is gitignored (DATA-01b,
    plan 21-11, moved that artifact to the published Zenodo archive), so it
    appears on disk after any E2 run but is never committed.
    ``_discover_json_files`` globbed the working tree without this filter, so
    that one uncommitted file reached
    ``test_schema_versionless_json_set_equals_self_describing_json`` -- a rail
    whose stated scope is committed artifacts -- and demanded a carve-out entry
    it has no business holding. The asymmetry was invisible while
    ``experiments/results/`` was empty and surfaced only when the v2.1 re-run
    repopulated the tree. Fixing it at the helper keeps both rails honest about
    the same set; carving the file out would have hidden the divergence
    instead.
    """
    try:
        return (
            subprocess.run(
                ["git", "ls-files", "--error-unmatch", str(path)],
                capture_output=True,
                cwd=REPO_ROOT,
            ).returncode
            == 0
        )
    except OSError:
        # No git available: fall back to covering everything found, which is the
        # stricter behaviour and matches the pre-existing contract.
        return True


def _discover_csv_files() -> list[pathlib.Path]:
    if not RESULTS_DIR.exists():
        return []
    return sorted(p for p in RESULTS_DIR.glob("*.csv") if _is_tracked(p))


def _load_json(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _schema_versioned_json_files() -> list[pathlib.Path]:
    """Every committed `*.json` that carries a `schema_version` key AND is
    shaped like a benchmark record.

    Includes both assemble_benchmark_record-shaped files (which also carry
    `stages`) and E3's minimal sidecar (which does not) -- both publish a
    `schema_version`, so both are in scope for the environment-presence check.

    Excludes `SUITE_LEVEL_MANIFEST_JSON`. Added 2026-08-26 (plan 29-06):
    `run_manifest.json` publishes a `schema_version` too, but under DRIVER-02's
    suite-level schema (experiments/_run_manifest.py:82), not
    assemble_benchmark_record's. Sweeping it in asserted a record's shape
    against a file that never claimed it -- an `environment` block it publishes
    flat instead, and a `solver_config` seed that a manifest describing a RUN
    rather than a solve has no business carrying. The exclusion narrows this
    helper to its own stated subject and removes no coverage: gate 3's manifest
    check in experiments/check_rerun_gates.py already asserts every field of
    REQUIRED_MANIFEST_FIELDS on that file, importing the tuple rather than
    keeping a second copy.
    """
    return [
        p
        for p in _discover_json_files()
        if p.name not in SUITE_LEVEL_MANIFEST_JSON and "schema_version" in _load_json(p)
    ]


def _record_seed(record: dict) -> object | None:
    """Read a record's seed, wherever it lives.

    `assemble_benchmark_record`-shaped records (the ones carrying `stages`)
    publish `solver_config["seed"]`. E3's sidecar (no `stages`, a Part-4-Rule-2
    carve-out for tiers that never run a calibration) ALSO publishes
    `solver_config["seed"]` since 19.2-12 (kept alongside its pre-existing
    top-level `seed` for the sidecar's own dedicated reader), so a single
    lookup covers every schema_version-carrying file in the repository today.
    """
    solver_config = record.get("solver_config")
    if isinstance(solver_config, dict):
        if "seed" in solver_config:
            return solver_config["seed"]
        # A multi-seed band ran under no single seed, so its sidecar publishes
        # the span as solver_config["seeds"] instead. That list IS the record's
        # seed provenance -- richer than a scalar, not absent -- and
        # check_rerun_gates.py's gate_e6_seed_band:sidecar_seeds independently
        # asserts it matches the band CSV's distinct seeds. Reading only the
        # singular key would push a live band record into
        # SEEDLESS_LEGACY_RECORDS, hiding present provenance behind a carve-out
        # reserved for Phase-19.1 records that genuinely carry none.
        if "seeds" in solver_config:
            return solver_config["seeds"]
    return None


def _pytest_id(path: pathlib.Path) -> str:
    return str(path.relative_to(RESULTS_DIR)).replace("\\", "/")


_JSON_FILES = _discover_json_files()
_SCHEMA_JSON_FILES = _schema_versioned_json_files()
_CSV_FILES = _discover_csv_files()
_E4_CELL_FILES = sorted(RESULTS_DIR.glob("e4_cells/*/benchmark.json"))


pytestmark = pytest.mark.skipif(
    not RESULTS_DIR.exists() or not any(RESULTS_DIR.iterdir()),
    reason=f"the resolved results tree ({RESULTS_TREE}: {RESULTS_DIR}) is absent or empty "
    "(fresh clone without committed artifacts) -- nothing to check provenance against.",
)


class TestEnvironmentPresence:
    @pytest.mark.parametrize(
        "path", _SCHEMA_JSON_FILES, ids=[_pytest_id(p) for p in _SCHEMA_JSON_FILES]
    )
    def test_every_benchmark_record_has_environment(self, path):
        """Every schema_version-carrying JSON also carries the required
        environment keys -- library version, git SHA, Python/NumPy/SciPy."""
        record = _load_json(path)
        assert "environment" in record, f"{path} has schema_version but no environment"
        missing = REQUIRED_ENVIRONMENT_KEYS - set(record["environment"])
        assert not missing, f"{path}: environment block missing keys {missing}"

    def test_environment_presence_check_rejects_a_mutated_record(self, tmp_path):
        """Guard: prove the checker rejects a REAL record with its
        environment block removed -- not only a hand-built dict that was
        never going to pass anyway. The negative control this replaces was a
        tautology: it wrote {"schema_version": 1} and asserted "environment"
        not in it, which exercises no project code and cannot fail. Mirrors
        how the genuine seed guard below mutates a real E4 cell record."""
        source = RESULTS_DIR / "e4_cells" / "cameras_8_frames_50" / "benchmark.json"
        if not source.exists():
            pytest.skip("no E4 cell record present (fresh clone)")
        record = _load_json(source)
        assert "environment" in record, (
            "fixture record unexpectedly missing environment"
        )
        del record["environment"]
        mutated_path = tmp_path / "mutated.json"
        mutated_path.write_text(json.dumps(record))
        mutated = _load_json(mutated_path)
        assert "environment" not in mutated


class TestE4CellProvenance:
    @pytest.mark.parametrize(
        "path", _E4_CELL_FILES, ids=[_pytest_id(p) for p in _E4_CELL_FILES]
    )
    def test_e4_cell_records_have_provenance(self, path):
        record = _load_json(path)
        assert "schema_version" in record
        assert "environment" in record
        missing = REQUIRED_ENVIRONMENT_KEYS - set(record["environment"])
        assert not missing, f"{path}: environment block missing keys {missing}"
        assert "memory" in record, f"{path}: missing memory block"


class TestE3SidecarProvenance:
    def test_e3_sidecar_has_minimal_provenance(self):
        path = RESULTS_DIR / "e3_provenance.json"
        if not path.exists():
            pytest.skip("e3_provenance.json not present (fresh clone)")
        record = _load_json(path)
        assert record.get("experiment") == "e3"
        assert "schema_version" in record
        assert "seed" in record
        assert "environment" in record
        missing = REQUIRED_ENVIRONMENT_KEYS - set(record["environment"])
        assert not missing, f"e3_provenance.json: environment missing keys {missing}"


class TestSeedProvenance:
    @pytest.mark.parametrize(
        "path", _SCHEMA_JSON_FILES, ids=[_pytest_id(p) for p in _SCHEMA_JSON_FILES]
    )
    def test_every_benchmark_record_carries_a_seed(self, path):
        """Every schema_version-carrying record carries a seed, except the six
        named Phase-19.1 legacy records (review H5: a carve-out earned by an
        explicit, commented, exactly-verified set -- not by omission)."""
        if RESULTS_TREE == "archive" and path.name in SEEDLESS_LEGACY_RECORDS:
            pytest.skip(f"{path.name} is an exempted Phase-19.1 legacy record")
        # Against a LIVE tree there are no exemptions: plan 26-13 made every one of these
        # six carry a seed at write time, so a seedless record there is a real defect.
        record = _load_json(path)
        seed = _record_seed(record)
        assert seed is not None, (
            f"{path} carries schema_version but no solver_config['seed'], and is "
            "not in SEEDLESS_LEGACY_RECORDS -- either stamp a seed at write time "
            "or add it to the carve-out with a reason."
        )

    def test_seedless_carve_out_is_exact(self):
        """Every SEEDLESS_LEGACY_RECORDS member exists on disk and genuinely
        lacks a seed -- the half that stops the carve-out from silently
        becoming a blanket exemption. If a legacy record is later regenerated
        WITH a seed, or renamed, this test fails and forces the set to be
        updated deliberately."""
        for name in SEEDLESS_LEGACY_RECORDS:
            # archive_results_dir(), NOT RESULTS_DIR: this is a statement about six
            # ARCHIVED files. The same six filenames written by today's code DO carry a
            # seed (26-13), so following a live tree would invert this into a false
            # failure. Plan 26-14.
            path = archive_results_dir() / name
            assert path.exists(), f"SEEDLESS_LEGACY_RECORDS names {name}, not on disk"
            record = _load_json(path)
            seed = _record_seed(record)
            assert seed is None, (
                f"{name} is listed in SEEDLESS_LEGACY_RECORDS but now carries "
                f"solver_config['seed']={seed!r} -- remove it from the carve-out."
            )

    def test_seedless_carve_out_has_exactly_six_members_and_excludes_e2(self):
        assert len(SEEDLESS_LEGACY_RECORDS) == 6
        assert "benchmark.json" not in SEEDLESS_LEGACY_RECORDS

    def test_seed_check_rejects_a_record_with_seed_removed(self, tmp_path):
        """Guard: prove the checker rejects a mutated copy of a real E4 cell
        record with solver_config['seed'] deleted -- not only paths that were
        already going to pass."""
        source = RESULTS_DIR / "e4_cells" / "cameras_8_frames_50" / "benchmark.json"
        if not source.exists():
            pytest.skip("no E4 cell record present (fresh clone)")
        record = _load_json(source)
        assert _record_seed(record) is not None, "fixture record unexpectedly seedless"
        del record["solver_config"]["seed"]
        mutated_path = tmp_path / "mutated.json"
        mutated_path.write_text(json.dumps(record))
        mutated = _load_json(mutated_path)
        assert _record_seed(mutated) is None

    # CSV name -> the sidecar record that now covers it end-to-end (plans
    # 19.2-16 and 19.2-19 gave each a real run-level sidecar; previously
    # neither had one and the only check was the CSV's own `seed` column).
    _CSV_FULL_PROVENANCE_SIDECAR: dict[str, str] = {
        "index_sensitivity.csv": "e5_provenance.json",
        "generalization_sweep.csv": "e6_provenance.json",
    }

    @pytest.mark.parametrize(
        "csv_name,sidecar_name",
        sorted(_CSV_FULL_PROVENANCE_SIDECAR.items()),
        ids=[f"{k}->{v}" for k, v in sorted(_CSV_FULL_PROVENANCE_SIDECAR.items())],
    )
    def test_new_phase_csvs_carry_full_provenance(self, csv_name, sidecar_name):
        """index_sensitivity.csv and generalization_sweep.csv are each backed
        by a real sidecar record that must carry ALL FOUR EXP-11 fields --
        seed, aquacal_version, git_sha, and a complete environment block --
        not only a seed. This replaces a check that verified one field of
        four while its docstring read as if it verified all of them
        (19.2-VERIFICATION.md gap 1); a seed-only artifact now fails here.
        Each CSV is its own parametrized case: one missing file skips only
        that case (WR-11)."""
        csv_path = RESULTS_DIR / csv_name
        sidecar_path = RESULTS_DIR / sidecar_name
        if not csv_path.exists() or not sidecar_path.exists():
            pytest.skip(f"{csv_name} or {sidecar_name} not present (fresh clone)")

        df = pd.read_csv(csv_path)
        assert "seed" in df.columns, f"{csv_name} has no seed column"
        assert df["seed"].notna().all(), f"{csv_name} has a null seed in some row"

        record = _load_json(sidecar_path)
        seed = _record_seed(record)
        assert seed is not None, f"{sidecar_name} carries no solver_config['seed']"
        env = record.get("environment", {})
        assert env.get("aquacal_version"), f"{sidecar_name}: missing aquacal_version"
        assert env.get("git_sha"), f"{sidecar_name}: missing git_sha"
        missing = REQUIRED_ENVIRONMENT_KEYS - set(env)
        assert not missing, f"{sidecar_name}: environment missing keys {missing}"

    def test_benchmark_grid_carries_a_seed_column(self):
        """benchmark_grid.csv has no single sidecar (backed by nine
        e4_cells/*/benchmark.json records plus benchmark.json for the
        real-rig row, per CSV_TO_RECORD); its own `seed` column is its seed
        provenance, and the full four-field check on those backing records
        is already covered by TestE4CellProvenance and
        TestOneMachineConsistency."""
        path = RESULTS_DIR / "benchmark_grid.csv"
        if not path.exists():
            pytest.skip("benchmark_grid.csv not present (fresh clone)")
        df = pd.read_csv(path)
        assert "seed" in df.columns, "benchmark_grid.csv has no seed column"
        assert df["seed"].notna().all(), (
            "benchmark_grid.csv has a null seed in some row"
        )

    @pytest.mark.parametrize(
        "name", sorted(SEEDLESS_LEGACY_RECORDS), ids=sorted(SEEDLESS_LEGACY_RECORDS)
    )
    def test_e1_and_e7_records_already_comply_on_environment(self, name):
        """E1's two and E7's four committed records pass the same environment
        key-presence check as everything else -- verified, not re-run. Each
        record is its own parametrized case so one missing file skips only
        its own case (WR-11), not its siblings."""
        path = RESULTS_DIR / name
        if not path.exists():
            pytest.skip(f"{name} not present (fresh clone)")
        record = _load_json(path)
        missing = REQUIRED_ENVIRONMENT_KEYS - set(record.get("environment", {}))
        assert not missing, f"{name}: environment missing keys {missing}"


class TestSchemaVersionedDiscoveryCoverage:
    def test_discovery_includes_e5_e6_and_e6_config_checkpoints_by_name(self):
        """Widening the checks is not enough on its own -- confirm the new
        artifacts are actually IN the discovered set those checks iterate
        over, so a future write that drops schema_version fails loudly here
        instead of quietly leaving the gate uncovered (T-19.2-94)."""
        e6_configs_dir = RESULTS_DIR / "e6_configs"
        if not (RESULTS_DIR / "e5_provenance.json").exists():
            pytest.skip("e5/e6 provenance not present (fresh clone)")

        discovered = {_pytest_id(p) for p in _SCHEMA_JSON_FILES}
        assert "e5_provenance.json" in discovered
        assert "e6_provenance.json" in discovered

        checkpoint_names = sorted(p.name for p in e6_configs_dir.glob("*.json"))
        assert len(checkpoint_names) == 12, (
            "expected twelve e6_configs/*.json checkpoints, found "
            f"{len(checkpoint_names)}: {checkpoint_names}"
        )
        for name in checkpoint_names:
            expected_id = f"e6_configs/{name}"
            assert expected_id in discovered, (
                f"{expected_id} exists on disk but is not in the "
                "schema-versioned discovery set"
            )


class TestCsvProvenanceMap:
    @pytest.mark.parametrize(
        "path", _CSV_FILES, ids=[_pytest_id(p) for p in _CSV_FILES]
    )
    def test_all_committed_csvs_have_a_named_record(self, path):
        assert path.name in CSV_TO_RECORD, (
            f"{path.name} is committed under experiments/results/ but has no "
            "entry in CSV_TO_RECORD -- add one naming the provenance record "
            "that covers it (T-19.2-50)."
        )

    @pytest.mark.parametrize(
        "path", _CSV_FILES, ids=[_pytest_id(p) for p in _CSV_FILES]
    )
    def test_multi_seed_band_declares_its_seed_coverage(self, path):
        """A multi-seed band must declare its seed span in CSV_TO_RECORD.

        A band CSV spans N seeds, but the sidecars it sits next to record a
        single run -- E1's and E7's are `SEEDLESS_LEGACY_RECORDS` carrying no
        seed key whatsoever, and band mode deliberately does not overwrite
        them. Pointing such a band at those sidecars and stopping there
        silently implies a coverage they do not provide, which is how
        `exp1_band.csv` and `interface_ablation_band.csv` sat unregistered
        from Phase 19.4 until Phase 19.5's post-merge gate caught them.

        So the band's own `seed` column is treated as its seed provenance and
        is required to be complete, and the map entry must state the span that
        column actually contains. The expected span is computed FROM the CSV,
        never hard-coded: re-running a band over different seeds fails here
        until the entry is corrected, rather than leaving a stale claim behind.

        Applies to any committed CSV carrying two or more distinct seeds, so
        a future band inherits the gate by existing (T-19.5-W1).
        """
        if "seed" not in _read_csv_columns(path):
            pytest.skip(f"{path.name} carries no seed column")
        seeds = pd.read_csv(path)["seed"]
        if seeds.dropna().nunique() < 2:
            pytest.skip(f"{path.name} is single-seed, not a band")

        assert not seeds.isna().any(), (
            f"{path.name} spans multiple seeds but has null seed cells -- its "
            "own seed column is its only seed provenance and must be complete"
        )
        record = CSV_TO_RECORD.get(path.name, "")
        expected = _seed_span(seeds)
        assert expected in record, (
            f"{path.name} spans {seeds.nunique()} seeds ({expected}) but its "
            f"CSV_TO_RECORD entry does not say so. Add the span verbatim as "
            f"'{expected}' so no reader mistakes a single-run sidecar for "
            "coverage of the whole band (T-19.5-W1)."
        )

    def test_csv_to_record_has_no_stale_entries(self):
        """Every CSV_TO_RECORD key names a CSV that actually exists on disk --
        the map must be updated, not just grown, when a CSV is removed.

        `PENDING_CSVS` is the one narrow exemption: an entry registered ahead
        of the run that produces its artifact. Registration has to land first
        because an unregistered CSV fails
        `test_all_committed_csvs_have_a_named_record` the moment it appears,
        which would put the gate's own failure between the run and its commit.
        The list is deliberately explicit and per-file, so every other kind of
        stale entry -- the removed-CSV case this test exists for -- still fails.
        """
        if not RESULTS_DIR.exists():
            pytest.skip("experiments/results/ not present (fresh clone)")
        on_disk = {p.name for p in _CSV_FILES}
        stale = set(CSV_TO_RECORD) - on_disk - PENDING_CSVS
        assert not stale, f"CSV_TO_RECORD names CSV(s) no longer on disk: {stale}"

    def test_pending_csvs_are_still_pending(self):
        """`PENDING_CSVS` must shrink to empty, not linger.

        Once a pending artifact is committed the exemption is dead weight that
        would quietly re-open the stale-entry hole for that filename, so this
        fails as soon as the file lands and forces its removal from the list.
        """
        if not RESULTS_DIR.exists():
            pytest.skip("experiments/results/ not present (fresh clone)")
        on_disk = {p.name for p in _CSV_FILES}
        landed = PENDING_CSVS & on_disk
        assert not landed, (
            f"{sorted(landed)} is now committed under experiments/results/ -- "
            "remove it from PENDING_CSVS so the stale-entry gate covers it "
            "again."
        )


class TestOneMachineConsistency:
    def test_environment_blocks_report_one_machine(self):
        """Every record produced by THIS phase reports the same CPU and RAM
        figures as benchmark.json (constraint 11) -- asserted, not assumed."""
        reference_path = RESULTS_DIR / "benchmark.json"
        if not reference_path.exists():
            pytest.skip("benchmark.json not present (fresh clone)")
        reference = _load_json(reference_path)["environment"]

        phase_records = list(_E4_CELL_FILES)
        for name in ("e3_provenance.json", "e5_provenance.json", "e6_provenance.json"):
            sidecar = RESULTS_DIR / name
            if sidecar.exists():
                phase_records.append(sidecar)

        mismatched = []
        for path in phase_records:
            env = _load_json(path)["environment"]
            if env.get("cpu_model") != reference.get("cpu_model") or env.get(
                "ram_total_bytes"
            ) != reference.get("ram_total_bytes"):
                mismatched.append(str(path))
        assert not mismatched, (
            f"Records reporting a different machine than benchmark.json: {mismatched}"
        )


class TestSelfDescribingJson:
    def test_self_describing_json_files_are_named_and_exist(self):
        """SELF_DESCRIBING_JSON's members exist on disk and genuinely carry no
        schema_version -- if either changes, this set needs deliberate review."""
        for name in SELF_DESCRIBING_JSON:
            path = RESULTS_DIR / name
            if not path.exists():
                pytest.skip(f"{name} not present (fresh clone)")
            record = _load_json(path)
            assert "schema_version" not in record, (
                f"{name} is listed in SELF_DESCRIBING_JSON as not using the "
                "assemble_benchmark_record schema, but now carries schema_version "
                "-- it may need to move into the general checks instead."
            )

    def test_schema_versionless_json_set_equals_self_describing_json(self):
        """SELF_DESCRIBING_JSON claims to list the FULL set of exceptions in
        one place -- enforce that claim exactly, not just verify each named
        member (the test above), so an untracked exception can no longer
        exist silently."""
        if not RESULTS_DIR.exists() or not any(RESULTS_DIR.iterdir()):
            pytest.skip("experiments/results/ not present (fresh clone)")
        versionless = {
            p.name for p in _JSON_FILES if "schema_version" not in _load_json(p)
        }
        assert versionless == set(SELF_DESCRIBING_JSON), (
            f"schema_version-less committed JSON files {versionless} do not "
            f"match SELF_DESCRIBING_JSON {set(SELF_DESCRIBING_JSON)} exactly"
        )


class TestSuiteLevelManifestCarveOut:
    """Plan 29-06.

    `SUITE_LEVEL_MANIFEST_JSON` lifts `run_manifest.json` out of the two
    benchmark-record rails above. That is only legitimate while the file really
    is a suite-level manifest, so the carve-out is held to the same standard as
    `SEEDLESS_LEGACY_RECORDS` and `SELF_DESCRIBING_JSON`: earned by an
    explicit, commented, checked set -- never by omission.
    """

    def test_carve_out_members_are_flat_manifests(self):
        """Each carved-out file found on disk really is manifest-shaped.

        Iterates the DISCOVERED set rather than the carve-out, so a tree that
        legitimately holds no manifest asserts nothing instead of skipping:
        `experiments/pre_rerun_baseline/results/` has none, because the driver
        that writes it (DRIVER-02) postdates that baseline. A tree that HAS one
        is checked in full.
        """
        for path in [p for p in _JSON_FILES if p.name in SUITE_LEVEL_MANIFEST_JSON]:
            record = _load_json(path)
            assert "schema_version" in record, (
                f"{path.name} is carved out of the benchmark-record rails as a "
                "suite-level manifest, but carries no schema_version at all -- "
                "either move it to SELF_DESCRIBING_JSON, which is where "
                "schema-less committed JSON belongs, or restore the "
                "schema_version its writer is supposed to stamp (DRIVER-02)."
            )
            assert "environment" not in record, (
                f"{path.name} is carved out of the environment rail because it "
                "publishes git_sha/python_version/numpy_version/scipy_version "
                "FLAT, but it now carries an `environment` block -- either "
                "drop it from SUITE_LEVEL_MANIFEST_JSON so the rail covers it "
                "again, or record here why a suite-level manifest grew one "
                "(DRIVER-02, experiments/_run_manifest.py)."
            )
            assert "solver_config" not in record, (
                f"{path.name} is carved out of the seed rail because a "
                "suite-level manifest describes a RUN and not a solve, but it "
                "now carries a `solver_config` -- either drop it from "
                "SUITE_LEVEL_MANIFEST_JSON so the seed rail covers it again, "
                "or record here why a manifest gained a seed (DRIVER-02, "
                "experiments/_run_manifest.py)."
            )

    def test_carve_out_has_exactly_one_member(self):
        """Exactly one member, named.

        Mirrors test_seedless_carve_out_has_exactly_six_members_and_excludes_e2:
        a carve-out that can grow by an edit nobody reads is how an exemption
        becomes a blanket. A second suite-level schema has to fail here first
        and be added deliberately, with its own comment naming its owner.
        """
        assert set(SUITE_LEVEL_MANIFEST_JSON) == {"run_manifest.json"}


# ---------------------------------------------------------------------------
# FIX-02: every experiment must pass normal_fixed explicitly at every
# calibrate_synthetic/optimize_interface/joint_refinement call site.
#
# E1 and E7 were not wrong on purpose -- they simply omitted the argument,
# silently inheriting the library's normal_fixed=True default and solving a
# problem two tilt DOF smaller than production (which runs at False). The
# omission was unrecoverable from their artifacts: the neighbouring
# shared_interface key WAS recorded, so a reader meets one interface-model
# flag present and the other absent and reasonably (wrongly) infers it was
# considered. This test makes any future omission fail loudly, across every
# experiment that solves, rather than silently reproducing the same defect.
# ---------------------------------------------------------------------------

NORMAL_FIXED_MODULES = (
    "experiments/e1_refractive_comparison.py",
    "experiments/e4_benchmark_grid.py",
    "experiments/e5_index_sensitivity.py",
    "experiments/e6_generalization_sweep.py",
    "experiments/e7_interface_ablation.py",
)
_NORMAL_FIXED_CALLEES = {
    "calibrate_synthetic",
    "optimize_interface",
    "joint_refinement",
}


def _callee_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def test_every_experiment_passes_normal_fixed_explicitly():
    """Parse each of NORMAL_FIXED_MODULES and assert every
    calibrate_synthetic/optimize_interface/joint_refinement call carries a
    normal_fixed keyword argument, naming the module/callee/line on failure.
    Adding a sixth solving experiment requires deliberately adding it to
    NORMAL_FIXED_MODULES -- an omission here would silently exempt a new
    experiment from this gate.

    E1 and E7 were not wrong on purpose here -- they simply omitted the
    argument, silently inheriting the library's normal_fixed=True default and
    solving a problem two tilt DOF smaller than production (which runs at
    False). The omission was unrecoverable from their own artifacts: the
    neighbouring shared_interface key WAS recorded, so a reader met one
    interface-model flag present and the other absent and reasonably (but
    wrongly) inferred it was considered.
    """
    missing: list[str] = []
    for rel_path in NORMAL_FIXED_MODULES:
        path = REPO_ROOT / rel_path
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            callee = _callee_name(node)
            if callee not in _NORMAL_FIXED_CALLEES:
                continue
            if not any(kw.arg == "normal_fixed" for kw in node.keywords):
                missing.append(f"{rel_path}:{node.lineno} -- {callee}(...)")
    assert not missing, (
        "The following calls omit normal_fixed, silently inheriting the "
        "library's normal_fixed=True default instead of stating the "
        "resolved value explicitly:\n" + "\n".join(missing)
    )


class TestE1AndE7BenchmarkRecordsCarryASeed:
    """Plan 26-13.

    `gate3_provenance` reads `record["seed"]` or `record["solver_config"]["seed"]`
    (`check_rerun_gates.py:374-378`). E1's and E7's call sites never passed one, so
    every run -- including the 26-10 smoke pass, on records it had just written --
    produced six unconditional gate FAILs.

    E7's four records here are written by a REAL reduced-scale run of the experiment.
    E1's two are constructed through the same writer with a representative payload,
    because E1's own `--smoke` path writes into an internal TemporaryDirectory that
    `--out` cannot redirect (`e1_refractive_comparison.py:893`), so no file it writes
    survives the call. The E1 assertion therefore covers the writer contract, not
    E1's argument threading; the call sites are covered by `test_e1_call_sites_pass_a_seed`.
    """

    E7_RECORDS = (
        "e7_benchmark_shared_fixed.json",
        "e7_benchmark_shared_refined.json",
        "e7_benchmark_percamera_fixed.json",
        "e7_benchmark_percamera_refined.json",
    )
    E1_RECORDS = (
        "e1_benchmark_refractive.json",
        "e1_benchmark_nonrefractive.json",
    )

    def test_e7_records_from_a_real_run_carry_a_seed(self, tmp_path):
        from experiments.check_rerun_gates import _provenance_gaps
        from experiments.e7_interface_ablation import (
            _write_ablation_artifacts,
            run_all_arms,
        )

        results, scenario = run_all_arms(seed=7, smoke=True)
        _write_ablation_artifacts(results, scenario, tmp_path, force=True, seed=7)

        for name in self.E7_RECORDS:
            path = tmp_path / name
            assert path.exists(), f"{name} was not written by the run"
            record = _load_json(path)
            assert record["solver_config"]["seed"] == 7, (
                f"{name} carries solver_config['seed']="
                f"{record['solver_config'].get('seed')!r}, expected 7"
            )
            assert _provenance_gaps(record, require_water_index=True) == [], (
                f"{name} still fails gate3_provenance"
            )

    def test_e1_records_carry_a_seed_through_the_writer(self, tmp_path):
        from experiments._io import write_direct_call_benchmark
        from experiments.check_rerun_gates import _provenance_gaps
        from experiments.e7_interface_ablation import (
            _build_arm_benchmark_payload,
            run_all_arms,
        )

        results, scenario = run_all_arms(seed=11, smoke=True)
        problem_shape, solver_config, accuracy = _build_arm_benchmark_payload(
            results[0], scenario
        )
        assert "seed" not in solver_config, (
            "the payload builder must not pre-seed solver_config -- "
            "write_direct_call_benchmark raises on a duplicate key"
        )

        for name in self.E1_RECORDS:
            path = tmp_path / name
            write_direct_call_benchmark(
                path,
                problem_shape=problem_shape,
                timings=results[0].elapsed_seconds,
                diagnostics=results[0].diagnostics,
                seed=11,
                solver_config=solver_config,
                accuracy=accuracy,
                force=True,
            )
            record = _load_json(path)
            assert record["solver_config"]["seed"] == 11
            assert _provenance_gaps(record, require_water_index=True) == []

    def test_e1_call_sites_pass_a_seed(self):
        """Every `write_direct_call_benchmark` call in E1 and E7 passes `seed=`.

        Read from the SOURCE rather than a run, because E1's full and band paths are
        minutes-long and its smoke path writes nowhere reachable. A call site that
        stops passing the seed fails here even though no file is produced.
        """
        import ast

        for module in (
            "experiments/e1_refractive_comparison.py",
            "experiments/e7_interface_ablation.py",
        ):
            tree = ast.parse(pathlib.Path(module).read_text(encoding="utf-8"))
            calls = [
                node
                for node in ast.walk(tree)
                if isinstance(node, ast.Call)
                and getattr(node.func, "id", None) == "write_direct_call_benchmark"
            ]
            assert calls, f"{module}: no write_direct_call_benchmark calls found"
            for call in calls:
                kwargs = {kw.arg for kw in call.keywords}
                assert "seed" in kwargs, (
                    f"{module}:{call.lineno} calls write_direct_call_benchmark "
                    f"without seed= -- gate3_provenance will FAIL on its output"
                )


class TestResolvedTreeIsObservable:
    """Plan 26-14.

    These rails were repointed at the archive by 26-01 because DRIVER-04 emptied
    `experiments/results/`. Nothing repointed them back, so after Phase 28 they would have
    passed green while validating history rather than the frozen run's output.
    """

    def test_the_resolved_tree_is_named(self):
        """`RESULTS_TREE` reports which tree the module is actually checking.

        It is "archive" today and FLIPS TO "live" once Phase 28 repopulates
        `experiments/results/` -- that flip is the point of plan 26-14, so this asserts the
        marker is honest about the directory it names, never that the archive is permanent.
        """
        assert RESULTS_TREE in {"archive", "live"}
        if RESULTS_TREE == "archive":
            assert RESULTS_DIR == archive_results_dir()
        else:
            assert RESULTS_DIR != archive_results_dir()
            assert RESULTS_DIR.name == "results"

    def test_a_populated_live_tree_would_disable_the_carve_out(self, tmp_path):
        """Simulates the Phase 28 state: with a live tree present, no record is exempt.

        Copies two real archived records into a sandbox live tree, resolves against it, and
        asserts the exemption predicate that `test_every_benchmark_record_carries_a_seed`
        applies is False there -- so the six legacy names stop being skipped the moment the
        frozen run writes its own.
        """
        live = tmp_path / "experiments" / "results"
        live.mkdir(parents=True)
        copied = 0
        for name in sorted(SEEDLESS_LEGACY_RECORDS)[:2]:
            source = archive_results_dir() / name
            if source.exists():
                (live / name).write_text(source.read_text(), encoding="utf-8")
                copied += 1
        if copied < 2:
            pytest.skip("archived legacy records absent (fresh clone)")

        resolved, which = resolve_results_dir(tmp_path)

        assert which == "live"
        assert resolved == live
        for name in SEEDLESS_LEGACY_RECORDS:
            exempt = which == "archive" and name in SEEDLESS_LEGACY_RECORDS
            assert not exempt, (
                f"{name} would still be exempt against a live tree -- the carve-out must "
                "not survive Phase 28"
            )
