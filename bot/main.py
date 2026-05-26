"""
Главный файл для запуска Telegram бота
"""
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from shared.config import config
from bot.handlers import admin, billing, contest, forum_topics
from bot.tasks.redis_listener import redis_keyspace_listener, contest_schedule_watchdog
from database.db import engine, AsyncSessionLocal
from database.models import Base


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Главная функция запуска бота"""
    # БД инициализируется через миграции Alembic в docker-entrypoint.sh
    # Не нужно создавать таблицы здесь, чтобы избежать конфликтов
    
    # Создание бота и диспетчера
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # Автоопределение forum topics должно срабатывать до command handlers.
    dp.message.outer_middleware(forum_topics.ForumTopicRecorderMiddleware())
    
    # Регистрация роутеров
    dp.include_router(billing.router)
    dp.include_router(admin.router)
    dp.include_router(contest.router)
    dp.include_router(forum_topics.router)
    
    # Запускаем слушатель событий Redis для автоматического подведения итогов
    asyncio.create_task(redis_keyspace_listener(bot))
    logger.info("Слушатель событий Redis запущен")
    asyncio.create_task(contest_schedule_watchdog(bot, interval_seconds=60))
    logger.info("Watchdog расписаний конкурсов запущен")
    
    # Восстанавливаем планирование для активных конкурсов при старте
    await restore_contest_schedules(bot)
    await restore_scheduled_publications(bot)
    
    # Запуск бота
    logger.info("Бот запущен")
    await dp.start_polling(bot)


async def restore_contest_schedules(bot: Bot):
    """
    Восстановить планирование для активных конкурсов при старте бота
    Обработать уже истекшие конкурсы
    
    @param bot экземпляр бота
    """
    from database.db import AsyncSessionLocal
    from bot.services.contest_service import ContestService
    from database.models.contest import ContestStatus
    from sqlalchemy import select
    from database.models import Contest
    from shared.services.redis_service import get_database_now_kyiv, schedule_contest_finish
    from bot.tasks.redis_listener import handle_contest_expired
    
    async with AsyncSessionLocal() as db:
        service = ContestService(db)
        
        # Получаем все активные конкурсы
        result = await db.execute(
            select(Contest)
            .where(Contest.status == ContestStatus.ACTIVE)
        )
        active_contests = result.scalars().all()
        
        if active_contests:
            logger.info(f"Восстановление планирования для {len(active_contests)} активных конкурсов")
            
            now_db = await get_database_now_kyiv()
            
            for contest in active_contests:
                # Сравниваем даты напрямую (обе naive datetime)
                # end_date уже без timezone, now_db тоже без timezone
                is_expired = contest.end_date <= now_db
                logger.info(f"Проверка конкурса {contest.id}: end_date={contest.end_date}, now={now_db}, is_expired={is_expired}")
                
                if is_expired:
                    logger.info(f"Конкурс {contest.id} уже истек, обрабатываем немедленно")
                    await handle_contest_expired(contest.id, bot)
                else:
                    # Иначе планируем на будущее
                    logger.info(f"Конкурс {contest.id} еще активен, планируем на будущее")
                    await schedule_contest_finish(contest.id, contest.end_date)
        else:
            logger.info("Активных конкурсов для планирования не найдено")


async def restore_scheduled_publications(bot: Bot):
    """
    Восстановить отложенные публикации при старте бота
    """
    from sqlalchemy import select
    from database.models import Contest
    from database.models.contest import ContestStatus
    from shared.services.redis_service import get_database_now_kyiv, schedule_contest_publish
    from bot.tasks.redis_listener import handle_contest_publish

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Contest).where(
                Contest.status == ContestStatus.DRAFT,
                Contest.publish_at.is_not(None)
            )
        )
        scheduled_contests = result.scalars().all()

        if not scheduled_contests:
            logger.info("Отложенных публикаций для восстановления не найдено")
            return

        now_db = await get_database_now_kyiv()

        for contest in scheduled_contests:
            if contest.publish_at and contest.publish_at <= now_db:
                logger.info(f"Отложенная публикация конкурса {contest.id} уже просрочена, публикуем немедленно")
                await handle_contest_publish(contest.id, bot)
            else:
                logger.info(f"Восстановлена отложенная публикация конкурса {contest.id} на {contest.publish_at}")
                await schedule_contest_publish(contest.id, contest.publish_at)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
