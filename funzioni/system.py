# channel_manager.py
import asyncio
import random
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import RetryAfter
from loggerinfo import LoggerInfo
from config.settings import Settings
from database.database import DatabaseManager

DELAY = 2  # default delay tra invii

class ChannelManager:
    """Gestione canali, invio messaggi e rimozioni."""

    def __init__(self, comandi_bot=None):
        self.publishing_state = {}
        self.processo_lock = asyncio.Lock()
        self.logger = LoggerInfo(name="ChannelManager").get_logger()
        self.reset_tasks = {}
        self.comandi_bot = comandi_bot
        self.logger.info(f"ComandiBot collegato a ChannelManager {id(self.comandi_bot)}")

    # ------------------ ADD / REMOVE CHANNEL ------------------
    def add_channel(self, title: str, chat_id: str) -> bool:
        with DatabaseManager() as db:
            if db.channel_exists(chat_id):
                return False
            db.add_channel(chat_id, title)
            return True

    def remove_channel(self, identifier: str) -> bool:
        with DatabaseManager() as db:
            if identifier.lstrip("-").isdigit():
                # chat_id
                if not db.channel_exists(identifier):
                    return False
                db.delete_channel(identifier)
                return True

    def set_cmd_handler(self, comandi_bot):
        """Imposta il riferimento al command handler dopo l'inizializzazione."""
        self.comandi_bot = comandi_bot
        self.logger.info("✅ Command handler collegato a ChannelManager")

    # ------------------ HANDLE FORWARD MESSAGE ------------------
    async def handle_forward_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Inoltra il messaggio dell'utente a tutti i canali registrati."""
        user_id = update.effective_user.id
        if not self.comandi_bot.publishing_state.get(user_id, False):
            self.logger.debug(f"Utente {user_id} non in stato pubblicazione, ignoro messaggio")
            return
         # reset stato
        if not update.message:
            await update.effective_user.send_message("❌ Non ho ricevuto un messaggio valido.")
            return

        chat_id_orig = update.message.chat.id
        msg_id_orig = update.message.message_id

        async with self.processo_lock:
            Settings.invio = True
            Settings.processo_invio = True
            self.logger.info(f"Inizio invio messaggi dall'admin")

            with DatabaseManager() as db:
                canali = db.fetch_all_channels()

                for chat_id, _ in canali:
                    try:
                        await asyncio.sleep(DELAY + random.uniform(-0.5, 0.5))

                        # elimina vecchio post se presente
                        old_posts = db.fetch_all_posts()
                        for o_chat_id, fwd_id, _ in old_posts:
                            if o_chat_id == chat_id:
                                try:
                                    await context.bot.delete_message(chat_id=int(chat_id), message_id=fwd_id)
                                    db.delete_post(chat_id, fwd_id)
                                    self.logger.info(f"Post {fwd_id} eliminato da {chat_id} e rimosso dal DB")
                                except Exception:
                                    pass

                        # copia il messaggio
                        fwd_msg = await context.bot.forward_message(
                            chat_id=int(chat_id),
                            from_chat_id=chat_id_orig,
                            message_id=msg_id_orig
                        )

                        self.logger.info(F"Connessione al database in corso...")
                        db.upsert_post(msg_id_orig, chat_id, fwd_msg.message_id)
                    except RetryAfter as e:
                        self.logger.warning(f"Rate limit: attendere {e.retry_after} secondi")
                        await asyncio.sleep(e.retry_after + 1)
                    except Exception as e:
                        self.logger.error(f"Errore inoltrando messaggio al canale {chat_id}: {e}")
                        # Resetta comunque lo stato in caso di errore
                        if user_id in self.comandi_bot.reset_tasks:
                            task = self.comandi_bot.reset_tasks[user_id]
                            if not task.done():
                                task.cancel()
                            del self.comandi_bot.reset_tasks[user_id]
                        
                        self.comandi_bot.publishing_state[user_id] = False
                        Settings.invio = False
                        await update.message.reply_text(f"❌ Errore nella pubblicazione: {e}")
            if user_id in self.comandi_bot.reset_tasks:
                task = self.comandi_bot.reset_tasks[user_id]
                if not task.done():
                    task.cancel()
                    self.logger.info(f"✅ Task di timeout cancellato per utente {user_id}")
                    del self.comandi_bot.reset_tasks[user_id]

            Settings.invio = False
            Settings.processo_invio = False
            self.comandi_bot.publishing_state[user_id] = False
            await update.message.reply_text("Messaggio pubblicato nei canali privati.")
            self.logger.info("Invio completato a tutti i canali registrati.")

    # ------------------ BOT RIMOSSO ------------------
    async def bot_rimosso(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestisce la rimozione del bot dai canali privati."""
        chat_member_update = update.my_chat_member
        if not chat_member_update:
            return

        bot_id = context.bot.id
        old_status = chat_member_update.old_chat_member.status
        new_status = chat_member_update.new_chat_member.status
        user_id = chat_member_update.new_chat_member.user.id

        if user_id != bot_id:
            return

        if old_status in ("administrator", "member") and new_status not in ("administrator", "member"):
            chat_id = chat_member_update.chat.id
            chat_title = chat_member_update.chat.title or "<no title>"

            # rimuove post associati
            with DatabaseManager() as db:
                db.delete_channel(chat_id)

            # notifica admin
            await context.bot.send_message(
                chat_id=Settings.ADMIN_ID,
                text=f"⚠️ Sono stato rimosso dal canale privato {chat_title} ({chat_id}) "
                     "e tutti i post associati sono stati rimossi dal database."
            )
            self.logger.info(f"Bot rimosso dal canale {chat_title} ({chat_id}) e dati eliminati.")

    # ------------------ SCAN CHANNEL (CODICE PRIVATO) ------------------
    # async def scan_channel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    #     """Verifica un codice nel post del canale privato e registra il canale."""
    #     if not update.channel_post:
    #         return

    #     text = (update.channel_post.text or "").strip()
    #     admin_id = check_code(text)
    #     if not admin_id:
    #         return

    #     chat = update.channel_post.chat
    #     remove_code(text)

    #     with DatabaseManager() as db:
    #         db.add_channel(chat.id, chat.title)

    #     await context.bot.send_message(
    #         chat_id=admin_id,
    #         text=f"🎉 Canale registrato con successo!\nTitolo: {chat.title}\nID: {chat.id}"
    #     )
    #     await update.channel_post.reply_text("✅ Codice verificato, canale registrato!")
    #     logger.info(f"Canale privato registrato: {chat.title} ({chat.id})")
