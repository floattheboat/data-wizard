"""Machine learning model training and evaluation."""

import numpy as np
import pandas as pd

from data_wizard.utils.type_detection import classify_column

# Algorithm registry: task_type -> {display_name: sklearn_class_path}
ALGORITHMS = {
    "classification": {
        "Logistic Regression": "sklearn.linear_model.LogisticRegression",
        "Random Forest": "sklearn.ensemble.RandomForestClassifier",
        "Gradient Boosting": "sklearn.ensemble.GradientBoostingClassifier",
        "KNN": "sklearn.neighbors.KNeighborsClassifier",
        "Decision Tree": "sklearn.tree.DecisionTreeClassifier",
        "SVM": "sklearn.svm.SVC",
    },
    "regression": {
        "Linear Regression": "sklearn.linear_model.LinearRegression",
        "Random Forest": "sklearn.ensemble.RandomForestRegressor",
        "Gradient Boosting": "sklearn.ensemble.GradientBoostingRegressor",
        "KNN": "sklearn.neighbors.KNeighborsRegressor",
        "Decision Tree": "sklearn.tree.DecisionTreeRegressor",
        "Ridge": "sklearn.linear_model.Ridge",
    },
}

# Sensible defaults per algorithm
_DEFAULTS = {
    "LogisticRegression": {"max_iter": 1000, "random_state": 42},
    "RandomForestClassifier": {"n_estimators": 100, "random_state": 42},
    "GradientBoostingClassifier": {"n_estimators": 100, "random_state": 42},
    "KNeighborsClassifier": {},
    "DecisionTreeClassifier": {"random_state": 42},
    "SVC": {"random_state": 42},
    "LinearRegression": {},
    "RandomForestRegressor": {"n_estimators": 100, "random_state": 42},
    "GradientBoostingRegressor": {"n_estimators": 100, "random_state": 42},
    "KNeighborsRegressor": {},
    "DecisionTreeRegressor": {"random_state": 42},
    "Ridge": {"random_state": 42},
}


def infer_task_type(series: pd.Series) -> str:
    """Infer whether target column is a classification or regression task."""
    col_type = classify_column(series)
    if col_type == "numeric" and series.nunique() > 20:
        return "regression"
    return "classification"


def get_algorithms(task_type: str) -> list[str]:
    """Return list of algorithm display names for the given task type."""
    return list(ALGORITHMS.get(task_type, {}).keys())


def prepare_features(df: pd.DataFrame, target_col: str) -> tuple:
    """Separate features/target, encode categoricals, drop unusable columns.

    Returns (X, y, info_dict) where info_dict has keys:
        n_features, rows_dropped, target_encoded (bool)
    """
    work = df.copy()
    y = work.pop(target_col)

    # Drop datetime and text columns from features
    drop_cols = []
    for col in work.columns:
        ctype = classify_column(work[col])
        if ctype in ("datetime", "text"):
            drop_cols.append(col)
    work = work.drop(columns=drop_cols)

    # One-hot encode categorical features
    work = pd.get_dummies(work, drop_first=True)

    # Label-encode categorical target
    target_encoded = False
    if classify_column(y) in ("categorical", "text", "boolean"):
        from sklearn.preprocessing import LabelEncoder
        le = LabelEncoder()
        y = pd.Series(le.fit_transform(y.astype(str)), index=y.index, name=target_col)
        target_encoded = True

    # Combine and drop rows with NaN
    combined = work.copy()
    combined["__target__"] = y
    before_rows = len(combined)
    combined = combined.dropna()
    rows_dropped = before_rows - len(combined)

    y = combined.pop("__target__")
    X = combined

    info = {
        "n_features": X.shape[1],
        "rows_dropped": rows_dropped,
        "target_encoded": target_encoded,
    }
    return X, y, info


def train_model(
    df: pd.DataFrame,
    target_col: str,
    algorithm_name: str,
    task_type: str,
    test_size: float = 0.2,
) -> dict:
    """Train a model and return results dict.

    All sklearn imports are lazy to keep app startup fast.
    """
    try:
        from importlib import import_module
        from sklearn.model_selection import train_test_split

        # Prepare data
        X, y, prep_info = prepare_features(df, target_col)

        if len(X) < 10:
            return {"error": "Not enough data rows after preprocessing (need at least 10)."}

        # Stratify for classification
        stratify = y if task_type == "classification" else None
        try:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=42, stratify=stratify,
            )
        except ValueError:
            # Stratification can fail with very small classes
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=42,
            )

        # Instantiate algorithm
        class_path = ALGORITHMS[task_type][algorithm_name]
        module_path, class_name = class_path.rsplit(".", 1)
        module = import_module(module_path)
        cls = getattr(module, class_name)
        params = _DEFAULTS.get(class_name, {})
        model = cls(**params)

        # Fit and predict
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        # Compute metrics
        if task_type == "classification":
            from sklearn.metrics import (
                accuracy_score, balanced_accuracy_score,
                precision_score, recall_score, f1_score, log_loss,
            )
            metrics = {
                "accuracy": round(accuracy_score(y_test, y_pred), 4),
                "balanced_accuracy": round(balanced_accuracy_score(y_test, y_pred), 4),
                "precision": round(precision_score(y_test, y_pred, average="weighted", zero_division=0), 4),
                "recall": round(recall_score(y_test, y_pred, average="weighted", zero_division=0), 4),
                "f1": round(f1_score(y_test, y_pred, average="weighted", zero_division=0), 4),
            }
            try:
                y_proba = model.predict_proba(X_test)
                metrics["log_loss"] = round(log_loss(y_test, y_proba), 4)
            except AttributeError:
                metrics["log_loss"] = "N/A"
        else:
            from sklearn.metrics import (
                r2_score, mean_absolute_error, mean_squared_error,
                mean_absolute_percentage_error, max_error,
            )
            metrics = {
                "r2": round(r2_score(y_test, y_pred), 4),
                "mae": round(mean_absolute_error(y_test, y_pred), 4),
                "rmse": round(np.sqrt(mean_squared_error(y_test, y_pred)), 4),
                "mse": round(mean_squared_error(y_test, y_pred), 4),
                "max_error": round(max_error(y_test, y_pred), 4),
            }
            try:
                metrics["mape"] = round(mean_absolute_percentage_error(y_test, y_pred), 4)
            except Exception:
                metrics["mape"] = "N/A"

        # Feature importances
        feature_importances = None
        if hasattr(model, "feature_importances_"):
            importances = model.feature_importances_
            fi = sorted(
                zip(X.columns, importances), key=lambda x: abs(x[1]), reverse=True,
            )
            feature_importances = [(name, round(float(imp), 4)) for name, imp in fi]
        elif hasattr(model, "coef_"):
            coefs = model.coef_
            if coefs.ndim > 1:
                coefs = np.mean(np.abs(coefs), axis=0)
            else:
                coefs = np.abs(coefs)
            fi = sorted(
                zip(X.columns, coefs), key=lambda x: abs(x[1]), reverse=True,
            )
            feature_importances = [(name, round(float(imp), 4)) for name, imp in fi]

        return {
            "task_type": task_type,
            "algorithm": algorithm_name,
            "target_column": target_col,
            "n_features": prep_info["n_features"],
            "n_train": len(X_train),
            "n_test": len(X_test),
            "rows_dropped": prep_info["rows_dropped"],
            "metrics": metrics,
            "feature_importances": feature_importances,
            "error": None,
        }

    except Exception as e:
        return {"error": str(e)}
