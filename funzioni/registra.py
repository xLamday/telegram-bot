# channel_registrar.py
import asyncio
from telegram import ChatMemberUpdated
from telegram.ext import ContextTypes
from telegram.error import TelegramError, BadRequest, Forbidden
from loggerinfo import LoggerInfo
from database.manager import DatabaseManager
from config.settings import Settings
from funzioni.system import ChannelManager

class RegistrazioneCanale:
    """Classe per gestire la registrazione e rimozione dei canali privati."""

    def __init__(self):
        self.lock = asyncio.Lock()
        self.system = ChannelManager()
        self.logger = LoggerInfo(name="RegistrazioneCanale").get_logger()
        self.logger.info(f"🧩 Nuova istanza RegistrazioneCanale creata: {id(self)}")

    async def handle_chat_member_update(self, update: ChatMemberUpdated, context: ContextTypes.DEFAULT_TYPE):
        """
        Gestisce l'evento di aggiornamento dei permessi del bot in un canale.
        
        Casi gestiti:
        - Bot promosso ad admin/creator → Registra canale
        - Bot rimosso o perde permessi → Rimuove canale
        """
        cm = update.my_chat_member
        if not cm:
            return

        bot_id = context.bot.id
        user_id = cm.new_chat_member.user.id
        if user_id != bot_id:
            return

        chat = cm.chat
        chat_id = str(chat.id)
        chat_title = await self._get_chat_title(chat) or "<senza nome>"

        old_status = cm.old_chat_member.status
        new_status = cm.new_chat_member.status


        # Determina l'azione da eseguire
        is_promoted = await self._is_promoted(old_status, new_status)
        is_removed = await self._is_removed(old_status, new_status)

        is_admin_now = new_status in {"administrator", "creator"}

        # La rimozione ha priorità: va verificata PRIMA, indipendentemente dalla promozione
        if is_removed:
            await self._remove_channel(chat_id, chat_title, context)
            return

        if is_promoted:
            await self._register_channel(chat_id, chat_title, context)
            return

        if is_admin_now:
            self.logger.info(f"Il bot è admin su {chat_title}, però non è stato registrato. Registro ora {chat_title}...")
            await self._register_channel(chat_id, chat_title, context)
            return
        else:
            self.logger.info(f"Il bot non è admin su {chat_title}, ed il suo stato è {new_status}. IGNORO registrazione per {chat_title}")
            return

        self.logger.debug(
            f"Nessuna azione necessaria per {chat_title}: "
            f"{old_status} → {new_status}"
        )

    async def _get_chat_title(self, chat: ChatMemberUpdated) -> str:
        """Restituisce il titolo della chat o un placeholder."""
        return chat.title or chat.username or f"Chat {chat.id}"

    async def _is_promoted(self, old_status: str, new_status: str) -> bool:
        """Verifica se il bot è stato promosso ad admin."""
        admin = {"administrator", "creator"}
        
        return new_status in admin and old_status not in admin

    async def _is_removed(self, old_status: str, new_status: str) -> bool:
        """
        Verifica se il bot è stato rimosso o ha perso i permessi admin.
        
        Casi considerati come rimozione:
        - administrator/creator → member (perde permessi admin)
        - administrator/creator/member → left/kicked (rimosso dal canale)
        - administrator/creator/member → restricted (bannato o limitato)
        """
        admin_statuses = {"administrator", "creator"}
        active_statuses = {"administrator", "member", "creator"}
        removed_statuses = {"left", "kicked", "restricted"}
        
        # Caso 1: Perde i permessi admin (diventa member o peggio)
        was_admin = old_status in admin_statuses
        lost_admin = new_status not in admin_statuses
        
        # Caso 2: Viene completamente rimosso dal canale
        was_active = old_status in active_statuses
        is_removed = new_status in removed_statuses


        return (was_admin and lost_admin) or (was_active and is_removed)

    async def _ensure_channel(self, chat_id, chat_title, context):
        """
        Registra un canale se non esiste, senza fare il verify.
        Usato quando il bot viene promosso ad admin. In quel caso non serve fare il verify.
        """
        async with self.lock:
            try:
                inserted = False

                with DatabaseManager() as db:
                    inserted = db.channel.add_channel(chat_id, chat_title)

                if inserted:
                    self.logger.info(f"📥 Canale registrato: {chat_title} ({chat_id})")

                    await self._notify_channel_registration(chat_id, context)
                    await self._notify_admin_registration(chat_id, chat_title, context)
                else:
                    self.logger.info(
                        f"ℹ️ Canale già presente: {chat_title} ({chat_id})"
                    )

                return True

            except Exception as e:
                self.logger.error(f"Errore ensure channel {chat_id}: {e}")
                await self._notify_admin_error(str(e), context)
                return False

    async def _register_channel(self, chat_id: str, chat_title: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Registra un canale nel DB se non esiste già."""
        return await self._ensure_channel(chat_id, chat_title, context)

    async def _remove_channel(self, chat_id: str, chat_title: str, context: ContextTypes.DEFAULT_TYPE):
        """Rimuove un canale dal DB e notifica l'admin."""
        async with self.lock:
            try:
                # Verifica se il canale esiste nel DB
                with DatabaseManager() as db:
                    deleted = db.channel.delete_channel(chat_id)

                if deleted:
                    self.logger.info(f"Canale rimosso: {chat_title} ({chat_id})")
                    await self._notify_admin_removal(chat_id, chat_title, context)
                else:
                    self.logger.info(
                        f"ℹ️ Canale non rimosso: {chat_title} ({chat_id})"
                    )

            except Exception as e:
                self.logger.error(
                    f"❌ Errore durante rimozione canale {chat_title}: {e}"
                )
                await self._notify_admin_error(
                    f"Errore rimozione canale {chat_title} ({chat_id}): {e}",
                    context
                )
    async def _verify_admin_permissions(self, chat_id: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """
        Verifica che il bot abbia effettivamente i permessi admin.
        
        Returns:
            True se il bot è admin, False altrimenti
        """
        try:
            admins = await context.bot.get_chat_administrators(int(chat_id))
            bot_is_admin = any(
                admin.user.id == context.bot.id for admin in admins
            )
            
            if not bot_is_admin:
                self.logger.warning(
                    f"⚠️ Bot non risulta admin in {chat_id} durante verifica"
                )
                return bot_is_admin

            self.logger.info(f"Bot risulta admin in {chat_id} durante verifica")
            
            return bot_is_admin

        except (BadRequest, Forbidden) as e:
            self.logger.warning(
                f"⚠️ Impossibile verificare permessi in {chat_id}: {e}"
            )
            return False
        except TelegramError as e:
            self.logger.error(
                f"❌ Errore Telegram durante verifica permessi {chat_id}: {e}"
            )
            return False


    async def _notify_channel_registration(self, chat_id: str, context: ContextTypes.DEFAULT_TYPE):
        """Invia un messaggio di benvenuto nel canale (se possibile)."""
        try:
            await context.bot.send_message(
                chat_id=int(chat_id),
                text=(
                    "✅ <b>Bot configurato con successo!</b>\n\n"
                    "Sono stato aggiunto come amministratore e il canale "
                    "è stato registrato nel sistema.\n\n"
                    "Tutti i messaggi pubblicati qui saranno monitorati."
                ),
                parse_mode="HTML"
            )
        except Forbidden:
            self.logger.warning(
                f"⚠️ Bot non può inviare messaggi in {chat_id} "
                "(potrebbe non avere permessi di scrittura)"
            )
        except TelegramError as e:
            self.logger.warning(
                f"⚠️ Impossibile inviare messaggio in {chat_id}: {e}"
            )

    async def _notify_admin_registration(self, chat_id: str, chat_title: str, context: ContextTypes.DEFAULT_TYPE):
        """Notifica l'admin della registrazione di un nuovo canale."""
        try:
            message = (
                "📢 <b>Nuovo canale registrato!</b>\n\n"
                f"📺 <b>Titolo:</b> {chat_title}\n"
                f"🆔 <b>ID:</b> <code>{chat_id}</code>\n\n"
                "Il canale è ora monitorato dal sistema."
            )
            
            await context.bot.send_message(
                chat_id=Settings.ADMIN_ID,
                text=message,
                parse_mode="HTML"
            )
        except TelegramError as e:
            self.logger.error(f"❌ Errore notifica admin: {e}")

    async def _notify_admin_removal(self, chat_id: str, chat_title: int, context: ContextTypes.DEFAULT_TYPE):
        """Notifica l'admin della rimozione di un canale."""
        try:
            message = (
                "⚠️ <b>Canale rimosso dal sistema</b>\n\n"
                f"📺 <b>Titolo:</b> {chat_title}\n"
                f"🆔 <b>ID:</b> <code>{chat_id}</code>\n\n"
                "<i>Motivo: Bot rimosso o permessi revocati</i>\n\n"
            )
            
            await context.bot.send_message(
                chat_id=Settings.ADMIN_ID,
                text=message,
                parse_mode="HTML"
            )
        except TelegramError as e:
            self.logger.error(f"❌ Errore notifica admin rimozione: {e}")

    async def _notify_admin_error(self, error_message: str, context: ContextTypes.DEFAULT_TYPE):
        """Notifica l'admin di un errore durante le operazioni."""
        try:
            await context.bot.send_message(
                chat_id=Settings.ADMIN_ID,
                text=f"❌ <b>Errore sistema registrazione</b>\n\n{error_message}",
                parse_mode="HTML"
            )
        except TelegramError as e:
            self.logger.error(
                f"❌ Impossibile notificare admin dell'errore: {e}"
            )