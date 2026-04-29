from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, literal_column, text
from sqlalchemy.orm import selectinload
from aiogram import Bot
import httpx
from database.db import get_db
from database.models import Contest, Participant, Prize, ContestStatus
from web.api.deps import verify_admin
from datetime import date, datetime, time, timedelta
from shared.config import config
from shared.services.redis_service import get_redis

router = APIRouter(prefix="/api/admin/analytics", tags=["admin-analytics"])


def _serialize_issue_contest(contest: Contest, issue_type: str, detail: str, actionability: str) -> dict:
    return {
        "contest_id": contest.id,
        "title": contest.title,
        "status": contest.status.value,
        "channel_title": contest.channel.channel_title if getattr(contest, "channel", None) else None,
        "issue_type": issue_type,
        "detail": detail,
        "actionability": actionability,
    }

@router.get("/overview")
async def get_analytics_overview(
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(verify_admin)
):
    """Get aggregated analytics"""
    # Total contests
    res_contests = await db.execute(select(func.count(Contest.id)))
    total_contests = res_contests.scalar() or 0

    # Active contests
    res_active = await db.execute(select(func.count(Contest.id)).where(Contest.status == ContestStatus.ACTIVE))
    active_contests = res_active.scalar() or 0
    
    # Total participants
    res_parts = await db.execute(select(func.count(Participant.id)))
    total_participants = res_parts.scalar() or 0
    
    # Completed contests
    res_completed = await db.execute(select(func.count(Contest.id)).where(Contest.status == ContestStatus.FINISHED))
    completed_contests = res_completed.scalar() or 0
    
    return {
        "total_contests": total_contests,
        "active_contests": active_contests,
        "completed_contests": completed_contests,
        "total_participants": total_participants
    }

@router.get("/growth")
async def get_growth_data(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(verify_admin)
):
    """Get cumulative participants growth for the selected period."""
    today = datetime.utcnow().date()
    start_day = today - timedelta(days=days - 1)

    period_start = datetime.combine(start_day, time.min)
    period_end = datetime.combine(today + timedelta(days=1), time.min)
    day_bucket = func.date_trunc(literal_column("'day'"), Participant.registered_at)

    query = (
        select(
            day_bucket.label('day'),
            func.count(Participant.id).label('count')
        )
        .where(Participant.registered_at >= period_start)
        .where(Participant.registered_at < period_end)
        .group_by(day_bucket)
        .order_by(day_bucket)
    )

    result = await db.execute(query)
    rows = result.all()

    counts_by_day: dict[date, int] = {}
    for row in rows:
        day_value = row.day.date() if isinstance(row.day, datetime) else row.day
        counts_by_day[day_value] = int(row.count or 0)

    data = []
    running_total = 0
    for offset in range(days):
        current_day = start_day + timedelta(days=offset)
        running_total += counts_by_day.get(current_day, 0)
        data.append({
            "date": current_day.strftime("%d.%m"),
            "participants": running_total
        })

    return data


