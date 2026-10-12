"""
Application settings and configuration.
I segreti vanno nel file .env (mai nel codice).
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _richiesto(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Variabile d'ambiente mancante: {name} (impostala nel file .env)")
    return value


class Settings:
    """Bot settings."""

    TELEGRAM_TOKEN = _richiesto("TELEGRAM_TOKEN")
    ADMIN_ID = int(_richiesto("ADMIN_ID"))
    CANALE_CONTROLLO = int(_richiesto("CANALE_CONTROLLO"))
    DATABASE_PATH = os.getenv("DATABASE_PATH", "database/database.db")
    NOTIFICATION_BATCH_TIME = int(os.getenv("NOTIFICATION_BATCH_TIME", "300")) 
    NOTIFICATION_COOLDOWN = int(os.getenv("NOTIFICATION_COOLDOWN", "3600"))

    # Flag di stato runtime
    controllo_canali_attivo = False
    processo_invio = False
    invio = False
    check_admin = False
