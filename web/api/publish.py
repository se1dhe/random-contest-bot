"""
API роуты для публикации конкурсов
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from database.db import get_db
from bot.services.contest_service import ContestService
from bot.handlers.contest import publish_contest_to_channel, publish_results_to_channel
from aiogram import Bot
from shared.config import config
import os

router = APIRouter(prefix="/api/publish", tags=["publish"])


def verify_admin(
    user_id: Optional[int] = Query(None),
    _auth: Optional[str] = Query(None, alias="_auth")
) -> int:
    """
    Проверить, является ли пользователь администратором через Telegram WebApp
    
    @param user_id ID пользователя
    @param _auth initData от Telegram WebApp
    @return ID администратора
    """
    from web.services.telegram_auth import verify_telegram_webapp_initdata, is_admin
    
    # Проверяем initData если передан
    if _auth:
        auth_data = verify_telegram_webapp_initdata(_auth)
        if not auth_data:
            raise HTTPException(status_code=403, detail="Невалидные данные авторизации")
        
        auth_user_id = auth_data.get('user', {}).get('id')
        if not is_admin(auth_user_id):
            raise HTTPException(status_code=403, detail="Доступ запрещен")
        
        # Используем user_id из initData
        if auth_user_id:
            return auth_user_id
    
    # Fallback на проверку по user_id (для обратной совместимости)
    if not user_id or user_id != config.admin_id:
        raise HTTPException(status_code=403, detail="Доступ запрещен")
    return user_id


@router.post("/contest/{contest_id}")
async def publish_contest(
    contest_id: int,
    user_id: int = Depends(verify_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Опубликовать конкурс в канале
    
    @param contest_id ID конкурса
    @param user_id ID администратора
    @param db сессия БД
    @return результат публикации
    """
    # Получаем URL вебаппа (ngrok или локальный)
    # В Docker окружении ngrok всегда включен и используется
    if config.ngrok_enabled and config.ngrok_domain:
        webapp_url = f"https://{config.ngrok_domain}"
    else:
        # Fallback на локальный URL
        webapp_url = os.getenv("WEBAPP_URL", "http://localhost:8000")
    
    bot = Bot(token=config.bot_token)
    
    try:
        success = await publish_contest_to_channel(contest_id, bot, webapp_url)
        if not success:
            raise HTTPException(status_code=400, detail="Не удалось опубликовать конкурс")
        
        return {"success": True, "message": "Конкурс успешно опубликован"}
    finally:
        await bot.session.close()


@router.post("/results/{contest_id}")
async def publish_results(
    contest_id: int,
    user_id: int = Depends(verify_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Опубликовать результаты конкурса в канале
    
    @param contest_id ID конкурса
    @param user_id ID администратора
    @param db сессия БД
    @return результат публикации
    """
    # Получаем URL вебаппа (ngrok или локальный)
    # В Docker окружении ngrok всегда включен и используется
    if config.ngrok_enabled and config.ngrok_domain:
        webapp_url = f"https://{config.ngrok_domain}"
    else:
        # Fallback на локальный URL
        webapp_url = os.getenv("WEBAPP_URL", "http://localhost:8000")
    
    bot = Bot(token=config.bot_token)
    
    try:
        success = await publish_results_to_channel(contest_id, bot, webapp_url)
        if not success:
            raise HTTPException(status_code=400, detail="Не удалось опубликовать результаты")
        
        return {"success": True, "message": "Результаты успешно опубликованы"}
    finally:
        await bot.session.close()

