"""Movie domain model"""
from dataclasses import dataclass, field
from typing import Optional
import uuid

from domain.value_objects.file_path import FilePath
from domain.value_objects.media_type import MediaType


@dataclass
class Movie:
    """Represents a standalone movie file

    Domain entity for movie-based media.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    clean_title: str = ""  # Title with fluff removed
    year: Optional[int] = None
    path: FilePath = field(default_factory=lambda: FilePath("."))
    media_type: MediaType = MediaType.MOVIE
    original_basename: str = ""

    def __post_init__(self):
        """Ensure path is FilePath and set original_basename"""
        if not isinstance(self.path, FilePath):
            self.path = FilePath(self.path)

        if not self.original_basename:
            self.original_basename = self.path.name

        # Validate media type
        if not self.media_type.is_movie():
            raise ValueError(f"Invalid media type for Movie: {self.media_type}")

    @property
    def filename(self) -> str:
        """Get current filename"""
        return self.path.name

    @property
    def extension(self) -> str:
        """Get file extension"""
        return self.path.extension

    def formatted_title(self) -> str:
        """Get formatted title with year if available"""
        if self.year:
            return f"{self.title} ({self.year})"
        return self.title

    def __str__(self) -> str:
        return f"Movie({self.formatted_title()}, {self.filename})"

    def __repr__(self) -> str:
        return f"Movie(id={self.id[:8]}, title='{self.title}', year={self.year}, type={self.media_type.value})"
