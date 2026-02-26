import json
from datetime import datetime, timezone

import aio_pika

from app.config import settings

_connection: aio_pika.abc.AbstractRobustConnection | None = None
_channel: aio_pika.abc.AbstractChannel | None = None

EXCHANGE_NAME = "healthcare"


async def get_connection() -> aio_pika.abc.AbstractRobustConnection:
    global _connection
    if _connection is None or _connection.is_closed:
        _connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    return _connection


async def get_channel() -> aio_pika.abc.AbstractChannel:
    global _channel
    connection = await get_connection()
    if _channel is None or _channel.is_closed:
        _channel = await connection.channel()
    return _channel


async def publish_event(routing_key: str, data: dict) -> None:
    channel = await get_channel()
    exchange = await channel.declare_exchange(EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True)

    message_body = {
        "event_type": routing_key,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }

    message = aio_pika.Message(
        body=json.dumps(message_body, default=str).encode(),
        content_type="application/json",
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
    )

    await exchange.publish(message, routing_key=routing_key)


async def close_connection() -> None:
    global _connection, _channel
    if _channel and not _channel.is_closed:
        await _channel.close()
        _channel = None
    if _connection and not _connection.is_closed:
        await _connection.close()
        _connection = None
