"""Organize dialog for moving media to library directories"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QComboBox, QGroupBox, QTextEdit
)
from PySide6.QtCore import Qt
from typing import List

from config.settings import Settings


class OrganizeDialog(QDialog):
    """Dialog for organizing media folders into libraries

    V1 behavior: Simple move operation to selected library directory
    """

    def __init__(self, parent, selected_folders: List[str], settings: Settings):
        """Initialize organize dialog

        Args:
            parent: Parent window
            selected_folders: List of folder names to organize
            settings: Application settings
        """
        super().__init__(parent)
        self.selected_folders = selected_folders
        self.settings = settings
        self.target_directory = None

        self.setWindowTitle("Organize Media")
        self.setModal(True)
        self.resize(600, 500)

        self._build_ui()

    def _build_ui(self):
        """Build dialog UI"""
        layout = QVBoxLayout(self)

        # Header
        header = QLabel(f"Organize {len(self.selected_folders)} folder(s)")
        header.setStyleSheet("font-size: 14pt; font-weight: bold; padding: 10px;")
        layout.addWidget(header)

        # Source section
        source_group = QGroupBox("Selected Folders")
        source_layout = QVBoxLayout(source_group)

        self.source_list = QListWidget()
        self.source_list.addItems(self.selected_folders)
        source_layout.addWidget(self.source_list)

        layout.addWidget(source_group)

        # Target section
        target_group = QGroupBox("Target Library")
        target_layout = QVBoxLayout(target_group)

        target_label = QLabel("Move to:")
        target_layout.addWidget(target_label)

        self.target_combo = QComboBox()
        target_layout.addWidget(self.target_combo)

        layout.addWidget(target_group)

        # Preview section
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)

        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(150)
        preview_layout.addWidget(self.preview_text)

        # Update preview button
        update_preview_btn = QPushButton("Update Preview")
        update_preview_btn.clicked.connect(self._update_preview)
        preview_layout.addWidget(update_preview_btn)

        layout.addWidget(preview_group)

        # Button row
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        self.execute_btn = QPushButton("Execute")
        self.execute_btn.clicked.connect(self._on_execute)
        self.execute_btn.setDefault(True)
        button_layout.addWidget(self.execute_btn)

        layout.addLayout(button_layout)

        # Populate target combo after execute_btn is created
        self._populate_target_combo()

        # Update preview initially
        self._update_preview()

    def _populate_target_combo(self):
        """Populate target library combo box"""
        # Add configured library directories
        libraries = []

        if self.settings.directories.tv_shows:
            libraries.append(("TV Shows", self.settings.directories.tv_shows))

        if self.settings.directories.movies:
            libraries.append(("Movies", self.settings.directories.movies))

        if self.settings.directories.anime:
            libraries.append(("Anime", self.settings.directories.anime))

        if not libraries:
            self.target_combo.addItem("No library directories configured", None)
            self.execute_btn.setEnabled(False)
        else:
            for name, path in libraries:
                self.target_combo.addItem(f"{name} ({path})", path)

    def _update_preview(self):
        """Update the preview of what will happen"""
        target_path = self.target_combo.currentData()

        if not target_path:
            self.preview_text.setPlainText("No target directory selected.")
            return

        preview_lines = [
            f"The following folders will be moved to: {target_path}\n",
            "-" * 60
        ]

        staging = self.settings.directories.staging

        for folder in self.selected_folders:
            source = f"{staging}/{folder}" if staging else folder
            dest = f"{target_path}/{folder}"
            preview_lines.append(f"FROM: {source}")
            preview_lines.append(f"TO:   {dest}")
            preview_lines.append("")

        self.preview_text.setPlainText("\n".join(preview_lines))

    def _on_execute(self):
        """Execute the organize operation"""
        self.target_directory = self.target_combo.currentData()

        if not self.target_directory:
            return

        # Accept dialog - parent will handle the actual move
        self.accept()

    def get_target_directory(self) -> str:
        """Get the selected target directory

        Returns:
            Path to target directory
        """
        return self.target_directory
