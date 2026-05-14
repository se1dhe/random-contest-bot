"""
API оплаты подписки владельца.
"""
import hashlib
import hmac
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from database.db import get_db
from shared.services.subscription_service import (
    activate_payment_by_external_id,
    build_paykassa_checkout_url,
    create_subscription_payment,
    get_subscription_plan,
)
from web.services.telegram_auth import verify_telegram_webapp_initdata

router = APIRouter(prefix="/api/billing", tags=["billing"])


PAYKASSA_SUCCESS_STATUSES = {"success", "paid", "completed", "confirmed", "yes", "1", "true"}


def normalize_paykassa_amount(value) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(round(float(str(value).replace(",", ".")) * 100))
    except (TypeError, ValueError):
        return None


def verify_paykassa_signature(request: Request, payload: dict) -> None:
    """
    Optional shared-secret guard for PayKassa webhooks.
    When PAYKASSA_WEBHOOK_SECRET is set, the webhook must include a matching HMAC-SHA256
    in X-Paykassa-Signature, X-Signature, or signature/sign field.
    """
    secret = os.getenv("PAYKASSA_WEBHOOK_SECRET", "").strip()
    if not secret:
        return

    received = (
        request.headers.get("X-Paykassa-Signature")
        or request.headers.get("X-Signature")
        or payload.get("signature")
        or payload.get("sign")
        or ""
    )
    if not received:
        raise HTTPException(status_code=403, detail="Missing webhook signature")

    order_id = str(payload.get("order_id") or payload.get("external_charge_id") or "")
    amount = str(payload.get("amount") or "")
    currency = str(payload.get("currency") or "")
    status = str(payload.get("status") or payload.get("payment_status") or "")
    signed_payload = f"{order_id}:{amount}:{currency}:{status}".encode("utf-8")
    expected = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected.lower(), str(received).lower()):
        raise HTTPException(status_code=403, detail="Invalid webhook signature")


def resolve_user_id(user_id: Optional[int], init_data: Optional[str]) -> int:
    if init_data:
        auth_data = verify_telegram_webapp_initdata(init_data)
        if not auth_data:
            raise HTTPException(status_code=403, detail="Невалидные данные авторизации")
        telegram_id = auth_data.get("user", {}).get("id")
        if telegram_id:
            return int(telegram_id)
    if user_id:
        return int(user_id)
    raise HTTPException(status_code=403, detail="Telegram user не найден")


@router.get("/plans")
async def plans():
    plan = get_subscription_plan()
    return [
        {
            "code": "contest_month",
            "title": plan["title"],
            "description": plan["description"],
            "duration_days": plan["duration_days"],
            "telegram_stars": plan["stars"],
            "fiat_cents": plan["fiat_cents"],
        }
    ]


@router.post("/paykassa/create")
async def create_paykassa_checkout(
    user_id: Optional[int] = Query(None),
    _auth: Optional[str] = Query(None, alias="_auth"),
    db: AsyncSession = Depends(get_db),
):
    telegram_user_id = resolve_user_id(user_id, _auth)
    payment = await create_subscription_payment(
        db,
        user_id=telegram_user_id,
        provider="paykassa",
    )
    checkout_url = build_paykassa_checkout_url(payment)
    if not checkout_url:
        raise HTTPException(status_code=503, detail="PAYKASSA_CHECKOUT_URL не настроен")
    return {
        "payment_id": payment.id,
        "external_charge_id": payment.external_charge_id,
        "checkout_url": checkout_url,
    }


@router.post("/paykassa/webhook")
async def paykassa_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        payload = await request.json()
    else:
        form = await request.form()
        payload = dict(form)

    external_charge_id = payload.get("order_id") or payload.get("external_charge_id")
    if not external_charge_id:
        raise HTTPException(status_code=400, detail="Missing order_id")

    verify_paykassa_signature(request, payload)

    status = str(payload.get("status") or payload.get("payment_status") or "").strip().lower()
    if status and status not in PAYKASSA_SUCCESS_STATUSES:
        raise HTTPException(status_code=400, detail="Payment is not successful")

    expected_amount = normalize_paykassa_amount(payload.get("amount"))
    expected_currency = str(payload.get("currency") or "USD").upper()

    subscription = await activate_payment_by_external_id(
        db,
        str(external_charge_id),
        provider="paykassa",
        expected_amount=expected_amount,
        expected_currency=expected_currency,
    )
    if not subscription:
        raise HTTPException(status_code=404, detail="Payment not found")
    return {"ok": True}
