"""Move series use case"""
from typing import List, Optional, Callable

from domain.models.series import Series
from domain.value_objects.file_path import FilePath
from infrastructure.services.file_system_service import FileSystemService, MoveOperation
from infrastructure.services.history_service import HistoryService, HistoryAction, ActionType


class MoveSeriesUseCase:
    """Use case for moving series to library

    Moves organized series from staging to permanent library location.
    """

    def __init__(
        self,
        file_system: FileSystemService,
        history: Optional[HistoryService] = None,
        logger: Optional[Callable] = None
    ):
        """Initialize use case

        Args:
            file_system: File system service
            history: Optional history service for undo
            logger: Optional logging function
        """
        self.file_system = file_system
        self.history = history
        self.logger = logger or print

    def execute(
        self,
        series_list: List[Series],
        destination: FilePath
    ) -> dict:
        """Execute move operation

        Args:
            series_list: List of Series to move
            destination: Destination directory

        Returns:
            Dictionary with move results
        """
        if not destination.exists() or not destination.is_dir():
            return {
                "success": False,
                "error": "Destination directory does not exist"
            }

        # Check for conflicts
        conflicts = []
        operations = []

        for series in series_list:
            source = series.root_path
            dest = FilePath(destination.path / source.name)

            if dest.exists():
                conflicts.append(series.name)
            else:
                operations.append(MoveOperation(source=source, destination=dest))

        if conflicts:
            self.logger(f"Conflicts detected: {', '.join(conflicts)}")
            return {
                "success": False,
                "conflicts": conflicts,
                "error": f"{len(conflicts)} series already exist at destination"
            }

        if not operations:
            return {
                "success": False,
                "error": "No series to move"
            }

        # Execute moves
        if self.history:
            action = HistoryAction(
                description=f"Move {len(operations)} series to {destination.name}",
                action_type=ActionType.MOVE,
                operations=operations
            )
            success = self.history.execute_action(action)
            result = {
                "success": success,
                "series_moved": len(operations) if success else 0,
                "destination": destination.absolute
            }
        else:
            move_result = self.file_system.move_files(operations)
            result = {
                "success": move_result.success,
                "series_moved": move_result.operations_completed,
                "destination": destination.absolute,
                "errors": move_result.errors
            }

        if result["success"]:
            self.logger(f"Moved {result['series_moved']} series to {destination.name}")
        else:
            self.logger(f"Move failed: {result.get('errors', 'Unknown error')}")

        return result
