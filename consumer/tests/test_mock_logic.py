from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.database.tables import PaymentStatus
from src.tools.mock_logic import emulate_gateway, process_payment

WEBHOOK_URL = "https://example.com/hook"


def make_payment(status=PaymentStatus.PENDING):
    p = MagicMock()
    p.status = status
    p.id = "uuid-1"
    p.amount = Decimal("10.11")
    p.currency = "RUB"
    p.metadata = {"order_id": "123"}
    p.idempotency_key = "k1"
    p.webhook_url = WEBHOOK_URL
    return p


@pytest.fixture
def session():
    return AsyncMock()


@pytest.fixture
def orm():
    return AsyncMock()


@pytest.fixture
def webhook():
    """HTTP-клиент вебхука; по умолчанию получатель отвечает 200."""
    http = AsyncMock()
    http.post.return_value = httpx.Response(
        200, request=httpx.Request("POST", WEBHOOK_URL)
    )
    with patch("src.tools.mock_logic.httpx.AsyncClient") as client:
        client.return_value.__aenter__ = AsyncMock(return_value=http)
        client.return_value.__aexit__ = AsyncMock(return_value=None)
        yield http


@pytest.fixture(autouse=True)
def infrastructure(session, orm):
    factory = MagicMock()
    factory.return_value.__aenter__ = AsyncMock(return_value=session)
    factory.return_value.__aexit__ = AsyncMock(return_value=None)
    with patch("src.tools.mock_logic.async_session_fabric", factory), patch(
        "src.tools.mock_logic.OrmClient", return_value=orm
    ):
        yield


def gateway_returns(status):
    return patch(
        "src.tools.mock_logic.emulate_gateway",
        new_callable=AsyncMock,
        return_value=status,
    )


async def test_gateway_waits_between_2_and_5_seconds():
    with patch("src.tools.mock_logic.asyncio.sleep", new_callable=AsyncMock) as sleep:
        await emulate_gateway()

    delay = sleep.await_args.args[0]
    assert 2 <= delay <= 5


@pytest.mark.parametrize(
    ("roll", "expected"),
    [(0.0, PaymentStatus.FAILED), (0.99, PaymentStatus.SUCCESS)],
)
async def test_gateway_result(roll, expected):
    with patch("src.tools.mock_logic.asyncio.sleep", new_callable=AsyncMock), patch(
        "src.tools.mock_logic.random", return_value=roll
    ):
        assert await emulate_gateway() == expected


async def test_payment_not_found_returns_false(orm, webhook):
    orm.get_payment.return_value = None

    assert await process_payment({"idempotency_key": "k1"}) is False

    orm.update_payment_status.assert_not_called()
    webhook.post.assert_not_called()


@pytest.mark.parametrize("status", [PaymentStatus.SUCCESS, PaymentStatus.FAILED])
async def test_gateway_result_is_saved_and_sent_in_webhook(
    status, session, orm, webhook
):
    payment = make_payment()
    orm.get_payment.return_value = payment

    with gateway_returns(status):
        assert await process_payment({"idempotency_key": "k1"}) is True

    orm.update_payment_status.assert_awaited_once_with(payment.id, status)
    session.commit.assert_awaited_once()
    assert webhook.post.await_args.args == (WEBHOOK_URL,)
    assert webhook.post.await_args.kwargs["json"] == {
        "payment_id": "uuid-1",
        "status": status.value,
        "amount": "10.11",
        "currency": "RUB",
        "metadata": {"order_id": "123"},
        "idempotency_key": "k1",
    }


async def test_status_is_committed_before_webhook(session, orm, webhook):
    orm.get_payment.return_value = make_payment()
    call_order = []
    session.commit.side_effect = lambda: call_order.append("commit")

    async def post(*args, **kwargs):
        call_order.append("webhook")
        return httpx.Response(200, request=httpx.Request("POST", WEBHOOK_URL))

    webhook.post.side_effect = post

    with gateway_returns(PaymentStatus.SUCCESS):
        await process_payment({"idempotency_key": "k1"})

    assert call_order == ["commit", "webhook"]


@pytest.mark.parametrize("code", [302, 404, 500])
async def test_webhook_error_status_propagates_for_retry(code, orm, webhook):
    orm.get_payment.return_value = make_payment()
    webhook.post.return_value = httpx.Response(
        code, request=httpx.Request("POST", WEBHOOK_URL)
    )

    with gateway_returns(PaymentStatus.SUCCESS):
        with pytest.raises(httpx.HTTPStatusError):
            await process_payment({"idempotency_key": "k1"})


async def test_webhook_connection_error_propagates_for_retry(orm, webhook):
    orm.get_payment.return_value = make_payment()
    webhook.post.side_effect = httpx.ConnectError("connection refused")

    with gateway_returns(PaymentStatus.SUCCESS):
        with pytest.raises(httpx.ConnectError):
            await process_payment({"idempotency_key": "k1"})


async def test_retry_after_webhook_failure_only_resends_webhook(session, orm, webhook):
    orm.get_payment.return_value = make_payment(status=PaymentStatus.FAILED)

    with gateway_returns(PaymentStatus.SUCCESS) as gateway:
        assert await process_payment({"idempotency_key": "k1"}) is True

    gateway.assert_not_called()
    orm.update_payment_status.assert_not_called()
    session.commit.assert_not_called()
    assert webhook.post.await_args.kwargs["json"]["status"] == "failed"
