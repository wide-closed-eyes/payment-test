import pytest
from unittest.mock import AsyncMock

from src.database.repository.payment import PaymentRepository
from src.database.tables.payment import Payment


@pytest.fixture
def repo():
    return PaymentRepository(session=AsyncMock())


async def test_get_full_payment_returns_result(repo):
    payment = Payment(idempotency_key="key-1")
    repo._session.get = AsyncMock(return_value=payment)

    result = await repo.get_full_payment("some-uuid")

    assert result is payment


async def test_get_full_payment_returns_none_when_not_found(repo):
    repo._session.get = AsyncMock(return_value=None)

    result = await repo.get_full_payment("nonexistent-uuid")

    assert result is None
