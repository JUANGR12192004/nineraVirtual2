#!/usr/bin/env python
import os
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> None:
    """Django's command-line utility for administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ninera_virtual.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "No se pudo importar Django. ¿Está instalado y disponible en tu entorno?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
