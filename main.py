"""
FastAPI — API Layer per il Bot Telegram
Espone endpoint REST che il Django Panel e il Bot usano.
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from .routes import channels, messages, stats
from .database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Telegram Bot API",
    description="REST API per gestire il bot Telegram dal Web Panel",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(channels.router, prefix="/api/channels", tags=["Canali"])
app.include_router(messages.router, prefix="/api/messages", tags=["Messaggi"])
app.include_router(stats.router, prefix="/api/stats", tags=["Statistiche"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "telegram-bot-api"}
