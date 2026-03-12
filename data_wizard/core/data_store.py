"""Central DataFrame holder with undo stack and operations log."""

import pandas as pd
from typing import Optional, List, Dict, Any

from data_wizard.core.audit_logger import AuditLogger


class DataStore:
    """Singleton-style central data store for the application.

    Holds the current DataFrame, the original (unmodified) copy,
    an undo stack, and a log of all operations performed.
    """

    _instance: Optional["DataStore"] = None

    def __new__(cls) -> "DataStore":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.df: Optional[pd.DataFrame] = None
        self.original_df: Optional[pd.DataFrame] = None
        self._undo_stack: List[pd.DataFrame] = []
        self.operations: List[Dict[str, Any]] = []
        self.source_info: Dict[str, Any] = {}
        self._max_undo = 10
        self.audit = AuditLogger()
        # Callbacks for observers
        self._on_change_callbacks = []

    def on_change(self, callback):
        """Register a callback that fires when data changes."""
        self._on_change_callbacks.append(callback)

    def _notify(self):
        for cb in self._on_change_callbacks:
            try:
                cb()
            except Exception:
                pass

    def load(self, df: pd.DataFrame, source_info: Optional[Dict[str, Any]] = None):
        """Load a new DataFrame, resetting all state."""
        self.df = df.copy()
        self.original_df = df.copy()
        self._undo_stack.clear()
        self.operations.clear()
        self.source_info = source_info or {}
        self.audit.clear()
        self.audit.record_load(df, self.source_info)
        self._notify()

    @property
    def is_loaded(self) -> bool:
        return self.df is not None and not self.df.empty

    @property
    def shape(self):
        if self.df is not None:
            return self.df.shape
        return (0, 0)

    def snapshot(self):
        """Save current DataFrame to undo stack."""
        if self.df is not None:
            if len(self._undo_stack) >= self._max_undo:
                self._undo_stack.pop(0)
            self._undo_stack.append(self.df.copy())

    def undo(self) -> bool:
        """Restore previous DataFrame from undo stack. Returns True if successful."""
        if not self._undo_stack:
            return False
        self.df = self._undo_stack.pop()
        undone = self.operations.pop() if self.operations else None
        self.audit.record_undo(undone.get("operation") if undone else None)
        self._notify()
        return True

    @property
    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    def log_operation(self, operation: str, details: Dict[str, Any]):
        """Log an operation for the cleaning summary."""
        # Capture before from undo stack (the snapshot taken right before apply)
        df_before = self._undo_stack[-1] if self._undo_stack else self.original_df
        df_after = self.df
        if df_before is not None and df_after is not None:
            self.audit.record_operation(operation, details, df_before, df_after)
        self.operations.append({
            "operation": operation,
            "details": details,
            "shape_after": self.df.shape if self.df is not None else None,
        })

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all operations performed."""
        original_shape = self.original_df.shape if self.original_df is not None else (0, 0)
        current_shape = self.df.shape if self.df is not None else (0, 0)
        return {
            "original_shape": original_shape,
            "current_shape": current_shape,
            "rows_removed": original_shape[0] - current_shape[0],
            "operations": self.operations,
            "source": self.source_info,
        }

    def reset(self):
        """Reset the instance for a fresh start."""
        self.df = None
        self.original_df = None
        self._undo_stack.clear()
        self.operations.clear()
        self.source_info = {}
        self.audit.clear()
        self._notify()

    @classmethod
    def reset_instance(cls):
        """Fully reset the singleton (useful for testing)."""
        cls._instance = None
