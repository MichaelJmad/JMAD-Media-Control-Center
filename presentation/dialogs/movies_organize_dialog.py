"""Movies Organize Dialog"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTableWidget, QTableWidgetItem, QPushButton, QMessageBox, QMenu
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from typing import List, Dict
from pathlib import Path
import re

from config.settings import Settings


class MoviesOrganizeDialog(QDialog):
    """Simple dialog for organizing movies - each movie keeps its folder-based title"""

    def __init__(self, parent, folder_paths: Dict[str, str], settings: Settings, media_type: str):
        """Initialize movies organize dialog

        Args:
            parent: Parent window
            folder_paths: Dict mapping folder names to full paths
            settings: Application settings
            media_type: Media type (movies)
        """
        super().__init__(parent)
        self.folder_paths = folder_paths
        self.settings = settings
        self.media_type = media_type

        # Collect all media files from selected folders
        # Each entry: {folder, file_path, inferred_title, new_name, is_included}
        self.media_file_entries = []
        self.non_media_files = []
        self._collect_files()

        self.setWindowTitle(f"Organize {media_type.replace('_', ' ').title()}")
        self.setModal(True)
        self.resize(700, 500)

        self._build_ui()
        self._update_preview()

    def _infer_movie_title(self, folder_name: str) -> str:
        """Infer movie title with year from folder name

        Keeps year in title if present, removes quality tags and release groups.
        Extracts year and formats as "Title (Year)".

        Args:
            folder_name: Folder name to infer from

        Returns:
            Inferred title with year (e.g., "Inception (2010)")
        """
        # First, try to extract year from original folder name (before removing brackets)
        # Look for year in brackets or parentheses: [2018], (2018)
        year = None
        year_in_brackets = re.search(r'[\(\[](\d{4})[\)\]]', folder_name)
        if year_in_brackets:
            year = year_in_brackets.group(1)

        # If we didn't find a year in brackets, look for it in the original title
        # Common formats: "Movie 2008", "Movie.2008", "Movie - 2008"
        if not year:
            year_match = re.search(r'[\(\s\.\-_](\d{4})[\)\s\.\-_]*$', folder_name)
            if year_match:
                year = year_match.group(1)

        # Start cleaning process - replace dots and underscores with spaces
        title_cleaned = re.sub(r'[._]', ' ', folder_name)

        # Remove release group tags (typically -GROUPNAME at the end)
        title_cleaned = re.sub(r'-[A-Z0-9]+$', '', title_cleaned, flags=re.I)

        # Remove quality/resolution tags
        title_cleaned = re.sub(r'\b\d{3,4}p\b', '', title_cleaned, flags=re.I)  # 720p, 1080p, 2160p
        title_cleaned = re.sub(r'\b4K\b', '', title_cleaned, flags=re.I)
        title_cleaned = re.sub(r'\bp\b', '', title_cleaned, flags=re.I)  # Standalone 'p'

        # Remove source tags
        title_cleaned = re.sub(r'\b(BluRay|BDRip|BD|WEB-DL|WEBRip|HDTV|DVDRip|BRRip)\b', '', title_cleaned, flags=re.I)

        # Remove codec/encoding tags
        title_cleaned = re.sub(r'\b(x264|x265|H\.?264|H\.?265|HEVC|AVC|10-?Bit|8-?Bit)\b', '', title_cleaned, flags=re.I)
        title_cleaned = re.sub(r'\b\d+\s*bits?\b', '', title_cleaned, flags=re.I)  # "10 bits", "8 bit"

        # Remove audio tags
        title_cleaned = re.sub(r'\b(Dual[\s-]?Audio|Multi[\s-]?Audio|AAC|FLAC|DTS|DD|AC3|TrueHD|Atmos)\b', '', title_cleaned, flags=re.I)
        title_cleaned = re.sub(r'\bFLAC\d+\.\d+\b', '', title_cleaned, flags=re.I)  # FLAC5.1, FLAC2.0

        # Remove subtitle tags
        title_cleaned = re.sub(r'\b(Subbed|Dubbed|Multi[\s-]?Sub)\b', '', title_cleaned, flags=re.I)

        # Remove release info
        title_cleaned = re.sub(r'\b(REPACK|PROPER|REAL|RETAIL|EXTENDED|UNRATED|DIRECTORS CUT)\b', '', title_cleaned, flags=re.I)

        # Remove content in brackets and parentheses (except year)
        title_cleaned = re.sub(r'\[.*?\]', '', title_cleaned)
        if year:
            # Remove parentheses content except the year
            title_cleaned = re.sub(r'\([^)]*?\)', lambda m: '' if year not in m.group(0) else m.group(0), title_cleaned)
        else:
            title_cleaned = re.sub(r'\(.*?\)', '', title_cleaned)

        # Remove the year from title if found (we'll add it back formatted later)
        if year:
            title_cleaned = re.sub(r'\b' + re.escape(year) + r'\b', '', title_cleaned)
            title_cleaned = re.sub(r'[\(\[]' + re.escape(year) + r'[\)\]]', '', title_cleaned)

        # Clean up extra spaces
        title_cleaned = re.sub(r'\s+', ' ', title_cleaned).strip()

        # Remove trailing dashes, underscores, or parentheses
        title_cleaned = re.sub(r'[\(\[\s\.\-_]+$', '', title_cleaned).strip()

        # If we found a year, format as "Title (Year)"
        if year and title_cleaned:
            return f"{title_cleaned} ({year})"

        return title_cleaned if title_cleaned else folder_name

    def _apply_movie_pattern(self, inferred_title: str, ext: str) -> str:
        """Apply the movie pattern from settings to generate filename

        Args:
            inferred_title: The inferred movie title (e.g., "Inception (2010)")
            ext: File extension (e.g., ".mkv")

        Returns:
            Formatted filename according to movie_pattern setting
        """
        # Extract year from title if present (e.g., "Movie (2020)" -> "2020")
        year_match = re.search(r'\((\d{4})\)', inferred_title)
        year = year_match.group(1) if year_match else ""

        # Get clean title without year for {series} placeholder
        # Remove year in parentheses and trim whitespace
        clean_title = re.sub(r'\s*\(\d{4}\)\s*', '', inferred_title).strip()

        # Start with the movie pattern from settings
        pattern = self.settings.movie_pattern

        # Replace placeholders
        pattern = pattern.replace("{series}", clean_title)
        pattern = pattern.replace("{year}", year)
        pattern = pattern.replace("{ext}", ext)

        return pattern


    def _collect_files(self):
        """Collect all files from selected folders

        Separates media files from non-media files for preview.
        Stores media files with metadata for multi-select support.
        """
        VIDEO_EXTENSIONS = {
            '.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm',
            '.m4v', '.mpg', '.mpeg', '.3gp', '.ogv', '.ts'
        }

        print(f"DEBUG _collect_files: folder_paths = {self.folder_paths}")

        for folder_name, full_path in self.folder_paths.items():
            print(f"DEBUG: Processing folder '{folder_name}' at path '{full_path}'")
            folder_path = Path(full_path)

            if not folder_path.exists():
                print(f"DEBUG: Path does not exist: {folder_path}")
                continue

            if not folder_path.is_dir():
                print(f"DEBUG: Path is not a directory: {folder_path}")
                continue

            folder_media_files = []
            folder_non_media_files = []

            # Recursively find all files
            try:
                file_count = 0
                for file_path in folder_path.rglob("*"):
                    if file_path.is_file():
                        file_count += 1
                        ext = file_path.suffix.lower()
                        print(f"DEBUG: Checking file '{file_path.name}' with extension '{ext}'")
                        if ext in VIDEO_EXTENSIONS:
                            folder_media_files.append(str(file_path))
                            print(f"DEBUG: ✓ Found media file: {file_path.name}")
                        else:
                            folder_non_media_files.append(str(file_path))
                            print(f"DEBUG: ✗ Non-media file: {file_path.name} (ext: {ext})")
                print(f"DEBUG: Total files found in folder: {file_count}, media: {len(folder_media_files)}, non-media: {len(folder_non_media_files)}")
            except (OSError, PermissionError) as e:
                print(f"DEBUG: Error accessing folder: {e}")
                pass

            # Only add folders that have media files
            if folder_media_files:
                # Infer title from folder name (same for all files in this folder)
                inferred_title = self._infer_movie_title(folder_name)
                print(f"DEBUG: Inferred title: '{inferred_title}'")

                # Add media files with metadata
                for file_path in folder_media_files:
                    ext = Path(file_path).suffix
                    new_name = self._apply_movie_pattern(inferred_title, ext)

                    self.media_file_entries.append({
                        "folder": folder_name,
                        "file_path": file_path,
                        "inferred_title": inferred_title,
                        "new_name": new_name,  # Formatted using movie_pattern from settings
                        "is_included": True  # Include by default
                    })

                # Add non-media files
                self.non_media_files.extend(folder_non_media_files)
            else:
                print(f"DEBUG: No media files found in folder '{folder_name}'")

        print(f"DEBUG _collect_files DONE: Total entries = {len(self.media_file_entries)}, non-media = {len(self.non_media_files)}")

    def _build_ui(self):
        """Build the user interface"""
        layout = QVBoxLayout(self)

        # Info label
        info_label = QLabel("Preview: Double-click on 'New Name' to edit")
        info_label.setStyleSheet("font-weight: bold; padding: 5px;")
        layout.addWidget(info_label)

        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(3)
        self.preview_table.setHorizontalHeaderLabels(["Original File", "→", "New Name / Action"])
        self.preview_table.setColumnWidth(0, 250)
        self.preview_table.setColumnWidth(1, 30)
        self.preview_table.setColumnWidth(2, 300)
        self.preview_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.preview_table.setSelectionMode(QTableWidget.SingleSelection)
        self.preview_table.itemChanged.connect(self._on_item_edited)

        # Enable context menu
        self.preview_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.preview_table.customContextMenuRequested.connect(self._show_context_menu)

        layout.addWidget(self.preview_table)

        # Buttons
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

    def _on_item_edited(self, item: QTableWidgetItem):
        """Handle when user edits a cell in the preview table

        Args:
            item: The table item that was edited
        """
        row = item.row()
        col = item.column()

        # Only allow editing column 2 (new name)
        if col != 2:
            return

        # Only allow editing media file rows (not non-media rows)
        if row >= len(self.media_file_entries):
            return

        # Update the new_name in our data structure
        new_name = item.text()
        self.media_file_entries[row]["new_name"] = new_name

    def _show_context_menu(self, position):
        """Show context menu for preview table

        Args:
            position: Position where right-click occurred
        """
        # Get the row that was right-clicked
        item = self.preview_table.itemAt(position)
        if not item:
            return

        row = item.row()

        # Only show menu for media file rows
        if row >= len(self.media_file_entries):
            return

        menu = QMenu(self)

        # Add "Remove from list" action
        remove_action = menu.addAction("Remove from organize")
        remove_action.triggered.connect(lambda: self._remove_from_list(row))

        # Show menu at cursor position
        menu.exec_(self.preview_table.viewport().mapToGlobal(position))

    def _remove_from_list(self, row: int):
        """Remove a file from the organize list

        Args:
            row: Row index to remove
        """
        if row < len(self.media_file_entries):
            self.media_file_entries[row]["is_included"] = False
            self._update_preview()

    def _update_preview(self):
        """Update preview table with media files and non-media files"""
        # Temporarily disconnect signal to avoid triggering edits during update
        self.preview_table.itemChanged.disconnect(self._on_item_edited)
        self.preview_table.setRowCount(0)

        # Add media files (only included ones)
        for entry in self.media_file_entries:
            if not entry["is_included"]:
                continue  # Skip excluded files

            original_name = Path(entry["file_path"]).name
            new_name = entry["new_name"]

            row = self.preview_table.rowCount()
            self.preview_table.insertRow(row)

            # Original file (read-only)
            orig_item = QTableWidgetItem(original_name)
            orig_item.setForeground(QColor(255, 255, 255))
            orig_item.setFlags(orig_item.flags() & ~Qt.ItemIsEditable)  # Make read-only
            self.preview_table.setItem(row, 0, orig_item)

            # Arrow (read-only)
            arrow_item = QTableWidgetItem("→")
            arrow_item.setTextAlignment(Qt.AlignCenter)
            arrow_item.setForeground(QColor(150, 150, 150))
            arrow_item.setFlags(arrow_item.flags() & ~Qt.ItemIsEditable)  # Make read-only
            self.preview_table.setItem(row, 1, arrow_item)

            # New name (editable)
            new_item = QTableWidgetItem(new_name)
            new_item.setForeground(QColor(150, 255, 150))
            new_item.setFlags(new_item.flags() | Qt.ItemIsEditable)  # Make editable
            self.preview_table.setItem(row, 2, new_item)

        # Add non-media files (will be removed) - all read-only
        for file_path in self.non_media_files:
            original_name = Path(file_path).name

            row = self.preview_table.rowCount()
            self.preview_table.insertRow(row)

            # Original file (read-only)
            orig_item = QTableWidgetItem(original_name)
            orig_item.setForeground(QColor(200, 200, 200))
            orig_item.setFlags(orig_item.flags() & ~Qt.ItemIsEditable)
            self.preview_table.setItem(row, 0, orig_item)

            # Arrow (read-only)
            arrow_item = QTableWidgetItem("→")
            arrow_item.setTextAlignment(Qt.AlignCenter)
            arrow_item.setForeground(QColor(150, 150, 150))
            arrow_item.setFlags(arrow_item.flags() & ~Qt.ItemIsEditable)
            self.preview_table.setItem(row, 1, arrow_item)

            # Will be removed (read-only)
            action_item = QTableWidgetItem("(will be removed)")
            action_item.setForeground(QColor(255, 100, 100))
            action_item.setFlags(action_item.flags() & ~Qt.ItemIsEditable)
            self.preview_table.setItem(row, 2, action_item)

        # Reconnect signal
        self.preview_table.itemChanged.connect(self._on_item_edited)

    def _on_execute(self):
        """Handle Execute button click

        Validates and closes dialog with Accept.
        """
        # Count included media files
        included_count = sum(1 for entry in self.media_file_entries if entry["is_included"])

        if included_count == 0:
            QMessageBox.warning(
                self,
                "No Media Files",
                "No media files to organize. All files have been removed from the list."
            )
            return

        # Accept the dialog - main window will execute operations
        self.accept()

    def get_organize_operations(self) -> Dict:
        """Get the organize operations to perform

        Returns:
            Dictionary with list of movies and their new names
        """
        operations = {
            "movies": [],  # List of movies with their operations
            "non_media_files": self.non_media_files
        }

        # Build operations for each included media file
        for entry in self.media_file_entries:
            if not entry["is_included"]:
                continue

            # Extract movie title from new_name (remove extension)
            movie_title = Path(entry["new_name"]).stem

            operations["movies"].append({
                "original_path": entry["file_path"],
                "movie_title": movie_title,  # Title for folder name
                "new_name": entry["new_name"]  # Full filename with extension
            })

        return operations
