import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from pythonjsonlogger.json import JsonFormatter as jsonlogger_JsonFormatter

from app.api.routes import router as patient_router
from app.config import settings
from app.events.publisher import close_connection

# Structured JSON logging
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(
    jsonlogger_JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={"asctime": "timestamp", "levelname": "level", "name": "service"},
    )
)
logging.root.handlers = [handler]
logging.root.setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_connection()


app = FastAPI(title="Patient Service", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)

app.include_router(patient_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy"}
