"""
API оплаты подписки владельца.
"""
import hashlib
import hmac
import os
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database.db import get_db
from shared.config import config
from shared.services.subscription_service import (
    activate_payment_by_external_id,
    confirm_paykassa_private_hash,
    create_subscription_payment,
    create_paykassa_checkout_url,
    get_subscription_status,
    list_subscription_plans,
)
from web.api.deps import verify_telegram_user

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
        if os.getenv("PAYKASSA_REQUIRE_WEBHOOK_SECRET", "true").lower() in {"1", "true", "yes"}:
            raise HTTPException(status_code=503, detail="PAYKASSA_WEBHOOK_SECRET не настроен")
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


@router.get("/plans")
async def plans():
    return list_subscription_plans()


@router.get("/status")
async def subscription_status(
    telegram_user_id: int = Depends(verify_telegram_user),
    db: AsyncSession = Depends(get_db),
):
    status = await get_subscription_status(db, telegram_user_id)
    status["is_super_admin"] = config.is_admin(telegram_user_id)
    if status["is_super_admin"]:
        status["active"] = True
    return status


@router.post("/paykassa/create")
async def create_paykassa_checkout(
    plan_code: str = Query("contest_pro"),
    telegram_user_id: int = Depends(verify_telegram_user),
    db: AsyncSession = Depends(get_db),
):
    payment = await create_subscription_payment(
        db,
        user_id=telegram_user_id,
        provider="paykassa",
        plan_code=plan_code,
    )
    try:
        checkout_url = await create_paykassa_checkout_url(payment)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"PayKassa недоступна: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=f"PayKassa отклонила счет: {exc}") from exc
    if not checkout_url:
        raise HTTPException(status_code=503, detail="PayKassa не настроена")
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

    private_hash = str(payload.get("private_hash") or "").strip()
    confirmed_payload = None
    if private_hash:
        try:
            confirmed_payload = await confirm_paykassa_private_hash(private_hash)
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"PayKassa confirm failed: {exc}") from exc
        if confirmed_payload:
            payload.update(confirmed_payload)

    external_charge_id = (
        payload.get("order_id")
        or payload.get("external_charge_id")
        or payload.get("shop_order_id")
        or payload.get("order")
    )
    if not external_charge_id:
        raise HTTPException(status_code=400, detail="Missing order_id")

    if not confirmed_payload:
        verify_paykassa_signature(request, payload)

    status = str(payload.get("status") or payload.get("payment_status") or "").strip().lower()
    if status and status not in PAYKASSA_SUCCESS_STATUSES:
        raise HTTPException(status_code=400, detail="Payment is not successful")

    expected_amount = normalize_paykassa_amount(
        payload.get("amount_shop")
        or payload.get("amount")
        or payload.get("amount_pay")
    )
    expected_currency = str(payload.get("currency") or payload.get("currency_shop") or "USD").upper()

    subscription = await activate_payment_by_external_id(
        db,
        str(external_charge_id),
        provider="paykassa",
        expected_amount=expected_amount,
        expected_currency=expected_currency,
    )
    if not subscription:
        raise HTTPException(status_code=404, detail="Payment not found")
    return PlainTextResponse(f"{external_charge_id}|success")
