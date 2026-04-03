"""
Application settings and configuration.
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    """Bot settings."""
    
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    ADMIN_ID = int(os.getenv("ADMIN_ID"))
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'database/database.db')
    CANALE_CONTROLLO = os.getenv("CANALE_CONTROLLO")
    controllo_canali_attivo = False
    processo_invio = False
    invio = False
    CODE_VALIDITY = os.getenv("CODE_VALIDITY")
    DELAY = os.getenv("DELAY")