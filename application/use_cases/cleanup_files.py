"""Cleanup files use case"""
from typing import Set, Optional, Callable, List

from domain.value_objects.file_path import FilePath
from infrastructure.services.file_system_service import FileSystemService, MoveOperation
from infrastructure.services.history_service import HistoryService, HistoryAction, ActionType
from config.settings import Settings


class CleanupFilesUseCase:
    """Use case for cleaning up junk files

    Removes or moves unwanted files (NFOs, images, etc.) to trash.
    """

    def __init__(
        self,
        settings: Settings,
        file_system: FileSystemService,
        history: Optional[HistoryService] = None,
        logger: Optional[Callable] = None
    ):
        """Initialize use case

        Args:
            settings: Application settings
            file_system: File system service
            history: Optional history service for undo
            logger: Optional logging function
        """
        self.settings = settings
        self.file_system = file_system
        self.history = history
        self.logger = logger or print

    def execute(
        self,
        extensions: Set[str],
        target_paths: Optional[List[FilePath]] = None,
        use_trash: bool = True
    ) -> dict:
        """Execute cleanup operation

        Args:
            extensions: Set of extensions to clean (e.g., {'.nfo', '.txt'})
            target_paths: Optional list of specific paths to clean (defaults to staging)
            use_trash: If True, move to trash; if False, delete permanently

        Returns:
            Dictionary with cleanup results
        """
        # Default to staging directory if no targets specified
        if not target_paths:
            staging = self.settings.directories.staging
            if not staging:
                return {"success": False, "error": "No staging directory configured"}
            target_paths = [FilePath(staging)]

        # Find all files to clean
        files_to_clean = []
        for path in target_paths:
            if not path.exists():
                continue

            found = self.file_system.scan_directory(path, extensions)
            files_to_clean.extend(found)

        if not files_to_clean:
            self.logger(f"No files found with extensions: {', '.join(sorted(extensions))}")
            return {
                "success": True,
                "files_cleaned": 0,
                "message": "No files to clean"
            }

        # Confirm with count
        self.logger(f"Found {len(files_to_clean)} files to clean")

        # Execute cleanup
        if use_trash:
            result = self._move_to_trash(files_to_clean, target_paths[0])
        else:
            result = self._delete_permanently(files_to_clean)

        return result

    def _move_to_trash(self, files: List[FilePath], root_path: FilePath) -> dict:
        """Move files to trash directory

        Args:
            files: Files to move
            root_path: Root path for calculating relative paths

        Returns:
            Result dictionary
        """
        trash_dir = self.settings.directories.trash

        if not trash_dir or not FilePath(trash_dir).exists():
            self.logger("Warning: Trash directory not configured, files will be deleted permanently")
            return self._delete_permanently(files)

        trash_path = FilePath(trash_dir)

        # Build move operations with mirrored structure
        operations = []
        for file_path in files:
            # Calculate relative path from root
            relative = file_path.relative_to(root_path)
            if relative:
                dest = FilePath(trash_path.path / relative)
            else:
                # Fallback: use filename only
                dest = FilePath(trash_path.path / file_path.name)

            operations.append(MoveOperation(source=file_path, destination=dest))

        # Execute moves
        if self.history:
            action = HistoryAction(
                description=f"Cleanup {len(operations)} files",
                action_type=ActionType.CLEANUP,
                operations=operations
            )
            success = self.history.execute_action(action)
        else:
            result = self.file_system.move_files(operations)
            success = result.success

        if success:
            self.logger(f"Cleaned {len(operations)} files (moved to trash)")
            return {
                "success": True,
                "files_cleaned": len(operations),
                "method": "trash"
            }
        else:
            return {
                "success": False,
                "files_cleaned": 0,
                "error": "Failed to move files to trash"
            }

    def _delete_permanently(self, files: List[FilePath]) -> dict:
        """Delete files permanently

        Args:
            files: Files to delete

        Returns:
            Result dictionary
        """
        result = self.file_system.delete_files(files)

        if result.success:
            self.logger(f"Cleaned {result.operations_completed} files (permanently deleted)")
            return {
                "success": True,
                "files_cleaned": result.operations_completed,
                "method": "permanent"
            }
        else:
            self.logger(f"Cleanup failed: {len(result.errors)} errors")
            for error in result.errors:
                self.logger(f"  {error}")
            return {
                "success": False,
                "files_cleaned": result.operations_completed,
                "errors": result.errors
            }
