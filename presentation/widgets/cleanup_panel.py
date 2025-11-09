"""Cleanup panel widget"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QCheckBox, QTextEdit, QPushButton, QGroupBox,
    QGridLayout, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from typing import Set, List, Callable, Optional

from config.constants import CLEANUP_EXTENSIONS


class CleanupPanel(QWidget):
    """Panel for configuring and running file cleanup"""

    # Signal emitted when cleanup is requested
    cleanup_requested = Signal(set, list)  # extensions: Set[str], custom_patterns: List[str]

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.checkboxes = {}
        self.custom_patterns = []

        self._build_ui()

    def _build_ui(self):
        """Build the cleanup panel UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Common extensions group
        extensions_group = QGroupBox("File Extensions to Clean")
        extensions_layout = QGridLayout(extensions_group)

        # Define common extension categories
        extension_categories = {
            "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp"],
            "Text Files": [".txt", ".nfo", ".md"],
            "HTML/Web": [".html", ".htm", ".xml"],
            "Documents": [".pdf", ".docx", ".doc"],
            "Subtitles": [".srt", ".sub", ".ssa", ".ass"],
            "Audio": [".mp3", ".aac", ".flac"],
            "Data Files": [".json", ".yml", ".yaml", ".torrent"],
        }

        # Create checkboxes in a grid layout (2 columns)
        row = 0
        col = 0
        for category, extensions in extension_categories.items():
            # Category checkbox (selects all in category)
            category_cb = QCheckBox(f"{category} ({', '.join(extensions)})")
            category_cb.setChecked(False)  # Default unchecked

            # Store reference
            self.checkboxes[category] = {
                "checkbox": category_cb,
                "extensions": extensions
            }

            extensions_layout.addWidget(category_cb, row, col)

            col += 1
            if col > 1:  # 2 columns
                col = 0
                row += 1

        layout.addWidget(extensions_group)

        # Custom patterns group
        custom_group = QGroupBox("Custom Extensions (comma-separated)")
        custom_layout = QVBoxLayout(custom_group)

        # Instructions
        instructions = QLabel("Enter custom extensions or regex patterns (e.g., .log, .bak, .tmp)")
        instructions.setStyleSheet("color: #888; font-size: 10px;")
        custom_layout.addWidget(instructions)

        # Text entry (3-4 lines)
        self.custom_entry = QTextEdit()
        self.custom_entry.setMaximumHeight(80)
        self.custom_entry.setPlaceholderText(".log, .bak, .tmp, *.sample.*")
        custom_layout.addWidget(self.custom_entry)

        layout.addWidget(custom_group)

        # Buttons
        button_layout = QHBoxLayout()

        # Select All / Deselect All
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self._select_all)
        button_layout.addWidget(select_all_btn)

        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.clicked.connect(self._deselect_all)
        button_layout.addWidget(deselect_all_btn)

        button_layout.addStretch()

        # Run cleanup button
        self.cleanup_btn = QPushButton("Run Cleanup")
        self.cleanup_btn.setStyleSheet("background-color: #d9534f; color: white; font-weight: bold; padding: 8px;")
        self.cleanup_btn.clicked.connect(self._run_cleanup)
        button_layout.addWidget(self.cleanup_btn)

        layout.addLayout(button_layout)

        layout.addStretch()

    def _select_all(self):
        """Select all extension checkboxes"""
        for category_data in self.checkboxes.values():
            category_data["checkbox"].setChecked(True)

    def _deselect_all(self):
        """Deselect all extension checkboxes"""
        for category_data in self.checkboxes.values():
            category_data["checkbox"].setChecked(False)

    def _run_cleanup(self):
        """Gather selected extensions and emit cleanup signal"""
        # Collect selected extensions
        selected_extensions = set()

        for category_data in self.checkboxes.values():
            if category_data["checkbox"].isChecked():
                selected_extensions.update(category_data["extensions"])

        # Parse custom extensions from text entry
        custom_text = self.custom_entry.toPlainText().strip()
        if custom_text:
            # Split by comma and clean up
            custom_exts = [ext.strip() for ext in custom_text.split(',') if ext.strip()]

            # Add leading dot if missing
            for ext in custom_exts:
                if not ext.startswith('.'):
                    ext = '.' + ext
                selected_extensions.add(ext)

        # Check if anything is selected
        if not selected_extensions:
            QMessageBox.warning(
                self,
                "No Extensions Selected",
                "Please select at least one file extension or enter custom extensions."
            )
            return

        # Emit signal with selected extensions
        self.cleanup_requested.emit(selected_extensions, [])

    def get_selected_extensions(self) -> Set[str]:
        """Get currently selected extensions

        Returns:
            Set of selected extensions
        """
        selected_extensions = set()

        for category_data in self.checkboxes.values():
            if category_data["checkbox"].isChecked():
                selected_extensions.update(category_data["extensions"])

        # Add custom extensions
        custom_text = self.custom_entry.toPlainText().strip()
        if custom_text:
            custom_exts = [ext.strip() for ext in custom_text.split(',') if ext.strip()]
            for ext in custom_exts:
                if not ext.startswith('.'):
                    ext = '.' + ext
                selected_extensions.add(ext)

        return selected_extensions

    def set_custom_extensions(self, extensions: str):
        """Set custom extensions text

        Args:
            extensions: Comma-separated extensions
        """
        self.custom_entry.setPlainText(extensions)

    def update_button_text(self, text: str):
        """Update cleanup button text

        Args:
            text: New button text
        """
        self.cleanup_btn.setText(text)

    def load_settings(self, cleanup_states: dict):
        """Load cleanup settings from saved state

        Args:
            cleanup_states: Dictionary with 'selected' list and 'custom_exts_str'
        """
        # Get selected extensions list
        selected_exts = set(cleanup_states.get("selected", []))

        # Check appropriate category checkboxes based on selected extensions
        for category, category_data in self.checkboxes.items():
            extensions = category_data["extensions"]
            checkbox = category_data["checkbox"]

            # Check if ANY extension in this category is in selected list
            # (More forgiving when new extensions are added to categories)
            if any(ext in selected_exts for ext in extensions):
                checkbox.setChecked(True)
            else:
                checkbox.setChecked(False)

        # Load custom extensions
        custom_exts_str = cleanup_states.get("custom_exts_str", "")
        if custom_exts_str:
            self.custom_entry.setPlainText(custom_exts_str)

    def save_settings(self) -> dict:
        """Save current cleanup settings to dictionary

        Returns:
            Dictionary with 'selected' list and 'custom_exts_str'
        """
        # Collect selected extensions
        selected_extensions = []

        for category_data in self.checkboxes.values():
            if category_data["checkbox"].isChecked():
                selected_extensions.extend(category_data["extensions"])

        # Get custom extensions text
        custom_exts_str = self.custom_entry.toPlainText().strip()

        return {
            "selected": selected_extensions,
            "custom_exts_str": custom_exts_str
        }
