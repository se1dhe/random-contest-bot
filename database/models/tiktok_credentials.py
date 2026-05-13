"""
Модель для хранения TikTok OAuth credentials пользователей.
"""
import json

from sqlalchemy import BigInteger, Column, DateTime, String, Text

from database.models.base import BaseModel


class TikTokCredentials(BaseModel):
    """Сохраненные TikTok credentials для повторной проверки условий конкурса."""

    __tablename__ = "tiktok_credentials"

    user_id = Column(BigInteger, nullable=False, unique=True, index=True, comment="ID пользователя Telegram")
    tiktok_user_id = Column(String(255), nullable=False, index=True, comment="ID пользователя TikTok")
    tiktok_login = Column(String(255), nullable=True, comment="Логин пользователя TikTok")
    tiktok_display_name = Column(String(255), nullable=True, comment="Display name пользователя TikTok")
    token = Column(Text, nullable=False, comment="OAuth access token")
    refresh_token = Column(Text, nullable=True, comment="OAuth refresh token")
    token_uri = Column(String(255), nullable=False, server_default="https://open.tiktokapis.com/v2/oauth/token/", comment="Token URI")
    client_id = Column(String(255), nullable=False, comment="OAuth client ID")
    client_secret = Column(String(255), nullable=False, comment="OAuth client secret")
    scopes = Column(Text, nullable=False, comment="OAuth scopes (JSON array)")
    expires_at = Column(DateTime, nullable=True, comment="Время истечения токена")

    def to_dict(self) -> dict:
        """Преобразовать credentials в словарь."""
        return {
            "token": self.token,
            "refresh_token": self.refresh_token,
            "token_uri": self.token_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scopes": json.loads(self.scopes) if isinstance(self.scopes, str) else self.scopes,
        }
