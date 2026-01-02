"""
API роуты для админки
"""
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime
from dateutil import parser as date_parser
from database.db import get_db
from bot.services.contest_service import ContestService
from bot.services.participant_service import ParticipantService
from bot.services.draw_service import DrawService
from shared.services.youtube_service import YouTubeService
from database.models import Channel, Contest, Prize, Sponsor, YoutubeChannel
from database.models.contest import ContestStatus, ContestDrawMethod
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from shared.config import config
from pydantic import BaseModel
import os
import shutil
import uuid
from pathlib import Path

router = APIRouter(prefix="/api/admin", tags=["admin"])

# Настройка папки для загрузки файлов
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


class ContestCreate(BaseModel):
    """Модель создания конкурса"""
    title: str
    description: Optional[str] = None
    channel_id: int
    end_date: str  # ISO format
    prize_count: int
    draw_method: str  # "random" or "by_activity"
    prizes: List[dict]  # [{"place": 1, "title": "...", "description": "..."}]
    sponsors: Optional[List[dict]] = None  # [{"channel_id": ..., "channel_title": ...}]
    require_youtube_subscription: bool = False  # Требовать подписку на YouTube канал
    youtube_subscription_days_required: int = 0  # Минимальное количество дней подписки
    youtube_channel_id: Optional[str] = None  # ID YouTube канала (UC...)


class YoutubeChannelCreate(BaseModel):
    """Модель создания YouTube канала"""
    channel_id: str
    title: Optional[str] = None
    description: Optional[str] = None


class ChannelCreate(BaseModel):
    """Модель создания канала"""
    channel_id: int
    channel_username: Optional[str] = None
    channel_title: str
    youtube_channel_id: Optional[str] = None  # ID YouTube канала для проверки подписки


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


@router.get("/channels")
async def get_channels(
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(verify_admin)
):
    """
    Получить список каналов
    
    @param db сессия БД
    @param admin_id ID администратора
    @return список каналов
    """
    result = await db.execute(select(Channel).where(Channel.is_active == True))
    channels = result.scalars().all()
    
    return [
        {
            "id": channel.id,
            "channel_id": channel.channel_id,
            "channel_username": channel.channel_username,
            "channel_title": channel.channel_title,
            "youtube_channel_id": channel.youtube_channel_id
        }
        for channel in channels
    ]


@router.get("/channels/resolve-username")
async def resolve_channel_username(
    username: str = Query(..., description="Username канала (без @) или ID канала"),
    admin_id: int = Depends(verify_admin)
):
    """
    Получить информацию о канале по username
    
    @param username username канала (без @)
    @param admin_id ID администратора
    @return информация о канале
    """
    from shared.services.telegram_service import TelegramService
    from aiogram import Bot
    from shared.config import config
    import logging
    
    logger = logging.getLogger(__name__)
    
    bot = None
    try:
        bot = Bot(token=config.bot_token)
        telegram_service = TelegramService(bot)
        
        # Проверяем, не является ли это ID канала (отрицательное число)
        try:
            channel_id = int(username)
            if channel_id < 0:
                # Это ID канала, получаем информацию по ID
                chat_info = await telegram_service.get_chat_info(chat_id=channel_id)
                if chat_info:
                    return {
                        "channel_id": chat_info['id'],
                        "channel_title": chat_info['title'],
                        "channel_username": chat_info.get('username')
                    }
        except ValueError:
            # Не число, значит это username
            pass
        
        # Убираем @ если есть
        username = username.lstrip('@')
        
        # Пробуем получить информацию о канале
        chat_info = await telegram_service.get_chat_info_by_username(username)
        
        if not chat_info:
            # Пробуем получить более детальную информацию об ошибке
            error_detail = f"Канал @{username} не найден"
            try:
                # Пробуем проверить доступ через get_chat_member
                bot_info = await bot.get_me()
                try:
                    member = await bot.get_chat_member(chat_id=f"@{username}", user_id=bot_info.id)
                    logger.info(f"Статус бота в канале @{username}: {member.status}")
                    
                    # Если бот администратор, пробуем получить информацию о канале
                    if str(member.status) in ['ChatMemberStatus.ADMINISTRATOR', 'ChatMemberStatus.CREATOR', 'administrator', 'creator', 'member']:
                        # Пробуем получить информацию о канале через get_chat
                        try:
                            chat = await bot.get_chat(chat_id=f"@{username}")
                            chat_info = {
                                'id': chat.id,
                                'title': chat.title or username,
                                'username': chat.username or username,
                                'type': chat.type
                            }
                            logger.info(f"Успешно получена информация о канале через get_chat: {chat_info}")
                        except Exception as e2:
                            logger.warning(f"Ошибка получения информации о канале через get_chat (может быть проблема с десериализацией): {e2}")
                            # Если get_chat не работает, используем информацию из member
                            if hasattr(member, 'chat'):
                                chat_info = {
                                    'id': member.chat.id,
                                    'title': member.chat.title or username,
                                    'username': member.chat.username or username,
                                    'type': member.chat.type
                                }
                                logger.info(f"Используем информацию из member.chat: {chat_info}")
                            else:
                                # Пробуем получить через прямой вызов API
                                try:
                                    # Используем информацию из get_chat_member - извлекаем ID канала
                                    # Для этого нужно использовать другой подход
                                    # Пробуем получить через get_chat с ID, если знаем его
                                    logger.info("Пробуем альтернативные методы получения информации о канале")
                                except Exception as e3:
                                    logger.error(f"Не удалось получить информацию о канале альтернативными методами: {e3}")
                    
                    if not chat_info:
                        error_detail = f"Бот имеет доступ к каналу @{username} (статус: {member.status}), но не удалось получить информацию о канале"
                except Exception as e:
                    logger.error(f"Ошибка проверки доступа к каналу @{username}: {e}")
                    error_detail = f"Не удалось получить доступ к каналу @{username}. Убедитесь, что бот добавлен в канал как администратор."
            except Exception as e:
                logger.error(f"Ошибка при проверке доступа: {e}")
            
            if not chat_info:
                raise HTTPException(status_code=404, detail=error_detail)
        
        return {
            "channel_id": chat_info['id'],
            "channel_title": chat_info['title'],
            "channel_username": chat_info.get('username')
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Неожиданная ошибка при получении информации о канале: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при получении информации о канале: {str(e)}"
        )
    finally:
        if bot:
            try:
                await bot.session.close()
            except Exception:
                pass


