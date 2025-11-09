"""Series domain model"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import uuid

from domain.models.episode import Episode
from domain.models.season import Season
from domain.value_objects.media_type import MediaType
from domain.value_objects.file_path import FilePath


@dataclass
class Series:
    """Represents a TV series or anime with seasons and episodes

    Main aggregate root for series-based media.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    clean_name: str = ""  # Name with fluff removed
    media_type: MediaType = MediaType.UNKNOWN
    root_path: FilePath = field(default_factory=lambda: FilePath("."))
    seasons: Dict[int, Season] = field(default_factory=dict)
    unsorted_episodes: List[Episode] = field(default_factory=list)
    has_nonstandard_folders: bool = False

    def __post_init__(self):
        """Ensure root_path is FilePath"""
        if not isinstance(self.root_path, FilePath):
            self.root_path = FilePath(self.root_path)

    def add_episode(self, episode: Episode):
        """Add an episode to the appropriate season"""
        if episode.season is None:
            self.unsorted_episodes.append(episode)
            return

        season_num = episode.season
        if season_num not in self.seasons:
            self.seasons[season_num] = Season(number=season_num)

        self.seasons[season_num].add_episode(episode)

    def get_season(self, season_number: int) -> Optional[Season]:
        """Get season by number"""
        return self.seasons.get(season_number)

    def get_all_episodes(self) -> List[Episode]:
        """Get all episodes from all seasons including unsorted"""
        episodes = []
        for season in self.seasons.values():
            episodes.extend(season.episodes)
        episodes.extend(self.unsorted_episodes)
        return episodes

    def season_count(self) -> int:
        """Get total number of seasons"""
        return len(self.seasons)

    def total_episode_count(self) -> int:
        """Get total number of episodes across all seasons"""
        count = sum(season.episode_count() for season in self.seasons.values())
        count += len(self.unsorted_episodes)
        return count

    def has_specials(self) -> bool:
        """Check if series has specials (Season 0)"""
        return 0 in self.seasons

    def sort_all_seasons(self):
        """Sort episodes in all seasons"""
        for season in self.seasons.values():
            season.sort_episodes()

    def __str__(self) -> str:
        return f"{self.name} ({self.media_type.value}, {self.season_count()} seasons, {self.total_episode_count()} episodes)"

    def __repr__(self) -> str:
        return f"Series(id={self.id[:8]}, name='{self.name}', type={self.media_type.value}, seasons={self.season_count()})"
