import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app import app
from src.tools.worker import OutboxWorker, format_publish_error


def make_worker(broker) -> OutboxWorker:
    return OutboxWorker(broker, MagicMock())


async def test_worker_retries_broker_connection_until_success():
    broker = AsyncMock()
    broker.start.side_effect = [ConnectionError("down"), ConnectionError("down"), None]
    worker = make_worker(broker)
    worker.is_running = True

    with patch("src.tools.worker.BROKER_RECONNECT_SECONDS", 0):
        await worker._connect_broker()

    assert broker.start.await_count == 3


async def test_worker_stops_while_broker_is_unavailable():
    broker = AsyncMock()
    broker.start.side_effect = ConnectionError("down")
    worker = make_worker(broker)

    with patch("src.tools.worker.BROKER_RECONNECT_SECONDS", 0):
        task = asyncio.create_task(worker.start())
        await asyncio.sleep(0.01)
        await worker.stop()
        await asyncio.wait_for(task, timeout=1)

    worker.session_factory.assert_not_called()


def test_publish_error_names_queue_and_exception_type():
    message = format_publish_error("payments.new", TimeoutError())

    assert "payments.new" in message
    assert "TimeoutError" in message


def test_app_starts_and_stops_without_broker():
    with (
        patch("app.rabbitmq_client") as broker,
        patch("src.tools.worker.BROKER_RECONNECT_SECONDS", 0),
    ):
        broker.start = AsyncMock(side_effect=ConnectionError("down"))
        broker.stop = AsyncMock()

        with TestClient(app) as client:
            assert client.get("/api/v1/payments/1").status_code == 401

    broker.stop.assert_awaited_once()
