from __future__ import annotations

import base64
import json
from typing import List
import os
import logging

import cv2
import numpy as np
from channels.generic.websocket import AsyncWebsocketConsumer

try:
    from ultralytics import YOLO  # type: ignore
except Exception:  # pragma: no cover - si no estÃ¡ disponible mantenemos streaming sin inferencia
    YOLO = None  # type: ignore

from ml_models import get_model_path
from .legacy.config import Config
from .models import StreamAlert


class StreamConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.model_custom = None
        self.model_coco = None
        await self.accept()
        # Flags de entorno: permiten activar/desactivar modelos y ajustar tamaño
        self.use_primary = os.getenv("USE_PRIMARY", "1").lower() in {"1", "true", "yes"}
        self.use_coco = os.getenv("USE_COCO", "0").lower() in {"1", "true", "yes"}
        self.target_w = int(os.getenv("STREAM_IMG_W", "416"))
        self.conf_primary = float(os.getenv("YOLO_CONF_PRIMARY", "0.35"))
        self.conf_coco = float(os.getenv("YOLO_CONF_COCO", "0.25"))
        self.coco_model_file = os.getenv("COCO_MODEL_FILE", "yolov8n.pt")
        await self.send_json({"type": "ready", "message": "stream accepted"})

    def _lazy_models(self):
        if YOLO is None:
            return None, None
        if self.use_primary and self.model_custom is None:
            try:
                self.model_custom = YOLO(str(get_model_path("NiñeraV.pt")))
            except Exception:
                # Intentar con variantes de nombre
                self.model_custom = YOLO(str(get_model_path("ninera.pt")))
            logging.info("[stream] Modelo primary cargado")
        if self.use_coco and self.model_coco is None:
            try:
                self.model_coco = YOLO(str(get_model_path(self.coco_model_file)))
            except Exception:
                self.model_coco = None
            else:
                logging.info("[stream] Modelo coco cargado")
        return self.model_custom, self.model_coco

    @staticmethod
    def _decode_frame(b64: str) -> np.ndarray:
        if b64.startswith("data:"):
            b64 = b64.split(",", 1)[1]
        img_bytes = base64.b64decode(b64)
        arr = np.frombuffer(img_bytes, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        return frame

    @staticmethod
    def _resize(frame: np.ndarray, max_w: int = 480) -> np.ndarray:
        h, w = frame.shape[:2]
        if w <= max_w:
            return frame
        new_h = int(h * (max_w / w))
        return cv2.resize(frame, (max_w, new_h))

    async def receive(self, text_data: str | bytes | None = None, bytes_data: bytes | None = None):
        try:
            if text_data is None:
                return
            data = json.loads(text_data)
            if data.get("type") != "frame":
                return

            frame = self._decode_frame(data.get("data", ""))
            if frame is None:
                return
            frame = self._resize(frame, self.target_w)

            det_items: List[dict] = []
            model_custom, model_coco = self._lazy_models()

            def _fmt_results(res, src: str):
                nonlocal det_items
                if not res:
                    return
                r0 = res[0]
                if getattr(r0, "boxes", None) is None:
                    return
                names = getattr(getattr(self, f"model_{src}"), "names", {}) if hasattr(self, f"model_{src}") else {}
                for b in r0.boxes:
                    xyxy = b.xyxy.cpu().numpy().astype(int)[0].tolist()
                    conf = float(b.conf.item())
                    cls = int(b.cls.item())
                    label = str(names.get(cls, src)).lower()
                    det_items.append({"label": label, "box": xyxy, "conf": conf, "src": src})

            if self.use_primary and model_custom is not None:
                try:
                    res_c = model_custom.predict(source=frame, imgsz=self.target_w, conf=self.conf_primary, iou=0.45, device="cpu", verbose=False, max_det=50)
                    _fmt_results(res_c, "custom")
                except Exception:
                    logging.exception("[stream] error en primary")
            if self.use_coco and model_coco is not None:
                try:
                    res_y = model_coco.predict(source=frame, imgsz=self.target_w, conf=self.conf_coco, iou=0.45, device="cpu", verbose=False, max_det=50)
                    _fmt_results(res_y, "coco")
                except Exception:
                    logging.exception("[stream] error en coco")

            # Determinar items sobre umbral por CLASE (idéntico a escritorio)
            def threshold_for(label: str) -> float:
                l = (label or "").lower()
                return Config.CLASS_THRESHOLDS.get(l, self.conf_coco)

            over = [d for d in det_items if d.get("conf", 0.0) >= threshold_for(str(d.get("label", "")))]

            # Persistir alerta ligera si hubo detecciones significativas
            if over:
                try:
                    text = " · ".join([f"[{d.get('src')}] {d.get('label')} {d.get('conf'):.2f}" for d in over])
                    StreamAlert.objects.create(text=text)
                except Exception:
                    logging.exception("[stream] persist alert failed")

            await self.send_json({"type": "detections", "items": det_items, "over": over, "ts": data.get("ts")})
        except Exception as exc:  # pragma: no cover
            await self.send_json({"type": "error", "message": str(exc)})

    async def send_json(self, payload):
        await self.send(text_data=json.dumps(payload))

