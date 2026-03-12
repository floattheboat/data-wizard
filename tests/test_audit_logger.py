"""Tests for the audit logger."""

import json
import os
import tempfile

import pandas as pd
import numpy as np
import pytest

from data_wizard.core.audit_logger import AuditLogger
from data_wizard.core.data_store import DataStore


@pytest.fixture(autouse=True)
def reset_store():
    DataStore.reset_instance()
    yield
    DataStore.reset_instance()


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "age": [25, 30, np.nan, 45, 200],
        "name": ["Alice", "Bob", None, "Dave", "Eve"],
        "score": [88.5, 92.0, 76.3, np.nan, 95.1],
    })


class TestAuditLogger:

    def test_record_load(self, sample_df):
        audit = AuditLogger()
        source = {"filename": "test.csv", "type": "file"}
        audit.record_load(sample_df, source)

        assert len(audit.events) == 1
        ev = audit.events[0]
        assert ev["event"] == "load"
        assert ev["source"]["filename"] == "test.csv"
        assert ev["snapshot"]["rows"] == 5
        assert ev["snapshot"]["cols"] == 3
        assert ev["timestamp"] is not None

    def test_record_operation(self, sample_df):
        audit = AuditLogger()
        df_after = sample_df.dropna().reset_index(drop=True)
        audit.record_operation(
            "missing_values",
            {"age": "drop_rows", "name": "drop_rows"},
            sample_df,
            df_after,
        )

        assert len(audit.events) == 1
        ev = audit.events[0]
        assert ev["event"] == "operation"
        assert ev["operation"] == "missing_values"
        assert ev["before"]["rows"] == 5
        assert ev["after"]["rows"] == 3
        assert ev["diff"]["rows_delta"] == -2

    def test_record_undo(self):
        audit = AuditLogger()
        audit.record_undo("missing_values")

        assert len(audit.events) == 1
        assert audit.events[0]["event"] == "undo"
        assert audit.events[0]["operation_undone"] == "missing_values"

    def test_record_export(self, sample_df):
        audit = AuditLogger()
        audit.record_export(sample_df, "/tmp/out.csv", "csv")

        ev = audit.events[0]
        assert ev["event"] == "export"
        assert ev["format"] == "csv"
        assert ev["snapshot"]["rows"] == 5

    def test_full_session(self, sample_df):
        audit = AuditLogger()
        audit.record_load(sample_df, {"filename": "data.csv"})

        # Simulate filling missing age
        df2 = sample_df.copy()
        df2["age"] = df2["age"].fillna(df2["age"].mean())
        audit.record_operation("missing_values", {"age": "fill_mean"}, sample_df, df2)

        audit.record_export(df2, "/tmp/clean.csv", "csv")

        assert len(audit.events) == 3
        assert [e["event"] for e in audit.events] == ["load", "operation", "export"]

    def test_save_report_json(self, sample_df, tmp_path):
        audit = AuditLogger()
        audit.record_load(sample_df, {"filename": "x.csv"})
        path = str(tmp_path / "report.json")
        audit.save_report(path)

        assert os.path.exists(path)
        with open(path) as f:
            data = json.load(f)
        assert data["total_events"] == 1
        assert data["events"][0]["event"] == "load"

    def test_format_text_report(self, sample_df):
        audit = AuditLogger()
        audit.record_load(sample_df, {"filename": "data.csv"})

        df2 = sample_df.dropna().reset_index(drop=True)
        audit.record_operation("missing_values", {"age": "drop_rows"}, sample_df, df2)
        audit.record_export(df2, "/tmp/out.csv", "csv")

        text = audit.format_text_report()
        assert "AUDIT REPORT" in text
        assert "LOAD" in text
        assert "MISSING VALUES" in text
        assert "EXPORT" in text
        assert "BEFORE vs AFTER" in text

    def test_clear(self, sample_df):
        audit = AuditLogger()
        audit.record_load(sample_df, {})
        audit.clear()
        assert len(audit.events) == 0
        assert audit._session_start is None


class TestDataStoreAuditIntegration:

    def test_load_records_audit(self, sample_df):
        store = DataStore()
        store.load(sample_df, {"filename": "test.csv"})

        assert len(store.audit.events) == 1
        assert store.audit.events[0]["event"] == "load"

    def test_log_operation_records_audit(self, sample_df):
        store = DataStore()
        store.load(sample_df, {"filename": "test.csv"})
        store.snapshot()
        store.df = sample_df.dropna().reset_index(drop=True)
        store.log_operation("missing_values", {"age": "drop_rows"})

        assert len(store.audit.events) == 2
        op_ev = store.audit.events[1]
        assert op_ev["event"] == "operation"
        assert op_ev["before"]["rows"] == 5
        assert op_ev["after"]["rows"] == 3

    def test_undo_records_audit(self, sample_df):
        store = DataStore()
        store.load(sample_df)
        store.snapshot()
        store.df = sample_df.dropna().reset_index(drop=True)
        store.log_operation("missing_values", {"age": "drop_rows"})
        store.undo()

        assert len(store.audit.events) == 3
        assert store.audit.events[2]["event"] == "undo"
        assert store.audit.events[2]["operation_undone"] == "missing_values"

    def test_enriched_details_format(self, sample_df):
        """New-format details dicts flow through to audit events correctly."""
        store = DataStore()
        store.load(sample_df)
        store.snapshot()
        store.df = sample_df.fillna(0)
        store.log_operation("missing_values", {
            "age": {"strategy": "fill_mean", "custom_value": None},
            "name": {"strategy": "fill_custom", "custom_value": "Unknown"},
        })

        op_ev = store.audit.events[1]
        assert op_ev["details"]["age"]["strategy"] == "fill_mean"
        assert op_ev["details"]["name"]["custom_value"] == "Unknown"

    def test_enriched_details_text_report(self, sample_df):
        """Text report handles both old string and new dict detail formats."""
        audit = AuditLogger()
        audit.record_load(sample_df, {"filename": "data.csv"})
        # New dict format
        audit.record_operation(
            "missing_values",
            {"age": {"strategy": "fill_mean"}, "name": {"strategy": "fill_custom"}},
            sample_df, sample_df.fillna(0),
        )
        text = audit.format_text_report()
        assert "fill_mean" in text
        assert "fill_custom" in text

    def test_reset_clears_audit(self, sample_df):
        store = DataStore()
        store.load(sample_df)
        store.reset()

        assert len(store.audit.events) == 0
