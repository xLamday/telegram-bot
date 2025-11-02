from telegram import ChatMember
from config import TOKEN, processo_invio
from funzioni.init_db import init_db
from comandi.cmd import start, rimuovi, cmd_pubblica, registra_pubblico, registra
from funzioni.registra import registra_channel_post
from funzioni.system import bot_rimosso, handle_forward_message
from funzioni.scheduledfunzioni import check_bot_admin, check_post_eliminati
from telegram.ext import (ApplicationBuilder,CommandHandler,MessageHandler,ChatMemberHandler, filters)

# === MAIN ===
def main():
    init_db() # - INIZIALIZZAZIONE DEL DATABASE! NON ELIMINARE, ALTRIMENTI IL BOT NON FUNZIONA!
    app = ApplicationBuilder().token(TOKEN).build()
    job_queue = app.job_queue
    app.initialize()

    # -- COMANDI INIZIALIZZATI DAL BOT!
    app.add_handler(CommandHandler("start", start))
    ##app.add_handler(CommandHandler("registra_pubblico", registra_pubblico)) -- WIP REWORK
    # app.add_handler(CommandHandler("registra", registra))
    app.add_handler(CommandHandler("rimuovi", rimuovi))
    app.add_handler(CommandHandler("pubblica", cmd_pubblica))
    app.add_handler(ChatMemberHandler(bot_rimosso, chat_member_types="my_chat_member"))


    # Registrazione handler
    app.add_handler(ChatMemberHandler(registra_channel_post, ChatMemberHandler.MY_CHAT_MEMBER))         

    # Funzione tempo reale se il bot viene rimosso da un canale.

    # gestione dei messaggi inviati dall'utente per /pubblica
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE, handle_forward_message)) 

    job_queue.run_repeating(check_bot_admin, interval=120, first=10) # OGNI 2 MINUTI
    job_queue.run_repeating(check_post_eliminati, interval=60, first=10)


    # avvia il bot
    app.run_polling()

if __name__ == "__main__":
    main()
