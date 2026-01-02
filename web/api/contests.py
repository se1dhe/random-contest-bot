"""
API роуты для конкурсов
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime
from database.db import get_db
from database.models.contest import ContestStatus
from bot.services.contest_service import ContestService
from bot.services.participant_service import ParticipantService
from bot.services.draw_service import DrawService
from shared.services.telegram_service import TelegramService
from aiogram import Bot
from shared.config import config

router = APIRouter(prefix="/api/contests", tags=["contests"])


async def get_telegram_service() -> TelegramService:
    """Получить сервис Telegram"""
    bot = Bot(token=config.bot_token)
    return TelegramService(bot)


@router.get("/{contest_id}")
async def get_contest(
    contest_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить информацию о конкурсе
    
    @param contest_id ID конкурса
    @param db сессия БД
    @return информация о конкурсе
    """
    service = ContestService(db)
    contest = await service.get_contest_by_id(contest_id)
    
    if not contest:
        raise HTTPException(status_code=404, detail="Конкурс не найден")
    
    # Проверяем статус конкурса
    # Проверяем, активен ли конкурс
    if contest.status != ContestStatus.ACTIVE:
        if contest.status == ContestStatus.FINISHED or contest.status == ContestStatus.RESULTS_PUBLISHED:
            raise HTTPException(
                status_code=400,
                detail="Конкурс уже завершен"
            )
        elif contest.status == ContestStatus.DRAFT:
            raise HTTPException(
                status_code=400,
                detail="Конкурс еще не опубликован"
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Конкурс недоступен для регистрации"
            )
    
    # Проверяем, не закончился ли конкурс по дате
    if contest.end_date:
        # Получаем текущее время из БД для корректного сравнения
        from sqlalchemy import text
        result = await db.execute(text("SELECT NOW()::timestamp"))
        now_db = result.scalar()
        
        # Убираем timezone если есть (end_date хранится без timezone)
        if now_db and hasattr(now_db, 'tzinfo') and now_db.tzinfo is not None:
            from datetime import datetime
            now_db = datetime(now_db.year, now_db.month, now_db.day, now_db.hour, now_db.minute, now_db.second, now_db.microsecond)
        
        # Сравниваем даты (обе должны быть naive)
        if contest.end_date < now_db:
            raise HTTPException(
                status_code=400, 
                detail="Конкурс уже завершен"
            )
    
    # Преобразуем в словарь
    return {
        "id": contest.id,
        "title": contest.title,
        "description": contest.description,
        "channel_id": contest.channel_id,
        "channel_title": contest.channel.channel_title if contest.channel else None,
        "end_date": contest.end_date.isoformat(),
        "status": contest.status.value,
        "prize_count": contest.prize_count,
        "prizes": [
            {
                "id": prize.id,
                "place": prize.place,
                "title": prize.title,
                "description": prize.description
            }
            for prize in sorted(contest.prizes, key=lambda p: p.place)
        ],
        "sponsors": [
            {
                "id": sponsor.id,
                "channel_id": sponsor.channel_id,
                "channel_title": sponsor.channel_title,
                "channel_username": sponsor.channel_username
            }
            for sponsor in contest.sponsors
        ],
        "youtube_channel_id": contest.youtube_channel_id,
        "youtube_subscription_days_required": contest.youtube_subscription_days_required,
        "image_path": contest.image_path
    }


