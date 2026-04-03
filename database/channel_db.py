from typing import List, Tuple, Optional
import json
from .base import BaseDatabase
import psycopg2
from loggerinfo import LoggerInfo




class ChannelDatabase(BaseDatabase):
    def __init__(self):
        self.logger = LoggerInfo(name="ChannelDatabase").get_logger()
 # ------------------- CHANNELS -------------------
    def fetch_all_channels(self) -> List[Tuple[int, Optional[str]]]:
        return self._fetch_all("SELECT chat_id, title FROM channels")

    def delete_channel(self, chat_id: int):
        try:
            self._execute("DELETE FROM posts WHERE channel_chat_id=%s", (chat_id,))
            self._execute("DELETE FROM channels WHERE chat_id=%s", (chat_id,))
            self.logger.info(f"Canale {chat_id} e post associati eliminati dal DB")
        except psycopg2.Error as e:
            self.logger.error(f"Errore eliminazione canale {chat_id}: {e}")
            return False

    def _delete_only_channel(self, chat_id: int):
        """
            Elimina solamente il canale lasciando i post. 
            
            - In caso si voglia eliminare i post e canale, usare delete_channel.
            - In caso so voglia eliminare solo il canale, usare solo questa funzione.
            
            
            Args:
                chat_id: ID del canale
                
            Returns:
                booleano con 'True' se completato con successo, oppure False se non trovato o errore
        """
        try:
            self._execute("DELETE FROM channels WHERE chat_id=%s", (chat_id,))
            self.logger.info(f"Canale {chat_id} è stato rimosso dal database")
            return True
        except psycopg2.Error as e:
            self.logger.error(f"Errore eliminazione canale {chat_id}: {e}")
            return False

    def channel_exists(self, chat_id: int) -> bool:
        return self._fetch_one(
            "SELECT 1 FROM channels WHERE chat_id=%s LIMIT 1", (chat_id,)
        ) is not None

    # ------------------- UTILITY -------------------
    def add_channel(self, chat_id: int, title: str):
        if not self.channel_exists(chat_id):
            self._execute(
                "INSERT INTO channels (chat_id, title) VALUES (%s, %s)",
                (chat_id, title)
            )
            self.logger.info(f"Nuovo canale aggiunto: {chat_id} - {title}")
