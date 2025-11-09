"""Episode domain model"""
from dataclasses import dataclass, field
from typing import Optional
import uuid

from domain.value_objects.file_path import FilePath
from domain.value_objects.episode_number import EpisodeNumber


@dataclass
class Episode:
    """Represents a single episode file

    Core domain entity for episode-based media.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    path: FilePath = field(default_factory=lambda: FilePath("."))
    episode_number: Optional[EpisodeNumber] = None
    title: Optional[str] = None  # Episode title (if parsed or provided)
    year: Optional[int] = None  # Year (for movies or special releases)
    original_basename: str = ""  # Original filename for reference

    def __post_init__(self):
        """Ensure path is FilePath and set original_basename"""
        if not isinstance(self.path, FilePath):
            self.path = FilePath(self.path)

        if not self.original_basename:
            self.original_basename = self.path.name

    @property
    def filename(self) -> str:
        """Get current filename"""
        return self.path.name

    @property
    def extension(self) -> str:
        """Get file extension"""
        return self.path.extension

    @property
    def season(self) -> Optional[int]:
        """Get season number (convenience accessor)"""
        return self.episode_number.season if self.episode_number else None

    @property
    def episode(self) -> Optional[int]:
        """Get episode number (convenience accessor)"""
        return self.episode_number.episode if self.episode_number else None

    def is_special(self) -> bool:
        """Check if this is a special episode"""
        return self.episode_number.is_special() if self.episode_number else False

    def is_movie(self) -> bool:
        """Check if this represents a movie (season -1)"""
        return self.season == -1 if self.season is not None else False

    def has_episode_info(self) -> bool:
        """Check if episode information was successfully parsed"""
        return self.episode_number is not None

    def __str__(self) -> str:
        if self.episode_number:
            return f"Episode({self.episode_number}, {self.filename})"
        return f"Episode({self.filename})"

    def __repr__(self) -> str:
        return f"Episode(id={self.id[:8]}, path={self.path.name}, episode_number={self.episode_number})"
