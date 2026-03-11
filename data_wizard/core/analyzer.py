"""Per-column exploratory statistics and analysis."""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from scipy import stats as scipy_stats

from data_wizard.utils.type_detection import classify_column


def analyze_column(series: pd.Series) -> Dict[str, Any]:
    """Compute comprehensive stats for a single column."""
    col_type = classify_column(series)
    total = len(series)
    missing = int(series.isna().sum())
    present = total - missing

    result: Dict[str, Any] = {
        "name": series.name,
        "dtype": str(series.dtype),
        "inferred_type": col_type,
        "total": total,
        "missing": missing,
        "missing_pct": round(missing / total * 100, 2) if total > 0 else 0,
        "present": present,
        "unique": int(series.nunique()),
    }

    clean = series.dropna()

    if col_type == "numeric":
        numeric = pd.to_numeric(clean.astype(float, errors="ignore"), errors="coerce").dropna()
        if len(numeric) > 0:
            result.update({
                "min": float(numeric.min()),
                "max": float(numeric.max()),
                "mean": float(numeric.mean()),
                "median": float(numeric.median()),
                "std": float(numeric.std()),
                "skew": float(numeric.skew()) if len(numeric) > 2 else None,
                "kurtosis": float(numeric.kurtosis()) if len(numeric) > 3 else None,
                "q1": float(numeric.quantile(0.25)),
                "q3": float(numeric.quantile(0.75)),
                "zeros": int((numeric == 0).sum()),
                "negatives": int((numeric < 0).sum()),
            })

    elif col_type == "categorical" or col_type == "text":
        vc = clean.value_counts()
        result["top_values"] = vc.head(10).to_dict()
        if len(clean) > 0:
            result["most_common"] = str(vc.index[0])
            result["most_common_count"] = int(vc.iloc[0])

    elif col_type == "datetime":
        dt = pd.to_datetime(clean, errors="coerce").dropna()
        if len(dt) > 0:
            result["min_date"] = str(dt.min())
            result["max_date"] = str(dt.max())
            result["date_range_days"] = (dt.max() - dt.min()).days

    elif col_type == "boolean":
        vc = clean.value_counts()
        result["top_values"] = {str(k): int(v) for k, v in vc.items()}

    return result


def analyze_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyze every column in a DataFrame.

    Returns a dict with 'columns' (list of per-column stats) and 'overview' (shape info).
    """
    columns = []
    for col in df.columns:
        col_stats = analyze_column(df[col])
        columns.append(col_stats)

    overview = {
        "rows": len(df),
        "cols": len(df.columns),
        "total_missing": int(df.isna().sum().sum()),
        "total_cells": int(df.size),
        "missing_pct": round(df.isna().sum().sum() / df.size * 100, 2) if df.size > 0 else 0,
        "memory_mb": round(df.memory_usage(deep=True).sum() / 1024 / 1024, 2),
        "dtypes": df.dtypes.astype(str).value_counts().to_dict(),
    }

    return {"columns": columns, "overview": overview}


def compute_correlation(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """Compute correlation matrix for numeric columns."""
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) < 2:
        return None
    return df[numeric_cols].corr()
