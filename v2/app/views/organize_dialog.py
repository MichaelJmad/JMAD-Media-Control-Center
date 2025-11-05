
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QSplitter, QTreeView, QFrame, QPushButton, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItemModel, QStandardItem

from ..services.metadata_service import MetadataService

class OrganizeDialog(QDialog):
    def __init__(self, parent=None, settings_manager=None, state_manager=None):
        super().__init__(parent)
        self.setWindowTitle("Organize Media")
        self.setGeometry(200, 200, 1200, 800)

        self.settings_manager = settings_manager
        self.state_manager = state_manager
        tmdb_api_key = self.settings_manager.get("tmdb_api_key")
        self.metadata_service = MetadataService(api_key=tmdb_api_key)

        main_layout = QVBoxLayout(self)

        # Top Toolbar
        toolbar = QFrame()
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.addWidget(QLabel("Series Search:"))
        self.search_bar = QLineEdit()
        toolbar_layout.addWidget(self.search_bar)
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search_series)
        toolbar_layout.addWidget(self.search_button)
        main_layout.addWidget(toolbar)

        # Main Content
        main_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(main_splitter)

        # Source Pane
        source_panel = QFrame()
        source_layout = QVBoxLayout(source_panel)
        source_layout.addWidget(QLabel("Source Files"))
        self.source_tree = QTreeView()
        source_layout.addWidget(self.source_tree)
        main_splitter.addWidget(source_panel)

        # Action Pane
        action_panel = QFrame()
        action_layout = QVBoxLayout(action_panel)
        action_layout.addWidget(QPushButton("-> Set as Season"))
        action_layout.addWidget(QPushButton("-> Set as Movie"))
        action_layout.addWidget(QPushButton("-> Set as Special"))
        action_layout.addWidget(QPushButton("-> Set as Custom"))
        action_layout.addStretch()
        action_layout.addWidget(QPushButton("Auto-Sort"))
        action_layout.addStretch()
        action_layout.addWidget(QPushButton("Undo"))
        action_layout.addWidget(QPushButton("Redo"))
        action_layout.addStretch()
        action_layout.addWidget(QPushButton("<- Remove"))
        main_splitter.addWidget(action_panel)

        # Target Pane
        target_panel = QFrame()
        target_layout = QVBoxLayout(target_panel)
        target_layout.addWidget(QLabel("Target Structure"))
        self.target_tree = QTreeView()
        target_layout.addWidget(self.target_tree)
        main_splitter.addWidget(target_panel)

        # Bottom Buttons
        button_layout = QHBoxLayout()
        main_layout.addLayout(button_layout)
        button_layout.addStretch()
        self.process_button = QPushButton("Process Files")
        button_layout.addWidget(self.process_button)
        self.cancel_button = QPushButton("Cancel")
        button_layout.addWidget(self.cancel_button)
        self.cancel_button.clicked.connect(self.reject)

        self.populate_source_tree()

    def populate_source_tree(self):
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(['Path', 'Status'])
        items = self.state_manager.get_all_media_items()
        for item in items:
            path_item = QStandardItem(item[1])
            status_item = QStandardItem(item[2])
            model.appendRow([path_item, status_item])
        self.source_tree.setModel(model)

    def search_series(self):
        query = self.search_bar.text()
        if not query:
            QMessageBox.warning(self, "Search Error", "Please enter a series name to search.")
            return

        results = self.metadata_service.search_series(query)
        if not results:
            QMessageBox.information(self, "Search Results", "No series found for your query.")
            return

        # Display results in a list for user selection
        self.show_search_results(results)

    def show_search_results(self, results):
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Series")
        dialog_layout = QVBoxLayout(dialog)

        list_widget = QListWidget()
        for item in results:
            list_widget.addItem(f"{item.get('name')} ({item.get('first_air_date', '')[:4]})")
        dialog_layout.addWidget(list_widget)

        select_button = QPushButton("Select")
        select_button.clicked.connect(dialog.accept)
        dialog_layout.addWidget(select_button)

        if dialog.exec() == QDialog.Accepted:
            selected_item = list_widget.currentItem()
            if selected_item:
                # TODO: Process selected series (e.g., get details, update UI)
                QMessageBox.information(self, "Selected Series", f"You selected: {selected_item.text()}")

    def search_series(self):
        query = self.search_bar.text()
        if not query:
            QMessageBox.warning(self, "Search Error", "Please enter a series name to search.")
            return

        results = self.metadata_service.search_series(query)
        if not results:
            QMessageBox.information(self, "Search Results", "No series found for your query.")
            return

        # Display results in a list for user selection
        self.show_search_results(results)

    def show_search_results(self, results):
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Series")
        dialog_layout = QVBoxLayout(dialog)

        list_widget = QListWidget()
        for item in results:
            list_widget.addItem(f"{item.get('name')} ({item.get('first_air_date', '')[:4]})")
        dialog_layout.addWidget(list_widget)

        select_button = QPushButton("Select")
        select_button.clicked.connect(dialog.accept)
        dialog_layout.addWidget(select_button)

        if dialog.exec() == QDialog.Accepted:
            selected_item = list_widget.currentItem()
            if selected_item:
                # TODO: Process selected series (e.g., get details, update UI)
                QMessageBox.information(self, "Selected Series", f"You selected: {selected_item.text()}")
