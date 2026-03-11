"""Step 2: Exploratory stats + charts per column."""

import threading
import customtkinter as ctk
import pandas as pd

from data_wizard.utils.constants import (
    FONT_FAMILY, FONT_SIZE_SM, FONT_SIZE_MD, FONT_SIZE_LG,
    ACCENT_COLOR, MUTED_TEXT, SUCCESS_COLOR,
)
from data_wizard.core.data_store import DataStore
from data_wizard.core.analyzer import analyze_dataframe, compute_correlation
from data_wizard.gui.components.column_card import ColumnCard
from data_wizard.gui.components.chart_frame import ChartFrame
from data_wizard.gui.dialogs.progress_dialog import ProgressDialog


class ExploreView(ctk.CTkFrame):
    """View for exploratory analysis — column stats and charts."""

    def __init__(self, master, on_proceed=None, **kwargs):
        super().__init__(master, **kwargs)
        self._on_proceed = on_proceed
        self._store = DataStore()
        self._analysis = None
        self._col_cards = []
        self._selected_col = None

        self._build_ui()

    def _build_ui(self):
        # Title
        title = ctk.CTkLabel(
            self, text="Explore Data",
            font=(FONT_FAMILY, FONT_SIZE_LG, "bold"), anchor="w",
        )
        title.pack(fill="x", padx=20, pady=(15, 5))

        self._overview_label = ctk.CTkLabel(
            self, text="", font=(FONT_FAMILY, FONT_SIZE_SM), anchor="w",
        )
        self._overview_label.pack(fill="x", padx=20, pady=(0, 10))

        # Main content: left = scrollable cards, right = chart
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=2)
        content.grid_rowconfigure(0, weight=1)

        # Left: scrollable column list
        self._scroll = ctk.CTkScrollableFrame(content, width=300)
        self._scroll.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # Right: chart area
        chart_panel = ctk.CTkFrame(content)
        chart_panel.grid(row=0, column=1, sticky="nsew")
        chart_panel.grid_rowconfigure(1, weight=1)
        chart_panel.grid_columnconfigure(0, weight=1)

        # Chart type buttons
        chart_btn_row = ctk.CTkFrame(chart_panel, fg_color="transparent")
        chart_btn_row.grid(row=0, column=0, sticky="ew", padx=10, pady=5)

        self._chart_type_var = ctk.StringVar(value="histogram")
        for text_val, val in [("Histogram", "histogram"), ("Box Plot", "boxplot"),
                               ("Bar Chart", "bar"), ("Correlation", "correlation")]:
            ctk.CTkRadioButton(
                chart_btn_row, text=text_val, variable=self._chart_type_var,
                value=val, command=self._update_chart,
                font=(FONT_FAMILY, FONT_SIZE_SM),
            ).pack(side="left", padx=8)

        self._chart = ChartFrame(chart_panel, figsize=(6, 4))
        self._chart.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        self._chart_info = ctk.CTkLabel(
            chart_panel, text="Click a column card to view its distribution",
            font=(FONT_FAMILY, FONT_SIZE_SM), text_color=MUTED_TEXT,
        )
        self._chart_info.grid(row=2, column=0, pady=5)

        # Proceed button
        self._btn_proceed = ctk.CTkButton(
            self, text="Proceed to Missing Values  →", height=38,
            font=(FONT_FAMILY, FONT_SIZE_MD, "bold"),
            fg_color=SUCCESS_COLOR,
            command=self._proceed,
        )
        self._btn_proceed.pack(pady=(0, 15))

    def activate(self):
        """Called when this view becomes visible. Run analysis."""
        if not self._store.is_loaded:
            return

        progress = ProgressDialog(self.winfo_toplevel(), message="Analyzing data...")

        def do_analyze():
            analysis = analyze_dataframe(self._store.df)
            self.after(0, lambda: self._on_analysis_done(analysis, progress))

        threading.Thread(target=do_analyze, daemon=True).start()

    def _on_analysis_done(self, analysis, progress):
        progress.close()
        self._analysis = analysis

        # Overview
        ov = analysis["overview"]
        self._overview_label.configure(
            text=f"{ov['rows']:,} rows × {ov['cols']} cols  |  "
                 f"Missing: {ov['total_missing']:,} ({ov['missing_pct']}%)  |  "
                 f"Memory: {ov['memory_mb']:.1f} MB"
        )

        # Build column cards
        for w in self._scroll.winfo_children():
            w.destroy()
        self._col_cards.clear()

        for col_stats in analysis["columns"]:
            card = ColumnCard(self._scroll, col_stats, on_click=self._on_card_click)
            card.pack(fill="x", padx=5, pady=3)
            self._col_cards.append(card)

    def _on_card_click(self, col_stats):
        self._selected_col = col_stats

        # Highlight selected
        for card in self._col_cards:
            card.set_selected(card._col_stats["name"] == col_stats["name"])

        self._chart_info.configure(text=f"Showing: {col_stats['name']}")
        self._update_chart()

    def _update_chart(self):
        if self._selected_col is None:
            return

        col_stats = self._selected_col
        chart_type = self._chart_type_var.get()
        col_name = col_stats["name"]
        series = self._store.df[col_name]

        if chart_type == "correlation":
            corr = compute_correlation(self._store.df)
            if corr is not None:
                self._chart.plot_heatmap(corr)
            else:
                self._chart.clear()
            return

        col_type = col_stats["inferred_type"]

        if chart_type == "histogram":
            if col_type == "numeric":
                self._chart.plot_histogram(pd.to_numeric(series, errors="coerce"), title=col_name)
            elif col_type in ("categorical", "text", "boolean"):
                vc = series.value_counts().head(15)
                self._chart.plot_bar(vc.index, vc.values, title=col_name)
            else:
                self._chart.clear()

        elif chart_type == "boxplot":
            if col_type == "numeric":
                self._chart.plot_boxplot(pd.to_numeric(series, errors="coerce"), title=col_name)
            else:
                self._chart.clear()

        elif chart_type == "bar":
            vc = series.value_counts().head(15)
            self._chart.plot_bar(vc.index, vc.values, title=col_name)

    def _proceed(self):
        if self._on_proceed:
            self._on_proceed()
