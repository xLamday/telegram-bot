# main.py
"""
Main del bot Telegram (aggiornato per usare le nuove classi).
"""

import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ChatMemberHandler,
    ContextTypes,
    filters,
)
from telegram.error import TelegramError
from loggerinfo import LoggerInfo

# Import aggiornati delle classi/istanze che abbiamo creato
from config.settings import Settings
from database.connection import setup_database

# Moduli rifattorizzati
from comandi.cmd import ComandiBot
from funzioni.registra import RegistrazioneCanale
from funzioni.system import ChannelManager
from funzioni.scheduledfunzioni import BotMonitor

logger = LoggerInfo(name="main").get_logger()

# ====================== ERROR HANDLER ======================
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Gestione globale degli errori."""
    logger.error(f"❌ Errore non gestito: {context.error}")
    try:
        if update and getattr(update, "effective_message", None):
            await update.effective_message.reply_text(
                "⚠️ Si è verificato un errore interno. Riprova più tardi."
            )
    except TelegramError:
        # Evita ricorsione in caso di errori durante l'invio del messaggio di errore
        pass


# ====================== MAIN ======================
def main():
    """Inizializza e avvia il bot con i nuovi handler basati su classi."""
    # Init DB (setup tabelle / migrazioni)
    try:
        setup_database()
        logger.info("Database inizializzato correttamente.")
        
    except Exception as e:
        logger.critical(f"Errore durante init_db(): {e}")
        return

    # Crea le istanze delle classi che gestiscono la logica
    RegistrazioneCanali = RegistrazioneCanale()
    bot_monitor = BotMonitor()
    bot_commands = ComandiBot(bot_monitor=bot_monitor)

    channel_manager = ChannelManager()
    channel_manager.set_cmd_handler(bot_commands)

    # Crea l'applicazione
    app = ApplicationBuilder().token(Settings.TELEGRAM_TOKEN).post_init(on_startup).build()
    job_queue = app.job_queue

    # === HANDLER COMANDI ===
    # /start
    app.add_handler(CommandHandler("start", bot_commands.start))
    # /rimuovi <id>
    app.add_handler(CommandHandler("rimuovi", bot_commands.rimuovi))
    # /pubblica
    app.add_handler(CommandHandler("pubblica", bot_commands.cmd_pubblica))
    # /check_canali
    app.add_handler(CommandHandler("check_canali", bot_commands.check_canali))


    # === EVENTI CHAT MEMBER ===
    # Quando il bot viene rimosso / perde permessi
    app.add_handler(ChatMemberHandler(RegistrazioneCanali.handle_chat_member_update, chat_member_types=["my_chat_member"]))


    # app.add_handler(ChatMemberHandler(channel_manager.bot_rimosso, chat_member_types=["my_chat_member"]))
    # Quando il bot viene aggiunto come admin (registrazione automatica canali privati)
    # app.add_handler(ChatMemberHandler(RegistrazioneCanali.handle_chat_member_update, chat_member_types=["my_chat_member"]))

    # === MESSAGGI PRIVATI ===
    # Handler per ricevere il messaggio che deve essere inoltrato ai canali (stato pubblicazione)
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE, channel_manager.handle_forward_message))

    # === SCAN POST CANALE (codice privato) ===
    # Quando un canale pubblica un post (usato per rilevare il codice generato con /registra)
    # Filtra i post di canale (ChatType.CHANNEL)
    # app.add_handler(MessageHandler(filters.ChatType.CHANNEL & (~filters.COMMAND), channel_manager.scan_channel))

    # === JOBS PERIODICI ===
    try:
        # bot_monitor.check_bot_admin e check_post_eliminati sono metodi async dell'istanza
        job_queue.run_once(bot_monitor.check_bot_admin, when=10)
        job_queue.run_repeating(bot_monitor.check_bot_admin, interval=3600)
        job_queue.run_repeating(bot_monitor.check_post_eliminati, interval=60, first=15)
        logger.info("Job periodici avviati con successo.")
    except Exception as e:
        logger.warning(f"Errore nell’avvio dei job periodici: {e}")

    # === ERROR HANDLER GLOBALE ===
    app.add_error_handler(error_handler)

    # === AVVIO POLLING ===
    logger.info("🚀 Avvio del bot...")
    try:
        app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
        # all'avvio
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Arresto del bot richiesto dall’utente.")
    except Exception as e:
        logger.critical(f"Errore critico durante run_polling(): {e}")

async def on_startup(app):
    bot = await app.bot.get_me()
    app.bot_data["bot_id"] = bot.id
    
    logger.info(f"🤖 Bot avviato correttamente")
    logger.info(f"🆔 ID BOT: {bot.id}")
    logger.info(f"👤 Username: @{bot.username}")
    logger.info(f"🆚 Versione del bot: 2.1.1")

if __name__ == "__main__":
    main()
