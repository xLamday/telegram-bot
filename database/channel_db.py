from typing import List, Tuple, Optional
import json
from .base import BaseDatabase
import sqlite3
from loggerinfo import LoggerInfo




class ChannelDatabase(BaseDatabase):
    def __init__(self):
        self.logger = LoggerInfo(name="ChannelDatabase").get_logger()
 # ------------------- CHANNELS -------------------
    def fetch_all_channels(self) -> List[Tuple[int, Optional[str]]]:
        return self._fetch_all("SELECT chat_id, title FROM channels")

    def delete_channel(self, chat_id: int):
        try:
            self._execute("DELETE FROM posts WHERE channel_chat_id=?", (chat_id,))
            self._execute("DELETE FROM channels WHERE chat_id=?", (chat_id,))
            deleted_count = self.cursor.rowcount
            if deleted_count == 0:
                self.logger.info(f"Canale {chat_id} non trovato nel DB")
                return False
            self.logger.info(f"Canale {chat_id} e post associati eliminati dal DB")
            return True
        except sqlite3.Error as e:
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
            self._execute("DELETE FROM channels WHERE chat_id=?", (chat_id,))
            self.logger.info(f"Canale {chat_id} è stato rimosso dal database")
            return True
        except sqlite3.Error as e:
            self.logger.error(f"Errore eliminazione canale {chat_id}: {e}")
            return False

    def channel_exists(self, chat_id: int) -> bool:
        return self._fetch_one(
            "SELECT 1 FROM channels WHERE chat_id=? LIMIT 1", (chat_id,)
        ) is not None

    # ------------------- UTILITY -------------------
    def add_channel(self, chat_id: int, title: str) -> bool:
        """
            Aggiunge un canale al database se non esiste già.
            
            Args:
                chat_id: ID del canale
                title: Titolo del canale
                
            Returns:
                booleano con 'True' se il canale è stato aggiunto, oppure False se già esistente o errore
        """
        before = self._fetch_one(
            "SELECT 1 FROM channels WHERE chat_id=?",
            (chat_id,)
        )

        self._execute(
            "INSERT OR IGNORE INTO channels (chat_id, title) VALUES (?, ?)",
            (chat_id, title)
        )

        self.conn.commit()

        return before is None

        
