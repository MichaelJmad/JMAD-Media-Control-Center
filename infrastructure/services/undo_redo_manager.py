"""Undo/Redo manager service"""
from typing import List, Optional
from PySide6.QtCore import QObject, Signal

from application.commands.base_command import Command


class UndoRedoManager(QObject):
    """Manages command history for undo/redo functionality

    Singleton service that maintains undo and redo stacks.
    Emits signals when undo/redo availability changes.
    """

    # Signals
    history_changed = Signal()  # Emitted when history state changes
    undo_available = Signal(bool)  # Emitted when undo availability changes
    redo_available = Signal(bool)  # Emitted when redo availability changes

    _instance: Optional['UndoRedoManager'] = None

    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, max_history: int = 50):
        """Initialize undo/redo manager

        Args:
            max_history: Maximum number of commands to keep in history
        """
        if self._initialized:
            return

        super().__init__()
        self._undo_stack: List[Command] = []
        self._redo_stack: List[Command] = []
        self._max_history = max_history
        self._initialized = True

    def execute_command(self, command: Command) -> bool:
        """Execute a command and add it to undo stack

        Args:
            command: Command to execute

        Returns:
            True if successful, False otherwise
        """
        try:
            if command.execute():
                # Add to undo stack
                self._undo_stack.append(command)

                # Clear redo stack (can't redo after new action)
                self._redo_stack.clear()

                # Limit history size
                if len(self._undo_stack) > self._max_history:
                    self._undo_stack.pop(0)

                self._emit_history_signals()
                return True
            return False

        except Exception as e:
            print(f"Error executing command: {e}")
            return False

    def undo(self) -> bool:
        """Undo the last command

        Returns:
            True if successful, False otherwise
        """
        if not self.can_undo():
            return False

        try:
            command = self._undo_stack.pop()

            if command.undo():
                # Move to redo stack
                self._redo_stack.append(command)
                self._emit_history_signals()
                return True
            else:
                # Undo failed, put command back
                self._undo_stack.append(command)
                return False

        except Exception as e:
            print(f"Error undoing command: {e}")
            return False

    def redo(self) -> bool:
        """Redo the last undone command

        Returns:
            True if successful, False otherwise
        """
        if not self.can_redo():
            return False

        try:
            command = self._redo_stack.pop()

            if command.execute():
                # Move back to undo stack
                self._undo_stack.append(command)
                self._emit_history_signals()
                return True
            else:
                # Redo failed, put command back
                self._redo_stack.append(command)
                return False

        except Exception as e:
            print(f"Error redoing command: {e}")
            return False

    def can_undo(self) -> bool:
        """Check if undo is available

        Returns:
            True if there are commands to undo
        """
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        """Check if redo is available

        Returns:
            True if there are commands to redo
        """
        return len(self._redo_stack) > 0

    def get_undo_description(self) -> Optional[str]:
        """Get description of next undo operation

        Returns:
            Description string or None if no undo available
        """
        if self.can_undo():
            return self._undo_stack[-1].describe()
        return None

    def get_redo_description(self) -> Optional[str]:
        """Get description of next redo operation

        Returns:
            Description string or None if no redo available
        """
        if self.can_redo():
            return self._redo_stack[-1].describe()
        return None

    def clear_history(self):
        """Clear all undo/redo history"""
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._emit_history_signals()

    def get_history_size(self) -> int:
        """Get total number of commands in history

        Returns:
            Total size of undo + redo stacks
        """
        return len(self._undo_stack) + len(self._redo_stack)

    def _emit_history_signals(self):
        """Emit signals to update UI"""
        self.history_changed.emit()
        self.undo_available.emit(self.can_undo())
        self.redo_available.emit(self.can_redo())

    def __str__(self) -> str:
        return f"UndoRedoManager(undo={len(self._undo_stack)}, redo={len(self._redo_stack)})"
