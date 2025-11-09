"""Season domain model"""
from dataclasses import dataclass, field
from typing import List

from domain.models.episode import Episode


@dataclass
class Season:
    """Represents a season containing episodes

    Aggregates episodes for a specific season number.
    """

    number: int
    episodes: List[Episode] = field(default_factory=list)

    def add_episode(self, episode: Episode):
        """Add an episode to this season"""
        if episode.season != self.number:
            raise ValueError(
                f"Episode season {episode.season} does not match season {self.number}"
            )
        self.episodes.append(episode)

    def get_episode(self, episode_number: int) -> Episode | None:
        """Get episode by number"""
        for ep in self.episodes:
            if ep.episode == episode_number:
                return ep
        return None

    def episode_count(self) -> int:
        """Get total number of episodes"""
        return len(self.episodes)

    def is_special(self) -> bool:
        """Check if this is the specials season (Season 0)"""
        return self.number == 0

    def sort_episodes(self):
        """Sort episodes by episode number"""
        self.episodes.sort(
            key=lambda ep: ep.episode if ep.episode is not None else 999
        )

    def __str__(self) -> str:
        return f"Season {self.number} ({self.episode_count()} episodes)"

    def __repr__(self) -> str:
        return f"Season(number={self.number}, episodes={self.episode_count()})"
