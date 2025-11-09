"""Media type value object"""
from enum import Enum


class MediaType(str, Enum):
    """Enumeration of supported media types"""

    TV_SERIES = "TV Series"
    ANIME = "Anime"
    MOVIE = "Movie"
    ANIME_MOVIE = "Anime Movie"
    UNKNOWN = "Unknown"

    def __str__(self) -> str:
        return self.value

    @classmethod
    def from_string(cls, value: str) -> "MediaType":
        """Create MediaType from string value"""
        for media_type in cls:
            if media_type.value.lower() == value.lower():
                return media_type
        return cls.UNKNOWN

    def is_series(self) -> bool:
        """Check if this is a series type (TV or Anime)"""
        return self in (MediaType.TV_SERIES, MediaType.ANIME)

    def is_movie(self) -> bool:
        """Check if this is a movie type"""
        return self in (MediaType.MOVIE, MediaType.ANIME_MOVIE)
