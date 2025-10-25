from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QListWidget,
    QStackedWidget,
    QWidget,
    QDialogButtonBox,
    QVBoxLayout
)
from .settings_manager import SettingsManager
from .settings_pages.general_page import GeneralSettingsPage
from .settings_pages.directories_page import DirectoriesPage

class SettingsDialog(QDialog):
    """The settings dialog for the application."""

    def __init__(self, settings_manager: SettingsManager, parent=None):
        """Initializes the SettingsDialog."""
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.setWindowTitle("Settings")
        self.setMinimumSize(800, 600)

        self.categories_list = QListWidget()
        self.stacked_widget = QStackedWidget()

        self._create_categories()
        self._create_pages()

        self.categories_list.currentRowChanged.connect(self.stacked_widget.setCurrentIndex)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        # Main layout
        main_layout = QHBoxLayout()
        main_layout.addWidget(self.categories_list, 1)
        main_layout.addWidget(self.stacked_widget, 4)

        # Overall layout with buttons
        layout = QVBoxLayout()
        layout.addLayout(main_layout)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

    def _create_categories(self):
        """Creates the categories list."""
        self.categories_list.addItems([
            "General",
            "Directories",
            "Renaming",
            "Metadata",
            "Libraries",
            "Cleaning",
            "Trash Bin",
            "Appearance",
            "Hotkeys",
            "Performance"
        ])
        self.categories_list.setCurrentRow(0)

    def _create_pages(self):
        """Creates the pages for the settings dialog."""
        self.stacked_widget.addWidget(GeneralSettingsPage(self.settings_manager))
        self.stacked_widget.addWidget(DirectoriesPage(self.settings_manager))

        # Add placeholder pages for the rest
        for i in range(2, self.categories_list.count()):
            page = QWidget()
            self.stacked_widget.addWidget(page)

if __name__ == '__main__':
    import sys
    from PySide6.QtWidgets import QApplication
    from pathlib import Path
    # Create a dummy SettingsManager for testing
    config_dir = Path(__file__).parent.parent / 'config'
    settings_path = config_dir / 'settings.json'
    settings_manager = SettingsManager(settings_path)

    app = QApplication(sys.argv)
    dialog = SettingsDialog(settings_manager)
    dialog.exec()