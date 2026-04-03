"""
Base database class with common functionality.
"""
import sqlite3
from typing import Optional
from .connection import get_connection
from loggerinfo import LoggerInfo

logger = LoggerInfo(name="BaseDatabase").get_logger()

class BaseDatabase:
    """Base class for all database operations."""

    def __init__(self):
        self.conn: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None
    def __enter__(self):
        self.conn = get_connection()
        self.cursor = None
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()
        self.cursor = None
    
    def _execute(self, query, params=None) -> bool:
        """Execute a query and return success status."""
        if not self.conn:
            logger.error("Database connection is None in _execute")
            return False
        
        self.cursor = self.conn.cursor()
        self.cursor.execute(query, params or ())
        return self.cursor
    
    def _fetch_one(self, query: str, params: tuple = ()):
        """Fetch one row from query."""
        if not self.conn:
            logger.error("Database connection is None in _fetch_one")
            return None
        
        try:
            self.cursor = self.conn.cursor()
            self.cursor.execute(query, params)
            return self.cursor.fetchone()
        except sqlite3.Error as e:
            logger.error(f"Database error in _fetch_one: {e}")
            return None
    
    def _fetch_all(self, query: str, params: tuple = ()):
        """Fetch all rows from query."""
        if not self.conn:
            logger.error("Database connection is None in _fetch_all")
            return []
        
        try:
            self.cursor = self.conn.cursor()
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Database error in _fetch_all: {e}")
            return []