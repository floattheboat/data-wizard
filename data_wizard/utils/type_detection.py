"""Smart dtype inference for DataFrame columns."""

import pandas as pd
import numpy as np


def classify_column(series: pd.Series) -> str:
    """Classify a pandas Series into one of: numeric, categorical, datetime, boolean, text.

    Returns a human-friendly type string.
    """
    if series.dropna().empty:
        return "empty"

    dtype = series.dtype

    if pd.api.types.is_bool_dtype(dtype):
        return "boolean"

    if pd.api.types.is_numeric_dtype(dtype):
        return "numeric"

    if pd.api.types.is_datetime64_any_dtype(dtype):
        return "datetime"

    # Try to parse as datetime
    if dtype == object:
        sample = series.dropna().head(100)
        try:
            parsed = pd.to_datetime(sample, format="mixed")
            if parsed.notna().sum() > len(sample) * 0.8:
                return "datetime"
        except (ValueError, TypeError):
            pass

        # Try to parse as numeric
        try:
            parsed = pd.to_numeric(sample)
            if parsed.notna().sum() > len(sample) * 0.8:
                return "numeric"
        except (ValueError, TypeError):
            pass

        # Categorical vs text heuristic: if unique ratio is low, it's categorical
        nunique = series.nunique()
        total = len(series.dropna())
        if total > 0 and (nunique / total < 0.5 or nunique <= 50):
            return "categorical"

        return "text"

    return "text"


def try_convert_column(series: pd.Series, target_type: str) -> pd.Series:
    """Attempt to convert a Series to the specified type."""
    if target_type == "numeric":
        return pd.to_numeric(series, errors="coerce")
    elif target_type == "datetime":
        return pd.to_datetime(series, errors="coerce", infer_datetime_format=True)
    elif target_type == "boolean":
        mapping = {"true": True, "false": False, "1": True, "0": False,
                   "yes": True, "no": False}
        return series.astype(str).str.lower().map(mapping)
    elif target_type == "categorical":
        return series.astype("category")
    return series
