# database.py
import sqlite3
from typing import List, Tuple, Optional
from database.connection import get_connection
from loggerinfo import LoggerInfo


class DatabaseManager:
    """Gestione del DB SQLite (sincrono)."""

    def __init__(self):
        self.conn: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None
        self.logger = LoggerInfo(name="Database").get_logger()

    # ------------------- CONTEXT MANAGER -------------------
    def __enter__(self):
        self.conn = get_connection()
        self.cursor = self.conn.cursor()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            if exc_type is not None:
                self.conn.rollback()
            else:
                self.conn.commit()
                self.cursor.close()
                self.conn.close()

    # ------------------- POSTS -------------------
    def fetch_all_posts(self) -> List[Tuple[int, int, Optional[str]]]:
        query = """
            SELECT p.channel_chat_id, p.forwarded_message_id, c.title
            FROM posts p
            LEFT JOIN channels c ON p.channel_chat_id = c.chat_id
        """
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def delete_post(self, channel_chat_id: int, forwarded_message_id: int) -> Optional[bool]:
        """
            Elimina il post più recente per un canale specifico.
            
            Args:
                chat_id: ID del canale
                
            Returns:
                booleano con 'True' se completato con successo, oppure False se non trovato o errore
        """
        try:
            self.cursor.execute(
                "DELETE FROM posts WHERE channel_chat_id=? AND forwarded_message_id=?",
                (channel_chat_id, forwarded_message_id)
            )
            self.conn.commit()
            self.logger.info(f"Post {forwarded_message_id} rimosso dal canale {channel_chat_id}")
            return True
        except sqlite3.Error as e:
            self.logger.error(f"Errore eliminazione post per canale {channel_chat_id}: {e}")
            return False

    def count_posts(self, channel_chat_id: int) -> int:
        self.cursor.execute(
            "SELECT COUNT(*) FROM posts WHERE channel_chat_id=?", (channel_chat_id,)
        )
        result = self.cursor.fetchone()
        return result[0] if result else 0

    
    def get_post_by_channel(self, channel_chat_id: int) -> Optional[dict]:
        """
        Recupera il post più recente per un canale specifico.
        
        Args:
            chat_id: ID del canale
        Returns:
            dict con 'original_message_id' e 'forwarded_message_id', oppure None se non trovato
        """
        try:
            self.cursor.execute(
                "SELECT original_message_id, forwarded_message_id FROM posts WHERE channel_chat_id = ?",
                (channel_chat_id,)
            )
            row = self.cursor.fetchone()
            
            if row:
                return {
                    "original_message_id": row[0],
                    "forwarded_message_id": row[1]
                }
            return None
            
        except sqlite3.Error as e:
            self.logger.error(f"Errore recupero post per canale {channel_chat_id}: {e}")
            return None

    def get_duplicate_posts(self) -> List[Tuple[int, int]]:
        """
        Recupera i post duplicati per ogni canale.
        
        Returns:
            List[Tuple[int, int]] con 'channel_chat_id' e 'count'
        """
        try:
            self.cursor.execute("""
                SELECT p.channel_chat_id, COUNT(*) as count, c.title
                FROM posts p
                LEFT JOIN channels c ON p.channel_chat_id = c.chat_id
                GROUP BY p.channel_chat_id
                HAVING COUNT(*) > 1
            """)
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            self.logger.error(f"Errore recupero duplicati: {e}")
            return []

    def remove_duplicate_posts(self) -> int:
        """
        Elimina i post duplicati per ogni canale, mantenendo solo il più recente (id maggiore).
        
        Returns:
            Numero di duplicati eliminati
        """
        try:
            # Trova i canali con duplicati prima di eliminarli
            self.cursor.execute("""
                SELECT p.channel_chat_id, COUNT(*) as count, c.title
                FROM posts p
                LEFT JOIN channels c ON p.channel_chat_id = c.chat_id
                GROUP BY p.channel_chat_id
                HAVING COUNT(*) > 1
            """)
            duplicati = self.cursor.fetchall()
            
            if not duplicati:
                self.logger.info("Nessun post duplicato trovato")
                return 0
            
            for channel_chat_id, count, title in duplicati:
                nome = title if title else channel_chat_id
                self.logger.info(f"Canale con titolo '{nome}' ha {count} post duplicati, verrà mantenuto solo il più recente")

            # Elimina i duplicati
            self.cursor.execute("""
                DELETE FROM posts
                WHERE id NOT IN (
                    SELECT MAX(id)
                    FROM posts
                    GROUP BY channel_chat_id
                )
            """)
            deleted_count = self.cursor.rowcount
            self.conn.commit()
            self.logger.info(f"Rimossi {deleted_count} post duplicati in totale")
            return deleted_count
        
        except sqlite3.Error as e:
            self.logger.error(f"Errore rimozione duplicati: {e}")
            return 0

    def post_exists(self, channel_chat_id: int, forwarded_message_id: int) -> bool:
        self.cursor.execute(
            "SELECT 1 FROM posts WHERE channel_chat_id=? AND forwarded_message_id=? LIMIT 1",
            (channel_chat_id, forwarded_message_id)
        )
        return self.cursor.fetchone() is not None
    
    def upsert_post(self, original_message_id: int, channel_chat_id: int, forwarded_message_id: int):
        """
        Inserisce o aggiorna un post nel database.
        Se esiste già un post per quel canale con lo stesso original_message_id, lo aggiorna.
        Altrimenti elimina i vecchi post e inserisce il nuovo.
        
        Args:
            original_message_id: ID del messaggio originale
            channel_chat_id: ID del canale
            forwarded_message_id: ID del messaggio inoltrato nel canale
        """
        try:
            # Prima elimina eventuali post precedenti per questo canale
            self.cursor.execute(
                "DELETE FROM posts WHERE channel_chat_id = ?",
                (channel_chat_id,)
            )
            
            # Inserisce il nuovo post
            self.cursor.execute(
                """
                INSERT INTO posts (original_message_id, channel_chat_id, forwarded_message_id)
                VALUES (?, ?, ?)
                """,
                (original_message_id, channel_chat_id, forwarded_message_id)
            )
            
            self.conn.commit()
            self.logger.debug(
                f"Post upsert per canale {channel_chat_id}: "
                f"original={original_message_id}, forwarded={forwarded_message_id}"
            )
            
        except sqlite3.Error as e:
            self.logger.error(f"Errore upsert post: {e}")
            raise

    def delete_all_posts_by_channel(self, channel_chat_id: int) -> int:
        """
        Elimina tutti i post associati a un canale.
        
        Args:
            channel_chat_id: ID del canale
            
        Returns:
            Numero di post eliminati
        """
        try:
            self.cursor.execute(
                "DELETE FROM posts WHERE channel_chat_id = ?",
                (channel_chat_id,)
            )
            deleted_count = self.cursor.rowcount
            self.conn.commit()
            self.logger.debug(f"Eliminati {deleted_count} post per canale {channel_chat_id}")
            return deleted_count
            
        except sqlite3.Error as e:
            self.logger.error(f"Errore eliminazione post per canale {channel_chat_id}: {e}")
            return 0

    # ------------------- CHANNELS -------------------
    def fetch_all_channels(self) -> List[Tuple[int, Optional[str]]]:
        self.cursor.execute("SELECT chat_id, title FROM channels")
        return self.cursor.fetchall()

    def delete_channel(self, chat_id: int):
        self.cursor.execute("DELETE FROM posts WHERE channel_chat_id=?", (chat_id,))
        self.cursor.execute("DELETE FROM channels WHERE chat_id=?", (chat_id,))
        self.conn.commit()
        self.logger.info(f"Canale {chat_id} e post associati eliminati dal DB")

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
            self.cursor.execute("DELETE FROM channels WHERE chat_id=?", (chat_id,))
            self.conn.commit()
            self.logger.info(f"Canale {chat_id} è stato rimosso dal database")
            return True
        except sqlite3.Error as e:
            self.logger.error(f"Errore eliminazione canale {chat_id}: {e}")
            return False

    def channel_exists(self, chat_id: int) -> bool:
        self.cursor.execute("SELECT 1 FROM channels WHERE chat_id=? LIMIT 1", (chat_id,))
        return self.cursor.fetchone() is not None

    # ------------------- UTILITY -------------------
    def add_channel(self, chat_id: int, title: str):
        if not self.channel_exists(chat_id):
            self.cursor.execute(
                "INSERT INTO channels (chat_id, title) VALUES (?, ?)",
                (chat_id, title)
            )
            self.conn.commit()
            self.logger.info(f"Nuovo canale aggiunto: {chat_id} - {title}")
