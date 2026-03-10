"""bot/comandi/pubblica.py"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from telegram import Bot, Message, Update
from telegram.ext import ContextTypes

from database.session import AsyncSessionLocal
from database.repository import CanaleRepository, MessaggioRepository, LogEventoRepository
from shared.logger import get_logger

logger = get_logger("bot.pubblica")


# ---------------------------------------------------------------------------
# Risultato restituito da pubblica_su_canali()
# ---------------------------------------------------------------------------
@dataclass
class RisultatoBroadcast:
    ok: int
    fail: int

    @property
    def totale(self) -> int:
        return self.ok + self.fail

    def __str__(self) -> str:
        parts = [f"✅ Pubblicato su {self.ok} canali."]
        if self.fail:
            parts.append(f"❌ {self.fail} errori.")
        return " ".join(parts)


# ---------------------------------------------------------------------------
# Funzione core — usata sia dal comando /pubblica sia dal web panel
# ---------------------------------------------------------------------------
async def pubblica_su_canali(
    bot: Bot,
    testo: Optional[str] = None,
    foto_file_id: Optional[str] = None,
    video_file_id: Optional[str] = None,
    caption: Optional[str] = None,
) -> RisultatoBroadcast:
    """
    Invia un messaggio (testo, foto o video) a tutti i canali attivi.

    Parametri
    ---------
    bot           : istanza Bot di python-telegram-bot
    testo         : testo puro da inviare (mutualmente esclusivo con foto/video)
    foto_file_id  : file_id di una foto Telegram
    video_file_id : file_id di un video Telegram
    caption       : didascalia per foto/video

    Ritorna
    -------
    RisultatoBroadcast con i contatori ok/fail
    """
    if not testo and not foto_file_id and not video_file_id:
        raise ValueError("Almeno un contenuto tra testo, foto o video è obbligatorio.")

    ok, fail = 0, 0

    async with AsyncSessionLocal() as db:
        canali = await CanaleRepository(db).get_attivi()
        msg_repo = MessaggioRepository(db)
        log_repo = LogEventoRepository(db)

        for canale in canali:
            try:
                if testo:
                    sent = await bot.send_message(chat_id=canale.telegram_id, text=testo)
                elif foto_file_id:
                    sent = await bot.send_photo(canale.telegram_id, foto_file_id, caption=caption)
                elif video_file_id:
                    sent = await bot.send_video(canale.telegram_id, video_file_id, caption=caption)

                # Salva nel DB con esito positivo
                msg = await msg_repo.crea(
                    testo=testo or caption,
                    canale_id=canale.id,
                )
                await msg_repo.segna_pubblicato(msg.id, sent.message_id)
                ok += 1

            except Exception as e:
                fail += 1
                await log_repo.log(
                    "ERROR", "pubblica",
                    f"Errore pubblicazione su {canale.nome} ({canale.telegram_id}): {e}",
                )
                logger.error(f"Errore su {canale.nome}: {e}")

    return RisultatoBroadcast(ok=ok, fail=fail)


# ---------------------------------------------------------------------------
# Handler comando /pubblica — risponde a un messaggio in chat
# ---------------------------------------------------------------------------
async def pubblica_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pubblica il messaggio a cui si risponde su tutti i canali attivi."""
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "↩️ Rispondi a un messaggio con /pubblica per pubblicarlo sui canali."
        )
        return

    original: Message = update.message.reply_to_message

    # Determina il tipo di contenuto
    if original.text:
        kwargs = dict(testo=original.text)
    elif original.photo:
        kwargs = dict(foto_file_id=original.photo[-1].file_id, caption=original.caption)
    elif original.video:
        kwargs = dict(video_file_id=original.video.file_id, caption=original.caption)
    else:
        await update.message.reply_text("⚠️ Tipo di messaggio non supportato.")
        return

    # Controlla che ci siano canali prima di procedere
    async with AsyncSessionLocal() as db:
        canali = await CanaleRepository(db).get_attivi()
    if not canali:
        await update.message.reply_text("❌ Nessun canale attivo registrato.")
        return

    risultato = await pubblica_su_canali(bot=context.bot, **kwargs)
    await update.message.reply_text(str(risultato))
