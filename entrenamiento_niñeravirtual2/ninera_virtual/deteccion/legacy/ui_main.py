from __future__ import annotations

import csv
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from queue import Empty, Full, Queue
from threading import Thread
from typing import Dict, Optional

import cv2
import numpy as np
import tkinter as tk
from PIL import Image, ImageTk
from tkinter import filedialog, messagebox, simpledialog, ttk

from .adapters import VideoSourceFactory
from .config import Config
from .detection import (
    FusionDetectionStrategy,
    RiskAnalysisFacade,
    RiskEvent,
    YOLOCustomStrategy,
    YOLOCocoStrategy,
)
from .notifications import NotificationMediator


class CCTVMonitoringSystem:
    """Ventana principal (Observer de RiskAnalysisFacade)."""

    DARK = {
        "bg": "#0f172a",
        "bg2": "#111827",
        "panel": "#0b1220",
        "card": "#111827",
        "text": "#e5e7eb",
        "muted": "#9ca3af",
        "primary": "#2563eb",
        "primary_hover": "#1d4ed8",
        "accent": "#22c55e",
        "danger": "#ef4444",
        "warning": "#f59e0b",
        "outline": "#1f2937",
        "chip": "#1f2937",
    }
    LIGHT = {
        "bg": "#f3f4f6",
        "bg2": "#ffffff",
        "panel": "#ffffff",
        "card": "#ffffff",
        "text": "#111827",
        "muted": "#4b5563",
        "primary": "#2563eb",
        "primary_hover": "#1d4ed8",
        "accent": "#16a34a",
        "danger": "#dc2626",
        "warning": "#d97706",
        "outline": "#e5e7eb",
        "chip": "#f3f4f6",
    }

    def __init__(self, root, session_user: dict, on_logout=None):
        os.makedirs(Config.SAVE_IMG_DIR, exist_ok=True)
        logging.basicConfig(
            filename=str(Path(Config.BASE_DIR) / "nany.log"),
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s",
        )

        self.root = root
        self.root.title("Niñera Virtual - Monitoreo")
        self.root.minsize(1080, 680)
        self.theme = "dark"
        self.colors = self.DARK
        self.session_user = session_user
        self.on_logout_cb = on_logout
        self.is_fullscreen = False
        self._set_fullscreen(True)
        self.root.bind("<F11>", self._toggle_fullscreen)
        self.root.bind("<Escape>", self._exit_fullscreen)

        self.running = True
        self.current_camera_id: Optional[str] = None
        self.cameras: Dict[str, dict] = {}
        self.frame_queues: Dict[str, Queue] = {}
        self.infer_queues: Dict[str, Queue] = {}
        self.display_queues: Dict[str, Queue] = {}
        self.infer_threads: Dict[str, Thread] = {}
        self.alert_history = []
        self.per_camera_polygons: Dict[str, dict] = {}

        self._build_detector_and_facade()
        self.mediator = NotificationMediator()
        self.facade.subscribe(self)

        self.object_colors = {
            "nino": (72, 187, 120),
            "child": (72, 187, 120),
            "knife": (239, 68, 68),
            "cuchillo": (239, 68, 68),
            "stairs": (245, 158, 11),
            "escaleras": (245, 158, 11),
            "cooker": (37, 99, 235),
            "kitchen": (37, 99, 235),
            "cocina": (37, 99, 235),
            "oven": (99, 102, 241),
            "horno": (99, 102, 241),
            "pot": (236, 72, 153),
            "pan": (236, 72, 153),
            "olla": (236, 72, 153),
            "handrail": (168, 85, 247),
            "baranda": (168, 85, 247),
            "chair": (34, 211, 238),
            "silla": (34, 211, 238),
            "bar": (59, 130, 246),
            "barra": (59, 130, 246),
            "table": (16, 185, 129),
            "mesa": (16, 185, 129),
            "stool": (250, 204, 21),
            "taburete": (250, 204, 21),
            "counter": (251, 146, 60),
            "mostrador": (251, 146, 60),
            "shelf": (52, 211, 153),
            "estante": (52, 211, 153),
            "tijeras": (255, 140, 0),
            "scissors": (255, 140, 0),
            "default": (203, 213, 225),
        }

        self._configure_style()
        self._build_menu()
        self._build_layout()

        self.root.after(Config.UPDATE_MS, self._update_gui_frame)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # Observer interface -------------------------------------------------
    def on_alert(self, event: RiskEvent):
        text = " | ".join(sorted(set(event.messages)))
        self._append_feed(f"[{event.camera_name}] {text}")
        self._update_banner(text, danger=True)
        self._save_alert_image(event.frame_bgr, event.camera_name)
        self._bump_metrics(text)
        self._beep()
        if Config.SEND_TELEGRAM:
            self.mediator.notify(
                f"🚨 ALERTA ({event.camera_name}): {text}", frame_bgr=event.frame_bgr
            )

    # Detector setup ----------------------------------------------------
    def _build_detector_and_facade(self):
        try:
            custom = YOLOCustomStrategy(Config.YOLO_MODEL_PATH)
        except Exception as e:
            messagebox.showerror("Modelo", f"No pudo cargarse el modelo custom: {e}")
            raise
        coco = None
        if Config.USE_COCO_MODEL:
            try:
                coco = YOLOCocoStrategy(Config.COCO_MODEL_PATH)
            except Exception as e:
                logging.error(f"No se cargó COCO: {e}")
        fusion = FusionDetectionStrategy(custom, coco)
        self.facade = RiskAnalysisFacade(fusion)

    # UI setup -----------------------------------------------------------
    def _configure_style(self):
        s = ttk.Style()
        s.theme_use("clam")
        c = self.colors
        s.configure("TFrame", background=c["bg"])
        s.configure("Panel.TFrame", background=c["panel"], relief="flat")
        s.configure("Card.TFrame", background=c["card"], relief="flat")
        s.configure("TLabel", background=c["bg"], foreground=c["text"], font=("Segoe UI", 10))
        s.configure("Title.TLabel", background=c["bg"], foreground=c["text"], font=("Segoe UI", 16, "bold"))
        s.configure("Muted.TLabel", background=c["bg"], foreground=c["muted"], font=("Segoe UI", 9))
        s.configure(
            "TButton",
            background=c["primary"],
            foreground="#fff",
            borderwidth=0,
            padding=(12, 7),
            font=("Segoe UI Semibold", 10),
        )
        s.map("TButton", background=[("active", c["primary_hover"])])
        s.configure(
            "Ghost.TButton",
            background=c["chip"],
            foreground=c["text"],
            padding=(10, 6),
            borderwidth=0,
        )
        s.map("Ghost.TButton", background=[("active", c["outline"])])
        s.configure("TLabelframe", background=c["panel"], foreground=c["text"], bordercolor=c["outline"])
        s.configure("TLabelframe.Label", background=c["panel"], foreground=c["muted"], font=("Segoe UI Semibold", 10))
        s.configure(
            "Alert.TLabel",
            background=c["accent"],
            foreground="#fff",
            font=("Segoe UI Semibold", 10),
            padding=6,
            anchor="center",
        )
        s.configure(
            "Danger.Alert.TLabel",
            background=c["danger"],
            foreground="#fff",
            font=("Segoe UI Semibold", 10),
            padding=6,
            anchor="center",
        )

    def _build_menu(self):
        m = tk.Menu(self.root, tearoff=0)
        filem = tk.Menu(m, tearoff=0)
        filem.add_command(label="Exportar historial CSV", command=self.export_history_csv)
        filem.add_separator()
        filem.add_command(label="Salir", command=self.on_close)
        m.add_cascade(label="Archivo", menu=filem)

        zm = tk.Menu(m, tearoff=0)
        zm.add_command(label="Definir Zonas (polígonos)", command=self.define_zones_for_current)
        zm.add_command(label="Cargar Zonas (JSON)", command=self.load_zones_json)
        zm.add_command(label="Guardar Zonas (JSON)", command=self.save_zones_json)
        zm.add_separator()
        zm.add_command(label="🗑️ Eliminar zona por nombre", command=self.delete_zone_by_name)
        zm.add_command(label="🗑️ Eliminar TODAS las zonas (cámara actual)", command=self.delete_all_zones_current)
        m.add_cascade(label="Zonas", menu=zm)

        settings = tk.Menu(m, tearoff=0)
        settings.add_command(label="Tema: Oscuro/Claro", command=self.toggle_theme)
        m.add_cascade(label="Ajustes", menu=settings)

        account = tk.Menu(m, tearoff=0)
        account.add_command(
            label=f"Cerrar sesión ({self.session_user.get('name', '')})", command=self._logout
        )
        m.add_cascade(label="Cuenta", menu=account)

        helpm = tk.Menu(m, tearoff=0)
        helpm.add_command(
            label="Acerca de",
            command=lambda: messagebox.showinfo(
                "Acerca de", f"Niñera Virtual - {self.session_user.get('email', '')}"
            ),
        )
        m.add_cascade(label="Ayuda", menu=helpm)

        self.root.config(menu=m)

    def _build_layout(self):
        c = self.colors
        top = ttk.Frame(self.root, style="Panel.TFrame", padding=(16, 10))
        top.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(top, text="👶 Niñera Virtual", style="Title.TLabel").pack(side=tk.LEFT)
        usertxt = f"Sesión: {self.session_user.get('name', '')} • {self.session_user.get('email', '')}"
        ttk.Label(top, text=usertxt, style="Muted.TLabel").pack(side=tk.LEFT, padx=(10, 0))
        ttk.Button(top, text="☀/🌙 Tema", style="Ghost.TButton", command=self.toggle_theme).pack(
            side=tk.RIGHT, padx=6
        )

        body = ttk.Frame(self.root, style="TFrame")
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        left = ttk.Frame(body, style="Panel.TFrame", padding=12)
        left.pack(side=tk.LEFT, fill=tk.Y)
        self._build_left_panel(left)

        center = ttk.Frame(body, style="Panel.TFrame", padding=12)
        center.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._build_center_panel(center)

        right = ttk.Frame(body, style="Panel.TFrame", padding=12)
        right.pack(side=tk.RIGHT, fill=tk.Y)
        self._build_right_panel(right)

        status = ttk.Frame(self.root, style="Panel.TFrame")
        status.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_label = ttk.Label(status, text="Listo.", style="Muted.TLabel")
        self.status_label.pack(side=tk.LEFT, padx=10, pady=6)

    def _build_left_panel(self, parent):
        c = self.colors
        lf = ttk.LabelFrame(parent, text="Fuentes de Video", padding=10)
        lf.pack(fill=tk.X)
        btns = ttk.Frame(lf, style="Card.TFrame")
        btns.pack(fill=tk.X)
        ttk.Button(btns, text="📷  Agregar Cámara", command=self.add_camera_source).pack(fill=tk.X, pady=4)
        ttk.Button(btns, text="🎞️  Agregar Video", command=self.add_video_source).pack(fill=tk.X, pady=4)
        ttk.Button(btns, text="🗑️  Quitar Fuente", command=self.remove_camera_source).pack(fill=tk.X, pady=4)

        cf = ttk.LabelFrame(parent, text="Cámaras Activas", padding=10)
        cf.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        listc = ttk.Frame(cf, style="Card.TFrame")
        listc.pack(fill=tk.BOTH, expand=True)
        self.camera_list_box = tk.Listbox(
            listc,
            bg=c["card"],
            fg=c["text"],
            selectbackground=c["primary"],
            selectforeground="#fff",
            highlightthickness=0,
            bd=0,
            relief="flat",
            font=("Segoe UI", 10),
        )
        self.camera_list_box.pack(fill=tk.BOTH, expand=True)
        self.camera_list_box.bind("<<ListboxSelect>>", self.on_camera_select)

        zf = ttk.LabelFrame(parent, text="Zonas de Riesgo", padding=10)
        zf.pack(fill=tk.X, pady=(12, 0))
        ttk.Button(zf, text="✏️  Definir Zonas", command=self.define_zones_for_current, style="Ghost.TButton").pack(
            fill=tk.X, pady=3
        )
        ttk.Button(zf, text="📂  Cargar Zonas (JSON)", command=self.load_zones_json, style="Ghost.TButton").pack(
            fill=tk.X, pady=3
        )
        ttk.Button(zf, text="💾  Guardar Zonas (JSON)", command=self.save_zones_json, style="Ghost.TButton").pack(
            fill=tk.X, pady=3
        )

    def _build_center_panel(self, parent):
        card = ttk.Frame(parent, style="Card.TFrame", padding=10)
        card.pack(fill=tk.BOTH, expand=True)
        header = ttk.Frame(card, style="Card.TFrame")
        header.pack(fill=tk.X)
        ttk.Label(header, text="Vista en tiempo real", style="Title.TLabel").pack(side=tk.LEFT)
        ttk.Label(
            header,
            text="Selecciona una fuente para iniciar el monitoreo.",
            style="Muted.TLabel",
        ).pack(side=tk.LEFT, padx=(10, 0))
        self.video_label = ttk.Label(
            card,
            text="Niñera Virtual\n\nSelecciona o agrega una fuente.",
            anchor="center",
            style="TLabel",
            font=("Segoe UI Semibold", 14),
        )
        self.video_label.pack(fill=tk.BOTH, expand=True, pady=(8, 4))
        self.alert_banner = ttk.Label(card, text="Sistema listo.", style="Alert.TLabel")
        self.alert_banner.pack(fill=tk.X, pady=(6, 0))

    def _build_right_panel(self, parent):
        af = ttk.LabelFrame(parent, text="Alertas Recientes", padding=10)
        af.pack(fill=tk.BOTH, expand=True)
        feedc = ttk.Frame(af, style="Card.TFrame")
        feedc.pack(fill=tk.BOTH, expand=True)
        self.feed = tk.Text(
            feedc,
            height=14,
            wrap="word",
            bg=self.colors["card"],
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
            highlightthickness=0,
            bd=0,
            relief="flat",
            font=("Segoe UI", 10),
        )
        self.feed.pack(fill=tk.BOTH, expand=True)
        self.feed.config(state="disabled")

        mf = ttk.LabelFrame(parent, text="Métricas", padding=10)
        mf.pack(fill=tk.X, pady=(12, 0))
        self.metrics = {
            "total": tk.StringVar(value="0"),
            "knife": tk.StringVar(value="0"),
            "stairs": tk.StringVar(value="0"),
            "stove": tk.StringVar(value="0"),
            "pot": tk.StringVar(value="0"),
            "zone": tk.StringVar(value="0"),
            "high": tk.StringVar(value="0"),
            "scissors": tk.StringVar(value="0"),
        }

        grid = ttk.Frame(mf, style="Card.TFrame")
        grid.pack(fill=tk.X)
        self._metric_chip(grid, "🔢 Total", self.metrics["total"], 0, 0)
        self._metric_chip(grid, "🔪 Cuchillo", self.metrics["knife"], 0, 1)
        self._metric_chip(grid, "🪜 Escaleras", self.metrics["stairs"], 1, 0)
        self._metric_chip(grid, "🔥 Estufa", self.metrics["stove"], 1, 1)
        self._metric_chip(grid, "🍲 Olla", self.metrics["pot"], 2, 0)
        self._metric_chip(grid, "📍 Zonas", self.metrics["zone"], 2, 1)
        self._metric_chip(grid, "⬆️ Altura", self.metrics["high"], 3, 0)
        self._metric_chip(grid, "✂️ Tijeras", self.metrics["scissors"], 3, 1)

        actions = ttk.Frame(parent, style="Card.TFrame")
        actions.pack(fill=tk.X, pady=(12, 0))
        ttk.Button(actions, text="⬇️  Exportar historial CSV", command=self.export_history_csv).pack(
            fill=tk.X, pady=4
        )

    def _metric_chip(self, parent, label, var, row, col):
        card = ttk.Frame(parent, style="Card.TFrame", padding=8)
        card.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
        ttk.Label(card, text=label, style="Muted.TLabel").pack(anchor="w")
        ttk.Label(card, textvariable=var, style="Title.TLabel").pack(anchor="w")
        parent.grid_columnconfigure(col, weight=1)

    # Fuentes ------------------------------------------------------------
    def _add_source(self, target, kind):
        adapter = VideoSourceFactory.create(kind, target)
        if not adapter.open():
            messagebox.showerror("Fuente", f"No se pudo abrir {kind}: {target}")
            return

        camera_id = f"{kind}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        self.frame_queues[camera_id] = Queue(maxsize=2)
        self.infer_queues[camera_id] = Queue(maxsize=2)
        self.display_queues[camera_id] = Queue(maxsize=2)

        display = os.path.basename(str(target)) if isinstance(target, str) else f"Cámara {target}"

        fps = 25.0
        try:
            if hasattr(adapter, "cap"):
                val = adapter.cap.get(
                    cv2.CV_CAP_PROP_FPS if hasattr(cv2, "CV_CAP_PROP_FPS") else cv2.CAP_PROP_FPS
                )
                if val and val > 0:
                    fps = float(val)
        except Exception:
            pass
        frame_duration = 1.0 / max(fps, 1.0)

        self.cameras[camera_id] = {
            "adapter": adapter,
            "type": kind,
            "source_name": display,
            "thread": None,
            "active": True,
            "frame_duration": frame_duration,
        }

        t = Thread(target=self._capture_loop, args=(camera_id,), daemon=True)
        t.start()
        self.cameras[camera_id]["thread"] = t
        it = Thread(target=self._inference_loop, args=(camera_id,), daemon=True)
        it.start()
        self.infer_threads[camera_id] = it

        self.camera_list_box.insert(tk.END, display)
        if self.current_camera_id is None:
            self.camera_list_box.selection_set(0)
            self.on_camera_select(None)
        self._set_status(f"Fuente agregada: {display}")

    def add_camera_source(self):
        idx = 0
        names = {d["source_name"] for d in self.cameras.values()}
        while f"Cámara {idx}" in names:
            idx += 1
        self._add_source(idx, "live")

    def add_video_source(self):
        path = filedialog.askopenfilename(
            title="Seleccionar Video",
            filetypes=[("Video", "*.mp4 *.avi *.mov *.mkv"), ("Todos", "*.*")],
        )
        if path:
            self._add_source(path, "video")

    def remove_camera_source(self):
        sel = self.camera_list_box.curselection()
        if not sel:
            messagebox.showinfo("Fuentes", "Seleccione una fuente para quitar.")
            return
        name = self.camera_list_box.get(sel[0])
        cam_id = next((cid for cid, d in self.cameras.items() if d["source_name"] == name), None)
        if not cam_id:
            return

        self.cameras[cam_id]["active"] = False
        if self.cameras[cam_id]["thread"].is_alive():
            self.cameras[cam_id]["thread"].join(timeout=1.0)
        self.cameras[cam_id]["adapter"].release()
        del self.cameras[cam_id]

        for m in (self.frame_queues, self.infer_queues, self.display_queues):
            q = m.pop(cam_id, None)
            if q:
                while not q.empty():
                    try:
                        q.get_nowait()
                    except Empty:
                        break

        self.camera_list_box.delete(sel[0])
        if self.current_camera_id == cam_id:
            self.current_camera_id = None
            self.video_label.config(image="", text="Niñera Virtual\n\nSelecciona o agrega una fuente.")
            if hasattr(self.video_label, "imgtk"):
                self.video_label.imgtk = None

        self._set_status(f"Fuente eliminada: {name}")

    def _capture_loop(self, camera_id):
        cam = self.cameras[camera_id]
        adapter = cam["adapter"]
        is_video = isinstance(adapter.source, str)
        fdur = cam["frame_duration"]
        while self.running and cam.get("active", False) and adapter.is_opened():
            t0 = time.perf_counter()
            ret, frame = adapter.read()
            if not ret:
                if is_video and cam.get("active", False):
                    try:
                        adapter.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    except Exception:
                        break
                    continue
                else:
                    break
            rq = self.frame_queues.get(camera_id)
            if rq:
                if rq.full():
                    try:
                        rq.get_nowait()
                    except Empty:
                        pass
                try:
                    rq.put_nowait(frame)
                except Full:
                    pass
            iq = self.infer_queues.get(camera_id)
            if iq:
                if iq.full():
                    try:
                        iq.get_nowait()
                    except Empty:
                        pass
                try:
                    iq.put_nowait(frame)
                except Full:
                    pass
            if is_video:
                st = fdur - (time.perf_counter() - t0)
                if st > 0:
                    time.sleep(st)
        adapter.release()

    def on_camera_select(self, _):
        sel = self.camera_list_box.curselection()
        if not sel:
            if self.camera_list_box.size() > 0:
                self.camera_list_box.selection_set(0)
                sel = (0,)
            else:
                self.current_camera_id = None
                self.video_label.config(
                    image="", text="Niñera Virtual\n\nSelecciona o agrega una fuente."
                )
                if hasattr(self.video_label, "imgtk"):
                    self.video_label.imgtk = None
                return
        name = self.camera_list_box.get(sel[0])
        cam_id = next((cid for cid, d in self.cameras.items() if d["source_name"] == name), None)
        if cam_id and cam_id != self.current_camera_id:
            self.current_camera_id = cam_id
            dq = self.display_queues.get(self.current_camera_id)
            if dq:
                while not dq.empty():
                    try:
                        dq.get_nowait()
                    except Empty:
                        break
            self.video_label.config(image="", text="")
            if hasattr(self.video_label, "imgtk"):
                self.video_label.imgtk = None
            self._set_status(f"Visualizando: {name}")

    # Inferencia ---------------------------------------------------------
    def _inference_loop(self, camera_id):
        name = self.cameras[camera_id]["source_name"]
        while self.running and self.cameras.get(camera_id, {}).get("active", False):
            try:
                frame = self.infer_queues[camera_id].get(timeout=0.2)
            except Empty:
                continue
            try:
                frame_proc = self._preprocess(frame)
                detections = self.facade.detect_and_evaluate(frame_proc, camera_id, name)
                annotated = self._draw(detections, frame)
                dq = self.display_queues.get(camera_id)
                if dq:
                    if dq.full():
                        try:
                            dq.get_nowait()
                        except Empty:
                            pass
                    try:
                        dq.put_nowait(annotated)
                    except Full:
                        pass
            except Exception as e:
                logging.error(f"Inferencia {camera_id}: {e}")

    def _preprocess(self, frame):
        processed = frame.copy()
        try:
            if Config.GRAYSCALE:
                gray = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
                if Config.CLAHE:
                    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                    gray = clahe.apply(gray)
                processed = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
            elif Config.CLAHE:
                lab = cv2.cvtColor(processed, cv2.COLOR_BGR2LAB)
                l, a, b = cv2.split(lab)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                cl = clahe.apply(l)
                limg = cv2.merge((cl, a, b))
                processed = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
        except Exception as e:
            logging.warning(f"Preprocesado: {e}")
        return processed

    def _draw(self, detections, frame):
        out = frame.copy()
        for d in detections:
            x1, y1, x2, y2 = d.box
            color = self.object_colors.get(d.label, self.object_colors["default"])
            cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
            cv2.putText(
                out,
                f"{d.label} {d.confidence:.2f} ({d.src})",
                (x1, max(14, y1 - 6)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                2,
            )
        return out

    # Zonas --------------------------------------------------------------
    def define_zones_for_current(self):
        if not self.current_camera_id or self.current_camera_id not in self.cameras:
            messagebox.showinfo("Zonas", "Selecciona una camara activa.")
            return

        frame = None
        frame_queue = self.frame_queues.get(self.current_camera_id)
        if frame_queue is not None:
            try:
                frame = frame_queue.get_nowait()
            except Empty:
                frame = None
        if frame is None:
            display_queue = self.display_queues.get(self.current_camera_id)
            if display_queue is not None:
                try:
                    frame = display_queue.get_nowait()
                except Empty:
                    frame = None
        if frame is None:
            messagebox.showinfo("Zonas", "No hay imagen disponible en este momento. Intenta de nuevo.")
            return

        height, width = frame.shape[:2]
        max_w, max_h = 1280, 720
        scale = min(max_w / float(width), max_h / float(height), 1.0)
        if scale < 1.0:
            new_w = max(1, int(round(width * scale)))
            new_h = max(1, int(round(height * scale)))
            display = cv2.resize(frame, (new_w, new_h))
        else:
            display = frame.copy()
            scale = 1.0
        disp_h, disp_w = display.shape[:2]

        image_rgb = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
        image_pil = Image.fromarray(image_rgb)
        photo = ImageTk.PhotoImage(image=image_pil)

        cam_name = self.cameras[self.current_camera_id]["source_name"]
        win = tk.Toplevel(self.root)
        win.title(f"Definir zonas - {cam_name}")
        win.configure(background=self.colors.get("bg", "#0f172a"))
        win.transient(self.root)
        win.resizable(False, False)
        win.grab_set()
        win.columnconfigure(0, weight=1)
        win.rowconfigure(0, weight=1)

        container = ttk.Frame(win, style="Panel.TFrame", padding=(20, 16))
        container.grid(row=0, column=0, sticky="nsew")
        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=0)
        container.rowconfigure(0, weight=1)

        canvas_frame = ttk.Frame(container, style="Card.TFrame", padding=12)
        canvas_frame.grid(row=0, column=0, sticky="nsew")
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.rowconfigure(0, weight=1)
        canvas = tk.Canvas(canvas_frame, width=disp_w, height=disp_h, highlightthickness=0, bg="#000000")
        canvas.grid(row=0, column=0, sticky="nsew")
        canvas.create_image(0, 0, image=photo, anchor="nw")
        canvas.image = photo

        existing = self.per_camera_polygons.get(self.current_camera_id, {})
        existing_count = sum(len(polys) for polys in existing.values())

        controls = ttk.Frame(container, style="Card.TFrame", padding=(16, 12))
        controls.grid(row=0, column=1, sticky="ns", padx=(16, 0))
        controls.columnconfigure(0, weight=1)
        controls.rowconfigure(7, weight=1)

        ttk.Label(controls, text="Definir zonas", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        counter_var = tk.StringVar(value=f"Zonas registradas: {existing_count}")
        ttk.Label(controls, textvariable=counter_var, style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(0, 12))

        instructions = (
            "- Haz clic sobre la imagen para trazar los puntos.",
            "- Deshacer punto elimina el ultimo trazo.",
            "- Guardar zona cierra el poligono y lo agrega a la lista.",
            "- Solo las zonas nuevas se pueden eliminar aqui antes de aplicar.",
        )
        ttk.Label(
            controls,
            text="\n".join(instructions),
            style="Muted.TLabel",
            justify="left",
            wraplength=260,
        ).grid(row=2, column=0, sticky="w")

        ttk.Label(controls, text="Nombre de la zona", style="TLabel").grid(row=3, column=0, sticky="w", pady=(12, 0))
        zone_name_var = tk.StringVar()
        name_entry = ttk.Entry(controls, textvariable=zone_name_var)
        name_entry.grid(row=4, column=0, sticky="ew", pady=(2, 0))

        status_var = tk.StringVar(value="Puntos actuales: 0")
        ttk.Label(controls, textvariable=status_var, style="Muted.TLabel").grid(row=5, column=0, sticky="w", pady=(6, 6))

        actions = ttk.Frame(controls, style="Card.TFrame")
        actions.grid(row=6, column=0, sticky="ew")
        save_btn = ttk.Button(actions, text="Guardar zona")
        save_btn.pack(fill=tk.X, pady=(0, 6))
        undo_btn = ttk.Button(actions, text="Deshacer punto", style="Ghost.TButton")
        undo_btn.pack(fill=tk.X)
        reset_btn = ttk.Button(actions, text="Reiniciar poligono", style="Ghost.TButton")
        reset_btn.pack(fill=tk.X, pady=(6, 0))

        tree_frame = ttk.Frame(controls, style="Card.TFrame")
        tree_frame.grid(row=7, column=0, sticky="nsew", pady=(12, 6))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        tree = ttk.Treeview(
            tree_frame,
            columns=("zona", "estado", "puntos"),
            show="headings",
            selectmode="browse",
            height=7,
        )
        tree.heading("zona", text="Zona")
        tree.heading("estado", text="Estado")
        tree.heading("puntos", text="Puntos")
        tree.column("zona", width=120, anchor="w")
        tree.column("estado", width=80, anchor="center")
        tree.column("puntos", width=70, anchor="center")
        tree.grid(row=0, column=0, sticky="nsew")
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        tree.configure(yscrollcommand=vsb.set)
        tree.tag_configure("existing", foreground=self.colors.get("muted", "#9ca3af"))
        tree.tag_configure("new", foreground=self.colors.get("accent", "#22c55e"))

        ttk.Label(
            controls,
            text="Zonas nuevas agregadas aqui se guardaran al aplicar cambios.",
            style="Muted.TLabel",
            wraplength=260,
        ).grid(row=8, column=0, sticky="w")
        remove_btn = ttk.Button(controls, text="Eliminar seleccionada", style="Ghost.TButton")
        remove_btn.grid(row=9, column=0, sticky="ew", pady=(4, 0))

        footer = ttk.Frame(controls, style="Card.TFrame")
        footer.grid(row=10, column=0, sticky="ew", pady=(16, 0))
        apply_btn = ttk.Button(footer, text="Aplicar zonas")
        apply_btn.pack(side=tk.RIGHT, fill=tk.X)
        cancel_btn = ttk.Button(footer, text="Cancelar", style="Ghost.TButton")
        cancel_btn.pack(side=tk.RIGHT, padx=8)

        name_entry.focus_set()

        current_points = []
        point_handles = []
        line_handles = []
        new_polygons = []
        polygon_shapes = {}
        item_to_polygon = {}

        palette = self.colors
        accent_color = palette.get("accent", "#22c55e")
        muted_color = palette.get("muted", "#9ca3af")

        def to_display(pt):
            x, y = pt
            return int(round(x * scale)), int(round(y * scale))

        for label, polys in existing.items():
            for poly in polys:
                if not poly:
                    continue
                coords = []
                for px, py in poly:
                    dx, dy = to_display((px, py))
                    coords.extend((dx, dy))
                if coords:
                    canvas.create_polygon(coords, outline=muted_color, width=2, fill="")
                    tree.insert("", tk.END, values=(label, "Actual", len(poly)), tags=("existing",))

        def update_status(extra=None):
            text = f"Puntos actuales: {len(current_points)}"
            if extra:
                text = f"{text} | {extra}"
            status_var.set(text)

        def update_counter():
            base = sum(len(polys) for polys in existing.values())
            counter_var.set(f"Zonas registradas: {base + len(new_polygons)}")

        def on_canvas_click(event):
            x = max(0, min(disp_w - 1, int(event.x)))
            y = max(0, min(disp_h - 1, int(event.y)))
            point_handles.append(canvas.create_oval(x - 4, y - 4, x + 4, y + 4, fill=accent_color, outline=""))
            if current_points:
                lx, ly = current_points[-1]
                line_handles.append(canvas.create_line(lx, ly, x, y, fill=accent_color, width=2))
            current_points.append((x, y))
            update_status()

        def undo_point():
            if not current_points:
                return
            canvas.delete(point_handles.pop())
            if line_handles:
                canvas.delete(line_handles.pop())
            current_points.pop()
            update_status()

        def reset_polygon():
            while point_handles:
                canvas.delete(point_handles.pop())
            while line_handles:
                canvas.delete(line_handles.pop())
            current_points.clear()
            update_status("Poligono reiniciado.")

        def save_zone():
            name = (zone_name_var.get() or "").strip().lower()
            if not name:
                messagebox.showinfo("Zonas", "Ingresa un nombre para la zona.")
                return
            if len(current_points) < 3:
                messagebox.showinfo("Zonas", "Necesitas al menos 3 puntos para crear el poligono.")
                return
            original = []
            coords = []
            for x, y in current_points:
                ox = min(width - 1, max(0, int(round(x / scale))))
                oy = min(height - 1, max(0, int(round(y / scale))))
                original.append((ox, oy))
                coords.extend((x, y))
            poly_id = f"new_{int(time.time() * 1000)}_{len(new_polygons)}"
            new_polygons.append({"id": poly_id, "name": name, "points": original})
            polygon_shapes[poly_id] = canvas.create_polygon(coords, outline=accent_color, width=2, fill="")
            item_id = tree.insert("", tk.END, values=(name, "Nuevo", len(original)), tags=("new",))
            item_to_polygon[item_id] = poly_id
            zone_name_var.set("")
            reset_polygon()
            update_counter()
            update_status("Zona registrada, aplica cambios para guardar.")

        def remove_selected():
            sel = tree.selection()
            if not sel:
                messagebox.showinfo("Zonas", "Selecciona una zona nueva para eliminar.")
                return
            item = sel[0]
            poly_id = item_to_polygon.get(item)
            if not poly_id:
                messagebox.showinfo("Zonas", "Solo se pueden eliminar las zonas nuevas creadas en esta ventana.")
                return
            tree.delete(item)
            item_to_polygon.pop(item, None)
            for idx, data in enumerate(list(new_polygons)):
                if data["id"] == poly_id:
                    new_polygons.pop(idx)
                    break
            handle = polygon_shapes.pop(poly_id, None)
            if handle is not None:
                canvas.delete(handle)
            update_counter()
            update_status("Zona eliminada.")

        def apply_zones():
            if not new_polygons:
                messagebox.showinfo("Zonas", "No hay zonas nuevas para guardar.")
                return
            cam_polys = self.per_camera_polygons.get(self.current_camera_id, {}).copy()
            for data in new_polygons:
                cam_polys.setdefault(data["name"], []).append(data["points"])
            self.per_camera_polygons[self.current_camera_id] = cam_polys
            self.facade.set_polygons(self.current_camera_id, cam_polys)
            self._set_status(f"{len(new_polygons)} zona(s) nuevas registradas en {cam_name}.", "info")
            messagebox.showinfo("Zonas", f"Se guardaron {len(new_polygons)} zona(s).")
            try:
                win.grab_release()
            except Exception:
                pass
            win.destroy()

        def cancel():
            if new_polygons:
                if not messagebox.askyesno("Zonas", "¿Descartar las zonas nuevas sin guardar?"):
                    return
            try:
                win.grab_release()
            except Exception:
                pass
            win.destroy()

        save_btn.configure(command=save_zone)
        undo_btn.configure(command=undo_point)
        reset_btn.configure(command=reset_polygon)
        remove_btn.configure(command=remove_selected)
        apply_btn.configure(command=apply_zones)
        cancel_btn.configure(command=cancel)

        canvas.bind("<Button-1>", on_canvas_click)
        win.bind("<Return>", lambda _: save_zone())
        win.bind("<Escape>", lambda _: cancel())
        win.protocol("WM_DELETE_WINDOW", cancel)
        win.lift()
        update_status()
        update_counter()

    def load_zones_json(self):
        path = filedialog.askopenfilename(
            title="Cargar Zonas (JSON)", filetypes=[("JSON", "*.json")]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            out = {}
            for cam_id, zones in data.items():
                cmap = {}
                for label, polys in zones.items():
                    clean = [[(int(x), int(y)) for (x, y) in poly] for poly in polys]
                    cmap[label] = clean
                out[cam_id] = cmap
            self.per_camera_polygons = out
            for cam_id, z in out.items():
                self.facade.set_polygons(cam_id, z)
            messagebox.showinfo("Zonas", "Zonas cargadas.")
        except Exception as e:
            messagebox.showerror("Zonas", f"Error: {e}")

    def save_zones_json(self):
        if not self.per_camera_polygons:
            messagebox.showinfo("Zonas", "No hay zonas definidas.")
            return
        path = filedialog.asksaveasfilename(
            title="Guardar Zonas (JSON)",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.per_camera_polygons, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Zonas", "Zonas guardadas.")
        except Exception as e:
            messagebox.showerror("Zonas", f"Error: {e}")

    def delete_all_zones_current(self):
        if not self.current_camera_id:
            messagebox.showinfo("Zonas", "No hay cámara seleccionada.")
            return
        if self.current_camera_id not in self.per_camera_polygons:
            messagebox.showinfo("Zonas", "Esta cámara no tiene zonas.")
            return
        if not messagebox.askyesno("Zonas", "¿Eliminar TODAS las zonas de esta cámara?"):
            return
        del self.per_camera_polygons[self.current_camera_id]
        self.facade.set_polygons(self.current_camera_id, {})
        messagebox.showinfo("Zonas", "Zonas eliminadas para la cámara actual.")

    def delete_zone_by_name(self):
        if not self.current_camera_id:
            messagebox.showinfo("Zonas", "No hay cámara seleccionada.")
            return
        zones = self.per_camera_polygons.get(self.current_camera_id, {})
        if not zones:
            messagebox.showinfo("Zonas", "Esta cámara no tiene zonas.")
            return

        win = tk.Toplevel(self.root)
        win.title("Eliminar zona")
        win.transient(self.root)
        ttk.Label(win, text="Selecciona la zona a eliminar:", style="TLabel", padding=10).pack(anchor="w")
        lb = tk.Listbox(win, height=min(8, len(zones)))
        for name in zones.keys():
            lb.insert(tk.END, name)
        lb.pack(fill=tk.X, padx=10)

        def do_del():
            sel = lb.curselection()
            if not sel:
                messagebox.showinfo("Zonas", "Elige una zona.")
                return
            zname = lb.get(sel[0])
            if messagebox.askyesno("Zonas", f"¿Eliminar la zona '{zname}'?"):
                zones.pop(zname, None)
                if zones:
                    self.per_camera_polygons[self.current_camera_id] = zones
                else:
                    self.per_camera_polygons.pop(self.current_camera_id, None)
                self.facade.set_polygons(self.current_camera_id, zones)
                messagebox.showinfo("Zonas", f"Zona '{zname}' eliminada.")
                win.destroy()

        btns = ttk.Frame(win, padding=10)
        btns.pack(fill=tk.X)
        ttk.Button(btns, text="Eliminar", command=do_del).pack(side=tk.RIGHT)
        ttk.Button(btns, text="Cancelar", style="Ghost.TButton", command=win.destroy).pack(side=tk.RIGHT, padx=8)

    # Render -------------------------------------------------------------
    def _update_gui_frame(self):
        if self.current_camera_id and self.current_camera_id in self.display_queues:
            try:
                frame = self.display_queues[self.current_camera_id].get_nowait()
                img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img_pil = Image.fromarray(img_rgb)
                self.video_label.imgtk = ImageTk.PhotoImage(image=img_pil)
                self.video_label.configure(image=self.video_label.imgtk)
            except Empty:
                pass
            except Exception as e:
                logging.error(f"Update frame: {e}")
        self.root.after(Config.UPDATE_MS, self._update_gui_frame)

    # Utilidades ---------------------------------------------------------
    def _set_fullscreen(self, enabled: bool):
        try:
            self.root.attributes("-fullscreen", enabled)
        except tk.TclError:
            if enabled:
                try:
                    self.root.state("zoomed")
                except tk.TclError:
                    pass
            else:
                try:
                    self.root.state("normal")
                except tk.TclError:
                    pass
        self.is_fullscreen = enabled

    def _toggle_fullscreen(self, _event=None):
        self._set_fullscreen(not self.is_fullscreen)

    def _exit_fullscreen(self, _event=None):
        if self.is_fullscreen:
            self._set_fullscreen(False)

    def toggle_theme(self):
        self.theme = "light" if self.theme == "dark" else "dark"
        self.colors = self.LIGHT if self.theme == "light" else self.DARK
        self._configure_style()
        self._set_status(f"Tema cambiado a {'claro' if self.theme == 'light' else 'oscuro'}.")

    def export_history_csv(self):
        if not self.alert_history:
            messagebox.showinfo("Exportar", "No hay alertas aún.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            title="Guardar historial de alertas",
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["timestamp", "alerta", "fuente"])
                for row in self.alert_history:
                    w.writerow(row)
            messagebox.showinfo("Exportar", "Historial exportado.")
        except Exception as e:
            messagebox.showerror("Exportar", f"Error: {e}")

    def _append_feed(self, line):
        self.feed.config(state="normal")
        ts = datetime.now().strftime("%H:%M:%S")
        self.feed.insert("1.0", f"🛎️  {ts}  {line}\n")
        self.feed.config(state="disabled")
        cam = line.split("] ")[0].split("[")[-1]
        text = line.split("] ")[-1]
        self.alert_history.append((datetime.now().strftime("%Y-%m-%d %H:%M:%S"), text, cam))

    def _update_banner(self, text, danger=False):
        self.alert_banner.config(text=text, style="Danger.Alert.TLabel" if danger else "Alert.TLabel")

    def _bump_metrics(self, text):
        def inc(k):
            self.metrics[k].set(str(int(self.metrics[k].get()) + 1))
            self.metrics["total"].set(str(int(self.metrics["total"].get()) + 1))

        low = text.lower()
        if "cuchillo" in low:
            inc("knife")
        if "escalera" in low:
            inc("stairs")
        if "estufa" in low or "cocina" in low:
            inc("stove")
        if "olla" in low or "sartén" in low:
            inc("pot")
        if "zona" in low:
            inc("zone")
        if "sobre" in low:
            inc("high")
        if "tijeras" in low:
            inc("scissors")

    def _beep(self):
        if not Config.SOUND:
            return

        def t():
            try:
                if sys.platform == "win32":
                    import winsound

                    winsound.Beep(1300, 400)
                else:
                    print("\007", end="")
                    sys.stdout.flush()
            except Exception:
                pass

        Thread(target=t, daemon=True).start()

    def _save_alert_image(self, frame, camera_name):
        clean = "".join(ch if ch.isalnum() else "_" for ch in camera_name)
        tsf = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = os.path.join(Config.SAVE_IMG_DIR, f"alerta_{clean}_{tsf}.jpg")
        try:
            cv2.imwrite(path, frame, [cv2.IMWRITE_JPEG_QUALITY, Config.TELEGRAM_JPEG_QLTY])
        except Exception as e:
            logging.error(f"Guardar IMG: {e}")
        try:
            files = [
                os.path.join(Config.SAVE_IMG_DIR, f)
                for f in os.listdir(Config.SAVE_IMG_DIR)
                if f.lower().endswith((".jpg", ".jpeg", ".png"))
            ]
            files.sort(key=os.path.getmtime)
            while len(files) > Config.MAX_ALERT_IMGS:
                os.remove(files[0])
                files.pop(0)
        except Exception:
            pass

    def _set_status(self, text, tone="info"):
        palette = self.colors
        color_map = {
            "info": palette.get("muted", "#9ca3af"),
            "success": palette.get("accent", "#22c55e"),
            "warning": palette.get("warning", "#f59e0b"),
            "danger": palette.get("danger", "#dc2626"),
        }
        self.status_label.config(text=text, foreground=color_map.get(tone, palette.get("muted", "#9ca3af")))

    def _logout(self):
        if messagebox.askyesno("Cuenta", "¿Cerrar sesión y volver a la pantalla de inicio?"):
            try:
                self.on_close()
            except Exception:
                pass
            if callable(self.on_logout_cb):
                self.on_logout_cb()

    # Cierre -------------------------------------------------------------
    def on_close(self):
        self.running = False
        for d in list(self.cameras.values()):
            d["active"] = False
        for d in list(self.cameras.values()):
            if d.get("thread") and d["thread"].is_alive():
                d["thread"].join(timeout=0.8)
            d["adapter"].release()
        for m in (self.frame_queues, self.infer_queues, self.display_queues):
            for q in list(m.values()):
                while not q.empty():
                    try:
                        q.get_nowait()
                    except Empty:
                        break
        try:
            self.root.destroy()
        except Exception:
            pass
