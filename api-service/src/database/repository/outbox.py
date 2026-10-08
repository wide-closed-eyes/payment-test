from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.dependency.repository import AsyncRepository
from src.database.dependency.session import get_session
from src.database.tables import OutboxEvent, Payment


class OutboxRepository(AsyncRepository[OutboxEvent]):
    def __init__(self, session: AsyncSession):
        super().__init__(OutboxEvent, session)
    
    async def create_payment_event(self, payment: Payment):
        outbox_event = OutboxEvent(
            aggregate_type="Payment",
            aggregate_id=payment.id,
            event_type="payments.new",
            payload=payment.dict(),
        )
        return await self.create(outbox_event)
    
    async def select_for_update(self, limit: int = 10) -> list[OutboxEvent]:
        return await self.get_all(
            filter=[OutboxEvent.processed == False],
            order_by=OutboxEvent.created_at,
            is_for_update=True,
            limit=limit
        )


def get_repository() -> OutboxRepository:
    def func(session: AsyncSession = Depends(get_session)):
        return OutboxRepository(session)

    return func


OutboxRepositoryGetter = Annotated[
    OutboxRepository,
    Depends(get_repository()),
]
