# bot_monitor.py
import asyncio
from telegram.error import TelegramError, BadRequest, Forbidden, RetryAfter
from telegram.ext import ContextTypes
from loggerinfo import logger
from funzioni.system import remove_channel
from config.settings import Settings
from database.database import DatabaseManager

class BotMonitor:
    """Classe per il monitoraggio dei post e dei permessi admin."""

    def __init__(self):
        self.state_lock = asyncio.Lock()

    async def check_post_eliminati(self, context: ContextTypes.DEFAULT_TYPE):
        """Controlla se i post sono stati eliminati e segnala all'admin."""

        async with self.state_lock:
            if Settings.processo_invio or Settings.invio:
                logger.info(f"Skip check_post_eliminati: processo_invio={Settings.processo_invio}, invio={Settings.invio}")
                return

        with DatabaseManager() as db:
            posts = await db.fetch_all_posts()
            for chat_id, msg_id, title in posts:
                try:
                    await asyncio.sleep(2)
                    await self._forward_message_safe(context, chat_id, msg_id)
                except BadRequest:
                    # Messaggio eliminato
                    await context.bot.send_message(
                        chat_id=Settings.ADMIN_ID,
                        text=f"⚠️ Il messaggio pubblicato nel canale {chat_id}, titolo: {title}, è stato eliminato!"
                    )
                    #await db.delete_post(chat_id, msg_id)

                    logger.info(f"Post eliminato da {chat_id}.")

                except Forbidden:
                    await context.bot.send_message(
                        chat_id=Settings.ADMIN_ID,
                        text=f"⚠️ Non posso accedere al canale {chat_id}, potrebbe essere stato rimosso!"
                    )
                    logger.warning(f"Accesso proibito al canale {chat_id}")

                except TelegramError as e:
                    logger.warning(f"Errore Telegram controllando il messaggio {msg_id} in {chat_id}: {e}")

    async def _forward_message_safe(self, context, chat_id, msg_id, tentativi: int = 3):
        """Forward/copy message con retry in caso di RetryAfter o errori transitori."""
        for prova in range(1, tentativi + 1):
            try:
                await context.bot.copy_message(
                    chat_id=Settings.CANALE_CONTROLLO,
                    from_chat_id=int(chat_id),
                    message_id=msg_id
                )
                logger.info(f"Messaggio {msg_id} da {chat_id} inoltrato al canale di controllo")
                return
            except RetryAfter as e:
                attendi = e.retry_after + 1
                logger.warning(f"Rate limit Telegram. Riprova {prova}/{tentativi}. Attendi {attendi}s")
                await asyncio.sleep(attendi)
            except TelegramError as e:
                logger.warning(f"Errore Telegram nel forward {msg_id} da {chat_id}: {e}")
                if prova == tentativi:
                    raise e
                await asyncio.sleep(2)

    async def check_bot_admin(self, context: ContextTypes.DEFAULT_TYPE):
        """Controlla periodicamente se il bot ha ancora permessi admin nei canali."""

        with DatabaseManager() as db:
            channels = await db.fetch_all_channels()

        for chat_id, title in channels:
            try:
                await asyncio.sleep(5)
                admins = await context.bot.get_chat_administrators(int(chat_id))
                bot_admin = any(a.user.id == context.bot.id for a in admins)

                if not bot_admin:
                    #remove_channel(chat_id)
                    await context.bot.send_message(
                        chat_id=Settings.ADMIN_ID,
                        text=f"⚠️ Ho perso i permessi admin nel canale {chat_id}!"
                    )
                    async with DatabaseManager() as db:
                        #await db.delete_channel(chat_id)
                        logger.info(f"Il BOT ha perso i permessi admin nel canale: {title}")

                    await context.bot.send_message(
                        chat_id=Settings.ADMIN_ID,
                        text=f"⚠️ Riscontrato un errore, è possibile che non sia più amministratore nel canale con id: {chat_id} e titolo: {title}"
                    )
                    logger.info(f"Bot rimosso da admin in canale {chat_id} con titolo: {title}")

            except RetryAfter as e:
                logger.warning(f"Rate limit Telegram controllando canale {chat_id}, sleep {e.retry_after}s")
                await asyncio.sleep(e.retry_after + 1)
            except (BadRequest, Forbidden) as e:
                #remove_channel(chat_id)
                await context.bot.send_message(
                    chat_id=Settings.ADMIN_ID,
                    text=f"⚠️ Non posso accedere al canale {chat_id} ({type(e).__name__}). Rimosso dal DB."
                )
                logger.warning(f"Impossibile controllare canale {chat_id}: {e}")
            except TelegramError as e:
                logger.warning(f"Errore Telegram controllando canale {chat_id}: {e}")
