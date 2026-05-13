"""
API роуты для админки
"""
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from database.db import get_db
from bot.services.contest_service import ContestService
from bot.services.participant_service import ParticipantService
from bot.services.draw_service import DrawService
from shared.services.youtube_service import YouTubeService
from database.models import Channel, Contest, Prize, Sponsor, YoutubeChannel, TikTokChannel, InstagramChannel, Participant, AdminAction, ForumTopic
from database.models.contest import ContestStatus, ContestDrawMethod
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from shared.config import config
from pydantic import BaseModel
import os
import shutil
import uuid
from pathlib import Path
from io import StringIO
import csv
import difflib
import logging
from aiogram import Bot

from shared.services.admin_audit_service import log_admin_action
from shared.services.redis_service import (
    schedule_contest_publish,
    cancel_contest_publish,
    acquire_lock,
    release_lock,
)
from web.api.deps import verify_admin
from bot.handlers.contest import (
    publish_contest_to_channel,
    publish_results_to_channel,
    edit_contest_post,
    format_contest_message,
    format_results_message,
)
from shared.i18n import normalize_language

router = APIRouter(prefix="/api/admin", tags=["admin"])
logger = logging.getLogger(__name__)

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
    require_tiktok_follow: bool = False  # Требовать фолловинг на TikTok
    tiktok_follow_days_required: int = 0
    tiktok_channel_id: Optional[str] = None
    require_instagram_follow: bool = False  # Требовать фолловинг на Instagram
    instagram_follow_days_required: int = 0
    instagram_channel_id: Optional[str] = None
    message_thread_id: Optional[int] = None


class YoutubeChannelCreate(BaseModel):
    """Модель создания YouTube канала"""
    channel_id: str
    title: Optional[str] = None
    description: Optional[str] = None


class TikTokChannelCreate(BaseModel):
    """Модель создания TikTok аккаунта"""
    channel_id: str
    title: Optional[str] = None
    description: Optional[str] = None


class InstagramChannelCreate(BaseModel):
    """Модель создания Instagram канала"""
    channel_id: str
    title: Optional[str] = None
    description: Optional[str] = None


class ChannelCreate(BaseModel):
    """Модель создания канала"""
    channel_id: int
    channel_username: Optional[str] = None
    channel_title: str
    youtube_channel_id: Optional[str] = None  # ID YouTube канала для проверки подписки


class PublishScheduleRequest(BaseModel):
    """Запрос на отложенную публикацию конкурса"""
    publish_at: str


class RepublishContestRequest(BaseModel):
    """Запрос на перепубликацию или обновление поста конкурса"""
    mode: str = "repost"  # repost | edit


class DuplicateContestRequest(BaseModel):
    """Запрос на создание копии конкурса"""
    title: Optional[str] = None
    end_date: Optional[str] = None
    include_prizes: bool = True
    include_sponsors: bool = True


class BulkContestActionRequest(BaseModel):
    """Запрос на массовое действие по конкурсам"""
    contest_ids: List[int]


async def audit_admin(
    db: AsyncSession,
    admin_id: int,
    action_type: str,
    target_type: str,
    target_id: Optional[str] = None,
    contest_id: Optional[int] = None,
    status: str = "success",
    message: Optional[str] = None,
    payload: Optional[dict] = None
) -> None:
    """Сохранить запись аудита и завершить flush."""
    await log_admin_action(
        db=db,
        actor_user_id=admin_id,
        action_type=action_type,
        target_type=target_type,
        target_id=target_id,
        contest_id=contest_id,
        status=status,
        message=message,
        payload=payload,
    )


def serialize_admin_action(action: AdminAction) -> dict:
    contest_title = None
    if action.payload and isinstance(action.payload, dict):
        raw_title = action.payload.get("title")
        if raw_title:
            contest_title = str(raw_title)
    if not contest_title and action.contest:
        contest_title = action.contest.title

    return {
        "id": action.id,
        "created_at": action.created_at.isoformat(),
        "actor_user_id": action.actor_user_id,
        "action_type": action.action_type,
        "target_type": action.target_type,
        "target_id": action.target_id,
        "status": action.status,
        "message": action.message,
        "payload": action.payload,
        "contest_title": contest_title,
    }


def build_text_diff(previous_text: str, next_text: str) -> str:
    diff_lines = difflib.unified_diff(
        previous_text.splitlines(),
        next_text.splitlines(),
        fromfile="previous",
        tofile="current",
        lineterm="",
    )
    return "\n".join(diff_lines)


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


