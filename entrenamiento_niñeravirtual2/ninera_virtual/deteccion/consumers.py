from __future__ import annotations

import base64
import json
from typing import List

import cv2
import numpy as np
from channels.generic.websocket import AsyncWebsocketConsumer

try:
    from ultralytics import YOLO  # type: ignore
except Exception:  # pragma: no cover - si no está disponible mantenemos streaming sin inferencia
    YOLO = None  # type: ignore

from ml_models import get_model_path


class StreamConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.model_custom = None
        self.model_coco = None
        await self.accept()
        await self.send_json({"type": "ready", "message": "stream accepted"})

    def _lazy_models(self):
        if YOLO is None:
            return None, None
        if self.model_custom is None:
            try:
                self.model_custom = YOLO(str(get_model_path("NiñeraV.pt")))
            except Exception:
                # Intentar con variantes de nombre
                self.model_custom = YOLO(str(get_model_path("ninera.pt")))
        if self.model_coco is None:
            try:
                self.model_coco = YOLO(str(get_model_path("yolov8s.pt")))
            except Exception:
                self.model_coco = None
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
            frame = self._resize(frame, 416)

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

            if model_custom is not None:
                try:
                    res_c = model_custom.predict(source=frame, imgsz=416, conf=0.35, iou=0.45, device="cpu", verbose=False)
                    _fmt_results(res_c, "custom")
                except Exception:
                    pass
            if model_coco is not None:
                try:
                    res_y = model_coco.predict(source=frame, imgsz=416, conf=0.25, iou=0.45, device="cpu", verbose=False)
                    _fmt_results(res_y, "coco")
                except Exception:
                    pass

            await self.send_json({"type": "detections", "items": det_items, "ts": data.get("ts")})
        except Exception as exc:  # pragma: no cover
            await self.send_json({"type": "error", "message": str(exc)})

    async def send_json(self, payload):
        await self.send(text_data=json.dumps(payload))
