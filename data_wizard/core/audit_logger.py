"""Audit logger that records every transformation from load to export.

Hooks into DataStore to capture detailed before/after snapshots for each
operation, producing a full provenance trail of the dataset.
"""

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd
import numpy as np


def _snapshot_column(series: pd.Series) -> Dict[str, Any]:
    """Capture key stats for a single column."""
    total = len(series)
    missing = int(series.isna().sum())
    info: Dict[str, Any] = {
        "dtype": str(series.dtype),
        "missing": missing,
        "missing_pct": round(missing / total * 100, 2) if total else 0,
        "unique": int(series.nunique()),
    }
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if len(numeric) > 0 and np.issubdtype(series.dtype, np.number):
        info.update({
            "min": float(numeric.min()),
            "max": float(numeric.max()),
            "mean": round(float(numeric.mean()), 4),
            "median": round(float(numeric.median()), 4),
            "std": round(float(numeric.std()), 4),
        })
    return info


def _snapshot_df(df: pd.DataFrame) -> Dict[str, Any]:
    """Capture a lightweight snapshot of the whole DataFrame."""
    total_cells = df.size
    total_missing = int(df.isna().sum().sum())
    return {
        "rows": len(df),
        "cols": len(df.columns),
        "total_missing": total_missing,
        "missing_pct": round(total_missing / total_cells * 100, 2) if total_cells else 0,
        "memory_mb": round(df.memory_usage(deep=True).sum() / 1024 / 1024, 3),
        "columns": {col: _snapshot_column(df[col]) for col in df.columns},
    }


