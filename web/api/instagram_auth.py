"""
API роуты для OAuth авторизации через Instagram.
"""
from datetime import datetime, timedelta
from typing import Optional
import logging
import secrets
import json

import httpx
from fastapi import APIRouter, HTTPException, Query, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.db import get_db
from database.models import InstagramCredentials
from shared.config import config
from shared.services.instagram_service import (
    build_instagram_auth_url,
    build_instagram_code_challenge,
    check_instagram_follow,
    exchange_instagram_code_for_token,
    fetch_instagram_user_profile,
    generate_instagram_code_verifier,
    get_instagram_redirect_uri,
    is_instagram_oauth_configured,
)
from shared.services.redis_service import (
    consume_oauth_state,
    store_completed_oauth_auth,
    store_oauth_state,
)
from web.api.oauth_common import (
    build_oauth_check_auth_response,
    build_oauth_status_payload,
    render_oauth_error,
    render_oauth_success,
)

router = APIRouter(prefix="/api/instagram", tags=["instagram"])
logger = logging.getLogger(__name__)

STATE_EXPIRATION_SECONDS = 1800
PROVIDER = "instagram"
PROVIDER_LABEL = "Instagram"

INSTAGRAM_STATUS_NOT_CONNECTED = "not_connected"
INSTAGRAM_STATUS_VERIFIED = "verified"
INSTAGRAM_STATUS_NOT_FOLLOWING = "not_following"
INSTAGRAM_STATUS_UNVERIFIED = "unverified"

@router.get("/status")
async def instagram_status():
    """Проверить состояние Instagram OAuth конфигурации."""
    return build_oauth_status_payload(
        configured=is_instagram_oauth_configured(),
        redirect_uri=get_instagram_redirect_uri(),
    )


@router.get("/auth")
async def instagram_auth(
    contest_id: int = Query(..., description="ID конкурса"),
    user_id: int = Query(..., description="ID пользователя Telegram"),
):
    """Начать OAuth flow Instagram."""
    if not is_instagram_oauth_configured():
        raise HTTPException(status_code=500, detail="Instagram OAuth не настроен на сервере")

    state = secrets.token_urlsafe(32)
    code_verifier = generate_instagram_code_verifier()
    code_challenge = build_instagram_code_challenge(code_verifier)
    await store_oauth_state(
        state=state,
        contest_id=contest_id,
        user_id=user_id,
        ttl_seconds=STATE_EXPIRATION_SECONDS,
        provider="instagram",
        extra_data={"code_verifier": code_verifier},
    )

    auth_url = build_instagram_auth_url(state, code_challenge)
    logger.info(
        "Instagram OAuth start: user_id=%s contest_id=%s redirect_uri=%s authorize_url=%s pkce=%s",
        user_id,
        contest_id,
        get_instagram_redirect_uri(),
        auth_url.split("?")[0],
        "enabled",
    )
    return RedirectResponse(url=auth_url, status_code=302)


