"""Missing value detection and handling strategies."""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional

from data_wizard.utils.type_detection import classify_column


# Strategy definitions keyed by applicable types
STRATEGIES = {
    "drop_rows":       {"label": "Drop rows with missing values", "types": "all"},
    "fill_mean":       {"label": "Fill with mean",                "types": ["numeric"]},
    "fill_median":     {"label": "Fill with median",              "types": ["numeric"]},
    "fill_mode":       {"label": "Fill with mode",                "types": "all"},
    "fill_custom":     {"label": "Fill with custom value",        "types": "all"},
    "fill_forward":    {"label": "Forward fill",                  "types": "all"},
    "fill_backward":   {"label": "Backward fill",                 "types": "all"},
    "interpolate":     {"label": "Interpolate",                   "types": ["numeric"]},
    "leave":           {"label": "Leave as-is",                   "types": "all"},
}


def get_missing_columns(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Return list of columns that have missing values, with counts and types."""
    result = []
    for col in df.columns:
        missing = int(df[col].isna().sum())
        if missing > 0:
            col_type = classify_column(df[col])
            result.append({
                "name": col,
                "missing": missing,
                "missing_pct": round(missing / len(df) * 100, 2),
                "total": len(df),
                "inferred_type": col_type,
            })
    return result


def get_applicable_strategies(col_type: str) -> List[Dict[str, str]]:
    """Return strategies applicable for a given column type."""
    result = []
    for key, info in STRATEGIES.items():
        if info["types"] == "all" or col_type in info["types"]:
            result.append({"key": key, "label": info["label"]})
    return result


def apply_strategy(
    df: pd.DataFrame,
    column: str,
    strategy: str,
    custom_value: Any = None,
) -> pd.DataFrame:
    """Apply a missing-value strategy to a single column. Returns a modified copy."""
    df = df.copy()

    if strategy == "drop_rows":
        df = df.dropna(subset=[column]).reset_index(drop=True)

    elif strategy == "fill_mean":
        mean_val = pd.to_numeric(df[column], errors="coerce").mean()
        df[column] = df[column].fillna(mean_val)

    elif strategy == "fill_median":
        median_val = pd.to_numeric(df[column], errors="coerce").median()
        df[column] = df[column].fillna(median_val)

    elif strategy == "fill_mode":
        mode_vals = df[column].mode()
        if len(mode_vals) > 0:
            df[column] = df[column].fillna(mode_vals.iloc[0])

    elif strategy == "fill_custom":
        if custom_value is not None:
            df[column] = df[column].fillna(custom_value)

    elif strategy == "fill_forward":
        df[column] = df[column].ffill()

    elif strategy == "fill_backward":
        df[column] = df[column].bfill()

    elif strategy == "interpolate":
        df[column] = pd.to_numeric(df[column], errors="coerce").interpolate(method="linear")

    elif strategy == "leave":
        pass

    return df


def apply_strategies_bulk(
    df: pd.DataFrame,
    strategies: Dict[str, Dict[str, Any]],
) -> pd.DataFrame:
    """Apply strategies to multiple columns.

    Args:
        df: The DataFrame.
        strategies: Dict of {column_name: {"strategy": str, "custom_value": Any}}.

    Returns:
        Modified DataFrame copy.
    """
    df = df.copy()
    for col, config in strategies.items():
        strategy = config.get("strategy", "leave")
        custom_value = config.get("custom_value")
        if strategy != "leave":
            df = apply_strategy(df, col, strategy, custom_value)
    return df
