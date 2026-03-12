"""Tests for the ML runner module."""

import numpy as np
import pandas as pd
import pytest

from data_wizard.core.ml_runner import (
    ALGORITHMS,
    infer_task_type,
    get_algorithms,
    prepare_features,
    train_model,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def classification_df():
    """DataFrame suitable for classification."""
    rng = np.random.RandomState(42)
    n = 100
    return pd.DataFrame({
        "feat_a": rng.randn(n),
        "feat_b": rng.randn(n),
        "cat_feat": rng.choice(["x", "y", "z"], n),
        "target": rng.choice(["cat", "dog"], n),
    })


@pytest.fixture
def regression_df():
    """DataFrame suitable for regression."""
    rng = np.random.RandomState(42)
    n = 100
    x1 = rng.randn(n)
    x2 = rng.randn(n)
    return pd.DataFrame({
        "feat_a": x1,
        "feat_b": x2,
        "target": x1 * 2.5 + x2 * -1.3 + rng.randn(n) * 0.1,
    })


@pytest.fixture
def df_with_datetime():
    """DataFrame with a datetime column that should be dropped."""
    rng = np.random.RandomState(42)
    n = 50
    return pd.DataFrame({
        "feat_a": rng.randn(n),
        "date_col": pd.date_range("2020-01-01", periods=n),
        "target": rng.choice(["a", "b"], n),
    })


@pytest.fixture
def df_with_nans():
    """DataFrame with NaN values."""
    return pd.DataFrame({
        "feat_a": [1.0, 2.0, np.nan, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0,
                    11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0, 20.0],
        "feat_b": [10.0, np.nan, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0,
                    110.0, 120.0, 130.0, 140.0, 150.0, 160.0, 170.0, 180.0, 190.0, 200.0],
        "target": ["a", "a", "b", "a", "b", "a", "b", "a", "b", "a",
                    "a", "b", "a", "b", "a", "b", "a", "b", "a", "b"],
    })


# ---------------------------------------------------------------------------
# TestInferTaskType
# ---------------------------------------------------------------------------

class TestInferTaskType:
    def test_numeric_high_cardinality_is_regression(self):
        series = pd.Series(np.random.randn(100))
        assert infer_task_type(series) == "regression"

    def test_categorical_is_classification(self):
        series = pd.Series(["cat", "dog", "cat", "dog"] * 25)
        assert infer_task_type(series) == "classification"

    def test_boolean_is_classification(self):
        series = pd.Series([True, False, True, False] * 25, dtype=bool)
        assert infer_task_type(series) == "classification"

    def test_numeric_low_cardinality_is_classification(self):
        series = pd.Series([0, 1, 2, 0, 1, 2] * 10)
        assert infer_task_type(series) == "classification"


# ---------------------------------------------------------------------------
# TestGetAlgorithms
# ---------------------------------------------------------------------------

class TestGetAlgorithms:
    def test_classification_algorithms(self):
        algos = get_algorithms("classification")
        assert len(algos) == 6
        assert "Logistic Regression" in algos
        assert "Random Forest" in algos

    def test_regression_algorithms(self):
        algos = get_algorithms("regression")
        assert len(algos) == 6
        assert "Linear Regression" in algos
        assert "Ridge" in algos

    def test_unknown_task_type_returns_empty(self):
        assert get_algorithms("unknown") == []


# ---------------------------------------------------------------------------
# TestPrepareFeatures
# ---------------------------------------------------------------------------

class TestPrepareFeatures:
    def test_separates_target(self, classification_df):
        X, y, info = prepare_features(classification_df, "target")
        assert "target" not in X.columns
        assert len(y) == len(X)

    def test_encodes_categoricals(self, classification_df):
        X, y, info = prepare_features(classification_df, "target")
        # cat_feat was one-hot encoded (drop_first means 2 dummies for 3 categories)
        assert any("cat_feat" in col for col in X.columns)

    def test_drops_datetime_columns(self, df_with_datetime):
        X, y, info = prepare_features(df_with_datetime, "target")
        assert not any("date" in col.lower() for col in X.columns)

    def test_handles_nan_rows(self, df_with_nans):
        X, y, info = prepare_features(df_with_nans, "target")
        assert info["rows_dropped"] == 2  # two rows had NaN
        assert len(X) == 18


# ---------------------------------------------------------------------------
# TestTrainModel
# ---------------------------------------------------------------------------

class TestTrainModel:
    def test_classification_returns_correct_metrics(self, classification_df):
        results = train_model(classification_df, "target", "Logistic Regression", "classification")
        assert results["error"] is None
        metrics = results["metrics"]
        assert "accuracy" in metrics
        assert "precision" in metrics
        assert "recall" in metrics
        assert "f1" in metrics
        assert all(0 <= v <= 1 for v in metrics.values())

    def test_regression_returns_correct_metrics(self, regression_df):
        results = train_model(regression_df, "target", "Linear Regression", "regression")
        assert results["error"] is None
        metrics = results["metrics"]
        assert "r2" in metrics
        assert "mae" in metrics
        assert "rmse" in metrics

    def test_tree_models_return_feature_importances(self, classification_df):
        results = train_model(classification_df, "target", "Random Forest", "classification")
        assert results["error"] is None
        assert results["feature_importances"] is not None
        assert len(results["feature_importances"]) > 0
        # Each entry is (name, importance)
        name, imp = results["feature_importances"][0]
        assert isinstance(name, str)
        assert isinstance(imp, float)

    def test_invalid_target_returns_error(self, classification_df):
        results = train_model(classification_df, "nonexistent_col", "Logistic Regression", "classification")
        assert results["error"] is not None

    def test_input_dataframe_not_modified(self, classification_df):
        original = classification_df.copy()
        train_model(classification_df, "target", "Logistic Regression", "classification")
        pd.testing.assert_frame_equal(classification_df, original)

    @pytest.mark.parametrize("algo_name", list(ALGORITHMS["classification"].keys()))
    def test_all_classification_algorithms_run(self, classification_df, algo_name):
        results = train_model(classification_df, "target", algo_name, "classification")
        assert results["error"] is None, f"{algo_name} failed: {results['error']}"

    @pytest.mark.parametrize("algo_name", list(ALGORITHMS["regression"].keys()))
    def test_all_regression_algorithms_run(self, regression_df, algo_name):
        results = train_model(regression_df, "target", algo_name, "regression")
        assert results["error"] is None, f"{algo_name} failed: {results['error']}"
