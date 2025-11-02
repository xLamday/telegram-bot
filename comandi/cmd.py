import sqlite3 
import config
import asyncio
from config import *
from telegram import Update
from telegram.ext import ContextTypes
from helpers.helper import generate_code, save_code
from funzioni.system import add_channel, remove_channel


# === HANDLERS ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Ciao!\n\n"
        "➡️ /registra genererà un codice che dovrà essere poi inviato all'admin del canale che si vuole registrare, l'admin dovrà inserire quel codice per completare la registrazione!\n"
        "➡️ Per canali privati: basta pubblicare un messaggio nel canale dove sono admin, il bot rileverà automaticamente\n"
        "➡️ /rimuovi <link o ID> per rimuovere un canale\n"
        "➡️ /pubblica per inoltrare un messaggio a tutti i canali privati registrati"
    )


async def rimuovi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Devi fornire il titolo o l'ID del canale da rimuovere.")
        return

    raw = context.args[0].strip()

    if remove_channel(raw):
        try:
            if raw.lstrip("-").isdigit():
                await context.bot.send_message(chat_id=int(raw), text="❌ Questo canale è stato rimosso dal registro.")
        except Exception:
            pass

        await update.message.reply_text(f"✅ Canale e post associati rimossi: {raw}")
    else:
        await update.message.reply_text("⚠️ Questo canale non è presente nel database.")


# --- Comando /pubblica
async def cmd_pubblica(update: Update, context: ContextTypes.DEFAULT_TYPE):
    publishing_state[update.effective_user.id] = True
    await update.message.reply_text("Inoltra ora il messaggio da pubblicare nei canali privati.")
    config.invio = True
    print(f"Stato: {config.invio}")
    asyncio.sleep(120)
    config.invio = False

# --- Registrazione canali pubblici
async def registra_pubblico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Devi fornire il link o @username del canale pubblico.")
        return

    raw_input = context.args[0].strip()
    if raw_input.startswith("https://t.me/") or raw_input.startswith("http://t.me/"):
        username = raw_input.split("/")[-1]
        if not username.startswith("@"):
            username = "@" + username
        identifier = username
        link = raw_input
    else:
        identifier = raw_input
        link = raw_input

    try:
        chat = await context.bot.get_chat(identifier)
        username = chat.username
        chat_id = str(chat.id)

        if add_channel(link, username, chat_id):
            try:
                await context.bot.send_message(chat_id=chat.id, text="✅ Questo canale è stato registrato correttamente!")
            except Exception:
                pass
            await update.message.reply_text(f"Canale registrato!\nLink: {link}\nUsername: {username}\nID: {chat_id}")
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"📢 Nuovo canale registrato!\nLink: {link}\nUsername: {username}\nID: {chat_id}"
            )
        else:
            await update.message.reply_text("⚠️ Questo canale è già registrato.")
    except Exception as e:
        await update.message.reply_text(f"❌ Errore: {e}")


async def registra(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = generate_code()
    save_code(code, update.effective_user.id)
    await update.message.reply_text(
        f"✅ Codice generato!\nIncolla questo codice nel canale privato dove mi hai aggiunto admin:\n\n`{code}`",
        parse_mode="Markdown"
    )
