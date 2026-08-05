"""Unit tests for experiments/check_rerun_gates.py (plan 19.3-08, TDD).

Builds small synthetic fixture trees rather than depending on committed
`experiments/results/` state, so these tests are stable across re-runs.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from experiments.check_rerun_gates import (
    GateResult,
    check_band_csv,
    check_e1,
    check_e3,
    check_e4,
    check_e5,
    check_e6,
    check_e7,
    main,
    run_all_gates,
)


def _write_json(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(record, f)


def _good_environment(git_sha: str = "a" * 40) -> dict:
    return {
        "aquacal_version": "1.9.0",
        "git_sha": git_sha,
        "git_sha_source": "git_rev_parse",
    }


def _good_stages() -> dict:
    return {
        "stage3_interface_optimization": {"optimality": 1e-3},
        "stage3_intrinsic_pass": {"optimality": 2e-2},
    }


def _find(
    results: list[GateResult], *, experiment: str, gate_prefix: str
) -> list[GateResult]:
    return [
        r
        for r in results
        if r.experiment == experiment and r.gate.startswith(gate_prefix)
    ]


def _verdicts(
    results: list[GateResult], *, experiment: str, gate_prefix: str
) -> list[str]:
    return [
        r.verdict
        for r in _find(results, experiment=experiment, gate_prefix=gate_prefix)
    ]


class TestGate1GuardCount:
    """Gate 1: degenerate_observations_at_solution must be zero everywhere."""

    def test_pass_path_json_record_zero_guard_count(self, tmp_path):
        _write_json(
            tmp_path / "e1_benchmark_refractive.json",
            {
                "environment": _good_environment(),
                "solver_config": {"seed": 42, "n_water": 1.333},
                "problem_shape": {"degenerate_observations_at_solution": 0},
                "stages": _good_stages(),
            },
        )
        _write_json(
            tmp_path / "e1_benchmark_nonrefractive.json",
            {
                "environment": _good_environment(),
                "solver_config": {"seed": 42, "n_water": 1.333},
                "problem_shape": {"degenerate_observations_at_solution": 0},
                "stages": _good_stages(),
            },
        )
        results = check_e1(tmp_path)
        verdicts = _verdicts(results, experiment="E1", gate_prefix="gate1_guard_count")
        assert verdicts == ["PASS", "PASS"]

    def test_fail_path_json_record_nonzero_guard_count(self, tmp_path):
        _write_json(
            tmp_path / "e1_benchmark_refractive.json",
            {
                "environment": _good_environment(),
                "solver_config": {"seed": 42, "n_water": 1.333},
                "problem_shape": {"degenerate_observations_at_solution": 3},
                "stages": _good_stages(),
            },
        )
        _write_json(
            tmp_path / "e1_benchmark_nonrefractive.json",
            {
                "environment": _good_environment(),
                "solver_config": {"seed": 42, "n_water": 1.333},
                "problem_shape": {"degenerate_observations_at_solution": 0},
                "stages": _good_stages(),
            },
        )
        results = check_e1(tmp_path)
        verdicts = _verdicts(results, experiment="E1", gate_prefix="gate1_guard_count")
        assert "FAIL" in verdicts

    def test_fail_path_missing_guard_field_is_not_treated_as_zero(self, tmp_path):
        _write_json(
            tmp_path / "e1_benchmark_refractive.json",
            {
                "environment": _good_environment(),
                "solver_config": {"seed": 42, "n_water": 1.333},
                "problem_shape": {},
                "stages": _good_stages(),
            },
        )
        _write_json(
            tmp_path / "e1_benchmark_nonrefractive.json",
            {
                "environment": _good_environment(),
                "solver_config": {"seed": 42, "n_water": 1.333},
                "problem_shape": {},
                "stages": _good_stages(),
            },
        )
        results = check_e1(tmp_path)
        result = _find(
            results,
            experiment="E1",
            gate_prefix="gate1_guard_count:e1_benchmark_refractive",
        )[0]
        assert result.verdict == "FAIL"
        assert "cannot confirm zero" in result.detail

    def test_pass_path_aggregated_csv_all_zero(self, tmp_path):
        cells = tmp_path / "e4_cells"
        for name in ("cameras_8_frames_50",):
            _write_json(
                cells / name / "benchmark.json",
                {
                    "environment": _good_environment(),
                    "solver_config": {"seed": 42, "n_water": 1.333},
                    "problem_shape": {"degenerate_observations_at_solution": 0},
                    "stages": _good_stages(),
                },
            )
        df = pd.DataFrame(
            {"cell_key": ["a", "b"], "degenerate_observations_at_solution": [0, 0]}
        )
        df.to_csv(tmp_path / "benchmark_grid.csv", index=False)
        results = check_e4(tmp_path)
        result = _find(
            results, experiment="E4", gate_prefix="gate1_guard_count:benchmark_grid.csv"
        )[0]
        assert result.verdict == "PASS"

    def test_fail_path_aggregated_csv_nonzero_row(self, tmp_path):
        cells = tmp_path / "e4_cells"
        _write_json(
            cells / "cameras_8_frames_50" / "benchmark.json",
            {
                "environment": _good_environment(),
                "solver_config": {"seed": 42, "n_water": 1.333},
                "problem_shape": {"degenerate_observations_at_solution": 0},
                "stages": _good_stages(),
            },
        )
        df = pd.DataFrame(
            {"cell_key": ["a", "b"], "degenerate_observations_at_solution": [0, 5]}
        )
        df.to_csv(tmp_path / "benchmark_grid.csv", index=False)
        results = check_e4(tmp_path)
        result = _find(
            results, experiment="E4", gate_prefix="gate1_guard_count:benchmark_grid.csv"
        )[0]
        assert result.verdict == "FAIL"
        assert "1 of 2" in result.detail

    def test_fail_path_aggregated_csv_missing_column(self, tmp_path):
        df = pd.DataFrame({"cell_key": ["a", "b"]})
        df.to_csv(tmp_path / "benchmark_grid.csv", index=False)
        results = check_e4(tmp_path)
        result = _find(
            results, experiment="E4", gate_prefix="gate1_guard_count:benchmark_grid.csv"
        )[0]
        assert result.verdict == "FAIL"
        assert "no " in result.detail and "column present" in result.detail


class TestGate2Status:
    """Gate 2: no row is published with status == 'degenerate'."""

    def test_pass_path_no_degenerate_rows(self, tmp_path):
        df = pd.DataFrame(
            {
                "cell_key": ["a", "b"],
                "status": ["ok", "ok"],
                "degenerate_observations_at_solution": [0, 0],
            }
        )
        df.to_csv(tmp_path / "generalization_sweep.csv", index=False)
        for name in ("baseline",):
            _write_json(
                tmp_path / "e6_configs" / f"{name}.json",
                {
                    "environment": _good_environment(),
                    "solver_config": {"seed": 42},
                    "config": {"n_water": 1.333},
                    "degenerate_observations_at_solution": 0,
                    "metrics": {"optimality_stage3_interface_optimization": 1e-3},
                },
            )
        results = check_e6(tmp_path)
        result = _find(
            results,
            experiment="E6",
            gate_prefix="gate2_status:generalization_sweep.csv",
        )[0]
        assert result.verdict == "PASS"

    def test_fail_path_a_degenerate_row_is_published(self, tmp_path):
        df = pd.DataFrame(
            {
                "cell_key": ["a", "b"],
                "status": ["ok", "degenerate"],
                "degenerate_observations_at_solution": [0, 4],
            }
        )
        df.to_csv(tmp_path / "generalization_sweep.csv", index=False)
        results = check_e6(tmp_path)
        result = _find(
            results,
            experiment="E6",
            gate_prefix="gate2_status:generalization_sweep.csv",
        )[0]
        assert result.verdict == "FAIL"
        assert "1 row" in result.detail

    def test_na_path_no_status_column_reports_na_not_skip(self, tmp_path):
        df = pd.DataFrame({"seed": [42, 42]})
        df.to_csv(tmp_path / "index_sensitivity.csv", index=False)
        _write_json(
            tmp_path / "e5_provenance.json",
            {
                "environment": _good_environment(),
                "solver_config": {"seed": 42},
                "n_true": 1.333,
                "discard_stats": {"degenerate_observations_at_solution": 0},
            },
        )
        results = check_e5(tmp_path)
        result = _find(results, experiment="E5", gate_prefix="gate2_status")[0]
        assert result.verdict == "N/A"
        assert "no" in result.detail.lower()


class TestGate3Provenance:
    """Gate 3: git_sha, seed, water index and a timestamp must be present;
    every git_sha in the whole run must match."""

    def test_pass_path_all_fields_present(self, tmp_path):
        _write_json(
            tmp_path / "e7_benchmark_shared_fixed.json",
            {
                "environment": _good_environment(),
                "solver_config": {"seed": 42, "n_water": 1.333},
                "problem_shape": {"degenerate_observations_at_solution": 0},
                "stages": _good_stages(),
            },
        )
        for arm in ("shared_refined", "percamera_fixed", "percamera_refined"):
            _write_json(
                tmp_path / f"e7_benchmark_{arm}.json",
                {
                    "environment": _good_environment(),
                    "solver_config": {"seed": 42, "n_water": 1.333},
                    "problem_shape": {"degenerate_observations_at_solution": 0},
                    "stages": _good_stages(),
                },
            )
        results = check_e7(tmp_path)
        result = _find(
            results,
            experiment="E7",
            gate_prefix="gate3_provenance:e7_benchmark_shared_fixed",
        )[0]
        assert result.verdict == "PASS"

    def test_fail_path_missing_seed(self, tmp_path):
        _write_json(
            tmp_path / "e7_benchmark_shared_fixed.json",
            {
                "environment": _good_environment(),
                "solver_config": {"n_water": 1.333},
                "problem_shape": {"degenerate_observations_at_solution": 0},
                "stages": _good_stages(),
            },
        )
        results = check_e7(tmp_path)
        result = _find(
            results,
            experiment="E7",
            gate_prefix="gate3_provenance:e7_benchmark_shared_fixed",
        )[0]
        assert result.verdict == "FAIL"
        assert "seed" in result.detail

    def test_fail_path_missing_git_sha(self, tmp_path):
        _write_json(
            tmp_path / "e7_benchmark_shared_fixed.json",
            {
                "environment": {"git_sha": None},
                "solver_config": {"seed": 42, "n_water": 1.333},
                "problem_shape": {"degenerate_observations_at_solution": 0},
                "stages": _good_stages(),
            },
        )
        results = check_e7(tmp_path)
        result = _find(
            results,
            experiment="E7",
            gate_prefix="gate3_provenance:e7_benchmark_shared_fixed",
        )[0]
        assert result.verdict == "FAIL"
        assert "git_sha" in result.detail

    def test_e5_uses_n_true_as_its_water_index_field(self, tmp_path):
        _write_json(
            tmp_path / "e5_provenance.json",
            {
                "environment": _good_environment(),
                "solver_config": {"seed": 42},
                "n_true": 1.333,
                "discard_stats": {"degenerate_observations_at_solution": 0},
            },
        )
        results = check_e5(tmp_path)
        result = _find(results, experiment="E5", gate_prefix="gate3_provenance")[0]
        assert result.verdict == "PASS"

    def test_git_sha_consistency_fails_on_a_split_sha(self, tmp_path):
        _write_json(
            tmp_path / "e3_provenance.json",
            {
                "experiment": "e3",
                "environment": _good_environment(git_sha="a" * 40),
                "solver_config": {"seed": 42},
                "seed": 42,
            },
        )
        _write_json(
            tmp_path / "e5_provenance.json",
            {
                "environment": _good_environment(git_sha="b" * 40),
                "solver_config": {"seed": 42},
                "n_true": 1.333,
                "discard_stats": {"degenerate_observations_at_solution": 0},
            },
        )
        results = run_all_gates(tmp_path)
        result = _find(
            results, experiment="ALL", gate_prefix="gate3_git_sha_consistency"
        )[0]
        assert result.verdict == "FAIL"
        assert "committed while the queue's run was in flight" in result.detail

    def test_git_sha_consistency_passes_when_uniform(self, tmp_path):
        sha = "c" * 40
        _write_json(
            tmp_path / "e3_provenance.json",
            {
                "experiment": "e3",
                "environment": _good_environment(git_sha=sha),
                "solver_config": {"seed": 42},
                "seed": 42,
            },
        )
        _write_json(
            tmp_path / "e5_provenance.json",
            {
                "environment": _good_environment(git_sha=sha),
                "solver_config": {"seed": 42},
                "n_true": 1.333,
                "discard_stats": {"degenerate_observations_at_solution": 0},
            },
        )
        results = run_all_gates(tmp_path)
        result = _find(
            results, experiment="ALL", gate_prefix="gate3_git_sha_consistency"
        )[0]
        assert result.verdict == "PASS"


class TestGate4Optimality:
    """Gate 4: first-order optimality present, never compared to a value."""

    def test_pass_path_stages_block_present(self, tmp_path):
        _write_json(
            tmp_path / "e1_benchmark_refractive.json",
            {
                "environment": _good_environment(),
                "solver_config": {"seed": 42, "n_water": 1.333},
                "problem_shape": {"degenerate_observations_at_solution": 0},
                "stages": _good_stages(),
            },
        )
        _write_json(
            tmp_path / "e1_benchmark_nonrefractive.json",
            {
                "environment": _good_environment(),
                "solver_config": {"seed": 42, "n_water": 1.333},
                "problem_shape": {"degenerate_observations_at_solution": 0},
                "stages": _good_stages(),
            },
        )
        results = check_e1(tmp_path)
        verdicts = _verdicts(results, experiment="E1", gate_prefix="gate4_optimality")
        assert verdicts == ["PASS", "PASS"]

    def test_fail_path_optimality_null(self, tmp_path):
        _write_json(
            tmp_path / "e1_benchmark_refractive.json",
            {
                "environment": _good_environment(),
                "solver_config": {"seed": 42, "n_water": 1.333},
                "problem_shape": {"degenerate_observations_at_solution": 0},
                "stages": {"stage3_interface_optimization": {"optimality": None}},
            },
        )
        _write_json(
            tmp_path / "e1_benchmark_nonrefractive.json",
            {
                "environment": _good_environment(),
                "solver_config": {"seed": 42, "n_water": 1.333},
                "problem_shape": {"degenerate_observations_at_solution": 0},
                "stages": _good_stages(),
            },
        )
        results = check_e1(tmp_path)
        result = _find(
            results,
            experiment="E1",
            gate_prefix="gate4_optimality:e1_benchmark_refractive",
        )[0]
        assert result.verdict == "FAIL"

    def test_pass_path_e6_metrics_shape(self, tmp_path):
        _write_json(
            tmp_path / "e6_configs" / "baseline.json",
            {
                "environment": _good_environment(),
                "solver_config": {"seed": 42},
                "config": {"n_water": 1.333},
                "degenerate_observations_at_solution": 0,
                "metrics": {
                    "optimality_stage3_interface_optimization": 1e-3,
                    "optimality_stage3_intrinsic_pass": 2e-2,
                },
            },
        )
        results = check_e6(tmp_path)
        result = _find(
            results,
            experiment="E6",
            gate_prefix="gate4_optimality:e6_configs/baseline.json",
        )[0]
        assert result.verdict == "PASS"


class TestE3ShapedFixture:
    """E3 runs no calibration: gates 1, 2 and 4 must be N/A with a reason,
    never silently skipped -- gate 3 still applies."""

    def test_gates_1_2_4_report_na_with_reason(self, tmp_path):
        _write_json(
            tmp_path / "e3_provenance.json",
            {
                "experiment": "e3",
                "environment": _good_environment(),
                "solver_config": {"seed": 42},
                "seed": 42,
            },
        )
        results = check_e3(tmp_path)
        by_gate = {r.gate: r for r in results}
        assert by_gate["gate1_guard_count"].verdict == "N/A"
        assert "no calibration" in by_gate["gate1_guard_count"].detail
        assert by_gate["gate2_status"].verdict == "N/A"
        assert "no calibration" in by_gate["gate2_status"].detail
        assert by_gate["gate4_optimality"].verdict == "N/A"
        assert "no calibration" in by_gate["gate4_optimality"].detail

    def test_gate_3_still_enforced_on_provenance_sidecar(self, tmp_path):
        _write_json(
            tmp_path / "e3_provenance.json",
            {
                "experiment": "e3",
                "environment": {"git_sha": None},
                "solver_config": {},
            },
        )
        results = check_e3(tmp_path)
        gate3 = [r for r in results if r.gate.startswith("gate3_provenance")][0]
        assert gate3.verdict == "FAIL"

    def test_gate_3_passes_when_sidecar_is_complete(self, tmp_path):
        _write_json(
            tmp_path / "e3_provenance.json",
            {
                "experiment": "e3",
                "environment": _good_environment(),
                "solver_config": {"seed": 42},
                "seed": 42,
            },
        )
        results = check_e3(tmp_path)
        gate3 = [r for r in results if r.gate.startswith("gate3_provenance")][0]
        assert gate3.verdict == "PASS"


class TestMainCli:
    def test_exit_code_nonzero_on_missing_artifacts(self, tmp_path):
        assert main([str(tmp_path)]) == 1

    def test_exit_code_zero_on_a_fully_passing_tree(self, tmp_path, capsys):
        sha = "d" * 40

        def env():
            return _good_environment(git_sha=sha)

        _write_json(
            tmp_path / "e1_benchmark_refractive.json",
            {
                "environment": env(),
                "solver_config": {"seed": 42, "n_water": 1.333},
                "problem_shape": {"degenerate_observations_at_solution": 0},
                "stages": _good_stages(),
            },
        )
        _write_json(
            tmp_path / "e1_benchmark_nonrefractive.json",
            {
                "environment": env(),
                "solver_config": {"seed": 42, "n_water": 1.333},
                "problem_shape": {"degenerate_observations_at_solution": 0},
                "stages": _good_stages(),
            },
        )
        _write_json(
            tmp_path / "e3_provenance.json",
            {
                "experiment": "e3",
                "environment": env(),
                "solver_config": {"seed": 42},
                "seed": 42,
            },
        )
        for cell in ("cameras_8_frames_50",):
            _write_json(
                tmp_path / "e4_cells" / cell / "benchmark.json",
                {
                    "environment": env(),
                    "solver_config": {"seed": 42, "n_water": 1.333},
                    "problem_shape": {"degenerate_observations_at_solution": 0},
                    "stages": _good_stages(),
                },
            )
        pd.DataFrame(
            {
                "cell_key": ["cameras_8_frames_50"],
                "status": ["ok"],
                "degenerate_observations_at_solution": [0],
            }
        ).to_csv(tmp_path / "benchmark_grid.csv", index=False)
        _write_json(
            tmp_path / "e5_provenance.json",
            {
                "environment": env(),
                "solver_config": {"seed": 42},
                "n_true": 1.333,
                "discard_stats": {"degenerate_observations_at_solution": 0},
            },
        )
        pd.DataFrame({"seed": [42]}).to_csv(
            tmp_path / "index_sensitivity.csv", index=False
        )
        _write_json(
            tmp_path / "e6_configs" / "baseline.json",
            {
                "environment": env(),
                "solver_config": {"seed": 42},
                "config": {"n_water": 1.333},
                "degenerate_observations_at_solution": 0,
                "metrics": {
                    "optimality_stage3_interface_optimization": 1e-3,
                    "optimality_stage3_intrinsic_pass": 2e-2,
                },
            },
        )
        pd.DataFrame(
            {
                "config_key": ["baseline"],
                "status": ["ok"],
                "degenerate_observations_at_solution": [0],
            }
        ).to_csv(tmp_path / "generalization_sweep.csv", index=False)
        for arm in (
            "shared_fixed",
            "shared_refined",
            "percamera_fixed",
            "percamera_refined",
        ):
            _write_json(
                tmp_path / f"e7_benchmark_{arm}.json",
                {
                    "environment": env(),
                    "solver_config": {"seed": 42, "n_water": 1.333},
                    "problem_shape": {"degenerate_observations_at_solution": 0},
                    "stages": _good_stages(),
                },
            )
        pd.DataFrame({"seed": [42]}).to_csv(
            tmp_path / "interface_ablation.csv", index=False
        )

        exit_code = main([str(tmp_path)])
        captured = capsys.readouterr()
        assert exit_code == 0, captured.out
        assert "0 FAIL" in captured.out


# ---------------------------------------------------------------------------
# D-19.4-14 band-CSV gates (SC-5a)
#
# A band exists to make a published number regenerable. The gate must therefore
# check that the CSV really carries the N independent seeds its provenance
# claims -- a short band silently quoted as a 10-seed band is the failure mode
# these tests pin down.
# ---------------------------------------------------------------------------


def _write_band(path: Path, seeds: list[int]) -> None:
    """Two rows per seed, so distinct-seed counting is exercised rather than
    plain row counting."""
    rows = {"seed": [s for s in seeds for _ in range(2)]}
    rows["value"] = list(range(len(rows["seed"])))
    pd.DataFrame(rows).to_csv(path, index=False)


def test_band_gate_na_when_csv_absent(tmp_path):
    results = check_band_csv(
        "E7", tmp_path, "interface_ablation_band.csv", "e7_benchmark_*.json"
    )
    assert len(results) == 1
    assert results[0].verdict == "N/A"


def test_band_gate_passes_when_distinct_seeds_match_sidecar(tmp_path):
    seeds = [42, 43, 44]
    _write_band(tmp_path / "interface_ablation_band.csv", seeds)
    _write_json(
        tmp_path / "e7_benchmark_shared_fixed.json",
        {"solver_config": {"seeds": seeds}},
    )
    results = check_band_csv(
        "E7", tmp_path, "interface_ablation_band.csv", "e7_benchmark_*.json"
    )
    assert results[0].verdict == "PASS", results[0].detail


def test_band_gate_fails_when_band_is_short(tmp_path):
    """The negative case: the sidecar records 10 seeds, the CSV holds 3."""
    _write_band(tmp_path / "exp1_band.csv", [42, 43, 44])
    _write_json(
        tmp_path / "e1_benchmark_refractive.json",
        {"solver_config": {"seeds": list(range(42, 52))}},
    )
    results = check_band_csv("E1", tmp_path, "exp1_band.csv", "e1_benchmark_*.json")
    assert results[0].verdict == "FAIL"
    assert "must never be quoted as a full one" in results[0].detail


def test_band_gate_fails_without_seed_column(tmp_path):
    pd.DataFrame({"value": [1, 2]}).to_csv(tmp_path / "exp1_band.csv", index=False)
    _write_json(
        tmp_path / "e1_benchmark_refractive.json",
        {"solver_config": {"seeds": [42]}},
    )
    results = check_band_csv("E1", tmp_path, "exp1_band.csv", "e1_benchmark_*.json")
    assert results[0].verdict == "FAIL"
    assert "no 'seed' column" in results[0].detail


def test_band_gate_fails_when_sidecar_records_no_seeds(tmp_path):
    """A band CSV with no provenance to check it against is unverifiable, which
    is a FAIL rather than a pass-by-absence."""
    _write_band(tmp_path / "interface_ablation_band.csv", [42, 43])
    _write_json(
        tmp_path / "e7_benchmark_shared_fixed.json",
        {"solver_config": {"seed": 42}},
    )
    results = check_band_csv(
        "E7", tmp_path, "interface_ablation_band.csv", "e7_benchmark_*.json"
    )
    assert results[0].verdict == "FAIL"
    assert "cannot be verified" in results[0].detail
