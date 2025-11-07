from __future__ import annotations

import binascii
import hashlib
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

from django.conf import settings

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


def _workspace_roots() -> list[Path]:
    base_dir = Path(settings.BASE_DIR).resolve()  # entrenamiento_niñeravirtual2/ninera_virtual
    project_root = base_dir.parent  # entrenamiento_niñeravirtual2
    repo_root = project_root.parent  # nineraVirtual2
    candidates = [
        project_root / "ml_models",
        base_dir / "ml_models",
        repo_root / "ml_models",
        project_root,
        repo_root,
    ]
    ordered: list[Path] = []
    for path in candidates:
        resolved = path.resolve()
        if resolved not in ordered:
            ordered.append(resolved)
    return ordered


def _resolve_from_dirs(filenames: Iterable[str], search_dirs: Iterable[Path]) -> Path:
    for name in filenames:
        for directory in search_dirs:
            candidate = (directory / name).resolve()
            if candidate.exists() and candidate.stat().st_size > 0:
                return candidate
    first_dir = next(iter(search_dirs))
    first_name = next(iter(filenames))
    return (first_dir / first_name).resolve()


def _resolve_db_path() -> Path:
    override = os.getenv("LEGACY_DB_PATH")
    if override:
        target = Path(override).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    base_dir = Path(settings.BASE_DIR).resolve()
    project_root = base_dir.parent
    repo_root = project_root.parent
    candidates = [
        base_dir / "ninera_virtual.db",
        project_root / "ninera_virtual.db",
        repo_root / "ninera_virtual.db",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return (project_root / "ninera_virtual.db").resolve()


class Config:
    """Configuraciones compartidas por la aplicación legacy."""

    BASE_DIR = Path(settings.BASE_DIR)
    SEARCH_PATHS = _workspace_roots()

    YOLO_MODEL_PATH = str(
        _resolve_from_dirs(("ninera.pt", "NiñeraV.pt", "nineraV.pt"), SEARCH_PATHS)
    )
    COCO_MODEL_PATH = str(_resolve_from_dirs(("yolov8s.pt",), SEARCH_PATHS))
    USE_COCO_MODEL = True

    COCO_CLASS_MAP = {
        "knife": "cuchillo",
        "oven": "horno",
        "chair": "silla",
        "dining table": "mesa",
        "table": "mesa",
        "person": "nino",
        "scissors": "tijeras",
    }

    YOLO_CONF_DEFAULT = 0.25
    YOLO_IOU = 0.45
    CLASS_THRESHOLDS = {
        "cuchillo": 0.35,
        "knife": 0.35,
        "cocina": 0.35,
        "kitchen": 0.35,
        "cooker": 0.35,
        "olla": 0.35,
        "pot": 0.35,
        "pan": 0.35,
        "horno": 0.35,
        "oven": 0.35,
        "escaleras": 0.30,
        "stairs": 0.30,
        "nino": 0.40,
        "child": 0.40,
        "handrail": 0.35,
        "baranda": 0.35,
        "chair": 0.35,
        "silla": 0.35,
        "bar": 0.35,
        "barra": 0.35,
        "table": 0.35,
        "mesa": 0.35,
        "stool": 0.35,
        "taburete": 0.35,
        "counter": 0.35,
        "mostrador": 0.35,
        "shelf": 0.35,
        "estante": 0.35,
        "tijeras": 0.35,
        "scissors": 0.35,
    }
    HIGH_SURFACE_LABELS = [
        "chair",
        "silla",
        "bar",
        "barra",
        "table",
        "mesa",
        "stool",
        "taburete",
        "counter",
        "mostrador",
        "shelf",
        "estante",
    ]

    PROXIMITY_PX = 120.0
    CD_GENERAL = 5
    CD_HANDRAIL = 1
    CD_HEIGHT = 2

    TELEGRAM_BOT_TOKEN = os.getenv(
        "TELEGRAM_BOT_TOKEN", "7657028357:AAHV3c1mpfHrFFUK_HciH6NNQ30pxtC6dfQ"
    )
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "1626038555")
    SEND_TELEGRAM = bool(int(os.getenv("SEND_TELEGRAM_ALERTS", "1")))
    TELEGRAM_IMG_MAX_W = 640
    TELEGRAM_JPEG_QLTY = 80
    TELEGRAM_CONC = 2

    UPDATE_MS = 25
    SAVE_IMG_DIR = str(Path(settings.MEDIA_ROOT) / "alertas_img")
    MAX_ALERT_IMGS = 500
    SOUND = True

    GRAYSCALE = False
    CLAHE = False

    DB_PATH = str(_resolve_db_path())
    PASSWORD_ITERATIONS = 120_000


class DatabaseConnection:
    """Singleton para la conexión SQLite."""

    _instance: Optional["DatabaseConnection"] = None

    def __init__(self):
        self.conn = sqlite3.connect(Config.DB_PATH, check_same_thread=False)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._init_schema()

    @classmethod
    def get_instance(cls) -> "DatabaseConnection":
        if cls._instance is None:
            cls._instance = DatabaseConnection()
        return cls._instance

    def _init_schema(self) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """
        )
        self.conn.commit()

    def get_conn(self):
        return self.conn


class UserRepository:
    """Repositorio para operar sobre la tabla de usuarios."""

    def __init__(self, db: DatabaseConnection):
        self.conn = db.get_conn()

    @staticmethod
    def _hash_password(password: str, salt: bytes) -> str:
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, Config.PASSWORD_ITERATIONS
        )
        return binascii.hexlify(dk).decode("utf-8")

    def create_user(self, name: str, email: str, password: str) -> None:
        salt = os.urandom(16)
        phash = self._hash_password(password, salt)
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO users (name, email, password_hash, salt, created_at)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                name.strip(),
                email.strip().lower(),
                phash,
                binascii.hexlify(salt).decode("utf-8"),
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        self.conn.commit()

    def find_by_email(self, email: str):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT id, name, email, password_hash, salt FROM users WHERE email = ?",
            (email.strip().lower(),),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "name": row[1],
            "email": row[2],
            "password_hash": row[3],
            "salt": row[4],
        }

    def verify_credentials(self, email: str, password: str):
        user = self.find_by_email(email)
        if not user:
            return None
        salt = binascii.unhexlify(user["salt"].encode("utf-8"))
        phash = self._hash_password(password, salt)
        if phash == user["password_hash"]:
            return user
        return None
