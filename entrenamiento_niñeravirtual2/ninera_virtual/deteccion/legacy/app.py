from __future__ import annotations

import tkinter as tk

from .config import DatabaseConnection
from .ui_auth import AuthWindow


def run() -> None:
    """Entrada principal para la aplicación legacy."""
    DatabaseConnection.get_instance()
    root = tk.Tk()
    AuthWindow(root)
    root.mainloop()
