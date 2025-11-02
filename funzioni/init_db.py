
import sqlite3
from config import DB_FILE

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Tabella canali
    c.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            chat_id TEXT PRIMARY KEY,
            title TEXT
        )
    """)
    # Tabella post pubblicati
    c.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            original_message_id INTEGER,
            channel_chat_id TEXT,
            forwarded_message_id INTEGER,
            PRIMARY KEY (channel_chat_id)
        )
    """)

    conn.commit()
    conn.close()