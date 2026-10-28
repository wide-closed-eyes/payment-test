import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.tools.mock_logic import process_payment
from src.database.tables import PaymentStatus


def make_payment(status=PaymentStatus.PENDING):
    p = MagicMock()
    p.status = status
    p.id = "uuid-1"
    p.webhook_url = "https://example.com/hook"
    return p


def fake_session_gen():
    async def _gen():
        yield MagicMock()
    return _gen


async def test_payment_not_found_returns_false():
    orm = AsyncMock()
    orm.get_payment.return_value = None

    with patch("src.tools.mock_logic.get_session", fake_session_gen()), \
         patch("src.tools.mock_logic.OrmClient", return_value=orm):
        result = await process_payment({"idempotency_key": "k1"})

    assert result is False
    orm.update_payment_status.assert_not_called()


async def test_non_pending_returns_true_without_db_update():
    orm = AsyncMock()
    orm.get_payment.return_value = make_payment(status=PaymentStatus.SUCCESS)

    with patch("src.tools.mock_logic.get_session", fake_session_gen()), \
         patch("src.tools.mock_logic.OrmClient", return_value=orm):
        result = await process_payment({"idempotency_key": "k1"})

    assert result is True
    orm.update_payment_status.assert_not_called()


async def test_processing_failure_does_not_update_status():
    """RuntimeError before webhook → status must not be changed (fix: status updated only after webhook)."""
    orm = AsyncMock()
    orm.get_payment.return_value = make_payment()

    with patch("src.tools.mock_logic.get_session", fake_session_gen()), \
         patch("src.tools.mock_logic.OrmClient", return_value=orm), \
         patch("src.tools.mock_logic.randint", return_value=9):
        with pytest.raises(RuntimeError, match="Payment service unavailable"):
            await process_payment({"idempotency_key": "k1"})

    orm.update_payment_status.assert_not_called()


async def test_webhook_failure_does_not_update_status():
    """Webhook error → exception propagates, status stays pending so retry can re-send webhook."""
    orm = AsyncMock()
    orm.get_payment.return_value = make_payment()

    mock_http = AsyncMock()
    mock_http.post.side_effect = Exception("connection refused")

    with patch("src.tools.mock_logic.get_session", fake_session_gen()), \
         patch("src.tools.mock_logic.OrmClient", return_value=orm), \
         patch("src.tools.mock_logic.randint", return_value=0), \
         patch("src.tools.mock_logic.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_http)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=None)

        with pytest.raises(Exception, match="connection refused"):
            await process_payment({"idempotency_key": "k1"})

    orm.update_payment_status.assert_not_called()


async def test_success_calls_webhook_then_updates_status():
    """Happy path: webhook called, then status updated to SUCCESS, returns True."""
    payment = make_payment()
    orm = AsyncMock()
    orm.get_payment.return_value = payment

    mock_http = AsyncMock()
    call_order = []
    mock_http.post = AsyncMock(side_effect=lambda *a, **kw: call_order.append("webhook"))
    orm.update_payment_status = AsyncMock(side_effect=lambda *a, **kw: call_order.append("status"))

    with patch("src.tools.mock_logic.get_session", fake_session_gen()), \
         patch("src.tools.mock_logic.OrmClient", return_value=orm), \
         patch("src.tools.mock_logic.randint", return_value=0), \
         patch("src.tools.mock_logic.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_http)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await process_payment({"idempotency_key": "k1"})

    assert result is True
    assert call_order == ["webhook", "status"], "webhook must be called before status update"
    orm.update_payment_status.assert_awaited_once_with(payment.id, PaymentStatus.SUCCESS)
