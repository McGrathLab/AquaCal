"""Unit tests for `experiments._io.parse_seed_list` / `run_seed_band` (D-19.4-14).

These are the shared band-mechanism primitives E7's `--seeds` mode is built
on. All tests are fast: no calibration, no scenario construction, no I/O.
"""

from __future__ import annotations

import pandas as pd
import pytest

from experiments._io import (
    build_experiment_arg_parser,
    parse_seed_list,
    run_seed_band,
)


class TestParseSeedList:
    def test_multiple_seeds(self):
        assert parse_seed_list("42,43,44") == [42, 43, 44]

    def test_single_seed(self):
        assert parse_seed_list("42") == [42]

    def test_whitespace_tolerated(self):
        assert parse_seed_list(" 42 , 43 ") == [42, 43]

    def test_duplicate_seed_raises_naming_the_duplicate(self):
        with pytest.raises(ValueError, match="42"):
            parse_seed_list("42,42")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            parse_seed_list("")

    def test_trailing_comma_raises(self):
        with pytest.raises(ValueError, match="42,"):
            parse_seed_list("42,")

    def test_non_integer_token_raises_naming_the_token(self):
        with pytest.raises(ValueError, match="a"):
            parse_seed_list("a,b")


class TestRunSeedBand:
    def test_calls_runner_once_per_seed_in_order(self):
        calls: list[int] = []

        def runner(seed: int) -> pd.DataFrame:
            calls.append(seed)
            return pd.DataFrame({"value": [seed * 10]})

        run_seed_band(runner, [42, 43, 44])
        assert calls == [42, 43, 44]

    def test_concatenates_rows_with_seed_column(self):
        def runner(seed: int) -> pd.DataFrame:
            return pd.DataFrame({"camera": ["cam0", "cam1"], "value": [seed, seed]})

        result = run_seed_band(runner, [42, 43])
        assert list(result["seed"]) == [42, 42, 43, 43]
        assert len(result) == 4

    def test_seed_column_added_when_runner_omits_it(self):
        def runner(seed: int) -> pd.DataFrame:
            return pd.DataFrame({"x": [1, 2]})

        result = run_seed_band(runner, [7])
        assert "seed" in result.columns
        assert list(result["seed"]) == [7, 7]

    def test_seed_column_overwritten_when_runner_supplies_it(self):
        def runner(seed: int) -> pd.DataFrame:
            # A runner-supplied seed column (e.g. a stale default) must be
            # overwritten with the actual seed run_seed_band is iterating.
            return pd.DataFrame({"x": [1], "seed": [-1]})

        result = run_seed_band(runner, [7])
        assert list(result["seed"]) == [7]

    def test_propagates_runner_exception_immediately(self):
        def runner(seed: int) -> pd.DataFrame:
            if seed == 43:
                raise RuntimeError("boom")
            return pd.DataFrame({"x": [seed]})

        with pytest.raises(RuntimeError, match="boom"):
            run_seed_band(runner, [42, 43, 44])


def test_shared_five_flag_contract_unchanged():
    """The shared parser must still expose exactly five flags -- `--seeds`
    is a script-local addition, not a widening of this shared contract."""
    parser = build_experiment_arg_parser()
    options = sorted(a.option_strings[0] for a in parser._actions if a.option_strings)
    assert options == ["--check", "--force", "--out", "--seed", "--smoke"]
