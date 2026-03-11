"""Treeview-based data table with scrollbars and pagination."""

import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
import pandas as pd

from data_wizard.utils.constants import (
    TABLE_PAGE_SIZE, TABLE_MAX_COLUMN_WIDTH, TABLE_MIN_COLUMN_WIDTH,
    FONT_FAMILY, FONT_SIZE_SM,
)


class DataTable(ctk.CTkFrame):
    """A paginated table widget wrapping ttk.Treeview."""

    def __init__(self, master, page_size: int = TABLE_PAGE_SIZE, **kwargs):
        super().__init__(master, **kwargs)
        self._df: pd.DataFrame = pd.DataFrame()
        self._page_size = page_size
        self._current_page = 0
        self._total_pages = 0

        self._build_ui()

    def _build_ui(self):
        # Table frame
        table_frame = ctk.CTkFrame(self)
        table_frame.pack(fill="both", expand=True)

        # Scrollbars
        self._vsb = ttk.Scrollbar(table_frame, orient="vertical")
        self._hsb = ttk.Scrollbar(table_frame, orient="horizontal")

        self._tree = ttk.Treeview(
            table_frame,
            show="headings",
            yscrollcommand=self._vsb.set,
            xscrollcommand=self._hsb.set,
        )
        self._vsb.config(command=self._tree.yview)
        self._hsb.config(command=self._tree.xview)

        self._vsb.pack(side="right", fill="y")
        self._hsb.pack(side="bottom", fill="x")
        self._tree.pack(fill="both", expand=True)

        # Style
        style = ttk.Style()
        style.configure("Treeview", rowheight=24, font=(FONT_FAMILY, FONT_SIZE_SM))
        style.configure("Treeview.Heading", font=(FONT_FAMILY, FONT_SIZE_SM, "bold"))

        # Pagination bar
        pag_frame = ctk.CTkFrame(self, height=35)
        pag_frame.pack(fill="x", pady=(2, 0))
        pag_frame.pack_propagate(False)

        self._btn_first = ctk.CTkButton(pag_frame, text="<<", width=40, command=self._first_page)
        self._btn_first.pack(side="left", padx=2)
        self._btn_prev = ctk.CTkButton(pag_frame, text="<", width=40, command=self._prev_page)
        self._btn_prev.pack(side="left", padx=2)

        self._page_label = ctk.CTkLabel(pag_frame, text="Page 0 / 0", font=(FONT_FAMILY, FONT_SIZE_SM))
        self._page_label.pack(side="left", padx=10)

        self._btn_next = ctk.CTkButton(pag_frame, text=">", width=40, command=self._next_page)
        self._btn_next.pack(side="left", padx=2)
        self._btn_last = ctk.CTkButton(pag_frame, text=">>", width=40, command=self._last_page)
        self._btn_last.pack(side="left", padx=2)

        self._rows_label = ctk.CTkLabel(pag_frame, text="", font=(FONT_FAMILY, FONT_SIZE_SM))
        self._rows_label.pack(side="right", padx=10)

    def load_dataframe(self, df: pd.DataFrame):
        """Load a DataFrame into the table."""
        self._df = df
        self._current_page = 0
        self._total_pages = max(1, (len(df) - 1) // self._page_size + 1)

        # Configure columns
        cols = list(df.columns)
        self._tree["columns"] = cols
        for col in cols:
            width = min(TABLE_MAX_COLUMN_WIDTH, max(TABLE_MIN_COLUMN_WIDTH, len(str(col)) * 10))
            self._tree.heading(col, text=str(col), anchor="w")
            self._tree.column(col, width=width, minwidth=TABLE_MIN_COLUMN_WIDTH, anchor="w")

        self._render_page()

    def _render_page(self):
        # Clear existing rows
        self._tree.delete(*self._tree.get_children())

        if self._df.empty:
            self._page_label.configure(text="Page 0 / 0")
            self._rows_label.configure(text="0 rows")
            return

        start = self._current_page * self._page_size
        end = min(start + self._page_size, len(self._df))
        page_data = self._df.iloc[start:end]

        for _, row in page_data.iterrows():
            values = [str(v) if pd.notna(v) else "" for v in row]
            self._tree.insert("", "end", values=values)

        self._page_label.configure(
            text=f"Page {self._current_page + 1} / {self._total_pages}"
        )
        self._rows_label.configure(text=f"{len(self._df):,} rows total")

    def _first_page(self):
        self._current_page = 0
        self._render_page()

    def _prev_page(self):
        if self._current_page > 0:
            self._current_page -= 1
            self._render_page()

    def _next_page(self):
        if self._current_page < self._total_pages - 1:
            self._current_page += 1
            self._render_page()

    def _last_page(self):
        self._current_page = self._total_pages - 1
        self._render_page()

    def clear(self):
        self._tree.delete(*self._tree.get_children())
        self._tree["columns"] = []
        self._df = pd.DataFrame()
        self._page_label.configure(text="Page 0 / 0")
        self._rows_label.configure(text="")
