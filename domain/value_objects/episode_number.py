"""Episode number value object"""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class EpisodeNumber:
    """Value object representing an episode number

    Handles season and episode numbers, including special cases.
    """

    season: int
    episode: int
    end_episode: Optional[int] = None  # For multi-episode files (e.g., E01-E03)

    def __post_init__(self):
        """Validate episode numbers"""
        if self.season < 0:
            raise ValueError(f"Season number cannot be negative: {self.season}")
        if self.episode < 0:
            raise ValueError(f"Episode number cannot be negative: {self.episode}")
        if self.end_episode is not None and self.end_episode < self.episode:
            raise ValueError(
                f"End episode ({self.end_episode}) cannot be less than start episode ({self.episode})"
            )

    def is_special(self) -> bool:
        """Check if this is a special episode (Season 0)"""
        return self.season == 0

    def is_multi_episode(self) -> bool:
        """Check if this represents multiple episodes"""
        return self.end_episode is not None

    def format_standard(self) -> str:
        """Format as standard SxxExx notation"""
        if self.is_multi_episode():
            return f"S{self.season:02d}E{self.episode:02d}-E{self.end_episode:02d}"
        return f"S{self.season:02d}E{self.episode:02d}"

    def format_simple(self) -> str:
        """Format as simple season x episode notation"""
        if self.is_multi_episode():
            return f"{self.season}x{self.episode:02d}-{self.end_episode:02d}"
        return f"{self.season}x{self.episode:02d}"

    def __str__(self) -> str:
        return self.format_standard()

    def __repr__(self) -> str:
        if self.is_multi_episode():
            return f"EpisodeNumber(S{self.season}E{self.episode}-E{self.end_episode})"
        return f"EpisodeNumber(S{self.season}E{self.episode})"
