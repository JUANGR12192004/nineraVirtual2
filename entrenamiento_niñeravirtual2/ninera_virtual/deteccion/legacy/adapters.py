from __future__ import annotations

import cv2


class ICameraAdapter:
    """Interfaz base para adaptadores de fuentes de video."""

    def open(self) -> bool: ...

    def read(self): ...

    def release(self): ...

    def is_opened(self) -> bool: ...


class OpenCVCaptureAdapter(ICameraAdapter):
    """Adapter simple sobre cv2.VideoCapture (webcam, archivo, RTSP/HTTP)."""

    def __init__(self, source):
        self.source = source
        self.cap = None

    def open(self):
        self.cap = cv2.VideoCapture(self.source)
        return self.cap.isOpened()

    def read(self):
        if not self.cap:
            return False, None
        return self.cap.read()

    def release(self):
        if self.cap and self.cap.isOpened():
            self.cap.release()

    def is_opened(self):
        return self.cap is not None and self.cap.isOpened()


class VideoSourceFactory:
    """Factory Method: decide qué adapter construir (actualmente OpenCV)."""

    @staticmethod
    def create(kind: str, target):
        # Si mañana cambia la lib de cámara IP, se cambia aquí el adapter.
        return OpenCVCaptureAdapter(target)
