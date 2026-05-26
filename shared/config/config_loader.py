"""
Модуль для загрузки конфигурации из config.ini и переменных окружения.
"""
import configparser
import os
from pathlib import Path
from typing import Optional
from urllib.parse import quote


class Config:
    """Класс для работы с конфигурацией"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Инициализация конфигурации
        
        @param config_path путь к файлу конфигурации
        """
        if config_path is None:
            # Ищем config.ini в корне проекта
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config.ini"
        
        self.config = configparser.ConfigParser()
        self.config.read(config_path, encoding='utf-8')
    
    def get(self, section: str, key: str, default: Optional[str] = None) -> str:
        """
        Получить значение из конфигурации
        
        @param section секция конфигурации
        @param key ключ
        @param default значение по умолчанию
        @return значение из конфигурации
        """
        env_value = os.getenv(key) or os.getenv(f"{section.upper()}_{key}")
        if env_value is not None:
            return env_value

        try:
            return self.config.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            if default is not None:
                return default
            raise
    
    def get_bool(self, section: str, key: str, default: bool = False) -> bool:
        """
        Получить булево значение из конфигурации
        
        @param section секция конфигурации
        @param key ключ
        @param default значение по умолчанию
        @return булево значение
        """
        value = self.get(section, key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on')
    
    def get_int(self, section: str, key: str, default: int = 0) -> int:
        """
        Получить целочисленное значение из конфигурации
        
        @param section секция конфигурации
        @param key ключ
        @param default значение по умолчанию
        @return целочисленное значение
        """
        return int(self.get(section, key, str(default)))
    
    @property
    def bot_token(self) -> str:
        """Токен Telegram бота"""
        return self.get('telegram', 'BOT_TOKEN')
    
    @property
    def admin_id(self) -> int:
        """ID администратора"""
        return self.get_int('telegram', 'ADMIN_ID')

    @property
    def admin_ids(self) -> set[int]:
        """ID администраторов."""
        raw_value = os.getenv("ADMIN_IDS") or os.getenv("TELEGRAM_ADMIN_IDS") or ""
        ids: set[int] = set()

        if raw_value:
            for item in raw_value.replace(";", ",").split(","):
                item = item.strip()
                if not item:
                    continue
                ids.add(int(item))

        try:
            ids.add(self.admin_id)
        except Exception:
            pass

        return ids

    def is_admin(self, user_id: Optional[int]) -> bool:
        """Проверить, входит ли пользователь в список администраторов."""
        if user_id is None:
            return False
        return int(user_id) in self.admin_ids

    @property
    def telegram_mini_app_name(self) -> Optional[str]:
        """Short name отдельного Telegram Mini App, если он настроен в BotFather."""
        value = os.getenv("TELEGRAM_MINI_APP_NAME") or os.getenv("MINI_APP_SHORT_NAME") or ""
        value = value.strip().strip("/")
        return value or None

    def build_mini_app_link(self, bot_username: str, start_param: Optional[str] = None) -> str:
        """Собрать direct link Mini App для открытия из любого чата."""
        base = f"https://t.me/{bot_username}"
        if self.telegram_mini_app_name:
            base = f"{base}/{self.telegram_mini_app_name}"
        if start_param:
            return f"{base}?startapp={quote(start_param, safe='')}"
        return f"{base}?startapp"
    
    @property
    def db_host(self) -> str:
        """Хост базы данных"""
        return self.get('database', 'DB_HOST')
    
    @property
    def db_port(self) -> int:
        """Порт базы данных"""
        return self.get_int('database', 'DB_PORT')
    
    @property
    def db_name(self) -> str:
        """Имя базы данных"""
        return self.get('database', 'DB_NAME')
    
    @property
    def db_user(self) -> str:
        """Пользователь базы данных"""
        return self.get('database', 'DB_USER')
    
    @property
    def db_password(self) -> str:
        """Пароль базы данных"""
        return self.get('database', 'DB_PASSWORD')

    @property
    def database_url(self) -> str:
        """URL подключения к PostgreSQL для SQLAlchemy asyncpg"""
        value = os.getenv("DATABASE_URL")
        if value:
            if value.startswith("postgres://"):
                value = value.replace("postgres://", "postgresql://", 1)
            if value.startswith("postgresql://"):
                value = value.replace("postgresql://", "postgresql+asyncpg://", 1)
            return value
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )
    
    @property
    def redis_host(self) -> str:
        """Хост Redis"""
        return self.get('redis', 'REDIS_HOST')
    
    @property
    def redis_port(self) -> int:
        """Порт Redis"""
        return self.get_int('redis', 'REDIS_PORT')
    
    @property
    def redis_password(self) -> Optional[str]:
        """Пароль Redis"""
        password = self.get('redis', 'REDIS_PASSWORD', '')
        return password if password else None
    
    @property
    def redis_db(self) -> int:
        """Номер БД Redis"""
        return self.get_int('redis', 'REDIS_DB', 0)

    @property
    def redis_url(self) -> str:
        """URL подключения к Redis"""
        value = os.getenv("REDIS_URL")
        if value:
            return value
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    @property
    def web_port(self) -> int:
        """Порт веб-сервера"""
        return self.get_int('web', 'WEB_PORT', 8000)
    
    @property
    def web_host(self) -> str:
        """Хост веб-сервера"""
        return self.get('web', 'WEB_HOST', '0.0.0.0')
    
    @property
    def secret_key(self) -> str:
        """Секретный ключ для сессий"""
        return self.get('web', 'SECRET_KEY')
    
    @property
    def webapp_url(self) -> str:
        """Базовый URL для WebApp"""
        return self.get('web', 'WEBAPP_URL', 'http://localhost:8000')
    
    @property
    def max_participants(self) -> int:
        """Максимальное количество участников"""
        return self.get_int('bot', 'MAX_PARTICIPANTS', 10000)
    
    @property
    def youtube_api_key(self) -> Optional[str]:
        """API ключ YouTube Data API v3"""
        api_key = self.get('youtube', 'API_KEY', '')
        return api_key if api_key else None
    
    @property
    def youtube_client_id(self) -> Optional[str]:
        """OAuth 2.0 Client ID для YouTube"""
        client_id = self.get('youtube', 'CLIENT_ID', '')
        return client_id if client_id else None
    
    @property
    def youtube_client_secret(self) -> Optional[str]:
        """OAuth 2.0 Client Secret для YouTube"""
        client_secret = self.get('youtube', 'CLIENT_SECRET', '')
        return client_secret if client_secret else None

    @property
    def tiktok_enabled(self) -> bool:
        """Включена ли OAuth интеграция TikTok."""
        return self.get_bool('tiktok', 'ENABLED', False)

    @property
    def tiktok_client_id(self) -> Optional[str]:
        """Client key для TikTok Login Kit."""
        value = self.get('tiktok', 'CLIENT_ID', '')
        return value if value else None

    @property
    def tiktok_client_secret(self) -> Optional[str]:
        """Client secret для TikTok Login Kit."""
        value = self.get('tiktok', 'CLIENT_SECRET', '')
        return value if value else None

    @property
    def tiktok_scopes(self) -> str:
        """OAuth scopes для TikTok."""
        return self.get('tiktok', 'SCOPES', 'user.info.basic')

    @property
    def tiktok_research_access_token(self) -> Optional[str]:
        """Client access token TikTok Research API для проверки following."""
        value = self.get('tiktok', 'RESEARCH_ACCESS_TOKEN', '')
        return value if value else None


# Глобальный экземпляр конфигурации
config = Config()
