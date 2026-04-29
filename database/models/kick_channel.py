"""
Модель Kick канала.
"""
from sqlalchemy import Column, String, Text

from .base import BaseModel


class KickChannel(BaseModel):
    """Справочник Kick каналов для условий участия."""

    __tablename__ = "kick_channels"

    channel_id = Column(String(255), nullable=False, unique=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    def __repr__(self):
        return f"<KickChannel(id={self.channel_id}, title={self.title})>"
