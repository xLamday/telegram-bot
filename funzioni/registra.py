# channel_registrar.py
import asyncio
from telegram import ChatMemberUpdated
from telegram.ext import ContextTypes
from loggerinfo import LoggerInfo
from database.database import DatabaseManager
from config.settings import Settings
from funzioni.system import ChannelManager

class RegistrazioneCanale:
    """Classe per gestire la registrazione e rimozione dei canali privati."""

    def __init__(self):
        self.lock = asyncio.Lock()
        self.system = ChannelManager()
        self.logger = LoggerInfo(name="RegistrazioneCanale").get_logger()
    async def handle_chat_member_update(self, update: ChatMemberUpdated, context: ContextTypes.DEFAULT_TYPE):
        """Gestisce l'evento di aggiornamento dei permessi del bot in un canale."""
        cm = update.my_chat_member
        if not cm:
            return

        bot_id = context.bot.id
        chat = cm.chat
        chat_id = str(chat.id)
        chat_title = chat.title or "<senza nome>"

        old_status = cm.old_chat_member.status
        new_status = cm.new_chat_member.status
        user_id = cm.new_chat_member.user.id

        if user_id != bot_id:
            return

        # Se il bot diventa admin/creator
        if new_status in ("administrator", "creator") and old_status not in ("administrator", "creator"):
            await self._register_channel(chat_id, chat_title, context)

        # Se il bot perde i permessi o viene rimosso
        if old_status in ("administrator", "member") and new_status not in ("administrator", "member"):
            await self._remove_channel(chat_id, chat_title, context)

    async def _register_channel(self, chat_id: str, chat_title: str, context: ContextTypes.DEFAULT_TYPE):
        """Registra un canale nel DB se non esiste già."""
        async with self.lock:
            with DatabaseManager() as db:
                esiste = db.channel_exists(chat_id)
                if esiste:
                    self.logger.info(f"Canale {chat_title} ({chat_id}) già registrato.")
                    return

                # Notifica nel canale
                try:
                    await context.bot.send_message(chat_id=int(chat_id), text="✅ Sono admin, aggiungo il canale...")
                    self.system.add_channel(chat_title, chat_id)
                except Exception as e:
                    self.logger.warning(f"Impossibile inviare messaggio nel canale {chat_id}: {e}")

                # Aggiunge il canale al DB
                db.add_channel(chat_id, chat_title)
                # Notifica admin
                await context.bot.send_message(
                    chat_id=Settings.ADMIN_ID,
                    text=f"📢 Canale registrato!\nTitolo: {chat_title}\nID: {chat_id}"
                )
                self.logger.info(f"Registrato canale {chat_title} ({chat_id})")

    async def _remove_channel(self, chat_id: str, chat_title: str, context: ContextTypes.DEFAULT_TYPE):
        """Rimuove un canale dal DB e notifica l'admin."""
        async with self.lock:
            self.system.remove_channel(chat_id)  # Funzione locale che gestisce la rimozione dal DB

            with DatabaseManager() as db:
                db.delete_channel(chat_id)

            await context.bot.send_message(
                chat_id=Settings.ADMIN_ID,
                text=f"⚠️ Sono stato rimosso o ho perso i permessi dal canale {chat_title} ({chat_id}).\n"
                     "Il canale e i post associati sono stati rimossi dal database."
            )
            self.logger.info(f"Rimosso canale {chat_title} ({chat_id}) dal DB")
