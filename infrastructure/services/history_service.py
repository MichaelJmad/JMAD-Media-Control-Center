"""History service for undo/redo operations"""
from dataclasses import dataclass
from typing import List, Optional, Callable
from enum import Enum

from infrastructure.services.file_system_service import FileSystemService, MoveOperation


class ActionType(Enum):
    """Type of history action"""
    MOVE = "move"
    DELETE = "delete"
    ORGANIZE = "organize"
    CLEANUP = "cleanup"


@dataclass
class HistoryAction:
    """Represents an action that can be undone/redone"""
    description: str
    action_type: ActionType
    operations: List[MoveOperation]
    metadata: dict = None  # Additional metadata (e.g., deleted files for restore)

    def __str__(self) -> str:
        return f"{self.description} ({len(self.operations)} operations)"


class HistoryService:
    """Service for managing undo/redo history

    Maintains a stack of actions that can be undone and redone.
    """

    def __init__(self, file_system_service: FileSystemService, logger: Optional[Callable] = None):
        """Initialize history service

        Args:
            file_system_service: Service for file operations
            logger: Optional logging function
        """
        self.file_system = file_system_service
        self.logger = logger or print
        self.history: List[HistoryAction] = []
        self.current_position = -1

    def execute_action(self, action: HistoryAction) -> bool:
        """Execute an action and add to history

        Args:
            action: HistoryAction to execute

        Returns:
            True if successful, False otherwise
        """
        # Execute the move operations
        result = self.file_system.move_files(action.operations)

        if result.success:
            # Clear any redo history (can't redo after new action)
            if self.current_position < len(self.history) - 1:
                self.history = self.history[:self.current_position + 1]

            # Add to history
            self.history.append(action)
            self.current_position += 1

            self.logger(f"Action executed: {action.description}")
            return True
        else:
            self.logger(f"Action failed: {action.description}")
            for error in result.errors:
                self.logger(f"  Error: {error}")
            return False

    def can_undo(self) -> bool:
        """Check if undo is available

        Returns:
            True if can undo, False otherwise
        """
        return self.current_position >= 0

    def can_redo(self) -> bool:
        """Check if redo is available

        Returns:
            True if can redo, False otherwise
        """
        return self.current_position < len(self.history) - 1

    def undo(self) -> bool:
        """Undo the last action

        Returns:
            True if successful, False otherwise
        """
        if not self.can_undo():
            return False

        action = self.history[self.current_position]
        self.logger(f"Undoing: {action.description}")

        # Reverse the operations (move files back)
        reverse_operations = [
            MoveOperation(source=op.destination, destination=op.source)
            for op in reversed(action.operations)
        ]

        result = self.file_system.move_files(reverse_operations)

        if result.success:
            self.current_position -= 1
            self.logger(f"Undo successful: {action.description}")
            return True
        else:
            self.logger(f"Undo failed: {action.description}")
            for error in result.errors:
                self.logger(f"  Error: {error}")
            return False

    def redo(self) -> bool:
        """Redo the next action

        Returns:
            True if successful, False otherwise
        """
        if not self.can_redo():
            return False

        self.current_position += 1
        action = self.history[self.current_position]
        self.logger(f"Redoing: {action.description}")

        result = self.file_system.move_files(action.operations)

        if result.success:
            self.logger(f"Redo successful: {action.description}")
            return True
        else:
            self.logger(f"Redo failed: {action.description}")
            self.current_position -= 1  # Revert position
            for error in result.errors:
                self.logger(f"  Error: {error}")
            return False

    def get_undo_description(self) -> Optional[str]:
        """Get description of action that would be undone

        Returns:
            Description string or None if can't undo
        """
        if self.can_undo():
            return self.history[self.current_position].description
        return None

    def get_redo_description(self) -> Optional[str]:
        """Get description of action that would be redone

        Returns:
            Description string or None if can't redo
        """
        if self.can_redo():
            return self.history[self.current_position + 1].description
        return None

    def clear_history(self):
        """Clear all history"""
        self.history.clear()
        self.current_position = -1
        self.logger("History cleared")

    def get_history_list(self) -> List[str]:
        """Get list of all actions in history

        Returns:
            List of action descriptions
        """
        return [action.description for action in self.history]

    def get_current_position(self) -> int:
        """Get current position in history

        Returns:
            Current position index
        """
        return self.current_position
