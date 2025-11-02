import sqlite3
import time
import config
from config import DB_FILE, ADMIN_ID
from telegram.error import TelegramError, BadRequest, Forbidden
from telegram.ext import (ContextTypes)
from funzioni.system import remove_channel
from loggerinfo import logger
import asyncio

async def check_post_eliminati(context: ContextTypes.DEFAULT_TYPE):

    if config.processo_invio:
        print(f"Stato in check: {config.processo_invio}")
        print(f"Non fare il controllo, sto inviando nuovi post!")
        return
    else:
        pass

    if config.invio:
        print(f"Stato in check: {config.invio}")
        print(f"Non fare il controllo, sto per inviare nuovi post!")
        return
    else:
        pass

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT p.channel_chat_id, p.forwarded_message_id, c.title FROM posts p LEFT JOIN channels c ON p.channel_chat_id = c.chat_id")
    rows = c.fetchall()

   
    for chat_id, msg_id, title in rows:
        try:
            await asyncio.sleep(2)
            # proviamo a leggere il messaggio (edit_message_text come test)
            await context.bot.copy_message(
                chat_id=config.CANALE_CONTROLLO_ID,
                from_chat_id=int(chat_id),
                message_id=msg_id
            )
            print(f"Messaggio con ID: {msg_id} nel canale: {chat_id} è stato inviato al canale di controllo")
        except BadRequest as e:
            # se il messaggio non esiste, segnala admin e rimuovi dal D
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=f"⚠️ Il messaggio pubblicato nel canale {chat_id}, con nome: {title} è stato eliminato!"
                )

                # rimuovi dal DB
                # c.execute("DELETE FROM posts WHERE channel_chat_id=? AND forwarded_message_id=?",(chat_id, msg_id))

                c.execute("SELECT COUNT(*) FROM posts WHERE channel_chat_id=?", (chat_id,))
                count = c.fetchone()[0]

                # if count == 0:
                #     c.execute("DELETE FROM channels WHERE chat_id=?", (chat_id,))
                #     await context.bot.send_message(
                #         chat_id=ADMIN_ID,
                #         text=f"⚠️ Il canale {chat_id} è stato eliminato!"
                #     )
                # else:
                #      await context.bot.send_message(
                #         chat_id=ADMIN_ID,
                #         text=f"⚠️ Post eliminato dal canale {chat_id}, ma restano {count} post registrati."
                #     )
        except Forbidden:
                await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"⚠️ Non posso accedere al canale {chat_id}, potrebbe essere stato rimosso!"
            )
        except TelegramError:
            logger.warning(f"Errore verificando messaggio {msg_id} in {chat_id}: {e}")

    conn.commit()
    conn.close()

# --- Controllo periodico dei permessi admin
async def check_bot_admin(context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT chat_id, title FROM channels")
    rows = c.fetchall()
    conn.close()

    for chat_id, title in rows:
        try:
            await asyncio.sleep(5)
            admins = await context.bot.get_chat_administrators(int(chat_id))
            bot_admin = any(a.user.id == context.bot.id for a in admins)
            if not bot_admin:
                remove_channel(chat_id)
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=f"⚠️ Ho perso i permessi admin in un canale!\nID canale: {chat_id}"
                )
                    # Rimuove i post associati a questo canale privato dal DB
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute("DELETE FROM posts WHERE channel_chat_id=?", (chat_id,))
                conn.commit()
                conn.close()

                # Notifica l'admin
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=f"⚠️ Sono stato rimosso dal canale privato con ID: ({chat_id}) e tutti i post associati sono stati rimossi dal database."
                ) 
                
                logger.info(f"Bot rimosso da admin in canale {chat_id}, rimosso dal DB.")
        except BadRequest:
            await context.bot.send_message(
                 chat_id=ADMIN_ID,
                 text=f"⚠️ Non posso accedere al canale {chat_id} (Forbidden). Rimosso dal DB."
             )
            remove_channel(chat_id)
            logger.warning(f"Impossibile controllare canale {chat_id}")   
        except Forbidden:
            # Se non posso accedere, rimuovo comunque dal DB
            await context.bot.send_message(
                 chat_id=ADMIN_ID,
                 text=f"⚠️ Non posso accedere al canale {chat_id} (Forbidden). Rimosso dal DB."
             )
            remove_channel(chat_id)
            logger.warning(f"Impossibile controllare canale {chat_id}")   