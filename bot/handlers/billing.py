"""
Оплата подписки владельца через Telegram Stars.
"""
import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import LabeledPrice, Message, PreCheckoutQuery

from database.db import AsyncSessionLocal
from shared.services.subscription_service import (
    activate_subscription,
    create_subscription_payment,
    get_subscription_plan,
)

logger = logging.getLogger(__name__)
router = Router()


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
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def process_successful_payment(message: Message):
    payment = message.successful_payment
    payload = payment.invoice_payload if payment else ""
    parts = payload.split(":")
    if len(parts) != 3 or parts[0] != "subscription":
        logger.warning("Unsupported successful payment payload: %s", payload)
        await message.answer("Оплата получена, но подписка требует ручной проверки. Напиши в поддержку TelOnyx.")
        return

    external_charge_id = parts[1]
    plan_code = parts[2]
    async with AsyncSessionLocal() as db:
        await activate_subscription(
            db,
            user_id=message.from_user.id,
            provider="telegram_stars",
            plan_code=plan_code,
            external_charge_id=external_charge_id,
        )

    await message.answer("✅ Подписка активирована. Теперь доступна админ-панель: /admin")