@router.post("/channels")
async def create_channel(
    data: ChannelCreate,
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(verify_admin)
):
    """
    Создать новый канал
    
    @param data данные канала
    @param db сессия БД
    @param admin_id ID администратора
    @return созданный канал
    """
    # Проверяем, не существует ли уже
    result = await db.execute(
        select(Channel).where(Channel.channel_id == data.channel_id)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        existing.is_active = True
        existing.channel_username = data.channel_username
        existing.channel_title = data.channel_title
        existing.youtube_channel_id = data.youtube_channel_id.strip() if data.youtube_channel_id else None
        await db.commit()
        await db.refresh(existing)
        return {
            "id": existing.id,
            "channel_id": existing.channel_id,
            "channel_username": existing.channel_username,
            "channel_title": existing.channel_title,
            "youtube_channel_id": existing.youtube_channel_id
        }
    
    channel = Channel(
        channel_id=data.channel_id,
        channel_username=data.channel_username,
        channel_title=data.channel_title,
        youtube_channel_id=data.youtube_channel_id.strip() if data.youtube_channel_id else None
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)
    
    return {
        "id": channel.id,
        "channel_id": channel.channel_id,
        "channel_username": channel.channel_username,
        "channel_title": channel.channel_title,
        "youtube_channel_id": channel.youtube_channel_id
    }


@router.put("/channels/{channel_id}")
async def update_channel(
    channel_id: int,
    data: ChannelCreate,
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(verify_admin)
):
    """
    Обновить канал
    
    @param channel_id ID канала
    @param data данные канала
    @param db сессия БД
    @param admin_id ID администратора
    @return обновленный канал
    """
    result = await db.execute(
        select(Channel).where(Channel.channel_id == channel_id)
    )
    channel = result.scalar_one_or_none()
    
    if not channel:
        raise HTTPException(status_code=404, detail="Канал не найден")
    
    channel.channel_username = data.channel_username
    channel.channel_title = data.channel_title
    channel.youtube_channel_id = data.youtube_channel_id.strip() if data.youtube_channel_id else None
    await db.commit()
    await db.refresh(channel)
    
    return {
        "id": channel.id,
        "channel_id": channel.channel_id,
        "channel_username": channel.channel_username,
        "channel_title": channel.channel_title,
        "youtube_channel_id": channel.youtube_channel_id
    }


@router.delete("/channels/{channel_id}")
async def delete_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(verify_admin)
):
    """
    Удалить канал (деактивировать)
    
    @param channel_id ID канала
    @param db сессия БД
    @param admin_id ID администратора
    """
    result = await db.execute(
        select(Channel).where(Channel.channel_id == channel_id)
    )
    channel = result.scalar_one_or_none()
    
    if not channel:
        raise HTTPException(status_code=404, detail="Канал не найден")
    
    channel.is_active = False
    await db.commit()
    
    return {"success": True}