async def _handle_instagram_callback(
    code: Optional[str],
    state: Optional[str],
    error: Optional[str],
    db: AsyncSession,
) -> HTMLResponse:
    logger.info("Instagram OAuth callback received: has_code=%s has_state=%s error=%s", bool(code), bool(state), error)

    if error:
        return render_oauth_error(PROVIDER_LABEL, f"Instagram вернул ошибку: {error}")
    if not code or not state:
        return render_oauth_error(PROVIDER_LABEL, "Отсутствуют обязательные параметры code/state.")

    state_data = await consume_oauth_state(state)
    if not state_data:
        return render_oauth_error(PROVIDER_LABEL, "Сессия OAuth истекла. Начните авторизацию заново.")
    if state_data.get("provider") not in (None, PROVIDER):
        return render_oauth_error(PROVIDER_LABEL, "Некорректный OAuth state (provider mismatch).")

    try:
        code_verifier = state_data.get("code_verifier")
        if not code_verifier:
            return render_oauth_error(PROVIDER_LABEL, "Сессия авторизации повреждена: отсутствует PKCE verifier.")

        token_data = await exchange_instagram_code_for_token(code, code_verifier)
        access_token = token_data.get("access_token")
        if not access_token:
            return render_oauth_error(PROVIDER_LABEL, "Instagram не вернул access_token.")

        profile = await fetch_instagram_user_profile(access_token)
        if not profile:
            return render_oauth_error(PROVIDER_LABEL, "Не удалось получить профиль Instagram.")

        channel_id = str(
            profile.get("id")
            or profile.get("user_id")
            or profile.get("channel_id")
            or ""
        )
        channel_title = (
            profile.get("username")
            or profile.get("name")
            or profile.get("slug")
            or channel_id
        )
        if not channel_id:
            return render_oauth_error(PROVIDER_LABEL, "Профиль Instagram не содержит channel id.")

        expires_at = None
        if isinstance(token_data.get("expires_in"), int):
            expires_at = datetime.utcnow() + timedelta(seconds=token_data["expires_in"])
        scopes = [item for item in (part.strip() for part in (config.instagram_scopes or "").split(" ")) if item]

        result = await db.execute(
            select(InstagramCredentials).where(InstagramCredentials.user_id == state_data["user_id"])
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.instagram_user_id = channel_id
            existing.instagram_username = profile.get("username") or profile.get("name") or profile.get("slug")
            existing.token = access_token
            existing.refresh_token = token_data.get("refresh_token")
            existing.client_id = config.instagram_client_id or ""
            existing.client_secret = config.instagram_client_secret or ""
            existing.scopes = json.dumps(scopes)
            existing.expires_at = expires_at
            existing.updated_at = datetime.utcnow()
        else:
            db.add(
                InstagramCredentials(
                    user_id=state_data["user_id"],
                    instagram_user_id=channel_id,
                    instagram_username=profile.get("username") or profile.get("name") or profile.get("slug"),
                    token=access_token,
                    refresh_token=token_data.get("refresh_token"),
                    client_id=config.instagram_client_id or "",
                    client_secret=config.instagram_client_secret or "",
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
        logger.info("Instagram OAuth success: user_id=%s instagram_channel_id=%s", state_data["user_id"], channel_id)
        return render_oauth_success(PROVIDER_LABEL, channel_title)
    except httpx.HTTPStatusError as exc:
        response_text = exc.response.text[:500] if exc.response is not None else ""
        logger.error("Instagram OAuth HTTP status error: %s body=%s", exc, response_text, exc_info=True)
        return render_oauth_error(PROVIDER_LABEL, f"HTTP ошибка Instagram OAuth: {exc}")
    except httpx.HTTPError as exc:
        logger.error("Instagram OAuth HTTP error: %s", exc, exc_info=True)
        return render_oauth_error(PROVIDER_LABEL, f"HTTP ошибка Instagram OAuth: {exc}")
    except Exception as exc:
        logger.error("Instagram OAuth callback error: %s", exc, exc_info=True)
        return render_oauth_error(PROVIDER_LABEL, f"Внутренняя ошибка: {exc}")


@router.get("/callback")
async def instagram_callback_get(
    code: Optional[str] = Query(None, description="OAuth code"),
    state: Optional[str] = Query(None, description="OAuth state"),
    error: Optional[str] = Query(None, description="OAuth error"),
    db: AsyncSession = Depends(get_db),
):
    """Завершить OAuth flow Instagram (GET callback)."""
    return await _handle_instagram_callback(code=code, state=state, error=error, db=db)


@router.post("/callback")
async def instagram_callback_post(
    request: Request,
    code: Optional[str] = Form(None),
    state: Optional[str] = Form(None),
    error: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Завершить OAuth flow Instagram (POST callback)."""
    if not code and not state and not error:
        try:
            form = await request.form()
            code = form.get("code")
            state = form.get("state")
            error = form.get("error")
        except Exception:
            pass
    return await _handle_instagram_callback(code=code, state=state, error=error, db=db)


@router.get("/check-auth")
async def instagram_check_auth(
    user_id: int = Query(..., description="ID пользователя"),
    contest_id: int = Query(..., description="ID конкурса"),
    db: AsyncSession = Depends(get_db),
):
    """Проверка успешной Instagram авторизации (polling)."""
    return await build_oauth_check_auth_response(
        user_id=user_id,
        contest_id=contest_id,
        provider=PROVIDER,
        db=db,
        credentials_model=InstagramCredentials,
        channel_id_getter=lambda creds: creds.instagram_user_id,
        channel_title_getter=lambda creds: creds.instagram_username or creds.instagram_user_id,
    )


async def get_user_credentials(user_id: int, db: Optional[AsyncSession] = None) -> Optional[InstagramCredentials]:
    """Получить сохраненные Instagram credentials пользователя."""
    if not db:
        return None
    result = await db.execute(select(InstagramCredentials).where(InstagramCredentials.user_id == user_id))
    return result.scalar_one_or_none()


async def get_instagram_subscription_status(
    user_id: int,
    target_channel_id: str,
    days_required: int = 0,
    db: Optional[AsyncSession] = None,
) -> dict:
    """Вернуть подробный статус проверки Instagram-фолловинга."""
    creds = await get_user_credentials(user_id, db)
    if not creds:
        return {"connected": False, "met": False, "status": INSTAGRAM_STATUS_NOT_CONNECTED}

    try:
        result = await check_instagram_follow(
            access_token=creds.token,
            user_id=creds.instagram_user_id,
            target_channel_id=target_channel_id,
            min_follow_days=days_required,
        )
        if result is None:
            logger.warning("Instagram API не дал верифицируемый ответ по фолловингу для user_id=%s", user_id)
            return {"connected": True, "met": False, "status": INSTAGRAM_STATUS_UNVERIFIED}
        if result:
            return {"connected": True, "met": True, "status": INSTAGRAM_STATUS_VERIFIED}
        return {"connected": True, "met": False, "status": INSTAGRAM_STATUS_NOT_FOLLOWING}
    except Exception as exc:
        logger.warning("Не удалось проверить Instagram фолловинг user_id=%s: %s", user_id, exc)
        return {"connected": True, "met": False, "status": INSTAGRAM_STATUS_UNVERIFIED}


async def check_instagram_subscription(
    user_id: int,
    target_channel_id: str,
    days_required: int = 0,
    db: Optional[AsyncSession] = None,
) -> bool:
    """
    Проверить фолловинг пользователя на Instagram.
    """
    status = await get_instagram_subscription_status(
        user_id=user_id,
        target_channel_id=target_channel_id,
        days_required=days_required,
        db=db,
    )
    return bool(status["met"])
