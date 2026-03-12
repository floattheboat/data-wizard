"""Main window with sidebar navigation and view swapping."""

import customtkinter as ctk

from data_wizard.utils.constants import (
    WINDOW_TITLE, WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT,
    WINDOW_DEFAULT_GEOMETRY, SIDEBAR_WIDTH, SIDEBAR_PAD,
    FONT_FAMILY, FONT_SIZE_SM, FONT_SIZE_MD, FONT_SIZE_LG,
    ACCENT_COLOR, ACCENT_HOVER, MUTED_TEXT, STEPS,
)
from data_wizard.core.data_store import DataStore
from data_wizard.gui.components.status_bar import StatusBar
from data_wizard.gui.views.load_view import LoadView
from data_wizard.gui.views.explore_view import ExploreView
from data_wizard.gui.views.missing_view import MissingView
from data_wizard.gui.views.outlier_view import OutlierView
from data_wizard.gui.views.export_view import ExportView
from data_wizard.gui.views.ml_view import MLView


class MainWindow(ctk.CTk):
    """Application main window with wizard-step sidebar navigation."""

    def __init__(self):
        super().__init__()
        self.title(WINDOW_TITLE)
        self.geometry(WINDOW_DEFAULT_GEOMETRY)
        self.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

        self._store = DataStore()
        self._current_step = 0
        self._max_unlocked = 0  # Furthest step reached

        self._build_layout()
        self._create_views()
        self._bind_shortcuts()
        self._show_step(0)

    def _build_layout(self):
        # Sidebar
        self._sidebar = ctk.CTkFrame(self, width=SIDEBAR_WIDTH, corner_radius=0)
        self._sidebar.pack(side="left", fill="y")
        self._sidebar.pack_propagate(False)

        # App title in sidebar
        ctk.CTkLabel(
            self._sidebar, text="Data Wizard",
            font=(FONT_FAMILY, FONT_SIZE_LG, "bold"),
        ).pack(padx=SIDEBAR_PAD, pady=(20, 5))

        ctk.CTkLabel(
            self._sidebar, text="Interactive Data Cleaning",
            font=(FONT_FAMILY, FONT_SIZE_SM), text_color=MUTED_TEXT,
        ).pack(padx=SIDEBAR_PAD, pady=(0, 20))

        # Step buttons
        self._step_buttons = []
        for i, step in enumerate(STEPS):
            btn = ctk.CTkButton(
                self._sidebar,
                text=f"  {step['label']}",
                font=(FONT_FAMILY, FONT_SIZE_MD),
                anchor="w",
                height=40,
                fg_color="transparent",
                text_color=("gray30", "gray70"),
                hover_color=("gray85", "gray25"),
                command=lambda idx=i: self._on_step_click(idx),
            )
            btn.pack(fill="x", padx=SIDEBAR_PAD, pady=2)
            self._step_buttons.append(btn)

        # Theme toggle at bottom of sidebar
        spacer = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        spacer.pack(fill="both", expand=True)

        self._theme_var = ctk.StringVar(value="dark")
        theme_frame = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        theme_frame.pack(padx=SIDEBAR_PAD, pady=(5, 15))

        ctk.CTkLabel(theme_frame, text="Theme:", font=(FONT_FAMILY, FONT_SIZE_SM)).pack(side="left", padx=(0, 5))
        ctk.CTkSwitch(
            theme_frame, text="Dark", variable=self._theme_var,
            onvalue="dark", offvalue="light",
            command=self._toggle_theme,
            font=(FONT_FAMILY, FONT_SIZE_SM),
        ).pack(side="left")

        # Main content area
        self._content = ctk.CTkFrame(self, corner_radius=0)
        self._content.pack(side="left", fill="both", expand=True)

        # Status bar
        self._status_bar = StatusBar(self)
        self._status_bar.pack(side="bottom", fill="x")

    def _create_views(self):
        self._views = {
            "load": LoadView(self._content, on_proceed=lambda: self._advance_to(1)),
            "explore": ExploreView(self._content, on_proceed=lambda: self._advance_to(2)),
            "missing": MissingView(self._content, on_proceed=lambda: self._advance_to(3)),
            "outlier": OutlierView(self._content, on_proceed=lambda: self._advance_to(4)),
            "export": ExportView(self._content, on_proceed=lambda: self._advance_to(5)),
            "ml": MLView(self._content),
        }

        # Register data change callback for status bar updates
        self._store.on_change(self._update_status_bar)

    def _show_step(self, idx: int):
        """Show the view for step idx, hide all others."""
        self._current_step = idx
        step_key = STEPS[idx]["key"]

        for key, view in self._views.items():
            if key == step_key:
                view.pack(fill="both", expand=True)
            else:
                view.pack_forget()

        # Update sidebar button styles
        for i, btn in enumerate(self._step_buttons):
            if i == idx:
                btn.configure(fg_color=ACCENT_COLOR, text_color="white")
            elif i <= self._max_unlocked:
                btn.configure(fg_color="transparent", text_color=("gray10", "gray90"))
            else:
                btn.configure(fg_color="transparent", text_color=MUTED_TEXT)

        self._status_bar.set_step(STEPS[idx]["label"])

        # Activate views that need refresh
        view = self._views[step_key]
        if hasattr(view, "activate"):
            view.activate()

    def _on_step_click(self, idx: int):
        """Handle sidebar button click — only allow if step is unlocked."""
        if idx <= self._max_unlocked:
            self._show_step(idx)

    def _advance_to(self, idx: int):
        """Advance to a specific step (used by proceed buttons)."""
        self._max_unlocked = max(self._max_unlocked, idx)
        self._show_step(idx)

    def _update_status_bar(self):
        if self._store.is_loaded:
            rows, cols = self._store.shape
            mem = self._store.df.memory_usage(deep=True).sum() / 1024 / 1024
            self._status_bar.set_data_info(rows, cols, mem)

    def _toggle_theme(self):
        mode = self._theme_var.get()
        ctk.set_appearance_mode(mode)

    def _bind_shortcuts(self):
        self.bind("<Control-o>", lambda e: self._views["load"]._open_file())
        self.bind("<Control-z>", lambda e: self._handle_undo())
        self.bind("<Control-s>", lambda e: self._handle_save())

    def _handle_undo(self):
        if self._store.can_undo:
            self._store.undo()
            # Refresh current view
            step_key = STEPS[self._current_step]["key"]
            view = self._views[step_key]
            if hasattr(view, "activate"):
                view.activate()

    def _handle_save(self):
        # Switch to export view if data is loaded
        if self._store.is_loaded:
            self._max_unlocked = max(self._max_unlocked, 4)
            self._show_step(4)
