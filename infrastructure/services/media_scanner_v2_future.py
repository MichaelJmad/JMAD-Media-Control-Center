"""Media scanning service"""
from pathlib import Path
from typing import Dict, List, Optional
from collections import Counter

from domain.models.episode import Episode
from domain.models.series import Series
from domain.models.movie import Movie
from domain.value_objects.file_path import FilePath
from domain.value_objects.media_type import MediaType
from domain.value_objects.episode_number import EpisodeNumber
from infrastructure.parsers.episode_parser import EpisodeParser
from infrastructure.parsers.movie_parser import MovieParser
from infrastructure.parsers.fluff_parser import FluffParser
from config.constants import VIDEO_EXTENSIONS


class MediaScanner:
    """Service for scanning directories and discovering media files

    Creates domain models (Series, Movie, Episode) from filesystem.
    """

    # Organizational folders that indicate media type
    ORGANIZATIONAL_FOLDERS = {
        "Anime": MediaType.ANIME,
        "Movies": MediaType.MOVIE,
        "TV Series": MediaType.TV_SERIES,
        "TV Shows": MediaType.TV_SERIES,
    }

    def __init__(self, fluff_parser: FluffParser):
        """Initialize scanner

        Args:
            fluff_parser: Parser for cleaning filenames
        """
        self.fluff_parser = fluff_parser
        self.episode_parser = EpisodeParser()
        self.movie_parser = MovieParser()

    def scan_directory(self, directory: FilePath) -> Dict[str, Series]:
        """Scan a directory for media files and organize into Series

        Args:
            directory: Root directory to scan

        Returns:
            Dictionary mapping series names to Series objects
        """
        if not directory.exists() or not directory.is_dir():
            return {}

        series_map: Dict[str, Series] = {}

        # Walk directory tree
        for file_path in self._walk_directory(directory):
            self._process_file(file_path, directory, series_map, None)

        # Sort episodes in all series
        for series in series_map.values():
            series.sort_all_seasons()

        return series_map

    def _walk_directory(self, directory: FilePath) -> List[FilePath]:
        """Recursively walk directory and return all video files

        Args:
            directory: Directory to walk

        Returns:
            List of FilePath objects for video files
        """
        video_files = []

        try:
            for entry in directory.path.rglob("*"):
                if entry.is_file() and entry.suffix.lower() in VIDEO_EXTENSIONS:
                    video_files.append(FilePath(entry))
        except (OSError, PermissionError):
            pass

        return video_files

    def _process_file(
        self,
        file_path: FilePath,
        root_directory: FilePath,
        series_map: Dict[str, Series],
        inherited_media_type: Optional[MediaType]
    ):
        """Process a single media file

        Args:
            file_path: Path to media file
            root_directory: Root scan directory
            series_map: Dictionary to populate with series
            inherited_media_type: Media type inherited from organizational folder
        """
        filename = file_path.stem  # Name without extension

        # Check if file is in an organizational folder
        media_type = self._infer_media_type(file_path, root_directory, inherited_media_type)

        # Parse episode information
        episode_number = self.episode_parser.parse(filename)

        # Parse movie year
        year = self.movie_parser.parse_year(filename)

        # Determine series name
        series_name = self._extract_series_name(file_path, filename, episode_number)

        # Create Episode object
        episode = Episode(
            path=file_path,
            episode_number=episode_number,
            title=None,  # TODO: Extract episode title if present
            year=year,
            original_basename=file_path.name
        )

        # Add to appropriate series
        if series_name not in series_map:
            series_map[series_name] = Series(
                name=series_name,
                clean_name=self.fluff_parser.clean_name(series_name),
                media_type=media_type,
                root_path=file_path.parent
            )

        series_map[series_name].add_episode(episode)

    def _infer_media_type(
        self,
        file_path: FilePath,
        root_directory: FilePath,
        inherited_type: Optional[MediaType]
    ) -> MediaType:
        """Infer media type from file location

        Args:
            file_path: Path to media file
            root_directory: Root scan directory
            inherited_type: Type inherited from parent (if any)

        Returns:
            Inferred MediaType
        """
        # Check if file is in an organizational folder
        try:
            relative = file_path.relative_to(root_directory)
            if relative:
                parts = Path(relative).parts
                if len(parts) > 0:
                    top_folder = parts[0]
                    if top_folder in self.ORGANIZATIONAL_FOLDERS:
                        return self.ORGANIZATIONAL_FOLDERS[top_folder]
        except ValueError:
            pass

        # Check for Movies subfolder pattern (Movies/MovieTitle/movie.mkv)
        parent_name = file_path.parent.name
        grandparent_name = file_path.parent.parent.name

        if grandparent_name.lower() == "movies":
            return MediaType.MOVIE

        # Use inherited type if available
        if inherited_type:
            return inherited_type

        # Check if file has episode information (likely TV series)
        if self.episode_parser.has_episode_info(file_path.name):
            return MediaType.TV_SERIES

        # Default to unknown
        return MediaType.UNKNOWN

    def _extract_series_name(
        self,
        file_path: FilePath,
        filename: str,
        episode_number: Optional[EpisodeNumber]
    ) -> str:
        """Extract series name from file path and name

        Args:
            file_path: Full path to file
            filename: Filename without extension
            episode_number: Parsed episode number (if any)

        Returns:
            Series name
        """
        # Special case: Movies in Movies/MovieTitle/ structure
        parent_name = file_path.parent.name
        grandparent_name = file_path.parent.parent.name

        if grandparent_name.lower() == "movies":
            # Use parent folder name as movie title
            return parent_name

        # For TV series, try to extract from parent folder first
        # This is more reliable than parsing the filename
        if episode_number is not None:
            # Check if parent folder looks like a series name
            parent_clean = self.fluff_parser.clean_name(parent_name)
            if parent_clean and len(parent_clean) > 3:
                # Parent folder is likely the series name
                return parent_clean

        # Fall back to extracting from filename
        return self.fluff_parser.clean_name(filename)

    def detect_nonstandard_structure(self, series: Series) -> bool:
        """Check if series has non-standard folder structure

        Args:
            series: Series to check

        Returns:
            True if structure is non-standard, False otherwise
        """
        # Check if episodes are scattered across multiple directories
        directories = set()
        for episode in series.get_all_episodes():
            directories.add(episode.path.parent.absolute)

        # If episodes are in many different directories, it's non-standard
        # (Standard would be: Series/Season 1/, Series/Season 2/, etc.)
        if len(directories) > series.season_count() + 2:  # +2 for some flexibility
            return True

        return False
