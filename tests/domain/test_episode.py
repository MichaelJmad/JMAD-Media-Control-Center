"""Unit tests for Episode model"""
import pytest
from domain.models.episode import Episode
from domain.value_objects.file_path import FilePath
from domain.value_objects.episode_number import EpisodeNumber


def test_episode_creation():
    """Test basic episode creation"""
    path = FilePath("/test/episode.mkv")
    ep_num = EpisodeNumber(season=1, episode=5)

    episode = Episode(
        path=path,
        episode_number=ep_num,
        title="Test Episode"
    )

    assert episode.filename == "episode.mkv"
    assert episode.season == 1
    assert episode.episode == 5
    assert episode.title == "Test Episode"
    assert not episode.is_special()
    assert not episode.is_movie()


def test_episode_special():
    """Test special episode (Season 0)"""
    ep_num = EpisodeNumber(season=0, episode=1)
    episode = Episode(
        path=FilePath("/test/special.mkv"),
        episode_number=ep_num
    )

    assert episode.is_special()
    assert episode.season == 0


def test_episode_movie():
    """Test movie episode (season -1)"""
    ep_num = EpisodeNumber(season=-1, episode=0)
    episode = Episode(
        path=FilePath("/test/movie.mkv"),
        episode_number=ep_num
    )

    # Note: season=-1 is allowed by domain model for movies
    assert episode.is_movie()


def test_episode_without_number():
    """Test episode without parsed number"""
    episode = Episode(
        path=FilePath("/test/unknown.mkv"),
        episode_number=None
    )

    assert not episode.has_episode_info()
    assert episode.season is None
    assert episode.episode is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
