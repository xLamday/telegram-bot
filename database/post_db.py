from typing import List, Tuple, Optional
import json
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

    def delete_post(self, channel_chat_id: int, forwarded_message_id: int) -> Optional[bool]:
        """
            Elimina il post più recente per un canale specifico.
            
            Args:
                chat_id: ID del canale
                
            Returns:
                booleano con 'True' se completato con successo, oppure False se non trovato o errore
        """
        try:
            self._execute(
                "DELETE FROM posts WHERE channel_chat_id=? AND forwarded_message_id=?",
                (channel_chat_id, forwarded_message_id)
            )
            self.logger.info(f"Post {forwarded_message_id} rimosso dal canale {channel_chat_id}")
            return True
        except sqlite3.Error as e:
            self.logger.error(f"Errore eliminazione post per canale {channel_chat_id}: {e}")
            return False

    def count_posts(self, channel_chat_id: int) -> int:
        result = self._fetch_one(
            "SELECT COUNT(*) FROM posts WHERE channel_chat_id=?", (channel_chat_id,)
        )
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
            row = self._fetch_one(
                "SELECT original_message_id, forwarded_message_id FROM posts WHERE channel_chat_id = ?",
                (channel_chat_id,)
            )
            
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
            return self._fetch_all("""
                SELECT p.channel_chat_id, COUNT(*) as count, c.title
                FROM posts p
                LEFT JOIN channels c ON p.channel_chat_id = c.chat_id
                GROUP BY p.channel_chat_id
                HAVING COUNT(*) > 1
            """)
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
            self.logger.info(f"Rimossi {deleted_count} post duplicati in totale")
            return deleted_count
        
        except sqlite3.Error as e:
            self.logger.error(f"Errore rimozione duplicati: {e}")
            return 0

    def post_exists(self, channel_chat_id: int, forwarded_message_id: int) -> bool:
        return self._fetch_one(
            "SELECT 1 FROM posts WHERE channel_chat_id=? AND forwarded_message_id=? LIMIT 1",
            (channel_chat_id, forwarded_message_id)
        ) is not None
    
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
            self._execute(
                "DELETE FROM posts WHERE channel_chat_id = ?",
                (channel_chat_id,)
            )
            
            # Inserisce il nuovo post
            self._execute(
                """
                INSERT INTO posts (original_message_id, channel_chat_id, forwarded_message_id)
                VALUES (?, ?, ?)
                """,
                (original_message_id, channel_chat_id, forwarded_message_id)
            )
            
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
            self._execute(
                "DELETE FROM posts WHERE channel_chat_id = ?",
                (channel_chat_id,)
            )
            deleted_count = self.cursor.rowcount
            self.logger.debug(f"Eliminati {deleted_count} post per canale {channel_chat_id}")
            return deleted_count
            
        except sqlite3.Error as e:
            self.logger.error(f"Errore eliminazione post per canale {channel_chat_id}: {e}")
            return 0