"""Tests for the reproducible script generator."""

import os
import textwrap

import pandas as pd
import numpy as np
import pytest

from data_wizard.core.script_generator import generate_script, _resolve_events
from data_wizard.core.audit_logger import AuditLogger
from data_wizard.core.data_store import DataStore


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_store():
    DataStore.reset_instance()
    yield
    DataStore.reset_instance()


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "age": [25.0, 30.0, np.nan, 45.0, 200.0],
        "name": ["Alice", "Bob", None, "Dave", "Eve"],
        "score": [88.5, 92.0, 76.3, np.nan, 95.1],
    })


def _make_load_event(source=None):
    return {
        "event": "load",
        "timestamp": "2026-03-12T10:00:00+00:00",
        "source": source or {
            "type": "file",
            "file_type": "CSV",
            "path": "/data/input.csv",
            "filename": "input.csv",
            "encoding": "utf-8",
        },
        "snapshot": {"rows": 100, "cols": 5, "total_missing": 10, "missing_pct": 2.0,
                     "memory_mb": 0.1, "columns": {}},
    }


def _make_operation_event(operation, details, rows_before=100, rows_after=95):
    return {
        "event": "operation",
        "timestamp": "2026-03-12T10:05:00+00:00",
        "operation": operation,
        "details": details,
        "before": {"rows": rows_before, "cols": 5, "total_missing": 10},
        "after": {"rows": rows_after, "cols": 5, "total_missing": 0},
        "diff": {"rows_delta": rows_after - rows_before, "cols_delta": 0, "missing_delta": -10},
    }


def _make_undo_event(operation_undone=None):
    return {
        "event": "undo",
        "timestamp": "2026-03-12T10:06:00+00:00",
        "operation_undone": operation_undone,
    }


def _make_export_event(destination="/data/output.csv", fmt="csv"):
    return {
        "event": "export",
        "timestamp": "2026-03-12T10:10:00+00:00",
        "destination": destination,
        "format": fmt,
        "snapshot": {"rows": 95, "cols": 5, "total_missing": 0, "missing_pct": 0.0,
                     "memory_mb": 0.08, "columns": {}},
        "extra": {},
    }


# ------------------------------------------------------------------
# Undo resolution tests
# ------------------------------------------------------------------

class TestResolveEvents:

    def test_no_undos(self):
        events = [_make_load_event(), _make_operation_event("missing_values", {}), _make_export_event()]
        resolved = _resolve_events(events)
        assert len(resolved) == 3
        assert [e["event"] for e in resolved] == ["load", "operation", "export"]

    def test_single_undo(self):
        events = [
            _make_load_event(),
            _make_operation_event("missing_values", {"age": "fill_mean"}),
            _make_undo_event("missing_values"),
            _make_export_event(),
        ]
        resolved = _resolve_events(events)
        assert len(resolved) == 2
        assert [e["event"] for e in resolved] == ["load", "export"]

    def test_multiple_undos(self):
        events = [
            _make_load_event(),
            _make_operation_event("missing_values", {"age": "fill_mean"}),
            _make_operation_event("outlier_remediation", {"score": "cap"}),
            _make_undo_event(),
            _make_undo_event(),
            _make_export_event(),
        ]
        resolved = _resolve_events(events)
        assert len(resolved) == 2
        assert [e["event"] for e in resolved] == ["load", "export"]

    def test_undo_then_new_op(self):
        events = [
            _make_load_event(),
            _make_operation_event("missing_values", {"age": "drop_rows"}),
            _make_undo_event(),
            _make_operation_event("missing_values", {"age": "fill_mean"}),
            _make_export_event(),
        ]
        resolved = _resolve_events(events)
        assert len(resolved) == 3
        assert resolved[1]["details"] == {"age": "fill_mean"}

    def test_undo_with_empty_stack(self):
        """Undo with no operations is a no-op."""
        events = [_make_load_event(), _make_undo_event(), _make_export_event()]
        resolved = _resolve_events(events)
        assert len(resolved) == 2

    def test_interleaved(self):
        events = [
            _make_load_event(),
            _make_operation_event("missing_values", {"a": "fill_mean"}),
            _make_operation_event("outlier_remediation", {"b": "cap"}),
            _make_undo_event(),  # undoes outlier
            _make_operation_event("outlier_remediation", {"b": "remove"}),
            _make_export_event(),
        ]
        resolved = _resolve_events(events)
        assert len(resolved) == 4
        ops = [e for e in resolved if e["event"] == "operation"]
        assert ops[0]["details"] == {"a": "fill_mean"}
        assert ops[1]["details"] == {"b": "remove"}


