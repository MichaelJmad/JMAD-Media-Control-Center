
import unittest
import os
import sqlite3
from v2.app.services.state_manager import StateManager

class TestStateManager(unittest.TestCase):

    def setUp(self):
        self.test_db_path = "test_jmad_media_tool.db"
        self.state_manager = StateManager(self.test_db_path)
        self.state_manager.initialize_database()

    def tearDown(self):
        self.state_manager.close()
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    def test_add_and_get_media_item(self):
        item_id = self.state_manager.add_media_item("/my/media/file.mkv")
        self.assertIsNotNone(item_id)

        items = self.state_manager.get_all_media_items()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0][1], "/my/media/file.mkv")
        self.assertEqual(items[0][2], "Unorganized")

    def test_add_duplicate_media_item(self):
        self.state_manager.add_media_item("/my/media/file.mkv")
        item_id = self.state_manager.add_media_item("/my/media/file.mkv")
        self.assertIsNone(item_id)

    def test_update_media_item_status(self):
        item_id = self.state_manager.add_media_item("/my/media/file.mkv")
        self.state_manager.update_media_item_status(item_id, "Processed")

        items = self.state_manager.get_all_media_items()
        self.assertEqual(items[0][2], "Processed")

    def test_delete_media_item(self):
        self.state_manager.add_media_item("/my/media/file.mkv")
        self.state_manager.delete_media_item("/my/media/file.mkv")

        items = self.state_manager.get_all_media_items()
        self.assertEqual(len(items), 0)

    def test_move_media_item(self):
        self.state_manager.add_media_item("/my/media/file.mkv")
        self.state_manager.move_media_item("/my/media/file.mkv", "/my/new/media/file.mkv")

        items = self.state_manager.get_all_media_items()
        self.assertEqual(items[0][1], "/my/new/media/file.mkv")

if __name__ == '__main__':
    unittest.main()
