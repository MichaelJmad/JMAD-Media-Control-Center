"""Command for organizing media files"""
from pathlib import Path
from typing import List, Dict, Tuple
import shutil

from application.commands.base_command import Command


class OrganizeCommand(Command):
    """Command to track and undo organize operations

    Stores all file movements performed during organization
    and can reverse them.
    """

    def __init__(self, operations: List[Dict[str, str]], media_type: str):
        """Initialize organize command

        Args:
            operations: List of file operations, each dict contains:
                - 'source': Original file path
                - 'destination': New file path
            media_type: Type of media (anime, tv_shows, movies)
        """
        super().__init__()
        self.operations = operations
        self.media_type = media_type
        self._executed = False
        self._created_dirs: List[Path] = []

    def execute(self) -> bool:
        """Execute organize operations

        Note: This is typically called AFTER the operations have
        already been performed. We mark it as executed for tracking.

        Returns:
            True if successful
        """
        self._executed = True
        return True

    def undo(self) -> bool:
        """Undo organize operations by reversing file movements

        Returns:
            True if successful, False otherwise
        """
        if not self._executed:
            return False

        try:
            # Reverse the operations in reverse order
            for operation in reversed(self.operations):
                dest = Path(operation['destination'])
                source = Path(operation['source'])

                if not dest.exists():
                    print(f"Cannot undo: destination file no longer exists: {dest}")
                    continue

                # Recreate source directory if needed
                source.parent.mkdir(parents=True, exist_ok=True)

                # Move file back to original location
                shutil.move(str(dest), str(source))
                print(f"Restored: {dest.name} → {source}")

            # Remove empty directories created during organize
            self._cleanup_empty_directories()

            self._executed = False
            return True

        except Exception as e:
            print(f"Error undoing organize: {e}")
            return False

    def _cleanup_empty_directories(self):
        """Remove empty directories created during organize"""
        # Collect all unique destination directories
        dest_dirs = set()
        for operation in self.operations:
            dest_path = Path(operation['destination'])
            # Add parent directories up to the media type folder
            current = dest_path.parent
            while current.name and current.name.lower() not in ['staging', '']:
                dest_dirs.add(current)
                current = current.parent

        # Try to remove directories (will only remove if empty)
        for dir_path in sorted(dest_dirs, key=lambda p: len(str(p)), reverse=True):
            try:
                if dir_path.exists() and not any(dir_path.iterdir()):
                    dir_path.rmdir()
                    print(f"Removed empty directory: {dir_path}")
            except (OSError, PermissionError):
                pass  # Directory not empty or permission denied

    def describe(self) -> str:
        """Get description of organize operation

        Returns:
            Human-readable description
        """
        file_count = len(self.operations)
        return f"Organize {file_count} file(s) as {self.media_type}"

    def get_file_count(self) -> int:
        """Get number of files affected

        Returns:
            Number of files
        """
        return len(self.operations)
