"""
Подписчик на события Redis для автоматического подведения итогов конкурсов
"""
import asyncio
import logging
from database.db import AsyncSessionLocal
from bot.services.contest_service import ContestService
from bot.services.draw_service import DrawService
from shared.services.redis_service import get_redis, acquire_lock, release_lock
from aiogram import Bot
from shared.config import config

logger = logging.getLogger(__name__)


async def handle_contest_expired(contest_id: int, bot: Bot):
    """
    Обработать событие истечения конкурса
    
    @param contest_id ID конкурса
    @param bot экземпляр бота
    """
    lock_key = f"contest:draw:{contest_id}"
    lock_acquired = await acquire_lock(lock_key, timeout=90)
    if not lock_acquired:
        logger.info("Розыгрыш конкурса %s уже выполняется, событие пропущено", contest_id)
        return

    try:
        async with AsyncSessionLocal() as db:
            service = ContestService(db)
            draw_service = DrawService(db)
            
            # Получаем конкурс
            contest = await service.get_contest_by_id(contest_id)
            
            if not contest:
                logger.warning("Конкурс %s не найден при обработке события истечения", contest_id)
                return
            
            # Проверяем, что конкурс еще активен (может быть уже обработан)
            from database.models.contest import ContestStatus
            if contest.status != ContestStatus.ACTIVE:
                logger.info("Конкурс %s уже обработан, статус=%s", contest_id, contest.status)
                return
            
            try:
                logger.info("Автоматическое подведение итогов конкурса %s (%s)", contest_id, contest.title)
                
                # Проводим розыгрыш
                success = await draw_service.draw_winners(contest_id)
                
                if success:
                    # Завершаем конкурс
                    await service.finish_contest(contest_id)
                    logger.info("Конкурс %s успешно завершен и розыгрыш проведен", contest_id)
                    
                    # Публикуем результаты в канал
                    from bot.handlers.contest import publish_results_to_channel
                    webapp_url = config.webapp_url.rstrip("/")
                    publish_success = await publish_results_to_channel(contest_id, bot, webapp_url)
                    
                    if publish_success:
                        logger.info("Результаты конкурса %s успешно опубликованы в канале", contest_id)
                    else:
                        logger.warning("Не удалось опубликовать результаты конкурса %s в канале", contest_id)
                else:
                    logger.warning("Не удалось провести розыгрыш для конкурса %s: недостаточно участников", contest_id)
                    # Все равно завершаем конкурс
                    await service.finish_contest(contest_id)
                    
            except Exception as e:
                logger.error("Ошибка при автоматическом подведении итогов конкурса %s: %s", contest_id, e, exc_info=True)
    finally:
        await release_lock(lock_key)


async def handle_contest_publish(contest_id: int, bot: Bot):
    """
    Обработать событие отложенной публикации конкурса
    """
    lock_key = f"publish:contest:{contest_id}"
    lock_acquired = await acquire_lock(lock_key, timeout=90)
    if not lock_acquired:
        logger.info("Публикация конкурса %s уже выполняется, событие пропущено", contest_id)
        return

    try:
        async with AsyncSessionLocal() as db:
            service = ContestService(db)
            contest = await service.get_contest_by_id(contest_id)

            if not contest:
                logger.warning("Конкурс %s не найден при отложенной публикации", contest_id)
                return

            from database.models.contest import ContestStatus
            if contest.status == ContestStatus.ACTIVE and contest.message_id:
                logger.info("Конкурс %s уже опубликован, отложенная публикация пропущена", contest_id)
                return
            if contest.status not in (ContestStatus.DRAFT, ContestStatus.ACTIVE):
                logger.info("Конкурс %s имеет статус %s, отложенная публикация пропущена", contest_id, contest.status)
                return
            if contest.status == ContestStatus.ACTIVE and not contest.message_id:
                logger.warning(
                    "Конкурс %s имеет статус active без message_id, запускаем восстановительную публикацию по расписанию",
                    contest_id,
                )

            try:
                from bot.handlers.contest import publish_contest_to_channel

                logger.info("Запуск отложенной публикации конкурса %s (%s)", contest_id, contest.title)
                webapp_url = config.webapp_url.rstrip("/")
                publish_success = await publish_contest_to_channel(contest_id, bot, webapp_url)
                if publish_success:
                    logger.info("Конкурс %s успешно опубликован по расписанию", contest_id)
                else:
                    logger.warning("Не удалось опубликовать конкурс %s по расписанию", contest_id)
            except Exception as e:
                logger.error("Ошибка при отложенной публикации конкурса %s: %s", contest_id, e, exc_info=True)
    finally:
        await release_lock(lock_key)


