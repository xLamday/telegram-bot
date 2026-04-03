"""
PostgreSQL database connection management.
"""

import psycopg2
from config.db_config import DatabaseConfig
from loggerinfo import LoggerInfo

logger = LoggerInfo(name="DB").get_logger()
def get_connection():
    """Get PostgreSQL connection."""
    return psycopg2.connect(
        host=DatabaseConfig.HOST,
        port=DatabaseConfig.PORT,
        dbname=DatabaseConfig.NAME,
        user=DatabaseConfig.USER,
        password=DatabaseConfig.PASSWORD
    )


def setup_database():
    """Crea  tutte le tabelle richieste per il bot se non esistono"""
    conn = get_connection()
    cursor = conn.cursor()
    logger.info(f"[Postgres-SQL] Connessione al database inizializzata!")
    tables = [

        # Channels table
        """
        CREATE TABLE IF NOT EXISTS channels (
            chat_id BIGINT PRIMARY KEY,
            title TEXT
        )
        """,

        # Posts table
        """
        CREATE TABLE IF NOT EXISTS posts (
            id SERIAL PRIMARY KEY,
            original_message_id BIGINT NOT NULL,
            channel_chat_id BIGINT NOT NULL,
            forwarded_message_id BIGINT NOT NULL,
            FOREIGN KEY(channel_chat_id)
                REFERENCES channels(chat_id)
                ON DELETE CASCADE,
            UNIQUE(channel_chat_id, forwarded_message_id)
        )
        """
    ]

    for table_query in tables:
        cursor.execute(table_query)

    conn.commit()
    cursor.close()
    conn.close()