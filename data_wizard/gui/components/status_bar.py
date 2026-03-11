"""Bottom status bar showing current step, row/col count, and memory."""

import customtkinter as ctk

from data_wizard.utils.constants import FONT_FAMILY, FONT_SIZE_SM, MUTED_TEXT


class StatusBar(ctk.CTkFrame):
    """Fixed bottom bar with status information."""

    def __init__(self, master, **kwargs):
        super().__init__(master, height=30, **kwargs)
        self.pack_propagate(False)

        self._step_label = ctk.CTkLabel(
            self, text="Step: -", font=(FONT_FAMILY, FONT_SIZE_SM),
            text_color=MUTED_TEXT, anchor="w",
        )
        self._step_label.pack(side="left", padx=10)

        self._info_label = ctk.CTkLabel(
            self, text="No data loaded", font=(FONT_FAMILY, FONT_SIZE_SM),
            text_color=MUTED_TEXT, anchor="e",
        )
        self._info_label.pack(side="right", padx=10)

    def set_step(self, step_text: str):
        self._step_label.configure(text=f"Step: {step_text}")

    def set_data_info(self, rows: int, cols: int, memory_mb: float = 0):
        text = f"{rows:,} rows  ×  {cols} cols"
        if memory_mb > 0:
            text += f"  |  {memory_mb:.1f} MB"
        self._info_label.configure(text=text)

    def clear(self):
        self._step_label.configure(text="Step: -")
        self._info_label.configure(text="No data loaded")
