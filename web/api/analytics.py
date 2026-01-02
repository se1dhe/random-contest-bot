from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from database.db import get_db
from database.models import Contest, Participant, ContestStatus
from web.api.admin import verify_admin
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/admin/analytics", tags=["admin-analytics"])

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
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(verify_admin)
):
    """Get daily participants growth"""
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)
    
    # Postgres specific date_trunc
    query = (
        select(
            func.date_trunc('day', Participant.registered_at).label('day'),
            func.count(Participant.id).label('count')
        )
        .where(Participant.registered_at >= start_date)
        .group_by(func.date_trunc('day', Participant.registered_at))
        .order_by('day')
    )
    
    result = await db.execute(query)
    rows = result.all()
    
    data = []
    # Fill missing dates if necessary, or just return actuals
    # Return actuals for simplicity
    for row in rows:
        d = row.day
        if isinstance(d, datetime):
            d_str = d.strftime("%d.%m")
        else:
            d_str = str(d)
        data.append({"date": d_str, "participants": row.count})
        
    return data
