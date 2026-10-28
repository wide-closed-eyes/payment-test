from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.dependency.repository import AsyncRepository
from src.database.dependency.session import get_session
from src.database.tables.payment import Payment


class PaymentRepository(AsyncRepository[Payment]):
    def __init__(self, session: AsyncSession):
        super().__init__(Payment, session)

    async def get_full_payment(self, payment_id: str) -> Payment | None:
        return await self.get_by_pk(payment_id)


def get_repository() -> PaymentRepository:
    def func(session: AsyncSession = Depends(get_session)):
        return PaymentRepository(session)

    return func


PaymentRepositoryGetter = Annotated[
    PaymentRepository,
    Depends(get_repository()),
]
