"""
Helpers for contest media storage.

The web service owns uploaded files. Bot services should prefer public URLs when
they run in a separate container and cannot see the same filesystem.
"""
from pathlib import Path
from urllib.parse import urljoin
import os

from shared.config import config

UPLOAD_URL_PREFIX = "uploads"


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def get_upload_dir() -> Path:
    configured = os.getenv("UPLOAD_DIR", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return project_root() / UPLOAD_URL_PREFIX


def ensure_upload_dir() -> Path:
    upload_dir = get_upload_dir()
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def build_upload_path(filename: str) -> Path:
    return ensure_upload_dir() / filename


def build_upload_image_path(filename: str) -> str:
    return f"{UPLOAD_URL_PREFIX}/{filename}"


def resolve_upload_image_path(image_path: str | None) -> Path | None:
    if not image_path:
        return None
    if image_path.startswith(("http://", "https://")):
        return None
    path = Path(image_path)
    if path.is_absolute():
        return path
    if len(path.parts) > 1 and path.parts[0] == UPLOAD_URL_PREFIX:
        return get_upload_dir() / Path(*path.parts[1:])
    return project_root() / path


def build_public_media_url(image_path: str | None) -> str | None:
    if not image_path:
        return None
    if image_path.startswith(("http://", "https://")):
        return image_path
    base_url = config.webapp_url.rstrip("/") + "/"
    return urljoin(base_url, image_path.lstrip("/"))
