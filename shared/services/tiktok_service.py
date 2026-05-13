"""
Сервисные функции для OAuth интеграции TikTok.
"""
from typing import Optional
from urllib.parse import urlencode

import httpx

from shared.config import config


def is_tiktok_oauth_configured() -> bool:
    """Проверить, настроена ли TikTok OAuth интеграция."""
    return bool(config.tiktok_enabled and config.tiktok_client_id and config.tiktok_client_secret)


def get_tiktok_redirect_uri() -> str:
    """Построить redirect URI для TikTok OAuth."""
    base_url = config.webapp_url.rstrip("/")
    return f"{base_url}/api/tiktok/callback"


def build_tiktok_auth_url(state: str) -> str:
    """Сформировать URL авторизации TikTok."""
    params = {
        "client_key": config.tiktok_client_id,
        "redirect_uri": get_tiktok_redirect_uri(),
        "response_type": "code",
        "scope": config.tiktok_scopes,
        "state": state,
    }
    return f"https://www.tiktok.com/v2/auth/authorize/?{urlencode(params)}"


async def exchange_tiktok_code_for_token(code: str) -> dict:
    """Обменять authorization code на TikTok access token."""
    token_url = "https://open.tiktokapis.com/v2/oauth/token/"
    payload = {
        "client_key": config.tiktok_client_id,
        "client_secret": config.tiktok_client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": get_tiktok_redirect_uri(),
    }
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(token_url, data=payload)
    response.raise_for_status()
    return response.json()


async def fetch_tiktok_user_profile(access_token: str) -> Optional[dict]:
    """Получить профиль текущего TikTok пользователя."""
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"fields": "open_id,union_id,avatar_url,display_name,username"}
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            "https://open.tiktokapis.com/v2/user/info/",
            headers=headers,
            params=params,
        )
    response.raise_for_status()
    data = response.json()
    user = (data.get("data") or {}).get("user") if isinstance(data, dict) else None
    return user if isinstance(user, dict) else None


async def check_tiktok_follow(
    access_token: str,
    username: str,
    target_channel_id: str,
    min_follow_days: int = 0,
) -> Optional[bool]:
    """
    Проверить, что пользователь фолловит целевой TikTok-аккаунт.

    Официальная проверка доступна через TikTok Research API и только для публичных
    пользователей 18+, у которых открыт список following. Дата начала подписки в
    этом endpoint не возвращается, поэтому min_follow_days > 0 считается
    неподтверждаемым условием.
    """
    research_token = config.tiktok_research_access_token
    if not research_token or not username:
        return None
    headers = {"Authorization": f"Bearer {research_token}", "Content-Type": "application/json"}
    payload = {"username": username.lstrip("@"), "max_count": 100}
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            "https://open.tiktokapis.com/v2/research/user/following/",
            headers=headers,
            json=payload,
        )
    response.raise_for_status()
    data = response.json().get("data") or {}
    following = data.get("user_following") or []
    if min_follow_days > 0:
        return None
    target = target_channel_id.strip().lstrip("@").lower()
    for item in following:
        candidate = str((item or {}).get("username") or "").strip().lstrip("@").lower()
        if candidate == target:
            return True
    if data.get("has_more"):
        # Не делаем вид, что проверка окончательная, если результат обрезан.
        return None
    return False
