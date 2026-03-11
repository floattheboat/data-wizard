"""Tests for data_wizard.core.outlier_detector."""

import pytest
import pandas as pd
import numpy as np

from data_wizard.core.outlier_detector import (
    detect_outliers_iqr, detect_outliers_zscore,
    get_outlier_info, apply_remediation, apply_remediations_bulk,
)


@pytest.fixture
def df_with_outliers():
    np.random.seed(42)
    normal = np.random.normal(50, 10, 100).tolist()
    outliers = [200, -100, 300]
    return pd.DataFrame({
        "values": normal + outliers,
        "clean": list(range(103)),
        "cat": ["a"] * 103,
    })


class TestDetectOutliersIQR:
    def test_detects_extreme_values(self, df_with_outliers):
        mask = detect_outliers_iqr(df_with_outliers["values"])
        assert mask.sum() >= 3  # At least the injected outliers

    def test_no_outliers_in_uniform_data(self):
        s = pd.Series(range(100))
        mask = detect_outliers_iqr(s)
        assert mask.sum() == 0

    def test_stricter_threshold(self, df_with_outliers):
        mask_loose = detect_outliers_iqr(df_with_outliers["values"], multiplier=3.0)
        mask_strict = detect_outliers_iqr(df_with_outliers["values"], multiplier=1.0)
        assert mask_strict.sum() >= mask_loose.sum()


class TestDetectOutliersZscore:
    def test_detects_extreme_values(self, df_with_outliers):
        mask = detect_outliers_zscore(df_with_outliers["values"])
        assert mask.sum() >= 3

    def test_handles_zero_std(self):
        s = pd.Series([5, 5, 5, 5])
        mask = detect_outliers_zscore(s)
        assert mask.sum() == 0


class TestGetOutlierInfo:
    def test_returns_info_for_numeric_cols(self, df_with_outliers):
        info = get_outlier_info(df_with_outliers, method="iqr")
        names = [i["name"] for i in info]
        assert "values" in names
        # "clean" is uniform, probably no outliers; "cat" is not numeric

    def test_has_required_fields(self, df_with_outliers):
        info = get_outlier_info(df_with_outliers, method="iqr")
        for item in info:
            assert "name" in item
            assert "outlier_count" in item
            assert "outlier_pct" in item
            assert "lower_bound" in item
            assert "upper_bound" in item

    def test_zscore_method(self, df_with_outliers):
        info = get_outlier_info(df_with_outliers, method="zscore", threshold=3.0)
        assert len(info) > 0


class TestApplyRemediation:
    def test_remove(self, df_with_outliers):
        original_len = len(df_with_outliers)
        result = apply_remediation(df_with_outliers, "values", "remove", method="iqr")
        assert len(result) < original_len

    def test_cap(self, df_with_outliers):
        result = apply_remediation(df_with_outliers, "values", "cap", method="iqr")
        assert len(result) == len(df_with_outliers)
        # No values should exceed bounds after capping
        q1 = result["values"].quantile(0.25)
        q3 = result["values"].quantile(0.75)
        iqr = q3 - q1
        assert result["values"].max() <= q3 + 1.5 * iqr + 0.01
        assert result["values"].min() >= q1 - 1.5 * iqr - 0.01

    def test_log_transform(self, df_with_outliers):
        result = apply_remediation(df_with_outliers, "values", "log", method="iqr")
        assert len(result) == len(df_with_outliers)

    def test_leave(self, df_with_outliers):
        result = apply_remediation(df_with_outliers, "values", "leave")
        assert result["values"].equals(df_with_outliers["values"])

    def test_does_not_modify_original(self, df_with_outliers):
        original = df_with_outliers.copy()
        _ = apply_remediation(df_with_outliers, "values", "remove", method="iqr")
        assert len(df_with_outliers) == len(original)


class TestApplyRemediationsBulk:
    def test_bulk_apply(self, df_with_outliers):
        remediations = {
            "values": {"strategy": "cap", "method": "iqr", "threshold": 1.5},
        }
        result = apply_remediations_bulk(df_with_outliers, remediations)
        assert len(result) == len(df_with_outliers)
