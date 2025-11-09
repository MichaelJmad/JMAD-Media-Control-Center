"""Settings persistence repository"""
import json
from pathlib import Path
from typing import Optional

from config.settings import Settings
from config.constants import SETTINGS_FILE


class SettingsRepository:
    """Repository for persisting application settings to JSON file"""

    def __init__(self, settings_file: str = SETTINGS_FILE):
        """Initialize repository with settings file path

        Args:
            settings_file: Path to settings JSON file
        """
        self.settings_file = Path(settings_file)

    def load(self) -> Settings:
        """Load settings from file

        Returns default settings if file doesn't exist or is invalid.

        Returns:
            Settings object
        """
        if not self.settings_file.exists():
            # Return default settings
            return Settings()

        try:
            with open(self.settings_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return Settings.from_dict(data)
        except (json.JSONDecodeError, IOError, KeyError) as e:
            print(f"Warning: Failed to load settings from {self.settings_file}: {e}")
            print("Using default settings")
            return Settings()

    def save(self, settings: Settings) -> bool:
        """Save settings to file

        Args:
            settings: Settings object to save

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Ensure parent directory exists
            self.settings_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(settings.to_dict(), f, indent=2)
            return True
        except (IOError, OSError) as e:
            print(f"Error: Failed to save settings to {self.settings_file}: {e}")
            return False

    def validate_directories(self, settings: Settings) -> dict:
        """Validate that configured directories exist

        Args:
            settings: Settings to validate

        Returns:
            Dictionary mapping directory names to validation status
        """
        validation = {}

        dirs = {
            "staging": settings.directories.staging,
            "tv_shows": settings.directories.tv_shows,
            "movies": settings.directories.movies,
            "anime": settings.directories.anime,
            "trash": settings.directories.trash,
        }

        for name, path in dirs.items():
            if not path:
                validation[name] = "not_configured"
            elif not Path(path).exists():
                validation[name] = "does_not_exist"
            elif not Path(path).is_dir():
                validation[name] = "not_a_directory"
            else:
                validation[name] = "valid"

        return validation
