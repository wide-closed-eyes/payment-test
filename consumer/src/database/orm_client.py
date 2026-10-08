from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.tables import Payment


class OrmClient:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_payment(self, idempotency_key: str) -> Payment:
        query = (
            select(Payment)
            .where(Payment.idempotency_key == idempotency_key)
            .order_by(Payment.created_at.desc())
            .with_for_update(skip_locked=True)
        )
        result = await self._session.execute(query)
        return result.scalars().first()
    
    async def update_payment_status(self, payment_id: str, status: str) -> None:
        query = (
            update(Payment)
            .where(Payment.id == payment_id)
            .values(status=status)
        )
        await self._session.execute(query)
