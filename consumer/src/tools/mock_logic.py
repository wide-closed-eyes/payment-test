import asyncio
from random import random, uniform

import httpx

from src.database.database import async_session_fabric
from src.database.orm_client import OrmClient
from src.database.tables import Payment, PaymentStatus

GATEWAY_MIN_DELAY_SECONDS = 2
GATEWAY_MAX_DELAY_SECONDS = 5
GATEWAY_FAILURE_RATE = 0.1
WEBHOOK_TIMEOUT_SECONDS = 5


async def emulate_gateway() -> PaymentStatus:
    await asyncio.sleep(uniform(GATEWAY_MIN_DELAY_SECONDS, GATEWAY_MAX_DELAY_SECONDS))
    if random() < GATEWAY_FAILURE_RATE:
        return PaymentStatus.FAILED
    return PaymentStatus.SUCCESS


def build_webhook_payload(payment: Payment, status: str) -> dict:
    return {
        "payment_id": payment.id,
        "status": PaymentStatus(status).value,
        "amount": str(payment.amount),
        "currency": payment.currency,
        "metadata": payment.metadata,
        "idempotency_key": payment.idempotency_key,
    }


async def send_webhook(url: str, payload: dict) -> None:
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, timeout=WEBHOOK_TIMEOUT_SECONDS)
    response.raise_for_status()


async def process_payment(data: dict) -> bool:
    async with async_session_fabric() as session:
        orm_client = OrmClient(session)
        payment = await orm_client.get_payment(data.get("idempotency_key"))

        if not payment:
            return False

        status = payment.status
        if status == PaymentStatus.PENDING:
            status = await emulate_gateway()
            await orm_client.update_payment_status(payment.id, status)
            await session.commit()

        webhook_url = payment.webhook_url
        payload = build_webhook_payload(payment, status)

    await send_webhook(webhook_url, payload)
    return True
