"""
Обработчики команд администратора
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.filters.command import CommandObject
from shared.config import config
from shared.i18n import normalize_language, translate
import os

logger = logging.getLogger(__name__)

router = Router()


def is_private_chat(message: Message) -> bool:
    return getattr(message.chat, "type", None) == "private"


async def has_owner_access(user_id: int) -> bool:
    return config.is_admin(user_id)


def build_owner_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🔧 Открыть админ-панель",
            web_app={"url": get_admin_webapp_url()}
        )]
    ])


def get_admin_webapp_url() -> str:
    """
    Получить URL админ-панели
    
    @return URL админ-панели
    """
    return (os.getenv("WEBAPP_URL") or config.webapp_url).rstrip("/") + "/admin"


def get_webapp_url(path: str) -> str:
    """Build an absolute WebApp URL."""
    base_url = os.getenv("WEBAPP_URL") or config.webapp_url
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


async def get_contest_language(contest_id: int) -> str:
    from bot.services.contest_service import ContestService
    from database.db import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        contest = await ContestService(db).get_contest_by_id(contest_id)
        return normalize_language(contest.language if contest else None)


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    """
    Обработчик команды /start с поддержкой deep links
    
    @param message сообщение от пользователя
    @param command объект команды с аргументами
    """
    logger.info(f"Получена команда /start от пользователя {message.from_user.id}")
    if not is_private_chat(message):
        return

    args = command.args  # Получаем аргументы после /start
    
    # Обработка startapp для регистрации в конкурсе (используется из каналов)
    # Формат: /start contest_1 или /startapp contest_1
    if args and args.startswith("contest_"):
        try:
            contest_id = int(args.split("_")[1])
            language = await get_contest_language(contest_id)
            register_url = get_webapp_url(f"register?contest_id={contest_id}")
            
            # Отправляем URL кнопку в личный чат
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"🎯 {translate(language, 'register_in_contest')}",
                    web_app={"url": register_url}
                )]
            ])
            
            await message.answer(
                f"🎉 <b>{translate(language, 'registration_title')}</b>\n\n"
                f"{translate(language, 'registration_hint')}",
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
            language = await get_contest_language(contest_id)
            results_url = get_webapp_url(f"results/{contest_id}")
            
            # Отправляем URL кнопку в личный чат
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"📊 {translate(language, 'view_results')}",
                    web_app={"url": results_url}
                )]
            ])
            
            await message.answer(
                f"🏆 <b>{translate(language, 'results_generic')}</b>\n\n"
                f"{translate(language, 'results_hint')}",
                reply_markup=keyboard
            )
            return
        except (ValueError, IndexError):
            # Неверный формат аргументов
            pass
    
    
    # Обычный /start без аргументов
    try:
        if await has_owner_access(message.from_user.id):
            logger.info(f"Обработка /start для владельца {message.from_user.id}")
            await message.answer(
                "👋 <b>TelOnyx Contest Bot</b>\n\n"
                "Этот экземпляр настроен для твоих каналов. Открой панель владельца, чтобы управлять конкурсами.",
                reply_markup=build_owner_keyboard()
            )
        else:
            logger.info(f"Обработка /start для обычного пользователя {message.from_user.id}")
            await message.answer(
                "👋 <b>TelOnyx Contest Bot</b>\n\n"
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
    if not is_private_chat(message):
        return

    if not await has_owner_access(message.from_user.id):
        await message.answer("❌ Доступ к панели владельца разрешен только администратору этого экземпляра бота.")
        return
    
    await message.answer(
        "🔧 <b>Панель владельца</b>\n\n"
        "Нажми кнопку ниже, чтобы открыть управление конкурсами.",
        reply_markup=build_owner_keyboard()
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """
    Обработчик команды /help
    
    @param message сообщение от пользователя
    """
    if not is_private_chat(message):
        return

    if await has_owner_access(message.from_user.id):
        help_text = (
            "📋 <b>Команды владельца:</b>\n\n"
            "/start - Начать работу с ботом\n"
            "/admin - Открыть панель владельца\n"
            "/help - Показать это сообщение\n\n"
            "Для управления конкурсами используй команду /admin."
        )
    else:
        help_text = (
            "📋 <b>Информация:</b>\n\n"
            "Для участия перейди в канал с конкурсом и нажми кнопку регистрации."
        )
    
    await message.answer(help_text)
