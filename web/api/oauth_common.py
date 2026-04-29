"""
Общие утилиты для OAuth-провайдеров web API.
"""
from typing import Callable, Optional
import logging

from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.services.redis_service import get_completed_oauth_auth, store_oauth_state


def render_oauth_error(provider_label: str, message: str) -> HTMLResponse:
    """Унифицированная HTML-страница ошибки OAuth."""
    return HTMLResponse(
        content=f"""
        <!doctype html>
        <html lang="ru">
        <head><meta charset="utf-8"><title>{provider_label} OAuth Error</title></head>
        <body style="font-family:Arial,sans-serif;padding:24px">
            <h2>Ошибка {provider_label} авторизации</h2>
            <p>{message}</p>
            <button onclick="window.close()">Закрыть</button>
        </body>
        </html>
        """,
        status_code=400,
    )


def render_oauth_success(provider_label: str, channel_title: str) -> HTMLResponse:
    """Унифицированная HTML-страница успешной OAuth авторизации."""
    return HTMLResponse(
        content=f"""
        <!doctype html>
        <html lang="ru">
        <head><meta charset="utf-8"><title>{provider_label} OAuth Success</title></head>
        <body style="font-family:Arial,sans-serif;padding:24px">
            <h2>{provider_label} подключен</h2>
            <p>Аккаунт: <strong>{channel_title}</strong></p>
            <p>Окно можно закрыть.</p>
            <script>
                setTimeout(function() {{
                    try {{ window.close(); }} catch (e) {{}}
                }}, 900);
            </script>
        </body>
        </html>
        """,
        status_code=200,
    )


def build_oauth_status_payload(configured: bool, redirect_uri: str) -> dict:
    """Стандартный payload endpoint'а статуса OAuth."""
    return {
        "configured": configured,
        "enabled": bool(configured),
        "redirect_uri": redirect_uri,
    }


async def start_oauth_flow(
    *,
    provider: str,
    provider_label: str,
    contest_id: int,
    user_id: int,
    ttl_seconds: int,
    build_auth_url: Callable[[str], str],
    logger: logging.Logger,
    extra_state: Optional[dict] = None,
    redirect_uri: Optional[str] = None,
) -> RedirectResponse:
    """Сохранить state и вернуть redirect на страницу OAuth-провайдера."""
    import secrets

    state = secrets.token_urlsafe(32)
    await store_oauth_state(
        state=state,
        contest_id=contest_id,
        user_id=user_id,
        ttl_seconds=ttl_seconds,
        provider=provider,
        extra_data=extra_state,
    )
    auth_url = build_auth_url(state)
    logger.info(
        "%s OAuth start: user_id=%s contest_id=%s redirect_uri=%s authorize_url=%s",
        provider_label,
        user_id,
        contest_id,
        redirect_uri,
        auth_url.split("?")[0],
    )
    return RedirectResponse(url=auth_url, status_code=302)


async def build_oauth_check_auth_response(
    *,
    user_id: int,
    contest_id: int,
    provider: str,
    db: AsyncSession,
    credentials_model,
    channel_id_getter: Callable[[object], str],
    channel_title_getter: Callable[[object], str],
) -> dict:
    """Унифицированная логика polling-проверки завершенной OAuth авторизации."""
    result = await db.execute(select(credentials_model).where(credentials_model.user_id == user_id))
    db_creds = result.scalar_one_or_none()
    if db_creds:
        return {
            "authenticated": True,
            "channel_id": channel_id_getter(db_creds),
            "channel_title": channel_title_getter(db_creds),
        }

    auth_data = await get_completed_oauth_auth(user_id=user_id, provider=provider)
    if auth_data and auth_data.get("contest_id") == contest_id:
        return {
            "authenticated": True,
            "channel_id": auth_data.get("channel_id"),
            "channel_title": auth_data.get("channel_title"),
        }
    return {"authenticated": False}