@router.get("/health")
async def get_health_data(
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(verify_admin)
):
    """Get operational health snapshot for admin dashboard."""
    now_result = await db.execute(text("SELECT NOW()::timestamp"))
    now_db = now_result.scalar()

    active_without_message_id_result = await db.execute(
        select(func.count(Contest.id)).where(
            Contest.status == ContestStatus.ACTIVE,
            Contest.message_id.is_(None),
        )
    )
    results_without_message_id_result = await db.execute(
        select(func.count(Contest.id)).where(
            Contest.status == ContestStatus.RESULTS_PUBLISHED,
            Contest.results_message_id.is_(None),
        )
    )
    overdue_scheduled_result = await db.execute(
        select(func.count(Contest.id)).where(
            Contest.status == ContestStatus.DRAFT,
            Contest.publish_at.is_not(None),
            Contest.publish_at <= now_db,
        )
    )
    finished_without_winners_result = await db.execute(
        select(func.count(func.distinct(Contest.id)))
        .select_from(Contest)
        .join(Prize, Prize.contest_id == Contest.id)
        .where(
            Contest.status.in_([ContestStatus.FINISHED, ContestStatus.RESULTS_PUBLISHED]),
            Prize.winner_user_id.is_(None),
        )
    )

    database_status = {
        "status": "ok",
        "detail": "PostgreSQL отвечает",
    }

    redis_status = {
        "status": "error",
        "detail": "Redis не проверен",
    }
    try:
        redis = await get_redis()
        pong = await redis.ping()
        redis_status = {
            "status": "ok" if pong else "error",
            "detail": "Redis отвечает" if pong else "Redis не ответил на ping",
        }
    except Exception as exc:
        redis_status = {
            "status": "error",
            "detail": f"Redis error: {exc}",
        }

    bot_status = {
        "status": "error",
        "detail": "Telegram Bot API не проверен",
    }
    bot = Bot(token=config.bot_token)
    try:
        bot_info = await bot.get_me()
        bot_status = {
            "status": "ok",
            "detail": f"Бот @{bot_info.username or bot_info.id} отвечает",
        }
    except Exception as exc:
        bot_status = {
            "status": "error",
            "detail": f"Bot API error: {exc}",
        }
    finally:
        await bot.session.close()

    ngrok_status = {
        "status": "warning" if config.ngrok_enabled else "disabled",
        "detail": "Ngrok отключен в конфиге" if not config.ngrok_enabled else "Ngrok включен, статус уточняется",
        "public_url": None,
        "configured_domain": config.ngrok_domain,
    }
    if config.ngrok_enabled:
        try:
            async with httpx.AsyncClient(timeout=2.5) as client:
                response = await client.get("http://ngrok:4040/api/tunnels")
                response.raise_for_status()
                tunnels = response.json().get("tunnels", [])
                https_tunnel = next((t for t in tunnels if t.get("public_url", "").startswith("https://")), None)
                public_url = https_tunnel.get("public_url") if https_tunnel else None
                matches_config = bool(public_url and config.ngrok_domain and config.ngrok_domain in public_url)
                ngrok_status = {
                    "status": "ok" if public_url else "warning",
                    "detail": (
                        "Ngrok туннель активен"
                        if public_url and (matches_config or not config.ngrok_domain)
                        else "Ngrok активен, но домен не совпадает с конфигом"
                        if public_url
                        else "Ngrok не вернул HTTPS туннель"
                    ),
                    "public_url": public_url,
                    "configured_domain": config.ngrok_domain,
                }
        except Exception as exc:
            ngrok_status = {
                "status": "error",
                "detail": f"Ngrok API error: {exc}",
                "public_url": None,
                "configured_domain": config.ngrok_domain,
            }

    problematic_contests: list[dict] = []

    active_without_message_rows = await db.execute(
        select(Contest)
        .options(selectinload(Contest.channel))
        .where(
            Contest.status == ContestStatus.ACTIVE,
            Contest.message_id.is_(None),
        )
        .limit(5)
    )
    for contest in active_without_message_rows.scalars().all():
        problematic_contests.append(
            _serialize_issue_contest(
                contest,
                issue_type="active_without_message_id",
                detail="Конкурс активен, но пост в канале не зафиксирован.",
                actionability="auto_repairable",
            )
        )

    results_without_message_rows = await db.execute(
        select(Contest)
        .options(selectinload(Contest.channel))
        .where(
            Contest.status == ContestStatus.RESULTS_PUBLISHED,
            Contest.results_message_id.is_(None),
        )
        .limit(5)
    )
    for contest in results_without_message_rows.scalars().all():
        problematic_contests.append(
            _serialize_issue_contest(
                contest,
                issue_type="results_without_message_id",
                detail="Статус результатов выставлен, но сообщение с результатами не найдено.",
                actionability="auto_repairable",
            )
        )

    overdue_scheduled_rows = await db.execute(
        select(Contest)
        .options(selectinload(Contest.channel))
        .where(
            Contest.status == ContestStatus.DRAFT,
            Contest.publish_at.is_not(None),
            Contest.publish_at <= now_db,
        )
        .limit(5)
    )
    for contest in overdue_scheduled_rows.scalars().all():
        problematic_contests.append(
            _serialize_issue_contest(
                contest,
                issue_type="overdue_scheduled",
                detail="Отложенная публикация уже просрочена, но конкурс всё ещё в черновике.",
                actionability="auto_repairable",
            )
        )

    finished_without_winners_rows = await db.execute(
        select(Contest)
        .options(selectinload(Contest.channel))
        .join(Prize, Prize.contest_id == Contest.id)
        .where(
            Contest.status.in_([ContestStatus.FINISHED, ContestStatus.RESULTS_PUBLISHED]),
            Prize.winner_user_id.is_(None),
        )
        .distinct()
        .limit(5)
    )
    for contest in finished_without_winners_rows.scalars().all():
        participants_result = await db.execute(
            select(func.count(Participant.id)).where(Participant.contest_id == contest.id)
        )
        participants_count = int(participants_result.scalar() or 0)
        prizes_result = await db.execute(
            select(func.count(Prize.id)).where(Prize.contest_id == contest.id)
        )
        prizes_count = int(prizes_result.scalar() or 0)
        actionability = "auto_repairable" if participants_count >= prizes_count and prizes_count > 0 else "manual_attention"
        detail = (
            f"Не назначены победители: участников {participants_count}, призов {prizes_count}."
            if actionability == "manual_attention"
            else "Победители не назначены, но система может повторно выполнить розыгрыш."
        )
        problematic_contests.append(
            _serialize_issue_contest(
                contest,
                issue_type="finished_without_winners",
                detail=detail,
                actionability=actionability,
            )
        )

    issue_counts = {
        "active_without_message_id": int(active_without_message_id_result.scalar() or 0),
        "results_without_message_id": int(results_without_message_id_result.scalar() or 0),
        "overdue_scheduled": int(overdue_scheduled_result.scalar() or 0),
        "finished_without_winners": int(finished_without_winners_result.scalar() or 0),
    }

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "services": {
            "database": database_status,
            "redis": redis_status,
            "bot_api": bot_status,
            "ngrok": ngrok_status,
        },
        "issues": {
            **issue_counts,
            "total": sum(issue_counts.values()),
        },
        "problematic_contests": problematic_contests,
    }
