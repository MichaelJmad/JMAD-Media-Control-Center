from v2.app.database.database_manager import DatabaseManager

class StateManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def add_unorganized_file(self, file_path):
        """Adds a new file to the database with the 'Unorganized' status."""
        conn = self.db_manager.get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO media_items (path, status) VALUES (?, ?)", (file_path, 'Unorganized'))
            conn.commit()
            print(f"Added new file to database: {file_path}")
        except conn.IntegrityError:
            print(f"File already exists in database: {file_path}")
