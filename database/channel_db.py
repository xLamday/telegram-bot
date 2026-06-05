from typing import List, Tuple, Optional
from .base import BaseDatabase
import sqlite3
from loggerinfo import LoggerInfo


class ChannelDatabase(BaseDatabase):
    def __init__(self):
        self.logger = LoggerInfo(name="ChannelDatabase").get_logger()

    # ------------------- CHANNELS -------------------

    def fetch_all_channels(self) -> List[Tuple[int, Optional[str]]]:
        return self._fetch_all("SELECT chat_id, title FROM channels")

    def delete_channel(self, chat_id: int) -> bool:
        cursor_posts = self._execute(
            "DELETE FROM posts WHERE channel_chat_id=?", (chat_id,)
        )
        cursor_channel = self._execute(
            "DELETE FROM channels WHERE chat_id=?", (chat_id,)
        )

        if cursor_posts is None or cursor_channel is None:
            raise sqlite3.Error(f"Errore eliminazione canale {chat_id}")

        if cursor_channel.rowcount == 0:
            self.logger.info(f"Canale {chat_id} non trovato nel DB")
            return False

        self.logger.info(f"Canale {chat_id} e post associati eliminati dal DB")
        return True

    def _delete_only_channel(self, chat_id: int) -> bool:
        """
        Elimina solamente il canale lasciando i post.

        - Per eliminare anche i post, usare delete_channel.
        - Per eliminare solo il canale, usare questa funzione.

        Args:
            chat_id: ID del canale

        Returns:
            True se completato con successo, False se non trovato
        """
        cursor = self._execute(
            "DELETE FROM channels WHERE chat_id=?", (chat_id,)
        )
        if cursor is None:
            raise sqlite3.Error(f"Errore eliminazione canale {chat_id}")
        if cursor.rowcount == 0:
            self.logger.info(f"Canale {chat_id} non trovato nel DB")
            return False
        self.logger.info(f"Canale {chat_id} rimosso dal database")
        return True

    def channel_exists(self, chat_id: int) -> bool:
        return self._fetch_one(
            "SELECT 1 FROM channels WHERE chat_id=? LIMIT 1", (chat_id,)
        ) is not None

    # ------------------- UTILITY -------------------

    def add_channel(self, chat_id: int, title: str) -> bool:
        cursor = self._execute(
            "INSERT OR IGNORE INTO channels (chat_id, title) VALUES (?, ?)",
            (chat_id, title)
        )
        if cursor is None:
            raise sqlite3.Error(f"Errore aggiunta canale {chat_id}")
        return cursor.rowcount == 1