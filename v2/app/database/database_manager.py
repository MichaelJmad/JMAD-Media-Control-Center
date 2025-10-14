import sqlite3
import threading

class DatabaseManager:
    def __init__(self, db_path='jmad_media_tool.db'):
        self.db_path = db_path
        self.local = threading.local()
        self.create_tables()

    def get_conn(self):
        if not hasattr(self.local, 'conn'):
            self.local.conn = sqlite3.connect(self.db_path)
        return self.local.conn

    def create_tables(self):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS media_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL
            )
        ''')
        conn.commit()

    def get_all_media_items(self):
        """Fetches all media items from the database."""
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT path, status FROM media_items ORDER BY path")
        return cursor.fetchall()

    def close(self):
        if hasattr(self.local, 'conn'):
            self.local.conn.close()
