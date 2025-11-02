"""
Database connection management.
"""
import sqlite3
from config.settings import Settings
import logging

def get_connection():
    """Get a database connection."""
    return sqlite3.connect(Settings.DATABASE_PATH)

    
def setup_database():
    """Crea tutte le tabelle necessarie per il bot."""
    conn = get_connection()
    cursor = conn.cursor()

    tables = [
        # Tabella dei canali
        """
        CREATE TABLE IF NOT EXISTS channels (
            chat_id INTEGER PRIMARY KEY,
            title TEXT
        )
        """,
        # Tabella dei post pubblicati
        """
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_chat_id INTEGER NOT NULL,
            forwarded_message_id INTEGER NOT NULL,
            FOREIGN KEY(channel_chat_id) REFERENCES channels(chat_id) ON DELETE CASCADE,
            UNIQUE(channel_chat_id, forwarded_message_id)
        )
        """
    ]

    for table_query in tables:
        cursor.execute(table_query)

    # # Gestione migrazioni future (esempio: aggiunta colonne)
    # try:
    #     # Controlla se esistono colonne aggiuntive nella tabella channels
    #     cursor.execute("PRAGMA table_info(channels)")
    #     columns = [column[1] for column in cursor.fetchall()]
    #     if 'created_at' not in columns:
    #         cursor.execute("ALTER TABLE channels ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    #         logging.info("Aggiunto created_at column to channels table")
    #     if 'updated_at' not in columns:
    #         cursor.execute("ALTER TABLE channels ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    #         logging.info("Aggiunto updated_at column to channels table")
    # except Exception as e:
    #     logging.warning(f"Migration error (non-critical): {e}")

    conn.commit()
    conn.close()