async def handle_results_recovery(contest_id: int, bot: Bot, reason: str) -> None:
    """
    Восстановить публикацию результатов конкурса, если статус уже выставлен,
    а message_id отсутствует.
    """
    lock_key = f"publish:results:{contest_id}"
    lock_acquired = await acquire_lock(lock_key, timeout=90)
    if not lock_acquired:
        logger.info("Публикация результатов конкурса %s уже выполняется, recovery пропущен", contest_id)
        return

    try:
        async with AsyncSessionLocal() as db:
            service = ContestService(db)
            contest = await service.get_contest_by_id(contest_id)

            if not contest:
                logger.warning("Конкурс %s не найден при восстановлении результатов", contest_id)
                return

            if contest.results_message_id:
                logger.info("Результаты конкурса %s уже имеют message_id=%s, recovery не нужен", contest_id, contest.results_message_id)
                return

            logger.warning(
                "Запуск восстановительной публикации результатов конкурса %s (%s), причина=%s",
                contest_id,
                contest.title,
                reason,
            )
            from bot.handlers.contest import publish_results_to_channel

            webapp_url = config.webapp_url.rstrip("/")
            publish_success = await publish_results_to_channel(contest_id, bot, webapp_url)
            if publish_success:
                logger.info("Восстановительная публикация результатов конкурса %s выполнена успешно", contest_id)
            else:
                logger.warning("Не удалось восстановить публикацию результатов конкурса %s", contest_id)
    finally:
        await release_lock(lock_key)


async def repair_inconsistent_contests(bot: Bot, now_db) -> None:
    """
    Пытается автоматически исправить известные неконсистентные состояния конкурсов.
    """
    from sqlalchemy import select
    from database.models import Contest, Prize
    from database.models.contest import ContestStatus

    async with AsyncSessionLocal() as db:
        service = ContestService(db)
        draw_service = DrawService(db)

        active_without_message_result = await db.execute(
            select(Contest.id).where(
                Contest.status == ContestStatus.ACTIVE,
                Contest.message_id.is_(None),
            )
        )
        active_without_message_ids = [row[0] for row in active_without_message_result.all()]
        for contest_id in active_without_message_ids:
            logger.warning(
                "Watchdog recovery: найден contest %s в состоянии active без message_id, выполняем публикацию",
                contest_id,
            )
            await handle_contest_publish(contest_id, bot)

        results_without_message_result = await db.execute(
            select(Contest.id).where(
                Contest.status == ContestStatus.RESULTS_PUBLISHED,
                Contest.results_message_id.is_(None),
            )
        )
        results_without_message_ids = [row[0] for row in results_without_message_result.all()]
        for contest_id in results_without_message_ids:
            await handle_results_recovery(contest_id, bot, reason="results_published_without_message_id")

        contests_without_winners_result = await db.execute(
            select(Contest.id)
            .join(Prize, Prize.contest_id == Contest.id)
            .where(
                Contest.status.in_([ContestStatus.FINISHED, ContestStatus.RESULTS_PUBLISHED]),
                Prize.winner_user_id.is_(None),
            )
            .distinct()
        )
        contests_without_winners_ids = [row[0] for row in contests_without_winners_result.all()]
        for contest_id in contests_without_winners_ids:
            contest = await service.get_contest_by_id(contest_id)
            if not contest:
                continue

            logger.warning(
                "Watchdog recovery: найден contest %s (%s) без назначенных победителей, запускаем draw",
                contest_id,
                contest.title,
            )
            draw_success = await draw_service.draw_winners(contest_id)
            if draw_success:
                logger.info("Watchdog recovery: победители для конкурса %s успешно восстановлены", contest_id)
                if contest.status == ContestStatus.RESULTS_PUBLISHED and not contest.results_message_id:
                    await handle_results_recovery(contest_id, bot, reason="results_published_without_winners")
            else:
                logger.warning("Watchdog recovery: не удалось восстановить победителей для конкурса %s", contest_id)

        overdue_scheduled_result = await db.execute(
            select(Contest.id).where(
                Contest.status == ContestStatus.DRAFT,
                Contest.publish_at.is_not(None),
                Contest.publish_at <= now_db,
            )
        )
        overdue_scheduled_ids = [row[0] for row in overdue_scheduled_result.all()]
        for contest_id in overdue_scheduled_ids:
            logger.warning(
                "Watchdog recovery: найден contest %s с просроченной отложенной публикацией, запускаем publish",
                contest_id,
            )
            await handle_contest_publish(contest_id, bot)


