"""Data Transfer Objects for scan operations"""
from dataclasses import dataclass
from typing import Dict

from domain.models.series import Series


@dataclass
class ScanResult:
    """Result of media scan operation"""
    series_map: Dict[str, Series]
    total_series: int
    total_episodes: int
    errors: list

    @classmethod
    def from_series_map(cls, series_map: Dict[str, Series], errors: list = None) -> "ScanResult":
        """Create ScanResult from series map

        Args:
            series_map: Dictionary of series name to Series object
            errors: List of error messages (optional)

        Returns:
            ScanResult instance
        """
        total_episodes = sum(s.total_episode_count() for s in series_map.values())

        return cls(
            series_map=series_map,
            total_series=len(series_map),
            total_episodes=total_episodes,
            errors=errors or []
        )
