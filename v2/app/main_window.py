from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow,
    QApplication,
    QWidget,
    QVBoxLayout,
    QTextEdit,
    QTreeView,
    QSplitter,
    QToolBar
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from .settings_dialog import SettingsDialog
from .settings_manager import SettingsManager

class MainWindow(QMainWindow):
    """The main application window."""

    def __init__(self):
        """Initializes the MainWindow."""
        super().__init__()
        self.setWindowTitle("JMAD Media Tool V2")
        self.setGeometry(100, 100, 1200, 800)

        config_dir = Path(__file__).parent.parent / 'config'
        settings_path = config_dir / 'settings.json'
        self.settings_manager = SettingsManager(settings_path)

        self._create_toolbar()
        self._create_main_layout()

    def _create_toolbar(self):
        """Creates the main toolbar."""
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)

        scan_action = QAction("Scan", self)
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self._open_settings_dialog)
        organize_action = QAction("Organize", self)
        clean_action = QAction("Clean", self)

        toolbar.addAction(scan_action)
        toolbar.addAction(settings_action)
        toolbar.addSeparator()
        toolbar.addAction(organize_action)
        toolbar.addAction(clean_action)

    def _create_main_layout(self):
        """Creates the main three-panel layout."""
        # Main horizontal splitter (Left and Right panels)
        main_splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(main_splitter)

        # Left Panel: Media Tree
        media_tree_view = QTreeView()
        main_splitter.addWidget(media_tree_view)

        # Right Panel: Vertical splitter for Info/Preview and Console
        right_splitter = QSplitter(Qt.Vertical)

        # Top Right: Info/Preview Panel
        info_preview_panel = QTextEdit("Info/Preview Panel")
        right_splitter.addWidget(info_preview_panel)

        # Bottom Right: Console Panel
        console_panel = QTextEdit("Console Panel")
        right_splitter.addWidget(console_panel)

        # Add the right splitter to the main splitter
        main_splitter.addWidget(right_splitter)

        # Set initial splitter sizes
        main_splitter.setSizes([600, 600])  # 50/50 split
        right_splitter.setSizes([600, 200])  # Info panel 600px, console 200px

    def _open_settings_dialog(self):
        """Opens the settings dialog."""
        dialog = SettingsDialog(self.settings_manager, self)
        dialog.exec()

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())