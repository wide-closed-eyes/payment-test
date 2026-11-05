from typing import Annotated

from fastapi import Depends
from sqlalchemy.exc import IntegrityError

from src.database.repository.outbox import OutboxRepository
from src.database.repository.outbox import get_repository as get_outbox_repository
from src.database.repository.payment import PaymentRepository
from src.database.repository.payment import get_repository as get_payment_repository
from src.database.tables.payment import Payment


class PaymentService:
    def __init__(self, payment_repo: PaymentRepository, outbox_repo: OutboxRepository):
        self._payment = payment_repo
        self._outbox = outbox_repo

    async def create_payment(self, body: dict, idempotency_key: str) -> Payment:
        key_filter = [Payment.idempotency_key == idempotency_key]

        existing = await self._payment.get_one(key_filter)
        if existing:
            return existing

        payment = Payment(**body | {"idempotency_key": idempotency_key})
        try:
            payment = await self._payment.create(payment, with_commit=False)
        except IntegrityError:
            # Параллельный запрос с тем же ключом успел создать платёж первым
            await self._payment.rollback()
            existing = await self._payment.get_one(key_filter)
            if existing:
                return existing
            raise

        await self._outbox.create_payment_event(payment, with_commit=False)
        await self._payment.commit()
        return payment


def get_service():
    def func(
        payment_repo: PaymentRepository = Depends(get_payment_repository()),
        outbox_repo: OutboxRepository = Depends(get_outbox_repository()),
    ) -> PaymentService:
        return PaymentService(payment_repo, outbox_repo)

    return func


PaymentServiceGetter = Annotated[PaymentService, Depends(get_service())]
