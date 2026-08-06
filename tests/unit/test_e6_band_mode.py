"""Unit tests for `experiments/e6_generalization_sweep.py`'s `--seeds` band
mode (COV-03, COV-04, D-19.5-06).

Every test here runs at `--smoke` scale and writes to a `tmp_path_factory`
directory -- never `experiments/results/` and never the production E6 band
(~85-100 min/seed, forbidden by this plan). None of these tests are marked
slow.

Cost note: one E6 configuration solve at `--smoke` scale (12 cameras, 8
frames, refine_intrinsics=False) measured ~30s (2026-08-06). A real `--seeds
42,43 --smoke` band run is therefore run through a SESSION-scoped fixture
exactly ONCE and every assertion in `TestBandMode`/`TestSeedIsolation` reads
from that one run's artifacts -- calling `main()` separately per test (as
`tests/unit/test_e1_band_mode.py` does for E1's much cheaper "ideal" smoke
scenario) would multiply this module's real-solve cost well past the 500s
pytest budget this plan's acceptance criteria sets. `_band_smoke_
configurations()` (source) additionally trims the band's own `--smoke`
config set to two configurations (the shared baseline scene plus one
cameras-axis scene) for the same reason.

Mirrors `tests/unit/test_e1_band_mode.py`'s three-class shape (`TestCli`,
`TestBandMode`, `TestSingleSeedPathUnaffected`), plus a mandatory
`TestSeedIsolation` class asserting the per-seed directory isolation that is
correctness, not hygiene, for E6 specifically (its checkpoint cache is
seed-blind -- see `_run_seed_band`'s docstring, T-19.5-06-01).
"""

from __future__ import annotations

import json
import subprocess

import pandas as pd
import pytest

from experiments._io import build_experiment_arg_parser
from experiments.e6_generalization_sweep import (
    _band_smoke_configurations,
    build_arg_parser,
    build_smoke_configurations,
    main,
)


class TestCli:
    def test_help_lists_seeds(self, capsys):
        with pytest.raises(SystemExit):
            main(["--help"])
        out = capsys.readouterr().out
        assert "--seeds" in out
        assert "--no-fail-fast" in out

    def test_seeds_with_check_exits_nonzero(self):
        with pytest.raises(SystemExit) as exc_info:
            main(["--seeds", "42,43", "--check"])
        assert exc_info.value.code != 0

    def test_seeds_with_check_error_names_both_flags(self, capsys):
        with pytest.raises(SystemExit):
            main(["--seeds", "42,43", "--check"])
        err = capsys.readouterr().err
        assert "--seeds" in err
        assert "--check" in err

    def test_validate_e6_args_directly_rejects_seeds_with_check(self):
        from experiments.e6_generalization_sweep import _validate_e6_args

        parser = build_arg_parser()
        args = parser.parse_args(["--seeds", "42,43", "--check"])
        with pytest.raises(SystemExit):
            _validate_e6_args(parser, args)


@pytest.fixture(scope="module")
def band_run_dir(tmp_path_factory):
    """Run `--smoke --seeds 42,43` exactly ONCE for the whole module and
    return the `--out` directory every other test in this module reads
    from (see module docstring's cost note)."""
    out_dir = tmp_path_factory.mktemp("e6_band_smoke")
    exit_code = main(["--smoke", "--seeds", "42,43", "--out", str(out_dir)])
    assert exit_code == 0
    return out_dir


class TestBandMode:
    def test_band_csv_written_at_smoke_scale(self, band_run_dir):
        band_path = band_run_dir / "generalization_sweep_band.csv"
        assert band_path.exists()

        df = pd.read_csv(band_path)
        smoke_config_count = len(_band_smoke_configurations())
        assert len(df) == 2 * smoke_config_count
        assert "seed" in df.columns
        assert sorted(df["seed"].unique().tolist()) == [42, 43]

    def test_band_mode_does_not_write_single_seed_csv(self, band_run_dir):
        assert not (band_run_dir / "generalization_sweep.csv").exists()

    def test_band_mode_writes_provenance_sidecar(self, band_run_dir):
        sidecar_path = band_run_dir / "e6_seed_band_provenance.json"
        assert sidecar_path.exists()
        with open(sidecar_path) as f:
            sidecar = json.load(f)
        assert sidecar["solver_config"]["seeds"] == [42, 43]
        assert sidecar["include_cameras_axis"] is True
        assert set(sidecar["status_counts_by_seed"]) == {"42", "43"}
        smoke_config_count = len(_band_smoke_configurations())
        for counts in sidecar["status_counts_by_seed"].values():
            assert isinstance(counts, dict)
            assert sum(counts.values()) == smoke_config_count
        assert "scope" in sidecar
        assert "seed" in sidecar["scope"]
        assert isinstance(sidecar["seconds"], (int, float))
        assert sidecar["git_sha"]

    def test_no_results_dir_modified(self, band_run_dir):
        """Nothing under experiments/results/ was touched by the band run
        (the fixture already ran it; this asserts the CURRENT state, which
        is unaffected by tests running before or after this one)."""
        result = subprocess.run(
            ["git", "status", "--porcelain", "experiments/results/"],
            capture_output=True,
            text=True,
        )
        assert result.stdout == ""


