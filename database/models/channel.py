"""
Модель канала
"""
from sqlalchemy import Column, String, BigInteger, Boolean
from .base import BaseModel


class Channel(BaseModel):
    """Модель канала Telegram"""
    
    __tablename__ = 'channels'
    
    channel_id = Column(BigInteger, unique=True, nullable=False, index=True)
    channel_username = Column(String(255), nullable=True)
    channel_title = Column(String(255), nullable=False)
    owner_user_id = Column(BigInteger, nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    youtube_channel_id = Column(String(255), nullable=True)  # ID YouTube канала для проверки подписки
    
    def __repr__(self):
        return f"<Channel(id={self.id}, username={self.channel_username}, title={self.channel_title})>"
