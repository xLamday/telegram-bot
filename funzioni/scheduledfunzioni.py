# bot_monitor.py
import asyncio
import re
from typing import List, Tuple
from telegram.error import TelegramError, BadRequest, Forbidden, RetryAfter
from telegram.ext import ContextTypes
from loggerinfo import LoggerInfo
from funzioni.system import ChannelManager
from config.settings import Settings
from database.database import DatabaseManager


class BotMonitor:
    """Classe per il monitoraggio dei post e dei permessi admin."""
    
    def __init__(self):
        self.state_lock = asyncio.Lock()
        self.system = ChannelManager()
        self._lock_check_post = asyncio.Lock()
        self._lock_check_admin = asyncio.Lock()
        self.logger = LoggerInfo(name="BotMonitor").get_logger()
        self.logger.info(f"🧩 Nuova istanza BotMonitor creata: {id(self)}")
        
        # Configurazione per la gestione di molti canali
        self.batch_size = 10  # Processa N canali alla volta
        self.delay_between_batches = 10  # Secondi tra un batch e l'altro
        self.delay_between_checks = 2.5  # Secondi tra un controllo e l'altro nello stesso batch
        self.max_concurrent_tasks = 2  # Task simultanei per batch (Quanti messaggi possono essere inoltrati contemporaneamente)
        self._first_admin_check_done = False


    async def check_post_eliminati(self, context: ContextTypes.DEFAULT_TYPE):
        """Controlla se i post sono stati eliminati e segnala all'admin."""
        if Settings.processo_invio or Settings.invio or Settings.controllo_canali_attivo:
            self.logger.info(
                f"Skip check_post_eliminati: processo_invio={Settings.processo_invio}, "
                f"invio={Settings.invio}"
            )
            return
        
        if self._lock_check_post.locked():
            self.logger.info("⏸ check_post_eliminati: già in esecuzione, skip.")
            return
        
        async with self._lock_check_post:
            self.logger.info("🚀 Avvio controllo post eliminati...")
            Settings.controllo_canali_attivo = True
            
            try:
                with DatabaseManager() as db:
                    posts = db.fetch_all_posts()
                
                total_posts = len(posts)
                self.logger.info(f"📊 Totale post da controllare: {total_posts}")
                
                # Processa i post in batch
                await self._process_posts_in_batches(context, posts)
                
            finally:
                Settings.controllo_canali_attivo = False
                self.logger.info("✅ Controllo post eliminati completato.")
    
    async def _process_posts_in_batches(
        self, 
        context: ContextTypes.DEFAULT_TYPE, 
        posts: List[Tuple]
    ):
        """Processa i post in batch per evitare rate limiting."""
        for i in range(0, len(posts), self.batch_size):
            batch = posts[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (len(posts) + self.batch_size - 1) // self.batch_size
            
            self.logger.info(f"📦 Processando batch {batch_num}/{total_batches}")
            
            # Processa il batch con concorrenza limitata
            await self._process_batch_with_semaphore(context, batch)
            
            # Pausa tra i batch (eccetto l'ultimo)
            if i + self.batch_size < len(posts):
                self.logger.info(
                    f"⏸ Pausa di {self.delay_between_batches}s tra i batch..."
                )
                await asyncio.sleep(self.delay_between_batches)
    
    async def _process_batch_with_semaphore(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        batch: List[Tuple]
    ):
        """Processa un batch di post con semaforo per limitare la concorrenza."""
        semaforo = asyncio.Semaphore(self.max_concurrent_tasks)
        
        async def process_with_semaphore(post_data):
            async with semaforo:
                await self._check_single_post(context, *post_data)
                await asyncio.sleep(self.delay_between_checks)
        
        tasks = [process_with_semaphore(post) for post in batch]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _check_single_post(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        chat_id: str,
        msg_id: int,
        title: str
    ):
        """Controlla un singolo post."""
        try:
            await self._forward_message_safe(context, chat_id, msg_id)
            self.logger.debug(
                f"✓ Messaggio {msg_id} da {title} verificato"
            )
            
        except BadRequest as e:
            # Messaggio eliminato
            await self._notify_admin_deleted_post(context, chat_id, title, msg_id)
            self.logger.info(
                f"⚠️ Possibile post eliminato in {chat_id}, {title}"
            )
            
        except Forbidden:
            await self._notify_admin_forbidden_channel(context, chat_id, title)
            await self._remove_forbidden_channel(chat_id, msg_id)
            
        except RetryAfter as e:
            # Gestione flood control globale
            wait_time = e.retry_after + 2
            self.logger.warning(
                f"🚦 Flood control globale: attendo {wait_time}s"
            )
            await asyncio.sleep(wait_time)
            # Riprova una volta
            await self._check_single_post(context, chat_id, msg_id, title)
            
        except TelegramError as e:
            self.logger.error(
                f"❌ Errore Telegram controllando {chat_id}: {e}"
            )
    
    async def _forward_message_safe(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        chat_id: str,
        msg_id: int,
        tentativi: int = 3
    ):
        """Forward/copy message con retry in caso di RetryAfter o errori transitori."""
        for prova in range(1, tentativi + 1):
            try:
                await context.bot.copy_message(
                    chat_id=Settings.CANALE_CONTROLLO,
                    from_chat_id=int(chat_id),
                    message_id=msg_id
                )
                return
                
            except RetryAfter as e:
                attendi = e.retry_after + 1
                if prova == tentativi:
                    raise  # Rilancia l'eccezione all'ultimo tentativo
                    
                self.logger.warning(
                    f"⏳ Rate limit. Tentativo {prova}/{tentativi}. "
                    f"Attesa {attendi}s"
                )
                await asyncio.sleep(attendi)
                
            except (BadRequest, Forbidden):
                # Non ha senso ritentare per questi errori
                raise
                
            except TelegramError as e:
                if prova == tentativi:
                    raise
                    
                self.logger.warning(
                    f"⚠️ Errore tentativo {prova}/{tentativi}: {e}"
                )
                await asyncio.sleep(2 ** prova)  # Backoff esponenziale
    
    async def check_bot_admin(self, context: ContextTypes.DEFAULT_TYPE):
        """Controlla periodicamente se il bot ha ancora permessi admin nei canali."""
        if self._lock_check_admin.locked():
            self.logger.info("⏸ check_bot_admin: già in esecuzione, skip.")
            return
        
        async with self._lock_check_admin:
            self.logger.info("🔐 Avvio controllo permessi admin...")
            
            with DatabaseManager() as db:
                channels = db.fetch_all_channels()
            
            total_channels = len(channels)
            self.logger.info(f"📊 Totale canali da controllare: {total_channels}")
            
            # Processa i canali in batch
            await self._process_channels_in_batches(context, channels)
            
            self.logger.info("✅ Controllo permessi admin completato.")
    
    async def _process_channels_in_batches(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        channels: List[Tuple]
    ):
        """Processa i canali in batch per evitare rate limiting."""
        for i in range(0, len(channels), self.batch_size):
            batch = channels[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (len(channels) + self.batch_size - 1) // self.batch_size
            
            self.logger.info(
                f"Controllando batch {batch_num}/{total_batches} di canali"
            )
            
            # Processa il batch con concorrenza limitata
            await self._check_admin_batch_with_semaphore(context, batch)
            
            # Pausa tra i batch (eccetto l'ultimo)
            if i + self.batch_size < len(channels):
                self.logger.info(
                    f"⏸ Pausa di {self.delay_between_batches}s tra i batch..."
                )
                await asyncio.sleep(self.delay_between_batches)
    
    async def _check_admin_batch_with_semaphore(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        batch: List[Tuple]
    ):
        """Controlla i permessi admin per un batch con semaforo."""
        semaphore = asyncio.Semaphore(self.max_concurrent_tasks)
        
        async def check_with_semaphore(channel_data):
            async with semaphore:
                await self._check_single_channel_admin(context, *channel_data)
                await asyncio.sleep(self.delay_between_checks)
        
        tasks = [check_with_semaphore(channel) for channel in batch]
        await asyncio.gather(*tasks, return_exceptions=True)
        
    
    async def _check_single_channel_admin(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        chat_id: str,
        title: str
    ):
        """Fallback check per quando il bot era offline. Soggetto a cache Telegram."""
        bot_id = context.application.bot_data["bot_id"]
        try:
            admins = await context.bot.get_chat_administrators(int(chat_id))
            admin_ids = {a.user.id for a in admins}

            if bot_id not in admin_ids:
                self.logger.warning(f"⚠️ [FALLBACK] Bot non admin su '{title}'")
                await self._handle_lost_admin_rights(context, chat_id, title)
            else:
                self.logger.info(f"✅ [FALLBACK] Bot admin su '{title}'")

        except RetryAfter as e:
            wait_time = e.retry_after + 2
            self.logger.warning(f"🚦 Rate limit su '{title}': attesa {wait_time}s")
            await asyncio.sleep(wait_time)
            await self._check_single_channel_admin(context, chat_id, title)

        except BadRequest as e:
            await self._notify_admin_inaccessible_channel(
                context, chat_id, title, type(e).__name__
            )
            self.logger.warning(f"⚠️ Impossibile controllare '{title}': {e}")

        except Forbidden:
            await self._notify_admin_forbidden_channel(context, chat_id, title)
            await self._remove_forbidden_channel(chat_id, title)
        except TelegramError as e:
            self.logger.error(f"❌ Errore controllando '{title}': {e}")
    
    # Metodi helper per notifiche
    async def _notify_admin_deleted_post(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        chat_id: str,
        title: str,
        msg_id: int
    ):
        """Notifica admin di un post eliminato."""
        try:
            await context.bot.send_message(
                chat_id=Settings.ADMIN_ID,
                text=(
                    f"⚠️ Il messaggio pubblicato nel canale {chat_id}\n"
                    f"📢 Titolo: {title}\n"
                    f"🆔 Message ID: {msg_id}\n"
                    f"È possibile che sia stato eliminato!"
                )
            )
        except TelegramError as e:
            self.logger.error(f"Errore notifica admin: {e}")
    
    async def _notify_admin_forbidden_channel(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        chat_id: str,
        title: str
    ):
        """Notifica admin di un canale non accessibile."""
        try:
            await context.bot.send_message(
                chat_id=Settings.ADMIN_ID,
                text=(
                    f"⚠️ Non posso accedere al canale {chat_id}\n"
                    f"📢 Titolo: {title}\n"
                    f"Il canale è stato rimosso o il bot bannato!"
                )
            )
        except TelegramError as e:
            self.logger.error(f"Errore notifica admin: {e}")
    
    async def _notify_admin_inaccessible_channel(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        chat_id: str,
        title: str,
        error_type: str
    ):
        """Notifica admin di un canale inaccessibile."""
        try:
            await context.bot.send_message(
                chat_id=Settings.ADMIN_ID,
                text=(
                    f"⚠️ Non posso accedere al canale {chat_id}\n"
                    f"📢 Titolo: {title}\n"
                    f"❌ Errore: {error_type}"
                )
            )
        except TelegramError as e:
            self.logger.error(f"Errore notifica admin: {e}")
    
    async def _remove_forbidden_channel(self, chat_id: str, msg_id: int):
        """Rimuove un canale non accessibile dal database."""
        try:
            with DatabaseManager() as db:
                db.delete_channel(chat_id)
            self.logger.info(f"🗑️ Canale {chat_id} rimosso dal database")
        except Exception as e:
            self.logger.error(f"Errore rimozione canale {chat_id}: {e}")
    
    async def _handle_lost_admin_rights(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        chat_id: str,
        title: str
    ):
        """Gestisce la perdita dei permessi admin."""
        self.logger.warning(f"🔴 _handle_lost_admin_rights chiamata per '{title}'")
        await self.system._remove_channel_after_error(chat_id, title, context)
        
        try:
            messaggio = (
                "⚠️ Ho perso i permessi admin!\n"
                f"🆔 Canale: {chat_id}\n"
                f"📢 Titolo: {title}"
            )
            await context.bot.send_message(
                chat_id=Settings.ADMIN_ID,
                text=messaggio,
                parse_mode="HTML"
            )
        except TelegramError as e:
            self.logger.error(f"Errore notifica perdita admin: {e}")
        
        self.logger.info(f"⚠️ Permessi admin persi in {title}")