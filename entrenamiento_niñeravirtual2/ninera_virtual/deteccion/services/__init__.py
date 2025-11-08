"""Servicios para la app de detección.

Evita importar dependencias pesadas (torch/ultralytics) en tiempo de
importación del paquete. Provee funciones de acceso perezoso.
"""

from __future__ import annotations

from typing import Any, Dict


def get_models() -> Dict[str, object]:
    # Lazy import to delay torch loading until explicitly requested
    from .model_loader import get_models as _get_models

    return _get_models()


def run_inference(*args: Any, **kwargs: Any):
    from .inference import run_inference as _run

    return _run(*args, **kwargs)
