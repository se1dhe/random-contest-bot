"""
Сервисные функции для OAuth интеграции Twitch.
"""
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlencode

import httpx

from shared.config import config


def is_twitch_oauth_configured() -> bool:
    """Проверить, настроена ли Twitch OAuth интеграция."""
    return bool(config.twitch_enabled and config.twitch_client_id and config.twitch_client_secret)


def get_twitch_redirect_uri() -> str:
    """Построить redirect URI для Twitch OAuth."""
    base_url = config.webapp_url.rstrip("/")
    return f"{base_url}/api/twitch/callback"


def build_twitch_auth_url(state: str) -> str:
    """Сформировать URL авторизации Twitch."""
    params = {
        "client_id": config.twitch_client_id,
        "redirect_uri": get_twitch_redirect_uri(),
        "response_type": "code",
        "scope": config.twitch_scopes,
        "state": state,
        "force_verify": "true",
    }
    return f"https://id.twitch.tv/oauth2/authorize?{urlencode(params)}"


async def exchange_twitch_code_for_token(code: str) -> dict:
    """Обменять authorization code на Twitch access token."""
    token_url = "https://id.twitch.tv/oauth2/token"
    payload = {
        "client_id": config.twitch_client_id,
        "client_secret": config.twitch_client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": get_twitch_redirect_uri(),
    }
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(token_url, data=payload)
    response.raise_for_status()
    return response.json()


async def fetch_twitch_user_profile(access_token: str) -> Optional[dict]:
    """Получить профиль текущего Twitch пользователя."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Client-Id": config.twitch_client_id or "",
    }
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get("https://api.twitch.tv/helix/users", headers=headers)
    response.raise_for_status()
    data = response.json()
    users = data.get("data") or []
    if not users:
        return None
    return users[0]


async def check_twitch_follow(
    access_token: str,
    user_id: str,
    target_channel_id: str,
    min_follow_days: int = 0,
) -> bool:
    """
    Проверить, что пользователь фолловит целевой Twitch-канал.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Client-Id": config.twitch_client_id or "",
    }
    params = {"user_id": user_id, "broadcaster_id": target_channel_id}
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get("https://api.twitch.tv/helix/channels/followed", headers=headers, params=params)
    response.raise_for_status()
    payload = response.json()
    data = payload.get("data") or []
    if not data:
        return False
    if min_follow_days <= 0:
        return True
    followed_at_raw = data[0].get("followed_at")
    if not followed_at_raw:
        return False
    followed_at = datetime.fromisoformat(followed_at_raw.replace("Z", "+00:00"))
    now_utc = datetime.now(timezone.utc)
    return (now_utc - followed_at).days >= min_follow_days
