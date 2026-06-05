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

    def __enter__(self):
        self.conn = get_connection()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            if exc_type is not None:
                self.conn.rollback()
            self.conn.close()
        self.conn = None

    def _get_cursor(self) -> sqlite3.Cursor:
        """Return a new cursor, or None if connection is missing."""
        if not self.conn:
            raise sqlite3.Error("Database connection is None")
        return self.conn.cursor()

    def _execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """
        Execute a query without committing.
        Returns the cursor on success, None on failure.
        Commit is responsibility of the caller.
        """
        cursor = self._get_cursor()
        try:
            cursor.execute(query, params)
            return cursor
        except sqlite3.Error as e:
            logger.error(f"Database error in _execute: {e}")
            raise

    def _fetch_one(self, query: str, params: tuple = ()) -> Optional[tuple]:
        """Fetch one row from query."""
        cursor = self._execute(query, params)
        return cursor.fetchone()


    def _fetch_all(self, query: str, params: tuple = ()) -> list:
        """Fetch all rows from query."""
        cursor = self._execute(query, params)
        return cursor.fetchall()
