"""Fluff removal parser for cleaning filenames"""
import re
from typing import List


class FluffParser:
    """Remove junk/fluff from filenames to extract clean series names

    Uses regex patterns to remove release group tags, quality indicators,
    codec tags, and other metadata from filenames.
    """

    # Default patterns to remove
    DEFAULT_PATTERNS = [
        r"\[.*?\]",  # Remove anything in square brackets [GROUP][1080p]
        r"\(.*?\)",  # Remove anything in parentheses (but preserve years)
        r"\b(1080p|720p|2160p|4k|480p|x264|x265|h264|h265|hevc|avc)\b",  # Quality/codec
        r"\b(webrip|bluray|bdrip|web-dl|hdtv|dvdrip|brrip)\b",  # Source
        r"\b(dual.audio|multi.sub|subbed|dubbed)\b",  # Audio/subtitle info
        r"\b(repack|proper|real|retail)\b",  # Release info
        r"\b(10bit|8bit)\b",  # Bit depth
        r"(s\d+)",  # Standalone season tags like "s1"
    ]

    def __init__(self, custom_patterns: List[str] = None):
        """Initialize parser with custom patterns

        Args:
            custom_patterns: Additional regex patterns to remove (optional)
        """
        self.patterns = self.DEFAULT_PATTERNS.copy()
        if custom_patterns:
            self.patterns.extend(custom_patterns)

    def clean_name(self, name: str) -> str:
        """Remove fluff from name and clean up formatting

        Args:
            name: The name to clean

        Returns:
            Cleaned name with fluff removed

        Examples:
            "Series.Name.[1080p][GROUP]" -> "Series Name"
            "Movie.Title.2023.BluRay.x264" -> "Movie Title"
        """
        cleaned = name

        # Apply all patterns
        for pattern in self.patterns:
            try:
                cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
            except re.error:
                # Skip invalid patterns
                continue

        # Replace common separators with spaces
        cleaned = re.sub(r"[._-]", " ", cleaned)

        # Collapse multiple spaces and trim
        cleaned = " ".join(cleaned.split()).strip()

        return cleaned

    def add_pattern(self, pattern: str):
        """Add a custom pattern to the parser

        Args:
            pattern: Regex pattern to add
        """
        if pattern and pattern not in self.patterns:
            self.patterns.append(pattern)

    def remove_pattern(self, pattern: str):
        """Remove a pattern from the parser

        Args:
            pattern: Pattern to remove
        """
        if pattern in self.patterns:
            self.patterns.remove(pattern)

    def get_patterns(self) -> List[str]:
        """Get all current patterns

        Returns:
            List of regex patterns
        """
        return self.patterns.copy()
