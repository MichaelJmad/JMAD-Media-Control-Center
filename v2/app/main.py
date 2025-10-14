import sys
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QSplitter, QTextEdit, 
    QTreeView, QAbstractItemView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QStandardItemModel, QStandardItem

# To run this script directly, ensure the project root is in the Python path.
# This is typically done by running as a module: `python -m v2.app.main`
from v2.app.database.database_manager import DatabaseManager
from v2.app.services.directory_monitor import DirectoryMonitor
from v2.app.services.state_manager import StateManager
from v2.app.ui.organize_dialog_new import OrganizeDialogNew

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JMAD Media Tool V2")
        self.setGeometry(100, 100, 1200, 800)

        # Initialize Database, place it in the v2 folder
        self.db_manager = DatabaseManager(db_path='v2/jmad_media_tool.db')

        # Initialize State Manager
        self.state_manager = StateManager(self.db_manager)

        # Initialize Directory Monitor for the 'staging' folder in the root
        self.staging_path = "staging"
        if not os.path.exists(self.staging_path):
            os.makedirs(self.staging_path)
        self.directory_monitor = DirectoryMonitor(self.staging_path, self.state_manager)
        self.directory_monitor.start()

        # Create the main horizontal splitter
        main_splitter = QSplitter(Qt.Horizontal)

        # Left panel (Media Tree)
        self.media_tree_view = QTreeView()
        self.media_tree_model = QStandardItemModel()
        self.media_tree_view.setModel(self.media_tree_model)
        self.media_tree_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.media_tree_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        main_splitter.addWidget(self.media_tree_view)

        # Right panel (vertical splitter)
        right_splitter = QSplitter(Qt.Vertical)

        # Info/Preview panel
        info_preview_panel = QLabel("Info/Preview Panel")
        info_preview_panel.setAlignment(Qt.AlignCenter)
        right_splitter.addWidget(info_preview_panel)

        # Console panel
        console_panel = QTextEdit()
        console_panel.setReadOnly(True)
        console_panel.setPlaceholderText("Console output...")
        right_splitter.addWidget(console_panel)

        # Set initial sizes for the right splitter
        right_splitter.setSizes([600, 200])

        main_splitter.addWidget(right_splitter)

        # Set initial sizes for the main splitter to be 50/50
        main_splitter.setSizes([600, 600])

        self.setCentralWidget(main_splitter)

        # Create Toolbar
        toolbar = self.addToolBar("Main Toolbar")
        organize_action = QAction("Organize", self)
        organize_action.triggered.connect(self.open_organize_dialog)
        toolbar.addAction(organize_action)
        toolbar.addAction("Scan Staging Directory")
        refresh_action = QAction("Refresh", self)
        refresh_action.triggered.connect(self.populate_media_tree)
        toolbar.addAction(refresh_action)
        toolbar.addAction("Settings")
        toolbar.addAction("Tools")
        
        # Add a quit button to the toolbar
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.close)
        toolbar.addAction(quit_action)

        # Initial population of the tree view
        self.populate_media_tree()

    def open_organize_dialog(self):
        """Opens the organize dialog with the currently selected files."""
        selected_indexes = self.media_tree_view.selectionModel().selectedIndexes()
        if not selected_indexes:
            print("No items selected.") # Later, show this in the status bar
            return

        # We only care about the first column (path) and want unique paths
        selected_paths = set()
        for index in selected_indexes:
            if index.column() == 0:
                full_path = index.data(Qt.UserRole)
                if full_path:
                    selected_paths.add(full_path)
        
        if not selected_paths:
            print("No valid file/folder paths selected.")
            return

        # Expand folders to get all file paths
        paths_to_process = set()
        for path in selected_paths:
            if os.path.isdir(path):
                for root, _, files in os.walk(path):
                    for name in files:
                        file_path = os.path.join(root, name)
                        paths_to_process.add(file_path)
            elif os.path.isfile(path):
                paths_to_process.add(path)

        if not paths_to_process:
            print("Selection contains no processable files.")
            return

        dialog = OrganizeDialogNew(list(paths_to_process), self)
        dialog.exec()


    def populate_media_tree(self):
        """Clears and repopulates the media tree view from the database with a hierarchical structure."""
        self.media_tree_model.clear()
        self.media_tree_model.setHorizontalHeaderLabels(['Path', 'Status'])
        
        root_node = self.media_tree_model.invisibleRootItem()
        
        items = self.db_manager.get_all_media_items()
        
        for path, status in items:
            # Store the original full path
            full_path = path
            
            # Normalize path separators for consistent splitting
            normalized_path = path.replace('\\', '/')
            staging_path_norm = self.staging_path.replace('\\', '/')

            # Remove the staging path prefix
            if normalized_path.startswith(staging_path_norm):
                clean_path = normalized_path[len(staging_path_norm):]
            else:
                clean_path = normalized_path
            
            # Split the remaining path into parts, filtering out empty parts
            path_parts = [part for part in clean_path.split('/') if part]

            parent_item = root_node
            
            # Traverse the path, creating folder items as needed
            current_path_so_far = self.staging_path
            for part in path_parts[:-1]:
                current_path_so_far = os.path.join(current_path_so_far, part)
                next_item = None
                for i in range(parent_item.rowCount()):
                    child = parent_item.child(i)
                    if child and child.text() == part:
                        next_item = child
                        break
                
                if next_item is None:
                    new_folder_item = QStandardItem(part)
                    new_folder_item.setData(current_path_so_far, Qt.UserRole) # Store full path
                    parent_item.appendRow(new_folder_item)
                    next_item = new_folder_item
                
                parent_item = next_item

            # Add the file item
            file_item = QStandardItem(path_parts[-1])
            file_item.setData(full_path, Qt.UserRole) # Store full path
            status_item = QStandardItem(status)
            parent_item.appendRow([file_item, status_item])
            
        self.media_tree_view.resizeColumnToContents(0)

    def closeEvent(self, event):
        self.directory_monitor.stop()
        self.db_manager.close()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())