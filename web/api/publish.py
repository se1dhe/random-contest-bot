"""
API роуты для публикации конкурсов
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database.db import get_db
from database.models.contest import ContestStatus
from bot.services.contest_service import ContestService
from bot.handlers.contest import publish_contest_to_channel, publish_results_to_channel, format_contest_message
from aiogram import Bot
from shared.config import config
import os
from shared.services.admin_audit_service import log_admin_action
from shared.services.redis_service import cancel_contest_publish, acquire_lock, release_lock
from web.api.deps import verify_admin
import logging

router = APIRouter(prefix="/api/publish", tags=["publish"])
logger = logging.getLogger(__name__)


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
    lock_key = f"publish:contest:{contest_id}"
    lock_acquired = await acquire_lock(lock_key, timeout=45)
    if not lock_acquired:
        raise HTTPException(status_code=409, detail="Публикация уже выполняется, попробуйте через несколько секунд")

    contest_service = ContestService(db)
    contest = await contest_service.get_contest_by_id(contest_id)
    if not contest:
        await release_lock(lock_key)
        raise HTTPException(status_code=404, detail="Конкурс не найден")

    if contest.status == ContestStatus.ACTIVE and contest.message_id:
        await release_lock(lock_key)
        return {"success": True, "message": "Конкурс уже опубликован"}
    if contest.status not in (ContestStatus.DRAFT, ContestStatus.ACTIVE):
        await release_lock(lock_key)
        raise HTTPException(status_code=400, detail="Публикация доступна только для черновика")
    if contest.status == ContestStatus.ACTIVE and not contest.message_id:
        logger.warning(
            "Конкурс %s имеет статус active без message_id, запускаем восстановительную публикацию",
            contest_id,
        )

    webapp_url = (os.getenv("WEBAPP_URL") or config.webapp_url).rstrip("/")
    
    bot = Bot(token=config.bot_token)
    
    try:
        logger.info("Старт публикации конкурса %s администратором %s", contest_id, user_id)
        rendered_text = None
        rendered_button_url = None
        try:
            bot_info = await bot.get_me()
            contest = await contest_service.get_contest_by_id(contest_id)
            if contest and bot_info.username:
                rendered_text, preview_keyboard = await format_contest_message(
                    contest,
                    bot,
                    bot_info.username,
                    resolve_private_links=False
                )
                if preview_keyboard.inline_keyboard and preview_keyboard.inline_keyboard[0]:
                    rendered_button_url = preview_keyboard.inline_keyboard[0][0].url
        except Exception as exc:
            logger.warning("Не удалось собрать preview публикации конкурса %s: %s", contest_id, exc)
            rendered_text = None
            rendered_button_url = None

        success = await publish_contest_to_channel(contest_id, bot, webapp_url)
        if not success:
            logger.warning("Публикация конкурса %s завершилась без отправки сообщения", contest_id)
            raise HTTPException(status_code=400, detail="Не удалось опубликовать конкурс")

        await cancel_contest_publish(contest_id)
        await log_admin_action(
            db=db,
            actor_user_id=user_id,
            action_type="contest_published",
            target_type="contest",
            target_id=str(contest_id),
            contest_id=contest_id,
            payload={
                "webapp_url": webapp_url,
                "message_thread_id": contest.message_thread_id,
                "rendered_text": rendered_text,
                "button_url": rendered_button_url,
            }
        )
        await db.commit()
        logger.info("Конкурс %s успешно опубликован", contest_id)
        return {"success": True, "message": "Конкурс успешно опубликован"}
    finally:
        await release_lock(lock_key)
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
    lock_key = f"publish:results:{contest_id}"
    lock_acquired = await acquire_lock(lock_key, timeout=45)
    if not lock_acquired:
        raise HTTPException(status_code=409, detail="Публикация результатов уже выполняется, попробуйте позже")

    contest_service = ContestService(db)
    contest = await contest_service.get_contest_by_id(contest_id)
    if not contest:
        await release_lock(lock_key)
        raise HTTPException(status_code=404, detail="Конкурс не найден")

    if contest.status == ContestStatus.RESULTS_PUBLISHED:
        await release_lock(lock_key)
        return {"success": True, "message": "Результаты уже опубликованы"}
    if contest.status not in (ContestStatus.FINISHED, ContestStatus.ACTIVE):
        await release_lock(lock_key)
        raise HTTPException(status_code=400, detail="Результаты можно публиковать только для активного или завершённого конкурса")

    webapp_url = (os.getenv("WEBAPP_URL") or config.webapp_url).rstrip("/")
    
    bot = Bot(token=config.bot_token)
    
    try:
        logger.info("Старт публикации результатов конкурса %s администратором %s", contest_id, user_id)
        success = await publish_results_to_channel(contest_id, bot, webapp_url)
        if not success:
            logger.warning("Публикация результатов конкурса %s завершилась без отправки сообщения", contest_id)
            raise HTTPException(status_code=400, detail="Не удалось опубликовать результаты")
        await log_admin_action(
            db=db,
            actor_user_id=user_id,
            action_type="contest_results_published",
            target_type="contest",
            target_id=str(contest_id),
            contest_id=contest_id,
            payload={
                "webapp_url": webapp_url,
                "message_thread_id": contest.message_thread_id,
            }
        )
        await db.commit()
        logger.info("Результаты конкурса %s успешно опубликованы", contest_id)
        return {"success": True, "message": "Результаты успешно опубликованы"}
    finally:
        await release_lock(lock_key)
        await bot.session.close()
