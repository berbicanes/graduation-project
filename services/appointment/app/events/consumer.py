import asyncio
import json
import logging

import aio_pika

from app.config import settings
from app.crud import cache_patient
from app.db import async_session_maker

logger = logging.getLogger(__name__)

EXCHANGE_NAME = "healthcare"
QUEUE_NAME = "appointment.patient_events"

_connection: aio_pika.abc.AbstractRobustConnection | None = None


async def handle_patient_created(data: dict) -> None:
    """Cache patient info when a patient is created or updated."""
    import uuid

    patient_id = uuid.UUID(data["id"])
    first_name = data["first_name"]
    last_name = data["last_name"]

    async with async_session_maker() as session:
        try:
            await cache_patient(session, patient_id, first_name, last_name)
            await session.commit()
            logger.info("Cached patient %s", patient_id)
        except Exception:
            await session.rollback()
            logger.exception("Failed to cache patient %s", patient_id)


async def process_message(message: aio_pika.abc.AbstractIncomingMessage) -> None:
    async with message.process():
        try:
            body = json.loads(message.body.decode())
            event_type = body.get("event_type", "")
            data = body.get("data", {})

            if event_type in ("patient.created", "patient.updated"):
                await handle_patient_created(data)
            else:
                logger.debug("Ignoring event: %s", event_type)
        except Exception:
            logger.exception("Error processing message")


async def start_consumer() -> None:
    global _connection
    while True:
        try:
            _connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
            channel = await _connection.channel()
            await channel.set_qos(prefetch_count=10)

            exchange = await channel.declare_exchange(EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True)
            queue = await channel.declare_queue(QUEUE_NAME, durable=True)
            await queue.bind(exchange, routing_key="patient.*")

            logger.info("Consumer started, listening on %s", QUEUE_NAME)
            await queue.consume(process_message)

            # Keep running until connection closes
            await asyncio.Future()
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("Consumer connection lost, reconnecting in 5s...")
            await asyncio.sleep(5)


async def close_consumer() -> None:
    global _connection
    if _connection and not _connection.is_closed:
        await _connection.close()
        _connection = None
