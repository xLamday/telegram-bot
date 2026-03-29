# bot_commands.py
import asyncio
from telegram import Update
from telegram.ext import ContextTypes, filters
from loggerinfo import LoggerInfo
from funzioni.system import ChannelManager
from funzioni.scheduledfunzioni import BotMonitor
from config.settings import Settings
from database.manager import DatabaseManager
from utils import rate_limiter

class ComandiBot:
    """Gestisce tutti i comandi del bot Telegram."""

    def __init__(self, bot_monitor: BotMonitor):
        self.publishing_state = {}
        self.system = ChannelManager()
        self.botmonitor = bot_monitor
        self.logger = LoggerInfo(name="ComandiBot").get_logger()
        self.logger.info(f"🧠 ComandiBot collegato a BotMonitor {id(self.botmonitor)}")
        self.reset_tasks = {}

    # ------------------ START ------------------
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Messaggio di benvenuto con istruzioni."""
        text = (
            "👋 Ciao!\n\n"
            "➡️ /registra genererà un codice da inviare all'admin del canale che si vuole registrare.\n"
            "L'admin dovrà inserire quel codice per completare la registrazione.\n"
            "➡️ Per canali privati: basta inserire il bot come admin nel canale dove si vuole registrare, "
            "il bot rileverà automaticamente.\n"
            "➡️ /rimuovi <link o ID> per rimuovere un canale.\n"
            "➡️ /pubblica per inoltrare un messaggio a tutti i canali privati registrati.\n"
            "➡️ /check_duplicati per controllare se ci sono post duplicati nel database.\n"
            "➡️ /check_rate per controllare le statistiche su log del RateLimiter.\n"
            "➡️ /pulisci_duplicati per rimuovere i post duplicati dal database.\n"
            "➡️ /check_canali per controllare se i canali privati sono registrati e se i post sono stati inoltrati correttamente."
        )
        await update.message.reply_text(text)

    # ------------------ CHECK DUPLICATI ------------------
    async def check_duplicati(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Controlla se ci sono post duplicati nel database senza eliminarli."""
        try:
            with DatabaseManager() as db:
                duplicati = db.post.get_duplicate_posts()
                if not duplicati:
                    await update.message.reply_text("✅ Nessun post duplicato trovato.")
                    return
                
                text = f"⚠️ Trovati duplicati in {len(duplicati)} canali:\n\n"
                for channel_chat_id, count, title in duplicati:
                    nome = title if title else channel_chat_id
                    text += f"• Canale con titolo '{nome}' ha {count} post duplicati\n"
                text += "\nUsa /pulisci_duplicati per rimuoverli."
                await update.message.reply_text(text)
        except Exception as e:
            self.logger.error(f"Errore controllo duplicati: {e}")
            await update.message.reply_text(f"❌ Errore controllo duplicati: {e}")

    # ------------------ PULISCI DUPLICATI ------------------
    async def pulisci_duplicati(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Pulisce i post duplicati dal database."""
        try:
            with DatabaseManager() as db:
                deleted_count = db.post.remove_duplicate_posts()
                if deleted_count > 0:
                    await update.message.reply_text(f"✅ Rimossi {deleted_count} post duplicati.")
                else:
                    await update.message.reply_text("❌ Nessun post duplicato da rimuovere.")
        except Exception as e:
            self.logger.error(f"Errore pulizia duplicati: {e}")
            await update.message.reply_text(f"❌ Errore pulizia duplicati: {e}")

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

    # ------------------ CHECK RATE ------------------
    async def check_rate(self, update: Update,context: ContextTypes.DEFAULT_TYPE):
        try:
            await rate_limiter.log_stats(context)
        except Exception as errore:
            self.logger.info(f"Errore riscontrato: {errore}")


    # ------------------ PUBBLICA ------------------
    async def cmd_pubblica(self, update: Update, context: ContextTypes.DEFAULT_TYPE, timeout: int = 60):
        """Abilita lo stato di pubblicazione per un utente e resetta dopo timeout."""
        user_id = update.effective_user.id
        if user_id in self.reset_tasks and not self.reset_tasks[user_id].done():
            self.reset_tasks[user_id].cancel()
        
        self.publishing_state[user_id] = True
        Settings.invio = True
        await update.message.reply_text("Inoltra ora il messaggio da pubblicare nei canali privati.")
        self.logger.info(f"Utente {user_id} ha iniziato la pubblicazione. Stato invio: {Settings.invio}")

        # Reset automatico dopo timeout
        async def reset_state():
            try:
             await asyncio.sleep(timeout)
             if self.publishing_state.get(user_id, False):
                 self.publishing_state[user_id] = False
                 Settings.invio = False
                 self.logger.info(f"Stato pubblicazione reset per utente {user_id}. Stato invio: {Settings.invio}")
                 await update.message.reply_text("Hai impiegato troppo tempo per inviare il messaggio!")
                 if user_id in self.reset_tasks:
                        del self.reset_tasks[user_id]
            except asyncio.CancelledError:
                self.logger.info(f"Task di reset cancellato per utente {user_id} (messaggio inviato in tempo)")
                Settings.invio = False
                Settings.processo_invio = False
            except Exception as e:
                self.logger.error(f"Errore nel reset dello stato di pubblicazione per utente {user_id}: {e}")
            # Salva il task nel dizionario
        self.reset_tasks[user_id] = asyncio.create_task(reset_state())
