"""Settings panel widget"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QGroupBox, QFormLayout,
    QFileDialog, QListWidget, QListWidgetItem, QMenu, QCheckBox
)
from PySide6.QtCore import Signal, Qt
from typing import Optional

from config.settings import Settings


class SettingsPanel(QWidget):
    """Panel for configuring application settings"""

    # Signal emitted when any setting changes
    settings_changed = Signal()

    # Available placeholders for patterns
    SERIES_PLACEHOLDERS = {
        "{original}": "Original series name",
        "{clean}": "Cleaned series name (no tags)",
    }

    EPISODE_PLACEHOLDERS = {
        "{series}": "Series name",
        "{season:02d}": "Season number (2 digits)",
        "{episode:02d}": "Episode number (2 digits)",
        "{title}": "Episode title",
    }

    MOVIE_PLACEHOLDERS = {
        "{series}": "Movie title",
        "{year}": "Release year",
    }

    def __init__(self, settings: Settings, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.settings = settings
        self.custom_directories = {}  # Map of directory names to paths
        self._build_ui()
        self._load_settings()

    def _build_ui(self):
        """Build the settings panel UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("Settings")
        title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        layout.addWidget(title)

        # Directories group
        directories_group = QGroupBox("Directories")
        directories_layout = QVBoxLayout(directories_group)

        # Mandatory directories section
        mandatory_label = QLabel("Required Directories:")
        mandatory_label.setStyleSheet("font-weight: bold;")
        directories_layout.addWidget(mandatory_label)

        # Staging directory
        staging_layout = QHBoxLayout()
        staging_layout.addWidget(QLabel("Staging:"))
        self.staging_edit = QLineEdit()
        self.staging_edit.textChanged.connect(self._on_setting_changed)
        staging_layout.addWidget(self.staging_edit)
        staging_btn = QPushButton("Browse...")
        staging_btn.clicked.connect(lambda: self._browse_directory(self.staging_edit))
        staging_layout.addWidget(staging_btn)
        directories_layout.addLayout(staging_layout)

        # Trash directory
        trash_layout = QHBoxLayout()
        trash_layout.addWidget(QLabel("Trash:"))
        self.trash_edit = QLineEdit()
        self.trash_edit.textChanged.connect(self._on_setting_changed)
        trash_layout.addWidget(self.trash_edit)
        trash_btn = QPushButton("Browse...")
        trash_btn.clicked.connect(lambda: self._browse_directory(self.trash_edit))
        trash_layout.addWidget(trash_btn)
        directories_layout.addLayout(trash_layout)

        # Optional directories section
        optional_label = QLabel("Library Directories (Optional):")
        optional_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        directories_layout.addWidget(optional_label)

        # Directory list
        self.directory_list = QListWidget()
        self.directory_list.setMaximumHeight(150)
        directories_layout.addWidget(self.directory_list)

        # Add/Remove buttons
        dir_buttons = QHBoxLayout()
        add_dir_btn = QPushButton("Add Library Directory")
        add_dir_btn.clicked.connect(self._add_directory)
        dir_buttons.addWidget(add_dir_btn)

        remove_dir_btn = QPushButton("Remove Selected")
        remove_dir_btn.clicked.connect(self._remove_directory)
        dir_buttons.addWidget(remove_dir_btn)
        dir_buttons.addStretch()
        directories_layout.addLayout(dir_buttons)

        layout.addWidget(directories_group)

        # Naming patterns group
        patterns_group = QGroupBox("Naming Patterns")
        patterns_layout = QVBoxLayout(patterns_group)

        # Series pattern
        patterns_layout.addWidget(QLabel("Series Folder Pattern:"))
        series_pattern_layout = QHBoxLayout()
        self.series_pattern_edit = QLineEdit()
        self.series_pattern_edit.textChanged.connect(self._on_setting_changed)
        self.series_pattern_edit.textChanged.connect(lambda: self._update_preview("series"))
        series_pattern_layout.addWidget(self.series_pattern_edit)

        series_placeholders_btn = QPushButton("Insert Placeholder ▼")
        series_placeholders_btn.clicked.connect(lambda: self._show_placeholder_menu(
            self.series_pattern_edit, self.SERIES_PLACEHOLDERS
        ))
        series_pattern_layout.addWidget(series_placeholders_btn)
        patterns_layout.addLayout(series_pattern_layout)

        self.series_preview = QLabel("Preview: My Series Name")
        self.series_preview.setStyleSheet("color: #888; font-size: 10px; padding-left: 5px;")
        patterns_layout.addWidget(self.series_preview)

        # Episode pattern
        patterns_layout.addWidget(QLabel("Episode Pattern:"))
        episode_pattern_layout = QHBoxLayout()
        self.episode_pattern_edit = QLineEdit()
        self.episode_pattern_edit.textChanged.connect(self._on_setting_changed)
        self.episode_pattern_edit.textChanged.connect(lambda: self._update_preview("episode"))
        episode_pattern_layout.addWidget(self.episode_pattern_edit)

        episode_placeholders_btn = QPushButton("Insert Placeholder ▼")
        episode_placeholders_btn.clicked.connect(lambda: self._show_placeholder_menu(
            self.episode_pattern_edit, self.EPISODE_PLACEHOLDERS
        ))
        episode_pattern_layout.addWidget(episode_placeholders_btn)
        patterns_layout.addLayout(episode_pattern_layout)

        self.episode_preview = QLabel("Preview: Series Name - S01E05.mkv")
        self.episode_preview.setStyleSheet("color: #888; font-size: 10px; padding-left: 5px;")
        patterns_layout.addWidget(self.episode_preview)

        # Movie pattern
        patterns_layout.addWidget(QLabel("Movie Pattern:"))
        movie_pattern_layout = QHBoxLayout()
        self.movie_pattern_edit = QLineEdit()
        self.movie_pattern_edit.textChanged.connect(self._on_setting_changed)
        self.movie_pattern_edit.textChanged.connect(lambda: self._update_preview("movie"))
        movie_pattern_layout.addWidget(self.movie_pattern_edit)

        movie_placeholders_btn = QPushButton("Insert Placeholder ▼")
        movie_placeholders_btn.clicked.connect(lambda: self._show_placeholder_menu(
            self.movie_pattern_edit, self.MOVIE_PLACEHOLDERS
        ))
        movie_pattern_layout.addWidget(movie_placeholders_btn)
        patterns_layout.addLayout(movie_pattern_layout)

        self.movie_preview = QLabel("Preview: Movie Title (2023).mkv")
        self.movie_preview.setStyleSheet("color: #888; font-size: 10px; padding-left: 5px;")
        patterns_layout.addWidget(self.movie_preview)

        layout.addWidget(patterns_group)

        # Organize preferences group
        organize_group = QGroupBox("Organize Preferences")
        organize_layout = QVBoxLayout(organize_group)

        # Specials folder naming checkbox
        self.season_00_checkbox = QCheckBox("Use 'Season 00' instead of 'Specials' for special episodes")
        self.season_00_checkbox.stateChanged.connect(self._on_setting_changed)
        organize_layout.addWidget(self.season_00_checkbox)

        # Confirmation dialog checkbox
        self.show_confirmation_checkbox = QCheckBox("Show confirmation dialog after organizing")
        self.show_confirmation_checkbox.stateChanged.connect(self._on_setting_changed)
        organize_layout.addWidget(self.show_confirmation_checkbox)

        # Organizational folder names
        folder_names_label = QLabel("Organizational Folder Names:")
        folder_names_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        organize_layout.addWidget(folder_names_label)

        # Anime folder name
        anime_folder_layout = QHBoxLayout()
        anime_folder_layout.addWidget(QLabel("Anime:"))
        self.anime_folder_edit = QLineEdit()
        self.anime_folder_edit.setPlaceholderText("Anime")
        self.anime_folder_edit.textChanged.connect(self._on_setting_changed)
        anime_folder_layout.addWidget(self.anime_folder_edit)
        organize_layout.addLayout(anime_folder_layout)

        # TV Shows folder name
        tv_shows_folder_layout = QHBoxLayout()
        tv_shows_folder_layout.addWidget(QLabel("TV Shows:"))
        self.tv_shows_folder_edit = QLineEdit()
        self.tv_shows_folder_edit.setPlaceholderText("TV Shows")
        self.tv_shows_folder_edit.textChanged.connect(self._on_setting_changed)
        tv_shows_folder_layout.addWidget(self.tv_shows_folder_edit)
        organize_layout.addLayout(tv_shows_folder_layout)

        # Movies folder name
        movies_folder_layout = QHBoxLayout()
        movies_folder_layout.addWidget(QLabel("Movies:"))
        self.movies_folder_edit = QLineEdit()
        self.movies_folder_edit.setPlaceholderText("Movies")
        self.movies_folder_edit.textChanged.connect(self._on_setting_changed)
        movies_folder_layout.addWidget(self.movies_folder_edit)
        organize_layout.addLayout(movies_folder_layout)

        layout.addWidget(organize_group)

        layout.addStretch()

        # Info label at bottom
        info = QLabel("Settings are automatically saved when changed")
        info.setStyleSheet("color: #888; font-style: italic; padding: 10px;")
        layout.addWidget(info)

    def _load_settings(self):
        """Load current settings into UI"""
        # Block signals while loading
        self.staging_edit.blockSignals(True)
        self.trash_edit.blockSignals(True)
        self.series_pattern_edit.blockSignals(True)
        self.episode_pattern_edit.blockSignals(True)
        self.movie_pattern_edit.blockSignals(True)
        self.season_00_checkbox.blockSignals(True)
        self.anime_folder_edit.blockSignals(True)
        self.tv_shows_folder_edit.blockSignals(True)
        self.movies_folder_edit.blockSignals(True)

        # Load mandatory directories
        self.staging_edit.setText(self.settings.directories.staging)
        self.trash_edit.setText(self.settings.directories.trash)

        # Load optional directories
        if self.settings.directories.tv_shows:
            self._add_directory_to_list("TV Shows", self.settings.directories.tv_shows)
        if self.settings.directories.movies:
            self._add_directory_to_list("Movies", self.settings.directories.movies)
        if self.settings.directories.anime:
            self._add_directory_to_list("Anime", self.settings.directories.anime)

        # Load patterns (without {ext})
        episode_pattern = self.settings.episode_pattern.replace("{ext}", "").strip()
        movie_pattern = self.settings.movie_pattern.replace("{ext}", "").strip()

        # Load or set default series pattern
        series_pattern = getattr(self.settings, 'series_pattern', '{clean}')

        self.series_pattern_edit.setText(series_pattern)
        self.episode_pattern_edit.setText(episode_pattern)
        self.movie_pattern_edit.setText(movie_pattern)

        # Load organize preferences
        self.season_00_checkbox.setChecked(self.settings.use_season_00_for_specials)
        self.show_confirmation_checkbox.setChecked(self.settings.show_organize_confirmation)
        self.anime_folder_edit.setText(self.settings.org_folder_anime)
        self.tv_shows_folder_edit.setText(self.settings.org_folder_tv_shows)
        self.movies_folder_edit.setText(self.settings.org_folder_movies)

        # Unblock signals
        self.staging_edit.blockSignals(False)
        self.trash_edit.blockSignals(False)
        self.series_pattern_edit.blockSignals(False)
        self.episode_pattern_edit.blockSignals(False)
        self.movie_pattern_edit.blockSignals(False)
        self.season_00_checkbox.blockSignals(False)
        self.anime_folder_edit.blockSignals(False)
        self.tv_shows_folder_edit.blockSignals(False)
        self.movies_folder_edit.blockSignals(False)

        # Update previews
        self._update_preview("series")
        self._update_preview("episode")
        self._update_preview("movie")

    def _add_directory_to_list(self, name: str, path: str):
        """Add directory to the list widget"""
        item = QListWidgetItem(f"{name}: {path}")
        item.setData(Qt.UserRole, name)  # Store name in item data
        self.directory_list.addItem(item)
        self.custom_directories[name] = path

    def _add_directory(self):
        """Add a new library directory"""
        from PySide6.QtWidgets import QInputDialog

        # Ask for directory name
        name, ok = QInputDialog.getText(
            self,
            "Add Library Directory",
            "Enter library name (e.g., 'Anime', 'TV Shows', 'Movies'):"
        )

        if not ok or not name:
            return

        # Browse for directory path
        path = QFileDialog.getExistingDirectory(self, f"Select {name} Library Directory")

        if path:
            self._add_directory_to_list(name, path)
            self._on_setting_changed()

    def _remove_directory(self):
        """Remove selected directory from list"""
        current = self.directory_list.currentItem()
        if current:
            name = current.data(Qt.UserRole)
            if name in self.custom_directories:
                del self.custom_directories[name]
            self.directory_list.takeItem(self.directory_list.row(current))
            self._on_setting_changed()

    def _show_placeholder_menu(self, line_edit: QLineEdit, placeholders: dict):
        """Show menu with available placeholders

        Args:
            line_edit: Line edit to insert placeholder into
            placeholders: Dictionary of placeholder -> description
        """
        menu = QMenu(self)

        for placeholder, description in placeholders.items():
            action = menu.addAction(f"{placeholder} - {description}")
            action.triggered.connect(lambda checked=False, p=placeholder: self._insert_placeholder(line_edit, p))

        # Show menu at button position
        menu.exec_(self.mapToGlobal(line_edit.geometry().bottomLeft()))

    def _insert_placeholder(self, line_edit: QLineEdit, placeholder: str):
        """Insert placeholder at cursor position

        Args:
            line_edit: Line edit to insert into
            placeholder: Placeholder text to insert
        """
        current_text = line_edit.text()
        cursor_pos = line_edit.cursorPosition()

        new_text = current_text[:cursor_pos] + placeholder + current_text[cursor_pos:]
        line_edit.setText(new_text)
        line_edit.setCursorPosition(cursor_pos + len(placeholder))

    def _update_preview(self, pattern_type: str):
        """Update preview label for pattern

        Args:
            pattern_type: Type of pattern ('series', 'episode', or 'movie')
        """
        if pattern_type == "series":
            pattern = self.series_pattern_edit.text()
            preview = pattern.replace("{original}", "My Series [1080p]").replace("{clean}", "My Series")
            self.series_preview.setText(f"Preview: {preview}")

        elif pattern_type == "episode":
            pattern = self.episode_pattern_edit.text()
            preview = (pattern
                      .replace("{series}", "Series Name")
                      .replace("{season:02d}", "01")
                      .replace("{episode:02d}", "05")
                      .replace("{title}", "Episode Title"))
            self.episode_preview.setText(f"Preview: {preview}.mkv")

        elif pattern_type == "movie":
            pattern = self.movie_pattern_edit.text()
            preview = (pattern
                      .replace("{series}", "Movie Title")
                      .replace("{year}", "2023"))
            self.movie_preview.setText(f"Preview: {preview}.mkv")

    def _on_setting_changed(self):
        """Called when any setting is changed"""
        # Update settings object
        self.settings.directories.staging = self.staging_edit.text()
        self.settings.directories.trash = self.trash_edit.text()

        # Update custom directories
        self.settings.directories.tv_shows = self.custom_directories.get("TV Shows", "")
        self.settings.directories.movies = self.custom_directories.get("Movies", "")
        self.settings.directories.anime = self.custom_directories.get("Anime", "")

        # Update patterns (add {ext} back automatically)
        self.settings.series_pattern = self.series_pattern_edit.text()
        self.settings.episode_pattern = self.episode_pattern_edit.text() + "{ext}"
        self.settings.movie_pattern = self.movie_pattern_edit.text() + "{ext}"

        # Update organize preferences
        self.settings.use_season_00_for_specials = self.season_00_checkbox.isChecked()
        self.settings.show_organize_confirmation = self.show_confirmation_checkbox.isChecked()
        self.settings.org_folder_anime = self.anime_folder_edit.text() or "Anime"
        self.settings.org_folder_tv_shows = self.tv_shows_folder_edit.text() or "TV Shows"
        self.settings.org_folder_movies = self.movies_folder_edit.text() or "Movies"

        # Emit signal to trigger auto-save
        self.settings_changed.emit()

    def _browse_directory(self, line_edit: QLineEdit):
        """Browse for a directory

        Args:
            line_edit: The line edit to update with selected directory
        """
        current = line_edit.text()
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Directory",
            current if current else ""
        )

        if directory:
            line_edit.setText(directory)

    def get_settings(self) -> Settings:
        """Get current settings

        Returns:
            Settings object with current values
        """
        return self.settings
