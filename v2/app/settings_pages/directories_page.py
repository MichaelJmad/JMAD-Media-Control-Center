from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QGroupBox,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QTableWidget,
    QHeaderView,
    QFileDialog,
    QTableWidgetItem
)
from ..settings_manager import SettingsManager

class DirectoriesPage(QWidget):
    """The 'Directories' settings page."""

    def __init__(self, settings_manager: SettingsManager, parent=None):
        """Initializes the DirectoriesPage."""
        super().__init__(parent)
        self.settings_manager = settings_manager

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Staging Directory Group
        staging_group = QGroupBox("Staging Directory")
        staging_layout = QHBoxLayout(staging_group)

        self.staging_path_edit = QLineEdit()
        self.browse_staging_button = QPushButton("Browse...")
        staging_layout.addWidget(self.staging_path_edit)
        staging_layout.addWidget(self.browse_staging_button)

        # Library Destinations Group
        library_group = QGroupBox("Library Destinations")
        library_layout = QVBoxLayout(library_group)

        self.library_table = QTableWidget()
        self.library_table.setColumnCount(2)
        self.library_table.setHorizontalHeaderLabels(["Name", "Path"])
        self.library_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.library_table.horizontalHeader().setStretchLastSection(True)
        library_layout.addWidget(self.library_table)

        library_button_layout = QHBoxLayout()
        self.add_library_button = QPushButton("Add")
        self.remove_library_button = QPushButton("Remove")
        library_button_layout.addStretch()
        library_button_layout.addWidget(self.add_library_button)
        library_button_layout.addWidget(self.remove_library_button)
        library_layout.addLayout(library_button_layout)

        layout.addWidget(staging_group)
        layout.addWidget(library_group)
        layout.addStretch()

        self.load_settings()
        self.connect_signals()

    def load_settings(self):
        """Loads the settings from the SettingsManager and updates the UI."""
        self.staging_path_edit.setText(self.settings_manager.get("directories.staging", ""))
        
        libraries = self.settings_manager.get("directories.libraries", [])
        self.library_table.setRowCount(len(libraries))
        for i, lib in enumerate(libraries):
            self.library_table.setItem(i, 0, QTableWidgetItem(lib.get("name", "")))
            self.library_table.setItem(i, 1, QTableWidgetItem(lib.get("path", "")))


    def connect_signals(self):
        """Connects the UI element signals to the settings manager."""
        self.browse_staging_button.clicked.connect(self.browse_staging)
        self.staging_path_edit.textChanged.connect(
            lambda text: self.settings_manager.set("directories.staging", text)
        )
        # Signals for library table will be connected later

    def browse_staging(self):
        """Opens a dialog to browse for the staging directory."""
        directory = QFileDialog.getExistingDirectory(self, "Select Staging Directory")
        if directory:
            self.staging_path_edit.setText(directory)
