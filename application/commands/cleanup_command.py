"""Command for cleanup operations"""
from pathlib import Path
from typing import List, Dict
import shutil

from application.commands.base_command import Command


class CleanupCommand(Command):
    """Command to track and undo cleanup operations

    Stores all file deletions performed during cleanup
    and can restore them from trash.
    """

    def __init__(self, removed_files: List[str], trash_dir: Path, removed_dirs: List[str] = None):
        """Initialize cleanup command

        Args:
            removed_files: List of file paths that were removed
            trash_dir: Directory where files were moved (trash)
            removed_dirs: List of directory paths that were removed (optional)
        """
        super().__init__()
        self.removed_files = removed_files
        self.trash_dir = Path(trash_dir)
        self.removed_dirs = removed_dirs or []
        self._executed = False
        # Map original path to trash path
        self._file_mapping: Dict[str, str] = {}

    def execute(self) -> bool:
        """Execute cleanup operations

        Note: This is typically called AFTER the operations have
        already been performed. We mark it as executed for tracking.

        Returns:
            True if successful
        """
        self._executed = True

        # Build mapping of original paths to trash paths
        for original_path in self.removed_files:
            file_name = Path(original_path).name
            trash_path = self.trash_dir / file_name

            # Handle duplicate names in trash
            counter = 1
            while trash_path in self._file_mapping.values():
                stem = Path(original_path).stem
                suffix = Path(original_path).suffix
                trash_path = self.trash_dir / f"{stem}_{counter}{suffix}"
                counter += 1

            self._file_mapping[original_path] = str(trash_path)

        return True

    def undo(self) -> bool:
        """Undo cleanup operations by restoring files from trash and recreating directories

        Returns:
            True if successful, False otherwise
        """
        if not self._executed:
            return False

        try:
            restored_count = 0

            # Restore files first
            for original_path, trash_path in self._file_mapping.items():
                trash_file = Path(trash_path)
                original_file = Path(original_path)

                if not trash_file.exists():
                    # Try with just the filename in trash dir
                    trash_file = self.trash_dir / original_file.name
                    if not trash_file.exists():
                        print(f"Cannot restore: file no longer in trash: {original_file.name}")
                        continue

                # Recreate original directory if needed
                original_file.parent.mkdir(parents=True, exist_ok=True)

                # If original location is occupied, we can't restore
                if original_file.exists():
                    print(f"Cannot restore: file already exists at: {original_file}")
                    continue

                # Restore file from trash
                shutil.move(str(trash_file), str(original_file))
                print(f"Restored from trash: {original_file.name}")
                restored_count += 1

            # Recreate removed directories (in reverse order, so parent dirs are created last)
            for dir_path in reversed(self.removed_dirs):
                try:
                    dir_to_restore = Path(dir_path)
                    if not dir_to_restore.exists():
                        dir_to_restore.mkdir(parents=True, exist_ok=True)
                        print(f"Recreated directory: {dir_to_restore.name}")
                except Exception as e:
                    print(f"Failed to recreate directory {dir_path}: {e}")

            if restored_count > 0 or self.removed_dirs:
                self._executed = False
                return True
            else:
                print("No files or directories could be restored")
                return False

        except Exception as e:
            print(f"Error undoing cleanup: {e}")
            return False

    def describe(self) -> str:
        """Get description of cleanup operation

        Returns:
            Human-readable description
        """
        file_count = len(self.removed_files)
        dir_count = len(self.removed_dirs)

        if dir_count > 0:
            return f"Clean up {file_count} file(s) and {dir_count} folder(s)"
        else:
            return f"Clean up {file_count} file(s)"

    def get_file_count(self) -> int:
        """Get number of files affected

        Returns:
            Number of files
        """
        return len(self.removed_files)
