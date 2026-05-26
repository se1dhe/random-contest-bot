"""
Оплата подписки владельца через Telegram Stars.
"""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import LabeledPrice, Message, PreCheckoutQuery
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


@router.message(Command("subscribe"))
async def cmd_subscribe(message: Message):
    if not is_private_chat(message):
        return

    plan_code = parse_plan_arg(message)
    plan = get_subscription_plan(plan_code)
    async with AsyncSessionLocal() as db:
        payment = await create_subscription_payment(
            db,
            user_id=message.from_user.id,
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


@router.message(Command("paykassa"))
async def cmd_paykassa(message: Message):
    if not is_private_chat(message):
        return

    plan_code = parse_plan_arg(message)
    async with AsyncSessionLocal() as db:
        payment = await create_subscription_payment(
            db,
            user_id=message.from_user.id,
            provider="paykassa",
            plan_code=plan_code,
        )
    try:
        checkout_url = await create_paykassa_checkout_url(payment)
    except Exception as exc:
        logger.warning("PayKassa checkout failed for user_id=%s: %s", message.from_user.id, exc)
        checkout_url = None
    if not checkout_url:
        await message.answer(
            "PayKassa сейчас не настроена. Используй оплату Telegram Stars: /subscribe\n\n"
            f"Планы:\n{format_plan_list()}"
        )
        return
    await message.answer(
        "💳 Оплата подписки через PayKassa:\n"
        f"{checkout_url}\n\n"
        "После подтверждения платежа доступ к панели владельца активируется автоматически."
    )


@router.message(Command("subscription"))
async def cmd_subscription(message: Message):
    if not is_private_chat(message):
        return

    async with AsyncSessionLocal() as db:
        status = await get_subscription_status(db, message.from_user.id)

    if not status["active"]:
        await message.answer(
            "Подписка не активна.\n\n"
            "Оформи доступ через Telegram Stars: /subscribe\n"
            "PayKassa будет доступна после настройки мерчанта: /paykassa"
        )
        return

    limits = status["plan"]["limits"]
    usage = status["usage"]
    ends_at = status["subscription"]["ends_at"] if status.get("subscription") else None
    await message.answer(
        "✅ <b>Подписка активна</b>\n\n"
        f"План: {status['plan']['title']}\n"
        f"Действует до: {ends_at or 'без ограничения'}\n\n"
        f"Telegram каналы: {usage['channels']}/{limits['max_channels']}\n"
        f"Активные конкурсы: {usage['active_contests']}/{limits['max_active_contests']}\n"
        f"Черновики: {usage['draft_contests']}/{limits['max_draft_contests']}\n"
        f"YouTube/TikTok/Instagram: до {limits['max_external_channels_per_platform']} на платформу"
    )


@router.message(Command("plans"))
async def cmd_plans(message: Message):
    if not is_private_chat(message):
        return
    await message.answer(
        "Планы подписки:\n\n"
        f"{format_plan_list()}\n\n"
        "Оплата Stars: /subscribe pro\n"
        "Оплата PayKassa: /paykassa pro"
    )


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
