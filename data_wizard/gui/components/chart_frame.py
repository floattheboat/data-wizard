"""Matplotlib canvas wrapper for embedding charts in CustomTkinter."""

import customtkinter as ctk
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np
import pandas as pd
from typing import Optional


class ChartFrame(ctk.CTkFrame):
    """A frame that embeds a Matplotlib figure."""

    def __init__(self, master, figsize=(6, 4), **kwargs):
        super().__init__(master, **kwargs)
        self._figsize = figsize
        self._figure: Optional[Figure] = None
        self._canvas: Optional[FigureCanvasTkAgg] = None
        self._create_figure()

    def _create_figure(self):
        if self._canvas:
            self._canvas.get_tk_widget().destroy()

        self._figure = Figure(figsize=self._figsize, dpi=100)
        self._figure.patch.set_alpha(0)
        self._canvas = FigureCanvasTkAgg(self._figure, master=self)
        self._canvas.get_tk_widget().pack(fill="both", expand=True)

    def clear(self):
        self._figure.clear()
        self._canvas.draw()

    @property
    def figure(self) -> Figure:
        return self._figure

    def draw(self):
        self._figure.tight_layout()
        self._canvas.draw()

    def plot_histogram(self, data: pd.Series, title: str = "", bins: int = 30):
        """Plot a histogram of numeric data."""
        self._figure.clear()
        ax = self._figure.add_subplot(111)
        clean = data.dropna()
        if len(clean) == 0:
            ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        else:
            ax.hist(clean, bins=bins, color="#3B82F6", edgecolor="#1E3A5F", alpha=0.85)
            ax.set_title(title, fontsize=11)
            ax.set_ylabel("Frequency")
        self.draw()

    def plot_boxplot(self, data: pd.Series, title: str = ""):
        """Plot a box plot of numeric data."""
        self._figure.clear()
        ax = self._figure.add_subplot(111)
        clean = data.dropna()
        if len(clean) == 0:
            ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        else:
            bp = ax.boxplot(clean, vert=True, patch_artist=True)
            for patch in bp["boxes"]:
                patch.set_facecolor("#3B82F6")
                patch.set_alpha(0.7)
            ax.set_title(title, fontsize=11)
        self.draw()

    def plot_bar(self, categories, values, title: str = "", max_bars: int = 15):
        """Plot a bar chart (for categorical data)."""
        self._figure.clear()
        ax = self._figure.add_subplot(111)
        cats = list(categories)[:max_bars]
        vals = list(values)[:max_bars]
        if not cats:
            ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        else:
            bars = ax.barh(range(len(cats)), vals, color="#3B82F6", alpha=0.85)
            ax.set_yticks(range(len(cats)))
            ax.set_yticklabels([str(c)[:25] for c in cats], fontsize=9)
            ax.invert_yaxis()
            ax.set_title(title, fontsize=11)
            ax.set_xlabel("Count")
        self.draw()

    def plot_heatmap(self, corr_matrix: pd.DataFrame, title: str = "Correlation Matrix"):
        """Plot a correlation heatmap."""
        self._figure.clear()
        ax = self._figure.add_subplot(111)
        im = ax.imshow(corr_matrix.values, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
        ax.set_xticks(range(len(corr_matrix.columns)))
        ax.set_yticks(range(len(corr_matrix.columns)))
        ax.set_xticklabels(corr_matrix.columns, rotation=45, ha="right", fontsize=8)
        ax.set_yticklabels(corr_matrix.columns, fontsize=8)
        self._figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        ax.set_title(title, fontsize=11)
        self.draw()
