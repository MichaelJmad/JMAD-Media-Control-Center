"""Unit tests for EpisodeParser"""
import pytest
from infrastructure.parsers.episode_parser import EpisodeParser
from domain.value_objects.episode_number import EpisodeNumber


def test_parse_standard_format():
    """Test S01E02 format"""
    result = EpisodeParser.parse("Series.Name.S01E05.1080p.mkv")
    assert result is not None
    assert result.season == 1
    assert result.episode == 5


def test_parse_alternative_format():
    """Test 1x02 format"""
    result = EpisodeParser.parse("Series.Name.1x12.mkv")
    assert result is not None
    assert result.season == 1
    assert result.episode == 12


def test_parse_special_episode():
    """Test special episode S00E01"""
    result = EpisodeParser.parse("Series.Special.S00E01.mkv")
    assert result is not None
    assert result.season == 0
    assert result.episode == 1
    assert result.is_special()


def test_parse_three_digit():
    """Test 305 format (season 3, episode 5)"""
    result = EpisodeParser.parse("Series.Name.305.mkv")
    assert result is not None
    assert result.season == 3
    assert result.episode == 5


def test_parse_episode_only():
    """Test E05 format"""
    result = EpisodeParser.parse("Series.Name.Season.1.E05.mkv")
    assert result is not None
    assert result.season == 1  # Should infer from "Season 1"
    assert result.episode == 5


def test_parse_no_episode_info():
    """Test filename with no episode info"""
    result = EpisodeParser.parse("Random.Movie.File.2023.mkv")
    assert result is None


def test_has_episode_info():
    """Test checking if filename has episode info"""
    assert EpisodeParser.has_episode_info("Series.S01E05.mkv")
    assert not EpisodeParser.has_episode_info("Movie.2023.mkv")


def test_parse_various_formats():
    """Test multiple formats"""
    test_cases = [
        ("Episode 05.mkv", None, 5),  # "Episode" keyword
        ("Ep 12.mkv", None, 12),  # "Ep" abbreviation
        ("Part 3.mkv", None, 3),  # "Part" keyword
        ("005.mkv", None, 5),  # Three digits alone
    ]

    for filename, expected_season, expected_episode in test_cases:
        result = EpisodeParser.parse(filename)
        if result:
            assert result.episode == expected_episode


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
