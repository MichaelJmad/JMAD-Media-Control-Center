"""Episode renumber dialog for handling split seasons"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QSpinBox, QGroupBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from typing import List, Dict, Tuple, Optional
from pathlib import Path


class EpisodeRenumberDialog(QDialog):
    """Dialog for renumbering episodes in split seasons

    Allows user to select a group of files and renumber them sequentially.
    Useful for combining split seasons (Part 1 and Part 2) where both start at episode 1.

    Workflow:
    1. Show all files from selected folders/files
    2. User selects which files to renumber (Group B) using shift-click, drag, etc.
    3. Unselected files (Group A) keep their episode numbers
    4. Selected files (Group B) get renumbered starting from max(Group A) + 1
    5. Files are returned with new episode numbers to be moved to target season
    """

    def __init__(self, parent, files: List[Tuple[str, str]], episode_parser, media_title: str = ""):
        """Initialize episode renumber dialog

        Args:
            parent: Parent window
            files: List of (original_path, filename) tuples
            episode_parser: EpisodeParser instance for detecting episodes
            media_title: Optional media title for preview
        """
        super().__init__(parent)
        self.files = files
        self.episode_parser = episode_parser
        self.media_title = media_title

        # Parse episode numbers for all files
        self.file_episodes = {}  # original_path -> detected episode number
        for original_path, filename in files:
            ep_num = episode_parser.parse_episode_only(original_path)
            if ep_num is None:
                ep_num = episode_parser.parse_episode_only(filename)
            self.file_episodes[original_path] = ep_num if ep_num is not None else 0

        # Sort files by detected episode number
        self.files = sorted(self.files, key=lambda x: self.file_episodes.get(x[0], 0))

        self.setWindowTitle("Renumber Episodes (Split Season Tool)")
        self.setModal(True)
        self.resize(900, 600)

        self._build_ui()
        self._update_preview()

    def _build_ui(self):
        """Build the user interface"""
        layout = QVBoxLayout(self)

        # Instructions
        instructions = QLabel(
            "Select files to renumber (Group B) using click, Shift+click, Ctrl+click, or drag.\n"
            "Unselected files (Group A) keep their episode numbers.\n"
            "Group B will be renumbered starting from the last episode of Group A + 1."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # File selection table
        table_group = QGroupBox("Files (Select rows for Group B)")
        table_layout = QVBoxLayout(table_group)

        self.file_table = QTableWidget()
        self.file_table.setColumnCount(3)
        self.file_table.setHorizontalHeaderLabels(["Filename", "Current Ep", "New Ep"])

        # Enable extended selection (shift-click, ctrl-click, drag)
        self.file_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.file_table.setSelectionMode(QTableWidget.ExtendedSelection)

        # Set column widths
        header = self.file_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)

        # Populate table
        self.file_table.setRowCount(len(self.files))
        for row, (original_path, filename) in enumerate(self.files):
            # Store original path in first column item
            filename_item = QTableWidgetItem(filename)
            filename_item.setFlags(filename_item.flags() & ~Qt.ItemIsEditable)
            filename_item.setData(Qt.UserRole, original_path)  # Store original path
            self.file_table.setItem(row, 0, filename_item)

            # Current episode
            current_ep = self.file_episodes.get(original_path, 0)
            current_ep_item = QTableWidgetItem(str(current_ep) if current_ep > 0 else "Unknown")
            current_ep_item.setFlags(current_ep_item.flags() & ~Qt.ItemIsEditable)
            self.file_table.setItem(row, 1, current_ep_item)

            # New episode (will be calculated)
            new_ep_item = QTableWidgetItem("")
            new_ep_item.setFlags(new_ep_item.flags() & ~Qt.ItemIsEditable)
            self.file_table.setItem(row, 2, new_ep_item)

        # Connect selection changed signal
        self.file_table.itemSelectionChanged.connect(self._on_selection_changed)

        table_layout.addWidget(self.file_table)
        layout.addWidget(table_group)

        # Season selection
        season_group = QGroupBox("Target Season")
        season_layout = QHBoxLayout(season_group)

        season_label = QLabel("Move to Season:")
        season_layout.addWidget(season_label)

        self.season_spin = QSpinBox()
        self.season_spin.setMinimum(0)
        self.season_spin.setMaximum(100)
        self.season_spin.setValue(1)
        season_layout.addWidget(self.season_spin)

        season_layout.addStretch()
        layout.addWidget(season_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        self.execute_btn = QPushButton("Execute Renumber && Move")
        self.execute_btn.clicked.connect(self.accept)
        self.execute_btn.setDefault(True)
        button_layout.addWidget(self.execute_btn)

        layout.addLayout(button_layout)

    def _on_selection_changed(self):
        """Handle selection change - recalculate episode numbers"""
        self._update_preview()

    def _update_preview(self):
        """Update the 'New Ep' column based on current selection"""
        # Get selected rows
        selected_rows = set(index.row() for index in self.file_table.selectedIndexes())

        # Collect Group A (unselected) and Group B (selected)
        group_a = []
        group_b = []

        for row in range(self.file_table.rowCount()):
            filename_item = self.file_table.item(row, 0)
            original_path = filename_item.data(Qt.UserRole)
            current_ep = self.file_episodes.get(original_path, 0)

            is_selected = row in selected_rows

            if is_selected:
                group_b.append((row, original_path, current_ep))
            else:
                group_a.append((row, original_path, current_ep))

        # Calculate starting episode for Group B
        if group_a:
            max_group_a_ep = max(ep for _, _, ep in group_a)
            group_b_start = max_group_a_ep + 1
        else:
            group_b_start = 1

        # Update 'New Ep' column
        for row, original_path, current_ep in group_a:
            # Group A keeps original episode numbers
            new_ep_item = self.file_table.item(row, 2)
            new_ep_item.setText(str(current_ep) if current_ep > 0 else "Unknown")
            new_ep_item.setForeground(QColor(255, 255, 255))  # White

        for idx, (row, original_path, current_ep) in enumerate(group_b):
            # Group B gets renumbered starting from group_b_start
            new_ep = group_b_start + idx
            new_ep_item = self.file_table.item(row, 2)
            new_ep_item.setText(str(new_ep))
            new_ep_item.setForeground(QColor(100, 255, 100))  # Green to indicate change

    def get_renumber_info(self) -> Tuple[int, Dict[str, int]]:
        """Get the renumbering information

        Returns:
            Tuple of (season_num, file_renumber_map)
            where file_renumber_map is original_path -> new_episode_number
        """
        season_num = self.season_spin.value()
        file_renumber_map = {}

        for row in range(self.file_table.rowCount()):
            filename_item = self.file_table.item(row, 0)
            original_path = filename_item.data(Qt.UserRole)

            new_ep_item = self.file_table.item(row, 2)
            new_ep_text = new_ep_item.text()

            if new_ep_text and new_ep_text != "Unknown":
                try:
                    new_ep = int(new_ep_text)
                    file_renumber_map[original_path] = new_ep
                except ValueError:
                    pass

        return season_num, file_renumber_map
