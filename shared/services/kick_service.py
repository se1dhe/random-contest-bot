"""
Сервисные функции для OAuth интеграции Kick.
"""
import base64
import hashlib
import secrets
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlencode

import httpx

from shared.config import config


def is_kick_oauth_configured() -> bool:
    """Проверить, настроена ли Kick OAuth интеграция."""
    return bool(config.kick_enabled and config.kick_client_id and config.kick_client_secret)


def get_kick_redirect_uri() -> str:
    """Построить redirect URI для Kick OAuth."""
    base_url = config.webapp_url.rstrip("/")
    return f"{base_url}/api/kick/callback"


def generate_kick_code_verifier() -> str:
    """Создать PKCE code_verifier для Kick OAuth 2.1."""
    # token_urlsafe already uses URL-safe characters; 64 bytes gives a verifier within RFC length limits.
    return secrets.token_urlsafe(64)


def build_kick_code_challenge(code_verifier: str) -> str:
    """Построить PKCE code_challenge (S256) для Kick OAuth."""
    digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")


def build_kick_auth_url(state: str, code_challenge: str) -> str:
    """Сформировать URL авторизации Kick."""
    authorize_url = (config.kick_authorize_url or "").strip()
    # Защита от частой ошибки конфигурации: указывают только домен без пути.
    if authorize_url.rstrip("/") in ("https://id.kick.com", "https://kick.com"):
        authorize_url = f"{authorize_url.rstrip('/')}/oauth/authorize"

    params = {
        "client_id": config.kick_client_id,
        "redirect_uri": get_kick_redirect_uri(),
        "response_type": "code",
        "scope": config.kick_scopes,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{authorize_url}?{urlencode(params)}"


async def exchange_kick_code_for_token(code: str, code_verifier: str) -> dict:
    """Обменять authorization code на Kick access token."""
    payload = {
        "client_id": config.kick_client_id,
        "client_secret": config.kick_client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": get_kick_redirect_uri(),
        "code_verifier": code_verifier,
    }
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(config.kick_token_url, data=payload)
    response.raise_for_status()
    return response.json()


async def fetch_kick_user_profile(access_token: str) -> Optional[dict]:
    """Получить профиль текущего Kick пользователя."""
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(config.kick_userinfo_url, headers=headers)
    response.raise_for_status()
    data = response.json()
    if isinstance(data, list):
        return data[0] if data else None
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
        return data["data"][0] if data["data"] else None
    return data if isinstance(data, dict) else None


async def check_kick_follow(
    access_token: str,
    user_id: str,
    target_channel_id: str,
    min_follow_days: int = 0,
) -> Optional[bool]:
    """
    Проверить фолловинг Kick канала.
    Возвращает None, если API не позволил надежно проверить условие.
    """
    endpoint = config.kick_following_url.format(user_id=user_id)
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
