"""
Обработчики оплаты регистрации в конкурсе через Telegram Stars.
"""
import json
import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.types import Message, PreCheckoutQuery
from sqlalchemy import func, select

from bot.services.participant_service import ParticipantService
from database.db import AsyncSessionLocal
from database.models import ContestEntryPayment, ContestEntryPaymentStatus, Participant
from shared.services.redis_service import get_redis


router = Router()
logger = logging.getLogger(__name__)


def is_contest_entry_payload(payload: str | None) -> bool:
    return bool(payload and payload.startswith("contest_entry:"))


@router.pre_checkout_query()
async def pre_checkout_contest_entry(query: PreCheckoutQuery):
    if not is_contest_entry_payload(query.invoice_payload):
        return
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ContestEntryPayment).where(ContestEntryPayment.invoice_payload == query.invoice_payload)
        )
        entry_payment = result.scalar_one_or_none()
        if (
            not entry_payment
            or entry_payment.status != ContestEntryPaymentStatus.PENDING
            or query.currency != "XTR"
            or int(query.total_amount) != int(entry_payment.amount_stars)
        ):
            await query.answer(ok=False, error_message="Счет на регистрацию уже недействителен.")
            return
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_contest_entry_payment(message: Message):
    payment = message.successful_payment
    if not payment or not is_contest_entry_payload(payment.invoice_payload):
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ContestEntryPayment).where(ContestEntryPayment.invoice_payload == payment.invoice_payload)
        )
        entry_payment = result.scalar_one_or_none()
        if not entry_payment:
            logger.warning("Contest entry payment payload not found: %s", payment.invoice_payload)
            await message.answer("Оплата получена, но заявка на регистрацию не найдена. Напишите администратору.")
            return

        if payment.currency != "XTR" or int(payment.total_amount) != int(entry_payment.amount_stars):
            entry_payment.status = ContestEntryPaymentStatus.FAILED
            await db.commit()
            logger.warning(
                "Contest entry payment amount mismatch: payload=%s expected=%s got=%s %s",
                payment.invoice_payload,
                entry_payment.amount_stars,
                payment.total_amount,
                payment.currency,
            )
            await message.answer("Оплата получена с некорректной суммой. Напишите администратору.")
            return

        if entry_payment.status != ContestEntryPaymentStatus.SUCCEEDED:
            entry_payment.status = ContestEntryPaymentStatus.SUCCEEDED
            entry_payment.telegram_payment_charge_id = payment.telegram_payment_charge_id
            entry_payment.provider_payment_charge_id = payment.provider_payment_charge_id
            entry_payment.paid_at = datetime.utcnow()

        participant = await ParticipantService(db).register_participant(
            contest_id=entry_payment.contest_id,
            user_id=entry_payment.user_id,
            username=entry_payment.username,
            first_name=entry_payment.first_name,
            last_name=entry_payment.last_name,
        )
        await db.commit()

        if participant:
            try:
                redis = await get_redis()
                count_result = await db.execute(
                    select(func.count(Participant.id)).where(Participant.contest_id == entry_payment.contest_id)
                )
                await redis.publish("contest_updates", json.dumps({
                    "type": "new_registration",
                    "contest_id": entry_payment.contest_id,
                    "participants_count": int(count_result.scalar() or participant.registration_number),
                }))
            except Exception as exc:
                logger.warning("Failed to publish paid registration update: %s", exc)
            await message.answer(
                "✅ Оплата получена. Вы зарегистрированы в конкурсе "
                f"под номером {participant.registration_number}."
            )
        else:
            await message.answer("✅ Оплата получена. Вы уже зарегистрированы в этом конкурсе.")
