"""
Утилиты для работы с ngrok
"""
from pyngrok import ngrok, conf
from shared.config import config
import logging

logger = logging.getLogger(__name__)


def setup_ngrok(port: int) -> str:
    """
    Настроить ngrok туннель
    
    @param port порт для туннелирования
    @return URL туннеля
    """
    if not config.ngrok_enabled:
        logger.info("Ngrok отключен в конфигурации")
        return None
    
    try:
        # Устанавливаем токен
        conf.get_default().auth_token = config.ngrok_authtoken
        
        # Настраиваем регион
        conf.get_default().region = config.ngrok_region
        
        # Создаем туннель
        if config.ngrok_domain:
            # Используем постоянный домен
            tunnel = ngrok.connect(port, domain=config.ngrok_domain)
        else:
            # Создаем временный туннель
            tunnel = ngrok.connect(port)
        
        url = tunnel.public_url
        logger.info(f"Ngrok туннель создан: {url}")
        return url
        
    except Exception as e:
        logger.error(f"Ошибка настройки ngrok: {e}")
        return None


def close_ngrok():
    """Закрыть ngrok туннель"""
    try:
        ngrok.kill()
        logger.info("Ngrok туннель закрыт")
    except Exception as e:
        logger.error(f"Ошибка закрытия ngrok: {e}")

