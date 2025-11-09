"""Unit tests for Series model"""
import pytest
from domain.models.series import Series
from domain.models.episode import Episode
from domain.value_objects.media_type import MediaType
from domain.value_objects.file_path import FilePath
from domain.value_objects.episode_number import EpisodeNumber


def test_series_creation():
    """Test basic series creation"""
    series = Series(
        name="Test Series",
        clean_name="Test Series",
        media_type=MediaType.TV_SERIES,
        root_path=FilePath("/test/series")
    )

    assert series.name == "Test Series"
    assert series.media_type == MediaType.TV_SERIES
    assert series.season_count() == 0
    assert series.total_episode_count() == 0


def test_series_add_episodes():
    """Test adding episodes to series"""
    series = Series(name="Test Series", media_type=MediaType.ANIME)

    # Add episode to season 1
    ep1 = Episode(
        path=FilePath("/test/ep1.mkv"),
        episode_number=EpisodeNumber(season=1, episode=1)
    )
    series.add_episode(ep1)

    assert series.season_count() == 1
    assert series.total_episode_count() == 1

    # Add another episode to season 1
    ep2 = Episode(
        path=FilePath("/test/ep2.mkv"),
        episode_number=EpisodeNumber(season=1, episode=2)
    )
    series.add_episode(ep2)

    assert series.season_count() == 1
    assert series.total_episode_count() == 2

    # Add episode to season 2
    ep3 = Episode(
        path=FilePath("/test/ep3.mkv"),
        episode_number=EpisodeNumber(season=2, episode=1)
    )
    series.add_episode(ep3)

    assert series.season_count() == 2
    assert series.total_episode_count() == 3


def test_series_unsorted_episodes():
    """Test series with unsorted episodes"""
    series = Series(name="Test Series")

    # Add episode without season info
    ep = Episode(
        path=FilePath("/test/unknown.mkv"),
        episode_number=None
    )
    series.add_episode(ep)

    assert series.season_count() == 0
    assert series.total_episode_count() == 1
    assert len(series.unsorted_episodes) == 1


def test_series_has_specials():
    """Test series with specials"""
    series = Series(name="Test Series")

    # Add special episode
    special = Episode(
        path=FilePath("/test/special.mkv"),
        episode_number=EpisodeNumber(season=0, episode=1)
    )
    series.add_episode(special)

    assert series.has_specials()
    assert series.season_count() == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
