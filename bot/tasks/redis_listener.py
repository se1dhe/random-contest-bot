"""
Подписчик на события Redis для автоматического подведения итогов конкурсов
"""
import asyncio
import logging
import json
from database.db import AsyncSessionLocal
from bot.services.contest_service import ContestService
from bot.services.draw_service import DrawService
from shared.services.redis_service import get_redis
from aiogram import Bot
from shared.config import config

logger = logging.getLogger(__name__)


async def handle_contest_expired(contest_id: int, bot: Bot):
    """
    Обработать событие истечения конкурса
    
    @param contest_id ID конкурса
    @param bot экземпляр бота
    """
    async with AsyncSessionLocal() as db:
        service = ContestService(db)
        draw_service = DrawService(db)
        
        # Получаем конкурс
        contest = await service.get_contest_by_id(contest_id)
        
        if not contest:
            logger.warning(f"Конкурс {contest_id} не найден при обработке события истечения")
            return
        
        # Проверяем, что конкурс еще активен (может быть уже обработан)
        from database.models.contest import ContestStatus
        if contest.status != ContestStatus.ACTIVE:
            logger.info(f"Конкурс {contest_id} уже обработан, статус: {contest.status}")
            return
        
        try:
            logger.info(f"Автоматическое подведение итогов конкурса {contest_id} ({contest.title})")
            
            # Проводим розыгрыш
            success = await draw_service.draw_winners(contest_id)
            
            if success:
                # Завершаем конкурс
                await service.finish_contest(contest_id)
                logger.info(f"Конкурс {contest_id} успешно завершен и розыгрыш проведен")
                
                # Публикуем результаты в канал
                from bot.handlers.contest import publish_results_to_channel
                webapp_url = f"https://{config.ngrok_domain}" if config.ngrok_enabled and config.ngrok_domain else "http://localhost:8000"
                publish_success = await publish_results_to_channel(contest_id, bot, webapp_url)
                
                if publish_success:
                    logger.info(f"Результаты конкурса {contest_id} успешно опубликованы в канале")
                else:
                    logger.warning(f"Не удалось опубликовать результаты конкурса {contest_id} в канале")
            else:
                logger.warning(f"Не удалось провести розыгрыш для конкурса {contest_id}: недостаточно участников")
                # Все равно завершаем конкурс
                await service.finish_contest(contest_id)
                
        except Exception as e:
            logger.error(f"Ошибка при автоматическом подведении итогов конкурса {contest_id}: {e}", exc_info=True)


async def redis_keyspace_listener(bot: Bot):
    """
    Слушатель событий истечения ключей Redis (Keyspace Notifications)
    
    @param bot экземпляр бота
    """
    logger.info("Запуск слушателя событий Redis для автоматического подведения итогов")
    
    redis = await get_redis()
    pubsub = redis.pubsub()
    
    # Подписываемся на события истечения ключей (expired events)
    # Используем паттерн для ключей конкурсов
    await pubsub.psubscribe("__keyevent@0__:expired")
    
    logger.info("Слушатель Redis готов к получению событий")
    
    try:
        while True:
            try:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                
                if message and message['type'] == 'pmessage':
                    key = message['data']
                    
                    # Проверяем, что это ключ конкурса
                    if key and key.startswith('contest:finish:'):
                        try:
                            contest_id = int(key.split(':')[-1])
                            logger.info(f"Получено событие истечения для конкурса {contest_id}")
                            
                            # Обрабатываем событие
                            await handle_contest_expired(contest_id, bot)
                        except (ValueError, IndexError) as e:
                            logger.error(f"Ошибка парсинга ключа конкурса: {key}, ошибка: {e}")
            except asyncio.TimeoutError:
                # Таймаут - это нормально, продолжаем слушать
                pass
            except Exception as e:
                logger.error(f"Ошибка при получении сообщения из Redis: {e}", exc_info=True)
            
    except Exception as e:
        logger.error(f"Критическая ошибка в слушателе Redis: {e}", exc_info=True)
    finally:
        try:
            await pubsub.unsubscribe()
            await pubsub.close()
        except:
            pass

