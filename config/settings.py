"""
Application settings and configuration.
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    """Bot settings."""
    
    TELEGRAM_TOKEN = "8214983217:AAFBWblz_aAG80uwwKspLcNhZ9_zfHbMMFQ"
    ADMIN_ID = 961492841
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'database/database.db')
    CANALE_CONTROLLO = -1002900201712
    controllo_canali_attivo = False
    processo_invio = False
    invio = False
    CODE_VALIDITY = 10 * 60 # TEMPO DI VALIDITA' DEL CODICE (10 * 60 = 10 MINUTI)
    DELAY = 5