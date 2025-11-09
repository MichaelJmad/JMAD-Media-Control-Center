"""File system operations service"""
import shutil
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass

from domain.value_objects.file_path import FilePath


@dataclass
class MoveOperation:
    """Represents a file move operation"""
    source: FilePath
    destination: FilePath

    def __str__(self) -> str:
        return f"{self.source.name} -> {self.destination.absolute}"


@dataclass
class MoveResult:
    """Result of move operations"""
    success: bool
    operations_completed: int
    operations_failed: int
    errors: List[str]


class FileSystemService:
    """Service for all file system operations

    Provides safe file operations with rollback capability.
    """

    def __init__(self):
        """Initialize file system service"""
        pass

    def move_files(self, operations: List[MoveOperation]) -> MoveResult:
        """Execute a list of move operations

        Args:
            operations: List of MoveOperation objects

        Returns:
            MoveResult with success status and any errors
        """
        completed = []
        errors = []

        for operation in operations:
            try:
                result = self._move_single_file(operation)
                if result:
                    completed.append(operation)
                else:
                    errors.append(f"Failed to move {operation.source.name}")
            except Exception as e:
                errors.append(f"Error moving {operation.source.name}: {str(e)}")

        success = len(errors) == 0
        return MoveResult(
            success=success,
            operations_completed=len(completed),
            operations_failed=len(errors),
            errors=errors
        )

    def _move_single_file(self, operation: MoveOperation) -> bool:
        """Move a single file

        Args:
            operation: MoveOperation to execute

        Returns:
            True if successful, False otherwise
        """
        try:
            source = operation.source.path
            destination = operation.destination.path

            # Check source exists
            if not source.exists():
                return False

            # Create destination directory if needed
            destination.parent.mkdir(parents=True, exist_ok=True)

            # Move the file
            shutil.move(str(source), str(destination))

            return True

        except (OSError, PermissionError, FileNotFoundError):
            return False

    def copy_files(self, operations: List[MoveOperation]) -> MoveResult:
        """Copy files (instead of moving)

        Args:
            operations: List of MoveOperation objects (used for source/dest)

        Returns:
            MoveResult with success status and any errors
        """
        completed = []
        errors = []

        for operation in operations:
            try:
                source = operation.source.path
                destination = operation.destination.path

                if not source.exists():
                    errors.append(f"Source not found: {operation.source.name}")
                    continue

                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(source), str(destination))
                completed.append(operation)

            except Exception as e:
                errors.append(f"Error copying {operation.source.name}: {str(e)}")

        success = len(errors) == 0
        return MoveResult(
            success=success,
            operations_completed=len(completed),
            operations_failed=len(errors),
            errors=errors
        )

    def delete_files(self, paths: List[FilePath]) -> MoveResult:
        """Delete files

        Args:
            paths: List of FilePath objects to delete

        Returns:
            MoveResult with success status and any errors
        """
        completed = 0
        errors = []

        for file_path in paths:
            try:
                if file_path.exists():
                    file_path.path.unlink()
                    completed += 1
                else:
                    errors.append(f"File not found: {file_path.name}")
            except Exception as e:
                errors.append(f"Error deleting {file_path.name}: {str(e)}")

        success = len(errors) == 0
        return MoveResult(
            success=success,
            operations_completed=completed,
            operations_failed=len(errors),
            errors=errors
        )

    def validate_path(self, path: FilePath) -> bool:
        """Check if path exists and is accessible

        Args:
            path: FilePath to validate

        Returns:
            True if path is valid and accessible, False otherwise
        """
        return path.exists()

    def prune_empty_directories(self, path: FilePath, stop_at: Optional[FilePath] = None):
        """Remove empty directories recursively up the tree

        Args:
            path: Starting directory to prune
            stop_at: Stop pruning at this directory (don't remove it or above)
        """
        try:
            current = path.path

            # Don't prune if not a directory
            if not current.is_dir():
                return

            # Prune upward while empty
            while current.is_dir() and not any(current.iterdir()):
                # Stop if we've reached the stop_at directory
                if stop_at and current == stop_at.path:
                    break

                parent = current.parent
                current.rmdir()
                current = parent

        except (OSError, PermissionError):
            # Silently ignore permission errors
            pass

    def get_directory_size(self, path: FilePath) -> int:
        """Calculate total size of directory in bytes

        Args:
            path: Directory to measure

        Returns:
            Total size in bytes
        """
        total = 0
        try:
            for entry in path.path.rglob("*"):
                if entry.is_file():
                    total += entry.stat().st_size
        except (OSError, PermissionError):
            pass
        return total

    def scan_directory(self, path: FilePath, extensions: set = None) -> List[FilePath]:
        """Scan directory for files with specific extensions

        Args:
            path: Directory to scan
            extensions: Set of extensions to filter (e.g., {'.mkv', '.mp4'})
                       If None, returns all files

        Returns:
            List of FilePath objects for matching files
        """
        files = []

        try:
            for entry in path.path.rglob("*"):
                if entry.is_file():
                    if extensions is None or entry.suffix.lower() in extensions:
                        files.append(FilePath(entry))
        except (OSError, PermissionError):
            pass

        return files
