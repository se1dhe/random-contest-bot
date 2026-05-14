"""
Модель YouTube канала
"""
from sqlalchemy import BigInteger, Column, String, Text
from .base import BaseModel


class YoutubeChannel(BaseModel):
    """Модель YouTube канала"""
    
    __tablename__ = 'youtube_channels'
    
    channel_id = Column(String(255), nullable=False, unique=True)
    owner_user_id = Column(BigInteger, nullable=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<YoutubeChannel(id={self.channel_id}, title={self.title})>"
