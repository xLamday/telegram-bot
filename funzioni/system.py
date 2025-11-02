import sqlite3
from telegram import *
from telegram.ext import *
import config
import random
from config import *
from telegram import Update
from telegram.ext import MessageHandler, filters
from telegram.error import RetryAfter
from helpers.helper import check_code, remove_code
import time
import asyncio

def add_channel(title: str, chat_id: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO channels (title, chat_id) VALUES (?, ?)",
            (title, chat_id),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def remove_channel(identifier: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # prima otteniamo il chat_id del canale da rimuovere
    if identifier.lstrip("-").isdigit():
        # è un chat_id
        c.execute("SELECT chat_id FROM channels WHERE chat_id=?", (identifier,))
    else:
        # è un titolo
        c.execute("SELECT chat_id FROM channels WHERE title=?", (identifier,))
    row = c.fetchone()

    if not row:
        conn.close()
        return False  # nessun canale trovato

    chat_id = row[0]

    # eliminiamo il canale
    if identifier.lstrip("-").isdigit():
        c.execute("DELETE FROM channels WHERE chat_id=?", (identifier,))
    else:
        c.execute("DELETE FROM channels WHERE title=?", (identifier,))

    # eliminiamo anche i post associati a quel canale
    c.execute("DELETE FROM posts WHERE channel_chat_id=?", (chat_id,))

    conn.commit()
    conn.close()
    return True

async def handle_forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not publishing_state.get(user_id):
        return

    publishing_state[user_id] = False  # reset stato

    # Usa sempre update.message per messaggi privati
    if not update.message:
        await update.effective_user.send_message("❌ Non ho ricevuto un messaggio valido.")
        return
    
    config.invio = False
    print(f"Stato invio: {config.invio}")
    chat_id_orig = update.message.chat.id
    msg_id_orig = update.message.message_id

    # Cicla i canali registrati
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT chat_id FROM channels")
    channels = c.fetchall()
    for (chat_id,) in channels:
        try:
            config.processo_invio = True
            await asyncio.sleep(DELAY + random.uniform(-0.5, 0.5))
            print(f"E' passato {DELAY} s dal vecchio messaggio! Invio il prossimo!")
            # Elimina vecchio post se esiste
            c.execute("SELECT forwarded_message_id FROM posts WHERE channel_chat_id=?", (chat_id,))
            old_post = c.fetchone()
            if old_post:
                try:
                    await context.bot.delete_message(chat_id=int(chat_id), message_id=old_post[0])
                except Exception:
                    pass

            # Copia il messaggio
            fwd_msg = await context.bot.copy_message(
                chat_id=int(chat_id),
                from_chat_id=chat_id_orig,
                message_id=msg_id_orig
            )

            # Salva nel DB
            c.execute(
                "REPLACE INTO posts (original_message_id, channel_chat_id, forwarded_message_id) VALUES (?, ?, ?)",
                (msg_id_orig, chat_id, fwd_msg.message_id)
            )
        except RetryAfter as errore:
            print(f"Ricevuto Retry: attendere {errore.retry_after} secondi")
            await asyncio.sleep(errore.retry_after + 1)

    conn.commit()
    conn.close()
    await update.message.reply_text("Messaggio pubblicato nei canali privati.")
    config.processo_invio = False

async def bot_rimosso(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_member_update = update.my_chat_member  # usiamo my_chat_member per canali privati
    bot_id = context.bot.id

    if not chat_member_update:
        return

    old_status = chat_member_update.old_chat_member.status
    new_status = chat_member_update.new_chat_member.status

    if chat_member_update.new_chat_member.user.id == bot_id:
        # se il bot ha perso accesso o è stato rimosso
        if old_status in ("administrator", "member") and new_status not in ("administrator", "member"):
            chat_id = chat_member_update.chat.id
            chat_title = chat_member_update.chat.title or "<no title>"

            # Rimuove i post associati a questo canale privato dal DB
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("DELETE FROM posts WHERE channel_chat_id=?", (chat_id,))
            conn.commit()
            conn.close()

            # Notifica l'admin
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"⚠️ Sono stato rimosso dal canale privato {chat_title} ({chat_id}) e tutti i post associati sono stati rimossi dal database."
            )

# async def scan_channel(update, context):
#     if not update.channel_post:  # assicurati che sia un post del canale
#         return

#     text = update.channel_post.text.strip()
#     # qui metti la logica del codice di verifica
#     admin_id = check_code(text)
#     if admin_id:
#         chat = update.channel_post.chat
#         remove_code(text)

#         # salva il canale nel DB
#         conn = sqlite3.connect(DB_FILE)
#         c = conn.cursor()
#         c.execute(
#             "INSERT OR REPLACE INTO channels (title, chat_id) VALUES (?, ?)",
#             (chat.title, str(chat.id))
#         )
#         conn.commit()
#         conn.close()

#         await context.bot.send_message(
#             chat_id=admin_id,
#             text=f"🎉 Canale registrato con successo!\nTitolo: {chat.title}\nID: {chat.id}"
#         )
#         await update.channel_post.reply_text("✅ Codice verificato, canale registrato!")
#     else:
#         pass
