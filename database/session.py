"""
database/session.py
Gestione sessioni DB — sia sincrona (Django) che asincrona (bot/FastAPI).
"""
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, Session

from shared.config import db_config
from database.models import Base

# ── Assicura che la cartella data/ esista ──────────────────────────────────
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# ══════════════════════════════════════════════════════════════════════════════
# ENGINE SINCRONO  →  usato da Django, Alembic, script di setup
# ══════════════════════════════════════════════════════════════════════════════
sync_engine = create_engine(
    db_config.SYNC_URL,
    echo=db_config.ECHO,
    connect_args={"check_same_thread": False},  # necessario per SQLite
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
    class_=Session,
)


def get_sync_db() -> Session:
    """Dependency per Django / script sincroni."""
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════════
# ENGINE ASINCRONO  →  usato dal bot Telegram e FastAPI
# ══════════════════════════════════════════════════════════════════════════════
# SQLite asincrono usa aiosqlite
_async_url = db_config.SYNC_URL.replace("sqlite://", "sqlite+aiosqlite://")

async_engine = create_async_engine(
    _async_url,
    echo=db_config.ECHO,
)

AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_async_db() -> AsyncSession:
    """Dependency per FastAPI (async)."""
    async with AsyncSessionLocal() as session:
        yield session


# ══════════════════════════════════════════════════════════════════════════════
# INIT DB  →  crea tutte le tabelle se non esistono
# ══════════════════════════════════════════════════════════════════════════════
def init_db_sync():
    """Crea le tabelle usando l'engine sincrono (utile in setup/migrate)."""
    Base.metadata.create_all(bind=sync_engine)


async def init_db_async():
    """Crea le tabelle usando l'engine asincrono (utile all'avvio del bot)."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
