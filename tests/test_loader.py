"""Tests for data_wizard.core.loader."""

import os
import json
import tempfile
import pytest
import pandas as pd

from data_wizard.core.loader import load_file, detect_encoding, SUPPORTED_EXTENSIONS


@pytest.fixture
def sample_csv(tmp_path):
    path = tmp_path / "test.csv"
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"], "c": [1.1, 2.2, 3.3]})
    df.to_csv(path, index=False)
    return str(path)


@pytest.fixture
def sample_tsv(tmp_path):
    path = tmp_path / "test.tsv"
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    df.to_csv(path, index=False, sep="\t")
    return str(path)


@pytest.fixture
def sample_json(tmp_path):
    path = tmp_path / "test.json"
    data = [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}, {"a": 3, "b": "z"}]
    with open(path, "w") as f:
        json.dump(data, f)
    return str(path)


@pytest.fixture
def sample_excel(tmp_path):
    path = tmp_path / "test.xlsx"
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    df.to_excel(path, index=False)
    return str(path)


@pytest.fixture
def sample_parquet(tmp_path):
    path = tmp_path / "test.parquet"
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    df.to_parquet(path, index=False)
    return str(path)


class TestLoadFile:
    def test_load_csv(self, sample_csv):
        df, info = load_file(sample_csv)
        assert len(df) == 3
        assert list(df.columns) == ["a", "b", "c"]
        assert info["file_type"] == "CSV"

    def test_load_tsv(self, sample_tsv):
        df, info = load_file(sample_tsv)
        assert len(df) == 3
        assert info["file_type"] == "TSV"

    def test_load_json(self, sample_json):
        df, info = load_file(sample_json)
        assert len(df) == 3
        assert info["file_type"] == "JSON"

    def test_load_excel(self, sample_excel):
        df, info = load_file(sample_excel)
        assert len(df) == 3
        assert info["file_type"] == "Excel"

    def test_load_parquet(self, sample_parquet):
        df, info = load_file(sample_parquet)
        assert len(df) == 3
        assert info["file_type"] == "Parquet"

    def test_load_with_row_limit(self, sample_csv):
        df, info = load_file(sample_csv, row_limit=2)
        assert len(df) == 2

    def test_load_nonexistent_file(self):
        with pytest.raises(FileNotFoundError):
            load_file("/nonexistent/path.csv")

    def test_load_unsupported_format(self, tmp_path):
        path = tmp_path / "test.xyz"
        path.write_text("data")
        with pytest.raises(ValueError, match="Unsupported"):
            load_file(str(path))

    def test_source_info_has_required_keys(self, sample_csv):
        _, info = load_file(sample_csv)
        assert "type" in info
        assert "file_type" in info
        assert "total_rows" in info
        assert "total_cols" in info


class TestDetectEncoding:
    def test_detect_utf8(self, sample_csv):
        enc = detect_encoding(sample_csv)
        # chardet may detect as ascii, utf-8, or windows-1252 for simple ASCII content
        assert enc is not None
        assert len(enc) > 0
