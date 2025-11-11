"""Conflict resolution dialog for file conflicts during organize operations"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QRadioButton, QButtonGroup, QListWidget, QGroupBox
)
from PySide6.QtCore import Qt
from typing import List, Tuple


class ConflictResolutionDialog(QDialog):
    """Dialog for resolving file conflicts during organize operations

    Shows conflicting files and allows user to choose:
    - Overwrite all conflicts
    - Rename all conflicts (append number)
    - Cancel operation
    """

    # Return codes
    ACTION_OVERWRITE = 1
    ACTION_RENAME = 2
    ACTION_CANCEL = 0

    def __init__(self, parent, conflicts: List[Tuple[str, str]]):
        """Initialize conflict resolution dialog

        Args:
            parent: Parent widget
            conflicts: List of (source_file, target_file) tuples that conflict
        """
        super().__init__(parent)

        self.conflicts = conflicts
        self.selected_action = self.ACTION_CANCEL

        self.setWindowTitle("File Conflicts Detected")
        self.setModal(True)
        self.resize(600, 400)

        self._build_ui()

    def _build_ui(self):
        """Build the dialog UI"""
        layout = QVBoxLayout(self)

        # Header
        header = QLabel(f"Found {len(self.conflicts)} file conflict(s)")
        header.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px;")
        layout.addWidget(header)

        # Explanation
        explanation = QLabel(
            "The following files already exist at the destination.\n"
            "Choose how to handle these conflicts:"
        )
        explanation.setWordWrap(True)
        explanation.setStyleSheet("padding: 5px; color: #666;")
        layout.addWidget(explanation)

        # Conflicts list
        conflicts_group = QGroupBox("Conflicting Files:")
        conflicts_layout = QVBoxLayout(conflicts_group)

        self.conflicts_list = QListWidget()
        self.conflicts_list.setAlternatingRowColors(True)

        for source_file, target_file in self.conflicts:
            # Show just the filename, not full path
            from pathlib import Path
            source_name = Path(source_file).name
            target_name = Path(target_file).name

            # If names are the same, just show once, otherwise show both
            if source_name == target_name:
                self.conflicts_list.addItem(f"  • {source_name}")
            else:
                self.conflicts_list.addItem(f"  • {source_name} → {target_name}")

        conflicts_layout.addWidget(self.conflicts_list)
        layout.addWidget(conflicts_group)

        # Action selection
        actions_group = QGroupBox("Resolution:")
        actions_layout = QVBoxLayout(actions_group)

        self.action_group = QButtonGroup(self)

        self.overwrite_radio = QRadioButton("Overwrite existing files")
        self.overwrite_radio.setToolTip("Replace existing files with new ones")
        self.action_group.addButton(self.overwrite_radio, self.ACTION_OVERWRITE)
        actions_layout.addWidget(self.overwrite_radio)

        self.rename_radio = QRadioButton("Rename new files (add number suffix)")
        self.rename_radio.setToolTip("Keep both files by renaming the new file (e.g., 'File (1).mkv')")
        self.action_group.addButton(self.rename_radio, self.ACTION_RENAME)
        self.rename_radio.setChecked(True)  # Default to safer option
        actions_layout.addWidget(self.rename_radio)

        self.cancel_radio = QRadioButton("Cancel operation")
        self.cancel_radio.setToolTip("Don't move any files, cancel the entire operation")
        self.action_group.addButton(self.cancel_radio, self.ACTION_CANCEL)
        actions_layout.addWidget(self.cancel_radio)

        layout.addWidget(actions_group)

        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        ok_btn.setDefault(True)
        buttons_layout.addWidget(ok_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        layout.addLayout(buttons_layout)

    def get_selected_action(self) -> int:
        """Get the selected action

        Returns:
            ACTION_OVERWRITE, ACTION_RENAME, or ACTION_CANCEL
        """
        return self.action_group.checkedId()

    def exec_(self) -> int:
        """Execute the dialog and return the selected action

        Returns:
            ACTION_OVERWRITE, ACTION_RENAME, or ACTION_CANCEL
        """
        result = super().exec_()

        if result == QDialog.Accepted:
            self.selected_action = self.get_selected_action()
        else:
            self.selected_action = self.ACTION_CANCEL

        return self.selected_action
