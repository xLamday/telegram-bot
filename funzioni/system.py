# funzioni/system.py
import asyncio
from typing import List, Tuple
from telegram import Update, Message
from telegram.ext import ContextTypes
from telegram.error import TelegramError, RetryAfter, Forbidden, BadRequest
from utils import rate_limiter
from utils.telegram_errors import TelegramErrorClassificatore as TEC
from loggerinfo import LoggerInfo
from config.settings import Settings
from database.manager import DatabaseManager


class ChannelManager:
    """Classe per gestire l'invio e il monitoraggio dei messaggi nei canali."""
    
    def __init__(self, cmd_handler=None):
        """
        Args:
            cmd_handler: Istanza di ComandiBot (passata dopo l'inizializzazione)
        """
        self.cmd_handler = cmd_handler
        self.logger = LoggerInfo(name="ChannelManager").get_logger()
        self.logger.info(f"🧩 Nuova istanza ChannelManager creata: {id(self)}")
        
        # Configurazione per la gestione di molti canali
        self.batch_size = 15  # Invia a N canali alla volta
        self.delay_between_batches = 8  # Secondi tra un batch e l'altro
        self.delay_between_sends = 3  # Secondi tra un invio e l'altro nello stesso batch
        self.max_concurrent_sends = 4  # Invii simultanei per batch
        self.max_retries = 3  # Tentativi massimi per canale
        
        # Lock per evitare invii multipli simultanei
        self._send_lock = asyncio.Lock()
    
    def set_cmd_handler(self, cmd_handler):
        """Imposta il riferimento al command handler dopo l'inizializzazione."""
        self.cmd_handler = cmd_handler
        self.logger.info("✅ Command handler collegato a ChannelManager")
    
    async def handle_forward_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler per quando l'utente inoltra il messaggio da pubblicare."""
        user_id = update.effective_user.id
        
        # Verifica che cmd_handler sia stato impostato
        if self.cmd_handler is None:
            self.logger.error("❌ cmd_handler non impostato in ChannelManager!")
            await update.message.reply_text(
                "⚠️ Errore di configurazione del bot. Contatta l'amministratore."
            )
            return
        
        # Verifica se l'utente è in stato di pubblicazione
        if not self.cmd_handler.publishing_state.get(user_id, False):
            self.logger.debug(
                f"Utente {user_id} non in stato pubblicazione, ignoro messaggio"
            )
            return
        
        # Verifica se c'è già un invio in corso
        if self._send_lock.locked():
            await update.message.reply_text(
                "⏸️ C'è già un invio in corso. Attendere il completamento..."
            )
            self.logger.warning(
                f"Utente {user_id} ha tentato invio durante altro invio in corso"
            )
            return
        
        async with self._send_lock:
            try:
                self.logger.info(
                    f"📨 Avvio pubblicazione messaggio da utente {user_id}"
                )
                Settings.processo_invio = True
                
                # Invia messaggio di avvio
                status_msg = await update.message.reply_text(
                    "📤 <b>Avvio pubblicazione...</b>\n"
                    "⏳ Recupero lista canali...",
                    parse_mode="HTML"
                )
                
                # Ottieni i canali dal database
                with DatabaseManager() as db:
                    channels = db.channel.fetch_all_channels()
                
                if not channels:
                    await status_msg.edit_text(
                        "⚠️ <b>Nessun canale registrato!</b>\n\n"
                        "Aggiungi il bot come amministratore in almeno un canale.",
                        parse_mode="HTML"
                    )
                    self.logger.warning("Nessun canale disponibile per la pubblicazione")
                    return
                
                total_channels = len(channels)
                self.logger.info(f"📊 Totale canali target: {total_channels}")
                
                await status_msg.edit_text(
                    f"📤 <b>Pubblicazione in corso...</b>\n"
                    f"📊 Canali da processare: {total_channels}\n"
                    f"⏳ Attendere...",
                    parse_mode="HTML"
                )
                
                # Pubblica il messaggio in batch
                results = await self._publish_to_channels_in_batches(
                    channels=channels,
                    message=update.message,
                    context=context,
                    status_msg=status_msg
                )
                
                # Analizza i risultati
                successi = results["successi"]
                fallimenti = results["fallimenti"]
                canali_rimossi = results["canali_rimossi"]
                
                # Messaggio di riepilogo
                emoji_status = "✅" if fallimenti == 0 else "⚠️"
                messaggio = (
                    f"{emoji_status} <b>Pubblicazione completata!</b>\n\n"
                    f"📊 <b>Statistiche:</b>\n"
                    f"✅ Successi: {successi}/{total_channels}\n"
                    f"❌ Fallimenti: {fallimenti}/{total_channels}\n"
                )
                
                if canali_rimossi > 0:
                    messaggio += f"🗑️ Canali rimossi: {canali_rimossi}\n"
                
                if fallimenti > 0:
                    messaggio += (
                        f"\n<i>Alcuni canali potrebbero aver rimosso il bot "
                        f"o presentare problemi di permessi.</i>"
                    )
                
                await status_msg.edit_text(messaggio, parse_mode="HTML")
                
                self.logger.info(
                    f"✅ Pubblicazione completata: {successi} successi, "
                    f"{fallimenti} fallimenti, {canali_rimossi} canali rimossi"
                )
                
            except Exception as e:
                self.logger.error(
                    f"❌ Errore critico durante pubblicazione: {e}", 
                    exc_info=True
                )
                await update.message.reply_text(
                    f"❌ <b>Errore durante la pubblicazione</b>\n\n"
                    f"<code>{str(e)}</code>",
                    parse_mode="HTML"
                )
                
            finally:
                # IMPORTANTE: Pulisci sempre lo stato, anche in caso di errore
                Settings.processo_invio = False
                
                if self.cmd_handler and user_id in self.cmd_handler.reset_tasks:
                    task = self.cmd_handler.reset_tasks[user_id]
                    if not task.done():
                        task.cancel()
                        self.logger.info(
                            f"✅ Task di timeout cancellato per utente {user_id}"
                        )
                    del self.cmd_handler.reset_tasks[user_id]
                
                if self.cmd_handler:
                    self.cmd_handler.publishing_state[user_id] = False
                Settings.invio = False
                
                self.logger.info(f"🧹 Stato pubblicazione resettato per utente {user_id}")
    
    async def _publish_to_channels_in_batches(self, channels: List[Tuple[str, str]], message: Message, context: ContextTypes.DEFAULT_TYPE, status_msg: 'Message') -> dict:
        """
        Pubblica il messaggio in tutti i canali usando elaborazione a batch.
        
        Returns:
            dict con chiavi: successi, fallimenti, canali_rimossi
        """
        results = {
            "successi": 0,
            "fallimenti": 0,
            "canali_rimossi": 0,
            "dettagli": []
        }
        
        total_batches = (len(channels) + self.batch_size - 1) // self.batch_size
        
        for i in range(0, len(channels), self.batch_size):
            batch = channels[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            
            self.logger.info(
                f"📦 Processando batch {batch_num}/{total_batches} "
                f"({len(batch)} canali)"
            )
            
            # Aggiorna messaggio di stato
            try:
                progress = (i / len(channels)) * 100
                await status_msg.edit_text(
                    f"📤 <b>Pubblicazione in corso...</b>\n"
                    f"📊 Progresso: {i}/{len(channels)} canali\n"
                    f"📈 {progress:.1f}% completato\n"
                    f"📦 Batch {batch_num}/{total_batches}",
                    parse_mode="HTML"
                )
            except TelegramError:
                pass  # Ignora errori nell'aggiornamento status
            
            # Processa il batch
            batch_results = await self._process_send_batch_with_semaphore(
                batch=batch,
                message=message,
                context=context
            )
            
            # Aggrega i risultati
            results["successi"] += batch_results["successi"]
            results["fallimenti"] += batch_results["fallimenti"]
            results["canali_rimossi"] += batch_results["canali_rimossi"]
            results["dettagli"].extend(batch_results["dettagli"])
            
            # Pausa tra i batch (eccetto l'ultimo)
            if i + self.batch_size < len(channels):
                self.logger.info(
                    f"⏸️ Pausa di {self.delay_between_batches}s tra i batch..."
                )
                await asyncio.sleep(self.delay_between_batches)
        
        return results
    
    async def _process_send_batch_with_semaphore(self,batch: List[Tuple[str, str]], message: Message, context: ContextTypes.DEFAULT_TYPE) -> dict:
        """Processa un batch di invii con semaforo per limitare la concorrenza."""
        semaphore = asyncio.Semaphore(self.max_concurrent_sends)
        
        results = {
            "successi": 0,
            "fallimenti": 0,
            "canali_rimossi": 0,
            "dettagli": []
        }
        results_lock = asyncio.Lock()
        
        async def send_with_semaphore(channel_data):
            async with semaphore:
                result = await self._send_to_single_channel(
                    channel_data=channel_data,
                    message=message,
                    context=context
                )
                
                # Aggiorna risultati in modo thread-safe
                async with results_lock:
                    if result["success"]:
                        results["successi"] += 1
                    else:
                        results["fallimenti"] += 1
                    
                    if result.get("channel_removed", False):
                        results["canali_rimossi"] += 1
                    
                    results["dettagli"].append(result)
                
                # Pausa tra gli invii
                await asyncio.sleep(self.delay_between_sends)
        
        # Esegui tutti gli invii del batch in parallelo (limitato dal semaforo)
        tasks = [send_with_semaphore(channel) for channel in batch]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        return results
    
    async def _send_to_single_channel(self,channel_data: Tuple[str, str], message: Message, context: ContextTypes.DEFAULT_TYPE) -> dict:
        """
        Invia il messaggio a un singolo canale con retry logic.
        Elimina il vecchio messaggio se presente e aggiorna il database.
        
        Returns:
            dict con informazioni sul risultato dell'invio
        """
        chat_id, title = channel_data
        original_message_id = message.message_id
        
        result = {
            "chat_id": chat_id,
            "title": title,
            "success": False,
            "channel_removed": False,
            "error": None,
            "attempts": 0,
            "old_message_deleted": False
        }
        
        # Recupera il vecchio messaggio inoltrato dal database
        old_forwarded_message_id = None
        try:
            with DatabaseManager() as db:
                old_post = db.post.get_post_by_channel(chat_id)
                if old_post:
                    old_forwarded_message_id = old_post["forwarded_message_id"]
                    self.logger.debug(
                        f"📝 Trovato vecchio messaggio inoltrato {old_forwarded_message_id} in {title} dal database"
                    )
        except Exception as e:
            self.logger.warning(
                f"⚠️ Errore recupero vecchio messaggio per {title}: {e}"
            )
        
        # Tentativo di eliminazione del vecchio messaggio inoltrato
        if old_forwarded_message_id:
            try:
                await context.bot.delete_message(
                    chat_id=int(chat_id),
                    message_id=old_forwarded_message_id
                )
                result["old_message_deleted"] = True
                self.logger.info(
                    f"🗑️ Vecchio messaggio {old_forwarded_message_id} eliminato da {title}"
                )
            except BadRequest as e:
                # Messaggio già eliminato o non trovato
                error_msg = str(e).lower()
                if "message to delete not found" in error_msg or "message can't be deleted" in error_msg:
                    self.logger.info(
                        f"ℹ️ Vecchio messaggio {old_forwarded_message_id} già eliminato o non trovato in {title}. Errore verificato: {e}"
                    )
                else:
                    self.logger.warning(
                        f"⚠️ Impossibile eliminare vecchio messaggio in {title}: {e}"
                    )
            except Forbidden:
                # Il bot non ha più accesso al canale
                self.logger.warning(
                    f"⚠️ Accesso negato durante eliminazione in {title}"
                )
            except TelegramError as e:
                self.logger.warning(
                    f"⚠️ Errore eliminazione vecchio messaggio in {title}: {e}"
                )
        
        # Invio del nuovo messaggio con retry
        for attempt in range(1, self.max_retries + 1):
            result["attempts"] = attempt
            
            try:
                # Invia il nuovo messaggio
                sent_message = await rate_limiter.execute(
                    chat_id=chat_id,
                    coro_factory=lambda cid=chat_id: context.bot.copy_message(
                        chat_id=int(cid),
                        from_chat_id=message.chat_id,
                        message_id=message.message_id,
                        reply_markup=message.reply_markup,
                    ),
                )
                
                # Aggiorna il database con upsert
                try:
                    with DatabaseManager() as db:
                        db.post.upsert_post(
                            original_message_id=original_message_id,
                            channel_chat_id=chat_id,
                            forwarded_message_id=sent_message.message_id
                        )
                    
                    result["success"] = True
                    result["message_id"] = sent_message.message_id
                    
                    log_msg = f"✅ Pubblicato in {title} ({chat_id}) [msg_id: {sent_message.message_id}]"
                    if old_forwarded_message_id:
                        log_msg += f" (sostituito {old_forwarded_message_id})"
                    log_msg += f" [tentativo {attempt}/{self.max_retries}]"
                    
                    self.logger.info(log_msg)
                    
                    return result
                    
                except Exception as db_error:
                    self.logger.error(
                        f"❌ Errore aggiornamento database per {title}: {db_error}"
                    )
                    # Anche se il DB fallisce, consideriamo l'invio riuscito
                    result["success"] = True
                    result["message_id"] = sent_message.message_id
                    result["error"] = f"Messaggio inviato ma errore DB: {db_error}"
                    return result
                    
            except RetryAfter as e:
                wait_time = e.retry_after + 2  # usa il valore indicato da Telegram + piccolo buffer
                
                if attempt == self.max_retries:
                    result["error"] = f"Rate limit dopo {attempt} tentativi"
                    self.logger.error(
                        f"❌ Rate limit superato per {title}: {e}"
                    )
                    break
                
                self.logger.warning(
                    f"⏳ Rate limit su {title}, attesa {wait_time}s "
                    f"(tentativo {attempt}/{self.max_retries})"
                )
                await asyncio.sleep(wait_time) ## Convertito in esponenziale
                
            except (BadRequest, Forbidden) as e:
                # Check se la chat è raggiungibile attraverso utils
                if TEC.è_chat_irraggiungibile(e):
                    result["error"] = "Canale non trovato o bot rimosso"
                    result["channel_removed"] = True
                    self.logger.warning(f"⚠️ Accesso negato a {title} ({chat_id}): {e}")
                    await self._remove_channel_after_error(chat_id, title, context)
                else:
                    result["error"] = f"BadRequest non classificata: {e}"
                    self.logger.warning(f"⚠️ [{TEC.classifica(e)}] BadRequest per '{title}' ({chat_id}): {e}")

                break
           
            except TelegramError as e:

                if TEC.è_chat_irraggiungibile(e):
                    result["error"] = "Canale non trovato o bot rimosso"
                    result["channel_removed"] = True
                    self.logger.warning(f"🚫 [{TEC.classifica(e)}] Chat irraggiungibile '{title}' ({chat_id}): {e}")
                    await self._remove_channel_after_error(chat_id, title, context)
                    break

                if attempt == self.max_retries:
                    result["error"] = f"Errore Telegram: {e}"
                    self.logger.error(f"❌ [{TEC.classifica(e)}] Errore persistente per '{title}' ({chat_id}): {e}")
                    break
                

                self.logger.warning(f"⚠️ [{TEC.classifica(e)}] Errore temporaneo per '{title}', riprovo... "f"(tentativo {attempt}/{self.max_retries}): {e}")
                await asyncio.sleep(2 ** attempt)  # Backoff esponenziale
                
            except Exception as e:
                result["error"] = f"Errore imprevisto: {e}"
                self.logger.error(
                    f"❌ Errore imprevisto pubblicando in {title}: {e}",
                    exc_info=True
                )
                break
        
        return result
    
    async def _remove_channel_after_error(self,chat_id: str,title: str,context: ContextTypes.DEFAULT_TYPE):
        """Rimuove un canale dal database dopo un errore di accesso."""
        try:
            with DatabaseManager() as db:
                db.channel.delete_channel(chat_id)
            
            self.logger.info(f"🗑️ Canale {title} ({chat_id}) rimosso dal database")
            
            # Notifica admin
            try:
                await context.bot.send_message(
                    chat_id=Settings.ADMIN_ID,
                    text=(
                        f"⚠️ <b>Canale rimosso automaticamente</b>\n\n"
                        f"📺 <b>Titolo:</b> {title}\n"
                        f"🆔 <b>ID:</b> <code>{chat_id}</code>\n\n"
                        f"<i>Motivo: Bot rimosso o canale eliminato</i>"
                    ),
                    parse_mode="HTML"
                )
            except TelegramError as e:
                self.logger.error(f"❌ [{TEC.classifica(e)}] Errore notifica admin rimozione: {e}")
                
        except Exception as e:
            self.logger.error(
                f"❌ Errore durante rimozione canale {chat_id}: {e}"
            )

    async def remove_channel_by_admin(self, chat_id: str, context: ContextTypes.DEFAULT_TYPE):
        try:
            with DatabaseManager() as db:
                eliminato = db.channel.delete_channel(chat_id)
                if eliminato:
                    await context.bot.send_message(chat_id=int(chat_id), text="❌ Questo canale è stato rimosso dal registro.")
        except Exception as errore:
            self.logger.info(f"Errore riscontrato: {errore}")
        