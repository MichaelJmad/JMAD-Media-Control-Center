"""Simple media scanner for V1 - displays raw folder names

This is a simplified scanner that shows folders as-is without intelligent
grouping or parsing. See media_scanner_v2_future.py for the intelligent
scanner that will be used in future versions.
"""
from pathlib import Path
from typing import Dict, Optional

from domain.models.series import Series
from domain.value_objects.file_path import FilePath
from domain.value_objects.media_type import MediaType
from config.constants import VIDEO_EXTENSIONS
from config.settings import Settings


class MediaScanner:
    """Simple service for listing media folders in staging

    V1 behavior: Lists top-level folders with raw names, no intelligent grouping.
    """

    def __init__(self, fluff_parser=None, settings: Optional[Settings] = None):
        """Initialize scanner

        Args:
            fluff_parser: Not used in V1, kept for compatibility
            settings: Application settings (for customizable folder names)
        """
        self.settings = settings

        # Build organizational folder mapping from settings (or use defaults)
        if settings:
            self.organizational_folders = {
                settings.org_folder_anime.lower(): MediaType.ANIME,
                settings.org_folder_tv_shows.lower(): MediaType.TV_SERIES,
                settings.org_folder_movies.lower(): MediaType.MOVIE,
            }
        else:
            # Default values if no settings provided
            self.organizational_folders = {
                "anime": MediaType.ANIME,
                "tv shows": MediaType.TV_SERIES,
                "movies": MediaType.MOVIE,
            }

    def scan_directory(self, directory: FilePath) -> Dict[str, Series]:
        """Scan a directory and list top-level folders

        Handles organizational folders (Anime, TV Shows, Movies) by scanning inside
        them and setting media types accordingly.

        Args:
            directory: Root directory to scan (staging)

        Returns:
            Dictionary mapping folder names to Series objects (one per folder)
        """
        if not directory.exists() or not directory.is_dir():
            return {}

        series_map: Dict[str, Series] = {}

        # List only top-level folders in staging
        try:
            for entry in directory.path.iterdir():
                if entry.is_dir():
                    folder_name = entry.name
                    folder_path = FilePath(entry)

                    # Check if this is an organizational folder
                    if folder_name.lower() in self.organizational_folders:
                        # Scan inside the organizational folder
                        media_type = self.organizational_folders[folder_name.lower()]
                        self._scan_organizational_folder(folder_path, media_type, series_map)
                    else:
                        # Regular folder - treat as media title
                        self._add_media_folder(folder_name, folder_path, series_map)

        except (OSError, PermissionError):
            pass

        return series_map

    def _scan_organizational_folder(self, org_folder: FilePath, media_type: MediaType, series_map: Dict[str, Series]):
        """Scan inside an organizational folder and add media titles

        Args:
            org_folder: Path to organizational folder (Anime, TV Shows, Movies)
            media_type: Media type to assign to all titles in this folder
            series_map: Dictionary to add series to
        """
        try:
            for entry in org_folder.path.iterdir():
                if entry.is_dir():
                    folder_name = entry.name
                    folder_path = FilePath(entry)
                    self._add_media_folder(folder_name, folder_path, series_map, media_type)
        except (OSError, PermissionError):
            pass

    def _add_media_folder(self, folder_name: str, folder_path: FilePath, series_map: Dict[str, Series], media_type: MediaType = None):
        """Add a media folder to the series map

        Args:
            folder_name: Name of the folder
            folder_path: Path to the folder
            series_map: Dictionary to add series to
            media_type: Optional media type to use (if None, auto-detect)
        """
        # Count video files in this folder (recursive)
        file_count = self._count_video_files(folder_path)

        # Use provided media type or detect it
        if media_type is None:
            media_type = self._simple_media_type_detection(folder_name)

        # Create a simple Series object for this folder
        series = Series(
            name=folder_name,  # Raw folder name, no cleaning
            clean_name=folder_name,  # Same as name for V1
            media_type=media_type,
            root_path=folder_path
        )

        # Store file count in a simple way (as a property or metadata)
        # For now, we'll just use the folder name as key
        series._v1_file_count = file_count

        series_map[folder_name] = series

    def _count_video_files(self, directory: FilePath) -> int:
        """Count video files in a directory recursively

        Args:
            directory: Directory to count files in

        Returns:
            Number of video files found
        """
        count = 0

        try:
            for entry in directory.path.rglob("*"):
                if entry.is_file() and entry.suffix.lower() in VIDEO_EXTENSIONS:
                    count += 1
        except (OSError, PermissionError):
            pass

        return count

    def _simple_media_type_detection(self, folder_name: str) -> MediaType:
        """Simple media type detection based on folder name patterns

        V1 uses basic heuristics:
        - For unprocessed folders in staging: Always return UNKNOWN
        - Media type is only set when folders are moved into organizational folders

        Args:
            folder_name: Name of the folder

        Returns:
            MediaType enum value (always UNKNOWN for V1)
        """
        # Always return UNKNOWN for unprocessed folders
        # Media type is assigned when user organizes them into Movies/TV Shows/Anime folders
        return MediaType.UNKNOWN

    def detect_nonstandard_structure(self, series: Series) -> bool:
        """Check if series has non-standard folder structure

        For V1, always returns False (no structure analysis).

        Args:
            series: Series to check

        Returns:
            False (not applicable in V1)
        """
        return False
