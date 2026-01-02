"""
Обработчики для работы с конкурсами в каналах
"""
from aiogram import Router, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from database.db import AsyncSessionLocal
from bot.services.contest_service import ContestService
from shared.services.telegram_service import TelegramService
from shared.config import config

router = Router()


def format_contest_message(contest, bot_username: str) -> tuple[str, InlineKeyboardMarkup]:
    """
    Форматировать сообщение о конкурсе
    
    @param contest объект конкурса
    @param bot_username username бота (без @)
    @return текст сообщения и клавиатура
    """
    text = f"🎉 <b>{contest.title}</b>\n\n"
    
    if contest.description:
        text += f"{contest.description}\n\n"
    
    # Призовые места
    text += "🏆 <b>Призовые места:</b>\n"
    prizes = sorted(contest.prizes, key=lambda p: p.place)
    for prize in prizes:
        emoji = "🥇" if prize.place == 1 else "🥈" if prize.place == 2 else "🥉" if prize.place == 3 else "🏆"
        text += f"{emoji} <b>{prize.place} место:</b> {prize.title}\n"
        if prize.description:
            text += f"   {prize.description}\n"
    
    # Спонсоры
    if contest.sponsors:
        text += "\n📢 <b>Спонсоры:</b>\n"
        for sponsor in contest.sponsors:
            text += f"• {sponsor.channel_title}\n"
    
    # Информация о YouTube подписке
    if contest.youtube_channel_id:
        youtube_url = None
        # Формируем URL в зависимости от формата ID
        yid = contest.youtube_channel_id.strip() if contest.youtube_channel_id else ""
        if not yid:
            youtube_url = None
        elif yid.startswith('http'):
            youtube_url = yid
        elif 'youtube.com' in yid:
            youtube_url = f"https://{yid}" if not yid.startswith('http') else yid
            if yid.startswith('//'):
                youtube_url = f"https:{yid}"
        elif yid.startswith('@'):
            youtube_url = f"https://youtube.com/{yid}"
        elif yid.startswith('UC') or yid.startswith('HC'):
            youtube_url = f"https://youtube.com/channel/{yid}"
        elif len(yid) == 22 and all(c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in yid):
            # Похоже на ID канала без префикса UC
            youtube_url = f"https://youtube.com/channel/UC{yid}"
        else:
            youtube_url = f"https://youtube.com/@{yid}"
        
        text += "\n📺 <b>Условие участия:</b>\n"
        text += f"Необходимо подписаться на YouTube канал:\n"
        text += f"<a href=\"{youtube_url}\">Подписаться на канал →</a>\n"
        if contest.youtube_subscription_days_required > 0:
            text += f"Требуется подписка минимум на {contest.youtube_subscription_days_required} "
            if contest.youtube_subscription_days_required == 1:
                text += "день\n"
            elif contest.youtube_subscription_days_required < 5:
                text += "дня\n"
            else:
                text += "дней\n"
    
    # Дата окончания - отображаем как есть (в БД хранится в киевском времени)
    text += f"\n⏰ <b>Дата окончания:</b> {contest.end_date.strftime('%d.%m.%Y %H:%M')}\n"
    
    # Используем startapp= для открытия WebApp напрямую
    # Формат: https://t.me/{bot_username}?startapp=contest_{contest.id}
    # Это работает только если домен настроен через /setdomain в BotFather
    # Telegram автоматически откроет WebApp с домена, указанного в /setdomain
    register_url = f"https://t.me/{bot_username}?startapp=contest_{contest.id}"
    
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Формируем startapp URL для регистрации конкурса {contest.id}: {register_url}")
    
    # Используем обычную URL кнопку с startapp параметром
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🎯 Зарегистрироваться",
            url=register_url
        )]
    ])
    
    return text, keyboard


def format_results_message(contest, bot_username: str) -> tuple[str, InlineKeyboardMarkup]:
    """
    Форматировать сообщение с результатами конкурса
    
    @param contest объект конкурса
    @param bot_username username бота (без @)
    @return текст сообщения и клавиатура
    """
    text = f"🏆 <b>Результаты конкурса: {contest.title}</b>\n\n"
    
    # Победители
    prizes = sorted(contest.prizes, key=lambda p: p.place)
    winners = [p for p in prizes if p.winner_user_id]
    
    if winners:
        text += "🎉 <b>Победители:</b>\n\n"
        for prize in winners:
            emoji = "🥇" if prize.place == 1 else "🥈" if prize.place == 2 else "🥉" if prize.place == 3 else "🏆"
            text += f"{emoji} <b>{prize.place} место:</b> {prize.title}\n"
            # Формируем ссылку на пользователя
            if prize.winner_username:
                winner_link = f"<a href=\"https://t.me/{prize.winner_username}\">@{prize.winner_username}</a>"
            elif prize.winner_firstname:
                winner_link = f"<a href=\"tg://user?id={prize.winner_user_id}\">{prize.winner_firstname}</a>"
            else:
                winner_link = "не указан"
            text += f"   Победитель: {winner_link}\n\n"
    
    # Используем startapp= для открытия WebApp напрямую
    # Формат: https://t.me/{bot_username}?startapp=results_{contest.id}
    results_url = f"https://t.me/{bot_username}?startapp=results_{contest.id}"
    
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Формируем startapp URL для результатов конкурса {contest.id}: {results_url}")
    
    # Используем обычную URL кнопку с startapp параметром
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📊 Посмотреть результаты",
            url=results_url
        )]
    ])
    
    return text, keyboard


