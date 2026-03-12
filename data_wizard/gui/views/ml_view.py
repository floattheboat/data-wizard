"""Step 6: Machine Learning model training and evaluation."""

import threading
import customtkinter as ctk

from data_wizard.utils.constants import (
    FONT_FAMILY, FONT_SIZE_SM, FONT_SIZE_MD, FONT_SIZE_LG,
    ACCENT_COLOR, SUCCESS_COLOR, MUTED_TEXT,
)
from data_wizard.core.data_store import DataStore
from data_wizard.core.ml_runner import infer_task_type, get_algorithms, train_model
from data_wizard.gui.components.chart_frame import ChartFrame
from data_wizard.gui.dialogs.progress_dialog import ProgressDialog


class MLView(ctk.CTkFrame):
    """View for training ML models and displaying results."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._store = DataStore()
        self._current_task_type = None

        self._build_ui()

    def _build_ui(self):
        # Title
        ctk.CTkLabel(
            self, text="Machine Learning",
            font=(FONT_FAMILY, FONT_SIZE_LG, "bold"), anchor="w",
        ).pack(fill="x", padx=20, pady=(15, 5))

        # Controls row
        ctrl_frame = ctk.CTkFrame(self, fg_color="transparent")
        ctrl_frame.pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkLabel(ctrl_frame, text="Target:", font=(FONT_FAMILY, FONT_SIZE_SM)).pack(side="left")
        self._target_var = ctk.StringVar()
        self._target_menu = ctk.CTkOptionMenu(
            ctrl_frame, variable=self._target_var,
            values=["(no data)"], width=180,
            command=self._on_target_change,
        )
        self._target_menu.pack(side="left", padx=(5, 15))

        ctk.CTkLabel(ctrl_frame, text="Algorithm:", font=(FONT_FAMILY, FONT_SIZE_SM)).pack(side="left")
        self._algo_var = ctk.StringVar()
        self._algo_menu = ctk.CTkOptionMenu(
            ctrl_frame, variable=self._algo_var,
            values=["(select target first)"], width=180,
        )
        self._algo_menu.pack(side="left", padx=(5, 15))

        self._btn_train = ctk.CTkButton(
            ctrl_frame, text="Train Model", width=120,
            fg_color=ACCENT_COLOR, command=self._train,
        )
        self._btn_train.pack(side="left", padx=5)

        # Info label
        self._info_label = ctk.CTkLabel(
            self, text="", font=(FONT_FAMILY, FONT_SIZE_SM),
            anchor="w", text_color=MUTED_TEXT,
        )
        self._info_label.pack(fill="x", padx=20, pady=(0, 5))

        # Results area: left = metrics, right = feature importance chart
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=1)
        content.grid_rowconfigure(0, weight=1)

        self._metrics_scroll = ctk.CTkScrollableFrame(content, width=350)
        self._metrics_scroll.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        self._chart = ChartFrame(content, figsize=(5, 4))
        self._chart.grid(row=0, column=1, sticky="nsew")

        # Bottom: proceed button to go back to export
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 15))

        self._btn_export = ctk.CTkButton(
            btn_frame, text="← Back to Export", height=38,
            font=(FONT_FAMILY, FONT_SIZE_MD, "bold"),
            fg_color=SUCCESS_COLOR,
            command=self._go_to_export,
        )
        self._btn_export.pack(side="right")

        # Status label
        self._status_label = ctk.CTkLabel(
            self, text="", font=(FONT_FAMILY, FONT_SIZE_SM),
        )
        self._status_label.pack(pady=(0, 5))

    def activate(self):
        """Populate target dropdown from current DataFrame columns."""
        if not self._store.is_loaded:
            return

        cols = list(self._store.df.columns)
        self._target_menu.configure(values=cols)
        # Default to last column
        self._target_var.set(cols[-1])
        self._on_target_change(cols[-1])

    def _on_target_change(self, _value=None):
        """Update task type and algorithm list when target changes."""
        if not self._store.is_loaded:
            return
        target = self._target_var.get()
        if target not in self._store.df.columns:
            return

        self._current_task_type = infer_task_type(self._store.df[target])
        algos = get_algorithms(self._current_task_type)
        self._algo_menu.configure(values=algos)
        self._algo_var.set(algos[0])

        n_features = len(self._store.df.columns) - 1
        self._info_label.configure(
            text=f"Task type: {self._current_task_type}  |  "
                 f"Features: {n_features}  |  "
                 f"Rows: {len(self._store.df):,}",
        )

    def _train(self):
        """Validate inputs and train model in background thread."""
        if not self._store.is_loaded:
            self._status_label.configure(text="No data loaded.", text_color="red")
            return

        target = self._target_var.get()
        algo = self._algo_var.get()
        task_type = self._current_task_type

        if not target or target not in self._store.df.columns:
            self._status_label.configure(text="Select a valid target column.", text_color="red")
            return
        if not task_type:
            self._status_label.configure(text="Could not determine task type.", text_color="red")
            return

        progress = ProgressDialog(self.winfo_toplevel(), message="Training model...")

        def do_train():
            results = train_model(self._store.df, target, algo, task_type)
            self.after(0, lambda: self._on_train_done(results, progress))

        threading.Thread(target=do_train, daemon=True).start()

    def _on_train_done(self, results: dict, progress):
        """Handle training completion on main thread."""
        progress.close()

        if results.get("error"):
            self._status_label.configure(
                text=f"Training error: {results['error']}", text_color="red",
            )
            return

        self._status_label.configure(
            text=f"Model trained successfully  |  "
                 f"Train: {results['n_train']:,}  Test: {results['n_test']:,}  "
                 f"Rows dropped: {results['rows_dropped']:,}",
            text_color=SUCCESS_COLOR,
        )
        self._display_results(results)

    def _display_results(self, results: dict):
        """Show metrics and feature importance chart."""
        # Clear old metric labels
        for w in self._metrics_scroll.winfo_children():
            w.destroy()

        # Header
        ctk.CTkLabel(
            self._metrics_scroll,
            text=f"{results['algorithm']} ({results['task_type']})",
            font=(FONT_FAMILY, FONT_SIZE_MD, "bold"), anchor="w",
        ).pack(fill="x", pady=(5, 10))

        # Metrics
        for name, value in results["metrics"].items():
            row = ctk.CTkFrame(self._metrics_scroll, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(
                row, text=f"{name.upper()}:",
                font=(FONT_FAMILY, FONT_SIZE_SM, "bold"), anchor="w", width=100,
            ).pack(side="left")
            value_color = MUTED_TEXT if value == "N/A" else None
            value_kwargs = {"text_color": value_color} if value_color else {}
            ctk.CTkLabel(
                row, text=f"{value}",
                font=(FONT_FAMILY, FONT_SIZE_MD), anchor="w",
                **value_kwargs,
            ).pack(side="left", padx=5)

        # Summary info
        ctk.CTkLabel(
            self._metrics_scroll, text="",
            font=(FONT_FAMILY, FONT_SIZE_SM),
        ).pack(pady=5)

        info_lines = [
            f"Target: {results['target_column']}",
            f"Features: {results['n_features']}",
            f"Train samples: {results['n_train']:,}",
            f"Test samples: {results['n_test']:,}",
            f"Rows dropped: {results['rows_dropped']:,}",
        ]
        ctk.CTkLabel(
            self._metrics_scroll,
            text="\n".join(info_lines),
            font=(FONT_FAMILY, FONT_SIZE_SM), text_color=MUTED_TEXT,
            anchor="w", justify="left",
        ).pack(fill="x")

        # Feature importance chart
        fi = results.get("feature_importances")
        if fi:
            names = [name for name, _ in fi[:15]]
            values = [imp for _, imp in fi[:15]]
            self._chart.plot_bar(names, values, title="Feature Importances")
        else:
            self._chart.clear()
            ax = self._chart.figure.add_subplot(111)
            ax.text(
                0.5, 0.5, "Feature importances\nnot available for this algorithm",
                ha="center", va="center", transform=ax.transAxes, fontsize=11,
                color="gray",
            )
            self._chart.draw()

    def _go_to_export(self):
        """Navigate back to export step via parent window."""
        # Walk up to MainWindow and show export step (index 4)
        top = self.winfo_toplevel()
        if hasattr(top, "_show_step"):
            top._show_step(4)
