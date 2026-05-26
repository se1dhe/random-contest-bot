"""
Оплата подписки владельца через Telegram Stars.
"""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, Message, PreCheckoutQuery
from sqlalchemy import select

from database.db import AsyncSessionLocal
from database.models import SubscriptionPayment, SubscriptionPaymentStatus
from shared.services.subscription_service import (
    activate_payment_by_external_id,
    create_paykassa_checkout_url,
    create_subscription_payment,
    get_subscription_plan,
    get_subscription_status,
    get_subscription_plan_code,
    list_subscription_plans,
)

logger = logging.getLogger(__name__)
router = Router()


def is_private_chat(message: Message) -> bool:
    return getattr(message.chat, "type", None) == "private"


def parse_subscription_payload(payload: str) -> tuple[str, str] | None:
    parts = payload.split(":")
    if len(parts) != 3 or parts[0] != "subscription":
        return None
    return parts[1], parts[2]


def parse_plan_arg(message: Message) -> str:
    parts = (message.text or "").split(maxsplit=1)
    return get_subscription_plan_code(parts[1] if len(parts) > 1 else "contest_pro")


def plan_short_code(plan_code: str) -> str:
    return get_subscription_plan_code(plan_code).replace("contest_", "")


def format_plan_list() -> str:
    lines = []
    for plan in list_subscription_plans():
        limits = plan["limits"]
        code = plan["code"].replace("contest_", "")
        lines.append(
            f"<b>{code}</b>: {plan['telegram_stars']} ⭐ / ${plan['fiat_cents'] / 100:.2f}, "
            f"каналов {limits['max_channels']}, активных конкурсов {limits['max_active_contests']}"
        )
    return "\n".join(lines)


def subscription_menu_text(is_owner: bool = False) -> str:
    intro = (
        "👋 <b>TelOnyx Contest Bot</b>\n\n"
        "Бот помогает владельцам каналов запускать конкурсы, публиковать посты, "
        "проверять подписки и автоматически выбирать победителей.\n\n"
    )
    if is_owner:
        return intro + "У тебя уже есть доступ. Открой панель владельца или проверь лимиты подписки."
    return intro + "Чтобы проводить конкурсы в своих каналах, посмотри тарифы и оформи подписку."


def build_subscription_menu_keyboard(include_admin: bool = False) -> InlineKeyboardMarkup:
    rows = []
    if include_admin:
        from bot.handlers.admin import get_admin_webapp_url

        rows.append([
            InlineKeyboardButton(text="Открыть админ-панель", web_app={"url": get_admin_webapp_url()})
        ])
    rows.extend([
        [InlineKeyboardButton(text="Тарифы и оплата", callback_data="billing:plans")],
        [InlineKeyboardButton(text="Моя подписка", callback_data="billing:status")],
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_plans_keyboard(prefix: str = "billing:stars") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"{plan_short_code(plan['code']).title()} · {plan['telegram_stars']} ⭐",
                callback_data=f"{prefix}:{plan['code']}",
            )
        ]
        for plan in list_subscription_plans()
    ] + [[InlineKeyboardButton(text="Назад", callback_data="billing:start")]])


def build_payment_method_keyboard(plan_code: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Telegram Stars", callback_data=f"billing:stars:{plan_code}"),
            InlineKeyboardButton(text="PayKassa", callback_data=f"billing:paykassa:{plan_code}"),
        ],
        [InlineKeyboardButton(text="Назад к тарифам", callback_data="billing:plans")],
    ])


async def send_stars_invoice(message: Message, user_id: int, plan_code: str) -> None:
    plan_code = get_subscription_plan_code(plan_code)
    plan = get_subscription_plan(plan_code)
    async with AsyncSessionLocal() as db:
        payment = await create_subscription_payment(
            db,
            user_id=user_id,
            provider="telegram_stars",
            plan_code=plan_code,
        )

    await message.answer_invoice(
        title=plan["title"],
        description=plan["description"],
        payload=f"subscription:{payment.external_charge_id}:{plan_code}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=plan["title"], amount=plan["stars"])],
    )


