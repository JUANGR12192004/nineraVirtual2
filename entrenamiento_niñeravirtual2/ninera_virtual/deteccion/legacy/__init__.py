"""Módulo legacy.

Evita importar la app GUI (tkinter) en tiempo de import para
entornos headless como servidores web. Si alguien necesita
ejecutar la GUI legacy, puede llamar a ``legacy.run()`` que
realiza la importación de forma perezosa.
"""

from __future__ import annotations

from typing import Any


def run(*args: Any, **kwargs: Any):  # lazy import to avoid tkinter at import time
    from .app import run as _run

    return _run(*args, **kwargs)


__all__ = ["run"]
