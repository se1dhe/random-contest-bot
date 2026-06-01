"""
Модель платежа за вход в конкретный конкурс.
"""
import enum

from sqlalchemy import BigInteger, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .base import BaseModel


class ContestEntryPaymentStatus(enum.Enum):
    """Статус платежа за регистрацию в конкурсе."""

    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ContestEntryPayment(BaseModel):
    """Telegram Stars платеж участника за вход в конкурс."""

    __tablename__ = "contest_entry_payments"

    contest_id = Column(Integer, ForeignKey("contests.id"), nullable=False, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    amount_stars = Column(Integer, nullable=False)
    status = Column(Enum(ContestEntryPaymentStatus), default=ContestEntryPaymentStatus.PENDING, nullable=False, index=True)
    invoice_payload = Column(String(255), nullable=False, unique=True, index=True)
    telegram_payment_charge_id = Column(String(255), nullable=True, unique=True, index=True)
    provider_payment_charge_id = Column(String(255), nullable=True)
    paid_at = Column(DateTime, nullable=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    invoice_link = Column(Text, nullable=True)

    contest = relationship("Contest")