async def contest_schedule_watchdog(bot: Bot, interval_seconds: int = 60):
    """
    Периодически проверяет просроченные публикации и завершения конкурсов.
    Страховка на случай пропуска Redis keyspace событий.
    """
    from sqlalchemy import select, text
    from database.models import Contest
    from database.models.contest import ContestStatus

    logger.info("Запуск watchdog проверки расписаний конкурсов (интервал %ss)", interval_seconds)

    while True:
        try:
            async with AsyncSessionLocal() as db:
                now_result = await db.execute(text("SELECT NOW()::timestamp"))
                now_db = now_result.scalar()

                overdue_finishes_result = await db.execute(
                    select(Contest.id).where(
                        Contest.status == ContestStatus.ACTIVE,
                        Contest.end_date <= now_db,
                    )
                )
                overdue_finish_ids = [row[0] for row in overdue_finishes_result.all()]
                for contest_id in overdue_finish_ids:
                    logger.info("Watchdog: найден просроченный active конкурс %s, запускаем завершение", contest_id)
                    await handle_contest_expired(contest_id, bot)

                overdue_publishes_result = await db.execute(
                    select(Contest.id).where(
                        Contest.status == ContestStatus.DRAFT,
                        Contest.publish_at.is_not(None),
                        Contest.publish_at <= now_db,
                    )
                )
                overdue_publish_ids = [row[0] for row in overdue_publishes_result.all()]
                for contest_id in overdue_publish_ids:
                    logger.info("Watchdog: найден просроченный scheduled конкурс %s, запускаем публикацию", contest_id)
                    await handle_contest_publish(contest_id, bot)

            await repair_inconsistent_contests(bot, now_db)
        except Exception as e:
            logger.error("Ошибка в contest_schedule_watchdog: %s", e, exc_info=True)

        await asyncio.sleep(interval_seconds)


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
                            logger.info("Получено событие истечения для конкурса %s", contest_id)
                            
                            # Обрабатываем событие
                            await handle_contest_expired(contest_id, bot)
                        except (ValueError, IndexError) as e:
                            logger.error("Ошибка парсинга ключа конкурса %s: %s", key, e)
                    elif key and key.startswith('contest:publish:'):
                        try:
                            contest_id = int(key.split(':')[-1])
                            logger.info("Получено событие публикации для конкурса %s", contest_id)
                            await handle_contest_publish(contest_id, bot)
                        except (ValueError, IndexError) as e:
                            logger.error("Ошибка парсинга ключа отложенной публикации %s: %s", key, e)
            except asyncio.TimeoutError:
                # Таймаут - это нормально, продолжаем слушать
                pass
            except Exception as e:
                logger.error("Ошибка при получении сообщения из Redis: %s", e, exc_info=True)
            
    except Exception as e:
        logger.error("Критическая ошибка в слушателе Redis: %s", e, exc_info=True)
    finally:
        try:
            await pubsub.unsubscribe()
            await pubsub.close()
        except Exception as exc:
            logger.warning("Ошибка при закрытии Redis pubsub: %s", exc)
