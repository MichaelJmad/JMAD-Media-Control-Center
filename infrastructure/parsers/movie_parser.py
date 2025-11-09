"""Movie information parser"""
import re
from typing import Optional


class MovieParser:
    """Parse movie information from filenames

    Extracts year and other movie-specific metadata.
    """

    # Year pattern: (2023), [2023], .2023., -2023-
    YEAR_PATTERN = re.compile(r"[\(\[._\-\s](\d{4})[\)\]_\-\s]", re.I)

    @classmethod
    def parse_year(cls, filename: str) -> Optional[int]:
        """Extract year from movie filename

        Args:
            filename: The filename to parse

        Returns:
            Year as integer if found, None otherwise

        Examples:
            "Inception (2010).mkv" -> 2010
            "Avatar.2009.1080p.mkv" -> 2009
            "[2023] Movie Name.mp4" -> 2023
        """
        match = cls.YEAR_PATTERN.search(filename)
        if match:
            try:
                year = int(match.group(1))
                # Validate year is reasonable (between 1900 and 2100)
                if 1900 <= year <= 2100:
                    return year
            except ValueError:
                pass
        return None

    @classmethod
    def has_year(cls, filename: str) -> bool:
        """Check if filename contains a year

        Args:
            filename: The filename to check

        Returns:
            True if year is found, False otherwise
        """
        return cls.parse_year(filename) is not None

    @classmethod
    def remove_year(cls, filename: str) -> str:
        """Remove year from filename

        Args:
            filename: The filename to clean

        Returns:
            Filename with year removed
        """
        return cls.YEAR_PATTERN.sub(" ", filename).strip()
