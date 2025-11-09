"""Base command class for undo/redo pattern"""
from abc import ABC, abstractmethod
from typing import Any, Dict
from datetime import datetime


class Command(ABC):
    """Abstract base class for all commands

    Implements the Command pattern for undo/redo functionality.
    Each concrete command must implement execute() and undo() methods.
    """

    def __init__(self):
        """Initialize command with timestamp"""
        self.timestamp = datetime.now()
        self._metadata: Dict[str, Any] = {}

    @abstractmethod
    def execute(self) -> bool:
        """Execute the command

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def undo(self) -> bool:
        """Undo the command

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def describe(self) -> str:
        """Get human-readable description of the command

        Returns:
            Description string for user feedback
        """
        pass

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value

        Args:
            key: Metadata key
            default: Default value if key not found

        Returns:
            Metadata value or default
        """
        return self._metadata.get(key, default)

    def set_metadata(self, key: str, value: Any):
        """Set metadata value

        Args:
            key: Metadata key
            value: Metadata value
        """
        self._metadata[key] = value

    def __str__(self) -> str:
        return f"{self.__class__.__name__}: {self.describe()}"
