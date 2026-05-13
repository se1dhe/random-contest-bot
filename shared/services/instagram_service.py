"""
Сервисные функции для OAuth интеграции Instagram.
"""
import base64
import hashlib
import secrets
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlencode

import httpx

from shared.config import config


def is_instagram_oauth_configured() -> bool:
    """Проверить, настроена ли Instagram OAuth интеграция."""
    return bool(config.instagram_enabled and config.instagram_client_id and config.instagram_client_secret)


def get_instagram_redirect_uri() -> str:
    """Построить redirect URI для Instagram OAuth."""
    base_url = config.webapp_url.rstrip("/")
    return f"{base_url}/api/instagram/callback"


def generate_instagram_code_verifier() -> str:
    """Создать PKCE code_verifier для Instagram OAuth 2.1."""
    # token_urlsafe already uses URL-safe characters; 64 bytes gives a verifier within RFC length limits.
    return secrets.token_urlsafe(64)


def build_instagram_code_challenge(code_verifier: str) -> str:
    """Построить PKCE code_challenge (S256) для Instagram OAuth."""
    digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")


def build_instagram_auth_url(state: str, code_challenge: str) -> str:
    """Сформировать URL авторизации Instagram."""
    authorize_url = (config.instagram_authorize_url or "").strip()
    # Защита от частой ошибки конфигурации: указывают только домен без пути.
    if authorize_url.rstrip("/") in ("https://id.instagram.com", "https://instagram.com"):
        authorize_url = f"{authorize_url.rstrip('/')}/oauth/authorize"

    params = {
        "client_id": config.instagram_client_id,
        "redirect_uri": get_instagram_redirect_uri(),
        "response_type": "code",
        "scope": config.instagram_scopes,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{authorize_url}?{urlencode(params)}"


async def exchange_instagram_code_for_token(code: str, code_verifier: str) -> dict:
    """Обменять authorization code на Instagram access token."""
    payload = {
        "client_id": config.instagram_client_id,
        "client_secret": config.instagram_client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": get_instagram_redirect_uri(),
        "code_verifier": code_verifier,
    }
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(config.instagram_token_url, data=payload)
    response.raise_for_status()
    return response.json()


async def fetch_instagram_user_profile(access_token: str) -> Optional[dict]:
    """Получить профиль текущего Instagram пользователя."""
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(config.instagram_userinfo_url, headers=headers)
    response.raise_for_status()
    data = response.json()
    if isinstance(data, list):
        return data[0] if data else None
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
        return data["data"][0] if data["data"] else None
    return data if isinstance(data, dict) else None


async def check_instagram_follow(
    access_token: str,
    user_id: str,
    target_channel_id: str,
    min_follow_days: int = 0,
) -> Optional[bool]:
    """
    Проверить фолловинг Instagram канала.
    Возвращает None, если API не позволил надежно проверить условие.
    """
    endpoint = config.instagram_following_url.format(user_id=user_id)
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(endpoint, headers=headers)
    if response.status_code >= 400:
        return None

    payload = response.json()
    items = []
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        if isinstance(payload.get("data"), list):
            items = payload["data"]
        elif isinstance(payload.get("items"), list):
            items = payload["items"]

    if not items:
        return False

    target = target_channel_id.strip().lower()
    matched = None
    for item in items:
        if not isinstance(item, dict):
            continue
        candidates = [
            str(item.get("id") or "").strip().lower(),
            str(item.get("channel_id") or "").strip().lower(),
            str(item.get("slug") or "").strip().lower(),
            str(item.get("username") or "").strip().lower(),
            str(item.get("name") or "").strip().lower(),
        ]
        if target in candidates:
            matched = item
            break

    if matched is None:
        return False
    if min_follow_days <= 0:
        return True

    followed_at_raw = matched.get("followed_at") or matched.get("created_at")
    if not followed_at_raw or not isinstance(followed_at_raw, str):
        return None
    try:
        followed_at = datetime.fromisoformat(followed_at_raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (datetime.now(timezone.utc) - followed_at).days >= min_follow_days
