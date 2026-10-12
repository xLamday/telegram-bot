import asyncio
import time
from typing import List, Dict, Optional
from telegram.ext import ContextTypes
from telegram.error import TelegramError, BadRequest
from config.settings import Settings
from loggerinfo import LoggerInfo

MAX_LEN = 4096
MAX_QUEUE= 200

class NotificationWrapper:
    """Classe per raggruppare e inviare notifiche in batch."""
    
    def __init__(self):
        self.notifications: List[str] = []
        self._last_seen: Dict[str, float] = {}
        self.lock = asyncio.Lock()
        self.logger = LoggerInfo(name="NotificationWrapper").get_logger()
        self.logger.info("🧩 Nuova istanza NotificationWrapper creata.")
    
    async def add_notification(self, message: str, key: Optional[str] = None, cooldown: Optional[int] = None):
        """
        Aggiunge un messaggio alla coda.
        Se la stessa `key` (default: il testo) è già stata accodata meno di `cooldown` secondi fa, viene ignorata.
        """
        key = key or message
        cooldown = Settings.NOTIFICATION_COOLDOWN if cooldown is None else cooldown
        now = time.monotonic()
        async with self.lock:
            last = self._last_seen.get(key)
            if last is not None and now - last < cooldown:
                self.logger.debug(f"Notifica duplicata ignorata (key={key[:60]!r})")
                return
            self._last_seen[key] = now
            self.notifications.append(message)
            if len(self.notifications) > MAX_QUEUE:
                dropped = len(self.notifications) - MAX_QUEUE
                del self.notifications[:dropped]
                self.logger.warning(f"Coda notifiche piena: scartate {dropped} notifiche più vecchie")
            self._purge_seen(now)
            self.logger.debug(f"Notifica aggiunta alla coda (totale: {len(self.notifications)})")

    def _purge_seen(self, now: float, max_age: float = 86400.0):
        """Elimina le chiavi più vecchie di 24h per non far crescere il dizionario. Chiamare dentro il lock."""
        if len(self._last_seen) < 500:
            return
        self._last_seen = {k: t for k, t in self._last_seen.items() if now - t < max_age}

    @staticmethod
    def _build_chunks(entries: List[str], header: str) -> List[List[str]]:
        """Impacchetta le notifiche in gruppi che stanno in un messaggio Telegram."""
        groups: List[List[str]] = []
        current: List[str] = []
        size = len(header)
        for entry in entries:
            if len(entry) > MAX_LEN - len(header) - 10:
                entry = entry[: MAX_LEN - len(header) - 20] + "…"
            if current and size + len(entry) > MAX_LEN:
                groups.append(current)
                current, size = [], len(header)
            current.append(entry)
            size += len(entry)
        if current:
            groups.append(current)
        return groups

    async def flush(self, context: ContextTypes.DEFAULT_TYPE):
        """Svuota la coda e invia le notifiche all'admin."""
        async with self.lock:
            if not self.notifications:
                return
            messages = list(self.notifications)
            self.notifications.clear()
 
        self.logger.info(f"📤 Invio di {len(messages)} notifiche raggruppate all'admin...")
 
        header = "🔔 <b>Riepilogo Notifiche</b>\n\n"
        entries = [f"🔹 <b>Avviso {i}:</b>\n{msg}\n\n" for i, msg in enumerate(messages, 1)]
        groups = self._build_chunks(entries, header)
 
        unsent: List[str] = []
        for idx, group in enumerate(groups):
            text = header + "".join(group)
            try:
                await self._send(context, text)
                await asyncio.sleep(0.5)  # pausa tra i chunk
            except TelegramError as e:
                self.logger.error(f"❌ Errore invio riepilogo notifiche: {e}")
                # rimetti in coda tutte le notifiche dei chunk non inviati
                done = sum(len(g) for g in groups[:idx])
                unsent = messages[done:]
                break
 
        if unsent:
            async with self.lock:
                self.notifications = (unsent + self.notifications)[-MAX_QUEUE:]
            self.logger.warning(f"↩️ {len(unsent)} notifiche rimesse in coda")


    async def _send(self, context: ContextTypes.DEFAULT_TYPE, text: str):
        try:
            await context.bot.send_message(chat_id=Settings.ADMIN_ID, text=text, parse_mode="HTML")
        except BadRequest as e:
            if "parse entities" not in str(e).lower():
                raise
            # HTML non valido: meglio un messaggio con i tag visibili che perderlo
            self.logger.warning(f"HTML non valido nel riepilogo, reinvio come testo semplice: {e}")
            await context.bot.send_message(chat_id=Settings.ADMIN_ID, text=text[:MAX_LEN])
 