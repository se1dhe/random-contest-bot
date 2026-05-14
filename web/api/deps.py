"""
Общие зависимости API.
"""
from typing import Optional

from fastapi import Depends, HTTPException, Query, Request

from database.db import get_db
from shared.config import config
from shared.services.subscription_service import has_active_subscription


def _extract_auth_user_id(init_data: Optional[str]) -> Optional[int]:
    if not init_data:
        return None
    from web.services.telegram_auth import verify_telegram_webapp_initdata

    auth_data = verify_telegram_webapp_initdata(init_data)
    if not auth_data:
        raise HTTPException(status_code=403, detail="Невалидные данные авторизации")

    auth_user_id = auth_data.get("user", {}).get("id")
    return int(auth_user_id) if auth_user_id else None


async def verify_telegram_user(
    request: Request,
    _auth: Optional[str] = Query(None, alias="_auth"),
) -> int:
    """
    Проверить Telegram Mini App initData и вернуть реальный user_id.
    Для пользовательских действий plain user_id из query/body не считается авторизацией.
    """
    init_data = _auth or request.headers.get("X-Telegram-Init-Data")
    auth_user_id = _extract_auth_user_id(init_data)
    if not auth_user_id:
        raise HTTPException(status_code=403, detail="Telegram авторизация обязательна")
    return auth_user_id


async def verify_admin(
    user_id: Optional[int] = Query(None),
    _auth: Optional[str] = Query(None, alias="_auth"),
    db=Depends(get_db),
) -> int:
    """
    Проверить доступ владельца к админке через Telegram WebApp.
    Глобальные ADMIN_ID(S) остаются супер-админами, остальные проходят по активной подписке.
    """
    from web.services.telegram_auth import is_admin

    auth_user_id = None
    if _auth:
        auth_user_id = _extract_auth_user_id(_auth)
    elif user_id:
        auth_user_id = user_id

    if not auth_user_id:
        raise HTTPException(status_code=403, detail="Доступ запрещен")

    if is_admin(auth_user_id) or await has_active_subscription(db, int(auth_user_id)):
        return int(auth_user_id)

    raise HTTPException(status_code=402, detail="Для управления конкурсами нужна активная подписка")
