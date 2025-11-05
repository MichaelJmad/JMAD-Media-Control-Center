
import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class StateManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None

    def initialize_database(self):
        try:
            self.conn = sqlite3.connect(self.db_path)
            cursor = self.conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS media_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL
            )
        """)
            self.conn.commit()
            logging.info("Database initialized.")
        except sqlite3.Error as e:
            logging.error(f"Database error: {e}")

    def add_media_item(self, path, status="Unorganized"):
        if not self.conn:
            self.initialize_database()
        try:
            cursor = self.conn.cursor()
            cursor.execute("INSERT INTO media_items (path, status) VALUES (?, ?)", (path, status))
            self.conn.commit()
            logging.info(f"Added media item: {path}")
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            logging.warning(f"Media item already exists: {path}")
            return None
        except sqlite3.Error as e:
            logging.error(f"Failed to add media item: {e}")
            return None

    def update_media_item_status(self, item_id, status):
        if not self.conn:
            self.initialize_database()
        try:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE media_items SET status = ? WHERE id = ?", (status, item_id))
            self.conn.commit()
            logging.info(f"Updated media item {item_id} to status: {status}")
        except sqlite3.Error as e:
            logging.error(f"Failed to update media item: {e}")

    def delete_media_item(self, path):
        if not self.conn:
            self.initialize_database()
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM media_items WHERE path = ?", (path,))
            self.conn.commit()
            logging.info(f"Deleted media item: {path}")
        except sqlite3.Error as e:
            logging.error(f"Failed to delete media item: {e}")

    def move_media_item(self, old_path, new_path):
        if not self.conn:
            self.initialize_database()
        try:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE media_items SET path = ? WHERE path = ?", (new_path, old_path))
            self.conn.commit()
            logging.info(f"Moved media item from {old_path} to {new_path}")
        except sqlite3.Error as e:
            logging.error(f"Failed to move media item: {e}")

    def get_all_media_items(self):
        if not self.conn:
            self.initialize_database()
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT id, path, status FROM media_items")
            return cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Failed to get media items: {e}")
            return []

    def close(self):
        if self.conn:
            self.conn.close()
            logging.info("Database connection closed.")
