"""Database connection dialog."""

import customtkinter as ctk
from typing import Optional, Dict, Any

from data_wizard.utils.constants import FONT_FAMILY, FONT_SIZE_SM, FONT_SIZE_MD, ACCENT_COLOR, SUCCESS_COLOR, DANGER_COLOR
from data_wizard.core.db_connector import DB_TYPES, build_connection_url, create_db_engine, test_connection, list_tables


class DBConnectDialog(ctk.CTkToplevel):
    """Modal dialog for database connection configuration."""

    def __init__(self, master):
        super().__init__(master)
        self.title("Connect to Database")
        self.geometry("480x520")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self.result: Optional[Dict[str, Any]] = None
        self._engine = None

        self._build_ui()

        # Center
        self.update_idletasks()
        x = master.winfo_rootx() + (master.winfo_width() - 480) // 2
        y = master.winfo_rooty() + (master.winfo_height() - 520) // 2
        self.geometry(f"+{x}+{y}")

    def _build_ui(self):
        pad = {"padx": 15, "pady": (5, 2)}

        # DB Type
        ctk.CTkLabel(self, text="Database Type", font=(FONT_FAMILY, FONT_SIZE_SM)).pack(**pad, anchor="w")
        self._db_type_var = ctk.StringVar(value="sqlite")
        self._db_type_menu = ctk.CTkOptionMenu(
            self, variable=self._db_type_var,
            values=list(DB_TYPES.keys()),
            command=self._on_db_type_change,
        )
        self._db_type_menu.pack(padx=15, pady=(0, 5), fill="x")

        # Database / file path
        ctk.CTkLabel(self, text="Database / File Path", font=(FONT_FAMILY, FONT_SIZE_SM)).pack(**pad, anchor="w")
        self._db_entry = ctk.CTkEntry(self, placeholder_text="path/to/database.db")
        self._db_entry.pack(padx=15, fill="x")

        # Host / Port frame
        self._host_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._host_frame.pack(padx=15, fill="x", pady=(5, 0))

        ctk.CTkLabel(self._host_frame, text="Host", font=(FONT_FAMILY, FONT_SIZE_SM)).grid(row=0, column=0, sticky="w")
        self._host_entry = ctk.CTkEntry(self._host_frame, placeholder_text="localhost", width=250)
        self._host_entry.grid(row=1, column=0, padx=(0, 10))

        ctk.CTkLabel(self._host_frame, text="Port", font=(FONT_FAMILY, FONT_SIZE_SM)).grid(row=0, column=1, sticky="w")
        self._port_entry = ctk.CTkEntry(self._host_frame, placeholder_text="5432", width=80)
        self._port_entry.grid(row=1, column=1)

        # Username / Password
        ctk.CTkLabel(self, text="Username", font=(FONT_FAMILY, FONT_SIZE_SM)).pack(**pad, anchor="w")
        self._user_entry = ctk.CTkEntry(self, placeholder_text="username")
        self._user_entry.pack(padx=15, fill="x")

        ctk.CTkLabel(self, text="Password", font=(FONT_FAMILY, FONT_SIZE_SM)).pack(**pad, anchor="w")
        self._pass_entry = ctk.CTkEntry(self, placeholder_text="password", show="*")
        self._pass_entry.pack(padx=15, fill="x")

        # Status label
        self._status = ctk.CTkLabel(self, text="", font=(FONT_FAMILY, FONT_SIZE_SM))
        self._status.pack(pady=(10, 5))

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=10)

        ctk.CTkButton(btn_frame, text="Test Connection", width=140, command=self._test).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Connect", width=140, fg_color=ACCENT_COLOR, command=self._connect).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Cancel", width=80, fg_color="gray50", command=self._cancel).pack(side="left", padx=5)

        # Initial state: hide host fields for SQLite
        self._on_db_type_change("sqlite")

    def _on_db_type_change(self, db_type: str):
        needs_host = DB_TYPES.get(db_type, {}).get("needs_host", True)
        if needs_host:
            self._host_frame.pack(padx=15, fill="x", pady=(5, 0))
        else:
            self._host_frame.pack_forget()

    def _get_connection_url(self) -> str:
        db_type = self._db_type_var.get()
        database = self._db_entry.get().strip()
        host = self._host_entry.get().strip() or "localhost"
        port_str = self._port_entry.get().strip()
        port = int(port_str) if port_str else None
        username = self._user_entry.get().strip()
        password = self._pass_entry.get().strip()
        return build_connection_url(db_type, database, host, port, username, password)

    def _test(self):
        try:
            url = self._get_connection_url()
            engine = create_db_engine(url)
            if test_connection(engine):
                tables = list_tables(engine)
                self._status.configure(
                    text=f"Connected! {len(tables)} table(s) found.",
                    text_color=SUCCESS_COLOR,
                )
                self._engine = engine
            else:
                self._status.configure(text="Connection failed.", text_color=DANGER_COLOR)
        except Exception as e:
            self._status.configure(text=f"Error: {e}", text_color=DANGER_COLOR)

    def _connect(self):
        try:
            if self._engine is None:
                url = self._get_connection_url()
                self._engine = create_db_engine(url)
            if test_connection(self._engine):
                tables = list_tables(self._engine)
                self.result = {
                    "engine": self._engine,
                    "tables": tables,
                    "db_type": self._db_type_var.get(),
                    "database": self._db_entry.get().strip(),
                }
                self.grab_release()
                self.destroy()
            else:
                self._status.configure(text="Connection failed.", text_color=DANGER_COLOR)
        except Exception as e:
            self._status.configure(text=f"Error: {e}", text_color=DANGER_COLOR)

    def _cancel(self):
        self.result = None
        self.grab_release()
        self.destroy()
