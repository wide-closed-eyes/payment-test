import logging
import asyncio
from faststream import FastStream, Logger
from faststream.rabbit import RabbitMessage

from src.tools.rabbit_client import broker, dlq, dlx, retry_exchange, retry_5s_queue, retry_15s_queue, retry_45s_queue, main_queue
from src.logger import logger
from src.tools.mock_logic import process_payment


app = FastStream(broker)


@app.on_startup
async def on_startup() -> None:
    logger.info("Consumer started, listening on payments.new")

@app.after_startup
async def _declare_topology() -> None:
    dlx_obj = await broker.declare_exchange(dlx)
    retry_exchange_obj = await broker.declare_exchange(retry_exchange)

    # 2. Объявляем очереди и получаем их объекты
    dlq_obj = await broker.declare_queue(dlq)
    retry_5s_obj = await broker.declare_queue(retry_5s_queue)
    retry_15s_obj = await broker.declare_queue(retry_15s_queue)
    retry_45s_obj = await broker.declare_queue(retry_45s_queue)

    # 3. Биндим, передавая низкоуровневые объекты exchange'ов
    await dlq_obj.bind(dlx_obj, routing_key="payments.dead")
    await retry_5s_obj.bind(retry_exchange_obj, routing_key="retry.5s")
    await retry_15s_obj.bind(retry_exchange_obj, routing_key="retry.15s")
    await retry_45s_obj.bind(retry_exchange_obj, routing_key="retry.45s")


RETRY_ROUTING_KEYS = {
    1: "retry.5s",
    2: "retry.15s",
    3: "retry.45s",
}

@app.on_shutdown
async def on_shutdown() -> None:
    logger.info("Consumer stopped")

@broker.subscriber(
    main_queue,
    ack_policy="MANUAL"
)
async def process_new_payment(
    body: dict,
    msg: RabbitMessage,
    logger: Logger,
) -> None:
    headers = dict(msg.headers or {})
    attempt = int(headers.get("x-retry-attempt", 0))

    logger.info(
        "Received message | attempt=%d | body=%s",
        attempt,
        body,
    )

    try:
        res = await process_payment(body)
        if not res:
            raise RuntimeError("Payment busy or does not exist")
    except Exception as e:
        logger.error(str(e))
        next_attempt = attempt + 1
        routing_key = RETRY_ROUTING_KEYS.get(next_attempt)

        if routing_key is None:
            logger.error("All attempts failed, moving to DLQ")
            await msg.reject(requeue=False)
            return

        await broker.publish(
            body,
            exchange=retry_exchange,
            routing_key=routing_key,
            headers={**headers, "x-retry-attempt": next_attempt},
            persist=True,
        )
        await msg.ack()
    
    logger.info(f"Payment {body.get('id')} processed successfully")

    await msg.ack()

if __name__ == "__main__":
    asyncio.run(app.run(log_level=logging.DEBUG))