async def send_paykassa_checkout(message: Message, user_id: int, plan_code: str) -> None:
    plan_code = get_subscription_plan_code(plan_code)
    plan = get_subscription_plan(plan_code)
    async with AsyncSessionLocal() as db:
        payment = await create_subscription_payment(
            db,
            user_id=user_id,
            provider="paykassa",
            plan_code=plan_code,
        )
    try:
        checkout_url = await create_paykassa_checkout_url(payment)
    except Exception as exc:
        logger.warning("PayKassa checkout failed for user_id=%s: %s", user_id, exc)
        checkout_url = None
    if not checkout_url:
        await message.answer(
            "PayKassa сейчас не настроена.\n\n"
            "Можно оплатить через Telegram Stars или выбрать другой способ ниже.",
            reply_markup=build_payment_method_keyboard(plan_code),
        )
        return
    await message.answer(
        f"💳 <b>{plan['title']}</b>\n\n"
        "Нажми кнопку ниже, чтобы открыть счет PayKassa. После подтверждения платежа подписка активируется автоматически.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Открыть PayKassa", url=checkout_url)],
            [InlineKeyboardButton(text="Проверить подписку", callback_data="billing:status")],
        ]),
    )


def format_subscription_status_text(status: dict) -> str:
    if not status["active"]:
        return (
            "⏸ <b>Подписка не активна</b>\n\n"
            "Выбери тариф и способ оплаты. После оплаты бот откроет доступ к панели владельца."
        )

    limits = status["plan"]["limits"]
    usage = status["usage"]
    ends_at = status["subscription"]["ends_at"] if status.get("subscription") else None
    return (
        "✅ <b>Подписка активна</b>\n\n"
        f"План: {status['plan']['title']}\n"
        f"Действует до: {ends_at or 'без ограничения'}\n\n"
        f"Telegram каналы: {usage['channels']}/{limits['max_channels']}\n"
        f"Активные конкурсы: {usage['active_contests']}/{limits['max_active_contests']}\n"
        f"Черновики: {usage['draft_contests']}/{limits['max_draft_contests']}\n"
        f"YouTube/TikTok: до {limits['max_external_channels_per_platform']} на платформу"
    )


@router.message(Command("subscribe"))
async def cmd_subscribe(message: Message):
    if not is_private_chat(message):
        return

    plan_code = parse_plan_arg(message)
    await send_stars_invoice(message, message.from_user.id, plan_code)


@router.message(Command("paykassa"))
async def cmd_paykassa(message: Message):
    if not is_private_chat(message):
        return

    plan_code = parse_plan_arg(message)
    await send_paykassa_checkout(message, message.from_user.id, plan_code)


@router.message(Command("subscription"))
async def cmd_subscription(message: Message):
    if not is_private_chat(message):
        return

    async with AsyncSessionLocal() as db:
        status = await get_subscription_status(db, message.from_user.id)

    await message.answer(format_subscription_status_text(status), reply_markup=build_subscription_menu_keyboard(status["active"]))


@router.message(Command("plans"))
async def cmd_plans(message: Message):
    if not is_private_chat(message):
        return
    await message.answer(
        "Планы подписки:\n\n"
        f"{format_plan_list()}\n\n"
        "Выбери тариф:"
        ,
        reply_markup=build_plans_keyboard("billing:choose"),
    )


@router.callback_query(F.data == "billing:start")
async def cb_billing_start(query: CallbackQuery):
    async with AsyncSessionLocal() as db:
        status = await get_subscription_status(db, query.from_user.id)
    await query.message.edit_text(
        subscription_menu_text(status["active"]),
        reply_markup=build_subscription_menu_keyboard(status["active"]),
    )
    await query.answer()


@router.callback_query(F.data == "billing:plans")
async def cb_billing_plans(query: CallbackQuery):
    await query.message.edit_text(
        "📦 <b>Тарифы TelOnyx Contest</b>\n\n"
        f"{format_plan_list()}\n\n"
        "Выбери тариф, затем способ оплаты.",
        reply_markup=build_plans_keyboard("billing:choose"),
    )
    await query.answer()


