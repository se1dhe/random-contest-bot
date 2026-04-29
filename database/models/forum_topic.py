"""
Модель Telegram forum topic.
"""
from sqlalchemy import Column, String, BigInteger, Integer, Boolean, UniqueConstraint
from .base import BaseModel


class ForumTopic(BaseModel):
    """Известный топик Telegram-группы."""

    __tablename__ = "forum_topics"
    __table_args__ = (
        UniqueConstraint("chat_id", "message_thread_id", name="uq_forum_topics_chat_thread"),
    )

    chat_id = Column(BigInteger, nullable=False, index=True)
    message_thread_id = Column(Integer, nullable=False)
    name = Column(String(255), nullable=False)
    icon_color = Column(Integer, nullable=True)
    icon_custom_emoji_id = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<ForumTopic(chat_id={self.chat_id}, thread={self.message_thread_id}, name={self.name})>"
