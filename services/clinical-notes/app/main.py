import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as notes_router
from app.config import settings
from app.events.consumer import close_consumer, start_consumer
from app.events.publisher import close_connection as close_publisher

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start RabbitMQ consumer as a background task
    consumer_task = asyncio.create_task(start_consumer())
    logger.info("Started RabbitMQ consumer background task")
    yield
    # Shutdown
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass
    await close_consumer()
    await close_publisher()


app = FastAPI(title="Clinical Notes Service", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(notes_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy"}
