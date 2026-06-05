"""
Application settings and configuration.
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    """Bot settings."""
    
    TELEGRAM_TOKEN = "8477419835:AAE1mVmAc9TQ6T8lQ0itd3DRInLTtRAyv3g"
    ADMIN_ID = 961492841
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'database/database.db')
    CANALE_CONTROLLO = -1002900201712
    controllo_canali_attivo = False
    processo_invio = False
    invio = False
    check_admin = False