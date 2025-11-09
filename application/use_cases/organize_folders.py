"""Organize folders use case (V1 simplified version)"""
from typing import List, Optional, Callable
from pathlib import Path

from domain.value_objects.file_path import FilePath
from infrastructure.services.file_system_service import FileSystemService, MoveOperation
from infrastructure.services.history_service import HistoryService, HistoryAction, ActionType


class OrganizeFoldersUseCase:
    """Use case for organizing folders to library directories

    V1 behavior: Simple folder moves without complex parsing.
    Works with folder names directly from staging.
    """

    def __init__(
        self,
        staging_dir: str,
        file_system: FileSystemService,
        history: Optional[HistoryService] = None,
        logger: Optional[Callable] = None
    ):
        """Initialize use case

        Args:
            staging_dir: Path to staging directory
            file_system: File system service
            history: Optional history service for undo
            logger: Optional logging function
        """
        self.staging_dir = FilePath(staging_dir)
        self.file_system = file_system
        self.history = history
        self.logger = logger or print

    def execute(
        self,
        folder_names: List[str],
        destination_dir: str
    ) -> dict:
        """Execute organize operation

        Args:
            folder_names: List of folder names to organize
            destination_dir: Destination directory path

        Returns:
            Dictionary with operation results
        """
        destination = FilePath(destination_dir)

        # Validate destination
        if not destination.exists():
            try:
                destination.path.mkdir(parents=True, exist_ok=True)
                self.logger(f"Created destination directory: {destination_dir}")
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to create destination: {str(e)}"
                }

        if not destination.is_dir():
            return {
                "success": False,
                "error": "Destination is not a directory"
            }

        # Build move operations
        operations = []
        conflicts = []
        not_found = []

        for folder_name in folder_names:
            source = FilePath(self.staging_dir.path / folder_name)

            if not source.exists():
                not_found.append(folder_name)
                continue

            dest = FilePath(destination.path / folder_name)

            if dest.exists():
                conflicts.append(folder_name)
            else:
                operations.append(MoveOperation(source=source, destination=dest))

        # Report issues
        if not_found:
            self.logger(f"Warning: Folders not found in staging: {', '.join(not_found)}")

        if conflicts:
            self.logger(f"Conflicts detected: {', '.join(conflicts)}")
            return {
                "success": False,
                "conflicts": conflicts,
                "not_found": not_found,
                "error": f"{len(conflicts)} folder(s) already exist at destination"
            }

        if not operations:
            return {
                "success": False,
                "error": "No folders to move",
                "not_found": not_found
            }

        # Execute moves
        self.logger(f"Moving {len(operations)} folder(s) to {destination_dir}...")

        if self.history:
            action = HistoryAction(
                description=f"Organize {len(operations)} folder(s) to {Path(destination_dir).name}",
                action_type=ActionType.MOVE,
                operations=operations
            )
            success = self.history.execute_action(action)
            result = {
                "success": success,
                "folders_moved": len(operations) if success else 0,
                "destination": destination.absolute,
                "not_found": not_found
            }
        else:
            move_result = self.file_system.move_files(operations)
            result = {
                "success": move_result.success,
                "folders_moved": move_result.operations_completed,
                "destination": destination.absolute,
                "errors": move_result.errors,
                "not_found": not_found
            }

        if result["success"]:
            self.logger(f"✓ Successfully moved {result['folders_moved']} folder(s)")
        else:
            errors = result.get('errors', ['Unknown error'])
            self.logger(f"✗ Move failed: {errors}")

        return result
