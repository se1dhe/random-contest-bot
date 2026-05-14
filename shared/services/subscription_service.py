"""
Сервис подписок владельцев.
"""
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    OwnerSubscription,
    OwnerSubscriptionStatus,
    SubscriptionPayment,
    SubscriptionPaymentStatus,
)


DEFAULT_PLANS = {
    "contest_month": {
        "title": "TelOnyx Contest Pro",
        "description": "30 дней доступа к созданию и управлению конкурсами",
        "duration_days": 30,
        "stars": int(os.getenv("SUBSCRIPTION_STARS_PRICE", "299")),
        "fiat_cents": int(os.getenv("SUBSCRIPTION_FIAT_CENTS", "500")),
    }
}


def get_subscription_plan(plan_code: str = "contest_month") -> dict:
    return DEFAULT_PLANS.get(plan_code, DEFAULT_PLANS["contest_month"])


async def has_active_subscription(db: AsyncSession, user_id: int) -> bool:
    now = datetime.utcnow()
    result = await db.execute(
        select(OwnerSubscription).where(
            OwnerSubscription.user_id == int(user_id),
            OwnerSubscription.status == OwnerSubscriptionStatus.ACTIVE,
            (OwnerSubscription.ends_at.is_(None)) | (OwnerSubscription.ends_at > now),
        )
    )
    return result.scalar_one_or_none() is not None


async def create_subscription_payment(
    db: AsyncSession,
    user_id: int,
    provider: str,
    plan_code: str = "contest_month",
    external_charge_id: Optional[str] = None,
) -> SubscriptionPayment:
    plan = get_subscription_plan(plan_code)
    payment = SubscriptionPayment(
        user_id=int(user_id),
        provider=provider,
        plan_code=plan_code,
        external_charge_id=external_charge_id or str(uuid.uuid4()),
        currency="XTR" if provider == "telegram_stars" else "USD",
        amount=plan["stars"] if provider == "telegram_stars" else plan["fiat_cents"],
        status=SubscriptionPaymentStatus.PENDING,
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return payment


async def activate_subscription(
    db: AsyncSession,
    user_id: int,
    provider: str,
    plan_code: str = "contest_month",
    external_charge_id: Optional[str] = None,
) -> OwnerSubscription:
    plan = get_subscription_plan(plan_code)
    now = datetime.utcnow()
    subscription = OwnerSubscription(
        user_id=int(user_id),
        provider=provider,
        plan_code=plan_code,
        status=OwnerSubscriptionStatus.ACTIVE,
        starts_at=now,
        ends_at=now + timedelta(days=plan["duration_days"]),
        external_charge_id=external_charge_id,
    )
    db.add(subscription)
    if external_charge_id:
        payment_result = await db.execute(
            select(SubscriptionPayment).where(SubscriptionPayment.external_charge_id == external_charge_id)
        )
        payment = payment_result.scalar_one_or_none()
        if payment:
            payment.status = SubscriptionPaymentStatus.SUCCEEDED
            payment.paid_at = now
    await db.commit()
    await db.refresh(subscription)
    return subscription


async def activate_payment_by_external_id(
    db: AsyncSession,
    external_charge_id: str,
    provider: str = "paykassa",
    expected_amount: Optional[int] = None,
    expected_currency: Optional[str] = None,
) -> Optional[OwnerSubscription]:
    result = await db.execute(
        select(SubscriptionPayment).where(
            SubscriptionPayment.external_charge_id == external_charge_id,
            SubscriptionPayment.provider == provider,
        )
    )
    payment = result.scalar_one_or_none()
    if not payment:
        return None
    if expected_amount is not None and int(payment.amount) != int(expected_amount):
        return None
    if expected_currency is not None and payment.currency.upper() != expected_currency.upper():
        return None
    if payment.status == SubscriptionPaymentStatus.SUCCEEDED:
        active_result = await db.execute(
            select(OwnerSubscription).where(
                OwnerSubscription.external_charge_id == external_charge_id,
                OwnerSubscription.provider == provider,
                OwnerSubscription.status == OwnerSubscriptionStatus.ACTIVE,
            )
        )
        return active_result.scalar_one_or_none()
    return await activate_subscription(
        db,
        user_id=payment.user_id,
        provider=provider,
        plan_code=payment.plan_code,
        external_charge_id=external_charge_id,
    )


def build_paykassa_checkout_url(payment: SubscriptionPayment) -> Optional[str]:
    base_url = os.getenv("PAYKASSA_CHECKOUT_URL", "").strip()
    if not base_url:
        return None
    separator = "&" if "?" in base_url else "?"
    return (
        f"{base_url}{separator}"
        f"order_id={payment.external_charge_id}&amount={payment.amount / 100:.2f}&currency=USD"
    )
