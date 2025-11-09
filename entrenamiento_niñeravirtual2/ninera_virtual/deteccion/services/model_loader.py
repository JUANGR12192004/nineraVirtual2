from functools import lru_cache
from typing import Dict

# Dependencias pesadas se importan de forma perezosa
torch = None  # lazy-loaded at runtime

from ml_models import get_model_path

MODEL_FILENAMES = {
    "primary": "NiñeraV.pt",
    "detector": "yolov8s.pt",
}


@lru_cache
def load_model(model_key: str):
    """Carga perezosa y tolerante.

    - Si Torch no está disponible o el archivo no es un TorchScript válido,
      retorna la ruta como marcador para que la UI funcione.
    - Evita errores tipo "PytorchStreamReader ... constants.pkl" cuando el .pt
      no es TorchScript. La inferencia real se puede implementar después.
    """
    if model_key not in MODEL_FILENAMES:
        raise KeyError(f"Modelo no registrado: {model_key}")

    model_path = str(get_model_path(MODEL_FILENAMES[model_key]))

    try:  # intento opcional de cargar TorchScript si Torch está disponible
        global torch
        if torch is None:
            import importlib
            torch = importlib.import_module("torch")
        return torch.jit.load(model_path)
    except Exception:
        return {"path": model_path}


def get_models() -> Dict[str, object]:
    """Obtiene los modelos registrados (o sus rutas si no se cargan)."""
    return {key: load_model(key) for key in MODEL_FILENAMES}
