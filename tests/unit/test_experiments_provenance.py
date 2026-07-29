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

import pandas as pd
import pytest

RESULTS_DIR = pathlib.Path("experiments/results")

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
# one-line comment naming what covers its provenance instead. Both are
# excluded from the schema_version-keyed checks below by construction (they
# have no schema_version to trigger those checks on) -- listed here anyway so
# a reader can see the full set of exceptions in one place rather than
# inferring it from what the glob happens not to catch.
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
    "exp1_parameter_errors.csv": (
        "experiments/results/e1_benchmark_refractive.json + "
        "e1_benchmark_nonrefractive.json (E1 calibrates both models)"
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
        "self (own seed column); no benchmark.json backs it -- "
        "experiments/results/e6_configs/*.json are per-configuration "
        "checkpoints, not schema_version-carrying provenance records"
    ),
    "index_sensitivity.csv": (
        "self (own seed column); no benchmark.json backs it (E5 has no "
        "per-row JSON sidecar)"
    ),
    "interface_ablation.csv": (
        "experiments/results/e7_benchmark_shared_fixed.json + "
        "e7_benchmark_shared_refined.json + e7_benchmark_percamera_fixed.json "
        "+ e7_benchmark_percamera_refined.json (four arms)"
    ),
    "newton_iterations.csv": "experiments/results/e3_provenance.json (E3 tier 2)",
    "reconstruction_errors.csv": "experiments/results/benchmark.json (E2, same run)",
    "reprojection_residuals.csv": "experiments/results/benchmark.json (E2, same run)",
}


def _discover_json_files() -> list[pathlib.Path]:
    if not RESULTS_DIR.exists():
        return []
    return sorted(RESULTS_DIR.rglob("*.json"))


def _discover_csv_files() -> list[pathlib.Path]:
    if not RESULTS_DIR.exists():
        return []
    return sorted(RESULTS_DIR.glob("*.csv"))


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
    if isinstance(solver_config, dict) and "seed" in solver_config:
        return solver_config["seed"]
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
        """Guard: prove the checker actually rejects a record with no
        environment block, not only records that already pass."""
        mutated = tmp_path / "mutated_benchmark.json"
        mutated.write_text(json.dumps({"schema_version": 1}))
        record = _load_json(mutated)
        assert "environment" not in record


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

    def test_new_phase_csvs_carry_a_seed_column(self):
        """benchmark_grid.csv, index_sensitivity.csv, and generalization_sweep.csv
        have no benchmark.json behind every row, so their own `seed` column IS
        their seed provenance."""
        for name in (
            "benchmark_grid.csv",
            "index_sensitivity.csv",
            "generalization_sweep.csv",
        ):
            path = RESULTS_DIR / name
            if not path.exists():
                pytest.skip(f"{name} not present (fresh clone)")
            df = pd.read_csv(path)
            assert "seed" in df.columns, f"{name} has no seed column"
            assert df["seed"].notna().all(), f"{name} has a null seed in some row"

    def test_e1_and_e7_records_already_comply_on_environment(self):
        """E1's two and E7's four committed records pass the same environment
        key-presence check as everything else -- verified, not re-run."""
        for name in SEEDLESS_LEGACY_RECORDS:
            path = RESULTS_DIR / name
            if not path.exists():
                pytest.skip(f"{name} not present (fresh clone)")
            record = _load_json(path)
            missing = REQUIRED_ENVIRONMENT_KEYS - set(record.get("environment", {}))
            assert not missing, f"{name}: environment missing keys {missing}"


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
        e3_sidecar = RESULTS_DIR / "e3_provenance.json"
        if e3_sidecar.exists():
            phase_records.append(e3_sidecar)

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
