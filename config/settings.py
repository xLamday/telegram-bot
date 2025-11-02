"""
Application settings and configuration.
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    """Bot settings."""
    
    TELEGRAM_TOKEN = os.getenv('TOKEN')
    ADMIN_ID = os.getenv('ADMIN_ID')
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'database/database.db')
    CANALE_CONTROLLO = os.getenv('CANALE_CONTROLLO_ID')
    processo_invio = False
    invio = False
    CODE_VALIDITY = 10 * 60 # TEMPO DI VALIDITA' DEL CODICE (10 * 60 = 10 MINUTI)
    DELAY = 5