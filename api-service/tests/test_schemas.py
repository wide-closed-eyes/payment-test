from datetime import datetime

import pytest
from pydantic import ValidationError

from src.api.schemas.payment import PaymentCreate, PaymentCreateResponse, PaymentFullResponse

VALID_PAYLOAD = {
    "amount": 10.50,
    "currency": "RUB",
    "description": "test",
    "metadata": {},
    "webhook_url": "https://example.com/hook",
}


def test_payment_create_valid():
    p = PaymentCreate(**VALID_PAYLOAD)
    assert p.amount == 10.50
    assert p.currency == "RUB"


def test_payment_create_invalid_currency():
    with pytest.raises(ValidationError):
        PaymentCreate(**{**VALID_PAYLOAD, "currency": "GBP"})


def test_payment_create_invalid_webhook_url():
    with pytest.raises(ValidationError):
        PaymentCreate(**{**VALID_PAYLOAD, "webhook_url": "not-a-url"})


def test_payment_create_webhook_url_required():
    payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "webhook_url"}
    with pytest.raises(ValidationError):
        PaymentCreate(**payload)


def test_payment_create_response_formats_datetime():
    resp = PaymentCreateResponse(id="uuid-1", status="pending", created_at=datetime(2026, 10, 28, 12, 34))
    assert resp.created_at == "28-10-2026 12:34"


def test_payment_create_response_passes_string_created_at():
    resp = PaymentCreateResponse(id="uuid-1", status="pending", created_at="already-a-string")
    assert resp.created_at == "already-a-string"


def test_payment_full_response_formats_both_dates():
    dt = datetime(2026, 1, 5, 9, 5)
    resp = PaymentFullResponse(
        id="uuid-1",
        amount=10.50,
        currency="RUB",
        description="test",
        metadata={},
        status="succeeded",
        idempotency_key="key-1",
        webhook_url="https://example.com/hook",
        created_at=dt,
        updated_at=dt,
    )
    assert resp.created_at == "05-01-2026 09:05"
    assert resp.updated_at == "05-01-2026 09:05"