@router.callback_query(F.data.startswith("billing:choose:"))
async def cb_choose_plan(query: CallbackQuery):
    plan_code = get_subscription_plan_code((query.data or "").split(":")[-1])
    plan = get_subscription_plan(plan_code)
    await query.message.edit_text(
        f"📦 <b>{plan['title']}</b>\n\n"
        f"{plan['description']}\n\n"
        f"Telegram Stars: {plan['stars']} ⭐\n"
        f"PayKassa: ${plan['fiat_cents'] / 100:.2f}\n\n"
        "Выбери способ оплаты.",
        reply_markup=build_payment_method_keyboard(plan_code),
    )
    await query.answer()


@router.callback_query(F.data.startswith("billing:stars:"))
async def cb_stars_invoice(query: CallbackQuery):
    plan_code = get_subscription_plan_code((query.data or "").split(":")[-1])
    await query.answer("Готовлю инвойс...")
    await send_stars_invoice(query.message, query.from_user.id, plan_code)


@router.callback_query(F.data.startswith("billing:paykassa:"))
async def cb_paykassa_checkout(query: CallbackQuery):
    plan_code = get_subscription_plan_code((query.data or "").split(":")[-1])
    await query.answer("Создаю счет...")
    await send_paykassa_checkout(query.message, query.from_user.id, plan_code)


@router.callback_query(F.data == "billing:status")
async def cb_subscription_status(query: CallbackQuery):
    async with AsyncSessionLocal() as db:
        status = await get_subscription_status(db, query.from_user.id)
    await query.message.edit_text(
        format_subscription_status_text(status),
        reply_markup=build_subscription_menu_keyboard(status["active"]),
    )
    await query.answer()


@router.pre_checkout_query()
async def process_pre_checkout(query: PreCheckoutQuery):
    parsed_payload = parse_subscription_payload(query.invoice_payload or "")
    if not parsed_payload:
        await query.answer(ok=False, error_message="Некорректный платеж подписки")
        return

    external_charge_id, plan_code = parsed_payload
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(SubscriptionPayment).where(
                SubscriptionPayment.external_charge_id == external_charge_id,
                SubscriptionPayment.provider == "telegram_stars",
            )
        )
        payment = result.scalar_one_or_none()

    if not payment:
        await query.answer(ok=False, error_message="Платеж не найден")
        return
    if payment.status == SubscriptionPaymentStatus.SUCCEEDED:
        await query.answer(ok=False, error_message="Платеж уже обработан")
        return
    if int(payment.user_id) != int(query.from_user.id):
        await query.answer(ok=False, error_message="Платеж создан другим пользователем")
        return
    if (
        payment.plan_code != plan_code
        or payment.currency != query.currency
        or int(payment.amount) != int(query.total_amount)
    ):
        await query.answer(ok=False, error_message="Параметры платежа изменились")
        return

    await query.answer(ok=True)


@router.message(F.successful_payment)
async def process_successful_payment(message: Message):
    if not is_private_chat(message):
        return

    payment = message.successful_payment
    payload = payment.invoice_payload if payment else ""
    parsed_payload = parse_subscription_payload(payload)
    if not parsed_payload:
        logger.warning("Unsupported successful payment payload: %s", payload)
        await message.answer("Оплата получена, но подписка требует ручной проверки. Напиши в поддержку TelOnyx.")
        return

    external_charge_id, _plan_code = parsed_payload
    async with AsyncSessionLocal() as db:
        subscription = await activate_payment_by_external_id(
            db,
            provider="telegram_stars",
            external_charge_id=external_charge_id,
            expected_amount=payment.total_amount,
            expected_currency=payment.currency,
        )

    if not subscription:
        logger.warning("Telegram Stars payment activation failed: %s", external_charge_id)
        await message.answer("Оплата получена, но подписка требует ручной проверки. Напиши в поддержку TelOnyx.")
        return

    await message.answer("✅ Подписка активирована. Теперь доступна админ-панель: /admin")
