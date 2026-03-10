"""bot/comandi/pubblica.py"""
from __future__ import annotations

import traceback
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from telegram import Bot, Message, Update
from telegram.ext import ContextTypes

from database.session import AsyncSessionLocal
from database.repository import CanaleRepository, MessaggioRepository, LogEventoRepository
from shared.logger import LoggerInfo

logger = LoggerInfo(name="cmd.pubblica").get_logger()


# ── Risultato ─────────────────────────────────────────────────────────────────
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


# ── Funzione core ─────────────────────────────────────────────────────────────
async def pubblica_su_canali(
    bot: Bot,
    testo: Optional[str] = None,
    foto_file_id: Optional[str] = None,
    video_file_id: Optional[str] = None,
    caption: Optional[str] = None,
) -> RisultatoBroadcast:


    if not testo and not foto_file_id and not video_file_id:
        logger.debug("STEP 1 — ABORT: nessun contenuto fornito")
        raise ValueError("Almeno un contenuto tra testo, foto o video è obbligatorio.")

    # STEP 2 — stato istanza Bot
    try:
        logger.debug("STEP 2 — stato bot",
             token_presente=bool(getattr(bot, "token", None)),
             initialized=getattr(bot, "_initialized", "n/a"),
             running=getattr(bot, "_running", "n/a"),
        )
    except Exception as e:
        logger.error(f"STEP 2 — errore lettura stato bot {e}")

    ok, fail = 0, 0

    try:
        async with AsyncSessionLocal() as db:
            logger.info("STEP 3 — sessione DB aperta")

            # STEP 4 — recupero canali
            logger.info("STEP 4 — recupero canali attivi")
            canali = await CanaleRepository(db).get_attivi()
            logger.info(f"STEP 4 — canali trovati. n={len(canali)} nomi={[c.nome for c in canali]}, telegram_ids={[c.telegram_id for c in canali]}")

            if not canali:
                logger.error("STEP 4 — ABORT: nessun canale attivo")
                return RisultatoBroadcast(ok=0, fail=0)

            msg_repo = MessaggioRepository(db)
            log_repo = LogEventoRepository(db)

            for idx, canale in enumerate(canali):
                logger.info(f"STEP 5.{idx} — inizio invio, {canale.nome} {canale.telegram_id}")
                try:
                    # STEP 5 — chiamata effettiva a Telegram
                    if testo:
                        logger.info(f"STEP 5.{idx} — bot.send_message {canale.telegram_id} {testo[:80]}",)
                        sent = await bot.send_message(
                            chat_id=canale.telegram_id,
                            text=testo,
                        )
                    # elif foto_file_id:
                    #     _dbg(f"STEP 5.{idx} — bot.send_photo",
                    #          chat_id=canale.telegram_id,
                    #          file_id=foto_file_id,
                    #     )
                    #     sent = await bot.send_photo(
                    #         canale.telegram_id, foto_file_id, caption=caption
       # WIP        #     )
                    # elif video_file_id:
                    #     _dbg(f"STEP 5.{idx} — bot.send_video",
                    #          chat_id=canale.telegram_id,
                    #          file_id=video_file_id,
                    #     )
                    #     sent = await bot.send_video(
                    #         canale.telegram_id, video_file_id, caption=caption
                    #     )

                    logger.info(f"STEP 5.{idx} — ✅ invio riuscito, {sent.message_id}, {sent.chat_id}",)
                    await log_repo.log(
                            "SUCCESS", "pubblica",
                            f"Messaggio inviato con successo su {canale.nome} ({canale.telegram_id})",
                        )
                    # STEP 6 — aggiornamento DB
                    logger.info(f"STEP 6.{idx} — salvataggio nel DB")
                    msg = await msg_repo.crea(
                        testo=testo or caption,
                        canale_id=canale.id,
                    )
                    await msg_repo.segna_pubblicato(msg.id, sent.message_id)
                    logger.info(f"STEP 6.{idx} — ✅ DB aggiornato, msg_id={msg.id}")
                    ok += 1

                except Exception as e:
                    fail += 1
                    tb = traceback.format_exc()
                    logger.error(f"STEP 5.{idx} — ❌ ECCEZIONE, tipo:{type(e).__name__}, messaggio={str(e)}, traceback={tb}")
                    try:
                        await log_repo.log(
                            "ERROR", "pubblica",
                            f"Errore su {canale.nome} ({canale.telegram_id}): {e}",
                        )
                    except Exception as log_err:
                        logger.error(f"STEP 5.{idx} — anche il log ha fallito, errore{str(log_err)}")
                    logger.error(f"Errore su {canale.nome}: {e}\n{tb}")

    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"STEP 3 — ❌ ECCEZIONE nel blocco DB principale | tipo={type(e).__name__}, messaggio={str(e)}, traceback={tb}")
        raise

    # STEP 7 — risultato finale
    logger.info(f"STEP 7 — completato ok={ok}, fail={fail}")
    return RisultatoBroadcast(ok=ok, fail=fail)


# ── Handler /pubblica ─────────────────────────────────────────────────────────
async def pubblica_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pubblica il messaggio a cui si risponde su tutti i canali attivi."""
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "↩️ Rispondi a un messaggio con /pubblica per pubblicarlo sui canali."
        )
        return

    original: Message = update.message.reply_to_message

    if original.text:
        kwargs = dict(testo=original.text)
    elif original.photo:
        kwargs = dict(foto_file_id=original.photo[-1].file_id, caption=original.caption)
    elif original.video:
        kwargs = dict(video_file_id=original.video.file_id, caption=original.caption)
    else:
        await update.message.reply_text("⚠️ Tipo di messaggio non supportato.")
        return

    async with AsyncSessionLocal() as db:
        canali = await CanaleRepository(db).get_attivi()
    if not canali:
        await update.message.reply_text("❌ Nessun canale attivo registrato.")
        return

    risultato = await pubblica_su_canali(bot=context.bot, **kwargs)
    await update.message.reply_text(str(risultato))