class AuditLogger:
    """Records every event that happens to the dataset.

    Usage::

        from data_wizard.core.audit_logger import AuditLogger
        audit = AuditLogger()

        # Called automatically when wired into DataStore, or manually:
        audit.record_load(df, source_info)
        audit.record_operation("missing_values", details, df_before, df_after)
        audit.record_export(path, fmt)

        # At the end, write the full report:
        audit.save_report("audit_report.json")
        print(audit.format_text_report())
    """

    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self._load_snapshot: Optional[Dict[str, Any]] = None
        self._session_start: Optional[str] = None

    # ------------------------------------------------------------------
    # Recording methods
    # ------------------------------------------------------------------

    def record_load(self, df: pd.DataFrame, source_info: Dict[str, Any]):
        """Record the initial dataset load."""
        now = _now()
        self._session_start = now
        self._load_snapshot = _snapshot_df(df)
        self.events.append({
            "event": "load",
            "timestamp": now,
            "source": source_info,
            "snapshot": self._load_snapshot,
        })

    def record_operation(
        self,
        operation: str,
        details: Dict[str, Any],
        df_before: pd.DataFrame,
        df_after: pd.DataFrame,
    ):
        """Record a data transformation with before/after snapshots."""
        before = _snapshot_df(df_before)
        after = _snapshot_df(df_after)
        diff = _compute_diff(before, after)
        self.events.append({
            "event": "operation",
            "timestamp": _now(),
            "operation": operation,
            "details": _sanitize(details),
            "before": {"rows": before["rows"], "cols": before["cols"],
                       "total_missing": before["total_missing"]},
            "after": {"rows": after["rows"], "cols": after["cols"],
                      "total_missing": after["total_missing"]},
            "diff": diff,
        })

    def record_undo(self, operation_undone: Optional[str] = None):
        """Record an undo action."""
        self.events.append({
            "event": "undo",
            "timestamp": _now(),
            "operation_undone": operation_undone,
        })

    def record_export(
        self,
        df: pd.DataFrame,
        destination: str,
        fmt: str,
        extra: Optional[Dict[str, Any]] = None,
    ):
        """Record the final export."""
        self.events.append({
            "event": "export",
            "timestamp": _now(),
            "destination": destination,
            "format": fmt,
            "snapshot": _snapshot_df(df),
            "extra": extra or {},
        })

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def get_report(self) -> Dict[str, Any]:
        """Return the full audit report as a dict."""
        return {
            "session_start": self._session_start,
            "session_end": _now(),
            "total_events": len(self.events),
            "events": self.events,
        }

    def save_report(self, path: str):
        """Write the audit report to a JSON file."""
        dirpath = os.path.dirname(path)
        if dirpath:
            os.makedirs(dirpath, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.get_report(), f, indent=2, default=str)
        return os.path.abspath(path)

    def format_text_report(self) -> str:
        """Return a human-readable text summary of the audit trail."""
        lines: List[str] = []
        lines.append("=" * 64)
        lines.append("  DATA WIZARD — AUDIT REPORT")
        lines.append("=" * 64)

        if self._session_start:
            lines.append(f"Session started: {self._session_start}")
        lines.append(f"Total events:    {len(self.events)}")
        lines.append("")

        for i, ev in enumerate(self.events, 1):
            etype = ev["event"]
            ts = ev.get("timestamp", "")

            if etype == "load":
                snap = ev["snapshot"]
                src = ev.get("source", {})
                lines.append(f"[{i}] LOAD  ({ts})")
                src_desc = src.get("filename") or src.get("table_name") or src.get("path", "unknown")
                lines.append(f"    Source:  {src_desc}")
                lines.append(f"    Shape:   {snap['rows']:,} rows × {snap['cols']} cols")
                lines.append(f"    Missing: {snap['total_missing']:,} cells ({snap['missing_pct']}%)")
                lines.append(f"    Memory:  {snap['memory_mb']:.2f} MB")

            elif etype == "operation":
                op = ev.get("operation", "?")
                before = ev["before"]
                after = ev["after"]
                diff = ev.get("diff", {})
                lines.append(f"[{i}] {op.upper().replace('_', ' ')}  ({ts})")

                details = ev.get("details", {})
                for col, action in details.items():
                    if isinstance(action, dict):
                        action_str = action.get("strategy", str(action))
                    else:
                        action_str = str(action)
                    lines.append(f"    • {col}: {action_str}")

                lines.append(f"    Rows:    {before['rows']:,} → {after['rows']:,}"
                             f"  ({diff.get('rows_delta', 0):+,})")
                lines.append(f"    Missing: {before['total_missing']:,} → {after['total_missing']:,}"
                             f"  ({diff.get('missing_delta', 0):+,})")

            elif etype == "undo":
                undone = ev.get("operation_undone", "last operation")
                lines.append(f"[{i}] UNDO  ({ts})")
                lines.append(f"    Reversed: {undone}")

            elif etype == "export":
                snap = ev["snapshot"]
                lines.append(f"[{i}] EXPORT  ({ts})")
                lines.append(f"    Destination: {ev.get('destination', '?')}")
                lines.append(f"    Format:      {ev.get('format', '?')}")
                lines.append(f"    Final shape: {snap['rows']:,} rows × {snap['cols']} cols")
                lines.append(f"    Missing:     {snap['total_missing']:,} cells ({snap['missing_pct']}%)")

            lines.append("")

        # Summary comparison if we have load and at least one other event
        load_ev = next((e for e in self.events if e["event"] == "load"), None)
        export_ev = next((e for e in reversed(self.events) if e["event"] == "export"), None)
        if load_ev and export_ev:
            ls = load_ev["snapshot"]
            es = export_ev["snapshot"]
            lines.append("-" * 64)
            lines.append("  BEFORE vs AFTER")
            lines.append("-" * 64)
            lines.append(f"  Rows:    {ls['rows']:,} → {es['rows']:,}  ({es['rows'] - ls['rows']:+,})")
            lines.append(f"  Cols:    {ls['cols']} → {es['cols']}  ({es['cols'] - ls['cols']:+})")
            lines.append(f"  Missing: {ls['total_missing']:,} → {es['total_missing']:,}"
                         f"  ({es['total_missing'] - ls['total_missing']:+,})")
            lines.append(f"  Memory:  {ls['memory_mb']:.2f} MB → {es['memory_mb']:.2f} MB")
            lines.append("")

        lines.append("=" * 64)
        return "\n".join(lines)

    def clear(self):
        """Reset all recorded events."""
        self.events.clear()
        self._load_snapshot = None
        self._session_start = None


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _compute_diff(before: Dict, after: Dict) -> Dict[str, Any]:
    """Compute high-level deltas between two snapshots."""
    return {
        "rows_delta": after["rows"] - before["rows"],
        "cols_delta": after["cols"] - before["cols"],
        "missing_delta": after["total_missing"] - before["total_missing"],
    }


def _sanitize(obj: Any) -> Any:
    """Make an object JSON-safe."""
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj
