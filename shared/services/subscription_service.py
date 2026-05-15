"""
Сервис подписок владельцев.
"""
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    Channel,
    Contest,
    ContestStatus,
    InstagramChannel,
    OwnerSubscription,
    OwnerSubscriptionStatus,
    SubscriptionPayment,
    SubscriptionPaymentStatus,
    TikTokChannel,
    YoutubeChannel,
)


DEFAULT_PLANS = {
    "contest_month": {
        "title": "TelOnyx Contest Pro",
        "description": "30 дней доступа к созданию и управлению конкурсами",
        "duration_days": 30,
        "stars": int(os.getenv("SUBSCRIPTION_STARS_PRICE", "299")),
        "fiat_cents": int(os.getenv("SUBSCRIPTION_FIAT_CENTS", "500")),
        "limits": {
            "max_channels": int(os.getenv("SUBSCRIPTION_MAX_CHANNELS", "5")),
            "max_active_contests": int(os.getenv("SUBSCRIPTION_MAX_ACTIVE_CONTESTS", "10")),
            "max_draft_contests": int(os.getenv("SUBSCRIPTION_MAX_DRAFT_CONTESTS", "50")),
            "max_external_channels_per_platform": int(os.getenv("SUBSCRIPTION_MAX_EXTERNAL_CHANNELS", "10")),
            "max_sponsors_per_contest": int(os.getenv("SUBSCRIPTION_MAX_SPONSORS", "10")),
            "max_prizes_per_contest": int(os.getenv("SUBSCRIPTION_MAX_PRIZES", "20")),
            "max_image_mb": int(os.getenv("SUBSCRIPTION_MAX_IMAGE_MB", "5")),
        },
    }
}


def get_subscription_plan(plan_code: str = "contest_month") -> dict:
    return DEFAULT_PLANS.get(plan_code, DEFAULT_PLANS["contest_month"])


async def has_active_subscription(db: AsyncSession, user_id: int) -> bool:
    return await get_active_subscription(db, user_id) is not None


async def get_active_subscription(db: AsyncSession, user_id: int) -> Optional[OwnerSubscription]:
    now = datetime.utcnow()
    result = await db.execute(
        select(OwnerSubscription)
        .where(
            OwnerSubscription.user_id == int(user_id),
            OwnerSubscription.status == OwnerSubscriptionStatus.ACTIVE,
            (OwnerSubscription.ends_at.is_(None)) | (OwnerSubscription.ends_at > now),
        )
        .order_by(OwnerSubscription.ends_at.desc().nulls_first(), OwnerSubscription.created_at.desc())
    )
    return result.scalars().first()


async def get_owner_usage(db: AsyncSession, user_id: int) -> dict:
    owner_id = int(user_id)

    async def count(query) -> int:
        result = await db.execute(query)
        return int(result.scalar() or 0)

    return {
        "channels": await count(
            select(func.count(Channel.id)).where(
                Channel.owner_user_id == owner_id,
                Channel.is_active == True,
            )
        ),
        "active_contests": await count(
            select(func.count(Contest.id)).where(
                Contest.owner_user_id == owner_id,
                Contest.status == ContestStatus.ACTIVE,
            )
        ),
        "draft_contests": await count(
            select(func.count(Contest.id)).where(
                Contest.owner_user_id == owner_id,
                Contest.status == ContestStatus.DRAFT,
            )
        ),
        "youtube_channels": await count(
            select(func.count(YoutubeChannel.id)).where(YoutubeChannel.owner_user_id == owner_id)
        ),
        "tiktok_channels": await count(
            select(func.count(TikTokChannel.id)).where(TikTokChannel.owner_user_id == owner_id)
        ),
        "instagram_channels": await count(
            select(func.count(InstagramChannel.id)).where(InstagramChannel.owner_user_id == owner_id)
        ),
    }


async def get_subscription_status(db: AsyncSession, user_id: int) -> dict:
    subscription = await get_active_subscription(db, user_id)
    plan_code = subscription.plan_code if subscription else "contest_month"
    plan = get_subscription_plan(plan_code)
    usage = await get_owner_usage(db, user_id)
    return {
        "active": subscription is not None,
        "subscription": {
            "id": subscription.id,
            "plan_code": subscription.plan_code,
            "provider": subscription.provider,
            "starts_at": subscription.starts_at.isoformat() if subscription.starts_at else None,
            "ends_at": subscription.ends_at.isoformat() if subscription.ends_at else None,
        } if subscription else None,
        "plan": {
            "code": plan_code,
            "title": plan["title"],
            "description": plan["description"],
            "duration_days": plan["duration_days"],
            "telegram_stars": plan["stars"],
            "fiat_cents": plan["fiat_cents"],
            "limits": plan["limits"],
        },
        "usage": usage,
    }


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
    active_subscription = await get_active_subscription(db, user_id)
    starts_at = now
    base_ends_at = active_subscription.ends_at if active_subscription and active_subscription.ends_at else now
    if base_ends_at < now:
        base_ends_at = now
    subscription = OwnerSubscription(
        user_id=int(user_id),
        provider=provider,
        plan_code=plan_code,
        status=OwnerSubscriptionStatus.ACTIVE,
        starts_at=starts_at,
        ends_at=base_ends_at + timedelta(days=plan["duration_days"]),
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
