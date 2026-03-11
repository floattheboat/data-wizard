"""Tests for data_wizard.core.analyzer."""

import pytest
import pandas as pd
import numpy as np

from data_wizard.core.analyzer import analyze_column, analyze_dataframe, compute_correlation


@pytest.fixture
def mixed_df():
    return pd.DataFrame({
        "num": [1, 2, 3, 4, 5, None],
        "cat": ["a", "b", "a", "b", "a", "c"],
        "dt": pd.to_datetime(["2023-01-01", "2023-06-01", "2023-12-01", None, "2024-01-01", "2024-06-01"]),
        "text": ["hello world", "foo bar", "test string", "another one", "something", None],
        "bool_col": [True, False, True, False, True, None],
    })


class TestAnalyzeColumn:
    def test_numeric_column(self, mixed_df):
        stats = analyze_column(mixed_df["num"])
        assert stats["inferred_type"] == "numeric"
        assert stats["missing"] == 1
        assert stats["missing_pct"] > 0
        assert "mean" in stats
        assert "std" in stats
        assert "min" in stats
        assert "max" in stats

    def test_categorical_column(self, mixed_df):
        stats = analyze_column(mixed_df["cat"])
        assert stats["inferred_type"] == "categorical"
        assert "top_values" in stats

    def test_datetime_column(self, mixed_df):
        stats = analyze_column(mixed_df["dt"])
        assert stats["inferred_type"] == "datetime"
        assert "min_date" in stats
        assert "max_date" in stats

    def test_empty_column(self):
        s = pd.Series([None, None, None], name="empty")
        stats = analyze_column(s)
        assert stats["inferred_type"] == "empty"
        assert stats["missing"] == 3

    def test_all_present(self):
        s = pd.Series([1, 2, 3], name="full")
        stats = analyze_column(s)
        assert stats["missing"] == 0
        assert stats["missing_pct"] == 0


class TestAnalyzeDataframe:
    def test_returns_columns_and_overview(self, mixed_df):
        result = analyze_dataframe(mixed_df)
        assert "columns" in result
        assert "overview" in result
        assert len(result["columns"]) == 5
        assert result["overview"]["rows"] == 6
        assert result["overview"]["cols"] == 5

    def test_overview_missing_count(self, mixed_df):
        result = analyze_dataframe(mixed_df)
        assert result["overview"]["total_missing"] > 0

    def test_memory_usage(self, mixed_df):
        result = analyze_dataframe(mixed_df)
        assert result["overview"]["memory_mb"] >= 0


class TestComputeCorrelation:
    def test_correlation_matrix(self):
        df = pd.DataFrame({"a": [1, 2, 3, 4], "b": [2, 4, 6, 8], "c": [10, 20, 30, 40]})
        corr = compute_correlation(df)
        assert corr is not None
        assert corr.shape == (3, 3)
        assert abs(corr.loc["a", "b"] - 1.0) < 0.01

    def test_no_numeric_columns(self):
        df = pd.DataFrame({"a": ["x", "y"], "b": ["1", "2"]})
        corr = compute_correlation(df)
        assert corr is None

    def test_single_numeric_column(self):
        df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        corr = compute_correlation(df)
        assert corr is None
