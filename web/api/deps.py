"""
Общие зависимости API.
"""
from typing import Optional

from fastapi import HTTPException, Query

from shared.config import config


def verify_admin(
    user_id: Optional[int] = Query(None),
    _auth: Optional[str] = Query(None, alias="_auth")
) -> int:
    """
    Проверить, является ли пользователь администратором через Telegram WebApp.
    """
    from web.services.telegram_auth import verify_telegram_webapp_initdata, is_admin

    if _auth:
        auth_data = verify_telegram_webapp_initdata(_auth)
        if not auth_data:
            raise HTTPException(status_code=403, detail="Невалидные данные авторизации")

        auth_user_id = auth_data.get('user', {}).get('id')
        if not is_admin(auth_user_id):
            raise HTTPException(status_code=403, detail="Доступ запрещен")

        if auth_user_id:
            return auth_user_id

    if not config.is_admin(user_id):
        raise HTTPException(status_code=403, detail="Доступ запрещен")
    return user_id
