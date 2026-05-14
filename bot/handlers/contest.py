"""
Обработчики для работы с конкурсами в каналах
"""
from __future__ import annotations

import logging

from aiogram import Router, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import FSInputFile
from sqlalchemy.ext.asyncio import AsyncSession
from database.db import AsyncSessionLocal
from bot.services.contest_service import ContestService
from shared.services.telegram_service import TelegramService
from shared.services.upload_storage import build_public_media_url, resolve_upload_image_path
from shared.config import config
from shared.i18n import day_unit, normalize_language, translate

router = Router()
logger = logging.getLogger(__name__)


async def format_contest_message(
    contest,
    bot: Bot,
    bot_username: str,
    resolve_private_links: bool = True,
) -> tuple[str, InlineKeyboardMarkup]:
    """
    Форматировать сообщение о конкурсе
    
    @param contest объект конкурса
    @param bot_username username бота (без @)
    @return текст сообщения и клавиатура
    """
    language = normalize_language(getattr(contest, "language", None))
    text = f"🎉 <b>{contest.title}</b>\n\n"
    
    if contest.description:
        text += f"{contest.description}\n\n"
    
    # Призовые места
    text += f"🏆 <b>{translate(language, 'prize_places')}:</b>\n"
    prizes = sorted(contest.prizes, key=lambda p: p.place)
    for prize in prizes:
        emoji = "🥇" if prize.place == 1 else "🥈" if prize.place == 2 else "🥉" if prize.place == 3 else "🏆"
        text += f"{emoji} <b>{prize.place} {translate(language, 'place')}:</b> {prize.title}\n"
        if prize.description:
            text += f"   {prize.description}\n"
    
    # Спонсоры
    if contest.sponsors:
        text += f"\n📢 <b>{translate(language, 'sponsors')}:</b>\n"
        for sponsor in contest.sponsors:
            if sponsor.channel_username:
                text += f"• <a href=\"https://t.me/{sponsor.channel_username}\">{sponsor.channel_title}</a>\n"
            elif resolve_private_links:
                try:
                    invite = await bot.create_chat_invite_link(chat_id=sponsor.channel_id, name=f"{contest.title} sponsor", creates_join_request=False)
                    if invite and getattr(invite, "invite_link", None):
                        text += f"• <a href=\"{invite.invite_link}\">{sponsor.channel_title}</a>\n"
                    else:
                        text += f"• {sponsor.channel_title}\n"
                except Exception:
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
        
        text += f"\n📺 <b>{translate(language, 'participation_condition')}:</b>\n"
        text += f"{translate(language, 'youtube_required')}\n"
        text += f"<a href=\"{youtube_url}\">{translate(language, 'subscribe_channel')}</a>\n"
        if contest.youtube_subscription_days_required > 0:
            days_required = contest.youtube_subscription_days_required
            text += translate(
                language,
                "subscription_required_days",
                days=days_required,
                unit=day_unit(language, days_required),
            )
            text += "\n"
    
    # Дата окончания - отображаем как есть (в БД хранится в киевском времени)
    text += f"\n⏰ <b>{translate(language, 'end_date')}:</b> {contest.end_date.strftime('%d.%m.%Y %H:%M')}\n"
    
    # Direct Link Mini App открывает приложение в текущем чате/топике.
    register_url = config.build_mini_app_link(bot_username, f"contest_{contest.id}")
    logger.info(f"Формируем Mini App direct link для регистрации конкурса {contest.id}: {register_url}")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"🎯 {translate(language, 'register')}",
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
    language = normalize_language(getattr(contest, "language", None))
    text = f"🏆 <b>{translate(language, 'results_title', title=contest.title)}</b>\n\n"
    
    # Победители
    prizes = sorted(contest.prizes, key=lambda p: p.place)
    winners = [p for p in prizes if p.winner_user_id]
    
    if winners:
        text += f"🎉 <b>{translate(language, 'winners')}:</b>\n\n"
        for prize in winners:
            emoji = "🥇" if prize.place == 1 else "🥈" if prize.place == 2 else "🥉" if prize.place == 3 else "🏆"
            text += f"{emoji} <b>{prize.place} {translate(language, 'place')}:</b> {prize.title}\n"
            # Формируем ссылку на пользователя
            if prize.winner_username:
                winner_link = f"<a href=\"https://t.me/{prize.winner_username}\">@{prize.winner_username}</a>"
            elif prize.winner_firstname:
                winner_link = f"<a href=\"tg://user?id={prize.winner_user_id}\">{prize.winner_firstname}</a>"
            else:
                winner_link = translate(language, "not_specified")
            text += f"   {translate(language, 'winner')}: {winner_link}\n\n"
    
    results_url = config.build_mini_app_link(bot_username, f"results_{contest.id}")

    logger.info(f"Формируем Mini App direct link для результатов конкурса {contest.id}: {results_url}")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"📊 {translate(language, 'view_results')}",
            url=results_url
        )]
    ])
    
    return text, keyboard


