# bot_commands.py
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from loggerinfo import LoggerInfo
from funzioni.system import ChannelManager
from funzioni.scheduledfunzioni import BotMonitor
from config.settings import Settings

class ComandiBot:
    """Gestisce tutti i comandi del bot Telegram."""

    def __init__(self, bot_monitor: BotMonitor):
        self.publishing_state = {}
        self.system = ChannelManager()
        self.botmonitor = bot_monitor
        self.logger = LoggerInfo(name="ComandiBot").get_logger()
        self.logger.info(f"🧠 ComandiBot collegato a BotMonitor {id(self.botmonitor)}")

    # ------------------ START ------------------
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Messaggio di benvenuto con istruzioni."""
        text = (
            "👋 Ciao!\n\n"
            "➡️ /registra genererà un codice da inviare all'admin del canale che si vuole registrare.\n"
            "L'admin dovrà inserire quel codice per completare la registrazione.\n"
            "➡️ Per canali privati: basta pubblicare un messaggio nel canale dove sono admin, "
            "il bot rileverà automaticamente.\n"
            "➡️ /rimuovi <link o ID> per rimuovere un canale.\n"
            "➡️ /pubblica per inoltrare un messaggio a tutti i canali privati registrati."
        )
        await update.message.reply_text(text)

    # ------------------ RIMUOVI CANALE ------------------
    async def rimuovi(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Rimuove un canale dal database."""
        if not context.args:
            await update.message.reply_text("Devi fornire il titolo o l'ID del canale da rimuovere.")
            return

        raw = context.args[0].strip()

        success = self.system.remove_channel(raw)
        if success:
            # Prova a notificare il canale rimosso
            try:
                if raw.lstrip("-").isdigit():
                    await context.bot.send_message(chat_id=int(raw), text="❌ Questo canale è stato rimosso dal registro.")
            except Exception:
                self.logger.warning(f"Impossibile inviare messaggio di rimozione al canale {raw}")
            await update.message.reply_text(f"✅ Canale e post associati rimossi: {raw}")
        else:
            await update.message.reply_text("⚠️ Questo canale non è presente nel database.")


    # ------------------ CHECK CANALE ------------------
    async def check_canali(self, update: Update,context: ContextTypes.DEFAULT_TYPE):
        try:
            await self.botmonitor.check_post_eliminati(context)
        except Exception as errore:
            self.logger.info(f"Errore riscontrato: {errore}")


    # ------------------ PUBBLICA ------------------
    async def cmd_pubblica(self, update: Update, context: ContextTypes.DEFAULT_TYPE, timeout: int = 120):
        """Abilita lo stato di pubblicazione per un utente e resetta dopo timeout."""
        user_id = update.effective_user.id
        self.publishing_state[user_id] = True
        await update.message.reply_text("Inoltra ora il messaggio da pubblicare nei canali privati.")
        self.logger.info(f"Utente {user_id} ha iniziato la pubblicazione. Stato invio: {Settings.invio}")

        # # Reset automatico dopo timeout
        # async def reset_state():
        #     await asyncio.sleep(timeout)
        #     self.publishing_state[user_id] = False
        #     Settings.invio = False
        #     logger.info(f"Stato pubblicazione reset per utente {user_id}. Stato invio: {Settings.invio}")

        # asyncio.create_task(reset_state())
