from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional

import numpy as np

from .config import Config

try:
    from ultralytics import YOLO
except Exception:  # pragma: no cover - dependencia pesada
    YOLO = None  # type: ignore


@dataclass
class Detection:
    label: str
    box: Iterable[int]
    confidence: float
    src: str


class IDetectionStrategy:
    def detect(self, frame_bgr) -> List[Detection]: ...


class YOLOCustomStrategy(IDetectionStrategy):
    def __init__(self, model_path: str):
        if YOLO is None:
            raise RuntimeError("Ultralytics YOLO no está disponible.")
        self.model = YOLO(model_path)

    def detect(self, frame_bgr):
        out: List[Detection] = []
        res = self.model.predict(
            source=frame_bgr,
            conf=min(Config.YOLO_CONF_DEFAULT, 0.25),
            iou=Config.YOLO_IOU,
            verbose=False,
        )
        if res and res[0].boxes is not None:
            names = self.model.names
            for b in res[0].boxes:
                xyxy = b.xyxy.cpu().numpy().astype(int)[0]
                conf = float(b.conf.item())
                cls = int(b.cls.item())
                label = names[cls].lower()
                out.append(Detection(label, xyxy, conf, "custom"))
        return out


class YOLOCocoStrategy(IDetectionStrategy):
    def __init__(self, model_path: str):
        if YOLO is None:
            raise RuntimeError("Ultralytics YOLO no está disponible.")
        self.model = YOLO(model_path)

    def detect(self, frame_bgr):
        out: List[Detection] = []
        res = self.model.predict(source=frame_bgr, conf=0.25, iou=0.5, verbose=False)
        if res and res[0].boxes is not None:
            names = self.model.names
            for b in res[0].boxes:
                xyxy = b.xyxy.cpu().numpy().astype(int)[0]
                conf = float(b.conf.item())
                cls = int(b.cls.item())
                raw = names[cls]
                if isinstance(raw, (bytes, bytearray)):
                    raw = raw.decode("utf-8", errors="ignore")
                mapped = Config.COCO_CLASS_MAP.get(str(raw).lower())
                if mapped:
                    out.append(Detection(mapped.lower(), xyxy, conf, "coco"))
        return out


class FusionDetectionStrategy(IDetectionStrategy):
    """Combina dos estrategias y aplica NMS por clase."""

    def __init__(self, strat_a: IDetectionStrategy, strat_b: Optional[IDetectionStrategy]):
        self.a = strat_a
        self.b = strat_b

    def detect(self, frame_bgr):
        dets: List[Detection] = []
        try:
            dets += self.a.detect(frame_bgr)
        except Exception as e:
            logging.error(f"Custom detect error: {e}")
        if self.b:
            try:
                dets += self.b.detect(frame_bgr)
            except Exception as e:
                logging.error(f"COCO detect error: {e}")
        if not dets:
            return []

        def iou(a, b):
            x1 = max(a[0], b[0])
            y1 = max(a[1], b[1])
            x2 = min(a[2], b[2])
            y2 = min(a[3], b[3])
            inter = max(0, x2 - x1) * max(0, y2 - y1)
            A = (a[2] - a[0]) * (a[3] - a[1])
            B = (b[2] - b[0]) * (b[3] - b[1])
            return inter / max(A + B - inter + 1e-9, 1e-9)

        res: List[Detection] = []
        used = [False] * len(dets)
        for i, di in enumerate(dets):
            if used[i]:
                continue
            best = di
            for j in range(i + 1, len(dets)):
                if used[j]:
                    continue
                dj = dets[j]
                if di.label == dj.label and iou(di.box, dj.box) > 0.5:
                    if dj.confidence > best.confidence:
                        best = dj
                    used[j] = True
            used[i] = True
            res.append(best)
        return res


class IRiskObserver:
    def on_alert(self, event): ...


class RiskEvent:
    def __init__(self, camera_name, messages, frame_bgr):
        self.camera_name = camera_name
        self.messages = messages
        self.frame_bgr = frame_bgr
        self.ts = datetime.now()


