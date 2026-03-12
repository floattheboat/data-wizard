"""Step 5: Export cleaned data."""

import os
import threading
import customtkinter as ctk
from tkinter import filedialog

from data_wizard.utils.constants import (
    FONT_FAMILY, FONT_SIZE_SM, FONT_SIZE_MD, FONT_SIZE_LG,
    ACCENT_COLOR, SUCCESS_COLOR, MUTED_TEXT,
)
from data_wizard.core.data_store import DataStore
from data_wizard.core.exporter import EXPORT_FORMATS, export_dataframe
from data_wizard.core.db_connector import (
    DB_TYPES, build_connection_url, create_db_engine, test_connection, write_table,
)
from data_wizard.gui.dialogs.db_connect_dialog import DBConnectDialog
from data_wizard.gui.dialogs.progress_dialog import ProgressDialog


class ExportView(ctk.CTkFrame):
    """View for exporting cleaned data to file or database."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._store = DataStore()
        self._db_engine = None

        self._build_ui()

    def _build_ui(self):
        ctk.CTkLabel(
            self, text="Export Data",
            font=(FONT_FAMILY, FONT_SIZE_LG, "bold"), anchor="w",
        ).pack(fill="x", padx=20, pady=(15, 5))

        # Cleaning summary
        self._summary_frame = ctk.CTkFrame(self)
        self._summary_frame.pack(fill="x", padx=20, pady=(0, 15))

        self._summary_label = ctk.CTkLabel(
            self._summary_frame, text="",
            font=(FONT_FAMILY, FONT_SIZE_SM), anchor="w", justify="left",
        )
        self._summary_label.pack(padx=15, pady=10, anchor="w")

        # Export to file section
        file_section = ctk.CTkFrame(self, fg_color="transparent")
        file_section.pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkLabel(
            file_section, text="Export to File",
            font=(FONT_FAMILY, FONT_SIZE_MD, "bold"), anchor="w",
        ).pack(anchor="w", pady=(0, 5))

        fmt_row = ctk.CTkFrame(file_section, fg_color="transparent")
        fmt_row.pack(fill="x")

        ctk.CTkLabel(fmt_row, text="Format:", font=(FONT_FAMILY, FONT_SIZE_SM)).pack(side="left")
        self._fmt_var = ctk.StringVar(value="csv")
        ctk.CTkOptionMenu(
            fmt_row, variable=self._fmt_var,
            values=list(EXPORT_FORMATS.keys()), width=120,
        ).pack(side="left", padx=(5, 15))

        ctk.CTkButton(
            fmt_row, text="Save As...", width=120,
            fg_color=ACCENT_COLOR, command=self._save_file,
        ).pack(side="left")

        # Export to DB section
        db_section = ctk.CTkFrame(self, fg_color="transparent")
        db_section.pack(fill="x", padx=20, pady=(10, 10))

        ctk.CTkLabel(
            db_section, text="Export to Database",
            font=(FONT_FAMILY, FONT_SIZE_MD, "bold"), anchor="w",
        ).pack(anchor="w", pady=(0, 5))

        db_row = ctk.CTkFrame(db_section, fg_color="transparent")
        db_row.pack(fill="x")

        ctk.CTkButton(
            db_row, text="Connect to Database", width=170,
            fg_color="gray50", command=self._connect_db,
        ).pack(side="left", padx=(0, 10))

        ctk.CTkLabel(db_row, text="Table name:", font=(FONT_FAMILY, FONT_SIZE_SM)).pack(side="left")
        self._table_name_entry = ctk.CTkEntry(db_row, placeholder_text="exported_data", width=180)
        self._table_name_entry.pack(side="left", padx=5)

        self._btn_db_export = ctk.CTkButton(
            db_row, text="Export to DB", width=120,
            fg_color=ACCENT_COLOR, state="disabled",
            command=self._export_to_db,
        )
        self._btn_db_export.pack(side="left", padx=5)

        # Status
        self._status_label = ctk.CTkLabel(
            self, text="", font=(FONT_FAMILY, FONT_SIZE_MD),
        )
        self._status_label.pack(pady=20)

    def activate(self):
        """Refresh the cleaning summary."""
        if not self._store.is_loaded:
            return
        summary = self._store.get_summary()

        lines = []
        orig = summary["original_shape"]
        curr = summary["current_shape"]
        lines.append(f"Original: {orig[0]:,} rows × {orig[1]} cols")
        lines.append(f"Current:  {curr[0]:,} rows × {curr[1]} cols")
        if summary["rows_removed"]:
            lines.append(f"Rows removed: {summary['rows_removed']:,}")

        if summary["operations"]:
            lines.append(f"\nOperations performed: {len(summary['operations'])}")
            for i, op in enumerate(summary["operations"], 1):
                op_name = op["operation"].replace("_", " ").title()
                detail_count = len(op.get("details", {}))
                lines.append(f"  {i}. {op_name} ({detail_count} column(s))")

        self._summary_label.configure(text="\n".join(lines))

    def _save_file(self):
        fmt = self._fmt_var.get()
        ext = EXPORT_FORMATS[fmt]["ext"]
        path = filedialog.asksaveasfilename(
            title="Save Data As",
            defaultextension=ext,
            filetypes=[(EXPORT_FORMATS[fmt]["label"], f"*{ext}"), ("All Files", "*.*")],
        )
        if not path:
            return

        progress = ProgressDialog(self.winfo_toplevel(), message="Exporting...")

        def do_export():
            try:
                saved_path = export_dataframe(self._store.df, path, fmt)
                self.after(0, lambda: self._on_export_done(saved_path, progress))
            except Exception as e:
                self.after(0, lambda: self._on_export_error(str(e), progress))

        threading.Thread(target=do_export, daemon=True).start()

    def _on_export_done(self, path, progress):
        progress.close()
        fmt = self._fmt_var.get()
        self._store.audit.record_export(self._store.df, path, fmt)
        self._save_audit_report(path)
        self._status_label.configure(
            text=f"Exported successfully to:\n{path}",
            text_color=SUCCESS_COLOR,
        )

    def _on_export_error(self, error, progress):
        progress.close()
        self._status_label.configure(text=f"Export error: {error}", text_color="red")

    def _connect_db(self):
        dialog = DBConnectDialog(self.winfo_toplevel())
        self.wait_window(dialog)
        if dialog.result:
            self._db_engine = dialog.result["engine"]
            self._btn_db_export.configure(state="normal")
            self._status_label.configure(
                text=f"Connected to {dialog.result['db_type']}: {dialog.result['database']}",
                text_color=SUCCESS_COLOR,
            )

    def _export_to_db(self):
        if not self._db_engine:
            return
        table_name = self._table_name_entry.get().strip() or "exported_data"

        progress = ProgressDialog(self.winfo_toplevel(), message="Exporting to database...")

        def do_export():
            try:
                rows = write_table(self._db_engine, self._store.df, table_name)
                self.after(0, lambda: self._on_db_export_done(table_name, rows, progress))
            except Exception as e:
                self.after(0, lambda: self._on_export_error(str(e), progress))

        threading.Thread(target=do_export, daemon=True).start()

    def _on_db_export_done(self, table_name, rows, progress):
        progress.close()
        self._store.audit.record_export(
            self._store.df, f"database://{table_name}", "database",
            extra={"table_name": table_name, "rows_written": rows},
        )
        self._save_audit_report(table_name)
        self._status_label.configure(
            text=f"Exported {rows:,} rows to table '{table_name}'",
            text_color=SUCCESS_COLOR,
        )

    def _save_audit_report(self, export_path: str):
        """Auto-save audit report and reproduction script alongside exported file."""
        import os
        from data_wizard.core.script_generator import generate_script

        if os.path.isfile(export_path):
            base, _ = os.path.splitext(export_path)
        else:
            base = export_path.replace("://", "_").replace("/", "_")
        json_path = base + "_audit.json"
        txt_path = base + "_audit.txt"
        script_path = base + "_reproduce.py"
        try:
            self._store.audit.save_report(json_path)
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(self._store.audit.format_text_report())
        except Exception:
            pass  # audit save is best-effort
        try:
            generate_script(self._store.audit.events, output_path=script_path)
        except Exception:
            pass  # script generation is best-effort
