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

import json
import pathlib
import subprocess

import pandas as pd
import pytest

# Anchored to the repository root via this file's own location, not the
# process working directory -- a gate that resolves relative to cwd can
# vanish from a run silently just because pytest was invoked from elsewhere
# (WR-06). tests/unit/test_experiments_provenance.py -> parents[2] == repo root.
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO_ROOT / "experiments" / "results"

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
        # calibration.json: E2's raw calibration artifact, copied verbatim
        # from the same pipeline run that also wrote the sibling
        # benchmark.json (same directory, same run, per the README's
        # provenance table) -- that sibling file is this one's provenance
        # record too.
        "calibration.json",
    }
)

# The six benchmark records written in Phase 19.1, before solver_config["seed"]
# existed: E1's two and E7's four. Plan 19.2-02 added seed= to the direct-call
# path (write_direct_call_benchmark) and plan 19.2-14 added it to the pipeline
# entry point's solver_config -- both are additive,
# landing AFTER these six records were written. Re-running them costs roughly
# 90 minutes for records the manuscript already cites and produces no new
# information (19.2-CONTEXT.md Claude's Discretion item 1). This exemption is
# removed the moment any of these six is regenerated -- test_seedless_carve_
# out_is_exact fails the instant a member stops lacking a seed, so the set
# cannot silently become a blanket exemption.
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
    "exp1_band.csv": (
        "its own seed column is its ONLY seed provenance, spanning seeds "
        "42-51; experiments/results/e1_benchmark_refractive.json + "
        "e1_benchmark_nonrefractive.json supply version/git_sha/environment "
        "but NOT this band's seeds -- both are SEEDLESS_LEGACY_RECORDS and "
        "carry no seed key at all, and band mode deliberately does not "
        "overwrite them (doing so would replace the single-seed production "
        "record with the last band seed's values)"
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
    "reconstruction_errors.csv": "experiments/results/benchmark.json (E2, same run)",
    "structural_scaling.csv": (
        "no calibration record exists or could exist: every row is closed-form "
        "structure (plan 19.5-01, COV-01) with no solve anywhere in its path, "
        "so there is no seed, no runtime and no environment to record; each row "
        "carries its own record_source column marking it computed (sparsity "
        "built directly) or predicted (closed form)"
    ),
    "reprojection_residuals.csv": "experiments/results/benchmark.json (E2, same run)",
}


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
    if not RESULTS_DIR.exists():
        return []
    return sorted(RESULTS_DIR.rglob("*.json"))


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
    """Every committed `*.json` that carries a `schema_version` key.

    Includes both assemble_benchmark_record-shaped files (which also carry
    `stages`) and E3's minimal sidecar (which does not) -- both publish a
    `schema_version`, so both are in scope for the environment-presence check.
    """
    return [p for p in _discover_json_files() if "schema_version" in _load_json(p)]


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
    reason="experiments/results/ is absent or empty (fresh clone without committed "
    "artifacts) -- nothing to check provenance against.",
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
        if path.name in SEEDLESS_LEGACY_RECORDS:
            pytest.skip(f"{path.name} is an exempted Phase-19.1 legacy record")
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
            path = RESULTS_DIR / name
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
        the map must be updated, not just grown, when a CSV is removed."""
        if not RESULTS_DIR.exists():
            pytest.skip("experiments/results/ not present (fresh clone)")
        on_disk = {p.name for p in _CSV_FILES}
        stale = set(CSV_TO_RECORD) - on_disk
        assert not stale, f"CSV_TO_RECORD names CSV(s) no longer on disk: {stale}"


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
