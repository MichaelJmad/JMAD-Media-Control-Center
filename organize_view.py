from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QSplitter
)

class OrganizeView(QDialog):
    """
    A dialog for organizing media files.
    """

    def __init__(self, file_paths, parent=None):
        """
        Initializes the OrganizeView dialog.

        Args:
            file_paths (list): A list of file paths to be organized.
            parent (QWidget): The parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("Unified Organize View")
        self.setGeometry(150, 150, 1024, 600)

        self.file_paths = file_paths

        # --- Layouts ---
        main_layout = QVBoxLayout(self)
        top_layout = QHBoxLayout()
        bottom_layout = QHBoxLayout()

        # --- Widgets ---
        # Top section (Series confirmation)
        series_label = QLabel("Series Title:")
        self.series_search = QLineEdit()
        confirm_button = QPushButton("Confirm Series")

        top_layout.addWidget(series_label)
        top_layout.addWidget(self.series_search)
        top_layout.addWidget(confirm_button)

        # Bottom section (Source and Target panes)
        self.source_list = QListWidget()
        self.target_list = QListWidget()
        
        # Populate the source list with the initial files
        self.source_list.addItems(self.file_paths)

        splitter = QSplitter()
        splitter.addWidget(self.source_list)
        splitter.addWidget(self.target_list)
        splitter.setSizes([512, 512])

        bottom_layout.addWidget(splitter)

        # Dialog buttons
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)

        # --- Assemble Layout ---
        main_layout.addLayout(top_layout)
        main_layout.addLayout(bottom_layout)
        main_layout.addLayout(button_layout)
