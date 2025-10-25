import json
from pathlib import Path

class SettingsManager:
    """Manages the application's settings."""

    def __init__(self, settings_path: Path):
        """
        Initializes the SettingsManager.

        Args:
            settings_path: The path to the settings file.
        """
        self.settings_path = settings_path
        self.settings = self._load_defaults()

        if self.settings_path.exists():
            self.load_settings()

    def _load_defaults(self):
        """Loads the default settings."""
        return {
            "general": {
                "start_with_windows": False,
                "minimize_to_tray": False,
                "show_notifications": True,
            },
            "directories": {
                "staging": "",
                "libraries": [],
            },
            "renaming": {
                "folder_template": "{series_name} - Season {season_number}",
                "file_template": "{series_name} - S{season_number:02d}E{episode_number:02d} - {episode_title}",
            },
            "metadata": {
                "providers": ["tmdb", "tvdb"],
                "api_keys": {
                    "tmdb": "",
                    "tvdb": "",
                },
            },
            "libraries_scan": {
                "scan_on_startup": False,
                "scan_interval_hours": 0,
            },
            "cleaning": {
                "default_categories": ["txt", "nfo"],
            },
            "trash_bin": {
                "enabled": True,
                "auto_purge_days": 30,
            },
            "appearance": {
                "theme": "system",
                "font_size": "normal",
            },
            "hotkeys": {
                "open_settings": "Ctrl+,",
                "scan_staging": "F5",
            },
            "performance": {
                "concurrent_operations": 4,
            },
        }

    def load_settings(self):
        """Loads settings from the settings file."""
        try:
            with open(self.settings_path, 'r') as f:
                self.settings.update(json.load(f))
        except (IOError, json.JSONDecodeError):
            # If file is corrupted or unreadable, use defaults
            self.settings = self._load_defaults()
            self.save_settings()


    def save_settings(self):
        """Saves the current settings to the settings file."""
        self.settings_path.parent.mkdir(exist_ok=True)
        with open(self.settings_path, 'w') as f:
            json.dump(self.settings, f, indent=4)

    def get(self, key, default=None):
        """Gets a setting value."""
        keys = key.split('.')
        value = self.settings
        for k in keys:
            value = value.get(k, {})
        return value if value else default

    def set(self, key, value):
        """Sets a setting value."""
        keys = key.split('.')
        d = self.settings
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = value
        self.save_settings()

if __name__ == '__main__':
    config_dir = Path(__file__).parent.parent / 'config'
    settings_path = config_dir / 'settings.json'
    settings_manager = SettingsManager(settings_path)
    settings_manager.save_settings()
    print(f"Default settings saved to: {settings_path}")
