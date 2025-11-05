
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SettingsManager:
    def __init__(self, settings_path):
        self.settings_path = settings_path
        self.settings = {}

    def load_settings(self):
        try:
            with open(self.settings_path, 'r') as f:
                self.settings = json.load(f)
        except FileNotFoundError:
            logging.warning(f"Settings file not found at {self.settings_path}. Creating a default one.")
            self.settings = {
                "staging_directory": ""
            }
            self.save_settings()
        except json.JSONDecodeError:
            logging.error(f"Error decoding JSON from {self.settings_path}. The file might be corrupted.")
            self.settings = {
                "staging_directory": ""
            }
        return self.settings

    def save_settings(self):
        try:
            with open(self.settings_path, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except IOError as e:
            logging.error(f"Failed to save settings to {self.settings_path}: {e}")

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value
        self.save_settings()
