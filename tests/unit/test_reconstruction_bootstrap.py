"""Unit tests for `experiments.reconstruction_bootstrap` (COV-08, D-19.5-05).

All tests are fast, pure-function tests over small synthetic frames -- no I/O,
no calibration, no reading of the real committed
`experiments/results/reconstruction_errors.csv`.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import experiments.reconstruction_bootstrap as rb
from experiments.reconstruction_bootstrap import (
    cluster_bootstrap,
    percentile_ci,
    reconstruction_statistics,
    resolve_reconstruction_errors_path,
)

_CSV = "frame_idx,signed_error_m\n0,0.001\n"


def _row_bootstrap(
    df: pd.DataFrame,
    statistic,
    n_resamples: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """A naive per-row (non-clustered) bootstrap, local to this test file.

    Exists only as the "what a naive bootstrap would have done" comparator
    for `test_cluster_bootstrap_wider_than_naive_row_bootstrap_when_between_
    cluster_variance_dominates` -- it is deliberately NOT exported from
    `experiments.reconstruction_bootstrap`, since a row bootstrap is the
    anti-pattern this module exists to avoid (see the module docstring and
    the plan's design decision).
    """
    n = len(df)
    index_array = df.index.to_numpy()
    samples = np.empty(n_resamples, dtype=float)
    for i in range(n_resamples):
        drawn_idx = rng.choice(index_array, size=n, replace=True)
        samples[i] = statistic(df.loc[drawn_idx])
    return samples


class _RecordingRNG:
    """Wraps a real `np.random.Generator`, recording every `choice(size=...)`."""

    def __init__(self, rng: np.random.Generator) -> None:
        self._rng = rng
        self.choice_sizes: list[int] = []

    def choice(self, a, size=None, replace=True):
        self.choice_sizes.append(size)
        return self._rng.choice(a, size=size, replace=replace)


class TestClusterBootstrapIsClustered:
    def test_resamples_are_unions_of_whole_clusters(self):
        # 3 clusters of 4 identical-within-cluster rows.
        df = pd.DataFrame(
            {
                "cluster": [0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2],
                "value": [10.0] * 4 + [20.0] * 4 + [30.0] * 4,
            }
        )
        captured: list[pd.DataFrame] = []

        def statistic(resampled: pd.DataFrame) -> float:
            captured.append(resampled.copy())
            return float(resampled["value"].mean())

        rng = np.random.default_rng(0)
        cluster_bootstrap(df, "cluster", statistic, n_resamples=25, rng=rng)

        assert len(captured) == 25
        for resampled in captured:
            counts = resampled["value"].value_counts()
            for value, count in counts.items():
                # Every cluster in this fixture has size 4 -- a resample
                # that is a union of whole clusters can only ever contain
                # each distinct value in a multiple of 4.
                assert count % 4 == 0, (
                    f"value {value} appeared {count} times, not a multiple "
                    "of the cluster size 4 -- resample is not a union of "
                    "whole clusters"
                )

    def test_each_resample_draws_exactly_n_clusters(self):
        df = pd.DataFrame(
            {
                "cluster": [0, 0, 1, 1, 1, 2],
                "value": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            }
        )
        n_clusters = 3
        recorder = _RecordingRNG(np.random.default_rng(5))

        cluster_bootstrap(df, "cluster", lambda d: 0.0, n_resamples=7, rng=recorder)

        assert len(recorder.choice_sizes) == 7
        assert all(size == n_clusters for size in recorder.choice_sizes)

    def test_reproducible_with_same_seed(self):
        df = pd.DataFrame(
            {
                "cluster": [0, 0, 1, 1, 2, 2],
                "value": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            }
        )

        def statistic(resampled: pd.DataFrame) -> float:
            return float(resampled["value"].mean())

        samples_a = cluster_bootstrap(
            df, "cluster", statistic, n_resamples=50, rng=np.random.default_rng(7)
        )
        samples_b = cluster_bootstrap(
            df, "cluster", statistic, n_resamples=50, rng=np.random.default_rng(7)
        )
        assert np.array_equal(samples_a, samples_b)

    def test_cluster_bootstrap_wider_than_naive_row_bootstrap_when_between_cluster_variance_dominates(
        self,
    ):
        data_rng = np.random.default_rng(1)
        n_clusters = 20
        per_cluster = 20
        # Large between-cluster spread, tiny within-cluster noise: the
        # bootstrap's motivating scenario for this module (rows sharing a
        # frame_idx share an estimated board pose -- they vary together).
        cluster_means = data_rng.normal(0, 100, size=n_clusters)
        rows = []
        for cluster_id, mean in enumerate(cluster_means):
            values = mean + data_rng.normal(0, 1, size=per_cluster)
            for value in values:
                rows.append({"cluster": cluster_id, "value": value})
        df = pd.DataFrame(rows)

        def statistic(resampled: pd.DataFrame) -> float:
            return float(resampled["value"].mean())

        cluster_samples = cluster_bootstrap(
            df, "cluster", statistic, n_resamples=500, rng=np.random.default_rng(42)
        )
        cluster_low, cluster_high = percentile_ci(cluster_samples)

        naive_samples = _row_bootstrap(
            df, statistic, n_resamples=500, rng=np.random.default_rng(42)
        )
        naive_low, naive_high = percentile_ci(naive_samples)

        assert (cluster_high - cluster_low) > (naive_high - naive_low), (
            "cluster-bootstrap interval must be strictly wider than the "
            "naive per-row bootstrap when between-cluster variance "
            "dominates -- this is the plan's stated motivation for "
            "resampling frames, not rows"
        )


class TestReconstructionStatistics:
    def test_converts_metres_to_millimetres(self):
        df = pd.DataFrame({"signed_error_m": [0.001]})
        stats = reconstruction_statistics(df)
        assert stats["reconstruction_rmse_mm"] == pytest.approx(1.0)
        assert stats["reconstruction_mae_mm"] == pytest.approx(1.0)
        assert stats["signed_mean_mm"] == pytest.approx(1.0)

    def test_field_names_match_experiments_results_vocabulary(self):
        df = pd.DataFrame({"signed_error_m": [0.001, -0.002, 0.0005]})
        stats = reconstruction_statistics(df)
        assert set(stats) == {
            "reconstruction_rmse_mm",
            "reconstruction_mae_mm",
            "signed_mean_mm",
        }

    def test_mae_and_rmse_differ_on_mixed_signed_data(self):
        df = pd.DataFrame({"signed_error_m": [0.001, -0.003, 0.002]})
        stats = reconstruction_statistics(df)
        signed = np.array([0.001, -0.003, 0.002]) * 1000.0
        assert stats["reconstruction_rmse_mm"] == pytest.approx(
            float(np.sqrt(np.mean(signed**2)))
        )
        assert stats["reconstruction_mae_mm"] == pytest.approx(
            float(np.mean(np.abs(signed)))
        )
        assert stats["signed_mean_mm"] == pytest.approx(float(np.mean(signed)))


class TestPercentileCi:
    def test_low_strictly_less_than_high(self):
        rng = np.random.default_rng(3)
        samples = rng.normal(size=1000)
        low, high = percentile_ci(samples)
        assert low < high

    def test_symmetric_distribution_brackets_the_mean(self):
        rng = np.random.default_rng(3)
        samples = rng.normal(loc=5.0, size=5000)
        low, high = percentile_ci(samples)
        assert low < 5.0 < high


class TestResolveReconstructionErrorsPath:
    """DATA-01b moved `reconstruction_errors.csv` out of the repo and into the
    published Zenodo archive, so the script resolves it at call time.

    Every test here monkeypatches `load_example`. None may reach the network --
    the real archive is 4.35 GB.
    """

    @staticmethod
    def _forbid_download(monkeypatch):
        """Make any archive lookup fail loudly rather than download."""

        def _boom(*_args, **_kwargs):
            raise AssertionError("load_example must not be called in this test")

        monkeypatch.setattr("aquacal.datasets.load_example", _boom, raising=True)

    @staticmethod
    def _fake_archive(monkeypatch, cache_dir):
        class _Ds:
            cache_path = cache_dir

        monkeypatch.setattr(
            "aquacal.datasets.load_example", lambda *_a, **_k: _Ds(), raising=True
        )

    def test_explicit_path_wins(self, tmp_path, monkeypatch):
        self._forbid_download(monkeypatch)
        explicit = tmp_path / "mine.csv"
        explicit.write_text(_CSV)
        local = tmp_path / "local.csv"
        local.write_text(_CSV)
        monkeypatch.setattr(rb, "LOCAL_RECONSTRUCTION_ERRORS_PATH", local)

        assert resolve_reconstruction_errors_path(explicit) == explicit

    def test_explicit_path_that_does_not_exist_raises(self, tmp_path, monkeypatch):
        self._forbid_download(monkeypatch)

        with pytest.raises(FileNotFoundError, match="does not exist"):
            resolve_reconstruction_errors_path(tmp_path / "nope.csv")

    def test_local_file_wins_over_the_archive(self, tmp_path, monkeypatch):
        self._forbid_download(monkeypatch)
        local = tmp_path / "local.csv"
        local.write_text(_CSV)
        monkeypatch.setattr(rb, "LOCAL_RECONSTRUCTION_ERRORS_PATH", local)

        assert resolve_reconstruction_errors_path() == local

    def test_falls_back_to_the_published_archive(self, tmp_path, monkeypatch):
        cache = tmp_path / "cache"
        (cache / "reference_outputs").mkdir(parents=True)
        archived = cache / "reference_outputs" / "reconstruction_errors.csv"
        archived.write_text(_CSV)
        monkeypatch.setattr(
            rb, "LOCAL_RECONSTRUCTION_ERRORS_PATH", tmp_path / "absent.csv"
        )
        self._fake_archive(monkeypatch, cache)

        assert resolve_reconstruction_errors_path() == archived

    def test_missing_everywhere_names_all_three_locations(self, tmp_path, monkeypatch):
        cache = tmp_path / "cache"
        cache.mkdir()
        monkeypatch.setattr(
            rb, "LOCAL_RECONSTRUCTION_ERRORS_PATH", tmp_path / "absent.csv"
        )
        self._fake_archive(monkeypatch, cache)

        with pytest.raises(FileNotFoundError) as excinfo:
            resolve_reconstruction_errors_path()

        message = str(excinfo.value)
        assert "--reconstruction-errors" in message
        assert "absent.csv" in message
        assert "reference_outputs" in message

    def test_module_constants_are_paths_at_import(self):
        """Resolution must not run at import time -- importing this module must
        never trigger a multi-gigabyte download."""
        assert isinstance(rb.LOCAL_RECONSTRUCTION_ERRORS_PATH, Path)
        assert isinstance(rb.ARCHIVE_RECONSTRUCTION_ERRORS_RELPATH, Path)