# ------------------------------------------------------------------
# Script generation tests
# ------------------------------------------------------------------

class TestGenerateScript:

    def test_basic_csv_load_export(self):
        events = [_make_load_event(), _make_export_event()]
        script = generate_script(events)
        assert "pd.read_csv" in script
        assert "to_csv" in script
        compile(script, "<test>", "exec")

    def test_excel_load(self):
        src = {"type": "file", "file_type": "Excel", "path": "/data/in.xlsx",
               "filename": "in.xlsx", "sheet_name": "Sheet1"}
        events = [_make_load_event(source=src), _make_export_event()]
        script = generate_script(events)
        assert "pd.read_excel" in script
        assert "'Sheet1'" in script
        compile(script, "<test>", "exec")

    def test_tsv_load(self):
        src = {"type": "file", "file_type": "TSV", "path": "/data/in.tsv",
               "filename": "in.tsv", "encoding": "utf-8"}
        events = [_make_load_event(source=src), _make_export_event()]
        script = generate_script(events)
        assert 'sep="\\t"' in script
        compile(script, "<test>", "exec")

    def test_parquet_load(self):
        src = {"type": "file", "file_type": "Parquet", "path": "/data/in.parquet",
               "filename": "in.parquet"}
        events = [_make_load_event(source=src), _make_export_event()]
        script = generate_script(events)
        assert "pd.read_parquet" in script
        compile(script, "<test>", "exec")

    def test_json_load(self):
        src = {"type": "file", "file_type": "JSON", "path": "/data/in.json",
               "filename": "in.json"}
        events = [_make_load_event(source=src), _make_export_event()]
        script = generate_script(events)
        assert "pd.read_json" in script
        compile(script, "<test>", "exec")

    def test_database_source(self):
        src = {"type": "database", "table_name": "users"}
        events = [_make_load_event(source=src), _make_export_event()]
        script = generate_script(events)
        assert "NotImplementedError" in script
        assert "TODO" in script
        compile(script, "<test>", "exec")

    def test_database_export(self):
        export = _make_export_event(destination="database://users", fmt="database")
        export["extra"] = {"table_name": "users"}
        events = [_make_load_event(), export]
        script = generate_script(events)
        assert "to_sql" in script
        assert "TODO" in script
        compile(script, "<test>", "exec")

    # -- Missing values strategies --

    def test_missing_fill_mean(self):
        details = {"age": {"strategy": "fill_mean"}}
        events = [_make_load_event(), _make_operation_event("missing_values", details), _make_export_event()]
        script = generate_script(events)
        assert ".fillna(" in script
        assert ".mean()" in script
        compile(script, "<test>", "exec")

    def test_missing_fill_median(self):
        details = {"age": {"strategy": "fill_median"}}
        events = [_make_load_event(), _make_operation_event("missing_values", details), _make_export_event()]
        script = generate_script(events)
        assert ".median()" in script
        compile(script, "<test>", "exec")

    def test_missing_fill_mode(self):
        details = {"age": {"strategy": "fill_mode"}}
        events = [_make_load_event(), _make_operation_event("missing_values", details), _make_export_event()]
        script = generate_script(events)
        assert ".mode()" in script
        compile(script, "<test>", "exec")

    def test_missing_fill_custom_numeric(self):
        details = {"age": {"strategy": "fill_custom", "custom_value": 42.0}}
        events = [_make_load_event(), _make_operation_event("missing_values", details), _make_export_event()]
        script = generate_script(events)
        assert "42.0" in script
        compile(script, "<test>", "exec")

    def test_missing_fill_custom_string(self):
        details = {"name": {"strategy": "fill_custom", "custom_value": "Unknown"}}
        events = [_make_load_event(), _make_operation_event("missing_values", details), _make_export_event()]
        script = generate_script(events)
        assert "'Unknown'" in script
        compile(script, "<test>", "exec")

    def test_missing_drop_rows(self):
        details = {"age": {"strategy": "drop_rows"}}
        events = [_make_load_event(), _make_operation_event("missing_values", details), _make_export_event()]
        script = generate_script(events)
        assert "dropna" in script
        compile(script, "<test>", "exec")

    def test_missing_ffill(self):
        details = {"age": {"strategy": "fill_forward"}}
        events = [_make_load_event(), _make_operation_event("missing_values", details), _make_export_event()]
        script = generate_script(events)
        assert ".ffill()" in script
        compile(script, "<test>", "exec")

    def test_missing_bfill(self):
        details = {"age": {"strategy": "fill_backward"}}
        events = [_make_load_event(), _make_operation_event("missing_values", details), _make_export_event()]
        script = generate_script(events)
        assert ".bfill()" in script
        compile(script, "<test>", "exec")

    def test_missing_interpolate(self):
        details = {"age": {"strategy": "interpolate"}}
        events = [_make_load_event(), _make_operation_event("missing_values", details), _make_export_event()]
        script = generate_script(events)
        assert "interpolate" in script
        compile(script, "<test>", "exec")

    def test_missing_leave_skipped(self):
        details = {"age": {"strategy": "leave"}}
        events = [_make_load_event(), _make_operation_event("missing_values", details), _make_export_event()]
        script = generate_script(events)
        assert "age" not in script.split("Handle missing")[1].split("Export")[0] or "leave" not in script

    def test_missing_backward_compat(self):
        """Old format: details values are plain strings."""
        details = {"age": "fill_mean", "name": "drop_rows"}
        events = [_make_load_event(), _make_operation_event("missing_values", details), _make_export_event()]
        script = generate_script(events)
        assert ".mean()" in script
        assert "dropna" in script
        compile(script, "<test>", "exec")

    # -- Outlier strategies --

    def test_outlier_cap_iqr(self):
        details = {"score": {"strategy": "cap", "method": "iqr", "threshold": 1.5}}
        events = [_make_load_event(), _make_operation_event("outlier_remediation", details), _make_export_event()]
        script = generate_script(events)
        assert "quantile(0.25)" in script
        assert "quantile(0.75)" in script
        assert "1.5" in script
        compile(script, "<test>", "exec")

    def test_outlier_remove_zscore(self):
        details = {"score": {"strategy": "remove", "method": "zscore", "threshold": 2.5}}
        events = [_make_load_event(), _make_operation_event("outlier_remediation", details), _make_export_event()]
        script = generate_script(events)
        assert "_mean" in script
        assert "_std" in script
        assert "~_mask" in script
        compile(script, "<test>", "exec")

    def test_outlier_log(self):
        details = {"score": {"strategy": "log", "method": "iqr", "threshold": 1.5}}
        events = [_make_load_event(), _make_operation_event("outlier_remediation", details), _make_export_event()]
        script = generate_script(events)
        assert "np.log1p" in script
        compile(script, "<test>", "exec")

    def test_outlier_backward_compat(self):
        """Old format: strategy string only, defaults to iqr."""
        details = {"score": "cap"}
        events = [_make_load_event(), _make_operation_event("outlier_remediation", details), _make_export_event()]
        script = generate_script(events)
        assert "quantile" in script
        assert "1.5" in script
        compile(script, "<test>", "exec")

    # -- Undo in script --

    def test_undo_strips_operation(self):
        events = [
            _make_load_event(),
            _make_operation_event("missing_values", {"age": {"strategy": "fill_mean"}}),
            _make_undo_event("missing_values"),
            _make_export_event(),
        ]
        script = generate_script(events)
        assert "missing" not in script.lower().split("step 1")[1].split("step 2")[0]  # no missing step
        compile(script, "<test>", "exec")

    # -- File output --

    def test_writes_to_file(self, tmp_path):
        events = [_make_load_event(), _make_export_event()]
        out = str(tmp_path / "reproduce.py")
        result = generate_script(events, output_path=out)
        assert os.path.exists(out)
        with open(out) as f:
            assert f.read() == result

    def test_header_contains_source(self):
        events = [_make_load_event(), _make_export_event()]
        script = generate_script(events)
        assert "input.csv" in script

    # -- Export formats --

    def test_export_excel(self):
        events = [_make_load_event(), _make_export_event("/out.xlsx", "excel")]
        script = generate_script(events)
        assert "to_excel" in script
        compile(script, "<test>", "exec")

    def test_export_json(self):
        events = [_make_load_event(), _make_export_event("/out.json", "json")]
        script = generate_script(events)
        assert "to_json" in script
        compile(script, "<test>", "exec")

    def test_export_parquet(self):
        events = [_make_load_event(), _make_export_event("/out.parquet", "parquet")]
        script = generate_script(events)
        assert "to_parquet" in script
        compile(script, "<test>", "exec")

    def test_export_tsv(self):
        events = [_make_load_event(), _make_export_event("/out.tsv", "tsv")]
        script = generate_script(events)
        assert 'sep="\\t"' in script
        compile(script, "<test>", "exec")


