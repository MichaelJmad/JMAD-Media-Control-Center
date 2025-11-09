"""Unit tests for MediaScanner"""
import pytest
from pathlib import Path
import tempfile
import os

from infrastructure.services.media_scanner import MediaScanner
from infrastructure.parsers.fluff_parser import FluffParser
from domain.value_objects.file_path import FilePath
from domain.value_objects.media_type import MediaType


@pytest.fixture
def temp_media_dir():
    """Create a temporary directory with media files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test structure
        base = Path(tmpdir)

        # TV Series
        tv_series = base / "My Show [1080p]"
        tv_series.mkdir()
        (tv_series / "My.Show.S01E01.mkv").touch()
        (tv_series / "My.Show.S01E02.mkv").touch()

        # Anime
        anime_dir = base / "Anime"
        anime_dir.mkdir()
        anime_series = anime_dir / "Cool Anime"
        anime_series.mkdir()
        (anime_series / "Cool.Anime.S01E01.mkv").touch()

        # Movies
        movies_dir = base / "Movies"
        movies_dir.mkdir()
        movie1 = movies_dir / "Great Movie (2023)"
        movie1.mkdir()
        (movie1 / "Great.Movie.2023.mkv").touch()

        yield base


def test_scanner_basic(temp_media_dir):
    """Test basic scanning functionality"""
    scanner = MediaScanner(FluffParser())
    result = scanner.scan_directory(FilePath(temp_media_dir))

    # Should find series
    assert len(result) > 0


def test_scanner_tv_series(temp_media_dir):
    """Test scanning TV series"""
    scanner = MediaScanner(FluffParser())
    result = scanner.scan_directory(FilePath(temp_media_dir))

    # Check for "My Show"
    found = False
    for series_name, series in result.items():
        if "My Show" in series_name or "My Show" in series.clean_name:
            found = True
            assert series.total_episode_count() == 2
            assert series.season_count() >= 1

    assert found, "TV series not found"


def test_scanner_media_type_inference(temp_media_dir):
    """Test media type inference from folders"""
    scanner = MediaScanner(FluffParser())
    result = scanner.scan_directory(FilePath(temp_media_dir))

    # Check anime type
    for series_name, series in result.items():
        if "Anime" in series_name or "Cool Anime" in series.clean_name:
            assert series.media_type == MediaType.ANIME


def test_scanner_empty_directory():
    """Test scanning empty directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        scanner = MediaScanner(FluffParser())
        result = scanner.scan_directory(FilePath(tmpdir))
        assert len(result) == 0


def test_scanner_nonexistent_directory():
    """Test scanning non-existent directory"""
    scanner = MediaScanner(FluffParser())
    result = scanner.scan_directory(FilePath("/nonexistent/path"))
    assert len(result) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
