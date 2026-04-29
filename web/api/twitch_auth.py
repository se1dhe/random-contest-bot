"""
API роуты для OAuth авторизации через Twitch.
"""
from datetime import datetime, timedelta
from typing import Optional
import logging
import json

import httpx
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.db import get_db
from database.models import TwitchCredentials
from shared.config import config
from shared.services.redis_service import (
    consume_oauth_state,
    store_completed_oauth_auth,
)
from shared.services.twitch_service import (
    build_twitch_auth_url,
    check_twitch_follow,
    exchange_twitch_code_for_token,
    fetch_twitch_user_profile,
    get_twitch_redirect_uri,
    is_twitch_oauth_configured,
)
from web.api.oauth_common import (
    build_oauth_check_auth_response,
    build_oauth_status_payload,
    render_oauth_error,
    render_oauth_success,
    start_oauth_flow,
)

router = APIRouter(prefix="/api/twitch", tags=["twitch"])
logger = logging.getLogger(__name__)

STATE_EXPIRATION_SECONDS = 600
PROVIDER = "twitch"
PROVIDER_LABEL = "Twitch"


@router.get("/status")
async def twitch_status():
    """Проверить состояние Twitch OAuth конфигурации."""
    return build_oauth_status_payload(
        configured=is_twitch_oauth_configured(),
        redirect_uri=get_twitch_redirect_uri(),
    )


@router.get("/auth")
async def twitch_auth(
    contest_id: int = Query(..., description="ID конкурса"),
    user_id: int = Query(..., description="ID пользователя Telegram"),
):
    """Начать OAuth flow Twitch."""
    if not is_twitch_oauth_configured():
        raise HTTPException(status_code=500, detail="Twitch OAuth не настроен на сервере")

    return await start_oauth_flow(
        provider=PROVIDER,
        provider_label=PROVIDER_LABEL,
        contest_id=contest_id,
        user_id=user_id,
        ttl_seconds=STATE_EXPIRATION_SECONDS,
        build_auth_url=build_twitch_auth_url,
        logger=logger,
        redirect_uri=get_twitch_redirect_uri(),
    )


