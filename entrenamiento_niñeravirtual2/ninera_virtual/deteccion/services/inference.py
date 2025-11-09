from pathlib import Path
from typing import Dict, Union, List

import cv2

FilePath = Union[str, Path]


def _ensure_yolo(model_obj):
    try:
        if hasattr(model_obj, "predict"):
            return model_obj
        if isinstance(model_obj, dict) and "path" in model_obj:
            from ultralytics import YOLO  # type: ignore
            return YOLO(str(model_obj["path"]))
    except Exception:
        return None
    return None


def run_inference(file_path: FilePath, models: Dict[str, object]) -> Dict[str, object]:
    """Inferencia con Niñera.pt y yolov8s.pt si están disponibles.

    - Usa el primer frame del video o la imagen completa.
    - Ejecuta predict en los modelos disponibles (CPU), combina resultados simples.
    """
    resolved_path = Path(file_path)
    img = None
    if resolved_path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}:
        img = cv2.imread(str(resolved_path))
    else:
        cap = cv2.VideoCapture(str(resolved_path))
        ok, frame = cap.read()
        cap.release()
        if ok:
            img = frame
    if img is None:
        return {"output_path": str(resolved_path), "detections": [], "models_used": []}

    h, w = img.shape[:2]
    if w > 640:
        new_h = int(h * (640 / w))
        img = cv2.resize(img, (640, new_h))

    used: List[str] = []
    detections: List[dict] = []

    for key in ("primary", "detector"):
        yolo = _ensure_yolo(models.get(key))
        if yolo is None:
            continue
        try:
            used.append(key)
            res = yolo.predict(
                source=img,
                imgsz=640,
                conf=0.35 if key == "primary" else 0.25,
                iou=0.45,
                device="cpu",
                verbose=False,
            )
            if res and res[0].boxes is not None:
                names = getattr(yolo, "names", {})
                for b in res[0].boxes:
                    xyxy = b.xyxy.cpu().numpy().astype(int)[0].tolist()
                    conf = float(b.conf.item())
                    cls = int(b.cls.item())
                    label = str(names.get(cls, key)).lower()
                    detections.append({"label": label, "conf": conf, "box": xyxy, "src": key})
        except Exception:
            continue

    return {"output_path": str(resolved_path), "detections": detections, "models_used": used}
