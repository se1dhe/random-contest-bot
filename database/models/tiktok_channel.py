"""
Модель TikTok аккаунта.
"""
from sqlalchemy import BigInteger, Column, String, Text

from .base import BaseModel


class TikTokChannel(BaseModel):
    """Справочник TikTok аккаунтов для условий участия."""

    __tablename__ = "tiktok_channels"

    channel_id = Column(String(255), nullable=False, unique=True)
    owner_user_id = Column(BigInteger, nullable=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    def __repr__(self):
        return f"<TikTokChannel(id={self.channel_id}, title={self.title})>"
