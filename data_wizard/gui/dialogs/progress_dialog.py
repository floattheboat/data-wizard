"""Loading/processing progress dialog."""

import customtkinter as ctk
from data_wizard.utils.constants import FONT_FAMILY, FONT_SIZE_MD


class ProgressDialog(ctk.CTkToplevel):
    """Modal progress dialog for long-running operations."""

    def __init__(self, master, title: str = "Processing...", message: str = "Please wait..."):
        super().__init__(master)
        self.title(title)
        self.geometry("350x130")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        x = master.winfo_rootx() + (master.winfo_width() - 350) // 2
        y = master.winfo_rooty() + (master.winfo_height() - 130) // 2
        self.geometry(f"+{x}+{y}")

        self._label = ctk.CTkLabel(self, text=message, font=(FONT_FAMILY, FONT_SIZE_MD))
        self._label.pack(pady=(20, 10))

        self._progress = ctk.CTkProgressBar(self, width=280)
        self._progress.pack(pady=5)
        self._progress.set(0)
        self._progress.configure(mode="indeterminate")
        self._progress.start()

    def set_message(self, msg: str):
        self._label.configure(text=msg)

    def close(self):
        self._progress.stop()
        self.grab_release()
        self.destroy()
