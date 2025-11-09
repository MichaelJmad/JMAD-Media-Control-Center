"""Unit tests for FileSystemService"""
import pytest
import tempfile
from pathlib import Path

from infrastructure.services.file_system_service import (
    FileSystemService,
    MoveOperation,
)
from domain.value_objects.file_path import FilePath


@pytest.fixture
def temp_files():
    """Create temporary test files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)

        # Create source files
        source_dir = base / "source"
        source_dir.mkdir()

        file1 = source_dir / "file1.txt"
        file2 = source_dir / "file2.txt"

        file1.write_text("test content 1")
        file2.write_text("test content 2")

        # Create destination directory
        dest_dir = base / "destination"
        dest_dir.mkdir()

        yield {
            "base": base,
            "source_dir": source_dir,
            "dest_dir": dest_dir,
            "file1": file1,
            "file2": file2,
        }


def test_move_single_file(temp_files):
    """Test moving a single file"""
    service = FileSystemService()

    source = FilePath(temp_files["file1"])
    dest = FilePath(temp_files["dest_dir"] / "file1.txt")

    operations = [MoveOperation(source=source, destination=dest)]
    result = service.move_files(operations)

    assert result.success
    assert result.operations_completed == 1
    assert result.operations_failed == 0
    assert dest.exists()
    assert not source.exists()


def test_move_multiple_files(temp_files):
    """Test moving multiple files"""
    service = FileSystemService()

    operations = [
        MoveOperation(
            source=FilePath(temp_files["file1"]),
            destination=FilePath(temp_files["dest_dir"] / "file1.txt")
        ),
        MoveOperation(
            source=FilePath(temp_files["file2"]),
            destination=FilePath(temp_files["dest_dir"] / "file2.txt")
        ),
    ]

    result = service.move_files(operations)

    assert result.success
    assert result.operations_completed == 2
    assert len(result.errors) == 0


def test_move_nonexistent_file(temp_files):
    """Test moving a file that doesn't exist"""
    service = FileSystemService()

    source = FilePath(temp_files["source_dir"] / "nonexistent.txt")
    dest = FilePath(temp_files["dest_dir"] / "nonexistent.txt")

    operations = [MoveOperation(source=source, destination=dest)]
    result = service.move_files(operations)

    assert not result.success
    assert result.operations_failed == 1


def test_validate_path(temp_files):
    """Test path validation"""
    service = FileSystemService()

    valid_path = FilePath(temp_files["file1"])
    invalid_path = FilePath(temp_files["source_dir"] / "nonexistent.txt")

    assert service.validate_path(valid_path)
    assert not service.validate_path(invalid_path)


def test_prune_empty_directories(temp_files):
    """Test pruning empty directories"""
    service = FileSystemService()

    # Create nested empty directories
    nested = temp_files["base"] / "a" / "b" / "c"
    nested.mkdir(parents=True)

    # Prune from deepest
    service.prune_empty_directories(FilePath(nested))

    # All empty directories should be removed
    assert not nested.exists()
    assert not (temp_files["base"] / "a" / "b").exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
