import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from main import process_new_payment


@pytest.fixture
def msg():
    m = AsyncMock()
    m.headers = {}
    return m


async def test_success_acks_exactly_once(msg):
    with patch("main.process_payment", new_callable=AsyncMock, return_value=True):
        await process_new_payment(body={"id": "p1"}, msg=msg, logger=MagicMock())

    msg.ack.assert_awaited_once()
    msg.reject.assert_not_awaited()


async def test_failure_attempt_0_routes_to_retry_5s(msg):
    msg.headers = {"x-retry-attempt": 0}

    with patch("main.process_payment", new_callable=AsyncMock, side_effect=RuntimeError("err")), \
         patch("main.broker") as mock_broker:
        mock_broker.publish = AsyncMock()
        await process_new_payment(body={"id": "p1"}, msg=msg, logger=MagicMock())

    mock_broker.publish.assert_awaited_once()
    assert mock_broker.publish.call_args.kwargs["routing_key"] == "retry.5s"
    # ack once in retry branch, then return — no second ack from the success path
    msg.ack.assert_awaited_once()
    msg.reject.assert_not_awaited()


async def test_failure_attempt_1_routes_to_retry_15s(msg):
    msg.headers = {"x-retry-attempt": 1}

    with patch("main.process_payment", new_callable=AsyncMock, side_effect=RuntimeError("err")), \
         patch("main.broker") as mock_broker:
        mock_broker.publish = AsyncMock()
        await process_new_payment(body={"id": "p1"}, msg=msg, logger=MagicMock())

    assert mock_broker.publish.call_args.kwargs["routing_key"] == "retry.15s"


async def test_failure_attempt_2_routes_to_retry_45s(msg):
    msg.headers = {"x-retry-attempt": 2}

    with patch("main.process_payment", new_callable=AsyncMock, side_effect=RuntimeError("err")), \
         patch("main.broker") as mock_broker:
        mock_broker.publish = AsyncMock()
        await process_new_payment(body={"id": "p1"}, msg=msg, logger=MagicMock())

    assert mock_broker.publish.call_args.kwargs["routing_key"] == "retry.45s"


async def test_failure_attempt_3_rejects_to_dlq_without_publish(msg):
    msg.headers = {"x-retry-attempt": 3}

    with patch("main.process_payment", new_callable=AsyncMock, side_effect=RuntimeError("err")), \
         patch("main.broker") as mock_broker:
        mock_broker.publish = AsyncMock()
        await process_new_payment(body={"id": "p1"}, msg=msg, logger=MagicMock())

    mock_broker.publish.assert_not_awaited()
    msg.reject.assert_awaited_once_with(requeue=False)
    msg.ack.assert_not_awaited()


async def test_retry_header_incremented_correctly(msg):
    msg.headers = {"x-retry-attempt": 0, "x-custom": "val"}

    with patch("main.process_payment", new_callable=AsyncMock, side_effect=RuntimeError("err")), \
         patch("main.broker") as mock_broker:
        mock_broker.publish = AsyncMock()
        await process_new_payment(body={"id": "p1"}, msg=msg, logger=MagicMock())

    published_headers = mock_broker.publish.call_args.kwargs["headers"]
    assert published_headers["x-retry-attempt"] == 1
    assert published_headers["x-custom"] == "val"
