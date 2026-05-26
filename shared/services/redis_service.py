"""
Сервис для работы с Redis
"""
import redis.asyncio as redis
import logging
from typing import Optional
from datetime import datetime
import json
from sqlalchemy import text
from database.db import AsyncSessionLocal
from shared.config import config

logger = logging.getLogger(__name__)

_redis_client: Optional[redis.Redis] = None
KYIV_TIMEZONE = "Europe/Kyiv"


async def get_redis() -> redis.Redis:
    """
    Получить клиент Redis (singleton)
    
    @return клиент Redis
    """
    global _redis_client
    
    if _redis_client is None:
        _redis_client = await redis.from_url(
            config.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        try:
            await _redis_client.config_set("notify-keyspace-events", "Ex")
        except Exception as exc:
            logger.warning("Не удалось включить Redis keyspace notifications: %s", exc)
        logger.info("Подключение к Redis установлено")
    
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


async def get_database_now_kyiv() -> datetime:
    """Return DB current time as naive Kyiv local timestamp."""
    async with AsyncSessionLocal() as db:
        now_result = await db.execute(text(f"SELECT (NOW() AT TIME ZONE '{KYIV_TIMEZONE}')::timestamp"))
        return now_result.scalar()


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
    now = await get_database_now_kyiv()
    
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


async def schedule_contest_publish(contest_id: int, publish_at: datetime):
    """
    Запланировать публикацию конкурса через Redis
    """
    redis = await get_redis()
    key = f"contest:publish:{contest_id}"

    now = await get_database_now_kyiv()

    ttl_seconds = int((publish_at - now).total_seconds())
    if ttl_seconds > 0:
        await redis.setex(key, ttl_seconds, str(contest_id))
        logger.info(f"Запланирована публикация конкурса {contest_id} через {ttl_seconds} секунд")
    else:
        await redis.setex(key, 1, str(contest_id))
        logger.warning(f"Время публикации конкурса {contest_id} уже прошло, публикация будет выполнена немедленно")


async def cancel_contest_publish(contest_id: int):
    """
    Отменить запланированную публикацию конкурса
    """
    redis = await get_redis()
    key = f"contest:publish:{contest_id}"
    await redis.delete(key)
    logger.info(f"Отменена отложенная публикация конкурса {contest_id}")


async def store_oauth_state(
    state: str,
    contest_id: int,
    user_id: int,
    ttl_seconds: int,
    provider: str = "youtube",
    extra_data: Optional[dict] = None,
):
    """
    Сохранить OAuth state в Redis с TTL.
    """
    redis = await get_redis()
    key = f"oauth:state:{state}"
    payload = {
        "contest_id": contest_id,
        "user_id": user_id,
        "provider": provider,
        "created_at": datetime.utcnow().isoformat(),
    }
    if extra_data:
        payload.update(extra_data)
    value = json.dumps(payload)
    await redis.setex(key, max(ttl_seconds, 1), value)


async def consume_oauth_state(state: str) -> Optional[dict]:
    """
    Получить и удалить OAuth state из Redis (single-use).
    """
    redis = await get_redis()
    key = f"oauth:state:{state}"
    raw = await redis.get(key)
    if raw is None:
        return None
    await redis.delete(key)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Не удалось декодировать OAuth state для ключа %s", key)
        return None


async def store_completed_oauth_auth(
    user_id: int,
    contest_id: int,
    channel_id: str,
    channel_title: str,
    ttl_seconds: int,
    provider: str = "youtube",
):
    """
    Сохранить временный статус завершенной OAuth авторизации для polling.
    """
    redis = await get_redis()
    key = f"oauth:completed:{provider}:{user_id}"
    value = json.dumps({
        "contest_id": contest_id,
        "channel_id": channel_id,
        "channel_title": channel_title,
        "provider": provider,
        "timestamp": datetime.utcnow().isoformat(),
    })
    await redis.setex(key, max(ttl_seconds, 1), value)


async def get_completed_oauth_auth(user_id: int, provider: str = "youtube") -> Optional[dict]:
    """
    Получить временный статус завершенной OAuth авторизации.
    """
    redis = await get_redis()
    key = f"oauth:completed:{provider}:{user_id}"
    raw = await redis.get(key)
    if raw is None and provider == "youtube":
        # Обратная совместимость со старым ключом без provider.
        raw = await redis.get(f"oauth:completed:{user_id}")
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Не удалось декодировать completed OAuth для ключа %s", key)
        return None


async def get_cached_channel_invite_link(channel_id: int) -> Optional[str]:
    """
    Получить закэшированную invite-ссылку канала.
    """
    redis = await get_redis()
    key = f"tg:invite:{channel_id}"
    value = await redis.get(key)
    return value if value else None


async def cache_channel_invite_link(channel_id: int, invite_link: str, ttl_seconds: int = 21600):
    """
    Сохранить invite-ссылку канала в кэш (по умолчанию 6 часов).
    """
    redis = await get_redis()
    key = f"tg:invite:{channel_id}"
    await redis.setex(key, max(ttl_seconds, 1), invite_link)
