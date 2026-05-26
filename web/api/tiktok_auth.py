"""
API роуты для OAuth авторизации через TikTok.
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
from database.models import TikTokCredentials
from shared.config import config
from shared.services.redis_service import (
    consume_oauth_state,
    store_completed_oauth_auth,
)
from shared.services.tiktok_service import (
    build_tiktok_auth_url,
    check_tiktok_follow,
    exchange_tiktok_code_for_token,
    fetch_tiktok_user_profile,
    get_tiktok_redirect_uri,
    is_tiktok_oauth_configured,
)
from web.api.oauth_common import (
    build_oauth_check_auth_response,
    build_oauth_status_payload,
    render_oauth_error,
    render_oauth_success,
    start_oauth_flow,
)
from web.api.deps import verify_telegram_user

router = APIRouter(prefix="/api/tiktok", tags=["tiktok"])
logger = logging.getLogger(__name__)

STATE_EXPIRATION_SECONDS = 600
PROVIDER = "tiktok"
PROVIDER_LABEL = "TikTok"
TIKTOK_STATUS_NOT_CONNECTED = "not_connected"
TIKTOK_STATUS_VERIFIED = "verified"
TIKTOK_STATUS_NOT_FOLLOWING = "not_following"
TIKTOK_STATUS_UNVERIFIED = "unverified"


@router.get("/status")
async def tiktok_status():
    """Проверить состояние TikTok OAuth конфигурации."""
    return build_oauth_status_payload(
        configured=is_tiktok_oauth_configured(),
        redirect_uri=get_tiktok_redirect_uri(),
    )


@router.get("/auth")
async def tiktok_auth(
    contest_id: int = Query(..., description="ID конкурса"),
    user_id: int = Query(..., description="ID пользователя Telegram"),
    auth_user_id: int = Depends(verify_telegram_user),
):
    """Начать OAuth flow TikTok."""
    if not is_tiktok_oauth_configured():
        raise HTTPException(status_code=500, detail="TikTok OAuth не настроен на сервере")
    if int(user_id) != int(auth_user_id):
        raise HTTPException(status_code=403, detail="Нельзя подключать TikTok для другого пользователя")

    return await start_oauth_flow(
        provider=PROVIDER,
        provider_label=PROVIDER_LABEL,
        contest_id=contest_id,
        user_id=user_id,
        ttl_seconds=STATE_EXPIRATION_SECONDS,
        build_auth_url=build_tiktok_auth_url,
        logger=logger,
        redirect_uri=get_tiktok_redirect_uri(),
    )


@router.get("/callback")
async def tiktok_callback(
    code: Optional[str] = Query(None, description="OAuth code"),
    state: Optional[str] = Query(None, description="OAuth state"),
    error: Optional[str] = Query(None, description="OAuth error"),
    db: AsyncSession = Depends(get_db),
):
    """Завершить OAuth flow TikTok."""
    logger.info("TikTok OAuth callback received: has_code=%s has_state=%s error=%s", bool(code), bool(state), error)
    if error:
        return render_oauth_error(PROVIDER_LABEL, f"TikTok вернул ошибку: {error}")
    if not code or not state:
        return render_oauth_error(PROVIDER_LABEL, "Отсутствуют обязательные параметры code/state.")

    state_data = await consume_oauth_state(state)
    if not state_data:
        return render_oauth_error(PROVIDER_LABEL, "Сессия OAuth истекла. Начните авторизацию заново.")
    if state_data.get("provider") not in (None, PROVIDER):
        return render_oauth_error(PROVIDER_LABEL, "Некорректный OAuth state (provider mismatch).")

    try:
        token_data = await exchange_tiktok_code_for_token(code)
        access_token = token_data.get("access_token")
        if not access_token:
            return render_oauth_error(PROVIDER_LABEL, "TikTok не вернул access_token.")

        profile = await fetch_tiktok_user_profile(access_token)
        if not profile:
            return render_oauth_error(PROVIDER_LABEL, "Не удалось получить профиль TikTok.")

        channel_id = str(profile.get("username") or profile.get("open_id") or profile.get("union_id") or "")
        channel_title = profile.get("display_name") or profile.get("username") or channel_id
        if not channel_id:
            return render_oauth_error(PROVIDER_LABEL, "Профиль TikTok не содержит идентификатор пользователя.")

        expires_at = None
        if isinstance(token_data.get("expires_in"), int):
            expires_at = datetime.utcnow() + timedelta(seconds=token_data["expires_in"])

        scopes = [item for item in (part.strip() for part in (config.tiktok_scopes or "").split(" ")) if item]

        result = await db.execute(
            select(TikTokCredentials).where(TikTokCredentials.user_id == state_data["user_id"])
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.tiktok_user_id = channel_id
            existing.tiktok_login = profile.get("username")
            existing.tiktok_display_name = profile.get("display_name")
            existing.token = access_token
            existing.refresh_token = token_data.get("refresh_token")
            existing.client_id = config.tiktok_client_id or ""
            existing.client_secret = config.tiktok_client_secret or ""
            existing.scopes = json.dumps(scopes)
            existing.expires_at = expires_at
            existing.updated_at = datetime.utcnow()
        else:
            db.add(
                TikTokCredentials(
                    user_id=state_data["user_id"],
                    tiktok_user_id=channel_id,
                    tiktok_login=profile.get("username"),
                    tiktok_display_name=profile.get("display_name"),
                    token=access_token,
                    refresh_token=token_data.get("refresh_token"),
                    client_id=config.tiktok_client_id or "",
                    client_secret=config.tiktok_client_secret or "",
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
        logger.info("TikTok OAuth success: user_id=%s tiktok_channel_id=%s", state_data["user_id"], channel_id)
        return render_oauth_success(PROVIDER_LABEL, channel_title)
    except httpx.HTTPStatusError as exc:
        response_text = exc.response.text[:500] if exc.response is not None else ""
        logger.error("TikTok OAuth HTTP status error: %s body=%s", exc, response_text, exc_info=True)
        return render_oauth_error(PROVIDER_LABEL, f"HTTP ошибка TikTok OAuth: {exc}")
    except httpx.HTTPError as exc:
        logger.error("TikTok OAuth HTTP error: %s", exc, exc_info=True)
        return render_oauth_error(PROVIDER_LABEL, f"HTTP ошибка TikTok OAuth: {exc}")
    except Exception as exc:
        logger.error("TikTok OAuth callback error: %s", exc, exc_info=True)
        return render_oauth_error(PROVIDER_LABEL, f"Внутренняя ошибка: {exc}")


@router.get("/check-auth")
async def tiktok_check_auth(
    user_id: int = Query(..., description="ID пользователя"),
    contest_id: int = Query(..., description="ID конкурса"),
    auth_user_id: int = Depends(verify_telegram_user),
    db: AsyncSession = Depends(get_db),
):
    """Проверка успешной TikTok авторизации (polling)."""
    if int(user_id) != int(auth_user_id):
        raise HTTPException(status_code=403, detail="Нельзя проверять OAuth статус другого пользователя")
    return await build_oauth_check_auth_response(
        user_id=user_id,
        contest_id=contest_id,
        provider=PROVIDER,
        db=db,
        credentials_model=TikTokCredentials,
        channel_id_getter=lambda creds: creds.tiktok_user_id,
        channel_title_getter=lambda creds: creds.tiktok_display_name or creds.tiktok_login or creds.tiktok_user_id,
    )


async def get_user_credentials(user_id: int, db: Optional[AsyncSession] = None) -> Optional[TikTokCredentials]:
    """Получить сохраненные TikTok credentials пользователя."""
    if not db:
        return None
    result = await db.execute(select(TikTokCredentials).where(TikTokCredentials.user_id == user_id))
    return result.scalar_one_or_none()


async def check_tiktok_subscription(
    user_id: int,
    target_channel_id: str,
    days_required: int = 0,
    db: Optional[AsyncSession] = None,
) -> bool:
    """Проверить фолловинг пользователя на TikTok."""
    status = await get_tiktok_subscription_status(
        user_id=user_id,
        target_channel_id=target_channel_id,
        days_required=days_required,
        db=db,
    )
    return bool(status["met"])


async def get_tiktok_subscription_status(
    user_id: int,
    target_channel_id: str,
    days_required: int = 0,
    db: Optional[AsyncSession] = None,
) -> dict:
    """Вернуть подробный статус проверки TikTok-фолловинга."""
    creds = await get_user_credentials(user_id, db)
    if not creds:
        return {"connected": False, "met": False, "status": TIKTOK_STATUS_NOT_CONNECTED}
    try:
        result = await check_tiktok_follow(
            access_token=creds.token,
            username=creds.tiktok_login or creds.tiktok_user_id,
            target_channel_id=target_channel_id,
            min_follow_days=0,
        )
        if result is None:
            return {"connected": True, "met": False, "status": TIKTOK_STATUS_UNVERIFIED}
        if result:
            return {"connected": True, "met": True, "status": TIKTOK_STATUS_VERIFIED}
        return {"connected": True, "met": False, "status": TIKTOK_STATUS_NOT_FOLLOWING}
    except Exception as exc:
        logger.warning("Не удалось проверить TikTok фолловинг user_id=%s: %s", user_id, exc)
        return {"connected": True, "met": False, "status": TIKTOK_STATUS_UNVERIFIED}
