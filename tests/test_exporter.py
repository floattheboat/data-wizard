"""Tests for data_wizard.core.exporter."""

import os
import pytest
import pandas as pd

from data_wizard.core.exporter import export_dataframe, EXPORT_FORMATS


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "a": [1, 2, 3],
        "b": ["x", "y", "z"],
        "c": [1.1, 2.2, 3.3],
    })


class TestExportDataframe:
    def test_export_csv(self, tmp_path, sample_df):
        path = str(tmp_path / "output.csv")
        result = export_dataframe(sample_df, path, "csv")
        assert os.path.exists(result)
        loaded = pd.read_csv(result)
        assert len(loaded) == 3
        assert list(loaded.columns) == ["a", "b", "c"]

    def test_export_excel(self, tmp_path, sample_df):
        path = str(tmp_path / "output.xlsx")
        result = export_dataframe(sample_df, path, "excel")
        assert os.path.exists(result)
        loaded = pd.read_excel(result)
        assert len(loaded) == 3

    def test_export_json(self, tmp_path, sample_df):
        path = str(tmp_path / "output.json")
        result = export_dataframe(sample_df, path, "json")
        assert os.path.exists(result)
        loaded = pd.read_json(result)
        assert len(loaded) == 3

    def test_export_parquet(self, tmp_path, sample_df):
        path = str(tmp_path / "output.parquet")
        result = export_dataframe(sample_df, path, "parquet")
        assert os.path.exists(result)
        loaded = pd.read_parquet(result)
        assert len(loaded) == 3

    def test_adds_correct_extension(self, tmp_path, sample_df):
        path = str(tmp_path / "output")
        result = export_dataframe(sample_df, path, "csv")
        assert result.endswith(".csv")

    def test_unsupported_format(self, tmp_path, sample_df):
        with pytest.raises(ValueError, match="Unsupported"):
            export_dataframe(sample_df, str(tmp_path / "out.txt"), "txt")

    def test_creates_directory(self, tmp_path, sample_df):
        path = str(tmp_path / "subdir" / "output.csv")
        result = export_dataframe(sample_df, path, "csv")
        assert os.path.exists(result)

    def test_roundtrip_csv(self, tmp_path, sample_df):
        path = str(tmp_path / "roundtrip.csv")
        export_dataframe(sample_df, path, "csv")
        loaded = pd.read_csv(path)
        pd.testing.assert_frame_equal(sample_df, loaded)

    def test_roundtrip_parquet(self, tmp_path, sample_df):
        path = str(tmp_path / "roundtrip.parquet")
        export_dataframe(sample_df, path, "parquet")
        loaded = pd.read_parquet(path)
        pd.testing.assert_frame_equal(sample_df, loaded)
