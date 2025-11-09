"""Unit tests for FluffParser"""
import pytest
from infrastructure.parsers.fluff_parser import FluffParser


def test_clean_name_basic():
    """Test basic fluff removal"""
    parser = FluffParser()

    assert parser.clean_name("Series.Name.[1080p]") == "Series Name"
    assert parser.clean_name("Movie.Title.(2023)") == "Movie Title"
    assert parser.clean_name("Series_Name_[GROUP]") == "Series Name"


def test_clean_name_quality_tags():
    """Test removal of quality tags"""
    parser = FluffParser()

    assert parser.clean_name("Series.1080p.BluRay") == "Series"
    assert parser.clean_name("Movie.720p.x264") == "Movie"
    assert parser.clean_name("Series.2160p.4K.HEVC") == "Series"


def test_clean_name_source_tags():
    """Test removal of source tags"""
    parser = FluffParser()

    assert parser.clean_name("Series.WEBRip") == "Series"
    assert parser.clean_name("Movie.BluRay.BDRip") == "Movie"
    assert parser.clean_name("Series.HDTV") == "Series"


def test_clean_name_complex():
    """Test complex filename with multiple fluff elements"""
    parser = FluffParser()

    input_name = "My.Anime.Series.[1080p][GROUP].S1.BluRay.x264"
    expected = "My Anime Series"
    assert parser.clean_name(input_name) == expected


def test_custom_patterns():
    """Test adding custom patterns"""
    parser = FluffParser()
    parser.add_pattern(r"\bCUSTOM\b")

    assert "CUSTOM" not in parser.clean_name("Series.Name.CUSTOM")


def test_get_patterns():
    """Test getting all patterns"""
    parser = FluffParser()
    patterns = parser.get_patterns()

    assert len(patterns) == len(FluffParser.DEFAULT_PATTERNS)
    assert r"\[.*?\]" in patterns


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
