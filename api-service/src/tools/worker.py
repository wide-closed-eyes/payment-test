import asyncio
import logging
from datetime import datetime, timezone

from faststream.rabbit import RabbitBroker

from src.database.repository.outbox import OutboxRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OutboxWorker")

BROKER_RECONNECT_SECONDS = 5


def format_publish_error(queue: str, error: Exception) -> str:
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return (
        f"{timestamp} публикация в очередь {queue} не удалась: "
        f"{type(error).__name__}: {error}"
    )


class OutboxWorker:
    def __init__(self, rmq_client: RabbitBroker, session_factory):
        self.rmq_client = rmq_client
        self.session_factory = session_factory
        self.is_running = False

    async def _process_outbox(self) -> bool:
        async with self.session_factory() as session:
            outbox_repository = OutboxRepository(session)
            events = await outbox_repository.select_for_update(limit=10)

            if not events:
                return False

            for event in events:
                try:
                    await self.rmq_client.publish(
                        message=event.payload,
                        queue=event.event_type,
                        correlation_id=str(event.id),
                    )

                    event.processed = True
                    event.processed_at = datetime.now()
                    logger.info(f"Событие {event.id} успешно доставлено в RabbitMQ.")
                except Exception as e:
                    event.error_log = format_publish_error(event.event_type, e)
                    logger.error(
                        f"Не удалось отправить событие {event.id}: {event.error_log}"
                    )
                    await asyncio.sleep(1)

            await outbox_repository.commit()
        return True

    async def _connect_broker(self) -> None:
        # Подключаемся в фоне, а не при старте приложения: API должен принимать
        # платежи и без брокера, события дождутся публикации в outbox.
        while self.is_running:
            try:
                await self.rmq_client.start()
                logger.info("Подключение к RabbitMQ установлено.")
                return
            except Exception as e:
                logger.warning(f"RabbitMQ недоступен, повторная попытка: {e}")
                await asyncio.sleep(BROKER_RECONNECT_SECONDS)

    async def start(self):
        self.is_running = True
        await self._connect_broker()
        while self.is_running:
            try:
                has_data = await self._process_outbox()

                if not has_data:
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Ошибка в воркере: {e}")
                await asyncio.sleep(10)

    async def stop(self):
        self.is_running = False