# ------------------------------------------------------------------
# End-to-end: build a real pipeline and exec the generated script
# ------------------------------------------------------------------

class TestEndToEnd:

    def test_full_pipeline_roundtrip(self, sample_df, tmp_path):
        """Run the wizard pipeline, generate a script, exec it, compare results."""
        from data_wizard.core.missing_handler import apply_strategies_bulk
        from data_wizard.core.outlier_detector import apply_remediations_bulk

        # Save source CSV
        input_path = str(tmp_path / "source.csv")
        sample_df.to_csv(input_path, index=False)

        # Simulate the wizard pipeline
        store = DataStore()
        store.load(sample_df, {
            "type": "file", "file_type": "CSV", "path": input_path,
            "filename": "source.csv", "encoding": "utf-8",
        })

        # Step: missing values
        missing_strategies = {
            "age": {"strategy": "fill_mean", "custom_value": None},
            "name": {"strategy": "fill_custom", "custom_value": "Unknown"},
            "score": {"strategy": "fill_median", "custom_value": None},
        }
        store.snapshot()
        new_df = apply_strategies_bulk(store.df, missing_strategies)
        store.df = new_df
        store.log_operation("missing_values", {
            col: cfg for col, cfg in missing_strategies.items() if cfg["strategy"] != "leave"
        })

        # Step: outlier remediation
        outlier_remediations = {
            "age": {"strategy": "cap", "method": "iqr", "threshold": 1.5},
        }
        store.snapshot()
        new_df = apply_remediations_bulk(store.df, outlier_remediations)
        store.df = new_df
        store.log_operation("outlier_remediation", {
            col: cfg for col, cfg in outlier_remediations.items()
        })

        # Record export
        export_path = str(tmp_path / "cleaned.csv")
        store.df.to_csv(export_path, index=False)
        store.audit.record_export(store.df, export_path, "csv")

        # The expected result
        expected_df = store.df.copy()

        # Generate and execute the reproduction script
        script = generate_script(store.audit.events)
        compile(script, "<roundtrip>", "exec")

        # Exec the script with overridden paths
        reproduced_path = str(tmp_path / "reproduced.csv")
        exec_globals = {"__name__": "__main__"}
        # Override sys.argv so the script picks up our paths
        import sys
        old_argv = sys.argv
        sys.argv = ["reproduce.py", input_path, reproduced_path]
        try:
            exec(compile(script, "<roundtrip>", "exec"), exec_globals)
        finally:
            sys.argv = old_argv

        # Compare
        reproduced_df = pd.read_csv(reproduced_path)
        pd.testing.assert_frame_equal(
            reproduced_df.reset_index(drop=True),
            expected_df.reset_index(drop=True),
            check_dtype=False,
            atol=1e-6,
        )
