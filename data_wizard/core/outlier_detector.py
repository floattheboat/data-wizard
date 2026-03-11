"""Outlier detection (IQR / Z-score) and remediation."""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from scipy import stats as scipy_stats

from data_wizard.utils.constants import IQR_MULTIPLIER, ZSCORE_THRESHOLD


def detect_outliers_iqr(
    series: pd.Series, multiplier: float = IQR_MULTIPLIER
) -> pd.Series:
    """Return boolean mask of outlier positions using IQR method."""
    numeric = pd.to_numeric(series, errors="coerce")
    q1 = numeric.quantile(0.25)
    q3 = numeric.quantile(0.75)
    iqr = q3 - q1
    lower = q1 - multiplier * iqr
    upper = q3 + multiplier * iqr
    return (numeric < lower) | (numeric > upper)


def detect_outliers_zscore(
    series: pd.Series, threshold: float = ZSCORE_THRESHOLD
) -> pd.Series:
    """Return boolean mask of outlier positions using Z-score method."""
    numeric = pd.to_numeric(series, errors="coerce")
    clean = numeric.dropna()
    if len(clean) == 0 or clean.std() == 0:
        return pd.Series(False, index=series.index)
    z = np.abs(scipy_stats.zscore(clean))
    mask = pd.Series(False, index=series.index)
    mask.loc[clean.index] = z > threshold
    return mask


def get_outlier_info(
    df: pd.DataFrame,
    method: str = "iqr",
    threshold: float = None,
) -> List[Dict[str, Any]]:
    """Detect outliers in all numeric columns.

    Returns list of dicts with column name, outlier count, bounds, etc.
    """
    if threshold is None:
        threshold = IQR_MULTIPLIER if method == "iqr" else ZSCORE_THRESHOLD

    results = []
    numeric_cols = df.select_dtypes(include=[np.number]).columns

    for col in numeric_cols:
        series = df[col]
        clean = series.dropna()
        if len(clean) == 0:
            continue

        if method == "iqr":
            mask = detect_outliers_iqr(series, multiplier=threshold)
            q1 = clean.quantile(0.25)
            q3 = clean.quantile(0.75)
            iqr = q3 - q1
            lower = q1 - threshold * iqr
            upper = q3 + threshold * iqr
        else:
            mask = detect_outliers_zscore(series, threshold=threshold)
            lower = float(clean.mean() - threshold * clean.std())
            upper = float(clean.mean() + threshold * clean.std())

        outlier_count = int(mask.sum())
        if outlier_count > 0:
            results.append({
                "name": col,
                "outlier_count": outlier_count,
                "outlier_pct": round(outlier_count / len(series) * 100, 2),
                "lower_bound": round(float(lower), 4),
                "upper_bound": round(float(upper), 4),
                "min": float(clean.min()),
                "max": float(clean.max()),
                "mean": float(clean.mean()),
                "std": float(clean.std()),
            })

    return results


# Remediation strategies
REMEDIATION_STRATEGIES = {
    "remove":      {"label": "Remove outlier rows"},
    "cap":         {"label": "Cap / Winsorize to bounds"},
    "log":         {"label": "Log transform"},
    "leave":       {"label": "Leave as-is"},
}


def apply_remediation(
    df: pd.DataFrame,
    column: str,
    strategy: str,
    method: str = "iqr",
    threshold: float = None,
) -> pd.DataFrame:
    """Apply an outlier remediation strategy to a column. Returns modified copy."""
    df = df.copy()

    if threshold is None:
        threshold = IQR_MULTIPLIER if method == "iqr" else ZSCORE_THRESHOLD

    if method == "iqr":
        mask = detect_outliers_iqr(df[column], multiplier=threshold)
        q1 = df[column].quantile(0.25)
        q3 = df[column].quantile(0.75)
        iqr = q3 - q1
        lower = q1 - threshold * iqr
        upper = q3 + threshold * iqr
    else:
        mask = detect_outliers_zscore(df[column], threshold=threshold)
        mean = df[column].mean()
        std = df[column].std()
        lower = mean - threshold * std
        upper = mean + threshold * std

    if strategy == "remove":
        df = df[~mask].reset_index(drop=True)

    elif strategy == "cap":
        df.loc[df[column] < lower, column] = lower
        df.loc[df[column] > upper, column] = upper

    elif strategy == "log":
        col_min = df[column].min()
        if col_min <= 0:
            shift = abs(col_min) + 1
            df[column] = np.log1p(df[column] + shift)
        else:
            df[column] = np.log1p(df[column])

    elif strategy == "leave":
        pass

    return df


def apply_remediations_bulk(
    df: pd.DataFrame,
    remediations: Dict[str, Dict[str, Any]],
) -> pd.DataFrame:
    """Apply remediations to multiple columns.

    Args:
        remediations: {column_name: {"strategy": str, "method": str, "threshold": float}}
    """
    df = df.copy()
    for col, config in remediations.items():
        strategy = config.get("strategy", "leave")
        if strategy != "leave":
            df = apply_remediation(
                df, col,
                strategy=strategy,
                method=config.get("method", "iqr"),
                threshold=config.get("threshold"),
            )
    return df
