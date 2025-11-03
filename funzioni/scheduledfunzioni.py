# bot_monitor.py
import asyncio
from telegram.error import TelegramError, BadRequest, Forbidden, RetryAfter
from telegram.ext import ContextTypes
import re
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
        self.logger = LoggerInfo(name="BotMonitor").get_logger()
        self.logger.info(f"🧩 Nuova istanza BotMonitor creata: {id(self)}")

    async def check_post_eliminati(self, context: ContextTypes.DEFAULT_TYPE):
        """Controlla se i post sono stati eliminati e segnala all'admin."""

        if Settings.processo_invio or Settings.invio or Settings.controllo_canali_attivo:
            self.logger.info(f"Skip check_post_eliminati: processo_invio={Settings.processo_invio}, invio={Settings.invio}")
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
                    for chat_id, msg_id, title in posts:
                        try:
                            await asyncio.sleep(2)
                            await self._forward_message_safe(context, chat_id, msg_id)
                            self.logger.info(f"Messaggio {msg_id} da {title} inoltrato al canale di controllo")
                        except BadRequest:
                            # Messaggio eliminato
                            await context.bot.send_message(
                                chat_id=Settings.ADMIN_ID,
                                text=f"⚠️ Il messaggio pubblicato nel canale {chat_id}, titolo: {title}, è possibile che sia stato eliminato!"
                            )
                            #db.delete_post(chat_id, msg_id)

                            self.logger.info(f"Possibile post eliminato in {chat_id}, {title}. ")

                        except Forbidden:
                            await context.bot.send_message(
                                chat_id=Settings.ADMIN_ID,
                                text=f"⚠️ Non posso accedere al canale {chat_id}, il canale è stato rimosso!"
                            )
                            self.logger.warning(f"Accesso proibito al canale {chat_id}")
                            db.delete_post(chat_id, msg_id)
                            db.delete_channel(chat_id)

                        except TelegramError as e:
                            if "Flood control exceeded" in str(e):
                                match = re.search(r"Retry in (\d+) seconds", str(e))
                                if match:
                                    wait_time = int(match.group(1))
                                    self.logger.warning(f"⏸ Flood control attivo: attendo {wait_time} secondi...")
                                    await asyncio.sleep(wait_time + 5)
                                    continue  # riprende dopo la pausa
            finally:
                Settings.controllo_canali_attivo = False
                self.logger.info("✅ Controllo post eliminati completato.")

    async def _forward_message_safe(self, context: ContextTypes.DEFAULT_TYPE, chat_id, msg_id, tentativi: int = 3):
        """Forward/copy message con retry in caso di RetryAfter o errori transitori."""
        for prova in range(1, tentativi + 1):
            try:
                await context.bot.forward_message(
                    chat_id=Settings.CANALE_CONTROLLO,
                    from_chat_id=int(chat_id),
                    message_id=msg_id
                )
                self.logger.info(f"Messaggio {msg_id} da {chat_id} inoltrato al canale di controllo")
                return
            except RetryAfter as e:
                attendi = e.retry_after + 1
                self.logger.warning(f"Rate limit Telegram. Riprova {prova}/{tentativi}. Attendi {attendi}s")
                await asyncio.sleep(attendi)
            except TelegramError as e:
                self.logger.warning(f"Errore Telegram nel forward {msg_id} da {chat_id}: {e}")
                if prova == tentativi:
                    raise e
                await asyncio.sleep(2)

    async def check_bot_admin(self, context: ContextTypes.DEFAULT_TYPE):
        """Controlla periodicamente se il bot ha ancora permessi admin nei canali."""

        with DatabaseManager() as db:
            channels = db.fetch_all_channels()

        for chat_id, title in channels:
            try:
                await asyncio.sleep(5)
                admins = await context.bot.get_chat_administrators(int(chat_id))
                bot_admin = any(a.user.id == context.bot.id for a in admins)

                if not bot_admin:
                    self.system.remove_channel(chat_id)
                    await context.bot.send_message(
                        chat_id=Settings.ADMIN_ID,
                        text=f"⚠️ Ho perso i permessi admin nel canale {chat_id}!"
                    )
                    async with DatabaseManager() as db:
                        #await db.delete_channel(chat_id)
                        self.logger.info(f"Il BOT ha perso i permessi admin nel canale: {title}")

                    await context.bot.send_message(
                        chat_id=Settings.ADMIN_ID,
                        text=f"⚠️ Riscontrato un errore, è possibile che non sia più amministratore nel canale con id: {chat_id} e titolo: {title}"
                    )
                    self.logger.info(f"Bot rimosso da admin in canale {chat_id} con titolo: {title}")

            except RetryAfter as e:
                self.logger.warning(f"Rate limit Telegram controllando canale {chat_id}, sleep {e.retry_after}s")
                await asyncio.sleep(e.retry_after + 1)
            except (BadRequest, Forbidden) as e:
                #remove_channel(chat_id)
                await context.bot.send_message(
                    chat_id=Settings.ADMIN_ID,
                    text=f"⚠️ Non posso accedere al canale {chat_id} ({type(e).__name__})."
                )
                self.logger.warning(f"Impossibile controllare canale {chat_id}: {e}")
            except TelegramError as e:
                self.logger.warning(f"Errore Telegram controllando canale {chat_id}: {e}")
