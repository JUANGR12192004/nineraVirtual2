from pathlib import Path
from typing import Dict, Union

FilePath = Union[str, Path]


def run_inference(file_path: FilePath, models: Dict[str, object]) -> Dict[str, object]:
    """
    Ejecuta inferencia utilizando los modelos cargados.

    Actualmente devuelve resultados simulados y debe reemplazarse con la lógica real.
    """
    resolved_path = Path(file_path)
    return {
        "output_path": str(resolved_path),
        "detections": [],
        "models_used": list(models.keys()),
    }
