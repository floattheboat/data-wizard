"""Per-column summary widget card."""

import customtkinter as ctk

from data_wizard.utils.constants import (
    FONT_FAMILY, FONT_SIZE_SM, FONT_SIZE_MD,
    ACCENT_COLOR, WARNING_COLOR, MUTED_TEXT,
)


class ColumnCard(ctk.CTkFrame):
    """Compact summary card for a single column's stats."""

    def __init__(self, master, col_stats: dict, on_click=None, **kwargs):
        super().__init__(master, corner_radius=8, border_width=1, **kwargs)
        self._col_stats = col_stats
        self._on_click = on_click
        self._selected = False

        self.configure(cursor="hand2")
        self.bind("<Button-1>", self._handle_click)

        self._build_ui()

    def _build_ui(self):
        stats = self._col_stats
        name = stats.get("name", "?")
        col_type = stats.get("inferred_type", "?")
        missing_pct = stats.get("missing_pct", 0)

        # Header row
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=8, pady=(6, 2))
        header.bind("<Button-1>", self._handle_click)

        name_label = ctk.CTkLabel(
            header, text=name, font=(FONT_FAMILY, FONT_SIZE_MD, "bold"),
            anchor="w",
        )
        name_label.pack(side="left", fill="x", expand=True)
        name_label.bind("<Button-1>", self._handle_click)

        type_label = ctk.CTkLabel(
            header, text=col_type,
            font=(FONT_FAMILY, FONT_SIZE_SM),
            text_color=ACCENT_COLOR,
        )
        type_label.pack(side="right")
        type_label.bind("<Button-1>", self._handle_click)

        # Stats lines
        lines = []
        lines.append(f"Unique: {stats.get('unique', '-')}")

        if missing_pct > 0:
            lines.append(f"Missing: {stats.get('missing', 0)} ({missing_pct}%)")
        else:
            lines.append("Missing: 0")

        if col_type == "numeric":
            mean = stats.get("mean")
            std = stats.get("std")
            if mean is not None:
                lines.append(f"Mean: {mean:.4g}  Std: {std:.4g}" if std else f"Mean: {mean:.4g}")
            mi, ma = stats.get("min"), stats.get("max")
            if mi is not None:
                lines.append(f"Range: [{mi:.4g}, {ma:.4g}]")
        elif col_type in ("categorical", "text", "boolean"):
            mc = stats.get("most_common")
            if mc:
                lines.append(f"Top: {mc} ({stats.get('most_common_count', '')})")
        elif col_type == "datetime":
            lines.append(f"{stats.get('min_date', '?')} → {stats.get('max_date', '?')}")

        stats_text = "\n".join(lines)
        missing_color = WARNING_COLOR if missing_pct > 5 else MUTED_TEXT

        body = ctk.CTkLabel(
            self, text=stats_text, font=(FONT_FAMILY, FONT_SIZE_SM),
            text_color=MUTED_TEXT, anchor="w", justify="left",
        )
        body.pack(fill="x", padx=8, pady=(0, 6))
        body.bind("<Button-1>", self._handle_click)

    def _handle_click(self, event=None):
        if self._on_click:
            self._on_click(self._col_stats)

    def set_selected(self, selected: bool):
        self._selected = selected
        if selected:
            self.configure(border_color=ACCENT_COLOR)
        else:
            self.configure(border_color=("gray70", "gray30"))
