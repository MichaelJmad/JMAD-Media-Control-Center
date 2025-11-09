"""Media type selection dialog"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QButtonGroup, QRadioButton
)
from PySide6.QtCore import Qt


class MediaTypeDialog(QDialog):
    """Dialog for selecting media type before organizing

    First step in organize workflow - determines which organize dialog to show.
    """

    # Media type constants
    TV_SERIES = "tv_series"
    MOVIES = "movies"
    ANIME = "anime"

    def __init__(self, parent, folder_count: int):
        """Initialize media type selection dialog

        Args:
            parent: Parent window
            folder_count: Number of folders being organized
        """
        super().__init__(parent)
        self.selected_type = None

        self.setWindowTitle("Select Media Type")
        self.setModal(True)
        self.resize(400, 300)

        self._build_ui(folder_count)

    def _build_ui(self, folder_count: int):
        """Build dialog UI

        Args:
            folder_count: Number of folders being organized
        """
        layout = QVBoxLayout(self)

        # Header
        header = QLabel(f"Select media type for {folder_count} folder(s)")
        header.setStyleSheet("font-size: 14pt; font-weight: bold; padding: 10px;")
        layout.addWidget(header)

        # Instructions
        instructions = QLabel(
            "Choose the type of media you are organizing.\n"
            "This determines how files will be organized and named."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("padding: 10px; color: #666;")
        layout.addWidget(instructions)

        # Radio buttons
        self.button_group = QButtonGroup(self)

        self.tv_series_radio = QRadioButton("TV Series")
        self.tv_series_radio.setStyleSheet("font-size: 12pt; padding: 8px;")
        self.button_group.addButton(self.tv_series_radio)
        layout.addWidget(self.tv_series_radio)

        self.movies_radio = QRadioButton("Movies")
        self.movies_radio.setStyleSheet("font-size: 12pt; padding: 8px;")
        self.button_group.addButton(self.movies_radio)
        layout.addWidget(self.movies_radio)

        self.anime_radio = QRadioButton("Anime")
        self.anime_radio.setStyleSheet("font-size: 12pt; padding: 8px;")
        self.button_group.addButton(self.anime_radio)
        layout.addWidget(self.anime_radio)

        # Default to TV Series
        self.tv_series_radio.setChecked(True)

        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        next_btn = QPushButton("Next →")
        next_btn.clicked.connect(self._on_next)
        next_btn.setDefault(True)
        button_layout.addWidget(next_btn)

        layout.addLayout(button_layout)

    def _on_next(self):
        """Handle Next button click"""
        # Determine which type was selected
        if self.tv_series_radio.isChecked():
            self.selected_type = self.TV_SERIES
        elif self.movies_radio.isChecked():
            self.selected_type = self.MOVIES
        elif self.anime_radio.isChecked():
            self.selected_type = self.ANIME

        self.accept()

    def get_selected_type(self) -> str:
        """Get the selected media type

        Returns:
            Media type constant (TV_SERIES, MOVIES, ANIME) or None
        """
        return self.selected_type

    def should_use_series_dialog(self) -> bool:
        """Check if series organize dialog should be used

        Returns:
            True if TV_SERIES or ANIME selected
        """
        return self.selected_type in [self.TV_SERIES, self.ANIME]

    def should_use_movies_dialog(self) -> bool:
        """Check if movies organize dialog should be used

        Returns:
            True if MOVIES selected
        """
        return self.selected_type == self.MOVIES
