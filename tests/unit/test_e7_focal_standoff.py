"""Unit tests for `experiments.e7_focal_standoff_analysis` (COV-08, plan 19.5-03).

All tests build tiny hand-crafted DataFrames -- no file I/O, no calibration, no
dependence on the real `interface_ablation_band.csv`. Mirrors the pure-function
test shape of `tests/unit/test_seed_band_io.py`.
"""

from __future__ import annotations

import pandas as pd
import pytest

from experiments.e7_focal_standoff_analysis import (
    degeneracy_verdict,
    focal_standoff_association,
    paired_arm_difference,
)


def _make_frame(arm: str, seed_to_signed_slope: dict[int, float]) -> pd.DataFrame:
    """Build a frame for one arm where `focal_drift_pct` and `standoff_m` are
    perfectly (anti)correlated within each seed, sign given by
    `seed_to_signed_slope`'s value's sign."""
    rows = []
    for seed, slope in seed_to_signed_slope.items():
        for cam_idx in range(4):
            standoff = 1.0 + cam_idx * 0.1
            rows.append(
                {
                    "arm": arm,
                    "seed": seed,
                    "camera": f"cam{cam_idx}",
                    "standoff_m": standoff,
                    "focal_drift_pct": slope * standoff,
                }
            )
    return pd.DataFrame(rows)


class TestFocalStandoffAssociation:
    def test_all_negative_signs_gives_exact_sign_test_p_value(self):
        df = _make_frame(
            "shared_refined",
            {42: -1.0, 43: -2.0, 44: -0.5, 45: -3.0},
        )
        result = focal_standoff_association(df, "shared_refined")
        n_seeds = result["n_seeds"]
        assert n_seeds == 4
        assert result["n_seeds_negative"] == 4
        assert result["n_seeds_positive"] == 0
        assert result["p_one_sided"] == pytest.approx(2**-n_seeds)

    def test_mixed_signs_gives_p_above_threshold_and_no_signature_verdict(self):
        df = _make_frame(
            "percamera_refined",
            {42: -1.0, 43: 2.0, 44: -0.5, 45: 3.0},
        )
        result = focal_standoff_association(df, "percamera_refined")
        assert result["p_one_sided"] > 0.05
        assert degeneracy_verdict(result) != "signature_present"

    def test_single_seed_is_underpowered(self):
        df = _make_frame("shared_fixed", {42: -1.0})
        result = focal_standoff_association(df, "shared_fixed")
        assert result["n_seeds"] == 1
        assert degeneracy_verdict(result) == "underpowered"

    def test_zero_seeds_is_underpowered(self):
        df = _make_frame("shared_fixed", {42: -1.0})
        result = focal_standoff_association(df, "percamera_fixed")  # absent arm
        assert result["n_seeds"] == 0
        assert degeneracy_verdict(result) == "underpowered"

    def test_p_one_sided_field_present_and_named_unambiguously(self):
        df = _make_frame("shared_refined", {42: -1.0, 43: -1.0})
        result = focal_standoff_association(df, "shared_refined")
        assert "p_one_sided" in result
        assert "p_value" not in result


class TestDegeneracyVerdict:
    def test_significant_p_gives_signature_present(self):
        association = {"n_seeds": 10, "p_one_sided": 0.001}
        assert degeneracy_verdict(association) == "signature_present"

    def test_nonsignificant_p_gives_no_signature(self):
        association = {"n_seeds": 10, "p_one_sided": 0.5}
        assert degeneracy_verdict(association) == "no_signature"

    def test_boundary_exactly_alpha_is_no_signature(self):
        # Strictly less-than: p == alpha does not count as significant.
        association = {"n_seeds": 10, "p_one_sided": 0.05}
        assert degeneracy_verdict(association, alpha=0.05) == "no_signature"

    def test_nan_p_is_underpowered(self):
        association = {"n_seeds": 5, "p_one_sided": float("nan")}
        assert degeneracy_verdict(association) == "underpowered"


class TestPairedArmDifference:
    def test_paired_difference_matches_hand_computed_values(self):
        df = pd.concat(
            [
                pd.DataFrame(
                    {
                        "arm": ["shared_fixed"] * 2,
                        "seed": [42, 43],
                        "camera_height_drift_mm": [1.0, 2.0],
                    }
                ),
                pd.DataFrame(
                    {
                        "arm": ["percamera_fixed"] * 2,
                        "seed": [42, 43],
                        "camera_height_drift_mm": [1.5, 2.5],
                    }
                ),
            ],
            ignore_index=True,
        )
        result = paired_arm_difference(
            df, "shared_fixed", "percamera_fixed", "camera_height_drift_mm"
        )
        assert result["n_seeds"] == 2
        assert result["per_seed_diff"] == {
            42: pytest.approx(0.5),
            43: pytest.approx(0.5),
        }
        assert result["mean_diff"] == pytest.approx(0.5)

    def test_mismatched_seed_sets_raises(self):
        df = pd.concat(
            [
                pd.DataFrame({"arm": ["shared_fixed"], "seed": [42], "x": [1.0]}),
                pd.DataFrame({"arm": ["percamera_fixed"], "seed": [43], "x": [1.0]}),
            ],
            ignore_index=True,
        )
        with pytest.raises(ValueError, match="seeds"):
            paired_arm_difference(df, "shared_fixed", "percamera_fixed", "x")

    def test_missing_arm_raises(self):
        df = pd.DataFrame({"arm": ["shared_fixed"], "seed": [42], "x": [1.0]})
        with pytest.raises(ValueError, match="percamera_fixed"):
            paired_arm_difference(df, "shared_fixed", "percamera_fixed", "x")

    def test_never_returns_marginal_spread_keys(self):
        """T-19.5-03-01: the result dict must never carry a marginal-spread field."""
        df = pd.concat(
            [
                pd.DataFrame({"arm": ["a"], "seed": [42], "x": [1.0]}),
                pd.DataFrame({"arm": ["b"], "seed": [42], "x": [2.0]}),
            ],
            ignore_index=True,
        )
        result = paired_arm_difference(df, "a", "b", "x")
        assert "marginal_spread" not in result
        assert "marginal_range" not in result
