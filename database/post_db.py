from typing import List, Tuple, Optional
from .base import BaseDatabase
import sqlite3
from loggerinfo import LoggerInfo


class PostDatabase(BaseDatabase):
    def __init__(self):
        self.logger = LoggerInfo(name="PostDatabase").get_logger()

    # ------------------- POSTS -------------------

    def fetch_all_posts(self) -> List[Tuple[int, int, Optional[str]]]:
        query = """
            SELECT p.channel_chat_id, p.forwarded_message_id, c.title
            FROM posts p
            LEFT JOIN channels c ON p.channel_chat_id = c.chat_id
        """
        return self._fetch_all(query)

    def delete_post(self, channel_chat_id: int, forwarded_message_id: int) -> bool:
        cursor = self._execute(
            "DELETE FROM posts WHERE channel_chat_id=? AND forwarded_message_id=?",
            (channel_chat_id, forwarded_message_id)
        )
        if cursor is None:
            raise sqlite3.Error(f"Errore eliminazione post {forwarded_message_id} dal canale {channel_chat_id}")
        if cursor.rowcount == 0:
            self.logger.info(f"Post {forwarded_message_id} non trovato nel canale {channel_chat_id}")
            return False
        self.logger.info(f"Post {forwarded_message_id} rimosso dal canale {channel_chat_id}")
        return True

    def count_posts(self, channel_chat_id: int) -> int:
        result = self._fetch_one(
            "SELECT COUNT(*) FROM posts WHERE channel_chat_id=?", (channel_chat_id,)
        )
        return result[0] if result else 0

    def get_post_by_channel(self, channel_chat_id: int) -> Optional[dict]:
        row = self._fetch_one(
            "SELECT original_message_id, forwarded_message_id FROM posts WHERE channel_chat_id=?",
            (channel_chat_id,)
        )
        if row:
            return {
                "original_message_id": row[0],
                "forwarded_message_id": row[1]
            }
        return None

    def get_duplicate_posts(self) -> List[Tuple[int, int]]:
        return self._fetch_all("""
            SELECT p.channel_chat_id, COUNT(*) as count, c.title
            FROM posts p
            LEFT JOIN channels c ON p.channel_chat_id = c.chat_id
            GROUP BY p.channel_chat_id
            HAVING COUNT(*) > 1
        """)

    def remove_duplicate_posts(self) -> int:
        """
        Elimina i post duplicati per ogni canale, mantenendo solo il più recente (id maggiore).

        Returns:
            Numero di duplicati eliminati, -1 se nessun duplicato trovato
        """
        duplicati = self._fetch_all("""
            SELECT p.channel_chat_id, COUNT(*) as count, c.title
            FROM posts p
            LEFT JOIN channels c ON p.channel_chat_id = c.chat_id
            GROUP BY p.channel_chat_id
            HAVING COUNT(*) > 1
        """)

        if not duplicati:
            self.logger.info("Nessun post duplicato trovato")
            return 0

        for channel_chat_id, count, title in duplicati:
            nome = title if title else channel_chat_id
            self.logger.info(
                f"Canale '{nome}' ha {count} post duplicati, verrà mantenuto solo il più recente"
            )

        cursor = self._execute("""
            DELETE FROM posts
            WHERE id NOT IN (
                SELECT MAX(id)
                FROM posts
                GROUP BY channel_chat_id
            )
        """)

        if cursor is None:
            raise sqlite3.Error("Errore durante la rimozione dei duplicati")

        deleted_count = cursor.rowcount
        self.logger.info(f"Rimossi {deleted_count} post duplicati in totale")
        return deleted_count

    def post_exists(self, channel_chat_id: int, forwarded_message_id: int) -> bool:
        return self._fetch_one(
            "SELECT 1 FROM posts WHERE channel_chat_id=? AND forwarded_message_id=? LIMIT 1",
            (channel_chat_id, forwarded_message_id)
        ) is not None

    def upsert_post(self, original_message_id: int, channel_chat_id: int, forwarded_message_id: int) -> bool:
        """
        Elimina i post precedenti del canale e inserisce il nuovo.
        Le due operazioni sono atomiche grazie al commit del DatabaseManager.
        """
        cursor_del = self._execute(
            "DELETE FROM posts WHERE channel_chat_id=?",
            (channel_chat_id,)
        )
        cursor_ins = self._execute(
            """
            INSERT INTO posts (original_message_id, channel_chat_id, forwarded_message_id)
            VALUES (?, ?, ?)
            """,
            (original_message_id, channel_chat_id, forwarded_message_id)
        )

        if cursor_del is None or cursor_ins is None:
            raise sqlite3.Error(f"Errore upsert post per canale {channel_chat_id}")

        self.logger.debug(
            f"Post upsert per canale {channel_chat_id}: "
            f"original={original_message_id}, forwarded={forwarded_message_id}"
        )
        return True

    def delete_all_posts_by_channel(self, channel_chat_id: int) -> int:
        """
        Returns:
            Numero di post eliminati
        """
        cursor = self._execute(
            "DELETE FROM posts WHERE channel_chat_id=?",
            (channel_chat_id,)
        )
        if cursor is None:
            raise sqlite3.Error(f"Errore eliminazione post per canale {channel_chat_id}")
        deleted_count = cursor.rowcount
        self.logger.debug(f"Eliminati {deleted_count} post per canale {channel_chat_id}")
        return deleted_count