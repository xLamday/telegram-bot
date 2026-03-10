"""bot/comandi/rimuovi.py"""
from telegram import Update
from telegram.ext import ContextTypes
from database.session import AsyncSessionLocal
from database.repository import CanaleRepository


async def rimuovi_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /rimuovi <telegram_id_canale>")
        return
    try:
        canale_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID non valido.")
        return

    async with AsyncSessionLocal() as db:
        ok = await CanaleRepository(db).disattiva(canale_id)
    if ok:
        await update.message.reply_text(f"✅ Canale {canale_id} disattivato.")
    else:
        await update.message.reply_text("❌ Canale non trovato.")


# ──────────────────────────────────────────────────────────────────────────────

"""bot/comandi/check_canali.py"""
from telegram import Update
from telegram.ext import ContextTypes
from database.session import AsyncSessionLocal
from database.repository import CanaleRepository


async def check_canali_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with AsyncSessionLocal() as db:
        canali = await CanaleRepository(db).get_attivi()

    if not canali:
        await update.message.reply_text("Nessun canale attivo registrato.")
        return

    lines = ["📢 <b>Canali attivi:</b>\n"]
    for c in canali:
        tag = f"@{c.username}" if c.username else str(c.telegram_id)
        lines.append(f"• {c.nome} ({tag})")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")