class RiskAnalysisFacade:
    """Aplica reglas de riesgo y notifica a observers."""

    def __init__(self, detector: IDetectionStrategy):
        self.detector = detector
        self.observers: List[IRiskObserver] = []
        self.cooldowns: Dict[tuple, datetime] = {}
        self.polygons_per_cam: Dict[str, Dict] = {}
        self.high_surfaces = set(Config.HIGH_SURFACE_LABELS)

    def subscribe(self, obs: IRiskObserver):
        self.observers.append(obs)

    def set_polygons(self, cam_id, zones_dict):
        self.polygons_per_cam[cam_id] = zones_dict

    @staticmethod
    def _center(box):
        return int((box[0] + box[2]) / 2), int((box[1] + box[3]) / 2)

    @staticmethod
    def _child_key(box, grid=25):
        cx, cy = RiskAnalysisFacade._center(box)
        return (int(cx // grid), int(cy // grid))

    @staticmethod
    def _proximity(b1, b2, thr):
        x1, y1 = RiskAnalysisFacade._center(b1)
        x2, y2 = RiskAnalysisFacade._center(b2)
        return np.hypot(x1 - x2, y1 - y2) < thr

    @staticmethod
    def _point_in_polygon(x, y, poly):
        inside = False
        n = len(poly)
        for i in range(n):
            x1, y1 = poly[i]
            x2, y2 = poly[(i + 1) % n]
            if (y1 > y) != (y2 > y) and (
                x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-9) + x1
            ):
                inside = not inside
        return inside

    @staticmethod
    def _polygon_probe_points(box):
        x1, y1, x2, y2 = box
        cx = int((x1 + x2) / 2)
        cy = int((y1 + y2) / 2)
        return [
            (cx, cy),
            (x1, y1),
            (x2, y1),
            (x2, y2),
            (x1, y2),
        ]

    @staticmethod
    def _child_on_high_surface(c, s, label):
        c_x1, c_y1, c_x2, c_y2 = c
        s_x1, s_y1, s_x2, s_y2 = s
        cw, ch = c_x2 - c_x1, c_y2 - c_y1
        sw, sh = s_x2 - s_x1, s_y2 - s_y1
        if cw <= 0 or ch <= 0 or sw <= 0 or sh <= 0:
            return False
        cx = (c_x1 + c_x2) / 2
        feet = c_y2
        ox = min(c_x2, s_x2) - max(c_x1, s_x1)
        if not (ox > cw * 0.35 or (s_x1 < cx < s_x2)):
            return False
        eff = max(sh, 10)
        if label in [
            "bar",
            "barra",
            "table",
            "mesa",
            "counter",
            "mostrador",
            "shelf",
            "estante",
        ]:
            tol = ch * 0.12
            cmin = s_y1 - tol
            cmax = s_y1 + eff * 0.30
            head_ok = c_y1 < s_y1 + eff * 0.10
            return (cmin < feet < cmax) and head_ok
        if label in ["chair", "silla", "stool", "taburete"]:
            top = s_y1 + sh * 0.15
            bottom = s_y1 + sh * 0.75
            return (top < feet < bottom) and (c_y1 < bottom)
        return False

    def _can(self, cam, typ, ck=None):
        last = self.cooldowns.get((cam, typ, ck))
        cd = Config.CD_GENERAL
        if typ == "CHILD_NEAR_RAILING":
            cd = Config.CD_HANDRAIL
        elif typ == "CHILD_ON_HIGH_SURFACE":
            cd = Config.CD_HEIGHT
        return (last is None) or (datetime.now() >= last + timedelta(seconds=cd))

    def _mark(self, cam, typ, ck=None):
        self.cooldowns[(cam, typ, ck)] = datetime.now()

    def detect_and_evaluate(self, frame_bgr, camera_id, camera_name):
        dets = self.detector.detect(frame_bgr)
        filtered = []
        for d in dets:
            thr = Config.CLASS_THRESHOLDS.get(d.label, Config.YOLO_CONF_DEFAULT)
            if d.confidence >= thr:
                filtered.append(d)
        msgs = []
        children = [d for d in filtered if d.label in ["nino", "child"]]
        prox_cfg = {
            "CHILD_NEAR_KNIFE": ("NIÑO CERCA DE CUCHILLO!", {"knife", "cuchillo"}),
            "CHILD_NEAR_STAIRS": ("NIÑO CERCA DE ESCALERAS!", {"stairs", "escaleras"}),
            "CHILD_NEAR_STOVE": ("NIÑO CERCA DE ESTUFA/COCINA!", {"cooker", "kitchen", "cocina"}),
            "CHILD_NEAR_POT": ("NIÑO CERCA DE OLLA/SARTÉN!", {"pot", "pan", "olla"}),
            "CHILD_NEAR_OVEN": ("NIÑO CERCA DE HORNO!", {"oven", "horno"}),
            "CHILD_NEAR_RAILING": ("NIÑO CERCA DE BARANDA!", {"handrail", "baranda"}),
            "CHILD_NEAR_SCISSORS": ("NIÑO CERCA DE TIJERAS!", {"scissors", "tijeras"}),
        }
        if children:
            for ch in children:
                ck = self._child_key(ch.box)
                for key, (m, labels) in prox_cfg.items():
                    boxes = [o.box for o in filtered if o.label in labels]
                    for bx in boxes:
                        if self._proximity(ch.box, bx, Config.PROXIMITY_PX):
                            if self._can(camera_id, key, ck):
                                msgs.append(m)
                                self._mark(camera_id, key, ck)
                            break
            high = [o for o in filtered if o.label in Config.HIGH_SURFACE_LABELS]
            for ch in children:
                if (ch.box[2] - ch.box[0]) * (ch.box[3] - ch.box[1]) < 40 * 40:
                    continue
                for s in high:
                    if self._child_on_high_surface(ch.box, s.box, s.label):
                        k = "CHILD_ON_HIGH_SURFACE"
                        ck = self._child_key(ch.box)
                        if self._can(camera_id, k, ck):
                            msgs.append(f"¡ALERTA! NIÑO SOBRE {s.label.upper()}!")
                            self._mark(camera_id, k, ck)
                        break
            zones = self.polygons_per_cam.get(camera_id, {})
            if zones:
                for ch in children:
                    ck = self._child_key(ch.box)
                    probes = self._polygon_probe_points(ch.box)
                    for name, polys in zones.items():
                        for poly in polys:
                            if any(
                                self._point_in_polygon(px, py, poly)
                                for px, py in probes
                            ):
                                k = f"CHILD_IN_ZONE_{name}"
                                if self._can(camera_id, k, ck):
                                    msgs.append(f"NIÑO EN ZONA: {name.upper()}!")
                                    self._mark(camera_id, k, ck)
                                break

        if msgs:
            ev = RiskEvent(camera_name, msgs, frame_bgr)
            for obs in self.observers:
                try:
                    obs.on_alert(ev)
                except Exception as e:
                    logging.error(f"Observer error: {e}")

        return filtered
