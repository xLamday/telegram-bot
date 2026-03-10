"""
bot/main.py
Entry point del bot Telegram.
Si integra con FastAPI notificando il suo stato online/offline.
"""

import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import asyncio
import requests
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ChatMemberHandler

from shared.config import bot_config, web_config
from shared.logger import get_logger
from database.session import init_db_async

logger = get_logger("bot")

API_BASE = f"http://127.0.0.1:{web_config.FASTAPI_PORT}"


def notify_api(endpoint: str):
    """Notifica FastAPI (ignora errori se l'API non è avviata)."""
    try:
        requests.post(f"{API_BASE}{endpoint}", timeout=2)
    except Exception:
        pass


async def post_init(application: Application):
    """Chiamato dopo l'avvio del bot."""
    await init_db_async()
    notify_api("/api/bot/online")
    logger.info("Bot avviato e database inizializzato.")


async def post_shutdown(application: Application):
    notify_api("/api/bot/offline")
    logger.info("Bot spento.")


def main():
    if not bot_config.TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN non impostato nel file .env!")
        return

    # Import handlers dopo l'inizializzazione
    from bot.comandi.start import start_handler
    from bot.comandi.pubblica import pubblica_handler
    from bot.comandi.rimuovi import rimuovi_handler
    from bot.comandi.check_canali import check_canali_handler
    from bot.funzioni.gestione_canali import channel_member_handler
    from bot.funzioni.registrazione import messaggio_privato_handler

    app = (
        Application.builder()
        .token(bot_config.TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("pubblica", pubblica_handler))
    app.add_handler(CommandHandler("rimuovi", rimuovi_handler))
    app.add_handler(CommandHandler("check_canali", check_canali_handler))
    app.add_handler(ChatMemberHandler(channel_member_handler, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & ~filters.COMMAND, messaggio_privato_handler))

    logger.info("Bot in ascolto...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