@router.get("/callback")
async def twitch_callback(
    code: Optional[str] = Query(None, description="OAuth code"),
    state: Optional[str] = Query(None, description="OAuth state"),
    error: Optional[str] = Query(None, description="OAuth error"),
    db: AsyncSession = Depends(get_db),
):
    """Завершить OAuth flow Twitch."""
    logger.info("Twitch OAuth callback received: has_code=%s has_state=%s error=%s", bool(code), bool(state), error)
    if error:
        return render_oauth_error(PROVIDER_LABEL, f"Twitch вернул ошибку: {error}")
    if not code or not state:
        return render_oauth_error(PROVIDER_LABEL, "Отсутствуют обязательные параметры code/state.")

    state_data = await consume_oauth_state(state)
    if not state_data:
        return render_oauth_error(PROVIDER_LABEL, "Сессия OAuth истекла. Начните авторизацию заново.")
    if state_data.get("provider") not in (None, PROVIDER):
        return render_oauth_error(PROVIDER_LABEL, "Некорректный OAuth state (provider mismatch).")

    try:
        token_data = await exchange_twitch_code_for_token(code)
        access_token = token_data.get("access_token")
        if not access_token:
            return render_oauth_error(PROVIDER_LABEL, "Twitch не вернул access_token.")

        profile = await fetch_twitch_user_profile(access_token)
        if not profile:
            return render_oauth_error(PROVIDER_LABEL, "Не удалось получить профиль Twitch.")

        channel_id = str(profile.get("id") or "")
        channel_title = profile.get("display_name") or profile.get("login") or channel_id
        if not channel_id:
            return render_oauth_error(PROVIDER_LABEL, "Профиль Twitch не содержит channel id.")

        expires_at = None
        if isinstance(token_data.get("expires_in"), int):
            expires_at = datetime.utcnow() + timedelta(seconds=token_data["expires_in"])

        scopes = [item for item in (part.strip() for part in (config.twitch_scopes or "").split(" ")) if item]

        result = await db.execute(
            select(TwitchCredentials).where(TwitchCredentials.user_id == state_data["user_id"])
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.twitch_user_id = channel_id
            existing.twitch_login = profile.get("login")
            existing.twitch_display_name = profile.get("display_name")
            existing.token = access_token
            existing.refresh_token = token_data.get("refresh_token")
            existing.client_id = config.twitch_client_id or ""
            existing.client_secret = config.twitch_client_secret or ""
            existing.scopes = json.dumps(scopes)
            existing.expires_at = expires_at
            existing.updated_at = datetime.utcnow()
        else:
            db.add(
                TwitchCredentials(
                    user_id=state_data["user_id"],
                    twitch_user_id=channel_id,
                    twitch_login=profile.get("login"),
                    twitch_display_name=profile.get("display_name"),
                    token=access_token,
                    refresh_token=token_data.get("refresh_token"),
                    client_id=config.twitch_client_id or "",
                    client_secret=config.twitch_client_secret or "",
                    scopes=json.dumps(scopes),
                    expires_at=expires_at,
                )
            )
        await db.commit()

        await store_completed_oauth_auth(
            user_id=state_data["user_id"],
            contest_id=state_data["contest_id"],
            channel_id=channel_id,
            channel_title=channel_title,
            ttl_seconds=STATE_EXPIRATION_SECONDS,
            provider=PROVIDER,
        )
        logger.info("Twitch OAuth success: user_id=%s twitch_channel_id=%s", state_data["user_id"], channel_id)
        return render_oauth_success(PROVIDER_LABEL, channel_title)
    except httpx.HTTPStatusError as exc:
        response_text = exc.response.text[:500] if exc.response is not None else ""
        logger.error("Twitch OAuth HTTP status error: %s body=%s", exc, response_text, exc_info=True)
        return render_oauth_error(PROVIDER_LABEL, f"HTTP ошибка Twitch OAuth: {exc}")
    except httpx.HTTPError as exc:
        logger.error("Twitch OAuth HTTP error: %s", exc, exc_info=True)
        return render_oauth_error(PROVIDER_LABEL, f"HTTP ошибка Twitch OAuth: {exc}")
    except Exception as exc:
        logger.error("Twitch OAuth callback error: %s", exc, exc_info=True)
        return render_oauth_error(PROVIDER_LABEL, f"Внутренняя ошибка: {exc}")


@router.get("/check-auth")
async def twitch_check_auth(
    user_id: int = Query(..., description="ID пользователя"),
    contest_id: int = Query(..., description="ID конкурса"),
    db: AsyncSession = Depends(get_db),
):
    """Проверка успешной Twitch авторизации (polling)."""
    return await build_oauth_check_auth_response(
        user_id=user_id,
        contest_id=contest_id,
        provider=PROVIDER,
        db=db,
        credentials_model=TwitchCredentials,
        channel_id_getter=lambda creds: creds.twitch_user_id,
        channel_title_getter=lambda creds: creds.twitch_display_name or creds.twitch_login or creds.twitch_user_id,
    )


async def get_user_credentials(user_id: int, db: Optional[AsyncSession] = None) -> Optional[TwitchCredentials]:
    """Получить сохраненные Twitch credentials пользователя."""
    if not db:
        return None
    result = await db.execute(select(TwitchCredentials).where(TwitchCredentials.user_id == user_id))
    return result.scalar_one_or_none()


async def check_twitch_subscription(
    user_id: int,
    target_channel_id: str,
    days_required: int = 0,
    db: Optional[AsyncSession] = None,
) -> bool:
    """Проверить фолловинг пользователя на Twitch."""
    creds = await get_user_credentials(user_id, db)
    if not creds:
        return False
    try:
        return await check_twitch_follow(
            access_token=creds.token,
            user_id=creds.twitch_user_id,
            target_channel_id=target_channel_id,
            min_follow_days=days_required,
        )
    except Exception as exc:
        logger.warning("Не удалось проверить Twitch фолловинг user_id=%s: %s", user_id, exc)
        return False
