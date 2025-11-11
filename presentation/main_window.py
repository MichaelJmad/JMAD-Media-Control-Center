"""Main application window"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTreeWidget, QTreeWidgetItem, QMessageBox,
    QSplitter, QTextEdit, QLabel, QTabWidget, QMenu, QProgressBar,
    QLineEdit, QComboBox, QCheckBox
)
from PySide6.QtCore import Qt, QFileSystemWatcher, QTimer, QThread, Signal
from PySide6.QtGui import QColor, QShortcut, QKeySequence
from typing import Optional, List, Dict
from pathlib import Path
import os

from config.settings import Settings
from infrastructure.repositories.settings_repository import SettingsRepository
from infrastructure.services.file_system_service import FileSystemService
from infrastructure.services.history_service import HistoryService
from infrastructure.services.undo_redo_manager import UndoRedoManager
from infrastructure.parsers.fluff_parser import FluffParser
from application.use_cases.scan_media import ScanMediaUseCase
from application.use_cases.cleanup_files import CleanupFilesUseCase
from application.use_cases.move_series import MoveSeriesUseCase
from application.use_cases.organize_folders import OrganizeFoldersUseCase
from application.commands.cleanup_command import CleanupCommand
from presentation.widgets.cleanup_panel import CleanupPanel
from presentation.widgets.settings_panel import SettingsPanel
from presentation.widgets.hotkeys_panel import HotkeysPanel
from presentation.widgets.toast import Toast
from presentation.dialogs.organize_dialog import OrganizeDialog
from presentation.dialogs.media_type_dialog import MediaTypeDialog
from presentation.dialogs.series_organize_dialog import SeriesOrganizeDialog
from presentation.dialogs.movies_organize_dialog import MoviesOrganizeDialog
from domain.value_objects.file_path import FilePath


class ScanWorker(QThread):
    """Background worker thread for media scanning"""

    # Signals
    scan_started = Signal()
    scan_progress = Signal(str)  # Progress message
    scan_completed = Signal(object)  # ScanResult
    scan_failed = Signal(str)  # Error message

    def __init__(self, settings: Settings, logger):
        super().__init__()
        self.settings = settings
        self.logger = logger

    def run(self):
        """Execute scan in background thread"""
        try:
            self.scan_started.emit()
            self.scan_progress.emit("Initializing scan...")

            # Create scan use case
            scan_use_case = ScanMediaUseCase(self.settings, self._thread_logger)

            # Execute scan
            self.scan_progress.emit("Scanning directories...")
            result = scan_use_case.execute()

            # Emit completion
            self.scan_completed.emit(result)

        except Exception as e:
            self.scan_failed.emit(str(e))

    def _thread_logger(self, message: str):
        """Logger that emits progress signal"""
        self.scan_progress.emit(message)


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()

        # Initialize services
        self.settings_repo = SettingsRepository()
        self.settings = self.settings_repo.load()
        self.file_system = FileSystemService()
        self.history = HistoryService(self.file_system, self.log)
        self.undo_redo_manager = UndoRedoManager()

        # Current scan result
        self.scan_result = None

        # Scan worker thread
        self.scan_worker = None
        self.is_scanning = False

        # Setup UI
        self.setWindowTitle("JMAD Media Tool - Refactored V1")
        self.setGeometry(100, 100, 1400, 800)

        self._build_ui()

        # Setup keyboard shortcuts for undo/redo
        self._setup_keyboard_shortcuts()

        # Connect UndoRedoManager signals
        self._connect_undo_redo_signals()

        # Setup file system watcher for staging directory
        self._setup_file_watcher()

        # Auto-scan on launch (delayed to let UI render)
        QTimer.singleShot(100, self._initial_scan)

    def _build_ui(self):
        """Build the user interface"""
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)

        # Main layout
        layout = QVBoxLayout(central)

        # Create toolbar at the top with split button layout
        toolbar_layout = QHBoxLayout()

        # Left stretch to push center buttons to middle
        toolbar_layout.addStretch()

        # Center buttons (Scan and Organize)
        center_buttons_layout = self._create_center_toolbar()
        toolbar_layout.addLayout(center_buttons_layout)

        # Middle stretch to keep center buttons centered
        toolbar_layout.addStretch()

        # Right buttons (Undo and Redo)
        right_buttons_layout = self._create_right_toolbar()
        toolbar_layout.addLayout(right_buttons_layout)

        layout.addLayout(toolbar_layout)

        # Tab widget for main content
        self.tabs = QTabWidget()
        self.tabs.currentChanged.connect(self._on_tab_changed)

        # Create media browser tab
        media_tab = self._create_media_tab()
        self.tabs.addTab(media_tab, "Media Browser")

        # Create settings tab with subtabs
        settings_container = self._create_settings_tab()
        self.tabs.addTab(settings_container, "Settings")

        layout.addWidget(self.tabs)

        # Status bar
        self.statusBar().showMessage("Ready")

    def _create_media_tab(self) -> QWidget:
        """Create the media browser tab content"""
        media_widget = QWidget()
        media_layout = QVBoxLayout(media_widget)
        media_layout.setContentsMargins(0, 0, 0, 0)

        # Main horizontal splitter (60/40 split: tree | right pane)
        main_splitter = QSplitter(Qt.Horizontal)

        # Left: Media tree (25%)
        tree_widget = QWidget()
        tree_layout = QVBoxLayout(tree_widget)
        tree_layout.setContentsMargins(0, 0, 0, 0)

        tree_header = QLabel("Media Tree")
        tree_header.setStyleSheet("font-weight: bold; padding: 5px;")
        tree_layout.addWidget(tree_header)

        # Search and filter controls
        search_filter_layout = QVBoxLayout()
        search_filter_layout.setSpacing(5)

        # Search bar
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        search_layout.addWidget(search_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Type to search folders...")
        self.search_input.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(self.search_input)
        search_filter_layout.addLayout(search_layout)

        # Filter controls
        filter_layout = QHBoxLayout()
        filter_label = QLabel("Filter:")
        filter_layout.addWidget(filter_label)

        # Show all / only unprocessed toggle
        self.show_processed_cb = QCheckBox("Show Processed")
        self.show_processed_cb.setChecked(True)  # Show all by default
        self.show_processed_cb.stateChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.show_processed_cb)

        # Media type filter
        self.media_type_filter = QComboBox()
        self.media_type_filter.addItems(["All Types", "TV Shows", "Anime", "Movies", "Unknown"])
        self.media_type_filter.currentTextChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.media_type_filter)

        filter_layout.addStretch()
        search_filter_layout.addLayout(filter_layout)

        tree_layout.addLayout(search_filter_layout)

        self.media_tree = QTreeWidget()
        self.media_tree.setHeaderLabels(["Folder Name", "File Count", "Media Type"])
        self.media_tree.setColumnWidth(0, 350)
        self.media_tree.setColumnWidth(1, 100)
        self.media_tree.setColumnWidth(2, 120)

        # Enable multi-select with standard keybindings (Ctrl+Click, Shift+Click)
        self.media_tree.setSelectionMode(QTreeWidget.ExtendedSelection)

        # Enable context menu (right-click)
        self.media_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.media_tree.customContextMenuRequested.connect(self._show_tree_context_menu)

        # Connect selection change to update organize button
        self.media_tree.itemSelectionChanged.connect(self._on_tree_selection_changed)

        tree_layout.addWidget(self.media_tree)

        main_splitter.addWidget(tree_widget)

        # Right: Vertical splitter for cleanup tool and console (50/50 split)
        right_splitter = QSplitter(Qt.Vertical)

        # Top: Cleanup Tool (50%)
        cleanup_container = QWidget()
        cleanup_container_layout = QVBoxLayout(cleanup_container)
        cleanup_container_layout.setContentsMargins(0, 0, 0, 0)

        cleanup_header = QLabel("Cleanup Tool")
        cleanup_header.setStyleSheet("font-weight: bold; padding: 5px; background-color: #2a2a2a; color: white;")
        cleanup_container_layout.addWidget(cleanup_header)

        # Cleanup panel widget
        self.cleanup_panel = CleanupPanel()
        self.cleanup_panel.cleanup_requested.connect(self._on_cleanup_requested)

        # Load saved cleanup settings
        if self.settings.cleanup_ext_states:
            self.cleanup_panel.load_settings(self.settings.cleanup_ext_states)

        cleanup_container_layout.addWidget(self.cleanup_panel)

        right_splitter.addWidget(cleanup_container)

        # Bottom: Console tabs (50%)
        console_container = QWidget()
        console_container_layout = QVBoxLayout(console_container)
        console_container_layout.setContentsMargins(0, 0, 0, 0)

        console_header = QLabel("Console & Preview")
        console_header.setStyleSheet("font-weight: bold; padding: 5px; background-color: #2a2a2a; color: white;")
        console_container_layout.addWidget(console_header)

        # Create tab widget for console and preview
        self.console_tabs = QTabWidget()

        # Console tab (log output)
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console_tabs.addTab(self.console, "Console")

        # Preview tab (file/folder structure)
        self.preview_tree = QTreeWidget()
        self.preview_tree.setHeaderLabels(["Name", "Type", "Size"])
        self.preview_tree.setColumnWidth(0, 300)
        self.preview_tree.setColumnWidth(1, 80)
        self.console_tabs.addTab(self.preview_tree, "Preview")

        console_container_layout.addWidget(self.console_tabs)

        # Progress bar for scan operations
        self.scan_progress_bar = QProgressBar()
        self.scan_progress_bar.setTextVisible(True)
        self.scan_progress_bar.setFormat("Ready")
        self.scan_progress_bar.setRange(0, 0)  # Indeterminate mode
        self.scan_progress_bar.setVisible(False)  # Hidden by default
        self.scan_progress_bar.setMaximumHeight(20)
        console_container_layout.addWidget(self.scan_progress_bar)

        right_splitter.addWidget(console_container)

        # Set 50/50 split for right pane
        right_splitter.setStretchFactor(0, 1)
        right_splitter.setStretchFactor(1, 1)

        main_splitter.addWidget(right_splitter)

        # Set 60/40 split for main layout (media tree gets more space)
        main_splitter.setStretchFactor(0, 3)  # Tree: 60%
        main_splitter.setStretchFactor(1, 2)  # Right pane: 40%

        media_layout.addWidget(main_splitter)

        return media_widget

    def _create_settings_tab(self) -> QWidget:
        """Create the settings tab with subtabs for General and Hotkeys"""
        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)
        settings_layout.setContentsMargins(0, 0, 0, 0)

        # Create tab widget for settings subtabs
        settings_tabs = QTabWidget()

        # General Settings subtab
        self.settings_panel = SettingsPanel(self.settings)
        self.settings_panel.settings_changed.connect(self._on_settings_changed)
        settings_tabs.addTab(self.settings_panel, "General")

        # Hotkeys subtab
        self.hotkeys_panel = HotkeysPanel(self.settings)
        self.hotkeys_panel.settings_changed.connect(self._on_settings_changed)
        settings_tabs.addTab(self.hotkeys_panel, "Hotkeys")

        settings_layout.addWidget(settings_tabs)

        return settings_widget

    def _setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for undo/redo"""
        # Undo: Ctrl+Z
        undo_shortcut = QShortcut(QKeySequence.StandardKey.Undo, self)
        undo_shortcut.activated.connect(self.undo_action)

        # Redo: Ctrl+Y (Windows/Linux) or Ctrl+Shift+Z (Mac-style, also works everywhere)
        redo_shortcut1 = QShortcut(QKeySequence.StandardKey.Redo, self)
        redo_shortcut1.activated.connect(self.redo_action)

        # Alternative redo: Ctrl+Shift+Z (works on all platforms)
        redo_shortcut2 = QShortcut(QKeySequence("Ctrl+Shift+Z"), self)
        redo_shortcut2.activated.connect(self.redo_action)

        self.log("Keyboard shortcuts enabled: Ctrl+Z (Undo), Ctrl+Y / Ctrl+Shift+Z (Redo)")

    def _create_center_toolbar(self) -> QHBoxLayout:
        """Create center toolbar with Scan and Organize buttons"""
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        # Scan button
        self.scan_btn = QPushButton("Scan")
        self.scan_btn.clicked.connect(self.scan_media)
        self.scan_btn.setMinimumWidth(100)
        toolbar.addWidget(self.scan_btn)

        # Organize button (disabled by default, green when enabled)
        self.organize_btn = QPushButton("Organize")
        self.organize_btn.clicked.connect(self._on_organize_clicked)
        self.organize_btn.setEnabled(False)
        self.organize_btn.setMinimumWidth(100)
        toolbar.addWidget(self.organize_btn)

        return toolbar

    def _create_right_toolbar(self) -> QHBoxLayout:
        """Create right toolbar with Undo and Redo buttons"""
        toolbar = QHBoxLayout()
        toolbar.setSpacing(5)

        # Undo button
        self.undo_btn = QPushButton("Undo")
        self.undo_btn.clicked.connect(self.undo_action)
        self.undo_btn.setEnabled(False)
        toolbar.addWidget(self.undo_btn)

        # Redo button
        self.redo_btn = QPushButton("Redo")
        self.redo_btn.clicked.connect(self.redo_action)
        self.redo_btn.setEnabled(False)
        toolbar.addWidget(self.redo_btn)

        return toolbar

    def scan_media(self):
        """Execute media scan in background thread"""
        # Prevent multiple simultaneous scans
        if self.is_scanning:
            self.log("Scan already in progress...")
            return

        # Clean up previous worker if exists
        if self.scan_worker is not None:
            self.scan_worker.wait()
            self.scan_worker.deleteLater()

        # Create and configure worker
        self.scan_worker = ScanWorker(self.settings, self.log)
        self.scan_worker.scan_started.connect(self._on_scan_started)
        self.scan_worker.scan_progress.connect(self._on_scan_progress)
        self.scan_worker.scan_completed.connect(self._on_scan_completed)
        self.scan_worker.scan_failed.connect(self._on_scan_failed)
        self.scan_worker.finished.connect(self._on_scan_finished)

        # Start scan
        self.is_scanning = True
        self.scan_worker.start()

    def _on_scan_started(self):
        """Handle scan started"""
        # Show progress bar
        self.scan_progress_bar.setVisible(True)
        self.scan_progress_bar.setFormat("Scanning...")
        self.log("Starting media scan...")

    def _on_scan_progress(self, message: str):
        """Handle scan progress update"""
        # Update progress bar text
        self.scan_progress_bar.setFormat(message)

    def _on_scan_completed(self, result):
        """Handle scan completion"""
        self.scan_result = result

        if self.scan_result.errors:
            for error in self.scan_result.errors:
                self.log(f"Error: {error}")
            QMessageBox.warning(self, "Scan Errors", "\n".join(self.scan_result.errors))
        else:
            # Populate tree
            self._populate_tree()

            # V1: Count total files instead of episodes
            total_files = sum(getattr(s, '_v1_file_count', 0) for s in self.scan_result.series_map.values())
            self.statusBar().showMessage(
                f"Scan complete: {self.scan_result.total_series} folders, {total_files} files"
            )

    def _on_scan_failed(self, error_message: str):
        """Handle scan failure"""
        self.log(f"Scan failed: {error_message}")
        QMessageBox.critical(self, "Scan Failed", f"An error occurred during scanning:\n{error_message}")

    def _on_scan_finished(self):
        """Handle scan thread finished (cleanup)"""
        self.is_scanning = False
        self.scan_progress_bar.setVisible(False)
        self.scan_progress_bar.setFormat("Ready")

    def _populate_tree(self):
        """Populate media tree with scan results (V1: simple folder list)"""
        from domain.value_objects.media_type import MediaType

        self.media_tree.clear()

        if not self.scan_result:
            return

        # V1: Simple folder listing (no seasons/episodes tree)
        for folder_name, series in self.scan_result.series_map.items():
            # Get file count if available
            file_count = getattr(series, '_v1_file_count', 0)

            # Check if media is in an organizational folder (processed)
            # A folder is processed if it's INSIDE an org folder, not just auto-detected
            is_processed = self._is_folder_processed(series)

            # Create top-level item showing folder name, file count, and media type
            folder_item = QTreeWidgetItem([
                series.name,  # Raw folder name
                f"{file_count} files",
                series.media_type.value  # Media type
            ])

            # Add green indicator for processed media
            if is_processed:
                # Set green color for all columns to indicate processed
                folder_item.setForeground(0, QColor(100, 255, 100))  # Bright green for folder name
                folder_item.setForeground(1, QColor(150, 255, 150))  # Lighter green for file count
                folder_item.setForeground(2, QColor(150, 255, 150))  # Lighter green for media type
                # Add checkmark prefix to folder name
                folder_item.setText(0, f"✓ {series.name}")

            self.media_tree.addTopLevelItem(folder_item)

    def _is_folder_processed(self, series: 'Series') -> bool:
        """Check if a folder is in an organizational folder (processed)

        Args:
            series: Series object to check

        Returns:
            True if folder is inside an organizational folder, False otherwise
        """
        # Get the parent directory of the series folder
        parent_dir = series.root_path.path.parent

        # Check if parent directory name matches an organizational folder
        org_folder_names = [
            self.settings.org_folder_anime.lower(),
            self.settings.org_folder_tv_shows.lower(),
            self.settings.org_folder_movies.lower()
        ]

        return parent_dir.name.lower() in org_folder_names

    def _on_settings_changed(self):
        """Called when any setting is changed - auto-save"""
        success = self.settings_repo.save(self.settings)
        if success:
            self.log("Settings saved automatically")

        # Update file watcher if staging directory changed
        self._update_file_watcher()

    def _on_tab_changed(self, index: int):
        """Called when user switches tabs

        Args:
            index: New tab index
        """
        # If switching away from settings tab, show toast
        if self.tabs.tabText(index) != "Settings":
            # Check if we were on settings tab before
            Toast.show_toast(self, "Settings saved", 1500, color="#4CAF50")  # Green color

    def undo_action(self):
        """Undo last action"""
        # Try UndoRedoManager first (for cleanup operations)
        if self.undo_redo_manager.can_undo():
            if self.undo_redo_manager.undo():
                self.log("Undo successful")
                self.scan_media()  # Refresh display
                return
        # Fall back to HistoryService (for organize operations)
        elif self.history.can_undo():
            if self.history.undo():
                self.log("Undo successful")
                self._update_undo_redo_buttons()
                self.scan_media()  # Refresh display
                return

        self.log("Undo failed")

    def redo_action(self):
        """Redo last undone action"""
        # Try UndoRedoManager first (for cleanup operations)
        if self.undo_redo_manager.can_redo():
            if self.undo_redo_manager.redo():
                self.log("Redo successful")
                self.scan_media()  # Refresh display
                return
        # Fall back to HistoryService (for organize operations)
        elif self.history.can_redo():
            if self.history.redo():
                self.log("Redo successful")
                self._update_undo_redo_buttons()
                self.scan_media()  # Refresh display
                return

        self.log("Redo failed")

    def _update_undo_redo_buttons(self):
        """Update undo/redo button states"""
        # Check both undo/redo systems
        can_undo = self.undo_redo_manager.can_undo() or self.history.can_undo()
        can_redo = self.undo_redo_manager.can_redo() or self.history.can_redo()

        self.undo_btn.setEnabled(can_undo)
        self.redo_btn.setEnabled(can_redo)

        # Update tooltips with action descriptions (prioritize UndoRedoManager)
        if self.undo_redo_manager.can_undo():
            self.undo_btn.setToolTip(f"Undo: {self.undo_redo_manager.get_undo_description()}")
        elif self.history.can_undo():
            self.undo_btn.setToolTip(f"Undo: {self.history.get_undo_description()}")
        else:
            self.undo_btn.setToolTip("Nothing to undo")

        if self.undo_redo_manager.can_redo():
            self.redo_btn.setToolTip(f"Redo: {self.undo_redo_manager.get_redo_description()}")
        elif self.history.can_redo():
            self.redo_btn.setToolTip(f"Redo: {self.history.get_redo_description()}")
        else:
            self.redo_btn.setToolTip("Nothing to redo")

    def _show_tree_context_menu(self, position):
        """Show context menu for media tree

        Args:
            position: Position where right-click occurred
        """
        # Get selected items
        selected_items = self.media_tree.selectedItems()

        if not selected_items:
            return

        # Create context menu
        menu = QMenu(self)

        # Add "Organize As" submenu for direct media type selection
        organize_menu = menu.addMenu("Organize As...")

        tv_action = organize_menu.addAction("TV Show")
        tv_action.triggered.connect(lambda: self._on_organize_with_type(MediaTypeDialog.TV_SERIES))

        anime_action = organize_menu.addAction("Anime")
        anime_action.triggered.connect(lambda: self._on_organize_with_type(MediaTypeDialog.ANIME))

        movie_action = organize_menu.addAction("Movie")
        movie_action.triggered.connect(lambda: self._on_organize_with_type(MediaTypeDialog.MOVIES))

        menu.addSeparator()

        # Add original "Organize..." (with dialog selection)
        organize_action = menu.addAction("Organize... (Choose Type)")
        organize_action.triggered.connect(self._on_organize_requested)

        menu.addSeparator()

        # Add "Open in Explorer" action
        import platform
        system = platform.system()
        if system == "Windows":
            explorer_text = "Open in Explorer"
        elif system == "Darwin":  # macOS
            explorer_text = "Open in Finder"
        else:  # Linux and others
            explorer_text = "Open in File Manager"

        open_explorer_action = menu.addAction(explorer_text)
        open_explorer_action.triggered.connect(self._on_open_in_explorer)

        # Show menu at cursor position
        menu.exec_(self.media_tree.viewport().mapToGlobal(position))

    def _on_tree_selection_changed(self):
        """Handle tree selection change - update organize button and cleanup button"""
        selected_items = self.media_tree.selectedItems()
        has_selection = len(selected_items) > 0
        selection_count = len(selected_items)

        # Update organize button - Enable/disable and change color
        self.organize_btn.setEnabled(has_selection)

        # Change color to green when enabled, gray when disabled
        if has_selection:
            self.organize_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        else:
            self.organize_btn.setStyleSheet("")  # Reset to default style

        # Update cleanup button text based on selection
        if has_selection:
            self.cleanup_panel.update_button_text(f"Clean Selected ({selection_count})")
        else:
            self.cleanup_panel.update_button_text("Clean Staging Directory")

        # Update preview tree
        self._update_preview_tree(selected_items)

    def _on_search_changed(self, text: str):
        """Handle search text change - filter tree items

        Args:
            text: Search text entered by user
        """
        self._apply_filters()

    def _on_filter_changed(self):
        """Handle filter change - apply filters to tree"""
        self._apply_filters()

    def _apply_filters(self):
        """Apply search and filter criteria to media tree"""
        search_text = self.search_input.text().lower()
        show_processed = self.show_processed_cb.isChecked()
        media_type_filter = self.media_type_filter.currentText()

        # Iterate through all top-level items
        for i in range(self.media_tree.topLevelItemCount()):
            item = self.media_tree.topLevelItem(i)
            folder_name = item.text(0)

            # Remove checkmark prefix for search
            display_name = folder_name
            is_processed = folder_name.startswith("✓ ")
            if is_processed:
                display_name = folder_name[2:]  # Remove "✓ " prefix

            # Check search filter
            search_match = search_text == "" or search_text in display_name.lower()

            # Check processed filter
            processed_match = show_processed or not is_processed

            # Check media type filter
            media_type = item.text(2)  # Media type is in column 2
            if media_type_filter == "All Types":
                type_match = True
            elif media_type_filter == "TV Shows":
                type_match = "TV" in media_type or "Series" in media_type
            elif media_type_filter == "Anime":
                type_match = "Anime" in media_type
            elif media_type_filter == "Movies":
                type_match = "Movie" in media_type
            elif media_type_filter == "Unknown":
                type_match = media_type == "Unknown" or media_type == ""
            else:
                type_match = True

            # Show/hide item based on all filters
            item.setHidden(not (search_match and processed_match and type_match))

    def _update_preview_tree(self, selected_items: List[QTreeWidgetItem]):
        """Update preview tree with files and folder structure of selected items

        Args:
            selected_items: List of selected tree items
        """
        self.preview_tree.clear()

        if not selected_items:
            # Show message when nothing is selected
            placeholder = QTreeWidgetItem(["No items selected", "", ""])
            placeholder.setForeground(0, QColor(128, 128, 128))
            self.preview_tree.addTopLevelItem(placeholder)
            return

        for tree_item in selected_items:
            folder_name = tree_item.text(0)
            # Strip the checkmark prefix if present (added to processed folders)
            if folder_name.startswith("✓ "):
                folder_name = folder_name[2:]  # Remove "✓ " prefix

            # Find the series in scan_result
            if not self.scan_result or folder_name not in self.scan_result.series_map:
                continue

            series = self.scan_result.series_map[folder_name]
            root_path = series.root_path.path

            # Create top-level item for this media title
            title_item = QTreeWidgetItem([folder_name, "Folder", ""])
            title_item.setForeground(0, QColor(255, 255, 255))
            title_item.setForeground(1, QColor(200, 200, 200))
            self.preview_tree.addTopLevelItem(title_item)

            # Recursively add folder structure
            self._add_folder_contents(title_item, root_path)

            # Expand the top level
            title_item.setExpanded(True)

    def _add_folder_contents(self, parent_item: QTreeWidgetItem, folder_path: Path):
        """Recursively add folder contents to preview tree

        Args:
            parent_item: Parent tree item
            folder_path: Path to folder to add
        """
        try:
            # List all entries in the folder
            entries = sorted(folder_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))

            for entry in entries:
                if entry.is_dir():
                    # Add folder
                    folder_item = QTreeWidgetItem([
                        entry.name,
                        "Folder",
                        ""
                    ])
                    folder_item.setForeground(1, QColor(150, 150, 255))
                    parent_item.addChild(folder_item)

                    # Recursively add contents
                    self._add_folder_contents(folder_item, entry)

                elif entry.is_file():
                    # Add file with size
                    size = entry.stat().st_size
                    size_str = self._format_file_size(size)

                    file_item = QTreeWidgetItem([
                        entry.name,
                        "File",
                        size_str
                    ])
                    file_item.setForeground(1, QColor(200, 200, 200))
                    file_item.setForeground(2, QColor(180, 180, 180))
                    parent_item.addChild(file_item)

        except (OSError, PermissionError):
            pass

    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format

        Args:
            size_bytes: Size in bytes

        Returns:
            Formatted size string (e.g., "1.5 GB")
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"

    def _on_organize_clicked(self):
        """Handle organize button click - calls organize workflow"""
        self._on_organize_requested()

    def _on_organize_requested(self):
        """Handle organize action from context menu - NEW WORKFLOW"""
        selected_items = self.media_tree.selectedItems()

        if not selected_items:
            QMessageBox.information(self, "No Selection", "Please select folders to organize.")
            return

        # Get folder names and their actual paths from scan result
        folder_paths = {}  # folder_name -> full_path
        for item in selected_items:
            folder_name = item.text(0)
            # Strip the checkmark prefix if present (added to processed folders)
            if folder_name.startswith("✓ "):
                folder_name = folder_name[2:]  # Remove "✓ " prefix

            self.log(f"DEBUG: Looking for folder: '{folder_name}'")

            if self.scan_result:
                self.log(f"DEBUG: Available folders in series_map: {list(self.scan_result.series_map.keys())}")

                if folder_name in self.scan_result.series_map:
                    series = self.scan_result.series_map[folder_name]
                    folder_paths[folder_name] = str(series.root_path.path)
                    self.log(f"DEBUG: Found path: {folder_paths[folder_name]}")
                else:
                    self.log(f"DEBUG: Folder '{folder_name}' NOT found in series_map")
            else:
                self.log(f"DEBUG: No scan_result available")

        if not folder_paths:
            error_msg = "Could not find paths for selected folders.\n\n"
            error_msg += f"Selected: {[item.text(0) for item in selected_items]}\n\n"
            if self.scan_result:
                error_msg += f"Available: {list(self.scan_result.series_map.keys())}"
            QMessageBox.warning(self, "Error", error_msg)
            return

        self.log(f"Organize requested for {len(folder_paths)} folder(s)")

        # Step 1: Show media type selection dialog
        media_type_dialog = MediaTypeDialog(self, len(folder_paths))

        if media_type_dialog.exec_() != MediaTypeDialog.Accepted:
            self.log("Organize cancelled - no media type selected")
            return

        media_type = media_type_dialog.get_selected_type()
        self.log(f"Media type selected: {media_type}")

        # Step 2: Route to appropriate organize dialog
        if media_type_dialog.should_use_series_dialog():
            # TV Series, Anime, or Anime Movies → Series Organize Dialog
            self._show_series_organize_dialog(folder_paths, media_type)
        elif media_type_dialog.should_use_movies_dialog():
            # Movies → Movies Organize Dialog
            self._show_movies_organize_dialog(folder_paths, media_type)

    def _on_organize_with_type(self, media_type: str):
        """Handle organize action with predefined media type (no dialog)

        Args:
            media_type: Media type constant from MediaTypeDialog
        """
        selected_items = self.media_tree.selectedItems()

        if not selected_items:
            QMessageBox.information(self, "No Selection", "Please select folders to organize.")
            return

        # Get folder names and their actual paths from scan result
        folder_paths = {}  # folder_name -> full_path
        for item in selected_items:
            folder_name = item.text(0)
            # Strip the checkmark prefix if present (added to processed folders)
            if folder_name.startswith("✓ "):
                folder_name = folder_name[2:]  # Remove "✓ " prefix

            if self.scan_result and folder_name in self.scan_result.series_map:
                series = self.scan_result.series_map[folder_name]
                folder_paths[folder_name] = str(series.root_path.path)

        if not folder_paths:
            QMessageBox.warning(self, "Error", "Could not find paths for selected folders.")
            return

        self.log(f"Organize as {media_type} requested for {len(folder_paths)} folder(s)")

        # Route to appropriate organize dialog based on media type
        if media_type in [MediaTypeDialog.TV_SERIES, MediaTypeDialog.ANIME]:
            self._show_series_organize_dialog(folder_paths, media_type)
        elif media_type == MediaTypeDialog.MOVIES:
            self._show_movies_organize_dialog(folder_paths, media_type)

    def _on_open_in_explorer(self):
        """Open selected folder(s) in file explorer/finder"""
        import subprocess
        import platform

        selected_items = self.media_tree.selectedItems()

        if not selected_items:
            return

        system = platform.system()

        for item in selected_items:
            folder_name = item.text(0)
            # Strip the checkmark prefix if present
            if folder_name.startswith("✓ "):
                folder_name = folder_name[2:]

            if self.scan_result and folder_name in self.scan_result.series_map:
                series = self.scan_result.series_map[folder_name]
                folder_path = str(series.root_path.path)

                try:
                    if system == "Windows":
                        # Open in Windows Explorer
                        subprocess.Popen(['explorer', folder_path])
                    elif system == "Darwin":  # macOS
                        # Open in Finder
                        subprocess.Popen(['open', folder_path])
                    else:  # Linux and others
                        # Try xdg-open (works on most Linux desktops)
                        subprocess.Popen(['xdg-open', folder_path])

                    self.log(f"Opened folder in file manager: {folder_name}")
                except Exception as e:
                    self.log(f"Error opening folder {folder_name}: {e}")
                    QMessageBox.warning(
                        self,
                        "Error",
                        f"Could not open folder in file manager:\n{e}"
                    )

    def _show_series_organize_dialog(self, folder_paths: Dict[str, str], media_type: str):
        """Show series organize dialog (3-pane)

        Args:
            folder_paths: Dict mapping folder names to full paths
            media_type: Media type string
        """
        series_dialog = SeriesOrganizeDialog(self, folder_paths, self.settings, media_type)

        if series_dialog.exec_() != SeriesOrganizeDialog.Accepted:
            self.log("Organize cancelled")
            return

        # Get organize operations from dialog
        operations = series_dialog.get_organize_operations()
        media_title = series_dialog.media_title

        self.log(f"Organizing '{media_title}' with {len(operations['seasons'])} season(s)")

        # Execute the organize operations
        self._execute_series_organize(operations, media_title, media_type)

    def _execute_series_organize(self, operations: Dict, media_title: str, media_type: str):
        """Execute series organize operations within staging directory

        Reorganizes files within staging into proper folder structure.
        Files stay in staging - they are not moved to library directories.

        Args:
            operations: Dictionary with seasons and file_renames
            media_title: Series title (e.g., "My Hero Academia")
            media_type: Media type (from MediaTypeDialog: "tv_series" or "anime")
        """
        import shutil
        from infrastructure.services.history_service import HistoryAction, ActionType
        from infrastructure.services.file_system_service import MoveOperation

        # Check staging directory is configured
        if not self.settings.directories.staging:
            QMessageBox.warning(
                self,
                "Staging Not Configured",
                "Please configure the staging directory in Settings."
            )
            return

        staging_path = Path(self.settings.directories.staging)

        # Determine media type folder name from settings
        if media_type == "tv_series":
            media_type_folder = self.settings.org_folder_tv_shows
        elif media_type == "anime":
            media_type_folder = self.settings.org_folder_anime
        elif media_type == "movies":
            media_type_folder = self.settings.org_folder_movies
        else:
            media_type_folder = self.settings.org_folder_tv_shows

        # Create series folder within staging/media_type/
        series_folder = staging_path / media_type_folder / media_title
        try:
            series_folder.mkdir(parents=True, exist_ok=True)
            self.log(f"Created series folder in staging: {series_folder}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create series folder: {e}")
            return

        # Track all source folders for cleanup
        source_folders_to_check = set()

        # Collect all move operations for history tracking
        move_operations = []

        # Process each season
        files_moved = 0
        errors = []

        for season_num, season_data in operations["seasons"].items():
            folder_name = season_data["folder_name"]  # e.g., "Season 1", "Specials"
            files = season_data["files"]

            # Create season folder
            season_folder = series_folder / folder_name
            try:
                season_folder.mkdir(parents=True, exist_ok=True)
                self.log(f"Created season folder: {season_folder}")
            except Exception as e:
                errors.append(f"Failed to create {season_folder}: {e}")
                continue

            # Move each file
            for file_info in files:
                original_path = Path(file_info["original_path"])
                new_name = file_info["new_name"]

                # For movies, create subfolder for each movie (folder = movie title without extension)
                if folder_name == "Movies":
                    movie_title = Path(new_name).stem  # Get filename without extension
                    movie_folder = season_folder / movie_title
                    try:
                        movie_folder.mkdir(parents=True, exist_ok=True)
                    except Exception as e:
                        errors.append(f"Failed to create movie folder {movie_title}: {e}")
                        continue
                    target_path = movie_folder / new_name
                else:
                    # For regular seasons, put files directly in season folder
                    target_path = season_folder / new_name

                # Track source folder for cleanup
                source_folders_to_check.add(original_path.parent)

                try:
                    # Move and rename file
                    shutil.move(str(original_path), str(target_path))
                    self.log(f"Moved: {original_path.name} → {target_path}")
                    files_moved += 1

                    # Record move operation for undo
                    move_operations.append(MoveOperation(
                        source=FilePath(str(original_path)),
                        destination=FilePath(str(target_path))
                    ))

                except Exception as e:
                    errors.append(f"Failed to move {original_path.name}: {e}")

        # Remove non-media files from source folders
        non_media_removed = self._cleanup_non_media_files(source_folders_to_check)

        # Clean up empty source folders
        self._cleanup_empty_folders(source_folders_to_check, staging_path)

        # Record organize action in history for undo/redo (only if files were moved)
        if move_operations:
            history_action = HistoryAction(
                description=f"Organize '{media_title}' ({len(move_operations)} files)",
                action_type=ActionType.ORGANIZE,
                operations=move_operations
            )
            # Add to history without re-executing (we already moved the files)
            self.history.history.append(history_action)
            self.history.current_position = len(self.history.history) - 1
            self.log(f"Recorded organize action in history: {history_action.description}")

        # Show results
        if errors:
            error_msg = f"Organized {files_moved} file(s) with errors:\n\n" + "\n".join(errors[:10])
            if len(errors) > 10:
                error_msg += f"\n... and {len(errors) - 10} more errors"
            QMessageBox.warning(self, "Organize Complete with Errors", error_msg)
        else:
            if self.settings.show_organize_confirmation:
                success_msg = f"Successfully organized {files_moved} file(s) in staging:\n{series_folder}"
                if non_media_removed > 0:
                    success_msg += f"\n\nRemoved {non_media_removed} non-media file(s)"
                success_msg += "\n\nFiles remain in staging and can now be moved to library using the Move tool."
                QMessageBox.information(self, "Organize Complete", success_msg)

        # Update undo/redo buttons
        self._update_undo_redo_buttons()

        # Refresh tree to show updated staging directory
        self.scan_media()

    def _show_movies_organize_dialog(self, folder_paths: Dict[str, str], media_type: str):
        """Show movies organize dialog

        Args:
            folder_paths: Dict mapping folder names to full paths
            media_type: Media type string
        """
        movies_dialog = MoviesOrganizeDialog(self, folder_paths, self.settings, media_type)

        if movies_dialog.exec_() != MoviesOrganizeDialog.Accepted:
            self.log("Organize cancelled")
            return

        # Get organize operations from dialog
        operations = movies_dialog.get_organize_operations()

        # Log
        movie_count = len(operations["movies"])
        self.log(f"Organizing {movie_count} movie(s)")

        # Execute the organize operations
        self._execute_movies_organize(operations, media_type)

    def _execute_movies_organize(self, operations: Dict, media_type: str):
        """Execute movies organize operations within staging directory

        Args:
            operations: Dictionary with movies list and non_media_files
            media_type: Media type (movies)
        """
        import shutil
        from infrastructure.services.history_service import HistoryAction, ActionType
        from infrastructure.services.file_system_service import MoveOperation

        # Check staging directory is configured
        if not self.settings.directories.staging:
            QMessageBox.warning(
                self,
                "Staging Not Configured",
                "Please configure the staging directory in Settings."
            )
            return

        staging_path = Path(self.settings.directories.staging)

        # Determine media type folder name from settings
        media_type_folder = self.settings.org_folder_movies

        # Track all source folders for cleanup
        source_folders_to_check = set()

        # Collect all move operations for history tracking
        move_operations = []

        # Process each movie
        files_moved = 0
        errors = []
        movies_created = set()  # Track unique movie folders created

        for movie_info in operations["movies"]:
            original_path = Path(movie_info["original_path"])
            movie_title = movie_info["movie_title"]
            new_name = movie_info["new_name"]

            # Create movie folder within staging/movies/
            movie_folder = staging_path / media_type_folder / movie_title

            try:
                movie_folder.mkdir(parents=True, exist_ok=True)
                if movie_title not in movies_created:
                    self.log(f"Created movie folder in staging: {movie_folder}")
                    movies_created.add(movie_title)
            except Exception as e:
                errors.append(f"Failed to create folder for {movie_title}: {e}")
                continue

            target_path = movie_folder / new_name

            # Track source folder for cleanup
            source_folders_to_check.add(original_path.parent)

            try:
                # Move and rename file
                shutil.move(str(original_path), str(target_path))
                self.log(f"Moved: {original_path.name} → {target_path}")
                files_moved += 1

                # Record move operation for undo
                move_operations.append(MoveOperation(
                    source=FilePath(str(original_path)),
                    destination=FilePath(str(target_path))
                ))

            except Exception as e:
                errors.append(f"Failed to move {original_path.name}: {e}")

        # Remove non-media files from source folders
        non_media_removed = self._cleanup_non_media_files(source_folders_to_check)

        # Clean up empty source folders
        self._cleanup_empty_folders(source_folders_to_check, staging_path)

        # Record organize action in history for undo/redo (only if files were moved)
        if move_operations:
            movie_count = len(movies_created)
            history_action = HistoryAction(
                description=f"Organize {movie_count} movie(s) ({len(move_operations)} files)",
                action_type=ActionType.ORGANIZE,
                operations=move_operations
            )
            # Add to history without re-executing (we already moved the files)
            self.history.history.append(history_action)
            self.history.current_position = len(self.history.history) - 1
            self.log(f"Recorded organize action in history: {history_action.description}")

        # Show results
        if errors:
            error_msg = f"Organized {files_moved} file(s) with errors:\n\n" + "\n".join(errors[:10])
            if len(errors) > 10:
                error_msg += f"\n... and {len(errors) - 10} more errors"
            QMessageBox.warning(self, "Organize Complete with Errors", error_msg)
        else:
            if self.settings.show_organize_confirmation:
                movie_count = len(movies_created)
                success_msg = f"Successfully organized {files_moved} file(s) into {movie_count} movie(s) in staging"

                if non_media_removed > 0:
                    success_msg += f"\n\nRemoved {non_media_removed} non-media file(s)"
                success_msg += "\n\nFiles remain in staging and can now be moved to library using the Move tool."
                QMessageBox.information(self, "Organize Complete", success_msg)

        # Update undo/redo buttons
        self._update_undo_redo_buttons()

        # Refresh tree to show updated staging directory
        self.scan_media()

    def _cleanup_non_media_files(self, folders: set) -> int:
        """Remove non-media files from folders recursively

        Args:
            folders: Set of folder paths to clean

        Returns:
            Number of non-media files removed
        """
        VIDEO_EXTENSIONS = {
            '.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm',
            '.m4v', '.mpg', '.mpeg', '.3gp', '.ogv', '.ts'
        }

        removed_count = 0

        for folder in folders:
            try:
                folder_path = Path(folder)
                if not folder_path.exists() or not folder_path.is_dir():
                    continue

                # Recursively find all files in this folder tree
                for root, dirs, files in os.walk(str(folder_path)):
                    for filename in files:
                        file_path = Path(root) / filename
                        ext = file_path.suffix.lower()
                        if ext not in VIDEO_EXTENSIONS:
                            # Non-media file - remove it
                            try:
                                file_path.unlink()
                                self.log(f"Removed non-media file: {file_path.name}")
                                removed_count += 1
                            except Exception as e:
                                self.log(f"Could not remove {file_path.name}: {e}")

            except (OSError, PermissionError) as e:
                self.log(f"Could not access folder {folder}: {e}")

        return removed_count

    def _cleanup_empty_folders(self, folders: set, staging_path: Path):
        """Clean up empty folders in staging recursively from bottom up

        Args:
            folders: Set of folder paths to check
            staging_path: Staging directory path
        """
        import os

        # Collect all folders to check (including parent folders)
        all_folders_to_check = set()
        for folder in folders:
            folder_path = Path(folder)
            # Only consider folders within staging
            if str(folder_path).startswith(str(staging_path)):
                # Add this folder and all parent folders up to staging
                current = folder_path
                while current != staging_path and current.parent != current:
                    all_folders_to_check.add(current)
                    current = current.parent
                    if not str(current).startswith(str(staging_path)):
                        break

        # Sort by depth (deepest first) to remove from bottom up
        sorted_folders = sorted(all_folders_to_check, key=lambda p: len(Path(p).parts), reverse=True)

        for folder_path in sorted_folders:
            try:
                folder_path = Path(folder_path)

                if not folder_path.exists() or not folder_path.is_dir():
                    continue

                # Check if folder is empty (no files or directories)
                try:
                    if not any(folder_path.iterdir()):
                        folder_path.rmdir()
                        self.log(f"Removed empty folder: {folder_path}")
                except StopIteration:
                    # Folder is empty
                    folder_path.rmdir()
                    self.log(f"Removed empty folder: {folder_path}")

            except Exception as e:
                # Silently skip folders that can't be removed (may have files or be in use)
                pass

    def _execute_organize(self, folder_names: List[str], target_dir: str):
        """Execute organize operation

        Args:
            folder_names: List of folder names to organize
            target_dir: Target directory path
        """
        if not self.settings.directories.staging:
            QMessageBox.warning(self, "Error", "Staging directory not configured.")
            return

        self.log(f"Organizing {len(folder_names)} folder(s) to {target_dir}...")

        # Create and execute use case
        organize_use_case = OrganizeFoldersUseCase(
            staging_dir=self.settings.directories.staging,
            file_system=self.file_system,
            history=self.history,
            logger=self.log
        )

        result = organize_use_case.execute(folder_names, target_dir)

        # Handle result
        if result["success"]:
            folders_moved = result.get("folders_moved", 0)
            message = f"Successfully organized {folders_moved} folder(s) to {target_dir}"

            if result.get("not_found"):
                message += f"\n\nWarning: {len(result['not_found'])} folder(s) not found in staging"

            QMessageBox.information(self, "Success", message)

            # Update undo/redo buttons
            self._update_undo_redo_buttons()

            # Refresh tree
            self.scan_media()
        else:
            error_msg = result.get("error", "Unknown error")

            if result.get("conflicts"):
                conflicts = result["conflicts"]
                error_msg += f"\n\nConflicting folders:\n" + "\n".join(f"  • {name}" for name in conflicts[:10])
                if len(conflicts) > 10:
                    error_msg += f"\n  ... and {len(conflicts) - 10} more"

            QMessageBox.warning(self, "Organize Failed", error_msg)

    def _on_cleanup_requested(self, extensions: set, custom_patterns: list, remove_empty_folders: bool):
        """Handle cleanup request from cleanup panel

        Args:
            extensions: Set of file extensions to clean
            custom_patterns: List of custom patterns (not used yet)
            remove_empty_folders: Whether to remove empty folders after cleanup
        """
        self.log(f"Cleanup requested for extensions: {', '.join(sorted(extensions))}")

        # Get selected series (if any)
        selected_items = self.media_tree.selectedItems()
        target_paths = []

        if selected_items:
            # Clean only selected series
            for item in selected_items:
                # Only process top-level items (series)
                if item.parent() is None:
                    series_name = item.text(0)
                    # Strip the checkmark prefix if present (added to processed folders)
                    if series_name.startswith("✓ "):
                        series_name = series_name[2:]  # Remove "✓ " prefix

                    if self.scan_result and series_name in self.scan_result.series_map:
                        series = self.scan_result.series_map[series_name]
                        target_paths.append(series.root_path)

            scope = f"{len(target_paths)} selected series"
        else:
            # Clean entire staging directory
            scope = "entire staging directory"

        # Check for sample files - if any extension contains "sample", show preview
        has_sample_pattern = any('sample' in ext.lower() for ext in extensions)

        if has_sample_pattern:
            # Scan for sample files first
            sample_files = self._find_sample_files(target_paths if target_paths else None)

            if sample_files:
                # Show preview dialog
                if not self._show_sample_preview_dialog(sample_files):
                    self.log("Cleanup cancelled by user after preview")
                    return
            else:
                self.log("No sample files found matching the patterns")
                QMessageBox.information(
                    self,
                    "No Sample Files Found",
                    "No sample files were found matching the selected patterns."
                )
                return
        else:
            # Normal confirmation for non-sample cleanups
            reply = QMessageBox.question(
                self,
                "Confirm Cleanup",
                f"Clean {scope} for extensions:\n{', '.join(sorted(extensions))}\n\n"
                f"Files will be moved to trash (if configured) or deleted permanently.\n\n"
                f"Continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                self.log("Cleanup cancelled by user")
                return

        # Execute cleanup with UndoRedoManager
        # Get trash directory
        trash_dir = self.settings.directories.trash
        if not trash_dir:
            QMessageBox.warning(
                self,
                "No Trash Directory",
                "Trash directory is not configured. Please set it in Settings."
            )
            return

        trash_path = Path(trash_dir)
        if not trash_path.exists():
            trash_path.mkdir(parents=True, exist_ok=True)

        # Scan for files to clean
        if not target_paths:
            staging = self.settings.directories.staging
            if not staging:
                QMessageBox.warning(self, "Error", "No staging directory configured")
                return
            target_paths = [FilePath(staging)]

        files_to_clean = []
        for path in target_paths:
            if not path.exists():
                continue
            found = self.file_system.scan_directory(path, extensions)
            files_to_clean.extend(found)

        if not files_to_clean:
            self.log(f"No files found with extensions: {', '.join(sorted(extensions))}")
            QMessageBox.information(
                self,
                "No Files Found",
                "No files matching the selected extensions were found."
            )
            return

        # Move files to trash
        from infrastructure.services.file_system_service import MoveOperation
        operations = []
        root_path = target_paths[0]

        for file_path in files_to_clean:
            # Calculate relative path from root
            relative = file_path.relative_to(root_path)
            if relative:
                dest = FilePath(trash_path / relative)
            else:
                # Fallback: use filename only
                dest = FilePath(trash_path / file_path.name)

            operations.append(MoveOperation(source=file_path, destination=dest))

        # Execute moves
        result = self.file_system.move_files(operations)

        if result.success:
            removed_file_paths = [str(op.source.path) for op in operations]
            removed_dirs = []

            # Remove empty folders if requested
            if remove_empty_folders:
                self.log("Scanning for empty folders...")
                removed_dirs = self._remove_empty_folders(target_paths)
                if removed_dirs:
                    self.log(f"Removed {len(removed_dirs)} empty folders")

            # Create cleanup command for undo/redo
            cleanup_cmd = CleanupCommand(removed_file_paths, trash_path, removed_dirs)

            # Register with UndoRedoManager
            self.undo_redo_manager.execute_command(cleanup_cmd)

            files_msg = f"{len(operations)} files"
            folders_msg = f", {len(removed_dirs)} empty folders" if removed_dirs else ""
            self.log(f"Cleanup complete: {files_msg}{folders_msg} moved to trash")

            QMessageBox.information(
                self,
                "Cleanup Complete",
                f"Successfully cleaned {files_msg}{folders_msg}"
            )

            # Refresh tree
            self.scan_media()
        else:
            error_msg = f"Failed to clean files: {len(result.errors)} errors"
            for error in result.errors[:5]:  # Show first 5 errors
                error_msg += f"\n  • {error}"
            if len(result.errors) > 5:
                error_msg += f"\n  ... and {len(result.errors) - 5} more"

            self.log(f"Cleanup failed: {error_msg}")
            QMessageBox.warning(self, "Cleanup Failed", error_msg)

    def _find_sample_files(self, target_paths: Optional[List] = None) -> List[Path]:
        """Find all sample files in target paths or staging directory

        Args:
            target_paths: Optional list of specific paths to search. If None, searches staging.

        Returns:
            List of Path objects for sample files
        """
        sample_files = []

        if target_paths:
            # Search in specific paths
            search_paths = target_paths
        else:
            # Search entire staging directory
            if not self.settings.directories.staging:
                return []
            search_paths = [Path(self.settings.directories.staging)]

        # Search for files containing "sample" in their name
        for search_path in search_paths:
            if isinstance(search_path, str):
                search_path = Path(search_path)

            if not search_path.exists():
                continue

            # Walk through directory recursively
            for file_path in search_path.rglob('*'):
                if file_path.is_file() and 'sample' in file_path.name.lower():
                    sample_files.append(file_path)

        return sorted(sample_files)

    def _show_sample_preview_dialog(self, sample_files: List[Path]) -> bool:
        """Show preview dialog for sample files before cleanup

        Args:
            sample_files: List of sample file paths

        Returns:
            True if user confirms deletion, False otherwise
        """
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QDialogButtonBox, QLabel

        dialog = QDialog(self)
        dialog.setWindowTitle("Sample Files Preview")
        dialog.setMinimumWidth(600)
        dialog.setMinimumHeight(400)

        layout = QVBoxLayout(dialog)

        # Header
        header = QLabel(f"Found {len(sample_files)} sample file(s) to delete:")
        header.setStyleSheet("font-weight: bold; font-size: 12pt; padding: 10px;")
        layout.addWidget(header)

        # List widget
        file_list = QListWidget()
        for file_path in sample_files:
            # Show relative path from staging if possible
            try:
                if self.settings.directories.staging:
                    rel_path = file_path.relative_to(self.settings.directories.staging)
                    display_path = str(rel_path)
                else:
                    display_path = str(file_path)
            except ValueError:
                display_path = str(file_path)

            file_list.addItem(display_path)

        layout.addWidget(file_list)

        # Warning label
        warning = QLabel("These files will be moved to trash or deleted permanently.")
        warning.setStyleSheet("color: #d9534f; padding: 10px;")
        layout.addWidget(warning)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        # Show dialog and return result
        result = dialog.exec()
        return result == QDialog.Accepted

    def _remove_empty_folders(self, target_paths: List[FilePath]) -> List[str]:
        """Remove empty folders from target paths

        Args:
            target_paths: Paths to scan for empty folders

        Returns:
            List of removed folder paths (as strings)
        """
        removed_dirs = []

        for target in target_paths:
            if not target.exists() or not target.path.is_dir():
                continue

            # Walk bottom-up to remove nested empty folders first
            for dirpath, dirnames, filenames in os.walk(str(target.path), topdown=False):
                # Skip if directory has files
                if filenames:
                    continue

                # Skip if directory has subdirectories (that weren't removed)
                current_path = Path(dirpath)
                if any(current_path.joinpath(d).exists() for d in dirnames):
                    continue

                # Skip the root target directory itself
                if current_path == target.path:
                    continue

                # Remove empty directory
                try:
                    current_path.rmdir()
                    removed_dirs.append(str(current_path))
                    self.log(f"  Removed empty folder: {current_path.name}")
                except OSError as e:
                    self.log(f"  Failed to remove {current_path.name}: {e}")

        return removed_dirs

    def log(self, message: str):
        """Log message to console"""
        self.console.append(message)
        print(message)  # Also print to stdout

    def closeEvent(self, event):
        """Handle window close event"""
        # Save cleanup panel settings
        self.settings.cleanup_ext_states = self.cleanup_panel.save_settings()

        # Save settings before closing
        self.settings_repo.save(self.settings)
        event.accept()

    def _connect_undo_redo_signals(self):
        """Connect UndoRedoManager signals to UI updates"""
        self.undo_redo_manager.undo_available.connect(self._on_undo_available_changed)
        self.undo_redo_manager.redo_available.connect(self._on_redo_available_changed)
        self.undo_redo_manager.history_changed.connect(self._on_history_changed)

    def _on_undo_available_changed(self, available: bool):
        """Handle undo availability change"""
        self.undo_btn.setEnabled(available)
        if available:
            desc = self.undo_redo_manager.get_undo_description()
            self.undo_btn.setToolTip(f"Undo: {desc}")
        else:
            self.undo_btn.setToolTip("Nothing to undo")

    def _on_redo_available_changed(self, available: bool):
        """Handle redo availability change"""
        self.redo_btn.setEnabled(available)
        if available:
            desc = self.undo_redo_manager.get_redo_description()
            self.redo_btn.setToolTip(f"Redo: {desc}")
        else:
            self.redo_btn.setToolTip("Nothing to redo")

    def _on_history_changed(self):
        """Handle history change event"""
        # Update button states based on current history
        self.undo_btn.setEnabled(self.undo_redo_manager.can_undo())
        self.redo_btn.setEnabled(self.undo_redo_manager.can_redo())

    def _setup_file_watcher(self):
        """Setup file system watcher for staging directory"""
        if not self.settings.directories.staging:
            # No staging directory configured yet
            self.file_watcher = None
            return

        self.file_watcher = QFileSystemWatcher()

        # Watch the staging directory
        staging_path = self.settings.directories.staging
        if staging_path:
            self.file_watcher.addPath(staging_path)
            self.log(f"Monitoring staging directory: {staging_path}")

        # Connect directory changed signal to refresh handler
        self.file_watcher.directoryChanged.connect(self._on_staging_changed)

    def _update_file_watcher(self):
        """Update file watcher when staging directory changes"""
        new_staging = self.settings.directories.staging

        # Remove old watcher if exists
        if hasattr(self, 'file_watcher') and self.file_watcher:
            # Get currently watched directories
            old_dirs = self.file_watcher.directories()
            if old_dirs:
                self.file_watcher.removePaths(old_dirs)

        # If no new staging directory, stop watching
        if not new_staging:
            return

        # Create new watcher if needed
        if not hasattr(self, 'file_watcher') or not self.file_watcher:
            self.file_watcher = QFileSystemWatcher()
            self.file_watcher.directoryChanged.connect(self._on_staging_changed)

        # Add new path
        self.file_watcher.addPath(new_staging)
        self.log(f"Now monitoring staging directory: {new_staging}")

    def _on_staging_changed(self, path: str):
        """Handle changes in staging directory

        Args:
            path: Path that changed
        """
        self.log(f"Staging directory changed, refreshing...")

        # Use a timer to debounce rapid changes (e.g., multiple files copied at once)
        if hasattr(self, '_refresh_timer'):
            self._refresh_timer.stop()

        self._refresh_timer = QTimer()
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.timeout.connect(self.scan_media)
        self._refresh_timer.start(1000)  # Wait 1 second after last change

    def _initial_scan(self):
        """Perform initial scan on application launch"""
        if self.settings.directories.staging:
            self.log("Performing initial scan...")
            self.scan_media()
        else:
            self.log("No staging directory configured. Please configure in Settings.")
