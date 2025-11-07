from __future__ import annotations

from pathlib import Path


BASE_MODELS_DIR = Path(__file__).resolve().parent

FILENAME_ALIASES = {
    "NiñeraV.pt": ("NiñeraV.pt", "ninera.pt", "nineraV.pt"),
    "ninera.pt": ("ninera.pt", "NiñeraV.pt", "nineraV.pt"),
}


def _search_dirs() -> list[Path]:
    parent = BASE_MODELS_DIR.parent
    grandparent = parent.parent
    roots = [
        BASE_MODELS_DIR,
        parent / "ml_models",
        parent,
        grandparent / "ml_models",
        grandparent,
    ]
    ordered: list[Path] = []
    for path in roots:
        resolved = path.resolve()
        if resolved not in ordered:
            ordered.append(resolved)
    return ordered


def get_model_path(filename: str) -> Path:
    """Return the absolute path for a model file, buscando en rutas conocidas."""
    candidates = FILENAME_ALIASES.get(filename, (filename,))
    for name in candidates:
        for directory in _search_dirs():
            candidate = (directory / name).resolve()
            if candidate.exists() and candidate.stat().st_size > 0:
                return candidate
    primary_dir = _search_dirs()[0]
    return (primary_dir / candidates[0]).resolve()
