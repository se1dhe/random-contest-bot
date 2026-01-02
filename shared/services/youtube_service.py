"""
Сервис для работы с YouTube API
Проверка подписки на YouTube канал
"""
import logging
import aiohttp
from typing import Optional, Dict
from datetime import datetime, timedelta
from shared.config import config

logger = logging.getLogger(__name__)


class YouTubeService:
    """Сервис для работы с YouTube API"""
    
    def __init__(self):
        """
        Инициализация сервиса
        
        """
        self.api_key = config.youtube_api_key if hasattr(config, 'youtube_api_key') else None
        self.base_url = "https://www.googleapis.com/youtube/v3"
    
    async def get_channel_info(self, channel_id: str) -> Optional[Dict[str, any]]:
        """
        Получить информацию о YouTube канале
        
        @param channel_id ID YouTube канала
        @return словарь с информацией о канале (title, description, customUrl, thumbnail)
        """
        if not self.api_key:
            logger.error("YouTube API ключ не настроен")
            return None
            
        try:
            url = f"{self.base_url}/channels"
            params = {
                'part': 'snippet',
                'id': channel_id,
                'key': self.api_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        logger.error(f"Ошибка YouTube API: {response.status}")
                        return None
                        
                    data = await response.json()
                    
                    if 'items' in data and len(data['items']) > 0:
                        snippet = data['items'][0]['snippet']
                        return {
                            'title': snippet.get('title'),
                            'description': snippet.get('description'),
                            'customUrl': snippet.get('customUrl'),
                            'thumbnail': snippet.get('thumbnails', {}).get('default', {}).get('url')
                        }
                    else:
                        logger.warning(f"Канал {channel_id} не найден")
                        return None
                        
        except Exception as e:
            logger.error(f"Ошибка при получении информации о канале {channel_id}: {e}")
            return None

    async def check_subscription(
        self, 
        user_youtube_channel_id: str, 
        required_channel_id: str,
        min_days: int = 0,
        oauth_token: Optional[str] = None,
        oauth_credentials: Optional[any] = None
    ) -> Dict[str, any]:
        """
        Проверить подписку пользователя на YouTube канал
        
        ВАЖНО: Для проверки подписки конкретного пользователя нужен OAuth credentials этого пользователя.
        
        @param user_youtube_channel_id ID YouTube канала пользователя (channel ID)
        @param required_channel_id ID YouTube канала, на который должна быть подписка
        @param min_days минимальное количество дней подписки (0 = проверка не требуется)
        @param oauth_token OAuth токен пользователя (устаревший параметр, используйте oauth_credentials)
        @param oauth_credentials OAuth credentials объект от google-auth
        @return словарь с результатом проверки: {'subscribed': bool, 'days_subscribed': int, 'error': str}
        """
        if oauth_credentials:
            # Используем google-api-python-client для проверки подписки
            try:
                from googleapiclient.discovery import build
                
                youtube = build('youtube', 'v3', credentials=oauth_credentials)
                
                # Проверяем подписку через subscriptions.list
                request = youtube.subscriptions().list(
                    part='snippet',
                    mine=True,
                    forChannelId=required_channel_id,
                    maxResults=1
                )
                
                response = request.execute()
                
                if 'items' in response and len(response['items']) > 0:
                    # Пользователь подписан
                    subscription = response['items'][0]
                    published_at_str = subscription['snippet'].get('publishedAt')
                    
                    if published_at_str:
                        # Парсим дату подписки
                        try:
                            published_at = datetime.fromisoformat(
                                published_at_str.replace('Z', '+00:00')
                            )
                            now = datetime.now(published_at.tzinfo) if published_at.tzinfo else datetime.utcnow()
                            days_subscribed = (now - published_at).days
                            
                            subscribed = days_subscribed >= min_days if min_days > 0 else True
                            
                            return {
                                'subscribed': subscribed,
                                'days_subscribed': days_subscribed,
                                'error': None
                            }
                        except ValueError as e:
                            logger.warning(f"Ошибка парсинга даты подписки: {e}")
                            return {
                                'subscribed': True,
                                'days_subscribed': 0,
                                'error': None
                            }
                    else:
                        return {
                            'subscribed': True,
                            'days_subscribed': 0,
                            'error': None
                        }
                else:
                    # Пользователь не подписан
                    return {
                        'subscribed': False,
                        'days_subscribed': 0,
                        'error': None
                    }
                    
            except Exception as e:
                logger.error(f"Ошибка проверки подписки через OAuth: {e}", exc_info=True)
                return {
                    'subscribed': False,
                    'days_subscribed': 0,
                    'error': str(e)
                }
        
        # Fallback на старый метод через API ключ (не работает для проверки подписки конкретного пользователя)
        if not self.api_key:
            logger.error("YouTube API ключ не настроен и OAuth credentials не предоставлены")
            return {
                'subscribed': False,
                'days_subscribed': 0,
                'error': 'YouTube API ключ не настроен и OAuth credentials не предоставлены'
            }
        
        try:
            # Проверяем подписку через YouTube Data API v3
            # Используем subscriptions.list для проверки подписки
            subscriptions_url = f"{self.base_url}/subscriptions"
            
            async with aiohttp.ClientSession() as session:
                params = {
                    'part': 'snippet,contentDetails',
                    'channelId': user_youtube_channel_id,
                    'forChannelId': required_channel_id,
                    'key': self.api_key,
                    'maxResults': 1
                }
                
                # Если есть OAuth токен, используем его вместо API ключа
                headers = {}
                if oauth_token:
                    headers['Authorization'] = f'Bearer {oauth_token}'
                    # При использовании OAuth токена не нужен API ключ в params
                    params.pop('key', None)
                
                async with session.get(subscriptions_url, params=params, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        if 'items' in data and len(data['items']) > 0:
                            # Пользователь подписан
                            subscription = data['items'][0]
                            published_at_str = subscription['snippet'].get('publishedAt')
                            
                            if published_at_str:
                                # Парсим дату подписки
                                try:
                                    published_at = datetime.fromisoformat(
                                        published_at_str.replace('Z', '+00:00')
                                    )
                                    now = datetime.now(published_at.tzinfo) if published_at.tzinfo else datetime.utcnow()
                                    days_subscribed = (now - published_at).days
                                    
                                    subscribed = days_subscribed >= min_days if min_days > 0 else True
                                    
                                    return {
                                        'subscribed': subscribed,
                                        'days_subscribed': days_subscribed,
                                        'error': None
                                    }
                                except ValueError as e:
                                    logger.warning(f"Ошибка парсинга даты подписки: {e}")
                                    return {
                                        'subscribed': True,
                                        'days_subscribed': 0,
                                        'error': None
                                    }
                            else:
                                return {
                                    'subscribed': True,
                                    'days_subscribed': 0,
                                    'error': None
                                }
                        else:
                            # Пользователь не подписан
                            return {
                                'subscribed': False,
                                'days_subscribed': 0,
                                'error': None
                            }
                    elif resp.status == 403:
                        error_data = await resp.json()
                        error_reason = error_data.get('error', {}).get('errors', [{}])[0].get('reason', 'unknown')
                        
                        if error_reason == 'insufficientPermissions':
                            return {
                                'subscribed': False,
                                'days_subscribed': 0,
                                'error': 'Недостаточно прав для проверки подписки. Требуется OAuth авторизация пользователя.'
                            }
                        else:
                            error_text = await resp.text()
                            logger.error(f"Ошибка YouTube API (403): {error_text}")
                            return {
                                'subscribed': False,
                                'days_subscribed': 0,
                                'error': f'Ошибка доступа: {error_reason}'
                            }
                    else:
                        error_text = await resp.text()
                        logger.error(f"Ошибка YouTube API: {resp.status} - {error_text}")
                        return {
                            'subscribed': False,
                            'days_subscribed': 0,
                            'error': f'Ошибка API: {resp.status}'
                        }
        except Exception as e:
            logger.error(f"Ошибка проверки подписки на YouTube: {e}", exc_info=True)
            return {
                'subscribed': False,
                'days_subscribed': 0,
                'error': str(e)
            }
    
    async def get_channel_id_by_username(self, username: str) -> Optional[str]:
        """
        Получить ID канала по username
        
        @param username username канала (без @)
        @return ID канала или None
        """
        if not self.api_key:
            logger.error("YouTube API ключ не настроен")
            return None
        
        try:
            # Убираем @ если есть
            username = username.lstrip('@')
            
            # Получаем информацию о канале
            channels_url = f"{self.base_url}/channels"
            
            async with aiohttp.ClientSession() as session:
                params = {
                    'part': 'id',
                    'forUsername': username,
                    'key': self.api_key
                }
                
                async with session.get(channels_url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        if 'items' in data and len(data['items']) > 0:
                            return data['items'][0]['id']
                        else:
                            logger.warning(f"Канал с username {username} не найден")
                            return None
                    else:
                        error_text = await resp.text()
                        logger.error(f"Ошибка получения канала {username}: {resp.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Ошибка получения ID канала {username}: {e}", exc_info=True)
            return None
    
    async def get_channel_id_by_url(self, url: str) -> Optional[str]:
        """
        Получить ID канала по URL
        
        @param url URL канала (например, https://www.youtube.com/@channel или https://www.youtube.com/channel/UC...)
        @return ID канала или None
        """
        if not self.api_key:
            logger.error("YouTube API ключ не настроен")
            return None
        
        try:
            # Извлекаем username или channel ID из URL
            if '/@' in url:
                # Новый формат: https://www.youtube.com/@username
                username = url.split('/@')[1].split('/')[0].split('?')[0]
                return await self.get_channel_id_by_username(username)
            elif '/channel/' in url:
                # Старый формат: https://www.youtube.com/channel/UC...
                channel_id = url.split('/channel/')[1].split('/')[0].split('?')[0]
                return channel_id
            elif '/c/' in url or '/user/' in url:
                # Формат: https://www.youtube.com/c/username или /user/username
                username = url.split('/')[-1].split('?')[0]
                return await self.get_channel_id_by_username(username)
            else:
                logger.warning(f"Неизвестный формат URL: {url}")
                return None
        except Exception as e:
            logger.error(f"Ошибка парсинга URL {url}: {e}", exc_info=True)
            return None

