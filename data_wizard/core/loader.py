"""Load data from CSV, Excel, JSON, Parquet, and TSV files."""

import os
from typing import Optional, Tuple

import pandas as pd
import chardet


SUPPORTED_EXTENSIONS = {
    ".csv": "CSV",
    ".tsv": "TSV",
    ".xlsx": "Excel",
    ".xls": "Excel",
    ".json": "JSON",
    ".parquet": "Parquet",
    ".pq": "Parquet",
}


def detect_encoding(file_path: str, sample_size: int = 100_000) -> str:
    """Detect file encoding using chardet."""
    with open(file_path, "rb") as f:
        raw = f.read(sample_size)
    result = chardet.detect(raw)
    return result.get("encoding", "utf-8") or "utf-8"


def load_file(
    file_path: str,
    row_limit: Optional[int] = None,
    sheet_name=0,
) -> Tuple[pd.DataFrame, dict]:
    """Load a file into a DataFrame.

    Returns:
        (DataFrame, source_info dict)

    Raises:
        ValueError: If file type is unsupported or file cannot be parsed.
        FileNotFoundError: If file doesn't exist.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type: {ext}. "
            f"Supported: {', '.join(SUPPORTED_EXTENSIONS.keys())}"
        )

    file_type = SUPPORTED_EXTENSIONS[ext]
    source_info = {
        "type": "file",
        "file_type": file_type,
        "path": file_path,
        "filename": os.path.basename(file_path),
    }

    if file_type == "CSV":
        encoding = detect_encoding(file_path)
        source_info["encoding"] = encoding
        df = pd.read_csv(
            file_path,
            encoding=encoding,
            nrows=row_limit,
            low_memory=False,
        )

    elif file_type == "TSV":
        encoding = detect_encoding(file_path)
        source_info["encoding"] = encoding
        df = pd.read_csv(
            file_path,
            sep="\t",
            encoding=encoding,
            nrows=row_limit,
            low_memory=False,
        )

    elif file_type == "Excel":
        df = pd.read_excel(
            file_path,
            sheet_name=sheet_name,
            nrows=row_limit,
            engine="openpyxl" if ext == ".xlsx" else None,
        )
        source_info["sheet_name"] = sheet_name

    elif file_type == "JSON":
        df = pd.read_json(file_path)
        if row_limit is not None:
            df = df.head(row_limit)

    elif file_type == "Parquet":
        df = pd.read_parquet(file_path)
        if row_limit is not None:
            df = df.head(row_limit)

    else:
        raise ValueError(f"Unhandled file type: {file_type}")

    source_info["total_rows"] = len(df)
    source_info["total_cols"] = len(df.columns)

    return df, source_info


def get_file_filter() -> list:
    """Return file dialog filter tuples for supported types."""
    return [
        ("All Supported", "*.csv *.tsv *.xlsx *.xls *.json *.parquet *.pq"),
        ("CSV Files", "*.csv"),
        ("TSV Files", "*.tsv"),
        ("Excel Files", "*.xlsx *.xls"),
        ("JSON Files", "*.json"),
        ("Parquet Files", "*.parquet *.pq"),
        ("All Files", "*.*"),
    ]
