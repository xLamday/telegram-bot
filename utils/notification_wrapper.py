import asyncio
from typing import List
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from config.settings import Settings
from loggerinfo import LoggerInfo

class NotificationWrapper:
    """Classe per raggruppare e inviare notifiche in batch."""
    
    def __init__(self):
        self.notifications: List[str] = []
        self.lock = asyncio.Lock()
        self.logger = LoggerInfo(name="NotificationWrapper").get_logger()
        self.logger.info("🧩 Nuova istanza NotificationWrapper creata.")

    async def add_notification(self, message: str):
        """Aggiunge un messaggio alla coda delle notifiche."""
        async with self.lock:
            self.notifications.append(message)
            self.logger.debug(f"Notifica aggiunta alla coda (totale: {len(self.notifications)})")

    def _chunk_message(self, message: str, max_length: int = 4096) -> List[str]:
        """Divide un messaggio lungo in chunk per rispettare i limiti di Telegram."""
        if len(message) <= max_length:
            return [message]
        
        chunks = []
        current_chunk = ""
        lines = message.split('\n')
        
        for line in lines:
            if len(current_chunk) + len(line) + 1 > max_length:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = line + "\n"
            else:
                current_chunk += line + "\n"
                
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks

    async def flush(self, context: ContextTypes.DEFAULT_TYPE):
        """Svuota la coda e invia le notifiche all'admin."""
        async with self.lock:
            if not self.notifications:
                return
            
            messages_to_send = list(self.notifications)
            self.notifications.clear()

        self.logger.info(f"📤 Invio di {len(messages_to_send)} notifiche raggruppate all'admin...")
        
        final_message = "🔔 <b>Riepilogo Notifiche</b>\n\n"
        for i, msg in enumerate(messages_to_send, 1):
            final_message += f"🔹 <b>Avviso {i}:</b>\n{msg}\n\n"
        
        chunks = self._chunk_message(final_message)
        
        for chunk in chunks:
            try:
                await context.bot.send_message(
                    chat_id=Settings.ADMIN_ID,
                    text=chunk,
                    parse_mode="HTML"
                )
                await asyncio.sleep(0.5) # Pausa tra i chunk per evitare rate limits
            except TelegramError as e:
                self.logger.error(f"❌ Errore invio riepilogo notifiche: {e}")
