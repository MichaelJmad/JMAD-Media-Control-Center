"""Hotkeys configuration panel widget"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QKeySequenceEdit, QMessageBox, QSizePolicy
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QKeySequence
from typing import Optional

from config.settings import Settings


class HotkeysPanel(QWidget):
    """Panel for configuring application hotkeys"""

    # Signal emitted when any hotkey changes
    settings_changed = Signal()

    # Human-readable descriptions for hotkey actions
    HOTKEY_DESCRIPTIONS = {
        # Season assignment (1-10)
        "season_1": "Move to Season 1",
        "season_2": "Move to Season 2",
        "season_3": "Move to Season 3",
        "season_4": "Move to Season 4",
        "season_5": "Move to Season 5",
        "season_6": "Move to Season 6",
        "season_7": "Move to Season 7",
        "season_8": "Move to Season 8",
        "season_9": "Move to Season 9",
        "season_10": "Move to Season 10",
        # Season assignment (11-20)
        "season_11": "Move to Season 11",
        "season_12": "Move to Season 12",
        "season_13": "Move to Season 13",
        "season_14": "Move to Season 14",
        "season_15": "Move to Season 15",
        "season_16": "Move to Season 16",
        "season_17": "Move to Season 17",
        "season_18": "Move to Season 18",
        "season_19": "Move to Season 19",
        "season_20": "Move to Season 20",
        # Quick actions (organize dialog)
        "move_to_specials": "Move to Specials",
        "move_to_movies": "Move to Movies",
        "rename_selected": "Rename Selected File",
        "delete_selected": "Delete/Remove Selected",
        "undo": "Undo Last Action",
        "redo": "Redo Last Action",
        "select_all": "Select All Files",
        "execute": "Execute/Apply Changes",
        # Media tree actions (main window)
        "open_anime_dialog": "Open Anime Organize Dialog",
        "open_movie_dialog": "Open Movie Organize Dialog",
        "open_tv_dialog": "Open TV Series Organize Dialog",
    }

    # Group hotkeys by category
    HOTKEY_CATEGORIES = {
        "Season Assignment (1-20)": [
            "season_1", "season_2", "season_3", "season_4", "season_5",
            "season_6", "season_7", "season_8", "season_9", "season_10",
            "season_11", "season_12", "season_13", "season_14", "season_15",
            "season_16", "season_17", "season_18", "season_19", "season_20"
        ],
        "Quick Actions (Organize Dialog)": [
            "move_to_specials", "move_to_movies", "rename_selected",
            "delete_selected", "undo", "redo", "select_all", "execute"
        ],
        "Media Tree Actions (Main Window)": [
            "open_anime_dialog", "open_movie_dialog", "open_tv_dialog"
        ]
    }

    def __init__(self, settings: Settings, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.settings = settings
        self._build_ui()
        self._load_settings()

    def _build_ui(self):
        """Build the hotkeys panel UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("Hotkey Configuration")
        title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        layout.addWidget(title)

        # Instructions
        instructions = QLabel(
            "Click on a hotkey field and press the desired key combination.\n"
            "Use Backspace to clear a hotkey assignment."
        )
        instructions.setStyleSheet("color: #666; padding: 5px;")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Create two-column layout: Season Assignments (left) and Actions (right)
        columns_layout = QHBoxLayout()

        # Left column: Season Assignments (1-20 combined)
        left_column = QVBoxLayout()

        season_group = self._create_category_group(
            "Season Assignment (1-20)",
            self.HOTKEY_CATEGORIES["Season Assignment (1-20)"]
        )
        left_column.addWidget(season_group, stretch=1)  # Give it stretch factor
        columns_layout.addLayout(left_column, stretch=1)

        # Right column: Quick Actions and Media Tree Actions
        right_column = QVBoxLayout()

        quick_actions_group = self._create_category_group(
            "Quick Actions (Organize Dialog)",
            self.HOTKEY_CATEGORIES["Quick Actions (Organize Dialog)"]
        )
        right_column.addWidget(quick_actions_group, stretch=1)  # Give it stretch factor

        media_tree_group = self._create_category_group(
            "Media Tree Actions (Main Window)",
            self.HOTKEY_CATEGORIES["Media Tree Actions (Main Window)"]
        )
        right_column.addWidget(media_tree_group, stretch=0)  # No stretch - keep compact

        columns_layout.addLayout(right_column, stretch=1)

        layout.addLayout(columns_layout, stretch=1)  # Allow columns to expand

        # Reset button
        reset_layout = QHBoxLayout()
        reset_layout.addStretch()

        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self._reset_to_defaults)
        reset_layout.addWidget(reset_btn)

        layout.addLayout(reset_layout)

        # Info label at bottom
        info = QLabel("Hotkeys are automatically saved when changed")
        info.setStyleSheet("color: #888; font-style: italic; padding: 10px;")
        layout.addWidget(info)

    def _create_category_group(self, category_name: str, action_keys: list) -> QGroupBox:
        """Create a group box for a category of hotkeys

        Args:
            category_name: Display name for the category
            action_keys: List of action keys in this category

        Returns:
            QGroupBox containing the hotkeys table
        """
        group = QGroupBox(category_name)
        # Allow group box to expand in both directions
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QVBoxLayout(group)

        # Create table for this category
        table = QTableWidget()
        # Allow table to expand in both directions
        table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Action", "Hotkey"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        table.verticalHeader().setVisible(False)
        table.setRowCount(len(action_keys))

        # Set row heights to stretch with the table
        table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Populate table
        for row, action_key in enumerate(action_keys):
            # Action description
            desc_item = QTableWidgetItem(self.HOTKEY_DESCRIPTIONS.get(action_key, action_key))
            desc_item.setFlags(desc_item.flags() & ~Qt.ItemIsEditable)
            table.setItem(row, 0, desc_item)

            # Hotkey editor
            hotkey_edit = QKeySequenceEdit()
            hotkey_edit.setProperty("action_key", action_key)
            hotkey_edit.keySequenceChanged.connect(self._on_hotkey_changed)
            table.setCellWidget(row, 1, hotkey_edit)

        layout.addWidget(table, stretch=1)  # Allow table to expand

        # Store reference for loading/resetting
        if not hasattr(self, 'hotkey_editors'):
            self.hotkey_editors = {}

        for row, action_key in enumerate(action_keys):
            editor = table.cellWidget(row, 1)
            self.hotkey_editors[action_key] = editor

        return group

    def _load_settings(self):
        """Load current hotkey settings into UI"""
        # Get default hotkeys for fallback
        default_hotkeys = Settings().hotkeys

        # Load each hotkey
        for action_key, editor in self.hotkey_editors.items():
            editor.blockSignals(True)

            # Get hotkey from settings or use default
            hotkey_str = self.settings.hotkeys.get(action_key, default_hotkeys.get(action_key, ""))

            if hotkey_str:
                # Convert string to QKeySequence
                key_sequence = QKeySequence(hotkey_str)
                editor.setKeySequence(key_sequence)

            editor.blockSignals(False)

    def _on_hotkey_changed(self):
        """Called when any hotkey is changed"""
        sender = self.sender()
        action_key = sender.property("action_key")
        key_sequence = sender.keySequence()

        # Convert to string
        hotkey_str = key_sequence.toString()

        # Check for conflicts
        if hotkey_str and self._check_conflict(action_key, hotkey_str):
            QMessageBox.warning(
                self,
                "Hotkey Conflict",
                f"The hotkey '{hotkey_str}' is already assigned to another action.\n"
                "Please choose a different key combination."
            )
            # Reload the original value
            sender.blockSignals(True)
            original = self.settings.hotkeys.get(action_key, "")
            sender.setKeySequence(QKeySequence(original))
            sender.blockSignals(False)
            return

        # Update settings
        if hotkey_str:
            self.settings.hotkeys[action_key] = hotkey_str
        else:
            # Remove if cleared
            if action_key in self.settings.hotkeys:
                del self.settings.hotkeys[action_key]

        # Emit signal to trigger auto-save
        self.settings_changed.emit()

    def _check_conflict(self, current_action: str, hotkey_str: str) -> bool:
        """Check if a hotkey conflicts with existing assignments

        Args:
            current_action: The action being edited
            hotkey_str: The hotkey string to check

        Returns:
            True if there's a conflict, False otherwise
        """
        for action_key, existing_hotkey in self.settings.hotkeys.items():
            if action_key != current_action and existing_hotkey == hotkey_str:
                return True
        return False

    def _reset_to_defaults(self):
        """Reset all hotkeys to default values"""
        reply = QMessageBox.question(
            self,
            "Reset Hotkeys",
            "Are you sure you want to reset all hotkeys to their default values?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Get default hotkeys
            default_settings = Settings()
            self.settings.hotkeys = default_settings.hotkeys.copy()

            # Reload UI
            self._load_settings()

            # Emit signal to trigger auto-save
            self.settings_changed.emit()

    def get_settings(self) -> Settings:
        """Get current settings

        Returns:
            Settings object with current values
        """
        return self.settings
