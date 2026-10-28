import pytest
from unittest.mock import AsyncMock
from sqlalchemy.exc import IntegrityError

from src.database.repository.payment import PaymentRepository
from src.database.tables.payment import Payment

BODY = {
    "amount": 10.0,
    "currency": "RUB",
    "description": "test",
    "metadata": {},
    "webhook_url": "https://example.com/hook",
}


@pytest.fixture
def repo():
    return PaymentRepository(session=AsyncMock())


async def test_create_from_request_raises_on_existing_idempotency_key(repo):
    repo.get_one = AsyncMock(return_value=Payment(idempotency_key="key-1"))

    with pytest.raises(Exception, match="Payment already exists"):
        await repo.create_from_request(body=BODY, idempotency_key="key-1")


async def test_create_from_request_raises_on_integrity_error_race(repo):
    """Two concurrent requests pass the check; the second hits the UNIQUE constraint."""
    repo.get_one = AsyncMock(return_value=None)
    repo.create = AsyncMock(side_effect=IntegrityError(None, None, Exception("unique")))

    with pytest.raises(Exception, match="Payment already exists"):
        await repo.create_from_request(body=BODY, idempotency_key="key-new")


async def test_create_from_request_returns_new_payment(repo):
    new_payment = Payment(idempotency_key="key-new")
    repo.get_one = AsyncMock(return_value=None)
    repo.create = AsyncMock(return_value=new_payment)

    result = await repo.create_from_request(body=BODY, idempotency_key="key-new")

    assert result is new_payment
    repo.create.assert_awaited_once()


async def test_create_from_request_with_commit_false_does_not_commit(repo):
    new_payment = Payment(idempotency_key="key-new")
    repo.get_one = AsyncMock(return_value=None)
    repo.create = AsyncMock(return_value=new_payment)

    await repo.create_from_request(body=BODY, idempotency_key="key-new", with_commit=False)

    _, kwargs = repo.create.call_args
    assert kwargs.get("with_commit") is False
