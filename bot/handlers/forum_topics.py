"""
Сбор известных Telegram forum topics.
"""
import logging

from aiogram import Router
from aiogram.types import Message
from sqlalchemy import select

from database.db import AsyncSessionLocal
from database.models import Channel, ForumTopic

router = Router()
logger = logging.getLogger(__name__)


def _topic_name_from_message(message: Message) -> str | None:
    created = getattr(message, "forum_topic_created", None)
    if created and getattr(created, "name", None):
        return created.name

    edited = getattr(message, "forum_topic_edited", None)
    if edited and getattr(edited, "name", None):
        return edited.name

    return None


@router.message()
async def remember_forum_topic(message: Message) -> None:
    """
    Telegram Bot API не дает получить полный список топиков по запросу.
    Запоминаем топики, которые бот видит через сервисные события или сообщения.
    """
    chat = message.chat
    thread_id = getattr(message, "message_thread_id", None)
    if not chat or not thread_id:
        return

    is_topic_message = bool(getattr(message, "is_topic_message", False))
    has_topic_event = any(
        getattr(message, field, None)
        for field in (
            "forum_topic_created",
            "forum_topic_edited",
            "forum_topic_closed",
            "forum_topic_reopened",
        )
    )
    if not is_topic_message and not has_topic_event:
        return

    name = _topic_name_from_message(message) or f"Топик #{thread_id}"
    icon_color = getattr(getattr(message, "forum_topic_created", None), "icon_color", None)
    icon_custom_emoji_id = getattr(getattr(message, "forum_topic_created", None), "icon_custom_emoji_id", None)

    async with AsyncSessionLocal() as db:
        channel_result = await db.execute(
            select(Channel).where(Channel.channel_id == chat.id, Channel.is_active == True)
        )
        if not channel_result.scalar_one_or_none():
            return

        topic_result = await db.execute(
            select(ForumTopic).where(
                ForumTopic.chat_id == chat.id,
                ForumTopic.message_thread_id == thread_id,
            )
        )
        topic = topic_result.scalar_one_or_none()

        if topic:
            topic.name = name if name != f"Топик #{thread_id}" or topic.name.startswith("Топик #") else topic.name
            topic.icon_color = icon_color if icon_color is not None else topic.icon_color
            topic.icon_custom_emoji_id = icon_custom_emoji_id or topic.icon_custom_emoji_id
            topic.is_active = True
        else:
            db.add(
                ForumTopic(
                    chat_id=chat.id,
                    message_thread_id=thread_id,
                    name=name,
                    icon_color=icon_color,
                    icon_custom_emoji_id=icon_custom_emoji_id,
                    is_active=True,
                )
            )

        await db.commit()
        logger.info("Запомнен топик Telegram: chat_id=%s thread_id=%s name=%s", chat.id, thread_id, name)
