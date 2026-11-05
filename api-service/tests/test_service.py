import pytest
from unittest.mock import AsyncMock
from sqlalchemy.exc import IntegrityError

from src.services.payment import PaymentService
from src.database.tables.payment import Payment

BODY = {
    "amount": 10.0,
    "currency": "RUB",
    "description": "test",
    "metadata": {},
    "webhook_url": "https://example.com/hook",
}


@pytest.fixture
def payment_repo():
    return AsyncMock()


@pytest.fixture
def outbox_repo():
    return AsyncMock()


@pytest.fixture
def service(payment_repo, outbox_repo):
    return PaymentService(payment_repo=payment_repo, outbox_repo=outbox_repo)


async def test_create_payment_returns_existing_on_repeated_key(service, payment_repo, outbox_repo):
    existing = Payment(idempotency_key="key-1")
    payment_repo.get_one = AsyncMock(return_value=existing)

    result = await service.create_payment(body=BODY, idempotency_key="key-1")

    assert result is existing
    payment_repo.create.assert_not_called()
    outbox_repo.create_payment_event.assert_not_called()


async def test_create_payment_returns_existing_on_integrity_error_race(service, payment_repo, outbox_repo):
    """Two concurrent requests pass the idempotency check; second hits UNIQUE constraint."""
    existing = Payment(idempotency_key="key-new")
    payment_repo.get_one = AsyncMock(side_effect=[None, existing])
    payment_repo.create = AsyncMock(side_effect=IntegrityError(None, None, Exception("unique")))

    result = await service.create_payment(body=BODY, idempotency_key="key-new")

    assert result is existing
    payment_repo.rollback.assert_awaited_once()
    outbox_repo.create_payment_event.assert_not_called()
    payment_repo.commit.assert_not_called()


async def test_create_payment_reraises_integrity_error_without_existing_payment(service, payment_repo):
    payment_repo.get_one = AsyncMock(return_value=None)
    payment_repo.create = AsyncMock(side_effect=IntegrityError(None, None, Exception("other")))

    with pytest.raises(IntegrityError):
        await service.create_payment(body=BODY, idempotency_key="key-new")


async def test_create_payment_writes_both_payment_and_outbox_in_one_transaction(service, payment_repo, outbox_repo):
    payment_repo.get_one = AsyncMock(return_value=None)
    new_payment = Payment(idempotency_key="key-new")
    payment_repo.create = AsyncMock(return_value=new_payment)

    result = await service.create_payment(body=BODY, idempotency_key="key-new")

    payment_repo.create.assert_awaited_once()
    _, create_kwargs = payment_repo.create.call_args
    assert create_kwargs.get("with_commit") is False

    outbox_repo.create_payment_event.assert_awaited_once()
    _, outbox_kwargs = outbox_repo.create_payment_event.call_args
    assert outbox_kwargs.get("with_commit") is False

    payment_repo.commit.assert_awaited_once()

    assert result is new_payment


async def test_create_payment_does_not_commit_on_outbox_failure(service, payment_repo, outbox_repo):
    payment_repo.get_one = AsyncMock(return_value=None)
    payment_repo.create = AsyncMock(return_value=Payment(idempotency_key="key-new"))
    outbox_repo.create_payment_event = AsyncMock(side_effect=Exception("outbox error"))

    with pytest.raises(Exception, match="outbox error"):
        await service.create_payment(body=BODY, idempotency_key="key-new")

    payment_repo.commit.assert_not_called()
