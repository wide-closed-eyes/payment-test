from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.v1 import router
from src.config import config
from src.database.tables.payment import Payment
from src.services.payment import PaymentServiceGetter

BODY = {
    "amount": 10.11,
    "currency": "RUB",
    "description": "test",
    "metadata": {},
    "webhook_url": "https://example.com/hook",
}


@pytest.fixture
def service():
    service = AsyncMock()
    service.create_payment.return_value = Payment(
        id="uuid-1", status="pending", created_at=datetime(2026, 10, 28, 12, 34)
    )
    return service


@pytest.fixture
def client(service):
    app = FastAPI()
    app.include_router(router)
    dependency = PaymentServiceGetter.__metadata__[0].dependency
    app.dependency_overrides[dependency] = lambda: service
    # raise_server_exceptions=False: ошибки сервиса проверяем как HTTP-ответ клиенту
    return TestClient(app, raise_server_exceptions=False)


def post(client, api_key=config.api_key, idempotency_key="key-1"):
    headers = {"Idempotency-Key": idempotency_key}
    if api_key is not None:
        headers["X-API-Key"] = api_key
    return client.post("/api/v1/payments", json=BODY, headers=headers)


@pytest.mark.parametrize("api_key", ["wrong-key", None])
def test_invalid_or_missing_api_key_returns_401(client, service, api_key):
    response = post(client, api_key=api_key)

    assert response.status_code == 401
    service.create_payment.assert_not_called()


def test_non_ascii_api_key_returns_401_not_500(client):
    response = client.post(
        "/api/v1/payments",
        json=BODY,
        headers={"Idempotency-Key": "key-1", "X-API-Key": "ключ".encode()},
    )

    assert response.status_code == 401


def test_repeated_request_returns_same_payment(client):
    first = post(client)
    second = post(client)

    assert first.status_code == second.status_code == 202
    assert first.json() == second.json()
    assert first.json()["id"] == "uuid-1"


def test_idempotency_key_longer_than_column_returns_422(client, service):
    response = post(client, idempotency_key="k" * 65)

    assert response.status_code == 422
    service.create_payment.assert_not_called()


def test_internal_error_is_not_reported_as_conflict(client, service):
    service.create_payment.side_effect = RuntimeError("db is down")

    assert post(client).status_code == 500
