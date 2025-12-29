"""
Сервис для проверки авторизации через Telegram WebApp
"""
import hmac
import hashlib
import json
import time
from typing import Optional, Dict
from urllib.parse import parse_qsl
from shared.config import config


def verify_telegram_webapp_initdata(init_data: str) -> Optional[Dict]:
    """
    Проверить и распарсить initData от Telegram WebApp
    
    Алгоритм проверки согласно документации Telegram:
    1. Парсим query string
    2. Извлекаем hash
    3. Создаем data_check_string из отсортированных параметров
    4. Вычисляем secret_key = HMAC_SHA256("WebAppData", bot_token)
    5. Вычисляем hash = HMAC_SHA256(secret_key, data_check_string)
    6. Сравниваем с полученным hash
    
    @param init_data строка initData от Telegram
    @return словарь с данными пользователя или None если невалидно
    """
    try:
        # Парсим query string
        parsed_data = dict(parse_qsl(init_data))
        
        # Проверяем наличие hash
        if 'hash' not in parsed_data:
            return None
        
        received_hash = parsed_data.pop('hash')
        
        # Создаем строку для проверки (сортируем по ключу)
        data_check_string = '\n'.join(
            f"{key}={value}"
            for key, value in sorted(parsed_data.items())
        )
        
        # Создаем секретный ключ: HMAC_SHA256("WebAppData", bot_token)
        secret_key = hmac.new(
            "WebAppData".encode(),
            config.bot_token.encode(),
            hashlib.sha256
        ).digest()
        
        # Вычисляем hash: HMAC_SHA256(secret_key, data_check_string)
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Проверяем hash
        if calculated_hash != received_hash:
            return None
        
        # Проверяем время (не старше 24 часов)
        if 'auth_date' in parsed_data:
            auth_date = int(parsed_data['auth_date'])
            current_time = int(time.time())
            if current_time - auth_date > 86400:  # 24 часа
                return None
        
        # Парсим user данные
        user_data = {}
        if 'user' in parsed_data:
            try:
                user_data = json.loads(parsed_data['user'])
            except json.JSONDecodeError:
                return None
        
        return {
            'user': user_data,
            'auth_date': parsed_data.get('auth_date'),
            'query_id': parsed_data.get('query_id'),
            'hash': received_hash
        }
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка проверки initData: {e}")
        return None


def is_admin(user_id: Optional[int]) -> bool:
    """
    Проверить, является ли пользователь администратором
    
    @param user_id ID пользователя
    @return True если администратор
    """
    if not user_id:
        return False
    return user_id == config.admin_id

