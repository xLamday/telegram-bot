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
from shared.logger import get_logger

logger = get_logger("bot.pubblica")


# ── Helper debug ──────────────────────────────────────────────────────────────
def _dbg(step: str, **kwargs):
    """Stampa un blocco debug nel terminale dove gira FastAPI / Bot."""
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    line = f"[DEBUG {ts}] ▶ {step}"
    for k, v in kwargs.items():
        line += f"\n          {k} = {v!r}"
    print(line, flush=True)
    logger.debug(line)


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

    # STEP 1 — parametri ricevuti
    _dbg("STEP 1 — pubblica_su_canali chiamata",
         testo=testo,
         foto_file_id=foto_file_id,
         video_file_id=video_file_id,
         caption=caption,
         bot_type=type(bot).__name__,
    )

    if not testo and not foto_file_id and not video_file_id:
        _dbg("STEP 1 — ABORT: nessun contenuto fornito")
        raise ValueError("Almeno un contenuto tra testo, foto o video è obbligatorio.")

    # STEP 2 — stato istanza Bot
    try:
        _dbg("STEP 2 — stato bot",
             token_presente=bool(getattr(bot, "token", None)),
             initialized=getattr(bot, "_initialized", "n/a"),
             running=getattr(bot, "_running", "n/a"),
        )
    except Exception as e:
        _dbg("STEP 2 — errore lettura stato bot", errore=str(e))

    ok, fail = 0, 0

    # STEP 3 — apertura sessione DB
    _dbg("STEP 3 — apertura AsyncSessionLocal")
    try:
        async with AsyncSessionLocal() as db:
            _dbg("STEP 3 — sessione DB aperta")

            # STEP 4 — recupero canali
            _dbg("STEP 4 — recupero canali attivi")
            canali = await CanaleRepository(db).get_attivi()
            _dbg("STEP 4 — canali trovati",
                 n=len(canali),
                 nomi=[c.nome for c in canali],
                 telegram_ids=[c.telegram_id for c in canali],
            )

            if not canali:
                _dbg("STEP 4 — ABORT: nessun canale attivo")
                return RisultatoBroadcast(ok=0, fail=0)

            msg_repo = MessaggioRepository(db)
            log_repo = LogEventoRepository(db)

            for idx, canale in enumerate(canali):
                _dbg(f"STEP 5.{idx} — inizio invio",
                     nome=canale.nome,
                     telegram_id=canale.telegram_id,
                )
                try:
                    # STEP 5 — chiamata effettiva a Telegram
                    if testo:
                        _dbg(f"STEP 5.{idx} — bot.send_message",
                             chat_id=canale.telegram_id,
                             text_preview=testo[:80],
                        )
                        sent = await bot.send_message(
                            chat_id=canale.telegram_id,
                            text=testo,
                        )
                    elif foto_file_id:
                        _dbg(f"STEP 5.{idx} — bot.send_photo",
                             chat_id=canale.telegram_id,
                             file_id=foto_file_id,
                        )
                        sent = await bot.send_photo(
                            canale.telegram_id, foto_file_id, caption=caption
                        )
                    elif video_file_id:
                        _dbg(f"STEP 5.{idx} — bot.send_video",
                             chat_id=canale.telegram_id,
                             file_id=video_file_id,
                        )
                        sent = await bot.send_video(
                            canale.telegram_id, video_file_id, caption=caption
                        )

                    _dbg(f"STEP 5.{idx} — ✅ invio riuscito",
                         message_id=sent.message_id,
                         chat_id=sent.chat_id,
                    )

                    # STEP 6 — aggiornamento DB
                    _dbg(f"STEP 6.{idx} — salvataggio nel DB")
                    msg = await msg_repo.crea(
                        testo=testo or caption,
                        canale_id=canale.id,
                    )
                    await msg_repo.segna_pubblicato(msg.id, sent.message_id)
                    _dbg(f"STEP 6.{idx} — ✅ DB aggiornato", msg_id=msg.id)
                    ok += 1

                except Exception as e:
                    fail += 1
                    tb = traceback.format_exc()
                    _dbg(f"STEP 5.{idx} — ❌ ECCEZIONE",
                         tipo=type(e).__name__,
                         messaggio=str(e),
                         traceback=tb,
                    )
                    try:
                        await log_repo.log(
                            "ERROR", "pubblica",
                            f"Errore su {canale.nome} ({canale.telegram_id}): {e}",
                        )
                    except Exception as log_err:
                        _dbg(f"STEP 5.{idx} — anche il log ha fallito", errore=str(log_err))
                    logger.error(f"Errore su {canale.nome}: {e}\n{tb}")

    except Exception as e:
        tb = traceback.format_exc()
        _dbg("STEP 3 — ❌ ECCEZIONE nel blocco DB principale",
             tipo=type(e).__name__,
             messaggio=str(e),
             traceback=tb,
        )
        raise

    # STEP 7 — risultato finale
    _dbg("STEP 7 — completato", ok=ok, fail=fail)
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
