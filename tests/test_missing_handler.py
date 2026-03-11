"""Tests for data_wizard.core.missing_handler."""

import pytest
import pandas as pd
import numpy as np

from data_wizard.core.missing_handler import (
    get_missing_columns, get_applicable_strategies, apply_strategy, apply_strategies_bulk,
)


@pytest.fixture
def df_with_missing():
    return pd.DataFrame({
        "num": [1.0, 2.0, None, 4.0, None],
        "cat": ["a", None, "b", "a", None],
        "full": [1, 2, 3, 4, 5],
    })


class TestGetMissingColumns:
    def test_finds_columns_with_nulls(self, df_with_missing):
        result = get_missing_columns(df_with_missing)
        names = [r["name"] for r in result]
        assert "num" in names
        assert "cat" in names
        assert "full" not in names

    def test_missing_count(self, df_with_missing):
        result = get_missing_columns(df_with_missing)
        num_info = next(r for r in result if r["name"] == "num")
        assert num_info["missing"] == 2
        assert num_info["missing_pct"] == 40.0

    def test_no_missing(self):
        df = pd.DataFrame({"a": [1, 2, 3]})
        assert get_missing_columns(df) == []


class TestGetApplicableStrategies:
    def test_numeric_has_mean_median(self):
        strats = get_applicable_strategies("numeric")
        keys = [s["key"] for s in strats]
        assert "fill_mean" in keys
        assert "fill_median" in keys
        assert "interpolate" in keys

    def test_categorical_no_mean(self):
        strats = get_applicable_strategies("categorical")
        keys = [s["key"] for s in strats]
        assert "fill_mean" not in keys
        assert "fill_mode" in keys


class TestApplyStrategy:
    def test_drop_rows(self, df_with_missing):
        result = apply_strategy(df_with_missing, "num", "drop_rows")
        assert len(result) == 3
        assert result["num"].isna().sum() == 0

    def test_fill_mean(self, df_with_missing):
        result = apply_strategy(df_with_missing, "num", "fill_mean")
        assert result["num"].isna().sum() == 0
        # Mean of [1, 2, 4] = 2.333...
        assert abs(result["num"].iloc[2] - 2.333) < 0.01

    def test_fill_median(self, df_with_missing):
        result = apply_strategy(df_with_missing, "num", "fill_median")
        assert result["num"].isna().sum() == 0
        assert result["num"].iloc[2] == 2.0

    def test_fill_mode(self, df_with_missing):
        result = apply_strategy(df_with_missing, "cat", "fill_mode")
        assert result["cat"].isna().sum() == 0
        assert result["cat"].iloc[1] == "a"

    def test_fill_custom(self, df_with_missing):
        result = apply_strategy(df_with_missing, "num", "fill_custom", custom_value=99)
        assert result["num"].iloc[2] == 99
        assert result["num"].iloc[4] == 99

    def test_forward_fill(self, df_with_missing):
        result = apply_strategy(df_with_missing, "num", "fill_forward")
        assert result["num"].iloc[2] == 2.0

    def test_backward_fill(self, df_with_missing):
        result = apply_strategy(df_with_missing, "num", "fill_backward")
        assert result["num"].iloc[2] == 4.0

    def test_interpolate(self, df_with_missing):
        result = apply_strategy(df_with_missing, "num", "interpolate")
        assert result["num"].isna().sum() == 0

    def test_leave(self, df_with_missing):
        result = apply_strategy(df_with_missing, "num", "leave")
        assert result["num"].isna().sum() == 2

    def test_does_not_modify_original(self, df_with_missing):
        _ = apply_strategy(df_with_missing, "num", "fill_mean")
        assert df_with_missing["num"].isna().sum() == 2


class TestApplyStrategiesBulk:
    def test_bulk_apply(self, df_with_missing):
        strategies = {
            "num": {"strategy": "fill_mean"},
            "cat": {"strategy": "fill_mode"},
        }
        result = apply_strategies_bulk(df_with_missing, strategies)
        assert result["num"].isna().sum() == 0
        assert result["cat"].isna().sum() == 0

    def test_bulk_with_leave(self, df_with_missing):
        strategies = {
            "num": {"strategy": "leave"},
        }
        result = apply_strategies_bulk(df_with_missing, strategies)
        assert result["num"].isna().sum() == 2
