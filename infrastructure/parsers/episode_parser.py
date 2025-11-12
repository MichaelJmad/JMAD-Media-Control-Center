"""Episode information parser"""
import re
from typing import Optional, Tuple

from domain.value_objects.episode_number import EpisodeNumber


class EpisodeParser:
    """Parse episode and season information from filenames

    Uses regex patterns to extract S01E02, 1x02, and other common formats.
    """

    # Episode patterns in order of precedence
    PATTERNS = [
        # Special episodes: S00E01, S00S01, S0S01 (single zero)
        (re.compile(r"s0{1,2}[exs](\d{1,3})", re.I), "special"),
        # Standard: S01E02, S01S02 (includes 's' separator)
        (re.compile(r"s(\d{1,2})[exs](\d{1,3})", re.I), "standard"),
        # Alternative: 1x02
        (re.compile(r"(\d{1,2})x(\d{1,3})", re.I), "alternative"),
        # Three digits: 105 (season 1, episode 5)
        (re.compile(r"[._\-\s](?<!\d)(\d)(\d{2})(?!\d)[._\-\s]?", re.I), "three_digit"),
        # Common anime pattern: "Series Name - 04" or "Series Name - Episode 04"
        # But NOT ranges like "01 ~ 24" (negative lookahead for tilde)
        # Supports version suffixes like v2, v3
        (re.compile(r"\s+-\s+(?:episode\s+)?(\d{1,3})(?!\s*~)(?:v\d+)?(?:[._\-\s\[]|$)", re.I), "dash_episode"),
        # Episode only: E01, episode 01, ep 01 (with optional version suffix)
        (re.compile(r"[._\-\s]e(\d{1,3})(?:v\d+)?(?:[._\-\s\[]|$)", re.I), "episode_only"),
        (re.compile(r"episode[\s._-]*(\d+)(?:v\d+)?", re.I), "episode_word"),
        (re.compile(r"ep[\s._-]*(\d+)(?:v\d+)?", re.I), "ep_abbrev"),
        (re.compile(r"part[\s._-]*(\d+)", re.I), "part"),
        # Four digits alone: 1234 (for episodes in thousands, at start or after separator)
        (re.compile(r"(?:^|(?<=[._\-\s]))(\d{4})(?=[._\-\s]|$)", re.I), "four_digit_only"),
        # Three digits alone: 001, 054 (at start or after separator)
        (re.compile(r"(?:^|(?<=[._\-\s]))(\d{3})(?=[._\-\s]|$)", re.I), "three_digit_only"),
        # Two digits alone: 01, 05 (at start or after separator)
        (re.compile(r"(?:^|(?<=[._\-\s]))(\d{2})(?=[._\-\s]|$)", re.I), "two_digit_only"),
        # Single digit alone: 1, 5 (very last resort, at start or after separator)
        (re.compile(r"(?:^|(?<=[._\-\s]))(\d)(?=[._\-\s]|$)", re.I), "single_digit_only"),
    ]

    # Season hint pattern
    SEASON_HINT_RE = re.compile(r"(?:season[\s._-]*([0-9]{1,2}))|(?:\bS([0-9]{1,2})\b)", re.I)

    @classmethod
    def parse(cls, filename: str) -> Optional[EpisodeNumber]:
        """Parse episode information from filename

        Args:
            filename: The filename to parse

        Returns:
            EpisodeNumber if parsed successfully, None otherwise
        """
        season, episode = cls._parse_season_episode(filename)

        if season is not None and episode is not None:
            try:
                return EpisodeNumber(season=season, episode=episode)
            except ValueError:
                return None

        return None

    @classmethod
    def _parse_season_episode(cls, filename: str) -> Tuple[Optional[int], Optional[int]]:
        """Extract season and episode numbers from filename

        Returns:
            Tuple of (season, episode) or (None, None) if not found
        """
        for pattern, pattern_type in cls.PATTERNS:
            match = pattern.search(filename)
            if not match or not match.groups():
                continue

            try:
                groups = match.groups()

                # Special episodes (S00E01)
                if pattern_type == "special":
                    return 0, int(groups[0])

                # Standard (S01E02) or Alternative (1x02)
                if pattern_type in ("standard", "alternative", "three_digit"):
                    return int(groups[0]), int(groups[1])

                # Episode only patterns - need to infer season
                if pattern_type in ("episode_only", "episode_word", "ep_abbrev", "part", "dash_episode",
                                    "four_digit_only", "three_digit_only", "two_digit_only", "single_digit_only"):
                    episode = int(groups[-1])
                    # Try to find season hint in filename
                    season = cls._find_season_hint(filename)
                    return season, episode

            except (ValueError, IndexError):
                continue

        return None, None

    @classmethod
    def _find_season_hint(cls, filename: str) -> Optional[int]:
        """Try to find season hint in filename or path

        Looks for "Season 01" or "S01" patterns in the filename.

        Returns:
            Season number if found, None otherwise
        """
        match = cls.SEASON_HINT_RE.search(filename)
        if match:
            for group in match.groups():
                if group:
                    try:
                        return int(group)
                    except ValueError:
                        pass
        return None

    @classmethod
    def parse_episode_only(cls, filename: str) -> Optional[int]:
        """Parse just the episode number from filename

        This method extracts the episode number without requiring season information.
        Useful when season is already known from context (like folder structure).

        Args:
            filename: The filename to parse

        Returns:
            Episode number if found, None otherwise
        """
        season, episode = cls._parse_season_episode(filename)

        # Return episode even if season is None
        return episode if episode is not None else None

    @classmethod
    def has_episode_info(cls, filename: str) -> bool:
        """Check if filename contains parseable episode information

        Args:
            filename: The filename to check

        Returns:
            True if episode info can be parsed, False otherwise
        """
        return cls.parse(filename) is not None
