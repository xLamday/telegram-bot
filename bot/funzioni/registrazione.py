"""
bot/funzioni/registrazione.py
Intercetta messaggi privati e li salva nel DB.
"""
from telegram import Update
from telegram.ext import ContextTypes
from database.session import AsyncSessionLocal
from database.repository import MessaggioRepository, UtenteRepository
from shared.logger import LoggerInfo

logger = LoggerInfo(name="bot.registrazione").get_logger()


async def messaggio_privato_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return

    user = update.effective_user

    async with AsyncSessionLocal() as db:
        utente_repo = UtenteRepository(db)
        msg_repo = MessaggioRepository(db)

        utente, _ = await utente_repo.get_or_create(
            telegram_id=user.id,
            username=user.username,
            nome=user.first_name,
            cognome=user.last_name,
        )

        # Determina tipo media
        tipo_media = None
        media_id = None
        if msg.photo:
            tipo_media = "photo"
            media_id = msg.photo[-1].file_id
        elif msg.video:
            tipo_media = "video"
            media_id = msg.video.file_id
        elif msg.document:
            tipo_media = "document"
            media_id = msg.document.file_id

        await msg_repo.crea(
            testo=msg.text or msg.caption,
            media_id=media_id,
            tipo_media=tipo_media,
            autore_id=utente.id,
        )
