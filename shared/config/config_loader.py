"""
Модуль для загрузки конфигурации из config.ini
"""
import configparser
import os
from pathlib import Path
from typing import Optional


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
    def ngrok_enabled(self) -> bool:
        """Включен ли ngrok"""
        return self.get_bool('ngrok', 'ENABLED')
    
    @property
    def ngrok_authtoken(self) -> str:
        """Токен ngrok"""
        return self.get('ngrok', 'NGROK_AUTHTOKEN')
    
    @property
    def ngrok_domain(self) -> Optional[str]:
        """Домен ngrok"""
        domain = self.get('ngrok', 'NGROK_DOMAIN', '')
        return domain if domain else None
    
    @property
    def ngrok_region(self) -> str:
        """Регион ngrok"""
        return self.get('ngrok', 'NGROK_REGION', 'eu')
    
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


# Глобальный экземпляр конфигурации
config = Config()

