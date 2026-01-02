"""
Сервис для работы с Telegram API
"""
from typing import Optional, List
from aiogram import Bot
from aiogram.types import ChatMember


class TelegramService:
    """Сервис для работы с Telegram API"""
    
    def __init__(self, bot: Bot):
        """
        Инициализация сервиса
        
        @param bot экземпляр бота aiogram
        """
        self.bot = bot
    
    async def check_subscription(self, user_id: int, channel_id: int) -> bool:
        """
        Проверить подписку пользователя на канал
        
        @param user_id ID пользователя
        @param channel_id ID канала
        @return True если пользователь подписан, False иначе
        """
        try:
            member = await self.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
            # Пользователь подписан если статус member, administrator или creator
            return member.status in ['member', 'administrator', 'creator']
        except Exception:
            return False
    
    async def check_subscriptions(self, user_id: int, channel_ids: List[int]) -> dict[int, bool]:
        """
        Проверить подписки пользователя на несколько каналов
        
        @param user_id ID пользователя
        @param channel_ids список ID каналов
        @return словарь {channel_id: is_subscribed}
        """
        import asyncio
        tasks = [self.check_subscription(user_id, channel_id) for channel_id in channel_ids]
        results_list = await asyncio.gather(*tasks)
        return {channel_id: result for channel_id, result in zip(channel_ids, results_list)}
    
    async def get_chat_info(self, chat_id: int) -> Optional[dict]:
        """
        Получить информацию о чате/канале
        
        @param chat_id ID чата/канала
        @return информация о чате или None
        """
        try:
            chat = await self.bot.get_chat(chat_id=chat_id)
            return {
                'id': chat.id,
                'title': chat.title,
                'username': chat.username,
                'type': chat.type
            }
        except Exception:
            return None
    
    async def get_chat_info_by_username(self, username: str) -> Optional[dict]:
        """
        Получить информацию о чате/канале по username
        
        Использует прямой вызов Telegram Bot API для обхода проблем с десериализацией
        новых типов реакций (например, 'paid')
        
        @param username username канала (без @)
        @return информация о чате или None
        """
        import logging
        import aiohttp
        from shared.config import config
        
        logger = logging.getLogger(__name__)
        
        try:
            # Убираем @ если есть
            username = username.lstrip('@')
            
            if not username:
                return None
            
            # Используем прямой вызов API для обхода проблем с десериализацией
            chat_id = f"@{username}"
            logger.debug(f"Попытка получить информацию о канале через прямой API: {chat_id}")
            
            async with aiohttp.ClientSession() as session:
                url = f"https://api.telegram.org/bot{config.bot_token}/getChat"
                async with session.get(url, params={"chat_id": chat_id}) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get('ok'):
                            result = data.get('result', {})
                            
                            # Извлекаем нужную информацию
                            channel_id = result.get('id')
                            channel_title = result.get('title')
                            channel_username = result.get('username')
                            channel_type = result.get('type')
                            
                            if channel_type not in ['channel', 'supergroup']:
                                logger.warning(f"Чат {username} не является каналом или супергруппой, тип: {channel_type}")
                                return None
                            
                            logger.info(f"Успешно получена информация о канале: id={channel_id}, title={channel_title}")
                            
                            return {
                                'id': channel_id,
                                'title': channel_title or username,
                                'username': channel_username or username,
                                'type': channel_type
                            }
                    else:
                        error_text = await resp.text()
                        logger.error(f"Ошибка API при получении канала {chat_id}: {resp.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Ошибка получения информации о канале {username}: {e}", exc_info=True)
            return None
    
    async def send_message_to_user(self, user_id: int, text: str, parse_mode: Optional[str] = None) -> bool:
        """
        Отправить сообщение пользователю
        
        @param user_id ID пользователя
        @param text текст сообщения
        @param parse_mode режим парсинга (HTML, Markdown)
        @return True если сообщение отправлено, False иначе
        """
        try:
            await self.bot.send_message(chat_id=user_id, text=text, parse_mode=parse_mode)
            return True
        except Exception:
            return False
    
    async def has_user_started_bot(self, user_id: int) -> bool:
        """
        Проверить, писал ли пользователь боту /start
        
        @param user_id ID пользователя
        @return True если пользователь писал боту, False иначе
        """
        try:
            # Пытаемся отправить пустое сообщение, если получится - пользователь писал боту
            # Но лучше использовать другой метод - проверить через get_chat
            chat = await self.bot.get_chat(user_id)
            return chat is not None
        except Exception:
            return False

