"""Step 4: Outlier detection and remediation prompts."""

import customtkinter as ctk
import pandas as pd
import numpy as np

from data_wizard.utils.constants import (
    FONT_FAMILY, FONT_SIZE_SM, FONT_SIZE_MD, FONT_SIZE_LG,
    ACCENT_COLOR, SUCCESS_COLOR, WARNING_COLOR, MUTED_TEXT,
    IQR_MULTIPLIER, ZSCORE_THRESHOLD,
)
from data_wizard.core.data_store import DataStore
from data_wizard.core.outlier_detector import (
    get_outlier_info, REMEDIATION_STRATEGIES, apply_remediations_bulk,
)
from data_wizard.gui.components.chart_frame import ChartFrame


class OutlierView(ctk.CTkFrame):
    """View for outlier detection and remediation."""

    def __init__(self, master, on_proceed=None, **kwargs):
        super().__init__(master, **kwargs)
        self._on_proceed = on_proceed
        self._store = DataStore()
        self._outlier_info = []
        self._remediation_widgets = {}  # col_name -> var

        self._build_ui()

    def _build_ui(self):
        ctk.CTkLabel(
            self, text="Detect & Handle Outliers",
            font=(FONT_FAMILY, FONT_SIZE_LG, "bold"), anchor="w",
        ).pack(fill="x", padx=20, pady=(15, 5))

        # Controls row
        ctrl_frame = ctk.CTkFrame(self, fg_color="transparent")
        ctrl_frame.pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkLabel(ctrl_frame, text="Method:", font=(FONT_FAMILY, FONT_SIZE_SM)).pack(side="left")
        self._method_var = ctk.StringVar(value="iqr")
        ctk.CTkOptionMenu(
            ctrl_frame, variable=self._method_var,
            values=["iqr", "zscore"], width=100,
            command=lambda _: self._detect(),
        ).pack(side="left", padx=(5, 15))

        ctk.CTkLabel(ctrl_frame, text="Threshold:", font=(FONT_FAMILY, FONT_SIZE_SM)).pack(side="left")
        self._threshold_var = ctk.DoubleVar(value=IQR_MULTIPLIER)
        self._threshold_slider = ctk.CTkSlider(
            ctrl_frame, from_=0.5, to=5.0, variable=self._threshold_var,
            width=150, command=self._on_threshold_change,
        )
        self._threshold_slider.pack(side="left", padx=5)
        self._threshold_label = ctk.CTkLabel(
            ctrl_frame, text=f"{IQR_MULTIPLIER:.1f}",
            font=(FONT_FAMILY, FONT_SIZE_SM), width=40,
        )
        self._threshold_label.pack(side="left")

        ctk.CTkButton(
            ctrl_frame, text="Detect", width=80,
            fg_color=ACCENT_COLOR, command=self._detect,
        ).pack(side="left", padx=10)

        self._summary_label = ctk.CTkLabel(
            self, text="", font=(FONT_FAMILY, FONT_SIZE_SM), anchor="w",
        )
        self._summary_label.pack(fill="x", padx=20, pady=(0, 5))

        # Main content: left = column list, right = boxplot
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=1)
        content.grid_rowconfigure(0, weight=1)

        self._scroll = ctk.CTkScrollableFrame(content, width=350)
        self._scroll.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        self._chart = ChartFrame(content, figsize=(5, 4))
        self._chart.grid(row=0, column=1, sticky="nsew")

        # Bottom buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 15))

        self._btn_undo = ctk.CTkButton(
            btn_frame, text="Undo Last", width=100,
            fg_color="gray50", command=self._undo,
        )
        self._btn_undo.pack(side="left", padx=(0, 10))

        self._btn_apply = ctk.CTkButton(
            btn_frame, text="Apply All Remediations", width=200,
            fg_color=ACCENT_COLOR, command=self._apply_all,
        )
        self._btn_apply.pack(side="left", padx=(0, 10))

        self._btn_proceed = ctk.CTkButton(
            btn_frame, text="Proceed to Export  →", height=38,
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
        if not self._store.is_loaded:
            return
        self._detect()

    def _on_threshold_change(self, val):
        self._threshold_label.configure(text=f"{float(val):.1f}")

    def _detect(self):
        method = self._method_var.get()
        threshold = self._threshold_var.get()

        # Update threshold default when switching methods
        if method == "zscore" and threshold == IQR_MULTIPLIER:
            self._threshold_var.set(ZSCORE_THRESHOLD)
            threshold = ZSCORE_THRESHOLD

        self._outlier_info = get_outlier_info(self._store.df, method=method, threshold=threshold)

        # Clear old widgets
        for w in self._scroll.winfo_children():
            w.destroy()
        self._remediation_widgets.clear()

        if not self._outlier_info:
            self._summary_label.configure(
                text="No outliers detected with current settings.",
                text_color=SUCCESS_COLOR,
            )
            self._btn_apply.configure(state="disabled")
            self._chart.clear()
            return

        total_outliers = sum(o["outlier_count"] for o in self._outlier_info)
        self._summary_label.configure(
            text=f"{len(self._outlier_info)} column(s) with outliers  |  "
                 f"{total_outliers:,} total outlier values  |  "
                 f"Method: {method.upper()}, threshold: {threshold:.1f}",
            text_color=WARNING_COLOR,
        )
        self._btn_apply.configure(state="normal")

        for info in self._outlier_info:
            self._add_outlier_row(info)

        # Show first column's boxplot
        if self._outlier_info:
            first_col = self._outlier_info[0]["name"]
            self._chart.plot_boxplot(
                pd.to_numeric(self._store.df[first_col], errors="coerce"),
                title=first_col,
            )

        self._btn_undo.configure(
            state="normal" if self._store.can_undo else "disabled"
        )

    def _add_outlier_row(self, info: dict):
        name = info["name"]
        row = ctk.CTkFrame(self._scroll, corner_radius=6, cursor="hand2")
        row.pack(fill="x", pady=3, padx=2)

        # Click to show boxplot
        row.bind("<Button-1>", lambda e, n=name: self._show_boxplot(n))

        info_frame = ctk.CTkFrame(row, fg_color="transparent")
        info_frame.pack(side="left", fill="x", expand=True, padx=10, pady=8)
        info_frame.bind("<Button-1>", lambda e, n=name: self._show_boxplot(n))

        lbl = ctk.CTkLabel(
            info_frame, text=name,
            font=(FONT_FAMILY, FONT_SIZE_MD, "bold"), anchor="w",
        )
        lbl.pack(anchor="w")
        lbl.bind("<Button-1>", lambda e, n=name: self._show_boxplot(n))

        detail_text = (
            f"Outliers: {info['outlier_count']} ({info['outlier_pct']}%)  |  "
            f"Bounds: [{info['lower_bound']:.2f}, {info['upper_bound']:.2f}]"
        )
        detail = ctk.CTkLabel(
            info_frame, text=detail_text,
            font=(FONT_FAMILY, FONT_SIZE_SM), text_color=MUTED_TEXT, anchor="w",
        )
        detail.pack(anchor="w")
        detail.bind("<Button-1>", lambda e, n=name: self._show_boxplot(n))

        # Remediation picker
        rem_var = ctk.StringVar(value="leave")
        ctk.CTkOptionMenu(
            row, variable=rem_var,
            values=list(REMEDIATION_STRATEGIES.keys()),
            width=160,
        ).pack(side="right", padx=10, pady=8)

        self._remediation_widgets[name] = rem_var

    def _show_boxplot(self, col_name: str):
        self._chart.plot_boxplot(
            pd.to_numeric(self._store.df[col_name], errors="coerce"),
            title=col_name,
        )

    def _apply_all(self):
        method = self._method_var.get()
        threshold = self._threshold_var.get()

        remediations = {}
        for col_name, var in self._remediation_widgets.items():
            strategy = var.get()
            if strategy != "leave":
                remediations[col_name] = {
                    "strategy": strategy,
                    "method": method,
                    "threshold": threshold,
                }

        if not remediations:
            self._status_label.configure(
                text="No remediations selected (all set to 'Leave as-is').",
                text_color=WARNING_COLOR,
            )
            return

        self._store.snapshot()
        try:
            new_df = apply_remediations_bulk(self._store.df, remediations)
            self._store.df = new_df

            details = {col: cfg["strategy"] for col, cfg in remediations.items()}
            self._store.log_operation("outlier_remediation", details)

            self._status_label.configure(
                text=f"Applied {len(remediations)} remediation(s). "
                     f"Data: {len(new_df):,} rows × {len(new_df.columns)} cols",
                text_color=SUCCESS_COLOR,
            )
            self._detect()
        except Exception as e:
            self._store.undo()
            self._status_label.configure(text=f"Error: {e}", text_color="red")

    def _undo(self):
        if self._store.undo():
            self._status_label.configure(text="Undo successful.", text_color=ACCENT_COLOR)
            self._detect()

    def _proceed(self):
        if self._on_proceed:
            self._on_proceed()