@router.get("/contests")
async def get_contests(
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(verify_admin),
    status: Optional[str] = Query(None)
):
    """
    Получить список конкурсов
    
    @param db сессия БД
    @param admin_id ID администратора
    @param status фильтр по статусу
    @return список конкурсов
    """
    service = ContestService(db)
    
    # Используем подзапрос для подсчета участников вместо lazy loading
    from database.models import Participant
    
    participants_count_subquery = (
        select(func.count(Participant.id))
        .where(Participant.contest_id == Contest.id)
        .scalar_subquery()
    )
    
    if status:
        query = select(
            Contest,
            participants_count_subquery.label('participants_count')
        ).options(
            selectinload(Contest.channel)
        ).where(Contest.status == ContestStatus(status))
    else:
        query = select(
            Contest,
            participants_count_subquery.label('participants_count')
        ).options(
            selectinload(Contest.channel),
            selectinload(Contest.prizes)
        ).where(
            Contest.status != ContestStatus.FINISHED,
            Contest.status != ContestStatus.RESULTS_PUBLISHED
        )
    
    result = await db.execute(query.order_by(Contest.created_at.desc()))
    rows = result.all()
    
    return [
        {
            "id": contest.id,
            "title": contest.title,
            "channel_id": contest.channel_id,
            "channel": {
                "channel_id": contest.channel.channel_id if contest.channel else None,
                "channel_title": contest.channel.channel_title if contest.channel else None,
                "channel_username": contest.channel.channel_username if contest.channel else None
            } if contest.channel else None,
            "end_date": contest.end_date.isoformat(),
            "status": contest.status.value,
            "participants_count": participants_count or 0,
            "prize_count": contest.prize_count,
            "prizes": [
                {
                    "id": p.id,
                    "place": p.place,
                    "title": p.title
                } for p in contest.prizes
            ] if contest.prizes else []
        }
        for contest, participants_count in rows
    ]