class TestSeedIsolation:
    """T-19.5-06-01 (mandatory): E6's checkpoint cache is seed-blind, so a
    two-seed band MUST produce two distinct e6_configs/ directories -- one
    per seed -- and no e6_configs/ directory at the band root itself."""

    def test_two_seeds_produce_two_distinct_config_dirs(self, band_run_dir):
        seed_42_configs = band_run_dir / "e6_band" / "seed_42" / "e6_configs"
        seed_43_configs = band_run_dir / "e6_band" / "seed_43" / "e6_configs"
        assert seed_42_configs.is_dir()
        assert seed_43_configs.is_dir()

        seed_42_files = sorted(p.name for p in seed_42_configs.glob("*.json"))
        seed_43_files = sorted(p.name for p in seed_43_configs.glob("*.json"))
        assert seed_42_files == seed_43_files  # same config_keys, isolated dirs
        assert len(seed_42_files) > 0

        # No e6_configs/ directory exists at the band root itself -- proves
        # the isolation is per-seed, not merely per-band.
        assert not (band_run_dir / "e6_configs").exists()

    def test_isolated_seeds_are_not_silently_resumed(self, band_run_dir):
        """Each seed's checkpoint records its OWN seed -- not a cached
        result from the other seed. This is the direct proof that the
        isolation prevents the seed-blind cache from resuming a prior
        seed's result under a new label (T-19.5-06-01)."""
        seed_42_dir = band_run_dir / "e6_band" / "seed_42" / "e6_configs"
        seed_43_dir = band_run_dir / "e6_band" / "seed_43" / "e6_configs"

        for config_path in seed_42_dir.glob("*.json"):
            with open(config_path) as f:
                checkpoint = json.load(f)
            assert checkpoint["seed"] == 42

        for config_path in seed_43_dir.glob("*.json"):
            with open(config_path) as f:
                checkpoint = json.load(f)
            assert checkpoint["seed"] == 43


class TestSingleSeedPathUnaffected:
    def test_seeds_none_dispatches_to_run_smoke_not_run_seed_band(self, monkeypatch):
        """When --seeds is not given, main() dispatches to _run_smoke, never
        _run_seed_band -- verified via monkeypatched stubs (no real solve),
        mirroring this module's own convention that a real --smoke solve is
        verified by the plan's <verify> block, not by pytest."""
        import experiments.e6_generalization_sweep as m

        calls: list[str] = []
        monkeypatch.setattr(m, "_run_smoke", lambda args: calls.append("smoke") or 0)
        monkeypatch.setattr(
            m,
            "_run_seed_band",
            lambda *a, **k: calls.append("seed_band"),
        )

        exit_code = m.main(["--smoke"])

        assert exit_code == 0
        assert calls == ["smoke"]

    def test_seeds_given_dispatches_to_run_seed_band_not_run_smoke(self, monkeypatch):
        import experiments.e6_generalization_sweep as m

        calls: list[str] = []
        monkeypatch.setattr(m, "_run_smoke", lambda args: calls.append("smoke") or 0)
        monkeypatch.setattr(
            m,
            "_run_seed_band",
            lambda *a, **k: calls.append("seed_band"),
        )

        exit_code = m.main(["--smoke", "--seeds", "42,43"])

        assert exit_code == 0
        assert calls == ["seed_band"]

    def test_plain_smoke_config_count_unaffected(self):
        """--smoke's own config set (no --seeds) is unchanged: six rows,
        four scenes -- the cameras axis stays band-mode-only."""
        configs = build_smoke_configurations()
        assert len(configs) == 6
        assert sum(1 for c in configs if c["is_baseline"]) == 3
        assert all(c["axis"] != "cameras" for c in configs)

    def test_shared_five_flag_contract_unchanged(self):
        parser = build_experiment_arg_parser()
        options = sorted(
            a.option_strings[0] for a in parser._actions if a.option_strings
        )
        assert options == ["--check", "--force", "--out", "--seed", "--smoke"]
