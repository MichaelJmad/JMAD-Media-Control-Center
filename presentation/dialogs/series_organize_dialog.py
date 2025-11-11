"""Series organize dialog with 3-pane layout"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeWidget, QTreeWidgetItem, QSplitter, QWidget, QGroupBox,
    QLineEdit, QInputDialog, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from copy import deepcopy

from config.settings import Settings
from domain.value_objects.file_path import FilePath
from infrastructure.parsers.episode_parser import EpisodeParser


class SeriesOrganizeDialog(QDialog):
    """Dialog for organizing series media with 3-pane layout

    Layout:
    - Left: Source pane (selected folders/files)
    - Middle: Action buttons (Move to Series/Specials/Movies)
    - Right: Target pane (organized structure)
    - Bottom: Preview (original → new filename)
    """

    def __init__(self, parent, folder_paths: Dict[str, str], settings: Settings, media_type: str):
        """Initialize series organize dialog

        Args:
            parent: Parent window
            folder_paths: Dict mapping folder names to full paths
            settings: Application settings
            media_type: Media type (from MediaTypeDialog: "tv_series" or "anime")
        """
        super().__init__(parent)
        self.folder_paths = folder_paths
        self.settings = settings
        self.media_type = media_type

        # Data structures
        self.source_files = {}  # folder_name -> list of files
        self.target_structure = {}  # season_num -> list of files
        self.file_renames = {}  # original_path -> new_name

        # Parser for extracting episode numbers
        self.episode_parser = EpisodeParser()

        # Local undo/redo history
        self.history_stack = []  # List of (target_tree_state, file_renames_state)
        self.history_position = -1

        self.setWindowTitle(f"Organize {media_type.replace('_', ' ').title()}")
        self.setModal(True)
        self.resize(1200, 700)

        # Infer media title from selected folders
        self.media_title = self._infer_title_from_folders(list(folder_paths.keys()))

        self._build_ui()
        self._load_source_files()

    def _infer_title_from_folders(self, folders: List[str]) -> str:
        """Infer media title from folder names

        Strips common patterns like season numbers, quality tags, and year tags
        to extract the core series title.

        Args:
            folders: List of folder names

        Returns:
            Inferred title, or empty string if cannot infer
        """
        import re

        if not folders:
            return ""

        # Take the first folder as the base
        folder_name = folders[0]

        # First, replace dots and underscores with spaces (before pattern matching)
        title = re.sub(r'[._]', ' ', folder_name)

        # Remove release group tags (typically -GROUPNAME at the end)
        title = re.sub(r'-[A-Z0-9]+$', '', title, flags=re.I)

        # Remove everything after season indicator (including the season tag itself)
        # This handles: S01, S1, Season 1, Season 01
        title = re.sub(r'\s+S(?:eason)?\s*\d{1,2}.*$', '', title, flags=re.I)

        # Remove quality/resolution tags
        title = re.sub(r'\b\d{3,4}p\b', '', title, flags=re.I)  # 720p, 1080p, 2160p
        title = re.sub(r'\b4K\b', '', title, flags=re.I)
        title = re.sub(r'\bp\b', '', title, flags=re.I)  # Standalone 'p'

        # Remove source tags
        title = re.sub(r'\b(BluRay|BDRip|BD|WEB-DL|WEBRip|HDTV|DVDRip|BRRip)\b', '', title, flags=re.I)

        # Remove codec/encoding tags
        title = re.sub(r'\b(x264|x265|H\.?264|H\.?265|HEVC|AVC|10-?Bit|8-?Bit)\b', '', title, flags=re.I)
        title = re.sub(r'\b\d+\s*bits?\b', '', title, flags=re.I)  # "10 bits", "8 bit"

        # Remove audio tags
        title = re.sub(r'\b(Dual[\s-]?Audio|Multi[\s-]?Audio|AAC|FLAC|DTS|DD|AC3|TrueHD|Atmos)\b', '', title, flags=re.I)
        title = re.sub(r'\bFLAC\d+\.\d+\b', '', title, flags=re.I)  # FLAC5.1, FLAC2.0

        # Remove subtitle tags
        title = re.sub(r'\b(Subbed|Dubbed|Multi[\s-]?Sub)\b', '', title, flags=re.I)

        # Remove release info
        title = re.sub(r'\b(REPACK|PROPER|REAL|RETAIL)\b', '', title, flags=re.I)

        # Remove content in brackets and parentheses
        title = re.sub(r'\[.*?\]', '', title)
        title = re.sub(r'\(.*?\)', '', title)

        # Remove year tags (4 consecutive digits)
        title = re.sub(r'\b\d{4}\b', '', title)

        # Clean up extra spaces and trim
        title = re.sub(r'\s+', ' ', title).strip()

        # Remove trailing dashes or underscores
        title = re.sub(r'[_\-\s]+$', '', title).strip()

        return title if title else folder_name

    def _build_ui(self):
        """Build 3-pane dialog UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)  # Reduce margins

        # Title field row
        title_layout = QHBoxLayout()
        title_label = QLabel("Media Title:")
        title_label.setStyleSheet("font-weight: bold; padding: 5px;")
        title_layout.addWidget(title_label)

        self.title_field = QLineEdit()
        self.title_field.setText(self.media_title)
        self.title_field.setPlaceholderText("Enter series title (e.g., My Hero Academia)")
        self.title_field.textChanged.connect(self._on_title_changed)
        self.title_field.installEventFilter(self)  # Install event filter for hotkeys
        title_layout.addWidget(self.title_field)

        layout.addLayout(title_layout)

        # Compact header with undo/redo
        header_layout = QHBoxLayout()

        header = QLabel(f"Organizing {len(self.folder_paths)} folder(s)")
        header.setStyleSheet("padding: 5px;")  # Smaller padding, not bold (title is now above)
        header_layout.addWidget(header)

        header_layout.addStretch()

        # Undo/Redo buttons
        self.undo_btn = QPushButton("← Undo")
        self.undo_btn.clicked.connect(self._on_local_undo)
        self.undo_btn.setEnabled(False)
        header_layout.addWidget(self.undo_btn)

        self.redo_btn = QPushButton("Redo →")
        self.redo_btn.clicked.connect(self._on_local_redo)
        self.redo_btn.setEnabled(False)
        header_layout.addWidget(self.redo_btn)

        layout.addLayout(header_layout)

        # Main 3-pane splitter (horizontal)
        main_splitter = QSplitter(Qt.Horizontal)

        # LEFT PANE - Source
        source_widget = self._create_source_pane()
        main_splitter.addWidget(source_widget)

        # MIDDLE PANE - Actions
        action_widget = self._create_action_pane()
        main_splitter.addWidget(action_widget)

        # RIGHT PANE - Target
        target_widget = self._create_target_pane()
        main_splitter.addWidget(target_widget)

        # Set initial sizes (30% | 15% | 55%)
        main_splitter.setStretchFactor(0, 3)
        main_splitter.setStretchFactor(1, 1)
        main_splitter.setStretchFactor(2, 5)

        layout.addWidget(main_splitter)

        # BOTTOM - Preview section
        preview_widget = self._create_preview_pane()
        layout.addWidget(preview_widget)

        # Bottom buttons
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

    def _create_source_pane(self) -> QWidget:
        """Create left pane showing source folders/files

        Returns:
            Widget containing source tree
        """
        widget = QGroupBox("Source (Staging)")
        layout = QVBoxLayout(widget)

        self.source_tree = QTreeWidget()
        self.source_tree.setHeaderLabels(["Folder / File"])
        self.source_tree.setSelectionMode(QTreeWidget.ExtendedSelection)
        self.source_tree.itemSelectionChanged.connect(self._on_source_selection_changed)
        self.source_tree.installEventFilter(self)  # Install event filter for hotkeys

        # Enable mouse tracking for tooltips
        self.source_tree.setMouseTracking(True)
        self.source_tree.itemEntered.connect(self._on_source_item_hover)

        layout.addWidget(self.source_tree)

        return widget

    def _create_action_pane(self) -> QWidget:
        """Create middle pane with action buttons

        Returns:
            Widget containing action buttons
        """
        widget = QGroupBox("Actions")
        layout = QVBoxLayout(widget)

        layout.addStretch()

        # Move to Season button
        self.move_to_series_btn = QPushButton("Move to Season")
        self.move_to_series_btn.clicked.connect(self._on_move_to_series)
        self.move_to_series_btn.setEnabled(False)
        layout.addWidget(self.move_to_series_btn)

        # Move to Specials button
        self.move_to_specials_btn = QPushButton("Move to Specials")
        self.move_to_specials_btn.clicked.connect(self._on_move_to_specials)
        self.move_to_specials_btn.setEnabled(False)
        layout.addWidget(self.move_to_specials_btn)

        # Move to Movies button
        self.move_to_movies_btn = QPushButton("Move to Movies")
        self.move_to_movies_btn.clicked.connect(self._on_move_to_movies)
        self.move_to_movies_btn.setEnabled(False)
        layout.addWidget(self.move_to_movies_btn)

        # Move to... (custom) button
        self.move_to_custom_btn = QPushButton("Move to...")
        self.move_to_custom_btn.clicked.connect(self._on_move_to_custom)
        self.move_to_custom_btn.setEnabled(False)
        layout.addWidget(self.move_to_custom_btn)

        layout.addStretch()

        return widget

    def _create_target_pane(self) -> QWidget:
        """Create right pane showing target structure

        Returns:
            Widget containing target tree
        """
        widget = QGroupBox("Target (Organized Structure)")
        layout = QVBoxLayout(widget)

        self.target_tree = QTreeWidget()
        self.target_tree.setHeaderLabels(["Season / File"])
        self.target_tree.setSelectionMode(QTreeWidget.ExtendedSelection)
        self.target_tree.itemSelectionChanged.connect(self._on_target_selection_changed)
        self.target_tree.installEventFilter(self)  # Install event filter for hotkeys

        layout.addWidget(self.target_tree)

        return widget

    def _create_preview_pane(self) -> QWidget:
        """Create bottom preview pane showing all target files

        Returns:
            Widget containing preview table
        """
        widget = QGroupBox("Preview (All Target Files)")
        layout = QVBoxLayout(widget)

        # Table showing all files in target
        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(3)
        self.preview_table.setHorizontalHeaderLabels(["Season/Folder", "Original Path", "New Name (Editable)"])

        # Set column widths
        header = self.preview_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)

        # Connect cell changed signal
        self.preview_table.cellChanged.connect(self._on_preview_cell_changed)
        self.preview_table.installEventFilter(self)  # Install event filter for hotkeys

        layout.addWidget(self.preview_table)

        return widget

    def _load_source_files(self):
        """Load source files from staging directory into source tree"""
        for folder_name, full_path in self.folder_paths.items():
            folder_path = Path(full_path)

            if not folder_path.exists():
                continue

            # Create folder item in tree
            folder_item = QTreeWidgetItem([folder_name])
            folder_item.setData(0, Qt.UserRole, str(folder_path))  # Store full path
            folder_item.setData(0, Qt.UserRole + 1, "folder")  # Mark as folder

            # Find video files in folder
            video_exts = ['.mkv', '.mp4', '.avi', '.m4v', '.mov']
            files = []

            for file_path in folder_path.rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in video_exts:
                    files.append(file_path)
                    file_item = QTreeWidgetItem([file_path.name])
                    file_item.setData(0, Qt.UserRole, str(file_path))  # Store full path
                    file_item.setData(0, Qt.UserRole + 1, "file")  # Mark as file
                    folder_item.addChild(file_item)

            self.source_files[folder_name] = files
            self.source_tree.addTopLevelItem(folder_item)

        # Expand all folders
        self.source_tree.expandAll()

        # Auto-select the first top-level item for keyboard workflow
        if self.source_tree.topLevelItemCount() > 0:
            first_item = self.source_tree.topLevelItem(0)
            self.source_tree.setCurrentItem(first_item)
            first_item.setSelected(True)

        # Save initial state for undo/redo
        self._save_history_state()

    def _on_source_selection_changed(self):
        """Handle selection change in source tree"""
        selected = self.source_tree.selectedItems()
        has_selection = len(selected) > 0

        # Enable/disable action buttons based on selection
        self.move_to_series_btn.setEnabled(has_selection)
        self.move_to_specials_btn.setEnabled(has_selection)
        self.move_to_movies_btn.setEnabled(has_selection)
        self.move_to_custom_btn.setEnabled(has_selection)

    def _on_source_item_hover(self, item, column):
        """Show tooltip with full name when hovering over items with long names

        Args:
            item: QTreeWidgetItem being hovered over
            column: Column index
        """
        if item is None:
            return

        # Get the text from the item
        text = item.text(column)

        # Set tooltip to show full text (helpful for long filenames)
        item.setToolTip(column, text)

    def _on_target_selection_changed(self):
        """Handle selection change in target tree - updates preview table"""
        # Update the preview table to show all files in target
        self._update_preview_table()

    def _update_preview_table(self):
        """Update preview table with all files from target pane, grouped by season"""
        # Block signals while updating
        self.preview_table.blockSignals(True)

        # Clear table
        self.preview_table.setRowCount(0)

        # Iterate through target tree and add all files, grouped by season
        row = 0
        for i in range(self.target_tree.topLevelItemCount()):
            folder_item = self.target_tree.topLevelItem(i)
            folder_name = folder_item.text(0)

            # Add section header row for this season/folder
            if folder_item.childCount() > 0:
                self.preview_table.insertRow(row)

                # Create header spanning all columns
                header_item = QTableWidgetItem(f"▼ {folder_name}")
                header_item.setFlags(header_item.flags() & ~Qt.ItemIsEditable)
                header_item.setBackground(QColor(80, 80, 80))  # Dark gray background
                header_item.setForeground(QColor(255, 255, 255))  # White text
                font = header_item.font()
                font.setBold(True)
                header_item.setFont(font)
                self.preview_table.setItem(row, 0, header_item)

                # Empty cells for other columns
                for col in range(1, 3):
                    empty_item = QTableWidgetItem("")
                    empty_item.setFlags(empty_item.flags() & ~Qt.ItemIsEditable)
                    empty_item.setBackground(QColor(80, 80, 80))  # Dark gray background
                    self.preview_table.setItem(row, col, empty_item)

                row += 1

            # Add files under this season
            for j in range(folder_item.childCount()):
                file_item = folder_item.child(j)
                original_path = file_item.data(0, Qt.UserRole)
                new_name = file_item.text(0)

                # Add file row
                self.preview_table.insertRow(row)

                # Season/Folder column (read-only, indented)
                season_item = QTableWidgetItem(f"  {folder_name}")
                season_item.setFlags(season_item.flags() & ~Qt.ItemIsEditable)
                self.preview_table.setItem(row, 0, season_item)

                # Original path column (read-only) - show relative path
                # Calculate relative path from staging directory
                if self.settings.directories.staging:
                    try:
                        staging_path = Path(self.settings.directories.staging)
                        full_path = Path(original_path)
                        relative_path = full_path.relative_to(staging_path)
                        display_path = str(relative_path)
                    except (ValueError, AttributeError):
                        # Fallback to full path if relative calculation fails
                        display_path = original_path
                else:
                    display_path = original_path

                original_item = QTableWidgetItem(display_path)
                original_item.setFlags(original_item.flags() & ~Qt.ItemIsEditable)
                original_item.setToolTip(original_path)  # Full path on mouse-over
                self.preview_table.setItem(row, 1, original_item)

                # New name column (editable)
                new_name_item = QTableWidgetItem(new_name)
                new_name_item.setData(Qt.UserRole, original_path)  # Store original path for reference
                self.preview_table.setItem(row, 2, new_name_item)

                row += 1

        # Unblock signals
        self.preview_table.blockSignals(False)

    def _on_preview_cell_changed(self, row: int, column: int):
        """Handle cell edit in preview table

        Args:
            row: Row number
            column: Column number
        """
        if column != 2:  # Only handle edits to "New Name" column
            return

        # Get the new name and original path
        new_name_item = self.preview_table.item(row, 2)
        if not new_name_item:
            return

        new_name = new_name_item.text()
        original_path = new_name_item.data(Qt.UserRole)

        # Update the file_renames dictionary
        self.file_renames[original_path] = new_name

        # Update the corresponding item in target tree
        self._update_target_tree_item_name(original_path, new_name)

        # Recheck for conflicts after rename
        self._check_conflicts()

    def _update_target_tree_item_name(self, original_path: str, new_name: str):
        """Update item name in target tree

        Args:
            original_path: Original file path (used as identifier)
            new_name: New filename
        """
        # Search target tree for item with this original path
        for i in range(self.target_tree.topLevelItemCount()):
            folder_item = self.target_tree.topLevelItem(i)

            for j in range(folder_item.childCount()):
                file_item = folder_item.child(j)
                if file_item.data(0, Qt.UserRole) == original_path:
                    file_item.setText(0, new_name)
                    return

    def _on_move_to_series(self):
        """Handle Move to Series button click"""
        # Prompt for season number
        season_num, ok = QInputDialog.getInt(
            self,
            "Season Number",
            "Enter season number:",
            1, 1, 100, 1
        )

        if not ok:
            return

        self._move_selected_to_target(f"Season {season_num}", season_num)

    def _on_move_to_specials(self):
        """Handle Move to Specials button click"""
        # Use setting to determine folder name
        if self.settings.use_season_00_for_specials:
            folder_name = "Season 00"
        else:
            folder_name = "Specials"
        self._move_selected_to_target(folder_name, 0)

    def _on_move_to_movies(self):
        """Handle Move to Movies button click"""
        self._move_selected_to_target("Movies", -1)  # -1 indicates movies

    def _on_move_to_custom(self):
        """Handle Move to... (custom) button click"""
        # Prompt for custom destination
        dest_name, ok = QInputDialog.getText(
            self,
            "Custom Destination",
            "Enter custom destination name:"
        )

        if not ok or not dest_name:
            return

        self._move_selected_to_target(dest_name, -2)  # -2 indicates custom

    def _move_selected_to_target(self, target_name: str, season_num: int):
        """Move selected items from source to target

        Args:
            target_name: Display name for target folder (e.g., "Season 1")
            season_num: Season number (0 for specials, -1 for movies, -2 for custom)
        """
        selected = self.source_tree.selectedItems()

        if not selected:
            return

        # Find or create target folder in target tree
        target_folder = self._find_or_create_target_folder(target_name, season_num)

        # Collect files to move
        files_to_move = []

        for item in selected:
            item_type = item.data(0, Qt.UserRole + 1)

            if item_type == "folder":
                # Move all files in folder
                for i in range(item.childCount()):
                    child = item.child(i)
                    files_to_move.append(child)
            elif item_type == "file":
                files_to_move.append(item)

        # Move files to target
        for file_item in files_to_move:
            original_path = file_item.data(0, Qt.UserRole)
            original_name = file_item.text(0)

            # Generate new filename based on season (pass full path for better detection)
            new_name = self._generate_filename(original_path, original_name, season_num)

            # Create item in target tree
            target_file_item = QTreeWidgetItem([new_name])
            target_file_item.setData(0, Qt.UserRole, original_path)
            target_file_item.setData(0, Qt.UserRole + 1, "file")

            target_folder.addChild(target_file_item)

            # Store rename
            self.file_renames[original_path] = new_name

            # Remove from source tree
            parent = file_item.parent()
            if parent:
                parent.removeChild(file_item)

        # Clean up empty folders in source
        self._remove_empty_folders()

        # Expand target folder
        target_folder.setExpanded(True)

        # Save state AFTER move completes
        self._save_history_state()

        # Update preview table to show new files
        self._update_preview_table()

        # Update undo/redo buttons
        self._update_undo_redo_buttons()

        # Check for conflicts and update UI
        self._check_conflicts()

        # Auto-select next top-level item in source for keyboard workflow
        if self.source_tree.topLevelItemCount() > 0:
            # Try to select the first item (which will be the next unprocessed folder)
            next_item = self.source_tree.topLevelItem(0)
            self.source_tree.setCurrentItem(next_item)
            next_item.setSelected(True)
            self.source_tree.scrollToItem(next_item)

    def _find_or_create_target_folder(self, folder_name: str, season_num: int) -> QTreeWidgetItem:
        """Find or create target folder in target tree

        Args:
            folder_name: Name of folder (e.g., "Season 1")
            season_num: Season number for sorting

        Returns:
            QTreeWidgetItem for the folder
        """
        # Search for existing folder
        for i in range(self.target_tree.topLevelItemCount()):
            item = self.target_tree.topLevelItem(i)
            if item.text(0) == folder_name:
                return item

        # Create new folder
        folder_item = QTreeWidgetItem([folder_name])
        folder_item.setData(0, Qt.UserRole, season_num)  # Store season num for sorting
        folder_item.setData(0, Qt.UserRole + 1, "folder")

        self.target_tree.addTopLevelItem(folder_item)

        # Re-sort folders
        self.target_tree.sortItems(0, Qt.AscendingOrder)

        return folder_item

    def _infer_movie_title(self, filename: str) -> str:
        """Infer movie title with year from filename (same logic as movies dialog)

        Keeps year in title if present, removes quality tags and release groups.

        Args:
            filename: Filename to infer from

        Returns:
            Inferred title with year (e.g., "Blue Exorcist M01 (2011)")
        """
        import re

        # Remove extension
        title = Path(filename).stem

        # Remove quality tags: [1080p], [720p], [BD], [BluRay], etc.
        title = re.sub(r'\[.*?\]', '', title)

        # Remove common release group patterns
        title = re.sub(r'\[.*?Subs\]', '', title, flags=re.I)

        # Clean up extra spaces and trim
        title = re.sub(r'\s+', ' ', title).strip()

        # Remove trailing dashes or underscores
        title = re.sub(r'[_\-\s]+$', '', title).strip()

        return title if title else Path(filename).stem

    def _generate_filename(self, original_path: str, original_name: str, season_num: int) -> str:
        """Generate new filename based on season, retaining original episode number

        Args:
            original_path: Full path to original file (for better episode detection)
            original_name: Original filename only
            season_num: Season number (0 for specials, -1 for movies, -2 for custom)

        Returns:
            Generated filename with correct season prefix and original episode number
        """
        # Get extension
        ext = Path(original_name).suffix

        # Specials (season 0) - keep original name
        if season_num == 0:
            return original_name

        # Extract episode number using the improved parser
        # Try with full path first (to capture folder hints), then fall back to just filename
        ep_num = self.episode_parser.parse_episode_only(original_path)
        if ep_num is None:
            ep_num = self.episode_parser.parse_episode_only(original_name)

        # If still no episode found, try basic regex fallback
        if ep_num is None:
            import re
            match = re.search(r'(\d+)', original_name)
            ep_num = int(match.group(1)) if match else 1

        # Build filename with media title if available
        if self.media_title:
            title_prefix = f"{self.media_title} "
        else:
            title_prefix = ""

        if season_num > 0:
            # Series episode - format as "Title S##E##.ext"
            return f"{title_prefix}S{season_num:02d}E{ep_num:02d}{ext}"
        elif season_num == -1:
            # Movie - infer movie title from filename (like movies dialog)
            movie_title = self._infer_movie_title(original_name)
            return f"{movie_title}{ext}"
        else:
            # Custom - keep original name
            return original_name

    def _remove_empty_folders(self):
        """Remove empty folders from source tree"""
        items_to_remove = []

        for i in range(self.source_tree.topLevelItemCount()):
            item = self.source_tree.topLevelItem(i)
            if item.childCount() == 0:
                items_to_remove.append(item)

        for item in items_to_remove:
            self.source_tree.takeTopLevelItem(self.source_tree.indexOfTopLevelItem(item))

    def _save_history_state(self):
        """Save current state to history for undo/redo"""
        # Save state of BOTH source and target trees, plus file_renames
        state = (
            self._serialize_tree(self.source_tree),
            self._serialize_tree(self.target_tree),
            deepcopy(self.file_renames)
        )

        # If we're not at the end of history, truncate forward history
        if self.history_position < len(self.history_stack) - 1:
            self.history_stack = self.history_stack[:self.history_position + 1]

        # Add new state
        self.history_stack.append(state)
        self.history_position += 1

    def _serialize_tree(self, tree: QTreeWidget) -> List:
        """Serialize tree widget state

        Args:
            tree: Tree widget to serialize

        Returns:
            List representation of tree
        """
        result = []
        for i in range(tree.topLevelItemCount()):
            item = tree.topLevelItem(i)
            result.append(self._serialize_tree_item(item))
        return result

    def _serialize_tree_item(self, item: QTreeWidgetItem) -> Dict:
        """Serialize single tree item

        Args:
            item: Tree item to serialize

        Returns:
            Dict representation
        """
        data = {
            "text": item.text(0),
            "user_role": item.data(0, Qt.UserRole),
            "user_role_1": item.data(0, Qt.UserRole + 1),
            "children": []
        }

        for i in range(item.childCount()):
            data["children"].append(self._serialize_tree_item(item.child(i)))

        return data

    def _deserialize_tree(self, tree: QTreeWidget, data: List):
        """Deserialize tree state

        Args:
            tree: Tree widget to restore
            data: Serialized tree data
        """
        tree.clear()
        for item_data in data:
            item = self._deserialize_tree_item(item_data)
            tree.addTopLevelItem(item)

    def _deserialize_tree_item(self, data: Dict) -> QTreeWidgetItem:
        """Deserialize tree item

        Args:
            data: Serialized item data

        Returns:
            QTreeWidgetItem
        """
        item = QTreeWidgetItem([data["text"]])
        item.setData(0, Qt.UserRole, data["user_role"])
        item.setData(0, Qt.UserRole + 1, data["user_role_1"])

        for child_data in data["children"]:
            child = self._deserialize_tree_item(child_data)
            item.addChild(child)

        return item

    def _on_title_changed(self, text: str):
        """Handle title field changes - regenerate all filenames in preview

        Args:
            text: New title text
        """
        self.media_title = text.strip()

        # Regenerate all filenames in target tree and preview
        self._regenerate_all_filenames()

    def _regenerate_all_filenames(self):
        """Regenerate all filenames based on current media title"""
        # Iterate through target tree and regenerate all filenames
        for i in range(self.target_tree.topLevelItemCount()):
            folder_item = self.target_tree.topLevelItem(i)
            season_num = folder_item.data(0, Qt.UserRole)  # Season number stored in folder

            for j in range(folder_item.childCount()):
                file_item = folder_item.child(j)
                original_path = file_item.data(0, Qt.UserRole)
                original_name = Path(original_path).name

                # Regenerate filename with new title
                new_name = self._generate_filename(original_path, original_name, season_num)

                # Update tree item
                file_item.setText(0, new_name)

                # Update rename mapping
                self.file_renames[original_path] = new_name

        # Update preview table
        self._update_preview_table()

        # Check for conflicts
        self._check_conflicts()

    def _on_local_undo(self):
        """Handle local undo button click"""
        if self.history_position <= 0:
            return

        self.history_position -= 1
        state = self.history_stack[self.history_position]

        # Restore state of BOTH trees
        self._deserialize_tree(self.source_tree, state[0])
        self._deserialize_tree(self.target_tree, state[1])
        self.file_renames = deepcopy(state[2])

        # Update UI
        self._update_preview_table()
        self._update_undo_redo_buttons()
        self._check_conflicts()

    def _on_local_redo(self):
        """Handle local redo button click"""
        if self.history_position >= len(self.history_stack) - 1:
            return

        self.history_position += 1
        state = self.history_stack[self.history_position]

        # Restore state of BOTH trees
        self._deserialize_tree(self.source_tree, state[0])
        self._deserialize_tree(self.target_tree, state[1])
        self.file_renames = deepcopy(state[2])

        # Update UI
        self._update_preview_table()
        self._update_undo_redo_buttons()
        self._check_conflicts()

    def _update_undo_redo_buttons(self):
        """Update undo/redo button states"""
        self.undo_btn.setEnabled(self.history_position > 0)
        self.redo_btn.setEnabled(self.history_position < len(self.history_stack) - 1)

    def _check_conflicts(self):
        """Check for filename conflicts in target tree and preview table, update UI

        Scans all folders in target tree and preview table for duplicate filenames.
        Highlights conflicting files in red and disables execute button.
        """
        has_conflicts = False

        # Reset all colors in target tree first
        for i in range(self.target_tree.topLevelItemCount()):
            folder_item = self.target_tree.topLevelItem(i)
            for j in range(folder_item.childCount()):
                file_item = folder_item.child(j)
                file_item.setForeground(0, QColor(255, 255, 255))  # White (default)

        # Check each folder for conflicts in target tree
        for i in range(self.target_tree.topLevelItemCount()):
            folder_item = self.target_tree.topLevelItem(i)

            # Build a dict of filename -> list of items with that name
            filename_map = {}
            for j in range(folder_item.childCount()):
                file_item = folder_item.child(j)
                filename = file_item.text(0)

                if filename not in filename_map:
                    filename_map[filename] = []
                filename_map[filename].append(file_item)

            # Mark duplicates in red
            for filename, items in filename_map.items():
                if len(items) > 1:
                    # Multiple files with same name - conflict!
                    has_conflicts = True
                    for item in items:
                        item.setForeground(0, QColor(255, 100, 100))  # Red

        # Reset all colors in preview table (skip header rows)
        for row in range(self.preview_table.rowCount()):
            season_item = self.preview_table.item(row, 0)
            if season_item and season_item.text().startswith("  "):  # File row (indented)
                for col in range(3):
                    item = self.preview_table.item(row, col)
                    if item:
                        item.setForeground(QColor(255, 255, 255))  # White (default)

        # Check preview table for conflicts (group by season/folder)
        # Build a map of season -> (filename -> list of rows)
        season_conflicts = {}
        for row in range(self.preview_table.rowCount()):
            season_item = self.preview_table.item(row, 0)
            new_name_item = self.preview_table.item(row, 2)

            if not season_item or not new_name_item:
                continue

            # Skip header rows (not indented)
            if not season_item.text().startswith("  "):
                continue

            season = season_item.text().strip()
            new_name = new_name_item.text()

            if season not in season_conflicts:
                season_conflicts[season] = {}

            if new_name not in season_conflicts[season]:
                season_conflicts[season][new_name] = []

            season_conflicts[season][new_name].append(row)

        # Mark duplicate rows in preview table in red
        for season, filename_map in season_conflicts.items():
            for filename, rows in filename_map.items():
                if len(rows) > 1:
                    # Multiple files with same name in same season - conflict!
                    has_conflicts = True
                    for row in rows:
                        for col in range(3):
                            item = self.preview_table.item(row, col)
                            if item:
                                item.setForeground(QColor(255, 100, 100))  # Red

        # Enable/disable execute button based on conflicts
        self.execute_btn.setEnabled(not has_conflicts)

        # Update execute button tooltip
        if has_conflicts:
            self.execute_btn.setToolTip("Cannot execute: Duplicate filenames detected (shown in red)")
        else:
            self.execute_btn.setToolTip("Execute the organize operation")

    def _on_execute(self):
        """Handle Execute button click

        Validates that files have been organized, then closes dialog with Accept.
        The main window will execute the actual file operations.
        """
        # Check if there are items in target
        if self.target_tree.topLevelItemCount() == 0:
            QMessageBox.warning(
                self,
                "No Files Organized",
                "Please organize files in the target pane before executing."
            )
            return

        # Accept the dialog - main window will execute operations
        self.accept()

    def get_organize_operations(self) -> Dict:
        """Get the organize operations to perform

        Returns:
            Dictionary with organize operations
        """
        operations = {
            "seasons": {},
            "file_renames": self.file_renames
        }

        # Build season structure from target tree
        for i in range(self.target_tree.topLevelItemCount()):
            folder_item = self.target_tree.topLevelItem(i)
            folder_name = folder_item.text(0)
            season_num = folder_item.data(0, Qt.UserRole)

            files = []
            for j in range(folder_item.childCount()):
                file_item = folder_item.child(j)
                files.append({
                    "original_path": file_item.data(0, Qt.UserRole),
                    "new_name": file_item.text(0)
                })

            operations["seasons"][season_num] = {
                "folder_name": folder_name,
                "files": files
            }

        return operations

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts

        Supports customizable hotkeys from settings for:
        - Season assignment (1-20)
        - Move to Specials
        - Move to Movies
        - Rename, Delete, Undo, Redo, Select All, Execute
        """
        from PySide6.QtCore import Qt

        key = event.key()
        modifiers = event.modifiers()

        # Helper to check if a specific modifier is pressed
        # In PySide6, modifiers are under Qt.KeyboardModifier
        shift_pressed = bool(modifiers & Qt.KeyboardModifier.ShiftModifier)
        ctrl_pressed = bool(modifiers & Qt.KeyboardModifier.ControlModifier)
        alt_pressed = bool(modifiers & Qt.KeyboardModifier.AltModifier)

        # Handle number keys for season assignment (1-9, 0)
        # Map key codes to numbers
        key_to_number = {
            Qt.Key_0: 0,
            Qt.Key_1: 1,
            Qt.Key_2: 2,
            Qt.Key_3: 3,
            Qt.Key_4: 4,
            Qt.Key_5: 5,
            Qt.Key_6: 6,
            Qt.Key_7: 7,
            Qt.Key_8: 8,
            Qt.Key_9: 9,
        }

        if key in key_to_number and not alt_pressed:
            number = key_to_number[key]

            if ctrl_pressed and not shift_pressed:
                # Ctrl + number = seasons 11-20
                season_num = 10 + number if number > 0 else 20  # Ctrl+0 = 20
            elif not ctrl_pressed and not shift_pressed:
                # Plain number = seasons 1-10
                season_num = number if number > 0 else 10  # 0 = season 10
            else:
                # Ignore other modifier combinations
                return

            self._move_selected_to_target(f"Season {season_num}", season_num)
            event.accept()
            return

        # Handle letter keys for quick actions (case-insensitive)
        if not ctrl_pressed and not alt_pressed and not shift_pressed:
            if key == Qt.Key_S:
                self._on_move_to_specials()
                event.accept()
                return
            elif key == Qt.Key_M:
                self._on_move_to_movies()
                event.accept()
                return

        # Handle special keys
        if key == Qt.Key_F2 and not ctrl_pressed:
            self._on_edit_preview_item()
            event.accept()
            return
        elif key == Qt.Key_Delete:
            self._delete_from_target()
            event.accept()
            return
        elif key == Qt.Key_Z and ctrl_pressed:
            self._on_local_undo()
            event.accept()
            return
        elif key == Qt.Key_Y and ctrl_pressed:
            self._on_local_redo()
            event.accept()
            return
        elif key == Qt.Key_A and ctrl_pressed:
            self._select_all_source()
            event.accept()
            return
        elif key == Qt.Key_Return and ctrl_pressed:
            self._on_execute()
            event.accept()
            return

        # If no hotkey matched, don't accept - allow default behavior
        # Don't call super() here - let the event filter handle it
        event.ignore()

    def eventFilter(self, obj, event):
        """Event filter to capture keyboard events from child widgets

        This allows hotkeys to work even when child widgets have focus.

        Args:
            obj: Object that received the event
            event: The event

        Returns:
            True if event was handled, False otherwise
        """
        from PySide6.QtCore import QEvent

        if event.type() == QEvent.KeyPress:
            # Forward key events to dialog's keyPressEvent
            # But first check if we should handle it
            key = event.key()
            modifiers = event.modifiers()

            # Don't intercept typing in the title field for regular text
            if obj == self.title_field:
                # Only intercept special keys (like Ctrl+Z, Ctrl+Y, etc.)
                ctrl_pressed = bool(modifiers & Qt.KeyboardModifier.ControlModifier)

                # Allow normal typing in title field, only intercept Ctrl shortcuts
                if not ctrl_pressed:
                    return False

            # Try to handle the event with our keyPressEvent
            self.keyPressEvent(event)

            # If the event was accepted, prevent further processing
            if event.isAccepted():
                return True

        # Pass event to parent's event filter
        return super().eventFilter(obj, event)

    def _select_all_source(self):
        """Select all items in source tree"""
        self.source_tree.selectAll()

    def _delete_from_target(self):
        """Delete/remove selected items from target tree"""
        selected = self.target_tree.selectedItems()

        if not selected:
            return

        # Collect files to remove
        files_to_remove = []

        for item in selected:
            # Check if it's a file item (not a folder)
            if item.parent() is not None:
                files_to_remove.append(item)

        if not files_to_remove:
            return

        # Save state before removal for undo
        self._save_history_state()

        # Remove files from target and file_renames
        for file_item in files_to_remove:
            original_path = file_item.data(0, Qt.UserRole)

            # Remove from file_renames
            if original_path in self.file_renames:
                del self.file_renames[original_path]

            # Remove from target tree
            parent_folder = file_item.parent()
            parent_folder.removeChild(file_item)

            # If folder is now empty, remove it too
            if parent_folder.childCount() == 0:
                root = self.target_tree.invisibleRootItem()
                root.removeChild(parent_folder)

        # Update preview
        self._update_preview_table()