@router.post("/contests")
async def create_contest(
    title: str = Form(...),
    description: Optional[str] = Form(None),
    channel_id: int = Form(...),
    end_date: str = Form(...),
    prize_count: int = Form(...),
    draw_method: str = Form(...),
    prizes: str = Form(...),  # JSON строка
    sponsors: Optional[str] = Form(None),  # JSON строка
    require_youtube_subscription: bool = Form(False),
    youtube_subscription_days_required: int = Form(0),
    youtube_channel_id: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(verify_admin)
):
    """
    Создать новый конкурс
    
    @param title название конкурса
    @param description описание конкурса
    @param channel_id ID канала
    @param end_date дата окончания (ISO format)
    @param prize_count количество призовых мест
    @param draw_method метод розыгрыша
    @param prizes JSON строка с призами
    @param sponsors JSON строка со спонсорами
    @param require_youtube_subscription требуется ли подписка на YouTube
    @param youtube_subscription_days_required минимальное количество дней подписки
    @param image загружаемое изображение
    @param db сессия БД
    @param admin_id ID администратора
    @return созданный конкурс
    """
    import json
    
    service = ContestService(db)
    
    # Сохраняем изображение, если загружено
    image_path = None
    if image and image.filename:
        # Проверяем расширение файла
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        file_ext = Path(image.filename).suffix.lower()
        if file_ext not in allowed_extensions:
            raise HTTPException(status_code=400, detail="Недопустимый формат изображения. Разрешены: JPG, PNG, GIF, WEBP")
        
        # Генерируем уникальное имя файла
        file_id = str(uuid.uuid4())
        filename = f"{file_id}{file_ext}"
        file_path = UPLOAD_DIR / filename
        
        # Сохраняем файл
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        
        image_path = f"uploads/{filename}"
    
    # Парсим JSON строки
    try:
        prizes_data = json.loads(prizes)
        sponsors_data = json.loads(sponsors) if sponsors else None
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Ошибка парсинга JSON: {str(e)}")
    
    # Обрабатываем дату: используем dateutil.parser для надежного парсинга
    try:
        # dateutil.parser может обработать различные форматы даты
        end_date = date_parser.parse(end_date)
        
        # Если дата без таймзоны, считаем что это киевское время
        # Сохраняем в БД как есть (PostgreSQL настроен на киевское время)
        if end_date.tzinfo is not None:
            # Если дата с таймзоной, конвертируем в киевское время
            from pytz import timezone
            kiev_tz = timezone('Europe/Kiev')
            end_date = end_date.astimezone(kiev_tz)
        
        # Убираем таймзону для сохранения в БД (TIMESTAMP WITHOUT TIME ZONE)
        # PostgreSQL интерпретирует это как локальное время (киевское)
        end_date = end_date.replace(tzinfo=None)
    except (ValueError, TypeError, AttributeError) as e:
        # Если dateutil не справился, пробуем стандартный fromisoformat
        try:
            end_date_str = data.end_date.strip()
            # Заменяем Z на +00:00 для fromisoformat
            if end_date_str.endswith('Z'):
                end_date_str = end_date_str[:-1] + '+00:00'
            # Если нет таймзоны, считаем что это киевское время
            elif '+' not in end_date_str and '-' not in end_date_str[-6:]:
                # Просто парсим как есть - PostgreSQL интерпретирует как локальное время (киевское)
                end_date = datetime.fromisoformat(end_date_str)
            else:
                end_date = datetime.fromisoformat(end_date_str)
                # Если есть таймзона, конвертируем в киевское время и убираем её
                if end_date.tzinfo is not None:
                    from pytz import timezone
                    kiev_tz = timezone('Europe/Kiev')
                    end_date = end_date.astimezone(kiev_tz)
                    end_date = end_date.replace(tzinfo=None)
        except (ValueError, AttributeError) as e2:
            raise HTTPException(
                status_code=400, 
                detail=f"Неверный формат даты: '{end_date}'. Ожидается ISO формат (например: 2024-12-31T23:59:59Z). Ошибка: {str(e2)}"
            )
    
    # Определяем метод розыгрыша
    draw_method = ContestDrawMethod.RANDOM if draw_method == "random" else ContestDrawMethod.BY_ACTIVITY
    
    # Получаем информацию о канале для получения YouTube канала
    channel_result = await db.execute(
        select(Channel).where(Channel.channel_id == channel_id)
    )
    channel = channel_result.scalar_one_or_none()
    
    if not channel:
        raise HTTPException(status_code=404, detail="Канал не найден")
    
    # Если требуется подписка на YouTube, берем YouTube канал
    final_youtube_channel_id = None
    if require_youtube_subscription:
        if youtube_channel_id:
            final_youtube_channel_id = youtube_channel_id
        elif channel.youtube_channel_id:
            final_youtube_channel_id = channel.youtube_channel_id
        else:
            raise HTTPException(
                status_code=400,
                detail="Для этого конкурса требуется подписка на YouTube канал, но YouTube канал не выбран."
            )
    
    # Создаем конкурс
    contest = await service.create_contest(
        title=title,
        channel_id=channel_id,
        end_date=end_date,
        prize_count=prize_count,
        draw_method=draw_method,
        description=description,
        youtube_channel_id=final_youtube_channel_id,
        youtube_subscription_days_required=youtube_subscription_days_required if require_youtube_subscription else 0,
        image_path=image_path
    )
    
    # Создаем призы
    for prize_data in prizes_data:
        prize = Prize(
            contest_id=contest.id,
            place=prize_data["place"],
            title=prize_data["title"],
            description=prize_data.get("description")
        )
        db.add(prize)
    
    # Создаем спонсоров
    if sponsors_data:
        for sponsor_data in sponsors_data:
            sponsor = Sponsor(
                contest_id=contest.id,
                channel_id=sponsor_data["channel_id"],
                channel_title=sponsor_data["channel_title"],
                channel_username=sponsor_data.get("channel_username")
            )
            db.add(sponsor)
    
    await db.commit()
    await db.refresh(contest)
    
    return {
        "id": contest.id,
        "title": contest.title,
        "status": contest.status.value
    }


