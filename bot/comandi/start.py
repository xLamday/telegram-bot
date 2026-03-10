"""
bot/comandi/start.py
Comando /start — registra l'utente nel DB tramite repository.
"""
from telegram import Update
from telegram.ext import ContextTypes
from database.session import AsyncSessionLocal
from database.repository import UtenteRepository, LogEventoRepository
from shared.logger import get_logger

logger = get_logger("bot.start")


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    async with AsyncSessionLocal() as db:
        repo = UtenteRepository(db)
        utente, created = await repo.get_or_create(
            telegram_id=user.id,
            username=user.username,
            nome=user.first_name,
            cognome=user.last_name,
        )
        log_repo = LogEventoRepository(db)
        if created:
            await log_repo.log("INFO", "bot", f"Nuovo utente registrato: {user.first_name} ({user.id})")
            logger.info(f"Nuovo utente: {user.id} @{user.username}")

    await update.message.reply_text(
        f"👋 Ciao, {user.first_name}!\n\n"
        "Sono il bot per la gestione dei canali.\n"
        "Aggiungimi come admin a un canale per iniziare.\n\n"
        "Comandi disponibili:\n"
        "/pubblica — pubblica un messaggio\n"
        "/check_canali — stato dei canali\n"
        "/rimuovi — rimuovi un canale"
    )
