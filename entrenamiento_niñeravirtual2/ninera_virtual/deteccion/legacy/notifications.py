from __future__ import annotations

import io
import logging
from threading import Semaphore, Thread

import cv2
import requests

from .config import Config


class INotificationService:
    def send_text(self, text: str): ...

    def send_image_with_caption(self, frame_bgr, caption: str): ...


class TelegramService(INotificationService):
    def __init__(self, token, chat_id, img_max_w, jpeg_quality, semaphore: Semaphore):
        self.token = token
        self.chat_id = chat_id
        self.img_max_w = img_max_w
        self.jpeg_quality = jpeg_quality
        self.sem = semaphore

    def _resize(self, frame):
        h, w = frame.shape[:2]
        if w > self.img_max_w:
            r = self.img_max_w / w
            return cv2.resize(
                frame, (self.img_max_w, int(h * r)), interpolation=cv2.INTER_AREA
            )
        return frame

    def send_text(self, text):
        def t():
            self.sem.acquire()
            try:
                url = f"https://api.telegram.org/bot{self.token}/sendMessage"
                r = requests.get(
                    url, params={"chat_id": self.chat_id, "text": text}, timeout=10
                )
                r.raise_for_status()
            except Exception as e:
                logging.error(f"Telegram text: {e}")
            finally:
                self.sem.release()

        Thread(target=t, daemon=True).start()

    def send_image_with_caption(self, frame_bgr, caption):
        def t():
            self.sem.acquire()
            try:
                fr = self._resize(frame_bgr)
                ok, buf = cv2.imencode(
                    ".jpg", fr, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality]
                )
                if not ok:
                    return
                url = f"https://api.telegram.org/bot{self.token}/sendPhoto"
                files = {"photo": ("alert.jpg", io.BytesIO(buf), "image/jpeg")}
                data = {"chat_id": self.chat_id, "caption": caption}
                r = requests.post(url, files=files, data=data, timeout=20)
                r.raise_for_status()
            except Exception as e:
                logging.error(f"Telegram photo: {e}")
            finally:
                self.sem.release()

        Thread(target=t, daemon=True).start()


class NotificationMediator:
    """Coordina los servicios externos de notificación."""

    def __init__(self):
        self.services = []
        if Config.SEND_TELEGRAM and Config.TELEGRAM_BOT_TOKEN and Config.TELEGRAM_CHAT_ID:
            self.services.append(
                TelegramService(
                    Config.TELEGRAM_BOT_TOKEN,
                    Config.TELEGRAM_CHAT_ID,
                    Config.TELEGRAM_IMG_MAX_W,
                    Config.TELEGRAM_JPEG_QLTY,
                    Semaphore(Config.TELEGRAM_CONC),
                )
            )

    def notify(self, text, frame_bgr=None):
        for s in self.services:
            try:
                if frame_bgr is not None:
                    s.send_image_with_caption(frame_bgr, text)
                else:
                    s.send_text(text)
            except Exception as e:
                logging.error(f"Mediator notify error: {e}")
