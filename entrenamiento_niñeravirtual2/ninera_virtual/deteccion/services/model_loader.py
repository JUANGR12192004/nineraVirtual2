from functools import lru_cache
from typing import Dict

try:
    import torch
except ImportError:  # pragma: no cover - torch se instala en producción
    torch = None  # type: ignore

from ml_models import get_model_path

MODEL_FILENAMES = {
    "primary": "NiñeraV.pt",
    "detector": "yolov8s.pt",
}


@lru_cache
def load_model(model_key: str):
    """Carga perezosa de un modelo registrado en MODEL_FILENAMES."""
    if torch is None:
        raise RuntimeError("PyTorch no está instalado en el entorno actual.")

    if model_key not in MODEL_FILENAMES:
        raise KeyError(f"Modelo no registrado: {model_key}")

    model_path = get_model_path(MODEL_FILENAMES[model_key])
    return torch.jit.load(model_path)


def get_models() -> Dict[str, object]:
    """Retorna un diccionario con todas las instancias de modelos necesarios."""
    return {key: load_model(key) for key in MODEL_FILENAMES}
