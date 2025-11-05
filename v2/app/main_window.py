

import logging
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QTextEdit, QTreeView, QFrame
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QAction, QStandardItemModel, QStandardItem

from .services.directory_monitor import DirectoryMonitor
from .services.state_manager import StateManager
from .services.settings_manager import SettingsManager
from app.views.organize_dialog import OrganizeDialog

class MainWindow(QMainWindow):
    file_system_event = Signal(str, str, str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("JMAD Media Tool V2")
        self.setGeometry(100, 100, 1400, 800)

        # Initialize settings manager
        self.settings_manager = SettingsManager("l:\\Projects\\JMAD-Media-Tool\\v2\\config\\settings.json")
        self.settings = self.settings_manager.load_settings()

        self._create_actions()
        self._create_toolbars()
        self._create_menus()

        # Create the main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # Create the main horizontal splitter
        main_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(main_splitter)

        # Left panel (Media Tree)
        left_panel = QFrame()
        left_layout = QVBoxLayout(left_panel)
        self.media_tree = QTreeView()
        left_layout.addWidget(self.media_tree)
        main_splitter.addWidget(left_panel)

        # Right panel (Info/Preview & Console)
        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)
        right_splitter = QSplitter(Qt.Vertical)
        right_layout.addWidget(right_splitter)

        # Info/Preview panel
        info_preview_panel = QTextEdit()
        right_splitter.addWidget(info_preview_panel)

        # Console panel
        console_panel = QTextEdit()
        right_splitter.addWidget(console_panel)

        # Add the right panel to the main splitter
        main_splitter.addWidget(right_panel)

        # Set splitter sizes
        main_splitter.setSizes([350, 1050])
        right_splitter.setSizes([600, 200])

        # Initialize services
        self.state_manager = StateManager("jmad_media_tool.db")
        self.state_manager.initialize_database()
        self.populate_media_tree()

        # Connect the file system event signal
        self.file_system_event.connect(self.handle_file_system_event)

        # Start the directory monitor in a separate thread
        staging_directory = self.settings_manager.get("staging_directory")
        if staging_directory:
            self.monitor_thread = QThread()
            self.directory_monitor = DirectoryMonitor(staging_directory, self.file_system_event.emit)
            self.directory_monitor.moveToThread(self.monitor_thread)
            self.monitor_thread.started.connect(self.directory_monitor.start)
            self.monitor_thread.start()

    def _create_actions(self):
        self.scan_action = QAction("Scan", self)
        self.settings_action = QAction("Settings", self)
        self.organize_action = QAction("Organize", self)
        self.organize_action.triggered.connect(self.open_organize_dialog)
        self.exit_action = QAction("Exit", self)
        self.exit_action.triggered.connect(self.close)

    def _create_toolbars(self):
        toolbar = self.addToolBar("Main Toolbar")
        toolbar.addAction(self.scan_action)
        toolbar.addAction(self.settings_action)
        toolbar.addAction(self.organize_action)

    def _create_menus(self):
        self.file_menu = self.menuBar().addMenu("&File")
        self.file_menu.addAction(self.scan_action)
        self.file_menu.addAction(self.settings_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.exit_action)

        self.tools_menu = self.menuBar().addMenu("&Tools")
        self.tools_menu.addAction(self.organize_action)

        self.help_menu = self.menuBar().addMenu("&Help")
        # Add help menu actions here

    def open_organize_dialog(self):
        dialog = OrganizeDialog(self, settings_manager=self.settings_manager, state_manager=self.state_manager)
        dialog.exec()

    def handle_file_system_event(self, event_type, src_path, dest_path=None):
        if event_type == "created":
            self.state_manager.add_media_item(src_path)
        elif event_type == "deleted":
            self.state_manager.delete_media_item(src_path)
        elif event_type == "moved":
            self.state_manager.move_media_item(src_path, dest_path)
        # TODO: Handle other event types (modified)
        self.populate_media_tree()

    def populate_media_tree(self):
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(['Path', 'Status'])
        items = self.state_manager.get_all_media_items()
        for item in items:
            path_item = QStandardItem(item[1])
            status_item = QStandardItem(item[2])
            model.appendRow([path_item, status_item])
        self.media_tree.setModel(model)

    def closeEvent(self, event):
        if hasattr(self, 'directory_monitor'):
            self.directory_monitor.stop()
            self.monitor_thread.quit()
            self.monitor_thread.wait()
        self.state_manager.close()
        event.accept()
