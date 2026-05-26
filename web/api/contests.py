"""
API роуты для конкурсов
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime
import base64
import hashlib
import hmac
import json
import logging
import secrets
import time
from database.db import get_db
from database.models.contest import ContestStatus
from bot.services.contest_service import ContestService
from bot.services.participant_service import ParticipantService
from bot.services.draw_service import DrawService
from shared.services.telegram_service import TelegramService
from shared.services.redis_service import get_cached_channel_invite_link, cache_channel_invite_link
from aiogram import Bot
from shared.config import config
from shared.i18n import day_unit, normalize_language, translate
from web.api.deps import verify_telegram_user

router = APIRouter(prefix="/api/contests", tags=["contests"])
logger = logging.getLogger(__name__)
CAPTCHA_TTL_SECONDS = 10 * 60


def _captcha_secret() -> bytes:
    return (config.secret_key or config.bot_token or "contest-captcha").encode("utf-8")


def _sign_captcha_payload(payload: dict) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hmac.new(_captcha_secret(), raw, hashlib.sha256).hexdigest()


def _encode_captcha_token(payload: dict) -> str:
    body = {
        "payload": payload,
        "sig": _sign_captcha_payload(payload),
    }
    raw = json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _captcha_answer_hash(answer: int, nonce: str) -> str:
    raw = f"{answer}:{nonce}".encode("utf-8")
    return hmac.new(_captcha_secret(), raw, hashlib.sha256).hexdigest()


def _decode_captcha_token(token: str) -> dict:
    padding = "=" * (-len(token) % 4)
    raw = base64.urlsafe_b64decode((token + padding).encode("ascii"))
    body = json.loads(raw.decode("utf-8"))
    payload = body.get("payload")
    signature = body.get("sig")
    if not isinstance(payload, dict) or not signature:
        raise ValueError("Invalid captcha token")
    expected = _sign_captcha_payload(payload)
    if not hmac.compare_digest(str(signature), expected):
        raise ValueError("Invalid captcha signature")
    return payload


def verify_captcha_token(token: str, answer: str, contest_id: int, user_id: int) -> bool:
    try:
        payload = _decode_captcha_token(token)
        if int(payload.get("contest_id")) != int(contest_id):
            return False
        if int(payload.get("user_id")) != int(user_id):
            return False
        if int(payload.get("exp")) < int(time.time()):
            return False
        submitted_answer = int(str(answer).strip())
        answer_hash = str(payload.get("answer_hash") or "")
        nonce = str(payload.get("nonce") or "")
        return hmac.compare_digest(answer_hash, _captcha_answer_hash(submitted_answer, nonce))
    except Exception:
        return False


async def get_telegram_service():
    """Получить сервис Telegram"""
    bot = Bot(token=config.bot_token)
    try:
        yield TelegramService(bot)
    finally:
        await bot.session.close()


async def _resolve_invite_link_cached(
    telegram_service: TelegramService,
    channel_id: int,
    invite_name: str,
) -> Optional[str]:
    """
    Получить invite-ссылку канала с кэшированием в Redis.
    """
    cached = await get_cached_channel_invite_link(channel_id)
    if cached:
        return cached

    try:
        invite = await telegram_service.bot.create_chat_invite_link(
            chat_id=channel_id,
            name=invite_name,
            creates_join_request=False,
        )
        invite_link = getattr(invite, "invite_link", None)
        if invite_link:
            await cache_channel_invite_link(channel_id, invite_link)
        return invite_link
    except Exception:
        return None


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
    import logging
    logger = logging.getLogger(__name__)
    
    service = ContestService(db)
    contest = await service.get_contest_by_id(contest_id)
    
    if not contest:
        logger.warning(f"Contest {contest_id} not found")
        raise HTTPException(status_code=404, detail="Конкурс не найден")
    
    # Проверяем статус конкурса
    if contest.status != ContestStatus.ACTIVE:
        logger.warning(f"Contest {contest_id} has invalid status: {contest.status}")
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
        from shared.services.redis_service import get_database_now_kyiv

        now_db = await get_database_now_kyiv()
        
        logger.info(f"Contest {contest_id} end_date: {contest.end_date}, now_db: {now_db}")
        
        # Сравниваем даты (обе должны быть naive)
        if contest.end_date < now_db:
            logger.warning(f"Contest {contest_id} expired: {contest.end_date} < {now_db}")
            raise HTTPException(
                status_code=400, 
                detail="Конкурс уже завершен"
            )
    
    # Get participant count
    participants_count = await service.get_participants_count(contest_id)
    
    # Преобразуем в словарь
    return {
        "id": contest.id,
        "title": contest.title,
        "description": contest.description,
        "language": normalize_language(contest.language),
        "channel_id": contest.channel_id,
        "channel_title": contest.channel.channel_title if contest.channel else None,
        "end_date": contest.end_date.isoformat(),
        "status": contest.status.value,
        "prize_count": contest.prize_count,
        "participants_count": participants_count,
        "image_url": f"/{contest.image_path}" if contest.image_path else None,
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
        "tiktok_channel_id": contest.tiktok_channel_id,
        "require_captcha": bool(getattr(contest, "require_captcha", False)),
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
        "language": normalize_language(contest.language),
        "prize_count": contest.prize_count,
        "participants_count": participants_count,
        "image_url": contest.image_path,  # Фронтенд ожидает image_url
        "end_date": contest.end_date.isoformat() if contest.end_date else None,
        "status": contest.status.value,
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
        "tiktok_channel_id": contest.tiktok_channel_id,
        "require_captcha": bool(getattr(contest, "require_captcha", False)),
        "image_path": contest.image_path
    }


@router.get("/{contest_id}/captcha")
async def get_captcha_challenge(
    contest_id: int,
    auth_user_id: int = Depends(verify_telegram_user),
    db: AsyncSession = Depends(get_db),
):
    service = ContestService(db)
    contest = await service.get_contest_by_id(contest_id)
    if not contest:
        raise HTTPException(status_code=404, detail="Конкурс не найден")
    if not getattr(contest, "require_captcha", False):
        raise HTTPException(status_code=400, detail="Капча для конкурса не включена")

    a = secrets.randbelow(8) + 2
    b = secrets.randbelow(8) + 2
    nonce = secrets.token_urlsafe(8)
    payload = {
        "contest_id": int(contest_id),
        "user_id": int(auth_user_id),
        "answer_hash": _captcha_answer_hash(a + b, nonce),
        "exp": int(time.time()) + CAPTCHA_TTL_SECONDS,
        "nonce": nonce,
    }
    return {
        "question": f"{a} + {b}",
        "token": _encode_captcha_token(payload),
        "expires_in": CAPTCHA_TTL_SECONDS,
    }


@router.get("/{contest_id}/check-subscription")
async def check_subscription(
    contest_id: int,
    user_id: int = Query(...),
    auth_user_id: int = Depends(verify_telegram_user),
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
    if int(user_id) != int(auth_user_id):
        raise HTTPException(status_code=403, detail="Нельзя проверять подписки другого пользователя")

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

    tiktok_subscribed = None
    if contest.tiktok_channel_id:
        from web.api.tiktok_auth import check_tiktok_subscription, get_user_credentials as get_tiktok_credentials
        tiktok_credentials = await get_tiktok_credentials(user_id, db)
        if tiktok_credentials:
            tiktok_subscribed = await check_tiktok_subscription(
                user_id=user_id,
                target_channel_id=contest.tiktok_channel_id,
                days_required=0,
                db=db,
            )
    
    return {
        "subscriptions": subscriptions,
        "youtube_subscribed": youtube_subscribed,
        "tiktok_subscribed": tiktok_subscribed,
    }


@router.get("/{contest_id}/auto-check")
async def auto_check(
    contest_id: int,
    user_id: int = Query(...),
    auth_user_id: int = Depends(verify_telegram_user),
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
    if int(user_id) != int(auth_user_id):
        raise HTTPException(status_code=403, detail="Нельзя проверять условия другого пользователя")

    service = ContestService(db)
    participant_service = ParticipantService(db)
    contest = await service.get_contest_by_id(contest_id)
    
    if not contest:
        raise HTTPException(status_code=404, detail="Конкурс не найден")
    
    # 1. Проверяем регистрацию
    participant = await participant_service.get_participant(contest_id, user_id)
    if participant:
        return {
            "is_registered": True,
            "can_register": False,
            "status": "already_registered",
            "participant": {
                "registration_number": participant.registration_number,
                "registered_at": participant.registered_at.isoformat()
            },
            "conditions": [],
            "participants_count": await service.get_participants_count(contest_id)
        }
    
    # 2. Собираем список условий
    conditions = []
    
    # Условие: Основной канал
    main_chat = await telegram_service.get_chat_info(contest.channel_id)
    main_invite = None
    if not (main_chat and main_chat.get('username')):
        main_invite = await _resolve_invite_link_cached(
            telegram_service=telegram_service,
            channel_id=contest.channel_id,
            invite_name=f"{contest.title} invite",
        )
    conditions.append({
        "type": "telegram",
        "id": contest.channel_id,
        "title": main_chat['title'] if main_chat else translate(contest.language, "main_channel"),
        "username": main_chat['username'] if main_chat else None,
        "invite_link": main_invite,
        "met": await telegram_service.check_subscription(user_id, contest.channel_id)
    })
    
    # Условие: Спонсоры
    if contest.sponsors:
        for sponsor in contest.sponsors:
            invite_link = None
            if not sponsor.channel_username:
                invite_link = await _resolve_invite_link_cached(
                    telegram_service=telegram_service,
                    channel_id=sponsor.channel_id,
                    invite_name=f"{contest.title} sponsor",
                )
            conditions.append({
                "type": "telegram",
                "id": sponsor.channel_id,
                "title": sponsor.channel_title or translate(contest.language, "sponsor_channel"),
                "username": sponsor.channel_username,
                "invite_link": invite_link,
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
            "title": translate(contest.language, "youtube_channel"),
            "met": youtube_met,
            "connected": credentials is not None
        }
        conditions.append(youtube_condition)

    tiktok_condition = None
    if contest.tiktok_channel_id:
        from web.api.tiktok_auth import get_tiktok_subscription_status
        tiktok_status = await get_tiktok_subscription_status(
            user_id=user_id,
            target_channel_id=contest.tiktok_channel_id,
            days_required=0,
            db=db,
        )
        tiktok_condition = {
            "type": "tiktok",
            "id": contest.tiktok_channel_id,
            "title": translate(contest.language, "tiktok_channel"),
            "met": tiktok_status["met"],
            "connected": tiktok_status["connected"],
            "verification_status": tiktok_status["status"],
        }
        conditions.append(tiktok_condition)

    all_met = all(c['met'] for c in conditions)
    captcha_required = bool(getattr(contest, "require_captcha", False))
    
    return {
        "status": "active",
        "is_registered": False,
        "can_register": all_met and not captcha_required,
        "external_conditions_met": all_met,
        "captcha_required": captcha_required,
        "conditions": conditions,
        "participants_count": await service.get_participants_count(contest_id)
    }


@router.post("/{contest_id}/register")
async def register_participant(
    contest_id: int,
    request: Request,
    data: Optional[dict] = None,
    user_id: Optional[int] = Query(None),
    username: Optional[str] = Query(None),
    auth_user_id: int = Depends(verify_telegram_user),
    db: AsyncSession = Depends(get_db),
    telegram_service: TelegramService = Depends(get_telegram_service)
):
    """
    Зарегистрировать участника в конкурсе
    
    @param contest_id ID конкурса
    @param data данные регистрации (body)
    @param user_id ID пользователя (query)
    @param username username (query)
    @param db сессия БД
    @param telegram_service сервис Telegram
    @return информация о регистрации
    """
    # Извлекаем user_id из разных источников (фронтенд шлет в query params)
    body_user_id = data.get("user_id") if data else None
    user_id = auth_user_id
    
    body_username = data.get("username") if data else None
    username = username or body_username
    
    if not user_id:
        raise HTTPException(status_code=400, detail="Не указан user_id")
    
    # Проверяем конкурс
    contest_service = ContestService(db)
    contest = await contest_service.get_contest_by_id(contest_id)
    
    if not contest:
        raise HTTPException(status_code=404, detail="Конкурс не найден")
    language = normalize_language(contest.language)
    
    if contest.status.value != "active":
        raise HTTPException(status_code=400, detail=translate(language, "contest_not_active"))

    if getattr(contest, "require_captcha", False):
        captcha_token = (data or {}).get("captcha_token")
        captcha_answer = (data or {}).get("captcha_answer")
        if not captcha_token or captcha_answer is None:
            raise HTTPException(status_code=400, detail=translate(language, "captcha_required"))
        if not verify_captcha_token(str(captcha_token), str(captcha_answer), contest_id, user_id):
            raise HTTPException(status_code=400, detail=translate(language, "captcha_invalid"))
    
    # Проверяем подписки на Telegram каналы
    channel_ids = [contest.channel_id]
    if contest.sponsors:
        channel_ids.extend([sponsor.channel_id for sponsor in contest.sponsors])
    
    subscriptions = await telegram_service.check_subscriptions(user_id, channel_ids)
    all_subscribed = all(subscriptions.values())
    
    if not all_subscribed:
        raise HTTPException(status_code=400, detail=translate(language, "telegram_required"))
    
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
                detail=translate(language, "youtube_auth_required")
            )
        
        # Получаем YouTube channel_id пользователя
        result = await db.execute(
            select(YouTubeCredentials).where(YouTubeCredentials.user_id == user_id)
        )
        user_youtube_creds = result.scalar_one_or_none()
        
        if not user_youtube_creds or not user_youtube_creds.youtube_channel_id:
            raise HTTPException(
                status_code=400,
                detail=translate(language, "youtube_channel_unknown")
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
                    detail=translate(language, "youtube_channel_duplicate")
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
                    detail=translate(
                        language,
                        "youtube_subscribe_days_required",
                        days=days_required,
                        unit=day_unit(language, days_required),
                    )
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=translate(language, "youtube_subscribe_required")
                )
    
    # Проверяем фолловинг TikTok, если требуется
    if contest.tiktok_channel_id:
        from web.api.tiktok_auth import TIKTOK_STATUS_UNVERIFIED, get_tiktok_subscription_status

        tiktok_status = await get_tiktok_subscription_status(
            user_id=user_id,
            target_channel_id=contest.tiktok_channel_id,
            days_required=0,
            db=db,
        )
        if not tiktok_status["connected"]:
            raise HTTPException(
                status_code=400,
                detail=translate(language, "tiktok_auth_required")
            )

        is_following_tiktok = tiktok_status["met"]
        if not is_following_tiktok:
            if tiktok_status["status"] == TIKTOK_STATUS_UNVERIFIED:
                raise HTTPException(
                    status_code=400,
                    detail=translate(language, "tiktok_follow_unverified")
                )
            raise HTTPException(
                status_code=400,
                detail=translate(language, "tiktok_follow_required")
            )

    # Извлекаем данные из initData если есть
    first_name = None
    last_name = None
    
    auth_data = request.query_params.get("_auth") or request.headers.get("X-Telegram-Init-Data")
    if auth_data:
        try:
            from urllib.parse import parse_qs, unquote
            parsed_auth = parse_qs(auth_data)
            if 'user' in parsed_auth:
                import json
                user_data = json.loads(unquote(parsed_auth['user'][0]))
                first_name = user_data.get('first_name')
                last_name = user_data.get('last_name')
                # Если username не передан явно, берем из initData
                if not username:
                    username = user_data.get('username')
        except Exception as e:
            logger.warning("Ошибка парсинга initData при регистрации в contest_id=%s user_id=%s: %s", contest_id, user_id, e)

    # Регистрируем участника
    participant_service = ParticipantService(db)
    participant = await participant_service.register_participant(
        contest_id=contest_id,
        user_id=user_id,
        username=username,
        first_name=first_name,
        last_name=last_name
    )
    
    if not participant:
        logger.info("Повторная регистрация отклонена: contest_id=%s user_id=%s", contest_id, user_id)
        raise HTTPException(status_code=400, detail=translate(language, "already_registered"))
    
    # Публикуем обновление в Redis для WebSocket
    try:
        from shared.services.redis_service import get_redis
        import json
        redis = await get_redis()
        participants_count = await contest_service.get_participants_count(contest_id)
        logger.info(f"Publishing update for contest {contest_id}: count={participants_count}")
        await redis.publish("contest_updates", json.dumps({
            "type": "new_registration",
            "contest_id": contest_id,
            "participants_count": participants_count
        }))
    except Exception as e:
        logger.warning("Ошибка при публикации обновления конкурса в Redis contest_id=%s user_id=%s: %s", contest_id, user_id, e)

    logger.info(
        "Участник зарегистрирован: contest_id=%s user_id=%s registration_number=%s",
        contest_id,
        user_id,
        participant.registration_number,
    )
    
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
    auth_user_id: int = Depends(verify_telegram_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить расширенную информацию для страницы результатов
    
    @param contest_id ID конкурса
    @param user_id ID пользователя
    @param db сессия БД
    @return информация о результатах и статусе пользователя
    """
    if int(user_id) != int(auth_user_id):
        raise HTTPException(status_code=403, detail="Нельзя получать результаты другого пользователя")

    service = ContestService(db)
    participant_service = ParticipantService(db)
    draw_service = DrawService(db)
    
    contest = await service.get_contest_by_id(contest_id)
    if not contest:
        raise HTTPException(status_code=404, detail="Конкурс не найден")
    
    # Get participant count
    participants_count = await service.get_participants_count(contest_id)
        
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
        "contest_title": contest.title,
        "contest_description": contest.description,
        "language": normalize_language(contest.language),
        "image_url": f"/{contest.image_path}" if contest.image_path else None,
        "end_date": contest.end_date.isoformat(),
        "participants_count": participants_count,
        "status": contest.status.value,
        "is_participant": participant is not None,
        "user_prize": user_prize,
        "winners": [
            {
                "place": p.place,
                "title": p.title,
                "user_id": p.winner_user_id,
                "username": p.winner_username,
                "firstname": p.winner_firstname
            }
            for p in sorted(winners, key=lambda x: x.place)
        ] if winners else []
    }
