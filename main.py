import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFileSystemModel,
    QMainWindow,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from custom_widgets import CustomTreeView
from organize_view import OrganizeView

class MainWindow(QMainWindow):
    """
    The main window for the JMAD Media Tool application.
    """

    def __init__(self):
        """
        Initializes the main window and sets up the UI layout.
        """
        super().__init__()
        self.setWindowTitle("JMAD Media Tool V2")
        self.setGeometry(100, 100, 1280, 720)  # Set initial size

        # Create the central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- Create Toolbar ---
        toolbar = self.addToolBar("Main Toolbar")
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        
        scan_action = QAction(QIcon.fromTheme("document-open"), "Scan Staging", self)
        scan_action.triggered.connect(self.scan_directory)
        toolbar.addAction(scan_action)

        toolbar.addSeparator()

        self.organize_action = QAction(QIcon.fromTheme("dialog-ok-apply"), "Organize", self)
        self.organize_action.triggered.connect(self.open_organize_view)
        self.organize_action.setEnabled(False) # Disable by default
        toolbar.addAction(self.organize_action)

        # --- Create Panels ---
        self.media_tree = CustomTreeView()
        self.info_preview = QTextEdit("Info/Preview Panel")
        self.console = QTextEdit("Console Panel")

        # --- Create Layout ---
        # Right-side splitter (Info vs. Console)
        right_splitter = QSplitter(Qt.Vertical)
        right_splitter.addWidget(self.info_preview)
        right_splitter.addWidget(self.console)
        right_splitter.setSizes([600, 200]) # 75% / 25% split

        # Main splitter (Media Tree vs. Right Side)
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.addWidget(self.media_tree)
        main_splitter.addWidget(right_splitter)
        main_splitter.setSizes([640, 640]) # 50% / 50% split

        # Add the main splitter to the main layout
        main_layout.addWidget(main_splitter)


    def update_actions(self):
        """
        Updates the state of actions based on the current selection.
        """
        has_selection = bool(self.media_tree.selectionModel().selectedIndexes())
        self.organize_action.setEnabled(has_selection)

    def open_organize_view(self):
        """
        Opens the Organize View dialog with the selected file paths.
        """
        selected_indexes = self.media_tree.selectionModel().selectedIndexes()
        if not selected_indexes:
            return

        file_paths = []
        for index in selected_indexes:
            if index.column() == 0: # Only process the first column
                file_paths.append(self.fs_model.filePath(index))
        
        if file_paths:
            organize_dialog = OrganizeView(file_paths, self)
            organize_dialog.exec()

    def scan_directory(self):
        """
        Opens a dialog to select a directory and displays its contents in the media_tree.
        """
        path = QFileDialog.getExistingDirectory(self, "Select Staging Directory")
        if path:
            self.console.append(f"Selected staging directory: {path}")
            # Create a file system model
            self.fs_model = QFileSystemModel()
            self.fs_model.setRootPath(path)
            
            # Set the model for the tree view and set the root index
            self.media_tree.setModel(self.fs_model)
            self.media_tree.setRootIndex(self.fs_model.index(path))

            # Connect signals now that the model is set
            self.media_tree.selectionModel().selectionChanged.connect(self.update_actions)


def main():
    """
    The main entry point for the application.
    """
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
