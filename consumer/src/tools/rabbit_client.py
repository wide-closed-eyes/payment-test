from faststream.rabbit import RabbitBroker, RabbitQueue, RabbitExchange, ExchangeType
from src.config import config


# --- DLX / DLQ ---
dlx = RabbitExchange("payments.dlx", type=ExchangeType.DIRECT, durable=True)
dlq = RabbitQueue(
    "payments.dlq",
    durable=True,
    routing_key="payments.dead",
)

# --- Основная очередь ---
main_queue = RabbitQueue(
    "payments.new",
    durable=True,
    arguments={
        "x-dead-letter-exchange": "payments.dlx",
        "x-dead-letter-routing-key": "payments.dead",
    },
)

# --- Retry exchange ---
retry_exchange = RabbitExchange(
    "payments.retry",
    type=ExchangeType.DIRECT,
    durable=True,
)


def make_retry_queue(name: str, ttl_ms: int, routing_key: str) -> RabbitQueue:
    return RabbitQueue(
        name,
        durable=True,
        routing_key=routing_key,
        arguments={
            # возврат в основную очередь через default exchange
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": "payments.new",
            "x-message-ttl": ttl_ms,
        },
    )


retry_5s_queue  = make_retry_queue("payments.retry.5s",  5_000,  "retry.5s")
retry_15s_queue = make_retry_queue("payments.retry.15s", 15_000, "retry.15s")
retry_45s_queue = make_retry_queue("payments.retry.45s", 45_000, "retry.45s")


broker = RabbitBroker(config.amqp_url)
