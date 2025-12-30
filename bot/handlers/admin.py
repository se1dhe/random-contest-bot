"""
Обработчики команд администратора
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.filters.command import CommandObject
from shared.config import config
import os

logger = logging.getLogger(__name__)

router = Router()


def get_admin_webapp_url() -> str:
    """
    Получить URL админ-панели
    
    @return URL админ-панели
    """
    if config.ngrok_enabled and config.ngrok_domain:
        return f"https://{config.ngrok_domain}/admin"
    return os.getenv("WEBAPP_URL", "http://localhost:8000") + "/admin"


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    """
    Обработчик команды /start с поддержкой deep links
    
    @param message сообщение от пользователя
    @param command объект команды с аргументами
    """
    logger.info(f"Получена команда /start от пользователя {message.from_user.id}")
    args = command.args  # Получаем аргументы после /start
    
    # Обработка startapp для регистрации в конкурсе (используется из каналов)
    # Формат: /start contest_1 или /startapp contest_1
    if args and args.startswith("contest_"):
        try:
            contest_id = int(args.split("_")[1])
            bot_info = await message.bot.get_me()
            bot_username = bot_info.username
            
            # Используем startapp для открытия WebApp напрямую
            register_url = f"https://t.me/{bot_username}?startapp=contest_{contest_id}"
            
            # Отправляем URL кнопку в личный чат
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="🎯 Зарегистрироваться в конкурсе",
                    url=register_url
                )]
            ])
            
            await message.answer(
                "🎉 <b>Регистрация в конкурсе</b>\n\n"
                "Нажмите кнопку ниже, чтобы открыть форму регистрации:",
                reply_markup=keyboard
            )
            return
        except (ValueError, IndexError):
            # Неверный формат аргументов
            pass
    
    # Обработка startapp для просмотра результатов (используется из каналов)
    # Формат: /start results_1 или /startapp results_1
    if args and args.startswith("results_"):
        try:
            contest_id = int(args.split("_")[1])
            bot_info = await message.bot.get_me()
            bot_username = bot_info.username
            
            # Используем startapp для открытия WebApp напрямую
            results_url = f"https://t.me/{bot_username}?startapp=results_{contest_id}"
            
            # Отправляем URL кнопку в личный чат
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="📊 Посмотреть результаты",
                    url=results_url
                )]
            ])
            
            await message.answer(
                "🏆 <b>Результаты конкурса</b>\n\n"
                "Нажмите кнопку ниже, чтобы посмотреть результаты:",
                reply_markup=keyboard
            )
            return
        except (ValueError, IndexError):
            # Неверный формат аргументов
            pass
    
    
    # Обычный /start без аргументов
    try:
        if message.from_user.id == config.admin_id:
            logger.info(f"Обработка /start для администратора {message.from_user.id}")
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="🔧 Открыть админ-панель",
                    web_app={"url": get_admin_webapp_url()}
                )]
            ])
            await message.answer(
                "👋 Привет, администратор!\n\n"
                "Используй админ-панель для управления конкурсами.",
                reply_markup=keyboard
            )
        else:
            logger.info(f"Обработка /start для обычного пользователя {message.from_user.id}")
            await message.answer(
                "👋 Привет!\n\n"
                "Этот бот предназначен для участия в конкурсах через каналы.\n"
                "Для участия перейди в канал с конкурсом и нажми кнопку регистрации."
            )
        logger.info(f"Ответ на /start успешно отправлен пользователю {message.from_user.id}")
    except Exception as e:
        logger.error(f"Ошибка при обработке /start: {e}", exc_info=True)
        try:
            await message.answer("❌ Произошла ошибка при обработке команды. Попробуйте позже.")
        except:
            pass


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """
    Обработчик команды /admin
    
    @param message сообщение от пользователя
    """
    if message.from_user.id != config.admin_id:
        await message.answer("❌ У вас нет доступа к админ-панели.")
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🔧 Открыть админ-панель",
            web_app={"url": get_admin_webapp_url()}
        )]
    ])
    
    await message.answer(
        "🔧 <b>Админ-панель</b>\n\n"
        "Нажмите кнопку ниже, чтобы открыть админ-панель для управления конкурсами.",
        reply_markup=keyboard
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """
    Обработчик команды /help
    
    @param message сообщение от пользователя
    """
    if message.from_user.id == config.admin_id:
        help_text = (
            "📋 <b>Команды администратора:</b>\n\n"
            "/start - Начать работу с ботом\n"
            "/admin - Открыть админ-панель\n"
            "/help - Показать это сообщение\n\n"
            "Для управления конкурсами используй команду /admin."
        )
    else:
        help_text = (
            "📋 <b>Информация:</b>\n\n"
            "Этот бот предназначен для участия в конкурсах.\n"
            "Для участия перейди в канал с конкурсом и нажми кнопку регистрации."
        )
    
    await message.answer(help_text)

