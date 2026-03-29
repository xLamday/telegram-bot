"""
Main database manager using consolidated database classes.
Provides backwards-compatible interface while using simplified architecture.
"""
from .channel_db import ChannelDatabase
from .post_db import PostDatabase


class DatabaseManager:
    """
    Main database manager with simplified, consolidated structure.
    
    Old structure (1 unique class):
    - database.py containing everything
    
    New structure (4 classes):
    - manager.py: It allows all databases to connect within a temporary-connection across the entire code-base.\n
        This ensures better scalability and fail-safe cases)

    - base.py: Base database operations file
    
    - channel_db: All channel operations (add_channel, register_channel, channel_exists)\n

    - post_db: All post operations (delete_all_posts_by_channel, upsert_post, post_exists, remove_duplicate_posts, ecc..)
    """
    
    def __init__(self):
        # New consolidated databases
        self._channel_db = ChannelDatabase()
        self._post_db = PostDatabase()

    # ==================== NEW API ====================
    
    @property
    def channel(self):
        """Access channel database (new simplified API)."""
        return self._channel_db
    
    @property
    def post(self):
        """Access post database (new simplified API)."""
        return self._post_db
    
    
    # ==================== CONTEXT MANAGER ====================
    
    def __enter__(self):
        """Create a single shared connection for all sub-databases."""
        from .connection import get_connection
        self.shared_conn = get_connection()
        
        # Initialize all sub-databases with the shared connection
        self._channel_db.conn = self.shared_conn
        self._post_db.conn = self.shared_conn
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Commit and close the shared connection."""
        if hasattr(self, 'shared_conn') and self.shared_conn:
            try:
                # Only commit if no exception occurred
                if exc_type is None:
                    self.shared_conn.commit()
                else:
                    # Rollback on exception
                    self.shared_conn.rollback()
            finally:
                self.shared_conn.close()
                self.shared_conn = None


if __name__ == '__main__':
    pass
