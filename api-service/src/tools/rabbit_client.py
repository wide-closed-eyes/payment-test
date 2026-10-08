from faststream.rabbit import RabbitBroker
from src.config import config


rabbitmq_client = RabbitBroker(config.amqp_url)
