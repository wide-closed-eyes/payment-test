from random import randint
import httpx

from src.database.orm_client import OrmClient
from src.database.tables import PaymentStatus
from src.database.database import get_session


async def process_payment(data: dict):
    async for session in get_session():
        orm_client = OrmClient(session)
        payment = await orm_client.get_payment(data.get("idempotency_key"))

        if payment.status != PaymentStatus.PENDING:
            return True
        if not payment:
            return False

        # Бизнес-логика обработки платежа
        res = randint(0, 9)

        if res < 9:
            await orm_client.update_payment_status(payment.id, PaymentStatus.SUCCESS)
        else:
            raise RuntimeError("Payment service unavailable")
        
        async with httpx.AsyncClient() as client:
            await client.post(payment.webhook_url, json=data, timeout=5)
        
        return True