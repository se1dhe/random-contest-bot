"""
Сервис аудита действий администратора
"""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from database.models import AdminAction


async def log_admin_action(
    db: AsyncSession,
    actor_user_id: int,
    action_type: str,
    target_type: str,
    target_id: Optional[str] = None,
    contest_id: Optional[int] = None,
    status: str = "success",
    message: Optional[str] = None,
    payload: Optional[dict[str, Any]] = None,
) -> AdminAction:
    """
    Сохранить запись в истории действий администратора
    """
    action = AdminAction(
        actor_user_id=actor_user_id,
        action_type=action_type,
        target_type=target_type,
        target_id=target_id,
        contest_id=contest_id,
        status=status,
        message=message,
        payload=payload,
    )
    db.add(action)
    await db.flush()
    return action