@router.get("/{contest_id}/info")
async def get_contest_info(
    contest_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить информацию о конкурсе без проверки статуса (для страницы результатов)
    
    @param contest_id ID конкурса
    @param db сессия БД
    @return информация о конкурсе
    """
    service = ContestService(db)
    contest = await service.get_contest_by_id(contest_id)
    
    if not contest:
        raise HTTPException(status_code=404, detail="Конкурс не найден")
    
    # Получаем количество участников
    participants_count = await service.get_participants_count(contest_id)
    
    # Преобразуем в словарь без проверки статуса
    return {
        "id": contest.id,
        "title": contest.title,
        "description": contest.description,
        "channel_id": contest.channel_id,
        "channel_title": contest.channel.channel_title if contest.channel else None,
        "end_date": contest.end_date.isoformat() if contest.end_date else None,
        "status": contest.status.value,
        "prize_count": contest.prize_count,
        "participants_count": participants_count,
        "prizes": [
            {
                "id": prize.id,
                "place": prize.place,
                "title": prize.title,
                "description": prize.description
            }
            for prize in sorted(contest.prizes, key=lambda p: p.place)
        ],
        "sponsors": [
            {
                "id": sponsor.id,
                "channel_id": sponsor.channel_id,
                "channel_title": sponsor.channel_title,
                "channel_username": sponsor.channel_username
            }
            for sponsor in contest.sponsors
        ],
        "youtube_channel_id": contest.youtube_channel_id,
        "youtube_subscription_days_required": contest.youtube_subscription_days_required,
        "image_path": contest.image_path
    }


@router.get("/{contest_id}/check-subscription")
async def check_subscription(
    contest_id: int,
    user_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    telegram_service: TelegramService = Depends(get_telegram_service)
):
    """
    Проверить подписки пользователя на каналы конкурса
    
    @param contest_id ID конкурса
    @param user_id ID пользователя
    @param db сессия БД
    @param telegram_service сервис Telegram
    @return статус подписок
    """
    service = ContestService(db)
    contest = await service.get_contest_by_id(contest_id)
    
    if not contest:
        raise HTTPException(status_code=404, detail="Конкурс не найден")
    
    # Собираем все каналы для проверки
    channel_ids = [contest.channel_id]
    if contest.sponsors:
        channel_ids.extend([sponsor.channel_id for sponsor in contest.sponsors])
    
    # Проверяем подписки
    subscriptions = await telegram_service.check_subscriptions(user_id, channel_ids)
    
    # Проверяем подписку на YouTube канал, если требуется
    youtube_subscribed = None
    if contest.youtube_channel_id:
        from web.api.youtube_auth import check_youtube_subscription, get_user_credentials
        credentials = await get_user_credentials(user_id, db)
        if credentials:
            youtube_subscribed = await check_youtube_subscription(
                user_id=user_id,
                target_channel_id=contest.youtube_channel_id,
                db=db
            )
    
    return {
        "subscriptions": subscriptions,
        "youtube_subscribed": youtube_subscribed
    }


@router.get("/{contest_id}/auto-check")
async def auto_check(
    contest_id: int,
    user_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    telegram_service: TelegramService = Depends(get_telegram_service)
):
    """
    Комплексная автоматическая проверка всех условий участия
    
    @param contest_id ID конкурса
    @param user_id ID пользователя
    @param db сессия БД
    @param telegram_service сервис Telegram
    @return статус всех условий и информация о регистрации
    """
    service = ContestService(db)
    participant_service = ParticipantService(db)
    contest = await service.get_contest_by_id(contest_id)
    
    if not contest:
        raise HTTPException(status_code=404, detail="Конкурс не найден")
    
    # 1. Проверяем регистрацию
    participant = await participant_service.get_participant(contest_id, user_id)
    if participant:
        return {
            "status": "already_registered",
            "participant": {
                "registration_number": participant.registration_number,
                "registered_at": participant.registered_at.isoformat()
            }
        }
    
    # 2. Собираем список условий
    conditions = []
    
    # Условие: Основной канал
    main_chat = await telegram_service.get_chat_info(contest.channel_id)
    conditions.append({
        "type": "telegram",
        "id": contest.channel_id,
        "title": main_chat['title'] if main_chat else "Основной канал",
        "username": main_chat['username'] if main_chat else None,
        "met": await telegram_service.check_subscription(user_id, contest.channel_id)
    })
    
    # Условие: Спонсоры
    if contest.sponsors:
        for sponsor in contest.sponsors:
            conditions.append({
                "type": "telegram",
                "id": sponsor.channel_id,
                "title": sponsor.channel_title or "Канал спонсора",
                "username": sponsor.channel_username,
                "met": await telegram_service.check_subscription(user_id, sponsor.channel_id)
            })
            
    # Условие: YouTube
    youtube_condition = None
    if contest.youtube_channel_id:
        from web.api.youtube_auth import check_youtube_subscription, get_user_credentials
        credentials = await get_user_credentials(user_id, db)
        
        youtube_met = False
        if credentials:
            youtube_met = await check_youtube_subscription(
                user_id=user_id,
                target_channel_id=contest.youtube_channel_id,
                db=db
            )
            
        youtube_condition = {
            "type": "youtube",
            "id": contest.youtube_channel_id,
            "title": "YouTube канал",
            "met": youtube_met,
            "connected": credentials is not None
        }
        conditions.append(youtube_condition)
        
    all_met = all(c['met'] for c in conditions)
    
    return {
        "status": "active",
        "all_met": all_met,
        "conditions": conditions
    }


@router.post("/{contest_id}/register")
async def register_participant(
    contest_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
    telegram_service: TelegramService = Depends(get_telegram_service)
):
    """
    Зарегистрировать участника в конкурсе
    
    @param contest_id ID конкурса
    @param data данные регистрации (user_id, username)
    @param db сессия БД
    @param telegram_service сервис Telegram
    @return информация о регистрации
    """
    user_id = data.get("user_id")
    username = data.get("username")
    
    if not user_id:
        raise HTTPException(status_code=400, detail="Не указан user_id")
    
    # Проверяем конкурс
    contest_service = ContestService(db)
    contest = await contest_service.get_contest_by_id(contest_id)
    
    if not contest:
        raise HTTPException(status_code=404, detail="Конкурс не найден")
    
    if contest.status.value != "active":
        raise HTTPException(status_code=400, detail="Конкурс не активен")
    
    # Проверяем подписки на Telegram каналы
    channel_ids = [contest.channel_id]
    if contest.sponsors:
        channel_ids.extend([sponsor.channel_id for sponsor in contest.sponsors])
    
    subscriptions = await telegram_service.check_subscriptions(user_id, channel_ids)
    all_subscribed = all(subscriptions.values())
    
    if not all_subscribed:
        raise HTTPException(status_code=400, detail="Необходимо подписаться на все каналы")
    
    # Проверяем подписку на YouTube канал, если требуется
    if contest.youtube_channel_id:
        # Используем функцию из youtube_auth для проверки подписки
        from web.api.youtube_auth import check_youtube_subscription, get_user_credentials
        from database.models import YouTubeCredentials
        from sqlalchemy import select
        
        # Проверяем, что пользователь авторизован через YouTube (проверяем БД)
        credentials = await get_user_credentials(user_id, db)
        if not credentials:
            raise HTTPException(
                status_code=400,
                detail="Для участия в конкурсе необходимо авторизоваться через YouTube"
            )
        
        # Получаем YouTube channel_id пользователя
        result = await db.execute(
            select(YouTubeCredentials).where(YouTubeCredentials.user_id == user_id)
        )
        user_youtube_creds = result.scalar_one_or_none()
        
        if not user_youtube_creds or not user_youtube_creds.youtube_channel_id:
            raise HTTPException(
                status_code=400,
                detail="Не удалось определить ваш YouTube канал"
            )
        
        user_youtube_channel_id = user_youtube_creds.youtube_channel_id
        
        # Проверяем, не используется ли этот YouTube канал другим пользователем в этом конкурсе
        # Находим всех пользователей с таким же youtube_channel_id
        result = await db.execute(
            select(YouTubeCredentials.user_id)
            .where(YouTubeCredentials.youtube_channel_id == user_youtube_channel_id)
            .where(YouTubeCredentials.user_id != user_id)
        )
        other_user_ids = [row[0] for row in result.all()]
        
        # Проверяем, не зарегистрированы ли эти пользователи в этом конкурсе
        if other_user_ids:
            from database.models import Participant
            result = await db.execute(
                select(Participant.user_id)
                .where(Participant.contest_id == contest_id)
                .where(Participant.user_id.in_(other_user_ids))
            )
            existing_participant = result.scalar_one_or_none()
            
            if existing_participant:
                raise HTTPException(
                    status_code=400,
                    detail="Этот YouTube канал уже используется другим пользователем для участия в этом конкурсе"
                )
        
        # Проверяем подписку
        is_subscribed = await check_youtube_subscription(
            user_id=user_id,
            target_channel_id=contest.youtube_channel_id,
            db=db
        )
        
        if not is_subscribed:
            days_required = contest.youtube_subscription_days_required
            if days_required > 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Необходимо быть подписанным на YouTube канал не менее {days_required} дней"
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Необходимо быть подписанным на указанный YouTube канал"
                )
    
    # Регистрируем участника
    participant_service = ParticipantService(db)
    participant = await participant_service.register_participant(
        contest_id=contest_id,
        user_id=user_id,
        username=username
    )
    
    if not participant:
        raise HTTPException(status_code=400, detail="Вы уже зарегистрированы в этом конкурсе")
    
    return {
        "registration_number": participant.registration_number,
        "registered_at": participant.registered_at.isoformat()
    }


@router.get("/{contest_id}/participants/{user_id}")
async def get_participant(
    contest_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить информацию об участнике
    
    @param contest_id ID конкурса
    @param user_id ID пользователя
    @param db сессия БД
    @return информация об участнике
    """
    service = ParticipantService(db)
    participant = await service.get_participant(contest_id, user_id)
    
    if not participant:
        raise HTTPException(status_code=404, detail="Участник не найден")
    
    return {
        "registration_number": participant.registration_number,
        "registered_at": participant.registered_at.isoformat()
    }


@router.get("/{contest_id}/winners")
async def get_winners(
    contest_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить список победителей конкурса
    
    @param contest_id ID конкурса
    @param db сессия БД
    @return список победителей
    """
    # Сначала проверяем, существует ли конкурс
    contest_service = ContestService(db)
    contest = await contest_service.get_contest_by_id(contest_id)
    
    if not contest:
        raise HTTPException(status_code=404, detail="Конкурс не найден")
    
    # Проверяем количество участников
    participants_count = await contest_service.get_participants_count(contest_id)
    prizes_count = len(contest.prizes) if contest.prizes else 0
    
    service = DrawService(db)
    winners = await service.get_winners(contest_id)
    
    if not winners:
        # Если конкурс завершен, но победители не определены
        if contest.status in [ContestStatus.FINISHED, ContestStatus.RESULTS_PUBLISHED]:
            if participants_count < prizes_count:
                raise HTTPException(
                    status_code=404,
                    detail=f"Конкурс завершен, но победители не определены: недостаточно участников (зарегистрировано: {participants_count}, требуется: {prizes_count})"
                )
            else:
                raise HTTPException(
                    status_code=404,
                    detail="Конкурс завершен, но победители еще не определены"
                )
        else:
            raise HTTPException(
                status_code=404,
                detail="Победители еще не определены"
            )
    
    return [
        {
            "place": prize.place,
            "title": prize.title,
            "description": prize.description,
            "winner_user_id": prize.winner_user_id,
            "winner_username": prize.winner_username,
            "winner_firstname": prize.winner_firstname
        }
        for prize in winners
    ]


@router.get("/{contest_id}/results-info")
async def get_results_info(
    contest_id: int,
    user_id: int = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить расширенную информацию для страницы результатов
    
    @param contest_id ID конкурса
    @param user_id ID пользователя
    @param db сессия БД
    @return информация о результатах и статусе пользователя
    """
    service = ContestService(db)
    participant_service = ParticipantService(db)
    draw_service = DrawService(db)
    
    contest = await service.get_contest_by_id(contest_id)
    if not contest:
        raise HTTPException(status_code=404, detail="Конкурс не найден")
        
    participant = await participant_service.get_participant(contest_id, user_id)
    winners = await draw_service.get_winners(contest_id)
    
    user_prize = None
    if winners:
        for prize in winners:
            if prize.winner_user_id == user_id:
                user_prize = {
                    "place": prize.place,
                    "title": prize.title
                }
    
    return {
        "status": contest.status.value,
        "is_participant": participant is not None,
        "user_prize": user_prize,
        "winners": [
            {
                "place": p.place,
                "title": p.title,
                "winner_username": p.winner_username,
                "winner_firstname": p.winner_firstname
            }
            for p in sorted(winners, key=lambda x: x.place)
        ] if winners else []
    }