async def publish_contest_to_channel(contest_id: int, bot: Bot, webapp_url: str) -> bool:
    """
    Опубликовать конкурс в канале
    
    @param contest_id ID конкурса
    @param bot экземпляр бота
    @param webapp_url URL вебаппа (не используется, оставлен для совместимости)
    @return True если успешно
    """
    async with AsyncSessionLocal() as db:
        service = ContestService(db)
        contest = await service.get_contest_by_id(contest_id)
        
        if not contest:
            return False
        
        # Получаем информацию о боте для проверки прав и username
        bot_info = await bot.get_me()
        bot_username = bot_info.username
        if not bot_username:
            print("Ошибка: Не удалось получить username бота")
            return False
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Публикация конкурса {contest_id}: bot_username = {bot_username}")
        
        # Формируем сообщение с startapp ссылкой для открытия WebApp
        text, keyboard = format_contest_message(contest, bot_username)
        
        try:
            # Проверяем права бота в канале
            try:
                bot_member = await bot.get_chat_member(chat_id=contest.channel_id, user_id=bot_info.id)
                if bot_member.status not in ['administrator', 'creator']:
                    print(f"Ошибка: Бот не является администратором канала. Статус: {bot_member.status}")
                    return False
            except Exception as e:
                print(f"Ошибка проверки прав бота: {e}")
                return False
            
            # Отправляем сообщение в канал с фото, если есть изображение
            if contest.image_path:
                # Проверяем существование файла
                import os
                from pathlib import Path
                from aiogram.types import FSInputFile
                
                # Формируем абсолютный путь к файлу в контейнере
                # contest.image_path хранится как "uploads/filename.png"
                # В контейнере рабочая директория /app
                if contest.image_path.startswith('/'):
                    image_path = Path(contest.image_path)
                else:
                    image_path = Path('/app') / contest.image_path
                
                if image_path.exists():
                    # Используем FSInputFile для отправки фото
                    photo_file = FSInputFile(str(image_path))
                    message = await bot.send_photo(
                        chat_id=contest.channel_id,
                        photo=photo_file,
                        caption=text,
                        reply_markup=keyboard,
                        parse_mode="HTML"
                    )
                else:
                    # Если файл не найден, отправляем без фото
                    print(f"Предупреждение: Файл изображения не найден: {image_path}")
                    message = await bot.send_message(
                        chat_id=contest.channel_id,
                        text=text,
                        reply_markup=keyboard,
                        parse_mode="HTML"
                    )
            else:
                # Отправляем сообщение в канал с обычной URL кнопкой
                message = await bot.send_message(
                    chat_id=contest.channel_id,
                    text=text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            
            await service.publish_contest(contest_id, message.message_id)
            return True
            
        except Exception as e:
            print(f"Ошибка публикации конкурса: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return False


async def publish_results_to_channel(contest_id: int, bot: Bot, webapp_url: str) -> bool:
    """
    Опубликовать результаты конкурса в канале
    
    @param contest_id ID конкурса
    @param bot экземпляр бота
    @param webapp_url URL вебаппа
    @return True если успешно
    """
    async with AsyncSessionLocal() as db:
        service = ContestService(db)
        contest = await service.get_contest_by_id(contest_id)
        
        if not contest:
            return False
        
        # Получаем username бота для создания startapp ссылки
        bot_info = await bot.get_me()
        bot_username = bot_info.username
        if not bot_username:
            print("Ошибка: Не удалось получить username бота")
            return False
        
        # Формируем сообщение с startapp ссылкой для открытия WebApp
        text, keyboard = format_results_message(contest, bot_username)
        
        try:
            message = await bot.send_message(
                chat_id=contest.channel_id,
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            
            await service.publish_results(contest_id, message.message_id)
            
            # Отправляем уведомления победителям
            await notify_winners(contest, bot)
            
            return True
        except Exception as e:
            print(f"Ошибка публикации результатов: {e}")
            return False


async def notify_winners(contest, bot: Bot):
    """
    Отправить уведомления победителям
    
    @param contest объект конкурса
    @param bot экземпляр бота
    """
    telegram_service = TelegramService(bot)
    
    prizes = sorted(contest.prizes, key=lambda p: p.place)
    winners = [p for p in prizes if p.winner_user_id]
    
    for prize in winners:
        if prize.winner_user_id:
            # Проверяем, писал ли пользователь боту
            has_started = await telegram_service.has_user_started_bot(prize.winner_user_id)
            
            if has_started:
                emoji = "🥇" if prize.place == 1 else "🥈" if prize.place == 2 else "🥉" if prize.place == 3 else "🏆"
                message = (
                    f"🎉 Поздравляем! Вы выиграли {prize.place} место в конкурсе \"{contest.title}\"!\n\n"
                    f"{emoji} <b>Ваш приз:</b> {prize.title}\n"
                )
                if prize.description:
                    message += f"{prize.description}\n"
                
                await telegram_service.send_message_to_user(
                    prize.winner_user_id,
                    message,
                    parse_mode="HTML"
                )

