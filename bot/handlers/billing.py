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
    create_subscription_payment,
    get_subscription_plan,
)

logger = logging.getLogger(__name__)
router = Router()


def parse_subscription_payload(payload: str) -> tuple[str, str] | None:
    parts = payload.split(":")
    if len(parts) != 3 or parts[0] != "subscription":
        return None
    return parts[1], parts[2]


@router.message(Command("subscribe"))
async def cmd_subscribe(message: Message):
    plan = get_subscription_plan()
    async with AsyncSessionLocal() as db:
        payment = await create_subscription_payment(
            db,
            user_id=message.from_user.id,
            provider="telegram_stars",
        )

    await message.answer_invoice(
        title=plan["title"],
        description=plan["description"],
        payload=f"subscription:{payment.external_charge_id}:contest_month",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=plan["title"], amount=plan["stars"])],
    )


@router.message(Command("paykassa"))
async def cmd_paykassa(message: Message):
    from shared.services.subscription_service import build_paykassa_checkout_url

    async with AsyncSessionLocal() as db:
        payment = await create_subscription_payment(
            db,
            user_id=message.from_user.id,
            provider="paykassa",
        )
    checkout_url = build_paykassa_checkout_url(payment)
    if not checkout_url:
        await message.answer("PayKassa сейчас не настроена. Используй оплату Telegram Stars: /subscribe")
        return
    await message.answer(
        "💳 Оплата подписки через PayKassa:\n"
        f"{checkout_url}\n\n"
        "После подтверждения платежа доступ к панели владельца активируется автоматически."
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
