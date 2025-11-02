# database.py
import sqlite3
from typing import List, Tuple, Optional
from database.connection import get_connection
from loggerinfo import logger


class DatabaseManager:
    """Gestione del DB SQLite (sincrono)."""

    def __init__(self):
        self.conn: Optional[sqlite3.Connection] = None

    # ------------------- CONTEXT MANAGER -------------------
    def __enter__(self):
        self.conn = get_connection()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.commit()
            self.conn.close()

    # ------------------- POSTS -------------------
    def fetch_all_posts(self) -> List[Tuple[int, int, Optional[str]]]:
        query = """
            SELECT p.channel_chat_id, p.forwarded_message_id, c.title
            FROM posts p
            LEFT JOIN channels c ON p.channel_chat_id = c.chat_id
        """
        cursor = self.conn.cursor()
        cursor.execute(query)
        return cursor.fetchall()

    def delete_post(self, channel_chat_id: int, forwarded_message_id: int):
        self.conn.execute(
            "DELETE FROM posts WHERE channel_chat_id=? AND forwarded_message_id=?",
            (channel_chat_id, forwarded_message_id)
        )
        self.conn.commit()
        logger.info(f"Post {forwarded_message_id} rimosso dal canale {channel_chat_id}")

    def count_posts(self, channel_chat_id: int) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM posts WHERE channel_chat_id=?", (channel_chat_id,)
        )
        result = cursor.fetchone()
        return result[0] if result else 0

    def post_exists(self, channel_chat_id: int, forwarded_message_id: int) -> bool:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT 1 FROM posts WHERE channel_chat_id=? AND forwarded_message_id=? LIMIT 1",
            (channel_chat_id, forwarded_message_id)
        )
        return cursor.fetchone() is not None
    
    def upsert_post(self, original_message_id: int, channel_chat_id: int, forwarded_message_id: int):
        """
        Inserisce o aggiorna un post nel DB.
        Se il post esiste già per quel canale, viene sostituito.
        """
        query = """
            REPLACE INTO posts (original_message_id, channel_chat_id, forwarded_message_id)
            VALUES (?, ?, ?)
        """
        self.conn.execute(query, (original_message_id, channel_chat_id, forwarded_message_id))
        self.conn.commit()
        logger.info(f"Post {forwarded_message_id} salvato per canale {channel_chat_id}")

    # ------------------- CHANNELS -------------------
    def fetch_all_channels(self) -> List[Tuple[int, Optional[str]]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT chat_id, title FROM channels")
        return cursor.fetchall()

    def delete_channel(self, chat_id: int):
        self.conn.execute("DELETE FROM posts WHERE channel_chat_id=?", (chat_id,))
        self.conn.execute("DELETE FROM channels WHERE chat_id=?", (chat_id,))
        self.conn.commit()
        logger.info(f"Canale {chat_id} e post associati eliminati dal DB")

    def channel_exists(self, chat_id: int) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM channels WHERE chat_id=? LIMIT 1", (chat_id,))
        return cursor.fetchone() is not None

    # ------------------- UTILITY -------------------
    def add_channel(self, chat_id: int, title: str):
        if not self.channel_exists(chat_id):
            self.conn.execute(
                "INSERT INTO channels (chat_id, title) VALUES (?, ?)",
                (chat_id, title)
            )
            self.conn.commit()
            logger.info(f"Nuovo canale aggiunto: {chat_id} - {title}")
