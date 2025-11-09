"""
sitecustomize: hooks loaded automatically by Python at startup.

We use this to unify ML model filenames across the project without
touching original modules that live in a folder with non-ASCII name.

It patches `ml_models.get_model_path` so that any code asking for
variants like 'NiñeraV.pt' / 'Ni�eraV.pt' / 'Ni��eraV.pt' or
'yolov8s.pt' resolves to an actually present file, preferring ASCII
names and lightweight weights when available.
"""
from __future__ import annotations

import os
import sys
import glob
from pathlib import Path


PREFERRED_PRIMARY = ("ninera.pt", "NiñeraV.pt", "Ni�eraV.pt", "Ni��eraV.pt", "nineraV.pt")
PREFERRED_DETECTOR = ("yolov8n.pt", "yolov8s.pt")  # prefer n over s (lighter)


def _candidate_names(requested: str) -> list[str]:
    r = requested.strip()
    base = r.lower()
    if "yolov8" in base:
        return list(PREFERRED_DETECTOR) + [r]
    # assume primary custom model otherwise
    return list(PREFERRED_PRIMARY) + [r]


def _search_dirs() -> list[Path]:
    # typical places inside the container/repo
    roots: list[Path] = []
    cwd = Path.cwd()
    roots.append(cwd / "ml_models")
    roots.append(cwd)
    # search under any path entry for ml_models
    for p in list(dict.fromkeys([Path(x) for x in sys.path if isinstance(x, str)])):
        roots.append(p / "ml_models")
        roots.append(p)
    # unique + existing
    out: list[Path] = []
    for d in roots:
        try:
            rd = d.resolve()
            if rd not in out and rd.exists():
                out.append(rd)
        except Exception:
            continue
    return out


def _resolve_model_path(name: str) -> Path:
    for cand in _candidate_names(name):
        for d in _search_dirs():
            p = (d / cand).resolve()
            try:
                if p.exists() and p.stat().st_size > 0:
                    return p
            except Exception:
                continue
    # last resort: return the first candidate under first dir even if missing
    roots = _search_dirs() or [Path.cwd()]
    return (roots[0] / _candidate_names(name)[0]).resolve()


def _patch_ml_models():
    try:
        import ml_models  # type: ignore
    except Exception:
        return

    try:
        def get_model_path(name: str):  # type: ignore
            return _resolve_model_path(name)

        ml_models.get_model_path = get_model_path  # type: ignore[attr-defined]
        # optional: expose helper for debugging
        ml_models.__dict__["_resolve_model_path"] = _resolve_model_path
    except Exception:
        pass


_patch_ml_models()

