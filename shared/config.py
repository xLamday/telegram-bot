"""
shared/config.py
Configurazione globale — usata sia dal bot che dal web panel.
Carica variabili da .env o ambiente di sistema.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class BotConfig:
    TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "8477419835:AAE1mVmAc9TQ6T8lQ0itd3DRInLTtRAyv3g")
    ADMIN_IDS: list[int] = [
        int(x) for x in os.getenv("ADMIN_IDS", "961492841").split(",") if x.strip()
    ]


class DatabaseConfig:
    # Usa SQLite di default (zero config su Windows)
    URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite+aiosync:///{BASE_DIR}/data/bot.db"
    )
    # Versione sincrona per Django ORM / alembic
    SYNC_URL: str = os.getenv(
        "DATABASE_SYNC_URL",
        f"sqlite:///{BASE_DIR}/data/bot.db"
    )
    ECHO: bool = os.getenv("DB_ECHO", "false").lower() == "true"


class WebConfig:
    SECRET_KEY: str = os.getenv("DJANGO_SECRET_KEY", "vm7@w5tdo(1qj4sfm$u$4*_ng)4v4d5j*3u=(b4q9*o&rs+%q!")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    ALLOWED_HOSTS: list[str] = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    FASTAPI_PORT: int = int(os.getenv("FASTAPI_PORT", "8001"))
    DJANGO_PORT: int = int(os.getenv("DJANGO_PORT", "8000"))


bot_config = BotConfig()
db_config = DatabaseConfig()
web_config = WebConfig()
