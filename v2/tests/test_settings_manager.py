
import unittest
import os
import json
from v2.app.services.settings_manager import SettingsManager

class TestSettingsManager(unittest.TestCase):

    def setUp(self):
        self.test_settings_path = "test_settings.json"
        self.settings_manager = SettingsManager(self.test_settings_path)

    def tearDown(self):
        if os.path.exists(self.test_settings_path):
            os.remove(self.test_settings_path)

    def test_load_settings_file_not_found(self):
        settings = self.settings_manager.load_settings()
        self.assertEqual(settings, {"staging_directory": ""})
        self.assertTrue(os.path.exists(self.test_settings_path))

    def test_load_settings_file_corrupted(self):
        with open(self.test_settings_path, 'w') as f:
            f.write("this is not json")
        settings = self.settings_manager.load_settings()
        self.assertEqual(settings, {"staging_directory": ""})

    def test_save_and_load_settings(self):
        self.settings_manager.set("staging_directory", "/my/staging/directory")
        self.settings_manager.set("another_setting", 123)

        new_settings_manager = SettingsManager(self.test_settings_path)
        settings = new_settings_manager.load_settings()

        self.assertEqual(settings.get("staging_directory"), "/my/staging/directory")
        self.assertEqual(settings.get("another_setting"), 123)

if __name__ == '__main__':
    unittest.main()
