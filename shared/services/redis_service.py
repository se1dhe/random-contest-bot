"""
Сервис для работы с Redis
"""
import redis.asyncio as redis
import logging
from typing import Optional
from datetime import datetime
from sqlalchemy import select, func
from database.db import AsyncSessionLocal
from shared.config import config

logger = logging.getLogger(__name__)

_redis_client: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    """
    Получить клиент Redis (singleton)
    
    @return клиент Redis
    """
    global _redis_client
    
    if _redis_client is None:
        redis_url = f"redis://{config.redis_host}:{config.redis_port}/{config.redis_db}"
        if config.redis_password:
            redis_url = f"redis://:{config.redis_password}@{config.redis_host}:{config.redis_port}/{config.redis_db}"
        
        _redis_client = await redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        logger.info(f"Подключение к Redis: {config.redis_host}:{config.redis_port}")
    
    return _redis_client


async def close_redis():
    """
    Закрыть соединение с Redis
    """
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None


async def acquire_lock(key: str, timeout: int = 60) -> bool:
    """
    Получить блокировку (distributed lock)
    
    @param key ключ блокировки
    @param timeout время жизни блокировки в секундах
    @return True если блокировка получена, False если уже занята
    """
    redis = await get_redis()
    lock_key = f"lock:{key}"
    
    # Пытаемся установить ключ с TTL (если ключ не существует)
    result = await redis.set(lock_key, "1", ex=timeout, nx=True)
    return result is True


async def release_lock(key: str):
    """
    Освободить блокировку
    
    @param key ключ блокировки
    """
    redis = await get_redis()
    lock_key = f"lock:{key}"
    await redis.delete(lock_key)


async def schedule_contest_finish(contest_id: int, end_date: datetime):
    """
    Запланировать автоматическое подведение итогов конкурса через Redis
    
    @param contest_id ID конкурса
    @param end_date дата окончания конкурса (без таймзоны, киевское время)
    """
    redis = await get_redis()
    key = f"contest:finish:{contest_id}"
    
    # Вычисляем TTL в секундах
    # end_date уже в киевском времени без таймзоны
    # Получаем текущее время из БД (киевское время)
    from sqlalchemy import select, func
    from database.db import AsyncSessionLocal
    
    async with AsyncSessionLocal() as db:
        # Получаем текущее время из БД в киевском часовом поясе (без timezone)
        from sqlalchemy import text
        now_result = await db.execute(text("SELECT (NOW() AT TIME ZONE 'Europe/Kiev')::timestamp"))
        now = now_result.scalar()
    
    # end_date уже без таймзоны (киевское время)
    # now тоже без таймзоны (киевское время)
    ttl_seconds = int((end_date - now).total_seconds())
    
    if ttl_seconds > 0:
        # Сохраняем ID конкурса в ключе с TTL
        # Значение не важно, важно только событие истечения
        await redis.setex(key, ttl_seconds, str(contest_id))
        hours = ttl_seconds // 3600
        minutes = (ttl_seconds % 3600) // 60
        logger.info(f"Запланировано автоматическое подведение итогов конкурса {contest_id} через {ttl_seconds} секунд ({hours}ч {minutes}м)")
    else:
        logger.warning(f"Конкурс {contest_id} уже истек, TTL = {ttl_seconds}. Подведение итогов будет выполнено немедленно.")
        # Если конкурс уже истек, обрабатываем сразу через минимальный TTL
        await redis.setex(key, 1, str(contest_id))


async def cancel_contest_finish(contest_id: int):
    """
    Отменить запланированное подведение итогов конкурса
    
    @param contest_id ID конкурса
    """
    redis = await get_redis()
    key = f"contest:finish:{contest_id}"
    await redis.delete(key)
    logger.info(f"Отменено автоматическое подведение итогов конкурса {contest_id}")

