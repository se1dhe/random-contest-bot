"""
Модель для хранения YouTube OAuth credentials пользователей
"""
from sqlalchemy import Column, BigInteger, String, Text, DateTime
from database.models.base import BaseModel
import json


class YouTubeCredentials(BaseModel):
    """
    Модель для хранения YouTube OAuth credentials пользователей
    
    Сохраняет credentials для повторного использования без повторной авторизации
    """
    __tablename__ = 'youtube_credentials'
    
    user_id = Column(BigInteger, nullable=False, unique=True, index=True, comment='ID пользователя Telegram')
    youtube_channel_id = Column(String(255), nullable=True, comment='ID YouTube канала пользователя')
    token = Column(Text, nullable=False, comment='OAuth access token')
    refresh_token = Column(Text, nullable=True, comment='OAuth refresh token')
    token_uri = Column(String(255), nullable=False, server_default='https://oauth2.googleapis.com/token', comment='Token URI')
    client_id = Column(String(255), nullable=False, comment='OAuth client ID')
    client_secret = Column(String(255), nullable=False, comment='OAuth client secret')
    scopes = Column(Text, nullable=False, comment='OAuth scopes (JSON array)')
    expires_at = Column(DateTime, nullable=True, comment='Время истечения токена')
    
    def to_dict(self) -> dict:
        """
        Преобразовать в словарь для создания Credentials объекта
        
        @return словарь с данными credentials
        """
        return {
            'token': self.token,
            'refresh_token': self.refresh_token,
            'token_uri': self.token_uri,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scopes': json.loads(self.scopes) if isinstance(self.scopes, str) else self.scopes
        }
    
    @classmethod
    def from_credentials_dict(cls, user_id: int, youtube_channel_id: str, creds_dict: dict, expires_at=None):
        """
        Создать объект из словаря credentials
        
        @param user_id ID пользователя Telegram
        @param youtube_channel_id ID YouTube канала пользователя
        @param creds_dict словарь с credentials
        @param expires_at время истечения токена
        @return объект YouTubeCredentials
        """
        return cls(
            user_id=user_id,
            youtube_channel_id=youtube_channel_id,
            token=creds_dict.get('token'),
            refresh_token=creds_dict.get('refresh_token'),
            token_uri=creds_dict.get('token_uri', 'https://oauth2.googleapis.com/token'),
            client_id=creds_dict.get('client_id'),
            client_secret=creds_dict.get('client_secret'),
            scopes=json.dumps(creds_dict.get('scopes', [])) if isinstance(creds_dict.get('scopes'), list) else creds_dict.get('scopes', '[]'),
            expires_at=expires_at
        )

