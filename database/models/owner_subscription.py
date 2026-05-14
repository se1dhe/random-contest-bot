"""
Подписки владельцев каналов.
"""
import enum
from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Enum, Integer, String

from .base import BaseModel


class OwnerSubscriptionStatus(enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELED = "canceled"


class SubscriptionPaymentStatus(enum.Enum):
    CREATED = "created"
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


class OwnerSubscription(BaseModel):
    """Активная или историческая подписка владельца."""

    __tablename__ = "owner_subscriptions"

    user_id = Column(BigInteger, nullable=False, index=True)
    plan_code = Column(String(64), nullable=False)
    provider = Column(String(32), nullable=False)
    status = Column(Enum(OwnerSubscriptionStatus), default=OwnerSubscriptionStatus.ACTIVE, nullable=False, index=True)
    starts_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ends_at = Column(DateTime, nullable=True, index=True)
    external_charge_id = Column(String(255), nullable=True, index=True)


class SubscriptionPayment(BaseModel):
    """Платеж за подписку, в том числе Telegram Stars и PayKassa."""

    __tablename__ = "subscription_payments"

    user_id = Column(BigInteger, nullable=False, index=True)
    plan_code = Column(String(64), nullable=False)
    provider = Column(String(32), nullable=False, index=True)
    external_charge_id = Column(String(255), nullable=False, unique=True, index=True)
    currency = Column(String(16), nullable=False)
    amount = Column(Integer, nullable=False)
    status = Column(Enum(SubscriptionPaymentStatus), default=SubscriptionPaymentStatus.CREATED, nullable=False, index=True)
    paid_at = Column(DateTime, nullable=True)
