"""
bot/funzioni/gestione_canali.py
Aggiunta/rimozione bot dai canali — aggiorna il DB.
"""
from telegram import Update, ChatMemberUpdated
from telegram.ext import ContextTypes
from database.session import AsyncSessionLocal
from database.repository import CanaleRepository, LogEventoRepository
from shared.logger import get_logger
from shared.config import BotConfig

logger = get_logger("bot.canali")


def _estrai_status_change(member: ChatMemberUpdated):
    old = member.old_chat_member.status
    new = member.new_chat_member.status
    return old, new


async def channel_member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.my_chat_member
    if not result:
        return

    old_status, new_status = _estrai_status_change(result)
    chat = result.chat

    async with AsyncSessionLocal() as db:
        canale_repo = CanaleRepository(db)
        log_repo = LogEventoRepository(db)

        # Bot aggiunto come admin
        if new_status in ("administrator", "member") and old_status not in ("administrator", "member"):
            canale, created = await canale_repo.registra(
                telegram_id=chat.id,
                nome=chat.title or str(chat.id),
                username=chat.username,
            )
            if created:
                await log_repo.log("INFO", "bot", f"Nuovo canale registrato: {chat.title} ({chat.id})")
                logger.info(f"Canale aggiunto: {chat.title}")
                message = (
                "📢 <b>Nuovo canale registrato!</b>\n\n"
                f"📺 <b>Titolo:</b> {chat.title}\n"
                f"🆔 <b>ID:</b> <code>{chat.id}</code>\n\n"
                "Il canale è ora monitorato dal sistema."
                )
                await context.bot.send_message(chat_id=BotConfig.ADMIN_IDS, text=message, parse_mode="HTML")

        # Bot rimosso dal canale
        elif new_status in ("kicked", "left") and old_status in ("administrator", "member"):
            await canale_repo.disattiva(chat.id)
            await log_repo.log("WARNING", "bot", f"Bot rimosso dal canale: {chat.title} ({chat.id})")
            logger.warning(f"Rimosso dal canale: {chat.title}")
            await context.bot.send_message(chat_id=BotConfig.ADMIN_IDS, text=f"Bot rimosso dal canale {chat.title}", parse_mode="HTML")