async def _send_contest_post(bot: Bot, contest, text: str, keyboard: InlineKeyboardMarkup, chat_id: int):
    message_thread_id = contest.message_thread_id if chat_id == contest.channel_id else None
    image_path = resolve_upload_image_path(contest.image_path)
    if image_path and image_path.exists():
        photo_file = FSInputFile(str(image_path))
        return await bot.send_photo(
            chat_id=chat_id,
            message_thread_id=message_thread_id,
            photo=photo_file,
            caption=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

    if image_path and not image_path.exists():
        logger.warning(f"Файл изображения не найден: {image_path}")

    public_image_url = build_public_media_url(contest.image_path)
    if public_image_url:
        try:
            return await bot.send_photo(
                chat_id=chat_id,
                message_thread_id=message_thread_id,
                photo=public_image_url,
                caption=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        except Exception as exc:
            logger.warning("Не удалось отправить изображение по URL %s: %s", public_image_url, exc)

    return await bot.send_message(
        chat_id=chat_id,
        message_thread_id=message_thread_id,
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )


def _is_message_not_modified_error(error: Exception) -> bool:
    return "message is not modified" in str(error).lower()


def _should_replace_message_after_edit_error(error: Exception) -> bool:
    error_text = str(error).lower()
    fallback_markers = (
        "message to edit not found",
        "there is no text in the message to edit",
        "there is no caption in the message to edit",
        "message content is not modified",
        "message can't be edited",
        "message identifier is not specified",
        "bad request: message to edit not found",
    )
    return any(marker in error_text for marker in fallback_markers)


async def publish_contest_to_channel(contest_id: int, bot: Bot, webapp_url: str, force_republish: bool = False) -> bool:
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

        if not force_republish and contest.status.value == "active" and contest.message_id:
            logger.info("Конкурс %s уже опубликован (message_id=%s), повторная публикация пропущена", contest_id, contest.message_id)
            return True
        
        # Получаем информацию о боте для проверки прав и username
        bot_info = await bot.get_me()
        bot_username = bot_info.username
        if not bot_username:
            logger.error("Не удалось получить username бота для публикации конкурса %s", contest_id)
            return False

        logger.info(f"Публикация конкурса {contest_id}: bot_username = {bot_username}")
        
        # Формируем сообщение с startapp ссылкой для открытия WebApp
        text, keyboard = await format_contest_message(contest, bot, bot_username)
        
        try:
            # Проверяем права бота в канале
            try:
                bot_member = await bot.get_chat_member(chat_id=contest.channel_id, user_id=bot_info.id)
                if bot_member.status not in ['administrator', 'creator']:
                    logger.error("Бот не является администратором канала %s. Статус: %s", contest.channel_id, bot_member.status)
                    return False
            except Exception as e:
                logger.error("Ошибка проверки прав бота для канала %s: %s", contest.channel_id, e, exc_info=True)
                return False

            message = await _send_contest_post(bot, contest, text, keyboard, contest.channel_id)

            if force_republish and contest.status.value == "active":
                contest.message_id = message.message_id
                await db.commit()
            else:
                await service.publish_contest(contest_id, message.message_id)
            
            # Публикация в каналы спонсоров
            if contest.post_to_sponsors and contest.sponsors:
                logger.info(f"Публикация в каналы спонсоров ({len(contest.sponsors)})")
                for sponsor in contest.sponsors:
                    try:
                        if contest.image_path:
                            await _send_contest_post(bot, contest, text, keyboard, sponsor.channel_id)
                        else:
                            await _send_contest_post(bot, contest, text, keyboard, sponsor.channel_id)
                    except Exception as e:
                        logger.error(f"Ошибка публикации в канал спонсора {sponsor.channel_title} ({sponsor.channel_id}): {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка публикации конкурса {contest_id}: {e}", exc_info=True)
            return False


async def edit_contest_post(contest_id: int, bot: Bot) -> bool:
    """
    Обновить уже опубликованный пост конкурса в основном канале.
    """
    async with AsyncSessionLocal() as db:
        service = ContestService(db)
        contest = await service.get_contest_by_id(contest_id)
        if not contest or not contest.message_id:
            logger.warning("Невозможно обновить пост конкурса %s: нет конкурса или message_id", contest_id)
            return False

        bot_info = await bot.get_me()
        bot_username = bot_info.username
        if not bot_username:
            logger.error("Не удалось получить username бота для обновления конкурса %s", contest_id)
            return False

        text, keyboard = await format_contest_message(contest, bot, bot_username)
        try:
            if contest.image_path:
                await bot.edit_message_caption(
                    chat_id=contest.channel_id,
                    message_id=contest.message_id,
                    caption=text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            else:
                await bot.edit_message_text(
                    chat_id=contest.channel_id,
                    message_id=contest.message_id,
                    text=text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            logger.info("Пост конкурса %s обновлен", contest_id)
            return True
        except Exception as e:
            if _is_message_not_modified_error(e):
                logger.info("Пост конкурса %s уже содержит актуальные данные", contest_id)
                return True

            if _should_replace_message_after_edit_error(e):
                logger.warning(
                    "Не удалось отредактировать существующий пост конкурса %s, будет создан новый пост: %s",
                    contest_id,
                    e,
                )
                try:
                    replacement_message = await _send_contest_post(
                        bot,
                        contest,
                        text,
                        keyboard,
                        contest.channel_id,
                    )
                    old_message_id = contest.message_id
                    contest.message_id = replacement_message.message_id
                    await db.commit()

                    if old_message_id and old_message_id != replacement_message.message_id:
                        try:
                            await bot.delete_message(chat_id=contest.channel_id, message_id=old_message_id)
                        except Exception as delete_error:
                            logger.warning(
                                "Не удалось удалить старый пост конкурса %s (%s): %s",
                                contest_id,
                                old_message_id,
                                delete_error,
                            )

                    logger.info("Пост конкурса %s заменен новым сообщением %s", contest_id, replacement_message.message_id)
                    return True
                except Exception as replacement_error:
                    logger.error(
                        "Ошибка замены поста конкурса %s новым сообщением: %s",
                        contest_id,
                        replacement_error,
                        exc_info=True,
                    )
                    return False

            logger.error("Ошибка обновления поста конкурса %s: %s", contest_id, e, exc_info=True)
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

        if contest.status.value == "results_published" and contest.results_message_id:
            logger.info(
                "Результаты конкурса %s уже опубликованы (message_id=%s), повторная публикация пропущена",
                contest_id,
                contest.results_message_id,
            )
            return True
        
        # Получаем username бота для создания startapp ссылки
        bot_info = await bot.get_me()
        bot_username = bot_info.username
        if not bot_username:
            logger.error("Не удалось получить username бота для публикации результатов конкурса %s", contest_id)
            return False
        
        # Формируем сообщение с startapp ссылкой для открытия WebApp
        text, keyboard = format_results_message(contest, bot_username)
        
        try:
            message = await bot.send_message(
                chat_id=contest.channel_id,
                message_thread_id=contest.message_thread_id,
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
            logger.error("Ошибка публикации результатов конкурса %s: %s", contest_id, e, exc_info=True)
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
    language = normalize_language(getattr(contest, "language", None))
    
    for prize in winners:
        if prize.winner_user_id:
            # Проверяем, писал ли пользователь боту
            has_started = await telegram_service.has_user_started_bot(prize.winner_user_id)
            
            if has_started:
                emoji = "🥇" if prize.place == 1 else "🥈" if prize.place == 2 else "🥉" if prize.place == 3 else "🏆"
                message = (
                    f"🎉 {translate(language, 'winner_notification', place=prize.place, title=contest.title)}\n\n"
                    f"{emoji} <b>{translate(language, 'your_prize')}:</b> {prize.title}\n"
                )
                if prize.description:
                    message += f"{prize.description}\n"
                
                await telegram_service.send_message_to_user(
                    prize.winner_user_id,
                    message,
                    parse_mode="HTML"
                )
