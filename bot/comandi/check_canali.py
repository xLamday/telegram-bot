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
