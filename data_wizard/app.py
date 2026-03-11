"""CustomTkinter application bootstrap."""

import customtkinter as ctk

from data_wizard.gui.main_window import MainWindow


def main():
    """Launch the Data Wizard application."""
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