@router.get("/channels/{channel_id}/forum-topics")
async def get_channel_forum_topics(
    channel_id: int,
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(verify_admin),
):
    """
    Получить известные топики forum-группы.
    """
    channel_result = await db.execute(
        select(Channel).where(Channel.channel_id == channel_id, Channel.is_active == True)
    )
    channel = channel_result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Канал или группа не найдены")

    topics_result = await db.execute(
        select(ForumTopic)
        .where(ForumTopic.chat_id == channel_id, ForumTopic.is_active == True)
        .order_by(ForumTopic.message_thread_id.asc())
    )
    topics = topics_result.scalars().all()

    return [
        {
            "message_thread_id": topic.message_thread_id,
            "name": topic.name,
            "icon_color": topic.icon_color,
            "icon_custom_emoji_id": topic.icon_custom_emoji_id,
        }
        for topic in topics
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
        await audit_admin(
            db,
            admin_id=admin_id,
            action_type="channel_reactivated",
            target_type="channel",
            target_id=str(existing.channel_id),
            payload={"channel_title": existing.channel_title}
        )
        await db.commit()
        return {
            "id": existing.id,
            "channel_id": existing.channel_id,
            "channel_username": existing.channel_username,
            "channel_title": existing.channel_title,
            "youtube_channel_id": existing.youtube_channel_id
        }
    
    # Проверка прав бота в канале
    from aiogram import Bot
    from shared.services.telegram_service import TelegramService
    bot = Bot(token=config.bot_token)
    try:
        bot_info = await bot.get_me()
        target = data.channel_username if data.channel_username else data.channel_id
        try:
            member = await bot.get_chat_member(chat_id=target if isinstance(target, int) else f"@{str(target).lstrip('@')}", user_id=bot_info.id)
        except Exception:
            raise HTTPException(status_code=403, detail="Бот не добавлен в канал или нет доступа")
        status_str = str(member.status)
        allowed = status_str.lower() in ['chatmemberstatus.administrator', 'chatmemberstatus.creator', 'administrator', 'creator']
        if not allowed:
            raise HTTPException(status_code=403, detail="Бот должен быть администратором канала")
    finally:
        try:
            await bot.session.close()
        except Exception:
            pass

    channel = Channel(
        channel_id=data.channel_id,
        channel_username=data.channel_username,
        channel_title=data.channel_title,
        youtube_channel_id=data.youtube_channel_id.strip() if data.youtube_channel_id else None
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)
    await audit_admin(
        db,
        admin_id=admin_id,
        action_type="channel_created",
        target_type="channel",
        target_id=str(channel.channel_id),
        payload={"channel_title": channel.channel_title}
    )
    await db.commit()
    
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
    await audit_admin(
        db,
        admin_id=admin_id,
        action_type="channel_updated",
        target_type="channel",
        target_id=str(channel.channel_id),
        payload={"channel_title": channel.channel_title}
    )
    await db.commit()
    
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
    await audit_admin(
        db,
        admin_id=admin_id,
        action_type="channel_deleted",
        target_type="channel",
        target_id=str(channel.channel_id),
        payload={"channel_title": channel.channel_title}
    )
    await db.commit()
    
    return {"success": True}


@router.get("/contests")
async def get_contests(
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(verify_admin),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    paginated: bool = Query(False),
):
    """
    Получить список конкурсов
    
    @param db сессия БД
    @param admin_id ID администратора
    @param status фильтр по статусу
    @return список конкурсов
    """
    # Используем подзапрос для подсчета участников вместо lazy loading
    from database.models import Participant
    
    participants_count_subquery = (
        select(func.count(Participant.id))
        .where(Participant.contest_id == Contest.id)
        .scalar_subquery()
    )

    filters = []
    normalized_status = (status or "").strip().lower()
    if normalized_status:
        if normalized_status == "scheduled":
            filters.append(Contest.status == ContestStatus.DRAFT)
            filters.append(Contest.publish_at.is_not(None))
        else:
            try:
                filters.append(Contest.status == ContestStatus(normalized_status))
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="Некорректный статус фильтра") from exc

    search_value = (search or "").strip()
    should_join_channel = bool(search_value)

    if search_value:
        search_pattern = f"%{search_value}%"
        filters.append(
            or_(
                Contest.title.ilike(search_pattern),
                Channel.channel_title.ilike(search_pattern),
                Channel.channel_username.ilike(search_pattern),
            )
        )

    base_query = (
        select(
            Contest,
            participants_count_subquery.label('participants_count')
        )
        .options(
            selectinload(Contest.channel),
            selectinload(Contest.prizes)
        )
    )
    if should_join_channel:
        base_query = base_query.join(Channel, Contest.channel_id == Channel.channel_id, isouter=True)
    if filters:
        base_query = base_query.where(*filters)

    if paginated:
        total_query = select(func.count(Contest.id))
        if should_join_channel:
            total_query = total_query.join(Channel, Contest.channel_id == Channel.channel_id, isouter=True)
        if filters:
            total_query = total_query.where(*filters)
        total_result = await db.execute(total_query)
        total = int(total_result.scalar() or 0)
        query = base_query.order_by(Contest.created_at.desc()).offset(offset).limit(limit)
    else:
        total = None
        query = base_query.order_by(Contest.created_at.desc())

    result = await db.execute(query)
    rows = result.all()

    items = [
        {
            "id": contest.id,
            "title": contest.title,
            "language": normalize_language(contest.language),
            "channel_id": contest.channel_id,
            "message_thread_id": contest.message_thread_id,
            "channel": {
                "channel_id": contest.channel.channel_id if contest.channel else None,
                "channel_title": contest.channel.channel_title if contest.channel else None,
                "channel_username": contest.channel.channel_username if contest.channel else None
            } if contest.channel else None,
            "end_date": contest.end_date.isoformat(),
            "status": contest.status.value,
            "publish_at": contest.publish_at.isoformat() if contest.publish_at else None,
            "participants_count": participants_count or 0,
            "prize_count": contest.prize_count,
            "require_youtube_subscription": bool(contest.youtube_channel_id),
            "youtube_subscription_days_required": contest.youtube_subscription_days_required,
            "youtube_channel_id": contest.youtube_channel_id,
            "require_tiktok_follow": bool(contest.tiktok_channel_id),
            "tiktok_follow_days_required": contest.tiktok_follow_days_required,
            "tiktok_channel_id": contest.tiktok_channel_id,
            "require_instagram_follow": bool(contest.instagram_channel_id),
            "instagram_follow_days_required": contest.instagram_follow_days_required,
            "instagram_channel_id": contest.instagram_channel_id,
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

    if paginated:
        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    return items


@router.post("/contests")
async def create_contest(
    title: str = Form(...),
    description: Optional[str] = Form(None),
    language: str = Form("ru"),
    channel_id: int = Form(...),
    end_date: str = Form(...),
    prize_count: int = Form(...),
    draw_method: str = Form(...),
    prizes: str = Form(...),  # JSON строка
    sponsors: Optional[str] = Form(None),  # JSON строка
    require_youtube_subscription: bool = Form(False),
    youtube_subscription_days_required: int = Form(0),
    youtube_channel_id: Optional[str] = Form(None),
    require_tiktok_follow: bool = Form(False),
    tiktok_follow_days_required: int = Form(0),
    tiktok_channel_id: Optional[str] = Form(None),
    require_instagram_follow: bool = Form(False),
    instagram_follow_days_required: int = Form(0),
    instagram_channel_id: Optional[str] = Form(None),
    message_thread_id: Optional[int] = Form(None),
    post_to_sponsors: bool = Form(False),
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
    @param require_tiktok_follow требуется ли фолловинг TikTok
    @param tiktok_follow_days_required минимальное количество дней фолловинга TikTok
    @param require_instagram_follow требуется ли фолловинг Instagram
    @param instagram_follow_days_required минимальное количество дней фолловинга Instagram
    @param image загружаемое изображение
    @param db сессия БД
    @param admin_id ID администратора
    @return созданный конкурс
    """
    import json
    
    service = ContestService(db)
    contest_language = normalize_language(language)
    
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

    if sponsors_data:
        sponsor_ids = [int(sponsor["channel_id"]) for sponsor in sponsors_data]
        duplicate_ids = sorted({str(cid) for cid in sponsor_ids if sponsor_ids.count(cid) > 1})
        if duplicate_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Каналы-спонсоры повторяются: {', '.join(duplicate_ids)}"
            )
        if channel_id in sponsor_ids:
            raise HTTPException(
                status_code=400,
                detail="Основной канал конкурса нельзя одновременно указывать как канал-спонсор"
            )
    
    # Обрабатываем дату: используем dateutil.parser для надежного парсинга
    try:
        original_end_date_str = end_date
        end_date = date_parser.parse(original_end_date_str)
        
        # Если дата без таймзоны, считаем что это киевское время
        # Сохраняем в БД как есть (PostgreSQL настроен на киевское время)
        if end_date.tzinfo is not None:
            # Если дата с таймзоной, конвертируем в киевское время
            from pytz import timezone
            kiev_tz = timezone('Europe/Kyiv')
            end_date = end_date.astimezone(kiev_tz)
        
        # Убираем таймзону для сохранения в БД (TIMESTAMP WITHOUT TIME ZONE)
        # PostgreSQL интерпретирует это как локальное время (киевское)
        end_date = end_date.replace(tzinfo=None)
    except (ValueError, TypeError, AttributeError) as e:
        # Если dateutil не справился, пробуем стандартный fromisoformat
        try:
            end_date_str = original_end_date_str.strip()
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
                    kiev_tz = timezone('Europe/Kyiv')
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

    final_tiktok_channel_id = None
    if require_tiktok_follow:
        if tiktok_channel_id and tiktok_channel_id.strip():
            final_tiktok_channel_id = tiktok_channel_id.strip()
        else:
            raise HTTPException(
                status_code=400,
                detail="Для этого конкурса требуется TikTok-канал, но он не указан."
            )

    final_instagram_channel_id = None
    if require_instagram_follow:
        if instagram_channel_id and instagram_channel_id.strip():
            final_instagram_channel_id = instagram_channel_id.strip()
        else:
            raise HTTPException(
                status_code=400,
                detail="Для этого конкурса требуется Instagram-канал, но он не указан."
            )

    final_message_thread_id = message_thread_id if message_thread_id and message_thread_id > 0 else None
    if final_message_thread_id:
        topic_result = await db.execute(
            select(ForumTopic).where(
                ForumTopic.chat_id == channel_id,
                ForumTopic.message_thread_id == final_message_thread_id,
            )
        )
        if not topic_result.scalar_one_or_none():
            db.add(
                ForumTopic(
                    chat_id=channel_id,
                    message_thread_id=final_message_thread_id,
                    name=f"Топик #{final_message_thread_id}",
                    is_active=True,
                )
            )
    
    # Создаем конкурс
    contest = await service.create_contest(
        title=title,
        language=contest_language,
        channel_id=channel_id,
        message_thread_id=final_message_thread_id,
        end_date=end_date,
        prize_count=prize_count,
        draw_method=draw_method,
        description=description,
        youtube_channel_id=final_youtube_channel_id,
        youtube_subscription_days_required=youtube_subscription_days_required if require_youtube_subscription else 0,
        tiktok_channel_id=final_tiktok_channel_id,
        tiktok_follow_days_required=tiktok_follow_days_required if require_tiktok_follow else 0,
        instagram_channel_id=final_instagram_channel_id,
        instagram_follow_days_required=instagram_follow_days_required if require_instagram_follow else 0,
        image_path=image_path,
        post_to_sponsors=post_to_sponsors
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
    await audit_admin(
        db,
        admin_id=admin_id,
        action_type="contest_created",
        target_type="contest",
        target_id=str(contest.id),
        contest_id=contest.id,
        payload={
            "title": contest.title,
            "language": contest.language,
            "channel_id": contest.channel_id,
            "message_thread_id": contest.message_thread_id,
            "sponsors": sponsors_data or [],
            "require_youtube_subscription": require_youtube_subscription,
            "require_tiktok_follow": require_tiktok_follow,
            "require_instagram_follow": require_instagram_follow,
        }
    )
    await db.commit()
    
    return {
        "id": contest.id,
        "title": contest.title,
        "status": contest.status.value
    }


@router.post("/contests/{contest_id}/duplicate")
async def duplicate_contest(
    contest_id: int,
    data: DuplicateContestRequest = Body(default_factory=DuplicateContestRequest),
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(verify_admin),
):
    """
    Создать новый черновик как копию существующего конкурса.
    """
    service = ContestService(db)
    source = await service.get_contest_by_id(contest_id)
    if not source:
        raise HTTPException(status_code=404, detail="Исходный конкурс не найден")

    duplicate_title = (data.title or f"{source.title} (копия)").strip()
    if not duplicate_title:
        raise HTTPException(status_code=400, detail="Название нового конкурса не может быть пустым")

    if data.end_date:
        try:
            parsed_end = date_parser.parse(data.end_date)
            if parsed_end.tzinfo is not None:
                from pytz import timezone
                parsed_end = parsed_end.astimezone(timezone('Europe/Kyiv')).replace(tzinfo=None)
            end_date = parsed_end
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Некорректный формат даты окончания") from exc
    else:
        end_date = datetime.now() + timedelta(days=7)

    new_contest = await service.create_contest(
        title=duplicate_title,
        language=normalize_language(source.language),
        channel_id=source.channel_id,
        message_thread_id=source.message_thread_id,
        end_date=end_date,
        prize_count=source.prize_count,
        draw_method=source.draw_method,
        description=source.description,
        youtube_channel_id=source.youtube_channel_id,
        youtube_subscription_days_required=source.youtube_subscription_days_required,
        tiktok_channel_id=source.tiktok_channel_id,
        tiktok_follow_days_required=source.tiktok_follow_days_required,
        instagram_channel_id=source.instagram_channel_id,
        instagram_follow_days_required=source.instagram_follow_days_required,
        image_path=source.image_path,
        post_to_sponsors=source.post_to_sponsors,
        publish_at=None,
    )

    if data.include_prizes and source.prizes:
        for source_prize in source.prizes:
            db.add(
                Prize(
                    contest_id=new_contest.id,
                    place=source_prize.place,
                    title=source_prize.title,
                    description=source_prize.description,
                )
            )

    if data.include_sponsors and source.sponsors:
        for source_sponsor in source.sponsors:
            db.add(
                Sponsor(
                    contest_id=new_contest.id,
                    channel_id=source_sponsor.channel_id,
                    channel_title=source_sponsor.channel_title,
                    channel_username=source_sponsor.channel_username,
                )
            )

    await db.commit()
    await db.refresh(new_contest)

    await audit_admin(
        db,
        admin_id=admin_id,
        action_type="contest_duplicated",
        target_type="contest",
        target_id=str(new_contest.id),
        contest_id=new_contest.id,
        payload={
            "source_contest_id": source.id,
            "source_title": source.title,
            "title": new_contest.title,
            "language": new_contest.language,
            "include_prizes": data.include_prizes,
            "include_sponsors": data.include_sponsors,
        }
    )
    await db.commit()

    return {
        "success": True,
        "contest": {
            "id": new_contest.id,
            "title": new_contest.title,
            "status": new_contest.status.value,
            "end_date": new_contest.end_date.isoformat(),
        }
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
    lock_key = f"contest:draw:{contest_id}"
    lock_acquired = await acquire_lock(lock_key, timeout=60)
    if not lock_acquired:
        raise HTTPException(status_code=409, detail="Розыгрыш уже выполняется, попробуйте позже")

    try:
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

        await audit_admin(
            db,
            admin_id=admin_id,
            action_type="contest_drawn",
            target_type="contest",
            target_id=str(contest_id),
            contest_id=contest_id,
            payload={
                "winners": [
                    {
                        "place": prize.place,
                        "winner_user_id": prize.winner_user_id,
                        "winner_username": prize.winner_username,
                    }
                    for prize in winners
                ]
            }
        )
        await db.commit()
        
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
    finally:
        await release_lock(lock_key)


@router.post("/contests/{contest_id}/repair")
async def repair_contest(
    contest_id: int,
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(verify_admin)
):
    """
    Попытаться автоматически восстановить неконсистентное состояние конкурса.
    """
    lock_key = f"contest:repair:{contest_id}"
    lock_acquired = await acquire_lock(lock_key, timeout=90)
    if not lock_acquired:
        raise HTTPException(status_code=409, detail="Восстановление уже выполняется, попробуйте позже")

    bot = Bot(token=config.bot_token)
    try:
        contest_service = ContestService(db)
        draw_service = DrawService(db)
        contest = await contest_service.get_contest_by_id(contest_id)

        if not contest:
            raise HTTPException(status_code=404, detail="Конкурс не найден")

        actions: list[str] = []
        webapp_url = config.webapp_url.rstrip("/")

        if contest.status == ContestStatus.ACTIVE and not contest.message_id:
            published = await publish_contest_to_channel(contest_id, bot, webapp_url)
            if published:
                actions.append("contest_post_restored")
            else:
                raise HTTPException(status_code=400, detail="Не удалось восстановить публикацию конкурса")

        await db.refresh(contest)
        prizes = sorted(contest.prizes or [], key=lambda prize: prize.place)
        participants_count = await contest_service.get_participants_count(contest_id)
        missing_winners = [prize for prize in prizes if not prize.winner_user_id]

        if contest.status in (ContestStatus.FINISHED, ContestStatus.RESULTS_PUBLISHED) and missing_winners:
            if participants_count < len(prizes):
                raise HTTPException(
                    status_code=400,
                    detail=f"Недостаточно участников для восстановления победителей. Зарегистрировано: {participants_count}, требуется: {len(prizes)}"
                )

            draw_success = await draw_service.draw_winners(contest_id)
            if draw_success:
                actions.append("winners_restored")
            else:
                raise HTTPException(status_code=400, detail="Не удалось восстановить победителей конкурса")

        await db.refresh(contest)
        if contest.status == ContestStatus.RESULTS_PUBLISHED and not contest.results_message_id:
            published_results = await publish_results_to_channel(contest_id, bot, webapp_url)
            if published_results:
                actions.append("results_post_restored")
            else:
                raise HTTPException(status_code=400, detail="Не удалось восстановить публикацию результатов")

        if contest.status == ContestStatus.DRAFT and contest.publish_at:
            now_result = await db.execute(select(func.now()))
            now_db = now_result.scalar()
            if now_db and getattr(now_db, "tzinfo", None) is not None:
                now_db = now_db.replace(tzinfo=None)
            if contest.publish_at <= now_db:
                published = await publish_contest_to_channel(contest_id, bot, webapp_url)
                if published:
                    actions.append("overdue_publish_recovered")
                else:
                    raise HTTPException(status_code=400, detail="Не удалось восстановить просроченную публикацию")

        if not actions:
            return {
                "success": True,
                "message": "Проблем, требующих восстановления, не найдено",
                "actions": [],
            }

        await audit_admin(
            db,
            admin_id=admin_id,
            action_type="contest_repaired",
            target_type="contest",
            target_id=str(contest_id),
            contest_id=contest_id,
            payload={"actions": actions},
        )
        await db.commit()

        return {
            "success": True,
            "message": "Восстановление выполнено",
            "actions": actions,
        }
    finally:
        await bot.session.close()
        await release_lock(lock_key)


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
    contest = await contest_service.get_contest_by_id(contest_id)
    if not contest:
        raise HTTPException(status_code=404, detail="Конкурс не найден")

    await audit_admin(
        db,
        admin_id=admin_id,
        action_type="contest_deleted",
        target_type="contest",
        target_id=str(contest_id),
        contest_id=contest_id,
        payload={"title": contest.title, "status": contest.status.value}
    )
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


@router.get("/contests/{contest_id}/preview")
async def get_contest_preview(
    contest_id: int,
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(verify_admin)
):
    """
    Получить предпросмотр поста конкурса
    """
    service = ContestService(db)
    contest = await service.get_contest_by_id(contest_id)
    if not contest:
        raise HTTPException(status_code=404, detail="Конкурс не найден")

    from aiogram import Bot
    bot = Bot(token=config.bot_token)
    try:
        bot_info = await bot.get_me()
        if not bot_info.username:
            raise HTTPException(status_code=500, detail="Не удалось получить username бота")
        text, keyboard = await format_contest_message(contest, bot, bot_info.username, resolve_private_links=False)
        button_url = None
        if keyboard.inline_keyboard and keyboard.inline_keyboard[0]:
            button_url = keyboard.inline_keyboard[0][0].url
    finally:
        await bot.session.close()

    return {
        "contest_id": contest.id,
        "title": contest.title,
        "status": contest.status.value,
        "scheduled_for": contest.publish_at.isoformat() if contest.publish_at else None,
        "text": text,
        "button_url": button_url,
        "has_image": bool(contest.image_path),
    }


@router.get("/contests/{contest_id}/republish-diff")
async def get_republish_diff(
    contest_id: int,
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(verify_admin)
):
    """
    Показать diff между последним опубликованным текстом и текущим рендером.
    """
    contest_service = ContestService(db)
    contest = await contest_service.get_contest_by_id(contest_id)
    if not contest:
        raise HTTPException(status_code=404, detail="Конкурс не найден")

    from aiogram import Bot
    bot = Bot(token=config.bot_token)
    try:
        bot_info = await bot.get_me()
        text, keyboard = await format_contest_message(contest, bot, bot_info.username, resolve_private_links=False)
        button_url = None
        if keyboard.inline_keyboard and keyboard.inline_keyboard[0]:
            button_url = keyboard.inline_keyboard[0][0].url
    finally:
        await bot.session.close()

    latest_action_result = await db.execute(
        select(AdminAction)
        .where(
            AdminAction.contest_id == contest_id,
            AdminAction.action_type.in_(["contest_published", "contest_republished", "contest_post_edited"])
        )
        .order_by(AdminAction.created_at.desc())
        .limit(1)
    )
    latest_action = latest_action_result.scalar_one_or_none()
    previous_text = ""
    has_baseline = False
    if latest_action and latest_action.payload and isinstance(latest_action.payload, dict):
        previous_text = str(latest_action.payload.get("rendered_text") or "")
        has_baseline = bool(previous_text)

    diff_text = build_text_diff(previous_text, text)
    return {
        "contest_id": contest.id,
        "title": contest.title,
        "previous_text": previous_text,
        "current_text": text,
        "button_url": button_url,
        "diff": diff_text,
        "has_changes": previous_text != text,
        "has_baseline": has_baseline,
    }


@router.get("/contests/{contest_id}/results-preview")
async def get_results_preview(
    contest_id: int,
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(verify_admin)
):
    """
    Получить черновик результатов конкурса перед публикацией
    """
    service = ContestService(db)
    contest = await service.get_contest_by_id(contest_id)
    if not contest:
        raise HTTPException(status_code=404, detail="Конкурс не найден")

    from aiogram import Bot
    bot = Bot(token=config.bot_token)
    try:
        bot_info = await bot.get_me()
        if not bot_info.username:
            raise HTTPException(status_code=500, detail="Не удалось получить username бота")
        text, keyboard = format_results_message(contest, bot_info.username)
        button_url = None
        if keyboard.inline_keyboard and keyboard.inline_keyboard[0]:
            button_url = keyboard.inline_keyboard[0][0].url
    finally:
        await bot.session.close()

    winners = [
        {
            "place": prize.place,
            "title": prize.title,
            "winner_user_id": prize.winner_user_id,
            "winner_username": prize.winner_username,
            "winner_firstname": prize.winner_firstname,
        }
        for prize in sorted(contest.prizes, key=lambda p: p.place)
        if prize.winner_user_id
    ]

    return {
        "contest_id": contest.id,
        "title": contest.title,
        "status": contest.status.value,
        "text": text,
        "button_url": button_url,
        "winners": winners,
    }


@router.get("/contests/{contest_id}/history")
async def get_contest_history(
    contest_id: int,
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(verify_admin)
):
    """
    Получить историю действий по конкурсу
    """
    result = await db.execute(
        select(AdminAction)
        .options(selectinload(AdminAction.contest))
        .where(AdminAction.contest_id == contest_id)
        .order_by(AdminAction.created_at.desc())
    )
    actions = result.scalars().all()

    return [serialize_admin_action(action) for action in actions]


@router.get("/actions/recent")
async def get_recent_admin_actions(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(verify_admin)
):
    """
    Получить последние действия администратора по всему проекту
    """
    result = await db.execute(
        select(AdminAction)
        .options(selectinload(AdminAction.contest))
        .order_by(AdminAction.created_at.desc())
        .limit(limit)
    )
    actions = result.scalars().all()
    return [serialize_admin_action(action) for action in actions]


@router.get("/contests/{contest_id}/participants/export")
async def export_contest_participants(
    contest_id: int,
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(verify_admin)
):
    """
    Экспорт участников конкурса в CSV
    """
    contest_service = ContestService(db)
    contest = await contest_service.get_contest_by_id(contest_id)
    if not contest:
        raise HTTPException(status_code=404, detail="Конкурс не найден")

    participants = sorted(contest.participants, key=lambda participant: participant.registration_number)
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "registration_number",
        "user_id",
        "username",
        "first_name",
        "last_name",
        "registered_at",
        "activity_score",
    ])
    for participant in participants:
        writer.writerow([
            participant.registration_number,
            participant.user_id,
            participant.username or "",
            participant.first_name or "",
            participant.last_name or "",
            participant.registered_at.isoformat() if participant.registered_at else "",
            participant.activity_score,
        ])
    buffer.seek(0)

    await audit_admin(
        db,
        admin_id=admin_id,
        action_type="contest_participants_exported",
        target_type="contest",
        target_id=str(contest_id),
        contest_id=contest_id,
        payload={"participants_count": len(participants)}
    )
    await db.commit()

    filename = f"contest_{contest_id}_participants.csv"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv; charset=utf-8", headers=headers)


@router.post("/contests/{contest_id}/schedule-publish")
async def schedule_contest_publication(
    contest_id: int,
    data: PublishScheduleRequest,
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(verify_admin)
):
    """
    Запланировать публикацию конкурса
    """
    service = ContestService(db)
    contest = await service.get_contest_by_id(contest_id)
    if not contest:
        raise HTTPException(status_code=404, detail="Конкурс не найден")
    if contest.status != ContestStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Отложенная публикация доступна только для черновиков")

    try:
        publish_at = date_parser.parse(data.publish_at)
        if publish_at.tzinfo is not None:
            from pytz import timezone
            publish_at = publish_at.astimezone(timezone('Europe/Kyiv')).replace(tzinfo=None)
    except (ValueError, TypeError) as e:
        raise HTTPException(status_code=400, detail=f"Неверный формат даты публикации: {e}")

    now_result = await db.execute(select(func.now()))
    now_db = now_result.scalar()
    if now_db and getattr(now_db, "tzinfo", None) is not None:
        publish_at_now_compare = publish_at
        now_db = now_db.replace(tzinfo=None)
    else:
        publish_at_now_compare = publish_at

    if publish_at_now_compare <= now_db:
        raise HTTPException(status_code=400, detail="Дата отложенной публикации должна быть позже текущего времени")

    await service.schedule_publish(contest_id, publish_at)
    await schedule_contest_publish(contest_id, publish_at)
    await audit_admin(
        db,
        admin_id=admin_id,
        action_type="contest_publish_scheduled",
        target_type="contest",
        target_id=str(contest_id),
        contest_id=contest_id,
        payload={"publish_at": publish_at.isoformat()}
    )
    await db.commit()

    return {"success": True, "publish_at": publish_at.isoformat()}


@router.post("/contests/{contest_id}/cancel-schedule-publish")
async def cancel_scheduled_contest_publication(
    contest_id: int,
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(verify_admin)
):
    """
    Отменить отложенную публикацию конкурса
    """
    service = ContestService(db)
    contest = await service.get_contest_by_id(contest_id)
    if not contest:
        raise HTTPException(status_code=404, detail="Конкурс не найден")
    if contest.status != ContestStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Отменить публикацию можно только у черновика")
    if not contest.publish_at:
        raise HTTPException(status_code=400, detail="У конкурса нет активной отложенной публикации")

    contest.publish_at = None
    await db.commit()
    await cancel_contest_publish(contest_id)
    await audit_admin(
        db,
        admin_id=admin_id,
        action_type="contest_publish_schedule_canceled",
        target_type="contest",
        target_id=str(contest_id),
        contest_id=contest_id,
    )
    await db.commit()

    return {"success": True}


@router.post("/contests/bulk/publish-now")
async def bulk_publish_now(
    data: BulkContestActionRequest,
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(verify_admin)
):
    """
    Массовая немедленная публикация конкурсов (черновиков).
    """
    contest_ids = sorted({contest_id for contest_id in data.contest_ids if contest_id > 0})
    if not contest_ids:
        raise HTTPException(status_code=400, detail="Список конкурсов пуст")

    bot = Bot(token=config.bot_token)
    contest_service = ContestService(db)
    published_ids: list[int] = []
    skipped: list[dict] = []
    try:
        for contest_id in contest_ids:
            contest = await contest_service.get_contest_by_id(contest_id)
            if not contest:
                skipped.append({"contest_id": contest_id, "reason": "not_found"})
                continue
            if contest.status == ContestStatus.ACTIVE and contest.message_id:
                skipped.append({"contest_id": contest_id, "reason": "already_published"})
                continue
            if contest.status not in (ContestStatus.DRAFT, ContestStatus.ACTIVE):
                skipped.append({"contest_id": contest_id, "reason": f"invalid_status:{contest.status.value}"})
                continue
            if contest.status == ContestStatus.ACTIVE and not contest.message_id:
                logger.warning(
                    "bulk_publish_now: конкурс %s имеет статус active без message_id, выполняем восстановительную публикацию",
                    contest_id,
                )

            success = await publish_contest_to_channel(contest_id, bot, config.webapp_url)
            if success:
                published_ids.append(contest_id)
                await cancel_contest_publish(contest_id)
                await audit_admin(
                    db,
                    admin_id=admin_id,
                    action_type="contest_published",
                    target_type="contest",
                    target_id=str(contest_id),
                    contest_id=contest_id,
                    payload={"source": "bulk_publish_now"}
                )
            else:
                skipped.append({"contest_id": contest_id, "reason": "publish_failed"})
        await db.commit()
    finally:
        await bot.session.close()

    return {
        "success": True,
        "published_count": len(published_ids),
        "published_ids": published_ids,
        "skipped": skipped,
    }


@router.post("/contests/bulk/cancel-schedule")
async def bulk_cancel_schedule(
    data: BulkContestActionRequest,
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(verify_admin)
):
    """
    Массовая отмена отложенной публикации для черновиков.
    """
    contest_ids = sorted({contest_id for contest_id in data.contest_ids if contest_id > 0})
    if not contest_ids:
        raise HTTPException(status_code=400, detail="Список конкурсов пуст")

    updated_ids: list[int] = []
    skipped: list[dict] = []
    contest_service = ContestService(db)

    for contest_id in contest_ids:
        contest = await contest_service.get_contest_by_id(contest_id)
        if not contest:
            skipped.append({"contest_id": contest_id, "reason": "not_found"})
            continue
        if contest.status != ContestStatus.DRAFT:
            skipped.append({"contest_id": contest_id, "reason": f"invalid_status:{contest.status.value}"})
            continue
        if not contest.publish_at:
            skipped.append({"contest_id": contest_id, "reason": "schedule_not_set"})
            continue

        contest.publish_at = None
        updated_ids.append(contest_id)
        await cancel_contest_publish(contest_id)
        await audit_admin(
            db,
            admin_id=admin_id,
            action_type="contest_publish_schedule_canceled",
            target_type="contest",
            target_id=str(contest_id),
            contest_id=contest_id,
            payload={"source": "bulk_cancel_schedule"}
        )

    await db.commit()

    return {
        "success": True,
        "updated_count": len(updated_ids),
        "updated_ids": updated_ids,
        "skipped": skipped,
    }


@router.post("/contests/{contest_id}/republish")
async def republish_contest(
    contest_id: int,
    data: RepublishContestRequest,
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(verify_admin)
):
    """
    Перепубликовать конкурс или обновить существующий пост
    """
    contest_service = ContestService(db)
    contest = await contest_service.get_contest_by_id(contest_id)
    if not contest:
        raise HTTPException(status_code=404, detail="Конкурс не найден")
    if contest.status != ContestStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Перепубликация доступна только для активных конкурсов")

    from aiogram import Bot
    bot = Bot(token=config.bot_token)
    rendered_text = None
    rendered_button_url = None
    try:
        bot_info = await bot.get_me()
        rendered_text, preview_keyboard = await format_contest_message(contest, bot, bot_info.username, resolve_private_links=False)
        if preview_keyboard.inline_keyboard and preview_keyboard.inline_keyboard[0]:
            rendered_button_url = preview_keyboard.inline_keyboard[0][0].url

        if data.mode == "edit":
            success = await edit_contest_post(contest_id, bot)
        else:
            success = await publish_contest_to_channel(contest_id, bot, config.webapp_url, force_republish=True)
    finally:
        await bot.session.close()

    if not success:
        raise HTTPException(status_code=400, detail="Не удалось выполнить операцию перепубликации")

    await audit_admin(
        db,
        admin_id=admin_id,
        action_type="contest_republished" if data.mode != "edit" else "contest_post_edited",
        target_type="contest",
        target_id=str(contest_id),
        contest_id=contest_id,
        payload={
            "mode": data.mode,
            "rendered_text": rendered_text,
            "button_url": rendered_button_url,
        }
    )
    await db.commit()
    return {"success": True}


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
    await audit_admin(
        db,
        admin_id=admin_id,
        action_type="youtube_channel_created",
        target_type="youtube_channel",
        target_id=channel.channel_id,
        payload={"title": channel.title}
    )
    await db.commit()
    
    return {
        "channel_id": channel.channel_id,
        "title": channel.title,
        "description": channel.description
    }


@router.delete("/youtube-channels/{channel_id}")
async def delete_youtube_channel(
    channel_id: str,
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(verify_admin)
):
    """
    Удалить YouTube канал
    """
    result = await db.execute(
        select(YoutubeChannel).where(YoutubeChannel.channel_id == channel_id)
    )
    channel = result.scalar_one_or_none()
    
    if not channel:
        raise HTTPException(status_code=404, detail="Канал не найден")
    
    await db.delete(channel)
    await db.commit()
    await audit_admin(
        db,
        admin_id=admin_id,
        action_type="youtube_channel_deleted",
        target_type="youtube_channel",
        target_id=channel.channel_id,
        payload={"title": channel.title}
    )
    await db.commit()
    
    return {"success": True}


@router.get("/tiktok-channels")
async def get_tiktok_channels(
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(verify_admin)
):
    """
    Получить список TikTok аккаунтов
    """
    result = await db.execute(select(TikTokChannel))
    channels = result.scalars().all()

    return [
        {
            "channel_id": c.channel_id,
            "title": c.title,
            "description": c.description
        }
        for c in channels
    ]


@router.post("/tiktok-channels")
async def add_tiktok_channel(
    data: TikTokChannelCreate,
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(verify_admin)
):
    """
    Добавить TikTok аккаунт
    """
    channel_id = data.channel_id.strip()
    if not channel_id:
        raise HTTPException(status_code=400, detail="TikTok аккаунт не может быть пустым")

    channel_id = (
        channel_id
        .replace("https://www.tiktok.com/@", "")
        .replace("https://tiktok.com/@", "")
        .replace("https://www.tiktok.com/", "")
        .replace("https://tiktok.com/", "")
        .replace("www.tiktok.com/@", "")
        .replace("tiktok.com/@", "")
        .replace("www.tiktok.com/", "")
        .replace("tiktok.com/", "")
        .replace("@", "")
        .strip("/")
        .strip()
    )

    result = await db.execute(
        select(TikTokChannel).where(TikTokChannel.channel_id == channel_id)
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Такой TikTok аккаунт уже добавлен")

    title = (data.title or f"@{channel_id}").strip()
    if not title:
        raise HTTPException(status_code=400, detail="Название TikTok аккаунта не может быть пустым")

    channel = TikTokChannel(
        channel_id=channel_id,
        title=title,
        description=data.description
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)
    await audit_admin(
        db,
        admin_id=admin_id,
        action_type="tiktok_channel_created",
        target_type="tiktok_channel",
        target_id=channel.channel_id,
        payload={"title": channel.title}
    )
    await db.commit()

    return {
        "channel_id": channel.channel_id,
        "title": channel.title,
        "description": channel.description
    }


@router.delete("/tiktok-channels/{channel_id}")
async def delete_tiktok_channel(
    channel_id: str,
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(verify_admin)
):
    """
    Удалить TikTok аккаунт
    """
    result = await db.execute(
        select(TikTokChannel).where(TikTokChannel.channel_id == channel_id)
    )
    channel = result.scalar_one_or_none()

    if not channel:
        raise HTTPException(status_code=404, detail="TikTok аккаунт не найден")

    await db.delete(channel)
    await db.commit()
    await audit_admin(
        db,
        admin_id=admin_id,
        action_type="tiktok_channel_deleted",
        target_type="tiktok_channel",
        target_id=channel.channel_id,
        payload={"title": channel.title}
    )
    await db.commit()

    return {"success": True}


@router.get("/instagram-channels")
async def get_instagram_channels(
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(verify_admin)
):
    """
    Получить список Instagram каналов
    """
    result = await db.execute(select(InstagramChannel))
    channels = result.scalars().all()

    return [
        {
            "channel_id": c.channel_id,
            "title": c.title,
            "description": c.description
        }
        for c in channels
    ]


@router.post("/instagram-channels")
async def add_instagram_channel(
    data: InstagramChannelCreate,
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(verify_admin)
):
    """
    Добавить Instagram канал
    """
    channel_id = data.channel_id.strip()
    if not channel_id:
        raise HTTPException(status_code=400, detail="ID Instagram канала не может быть пустым")

    channel_id = channel_id.replace("https://instagram.com/", "").replace("http://instagram.com/", "").strip("/")

    result = await db.execute(
        select(InstagramChannel).where(InstagramChannel.channel_id == channel_id)
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Такой Instagram канал уже добавлен")

    title = (data.title or channel_id).strip()
    if not title:
        raise HTTPException(status_code=400, detail="Название Instagram канала не может быть пустым")

    channel = InstagramChannel(
        channel_id=channel_id,
        title=title,
        description=data.description
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)
    await audit_admin(
        db,
        admin_id=admin_id,
        action_type="instagram_channel_created",
        target_type="instagram_channel",
        target_id=channel.channel_id,
        payload={"title": channel.title}
    )
    await db.commit()

    return {
        "channel_id": channel.channel_id,
        "title": channel.title,
        "description": channel.description
    }


@router.delete("/instagram-channels/{channel_id}")
async def delete_instagram_channel(
    channel_id: str,
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(verify_admin)
):
    """
    Удалить Instagram канал
    """
    result = await db.execute(
        select(InstagramChannel).where(InstagramChannel.channel_id == channel_id)
    )
    channel = result.scalar_one_or_none()

    if not channel:
        raise HTTPException(status_code=404, detail="Instagram канал не найден")

    await db.delete(channel)
    await db.commit()
    await audit_admin(
        db,
        admin_id=admin_id,
        action_type="instagram_channel_deleted",
        target_type="instagram_channel",
        target_id=channel.channel_id,
        payload={"title": channel.title}
    )
    await db.commit()

    return {"success": True}
