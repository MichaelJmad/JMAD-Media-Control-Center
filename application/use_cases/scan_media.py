"""Scan media use case"""
from typing import Optional, Callable

from domain.value_objects.file_path import FilePath
from infrastructure.services.media_scanner import MediaScanner
from infrastructure.parsers.fluff_parser import FluffParser
from application.dto.scan_result import ScanResult
from config.settings import Settings


class ScanMediaUseCase:
    """Use case for scanning media directories

    Scans the staging directory and discovers all media files,
    organizing them into Series objects.
    """

    def __init__(self, settings: Settings, logger: Optional[Callable] = None):
        """Initialize use case

        Args:
            settings: Application settings
            logger: Optional logging function
        """
        self.settings = settings
        self.logger = logger or print

        # Initialize scanner with fluff parser and settings
        fluff_parser = FluffParser(self.settings.fluff_patterns)
        self.scanner = MediaScanner(fluff_parser, settings)

    def execute(self) -> ScanResult:
        """Execute the scan operation

        Returns:
            ScanResult with discovered media
        """
        staging_dir = self.settings.directories.staging

        if not staging_dir:
            self.logger("Error: Staging directory not configured")
            return ScanResult.from_series_map({}, errors=["Staging directory not configured"])

        staging_path = FilePath(staging_dir)

        if not staging_path.exists():
            self.logger(f"Error: Staging directory does not exist: {staging_dir}")
            return ScanResult.from_series_map({}, errors=["Staging directory does not exist"])

        if not staging_path.is_dir():
            self.logger(f"Error: Staging path is not a directory: {staging_dir}")
            return ScanResult.from_series_map({}, errors=["Staging path is not a directory"])

        # Execute scan
        self.logger(f"Scanning directory: {staging_dir}")
        series_map = self.scanner.scan_directory(staging_path)

        # Check for non-standard structures
        for series in series_map.values():
            if self.scanner.detect_nonstandard_structure(series):
                series.has_nonstandard_folders = True

        result = ScanResult.from_series_map(series_map)

        # V1: Count files instead of episodes
        total_files = sum(getattr(s, '_v1_file_count', 0) for s in series_map.values())
        self.logger(f"Scan complete. Found {result.total_series} folders with {total_files} files")

        return result
