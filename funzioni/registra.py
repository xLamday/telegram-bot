from telegram import ChatMemberUpdated, ChatMember
from telegram.ext import ContextTypes
from config import *
from funzioni.system import *
from loggerinfo import logger


# -- REGISTRA CANALI PRIVATI --
async def registra_channel_post(update: ChatMemberUpdated, context: ContextTypes.DEFAULT_TYPE):
    
    cm = update.my_chat_member
    if not cm:
        return

    bot_id = context.bot.id
    chat = cm.chat
    chat_id = str(chat.id)
    chat_titolo = chat.title or "<senza nome>"

    old_status = cm.old_chat_member.status
    new_status = cm.new_chat_member.status
    user_id = cm.new_chat_member.user.id

    if user_id != bot_id:
        return

    if new_status in ("administrator", "creator") and old_status not in ("administrator", "creator"):
        connessione = sqlite3.connect(DB_FILE)
        cursore =  connessione.cursor()
        cursore.execute("SELECT * FROM channels where chat_id=?", (chat_id,))
        esiste = cursore.fetchone()
        if esiste:
            connessione.close()
            return

        messaggio = await context.bot.send_message(chat_id=chat.id, text="Sono admin, aggiungo il canale...")

        cursore.execute("INSERT INTO channels (chat_id, title) VALUES (?, ?)", (chat_id, chat.title))
        connessione.commit()
        connessione.close()

        await context.bot.send_message(ADMIN_ID, f"Canale con ID: {chat_id} e nome: {chat.title} è stato registrato!")

    if old_status in ("administrator", "member") and new_status not in ("administrator", "member"):
        remove_channel(chat_id)
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"⚠️ Sono stato rimosso o ho perso i permessi dal canale {chat_titolo} ({chat_id}).\n"f"Il canale e i post associati sono stati rimossi dal database.")
        return

    
    
    
    # Verifica che sia effettivamente un channel_post
    # if not update.channel_post:
    #     return

    # chat = update.channel_post.chat
    # chat_id = str(chat.id)
    # username = chat.username
    # title = chat.title or "<no title>"
    # link = f"{chat_id}"

    # if add_channel(link, chat_id):
    #     try:
    #         await context.bot.send_message(chat_id=chat_id, text="✅ Questo canale è stato registrato correttamente!")
    #     except Exception:
    #         pass
    #     await context.bot.send_message(
    #         chat_id=ADMIN_ID,
    #         text=f"📢 Nuovo canale registrato automaticamente!\nTitolo: {title}\nID: {chat_id}\nUsername: {username}"
    #     )
    #     logger.info(f"Registrato canale {title} ({chat_id}) automaticamente.")
    # else:
    #     logger.info(f"Canale {title} ({chat_id}) già registrato.")