"""
Общие зависимости API.
"""
from typing import Optional

from fastapi import Depends, HTTPException, Query

from database.db import get_db
from shared.config import config
from shared.services.subscription_service import has_active_subscription


async def verify_admin(
    user_id: Optional[int] = Query(None),
    _auth: Optional[str] = Query(None, alias="_auth"),
    db=Depends(get_db),
) -> int:
    """
    Проверить доступ владельца к админке через Telegram WebApp.
    Глобальные ADMIN_ID(S) остаются супер-админами, остальные проходят по активной подписке.
    """
    from web.services.telegram_auth import verify_telegram_webapp_initdata, is_admin

    auth_user_id = None
    if _auth:
        auth_data = verify_telegram_webapp_initdata(_auth)
        if not auth_data:
            raise HTTPException(status_code=403, detail="Невалидные данные авторизации")

        auth_user_id = auth_data.get('user', {}).get('id')
    elif user_id:
        auth_user_id = user_id

    if not auth_user_id:
        raise HTTPException(status_code=403, detail="Доступ запрещен")

    if is_admin(auth_user_id) or await has_active_subscription(db, int(auth_user_id)):
        return int(auth_user_id)

    raise HTTPException(status_code=402, detail="Для управления конкурсами нужна активная подписка")
