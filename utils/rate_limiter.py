import asyncio
import time
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any
from telegram.error import RetryAfter
from loggerinfo import LoggerInfo


class RateLimiter:
    """
    Rate limiter intelligente per le API di Telegram.
    Gestisce rate limiting preventivo, RetryAfter e cleanup automatico.
    """

    MAX_MESSAGES_PER_SECOND = 30
    MAX_MESSAGES_PER_CHAT_PER_SECOND = 1
    MAX_MESSAGES_PER_MINUTE_PER_CHAT = 10
    INACTIVITY_THRESHOLD = 600  # 10 minuti → rimuovi dal tracking

    def __init__(self):
        self.logger = LoggerInfo(name="RateLimiter").get_logger()
        self._last_send: dict[str, float] = defaultdict(float)
        self._sends_per_minute: dict[str, list[float]] = defaultdict(list)
        self._global_sends: list[float] = []
        self._lock = asyncio.Lock()
        self._stats = {
            "retry_after_hits": 0,
            "attesa_preventiva": 0,
            "total_calls": 0,
            "total_wait_time": 0.0,
        }
        self._cleanup_task: asyncio.Task | None = None

    def start(self):
        """Avvia il cleanup task. Chiamare dopo che l'event loop è attivo."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            self.logger.info("🧹 RateLimiter cleanup task avviato")

    async def stop(self):
        """Ferma il cleanup task e attende la chiusura pulita."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self.logger.info("🛑 RateLimiter cleanup task fermato")
        self._cleanup_task = None

    async def acquire(self, chat_id: str) -> bool:
        """
        Controlla se è possibile inviare senza attendere.
        Returns True se si può procedere subito, False se si è a limite.
        """
        chat_id = str(chat_id)
        async with self._lock:
            return self._calcola_wait(chat_id, time.monotonic()) == 0.0

    async def attendi_se_necessario(self, chat_id: str) -> None:
        """
        Attende il tempo necessario prima di poter inviare.
        Blocca finché non è sicuro procedere.
        """
        chat_id = str(chat_id)
        async with self._lock:
            adesso = time.monotonic()
            wait = self._calcola_wait(chat_id, adesso)
            slot = adesso + wait
            self._last_send[chat_id] = slot
            self._global_sends.append(slot)
            self._sends_per_minute[chat_id].append(slot)

        if wait > 0:
            self._stats["attesa_preventiva"] += 1
            self._stats["total_wait_time"] += wait
            self.logger.debug(f"⏳ Attesa preventiva {wait:.2f}s per chat {chat_id}")
            await asyncio.sleep(wait)

    async def execute(
        self,
        chat_id: str,
        coro_factory: Callable[[], Awaitable[Any]],
        max_retries: int = 3,
    ):
        """
        Esegue una coroutine rispettando i rate limit.
        Gestisce automaticamente RetryAfter con retry.

        Uso:
            sent = await rate_limiter.execute(
                chat_id=chat_id,
                coro_factory=lambda: bot.send_message(chat_id=chat_id, text="ciao")
            )
        """
        chat_id = str(chat_id)
        self._stats["total_calls"] += 1

        for tentativi in range(1, max_retries + 1):
            await self.attendi_se_necessario(chat_id)

            try:
                return await coro_factory()

            except RetryAfter as e:
                self._stats["retry_after_hits"] += 1
                retry_after = e.retry_after
                if hasattr(retry_after, "total_seconds"):
                    retry_after = retry_after.total_seconds()

                tempo_attesa = retry_after + 2                
                if tentativi == max_retries:
                    self.logger.error(
                        f"❌ RetryAfter esaurito dopo {tentativi} tentativi "
                        f"su chat {chat_id}"
                    )
                    raise

                self.logger.warning(
                    f"🚦 RetryAfter su {chat_id}: attesa {tempo_attesa}s "
                    f"(tentativo {tentativi}/{max_retries})"
                )
                self._stats["total_wait_time"] += tempo_attesa
                await asyncio.sleep(tempo_attesa)

    def _calcola_wait(self, chat_id: str, now: float) -> float:
        """Calcola il tempo di attesa necessario. Da chiamare dentro il lock."""
        wait = 0.0

        # 1. Rate limit per chat (1 msg/sec)
        ultimo = self._last_send[chat_id]
        if ultimo:
            residuo = now - ultimo
            min_interval = 1.0 / self.MAX_MESSAGES_PER_CHAT_PER_SECOND
            if residuo < min_interval:
                wait = max(wait, min_interval - residuo)

        # 2. Rate limit globale (30 msg/sec)
        self._global_sends = [t for t in self._global_sends if now - t < 1.0]
        if len(self._global_sends) >= self.MAX_MESSAGES_PER_SECOND:
            wait = max(wait, 1.0 - (now - self._global_sends[0]))

        # 3. Rate limit per minuto per chat (20 msg/min)
        minuto_fa = now - 60.0
        self._sends_per_minute[chat_id] = [
            t for t in self._sends_per_minute[chat_id] if t > minuto_fa
        ]
        if len(self._sends_per_minute[chat_id]) >= self.MAX_MESSAGES_PER_MINUTE_PER_CHAT:
            wait = max(wait, 60.0 - (now - self._sends_per_minute[chat_id][0]))

        return wait

    async def _cleanup_loop(self):
        """Rimuove periodicamente i dati delle chat inattive."""
        while True:
            try:
                await asyncio.sleep(300)  # Ogni 5 minuti
                await self._cleanup_chats_inattive()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"❌ Errore nel cleanup task: {e}")

    async def _cleanup_chats_inattive(self):
        async with self._lock:
            ora = time.monotonic()
            inattivo = [
                chat_id for chat_id, last in self._last_send.items()
                if ora - last > self.INACTIVITY_THRESHOLD
            ]
            for chat_id in inattivo:
                del self._last_send[chat_id]
                self._sends_per_minute.pop(chat_id, None)

            if inattivo:
                self.logger.debug(
                    f"🧹 Cleanup: rimossi {len(inattivo)} canali inattivi"
                )

    async def log_stats(self, context=None):
        stats = {**self._stats, "active_chats": len(self._last_send)}
        self.logger.info(
            f"📊 RateLimiter — chiamate: {stats['total_calls']}, "
            f"retry_after: {stats['retry_after_hits']}, "
            f"attese_preventive: {stats['attesa_preventiva']}, "
            f"tempo_attesa: {stats['total_wait_time']:.1f}s, "
            f"chat_attive: {stats['active_chats']}"
        )