"""Unit tests for `experiments.e7_focal_standoff_analysis` (COV-08, plan 19.5-03).

All tests build tiny hand-crafted DataFrames -- no file I/O, no calibration, no
dependence on the real `interface_ablation_band.csv`. Mirrors the pure-function
test shape of `tests/unit/test_seed_band_io.py`.
"""

from __future__ import annotations

import pandas as pd
import pytest

from experiments.e7_focal_standoff_analysis import (
    ARMS,
    SCOPE_TEXT,
    build_focal_standoff_df,
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

    def test_constant_focal_drift_counts_seeds_but_gives_vacuous_verdict(self):
        """A `fixed` arm never refines intrinsics, so `focal_drift_pct` is
        identically 0 within every seed -- correlation is undefined (0/0),
        not merely small. `n_seeds` must still count the seeds actually
        present (they are real, committed band rows). FIX-04 (23-03):
        because the correlation is UNDEFINED (not measured-and-zero), the
        verdict is now `"vacuous_by_construction"`, distinct from
        `"no_signature"` (a measured null) -- see
        `TestDegeneracyVerdict.test_vacuous_by_construction_*` for the
        distinguishing cases."""
        rows = []
        for seed in (42, 43, 44):
            for cam_idx in range(4):
                rows.append(
                    {
                        "arm": "shared_fixed",
                        "seed": seed,
                        "camera": f"cam{cam_idx}",
                        "standoff_m": 1.0 + cam_idx * 0.1,
                        "focal_drift_pct": 0.0,
                    }
                )
        df = pd.DataFrame(rows)
        result = focal_standoff_association(df, "shared_fixed")
        assert result["n_seeds"] == 3
        assert result["n_seeds_negative"] == 0
        assert result["n_seeds_positive"] == 0
        assert result["p_one_sided"] == pytest.approx(1.0)
        assert degeneracy_verdict(result) == "vacuous_by_construction"


class TestDegeneracyVerdict:
    def test_significant_p_gives_signature_present(self):
        # n_seeds_negative/positive nonzero and mean_within_seed_correlation
        # defined -- FIX-04's vacuous branch must not trigger.
        association = {
            "n_seeds": 10,
            "n_seeds_negative": 10,
            "n_seeds_positive": 0,
            "mean_within_seed_correlation": -0.9,
            "p_one_sided": 0.001,
        }
        assert degeneracy_verdict(association) == "signature_present"

    def test_nonsignificant_p_gives_no_signature(self):
        association = {
            "n_seeds": 10,
            "n_seeds_negative": 6,
            "n_seeds_positive": 4,
            "mean_within_seed_correlation": -0.1,
            "p_one_sided": 0.5,
        }
        assert degeneracy_verdict(association) == "no_signature"

    def test_boundary_exactly_alpha_is_no_signature(self):
        # Strictly less-than: p == alpha does not count as significant.
        association = {
            "n_seeds": 10,
            "n_seeds_negative": 8,
            "n_seeds_positive": 2,
            "mean_within_seed_correlation": -0.3,
            "p_one_sided": 0.05,
        }
        assert degeneracy_verdict(association, alpha=0.05) == "no_signature"

    def test_nan_p_is_underpowered(self):
        association = {
            "n_seeds": 5,
            "n_seeds_negative": 2,
            "n_seeds_positive": 1,
            "mean_within_seed_correlation": -0.2,
            "p_one_sided": float("nan"),
        }
        assert degeneracy_verdict(association) == "underpowered"

    def test_vacuous_by_construction_matches_committed_fixed_rows_shape(self):
        """FIX-04 (23-03): the committed `fixed` rows' exact shape --
        n_seeds=10, zero signs, undefined correlation, p_one_sided falls
        through to 1.0 -- classifies as vacuous_by_construction, not
        no_signature."""
        association = {
            "n_seeds": 10,
            "n_seeds_negative": 0,
            "n_seeds_positive": 0,
            "mean_within_seed_correlation": float("nan"),
            "p_one_sided": 1.0,
        }
        assert degeneracy_verdict(association) == "vacuous_by_construction"

    def test_zero_signs_with_defined_correlation_is_no_signature_not_vacuous(self):
        """A genuinely null result with a DEFINED correlation and zero signs
        must still classify as no_signature -- the vacuous branch cannot
        swallow a real null (all three conditions are required)."""
        association = {
            "n_seeds": 10,
            "n_seeds_negative": 0,
            "n_seeds_positive": 0,
            "mean_within_seed_correlation": 0.0,
            "p_one_sided": 1.0,
        }
        assert degeneracy_verdict(association) == "no_signature"

    def test_single_seed_is_underpowered_ahead_of_vacuous_branch(self):
        association = {
            "n_seeds": 1,
            "n_seeds_negative": 0,
            "n_seeds_positive": 0,
            "mean_within_seed_correlation": float("nan"),
            "p_one_sided": 1.0,
        }
        assert degeneracy_verdict(association) == "underpowered"


class TestBuildFocalStandoffDf:
    def _hand_built_band_df(self) -> pd.DataFrame:
        """A small `interface_ablation_band.csv`-shaped frame: the two
        `fixed` arms have focal_drift_pct == 0.0 for every camera and seed
        (undefined correlation); the two `refined` arms carry a real,
        perfectly-negative correlation across two seeds (measured
        signature_present)."""
        rows = []
        for arm in ARMS:
            is_fixed = arm.endswith("_fixed")
            for seed in (42, 43):
                for cam_idx in range(3):
                    standoff = 1.0 + cam_idx * 0.1
                    focal_drift = 0.0 if is_fixed else -1.0 * standoff
                    rows.append(
                        {
                            "arm": arm,
                            "seed": seed,
                            "camera": f"cam{cam_idx}",
                            "standoff_m": standoff,
                            "focal_drift_pct": focal_drift,
                        }
                    )
        return pd.DataFrame(rows)

    def test_fixed_rows_carry_vacuous_verdict_and_scope_reason(self):
        df = self._hand_built_band_df()
        result = build_focal_standoff_df(df)
        fixed_rows = result[result["arm"].isin(["shared_fixed", "percamera_fixed"])]
        assert len(fixed_rows) == 2
        assert (fixed_rows["verdict"] == "vacuous_by_construction").all()
        assert fixed_rows["scope"].str.contains("VACUOUS BY CONSTRUCTION").all()

    def test_refined_rows_keep_measured_verdict_and_unmodified_scope(self):
        """The refined arms carry a real, defined correlation (perfectly
        negative at 2 seeds -- too few for signature_present at alpha=0.05,
        but definitively NOT vacuous_by_construction), and their scope is
        untouched (no VACUOUS suffix)."""
        df = self._hand_built_band_df()
        result = build_focal_standoff_df(df)
        refined_rows = result[
            result["arm"].isin(["shared_refined", "percamera_refined"])
        ]
        assert len(refined_rows) == 2
        assert (refined_rows["verdict"] != "vacuous_by_construction").all()
        assert (refined_rows["mean_within_seed_correlation"].notna()).all()
        assert (refined_rows["scope"] == SCOPE_TEXT).all()

    def test_original_column_set_and_order_unchanged(self):
        """The nine original columns keep their names AND their positions.

        Re-anchored (plan 24-02) from an exact whole-header equality: the six
        degeneracy columns are APPENDED, so `== [...nine...]` necessarily
        fails while the property the test exists to protect -- that no
        pre-existing column was renamed, reordered or dropped -- still holds.
        Asserting the prefix keeps that property and adds the append-only
        constraint, rather than deleting the check.
        """
        df = self._hand_built_band_df()
        result = build_focal_standoff_df(df)
        assert list(result.columns)[:9] == [
            "arm",
            "n_seeds",
            "n_cameras_per_seed",
            "mean_within_seed_correlation",
            "n_seeds_negative",
            "n_seeds_positive",
            "p_one_sided",
            "verdict",
            "scope",
        ]
        assert list(result.columns)[9:] == [
            "degenerate_observations_at_solution",
            "degenerate_observations_cause_above_interface",
            "degenerate_observations_cause_behind_camera",
            "degenerate_observations_cause_interface_below_camera",
            "degenerate_observations_fate_extended",
            "degenerate_observations_fate_penalized",
        ]

    def test_band_without_degeneracy_columns_yields_none_not_zero(self):
        """A band CSV regenerated before plan 24-02 has none of the six
        columns. The output must then say "never measured" (`None`), never
        "measured and found clean" (`0`) -- collapsing the two would let a
        pre-instrumentation artifact read as a verified-clean one."""
        df = self._hand_built_band_df()
        assert "degenerate_observations_at_solution" not in df.columns
        result = build_focal_standoff_df(df)
        for column in list(result.columns)[9:]:
            assert result[column].isna().all()


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
