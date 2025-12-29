"""
Главный файл для запуска Telegram бота
"""
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from shared.config import config
from bot.handlers import admin, contest
from bot.tasks.redis_listener import redis_keyspace_listener
from database.db import engine
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
    
    # Регистрация роутеров
    dp.include_router(admin.router)
    dp.include_router(contest.router)
    
    # Запускаем слушатель событий Redis для автоматического подведения итогов
    asyncio.create_task(redis_keyspace_listener(bot))
    logger.info("Слушатель событий Redis запущен")
    
    # Восстанавливаем планирование для активных конкурсов при старте
    await restore_contest_schedules(bot)
    
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
    from sqlalchemy import select, func
    from database.models import Contest
    from shared.services.redis_service import schedule_contest_finish
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
            
            # Получаем текущее время из БД в киевском часовом поясе (без timezone)
            # PostgreSQL настроен на Europe/Kiev, поэтому NOW() уже в киевском времени
            from sqlalchemy import text
            now_result = await db.execute(text("SELECT NOW()::timestamp"))
            now_db = now_result.scalar()
            # Убираем timezone если есть (end_date хранится без timezone)
            if now_db and hasattr(now_db, 'tzinfo') and now_db.tzinfo is not None:
                from datetime import datetime
                now_db = datetime(now_db.year, now_db.month, now_db.day, now_db.hour, now_db.minute, now_db.second, now_db.microsecond)
            
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


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")

