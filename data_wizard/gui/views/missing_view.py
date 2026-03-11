"""Step 3: Missing value handling prompts."""

import customtkinter as ctk
import pandas as pd

from data_wizard.utils.constants import (
    FONT_FAMILY, FONT_SIZE_SM, FONT_SIZE_MD, FONT_SIZE_LG,
    ACCENT_COLOR, SUCCESS_COLOR, WARNING_COLOR, MUTED_TEXT,
)
from data_wizard.core.data_store import DataStore
from data_wizard.core.missing_handler import (
    get_missing_columns, get_applicable_strategies, apply_strategies_bulk,
)


class MissingView(ctk.CTkFrame):
    """View for handling missing values — per-column strategy selection."""

    def __init__(self, master, on_proceed=None, **kwargs):
        super().__init__(master, **kwargs)
        self._on_proceed = on_proceed
        self._store = DataStore()
        self._strategy_widgets = {}  # col_name -> (var, custom_entry)

        self._build_ui()

    def _build_ui(self):
        # Title
        ctk.CTkLabel(
            self, text="Handle Missing Values",
            font=(FONT_FAMILY, FONT_SIZE_LG, "bold"), anchor="w",
        ).pack(fill="x", padx=20, pady=(15, 5))

        self._summary_label = ctk.CTkLabel(
            self, text="", font=(FONT_FAMILY, FONT_SIZE_SM), anchor="w",
        )
        self._summary_label.pack(fill="x", padx=20, pady=(0, 10))

        # Scrollable area for column strategies
        self._scroll = ctk.CTkScrollableFrame(self)
        self._scroll.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # Bottom buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 15))

        self._btn_undo = ctk.CTkButton(
            btn_frame, text="Undo Last", width=100,
            fg_color="gray50", command=self._undo,
        )
        self._btn_undo.pack(side="left", padx=(0, 10))

        self._btn_apply = ctk.CTkButton(
            btn_frame, text="Apply All Strategies", width=180,
            fg_color=ACCENT_COLOR, command=self._apply_all,
        )
        self._btn_apply.pack(side="left", padx=(0, 10))

        self._btn_proceed = ctk.CTkButton(
            btn_frame, text="Proceed to Outliers  →", height=38,
            font=(FONT_FAMILY, FONT_SIZE_MD, "bold"),
            fg_color=SUCCESS_COLOR,
            command=self._proceed,
        )
        self._btn_proceed.pack(side="right")

        self._status_label = ctk.CTkLabel(
            self, text="", font=(FONT_FAMILY, FONT_SIZE_SM),
        )
        self._status_label.pack(pady=(0, 5))

    def activate(self):
        """Refresh the view with current data."""
        if not self._store.is_loaded:
            return
        self._refresh()

    def _refresh(self):
        # Clear old widgets
        for w in self._scroll.winfo_children():
            w.destroy()
        self._strategy_widgets.clear()

        missing_cols = get_missing_columns(self._store.df)

        if not missing_cols:
            self._summary_label.configure(
                text="No missing values found! Your data is complete.",
                text_color=SUCCESS_COLOR,
            )
            self._btn_apply.configure(state="disabled")
            self._status_label.configure(text="")
            return

        total_missing = sum(c["missing"] for c in missing_cols)
        self._summary_label.configure(
            text=f"{len(missing_cols)} column(s) with missing values  |  "
                 f"{total_missing:,} total missing cells",
            text_color=WARNING_COLOR,
        )
        self._btn_apply.configure(state="normal")

        # Build per-column rows
        for col_info in missing_cols:
            self._add_column_row(col_info)

        self._btn_undo.configure(
            state="normal" if self._store.can_undo else "disabled"
        )

    def _add_column_row(self, col_info: dict):
        name = col_info["name"]
        col_type = col_info["inferred_type"]
        strategies = get_applicable_strategies(col_type)

        row = ctk.CTkFrame(self._scroll, corner_radius=6)
        row.pack(fill="x", pady=3, padx=2)

        # Left: column info
        info_frame = ctk.CTkFrame(row, fg_color="transparent")
        info_frame.pack(side="left", fill="x", expand=True, padx=10, pady=8)

        ctk.CTkLabel(
            info_frame, text=name,
            font=(FONT_FAMILY, FONT_SIZE_MD, "bold"), anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            info_frame,
            text=f"Type: {col_type}  |  Missing: {col_info['missing']} ({col_info['missing_pct']}%)",
            font=(FONT_FAMILY, FONT_SIZE_SM), text_color=MUTED_TEXT, anchor="w",
        ).pack(anchor="w")

        # Right: strategy picker
        right_frame = ctk.CTkFrame(row, fg_color="transparent")
        right_frame.pack(side="right", padx=10, pady=8)

        strategy_var = ctk.StringVar(value="leave")
        strategy_labels = {s["key"]: s["label"] for s in strategies}
        strategy_menu = ctk.CTkOptionMenu(
            right_frame, variable=strategy_var,
            values=list(strategy_labels.keys()),
            width=180,
        )
        strategy_menu.pack(side="left", padx=(0, 5))

        # Custom value entry (shown for fill_custom)
        custom_entry = ctk.CTkEntry(right_frame, placeholder_text="value", width=100)

        def on_strategy_change(*_):
            if strategy_var.get() == "fill_custom":
                custom_entry.pack(side="left", padx=5)
            else:
                custom_entry.pack_forget()

        strategy_var.trace_add("write", on_strategy_change)

        self._strategy_widgets[name] = (strategy_var, custom_entry)

    def _apply_all(self):
        strategies = {}
        for col_name, (var, custom_entry) in self._strategy_widgets.items():
            strategy = var.get()
            custom_value = custom_entry.get().strip() if strategy == "fill_custom" else None
            # Try to convert custom value to numeric if possible
            if custom_value:
                try:
                    custom_value = float(custom_value)
                except ValueError:
                    pass
            strategies[col_name] = {"strategy": strategy, "custom_value": custom_value}

        # Only apply if at least one non-leave strategy
        active = {k: v for k, v in strategies.items() if v["strategy"] != "leave"}
        if not active:
            self._status_label.configure(
                text="No strategies selected (all set to 'Leave as-is').",
                text_color=WARNING_COLOR,
            )
            return

        self._store.snapshot()
        try:
            new_df = apply_strategies_bulk(self._store.df, strategies)
            self._store.df = new_df

            details = {col: cfg["strategy"] for col, cfg in active.items()}
            self._store.log_operation("missing_values", details)

            self._status_label.configure(
                text=f"Applied {len(active)} strategy(ies). "
                     f"Data: {len(new_df):,} rows × {len(new_df.columns)} cols",
                text_color=SUCCESS_COLOR,
            )
            self._refresh()
        except Exception as e:
            self._store.undo()
            self._status_label.configure(text=f"Error: {e}", text_color="red")

    def _undo(self):
        if self._store.undo():
            self._status_label.configure(text="Undo successful.", text_color=ACCENT_COLOR)
            self._refresh()

    def _proceed(self):
        if self._on_proceed:
            self._on_proceed()
