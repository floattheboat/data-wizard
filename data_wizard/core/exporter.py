"""Export cleaned data to various file formats."""

import os
import pandas as pd
from typing import Optional


EXPORT_FORMATS = {
    "csv":     {"label": "CSV (.csv)",         "ext": ".csv"},
    "excel":   {"label": "Excel (.xlsx)",       "ext": ".xlsx"},
    "json":    {"label": "JSON (.json)",        "ext": ".json"},
    "parquet": {"label": "Parquet (.parquet)",  "ext": ".parquet"},
}


def export_dataframe(
    df: pd.DataFrame,
    file_path: str,
    fmt: str,
    index: bool = False,
) -> str:
    """Export a DataFrame to the specified format.

    Args:
        df: DataFrame to export.
        file_path: Destination path.
        fmt: One of 'csv', 'excel', 'json', 'parquet'.
        index: Whether to include the DataFrame index.

    Returns:
        Absolute path of the saved file.

    Raises:
        ValueError: On unsupported format.
    """
    if fmt not in EXPORT_FORMATS:
        raise ValueError(f"Unsupported export format: {fmt}. Choose from {list(EXPORT_FORMATS.keys())}")

    # Ensure correct extension
    expected_ext = EXPORT_FORMATS[fmt]["ext"]
    base, ext = os.path.splitext(file_path)
    if ext.lower() != expected_ext:
        file_path = base + expected_ext

    # Ensure directory exists
    dirpath = os.path.dirname(file_path)
    if dirpath:
        os.makedirs(dirpath, exist_ok=True)

    if fmt == "csv":
        df.to_csv(file_path, index=index)
    elif fmt == "excel":
        df.to_excel(file_path, index=index, engine="openpyxl")
    elif fmt == "json":
        df.to_json(file_path, orient="records", indent=2)
    elif fmt == "parquet":
        df.to_parquet(file_path, index=index)

    return os.path.abspath(file_path)


def get_save_filter(fmt: str) -> list:
    """Return file dialog filter for a given format."""
    info = EXPORT_FORMATS.get(fmt)
    if info:
        return [(info["label"], f"*{info['ext']}")]
    return [("All Files", "*.*")]
