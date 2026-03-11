"""Step 1: File/DB picker + preview table."""

import os
import threading
import customtkinter as ctk
from tkinter import filedialog

from data_wizard.utils.constants import (
    FONT_FAMILY, FONT_SIZE_SM, FONT_SIZE_MD, FONT_SIZE_LG,
    ACCENT_COLOR, SUCCESS_COLOR, WARNING_COLOR, DANGER_COLOR,
    LARGE_DATASET_ROWS, DEFAULT_ROW_LIMIT,
)
from data_wizard.core.loader import load_file, get_file_filter
from data_wizard.core.data_store import DataStore
from data_wizard.core.db_connector import load_table
from data_wizard.gui.components.data_table import DataTable
from data_wizard.gui.dialogs.db_connect_dialog import DBConnectDialog
from data_wizard.gui.dialogs.progress_dialog import ProgressDialog


class LoadView(ctk.CTkFrame):
    """View for loading data from files or databases."""

    def __init__(self, master, on_proceed=None, **kwargs):
        super().__init__(master, **kwargs)
        self._on_proceed = on_proceed
        self._store = DataStore()
        self._db_engine = None
        self._db_tables = []

        self._build_ui()

    def _build_ui(self):
        # Title
        title = ctk.CTkLabel(
            self, text="Load Data",
            font=(FONT_FAMILY, FONT_SIZE_LG, "bold"), anchor="w",
        )
        title.pack(fill="x", padx=20, pady=(15, 5))

        desc = ctk.CTkLabel(
            self,
            text="Choose a file or connect to a database to load your dataset.",
            font=(FONT_FAMILY, FONT_SIZE_SM), anchor="w",
        )
        desc.pack(fill="x", padx=20, pady=(0, 10))

        # Source buttons row
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=5)

        self._btn_file = ctk.CTkButton(
            btn_row, text="Open File", width=130,
            fg_color=ACCENT_COLOR, command=self._open_file,
        )
        self._btn_file.pack(side="left", padx=(0, 10))

        self._btn_db = ctk.CTkButton(
            btn_row, text="Connect to Database", width=170,
            fg_color="gray50", command=self._open_db_dialog,
        )
        self._btn_db.pack(side="left", padx=(0, 10))

        # DB table selector (hidden initially)
        self._db_frame = ctk.CTkFrame(self, fg_color="transparent")

        ctk.CTkLabel(self._db_frame, text="Table:", font=(FONT_FAMILY, FONT_SIZE_SM)).pack(side="left", padx=(0, 5))
        self._table_var = ctk.StringVar()
        self._table_menu = ctk.CTkOptionMenu(self._db_frame, variable=self._table_var, values=[""])
        self._table_menu.pack(side="left", padx=(0, 10))
        ctk.CTkButton(self._db_frame, text="Load Table", width=100, command=self._load_db_table).pack(side="left")

        # File info label
        self._info_label = ctk.CTkLabel(
            self, text="", font=(FONT_FAMILY, FONT_SIZE_SM), anchor="w",
        )
        self._info_label.pack(fill="x", padx=20, pady=(5, 0))

        # Preview table
        self._table = DataTable(self)
        self._table.pack(fill="both", expand=True, padx=20, pady=10)

        # Proceed button
        self._btn_proceed = ctk.CTkButton(
            self, text="Proceed to Explore  →", height=38,
            font=(FONT_FAMILY, FONT_SIZE_MD, "bold"),
            fg_color=SUCCESS_COLOR, state="disabled",
            command=self._proceed,
        )
        self._btn_proceed.pack(pady=(0, 15))

    def _open_file(self):
        filetypes = get_file_filter()
        # Convert to tk format
        tk_filetypes = [(label, pattern) for label, pattern in filetypes]
        path = filedialog.askopenfilename(
            title="Select Data File",
            filetypes=tk_filetypes,
        )
        if not path:
            return

        # Show progress
        progress = ProgressDialog(self.winfo_toplevel(), message=f"Loading {os.path.basename(path)}...")

        def do_load():
            try:
                df, info = load_file(path)
                total_rows = len(df)

                # Large dataset warning
                if total_rows > LARGE_DATASET_ROWS:
                    # Load limited
                    df, info = load_file(path, row_limit=DEFAULT_ROW_LIMIT)
                    info["limited"] = True
                    info["original_total_rows"] = total_rows

                self.after(0, lambda: self._on_file_loaded(df, info, progress))
            except Exception as e:
                self.after(0, lambda: self._on_load_error(str(e), progress))

        threading.Thread(target=do_load, daemon=True).start()

    def _on_file_loaded(self, df, info, progress):
        progress.close()
        self._store.load(df, info)
        self._table.load_dataframe(df)

        # Info text
        text = f"Loaded: {info.get('filename', '?')}  |  {len(df):,} rows × {len(df.columns)} cols"
        if info.get("limited"):
            text += f"  (limited from {info.get('original_total_rows', '?'):,} rows)"
        self._info_label.configure(text=text, text_color=SUCCESS_COLOR)
        self._btn_proceed.configure(state="normal")

    def _on_load_error(self, error_msg, progress):
        progress.close()
        self._info_label.configure(text=f"Error: {error_msg}", text_color=DANGER_COLOR)

    def _open_db_dialog(self):
        dialog = DBConnectDialog(self.winfo_toplevel())
        self.wait_window(dialog)

        if dialog.result:
            self._db_engine = dialog.result["engine"]
            self._db_tables = dialog.result["tables"]
            if self._db_tables:
                self._table_var.set(self._db_tables[0])
                self._table_menu.configure(values=self._db_tables)
                self._db_frame.pack(fill="x", padx=20, pady=5, after=self._info_label)
                self._info_label.configure(
                    text=f"Connected to {dialog.result['db_type']}: {dialog.result['database']}",
                    text_color=SUCCESS_COLOR,
                )
            else:
                self._info_label.configure(text="Connected but no tables found.", text_color=WARNING_COLOR)

    def _load_db_table(self):
        if not self._db_engine:
            return
        table_name = self._table_var.get()
        if not table_name:
            return

        progress = ProgressDialog(self.winfo_toplevel(), message=f"Loading table '{table_name}'...")

        def do_load():
            try:
                df = load_table(self._db_engine, table_name)
                info = {
                    "type": "database",
                    "table_name": table_name,
                    "total_rows": len(df),
                    "total_cols": len(df.columns),
                }

                if len(df) > LARGE_DATASET_ROWS:
                    df = load_table(self._db_engine, table_name, row_limit=DEFAULT_ROW_LIMIT)
                    info["limited"] = True
                    info["original_total_rows"] = info["total_rows"]
                    info["total_rows"] = len(df)

                self.after(0, lambda: self._on_file_loaded(df, info, progress))
            except Exception as e:
                self.after(0, lambda: self._on_load_error(str(e), progress))

        threading.Thread(target=do_load, daemon=True).start()

    def _proceed(self):
        if self._on_proceed and self._store.is_loaded:
            self._on_proceed()