@router.post("/contests/{contest_id}/draw")
async def draw_winners(
    contest_id: int,
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(verify_admin)
):
    """
    Провести розыгрыш призов
    
    @param contest_id ID конкурса
    @param db сессия БД
    @param admin_id ID администратора
    @return результат розыгрыша
    """
    from shared.services.contest_service import ContestService
    from database.models.contest import ContestStatus
    
    # Проверяем, что конкурс существует и активен
    contest_service = ContestService(db)
    contest = await contest_service.get_contest_by_id(contest_id)
    
    if not contest:
        raise HTTPException(status_code=404, detail="Конкурс не найден")
    
    if contest.status != ContestStatus.ACTIVE:
        raise HTTPException(
            status_code=400, 
            detail=f"Конкурс уже завершен или не опубликован. Текущий статус: {contest.status.value}"
        )
    
    # Проверяем количество участников
    participants_count = await contest_service.get_participants_count(contest_id)
    prizes_count = len(contest.prizes) if contest.prizes else 0
    
    if participants_count < prizes_count:
        raise HTTPException(
            status_code=400,
            detail=f"Недостаточно участников для розыгрыша. Зарегистрировано: {participants_count}, требуется: {prizes_count}"
        )
    
    # Проводим розыгрыш
    draw_service = DrawService(db)
    success = await draw_service.draw_winners(contest_id)
    
    if not success:
        raise HTTPException(
            status_code=400, 
            detail="Не удалось провести розыгрыш. Возможно, недостаточно участников."
        )
    
    # Получаем firstname победителей из Telegram API
    from aiogram import Bot
    from shared.config import config
    bot = Bot(token=config.bot_token)
    try:
        # Обновляем конкурс для получения призов с победителями
        await db.refresh(contest)
        prizes = sorted(contest.prizes, key=lambda p: p.place)
        winners = [p for p in prizes if p.winner_user_id]
        
        for prize in winners:
            if prize.winner_user_id:
                try:
                    # Пытаемся получить информацию о пользователе через канал
                    member = await bot.get_chat_member(chat_id=contest.channel_id, user_id=prize.winner_user_id)
                    if member.user:
                        prize.winner_firstname = member.user.first_name
                except Exception:
                    # Если не удалось получить, оставляем None
                    pass
        
        await db.commit()
    finally:
        await bot.session.close()
    
    # Обновляем статус конкурса на FINISHED
    contest.status = ContestStatus.FINISHED
    await db.commit()
    await db.refresh(contest)
    
    # Получаем победителей
    winners = await draw_service.get_winners(contest_id)
    
    return {
        "success": True,
        "winners": [
            {
                "place": prize.place,
                "title": prize.title,
                "winner_username": prize.winner_username
            }
            for prize in winners
        ]
    }


@router.delete("/contests/{contest_id}")
async def delete_contest(
    contest_id: int,
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(verify_admin)
):
    """
    Удалить конкурс
    """
    contest_service = ContestService(db)
    success = await contest_service.delete_contest(contest_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Конкурс не найден")
        
    return {"success": True}


@router.get("/contests/{contest_id}/stats")
async def get_contest_stats(
    contest_id: int,
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(verify_admin)
):
    """
    Получить статистику по конкурсу
    
    @param contest_id ID конкурса
    @param db сессия БД
    @param admin_id ID администратора
    @return статистика конкурса
    """
    service = ContestService(db)
    contest = await service.get_contest_by_id(contest_id)
    
    if not contest:
        raise HTTPException(status_code=404, detail="Конкурс не найден")
    
    participants_count = len(contest.participants) if contest.participants else 0
    
    return {
        "id": contest.id,
        "title": contest.title,
        "status": contest.status.value,
        "participants_count": participants_count,
        "prize_count": contest.prize_count,
        "end_date": contest.end_date.isoformat()
    }


@router.get("/youtube-channels")
async def get_youtube_channels(
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(verify_admin)
):
    """
    Получить список YouTube каналов
    """
    result = await db.execute(select(YoutubeChannel))
    channels = result.scalars().all()
    
    return [
        {
            "channel_id": c.channel_id,
            "title": c.title,
            "description": c.description
        }
        for c in channels
    ]


@router.post("/youtube-channels")
async def add_youtube_channel(
    data: YoutubeChannelCreate,
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(verify_admin)
):
    """
    Добавить YouTube канал
    """
    # Проверяем на существование
    result = await db.execute(
        select(YoutubeChannel).where(YoutubeChannel.channel_id == data.channel_id)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(status_code=400, detail="Такой канал уже добавлен")
    
    # Получаем информацию о канале через API
    youtube_service = YouTubeService()
    channel_info = await youtube_service.get_channel_info(data.channel_id)
    
    if channel_info:
        title = channel_info.get('title')
        description = channel_info.get('description')
    else:
        # Если не удалось получить через API, используем переданные данные
        if not data.title:
            raise HTTPException(
                status_code=400, 
                detail="Не удалось получить информацию о канале через API, и название не указано вручную"
            )
        title = data.title
        description = data.description

    channel = YoutubeChannel(
        channel_id=data.channel_id,
        title=title,
        description=description
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)
    
    return {
        "channel_id": channel.channel_id,
        "title": channel.title,
        "description": channel.description
    }

