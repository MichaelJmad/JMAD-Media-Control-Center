import os
import re
import json
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeView,
    QPushButton, QLineEdit, QDialogButtonBox, QAbstractItemView, QLabel,
    QInputDialog
)
from PySide6.QtGui import QStandardItemModel, QStandardItem

class OrganizeDialogNew(QDialog):
    def __init__(self, selected_items, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Organize Media")
        self.setGeometry(150, 150, 1200, 700)

        # Data
        self.source_file_paths = selected_items
        self.confirmed_series_title = None

        # Main Layout
        main_layout = QVBoxLayout(self)

        # Top Toolbar & Title
        top_layout = QVBoxLayout()
        top_toolbar_layout = QHBoxLayout()
        self.series_search_input = QLineEdit()
        self.series_search_input.setPlaceholderText("Search for Series Title...")
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.on_search_clicked)
        top_toolbar_layout.addWidget(self.series_search_input)
        top_toolbar_layout.addWidget(self.search_button)
        self.confirmed_title_label = QLabel("Confirmed Title: None")
        top_layout.addLayout(top_toolbar_layout)
        top_layout.addWidget(self.confirmed_title_label)
        main_layout.addLayout(top_layout)

        # Panes Layout
        panes_layout = QHBoxLayout()
        
        # Source Pane
        self.source_tree = QTreeView()
        self.source_tree_model = QStandardItemModel()
        self.source_tree.setModel(self.source_tree_model)
        self.source_tree.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.source_tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        panes_layout.addWidget(self.source_tree)

        # Action Pane
        self._setup_action_pane(panes_layout)

        # Target Pane
        self.target_tree = QTreeView()
        self.target_tree_model = QStandardItemModel()
        self.target_tree.setModel(self.target_tree_model)
        self.target_tree_model.setHorizontalHeaderLabels(['Original Name', 'New Name'])
        self.target_tree.setEditTriggers(QAbstractItemView.AnyKeyPressed | QAbstractItemView.DoubleClicked)
        panes_layout.addWidget(self.target_tree)

        main_layout.addLayout(panes_layout)

        # Bottom Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Ok).setText("Process Files")
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        self.populate_source_tree()
        self.guess_and_set_series_title()

    def _setup_action_pane(self, parent_layout):
        action_pane_layout = QVBoxLayout()
        self.set_season_button = QPushButton("-> Set as Season")
        self.set_season_button.clicked.connect(self.on_set_as_season)
        self.set_movie_button = QPushButton("-> Set as Movie")
        self.set_special_button = QPushButton("-> Set as Special")
        self.set_custom_button = QPushButton("-> Set as Custom")
        self.auto_sort_button = QPushButton("Auto-Sort")
        self.undo_button = QPushButton("Undo")
        self.redo_button = QPushButton("Redo")
        self.remove_button = QPushButton("<- Remove")

        self.undo_button.setEnabled(False)
        self.redo_button.setEnabled(False)

        action_pane_layout.addWidget(self.set_season_button)
        action_pane_layout.addWidget(self.set_movie_button)
        action_pane_layout.addWidget(self.set_special_button)
        action_pane_layout.addWidget(self.set_custom_button)
        action_pane_layout.addStretch()
        action_pane_layout.addWidget(self.auto_sort_button)
        action_pane_layout.addStretch()
        action_pane_layout.addWidget(self.undo_button)
        action_pane_layout.addWidget(self.redo_button)
        action_pane_layout.addStretch()
        action_pane_layout.addWidget(self.remove_button)
        parent_layout.addLayout(action_pane_layout)

    def _guess_episode_number(self, filename):
        match = re.search(r'[sS]\d+[eE](\d+)', filename) or re.search(r' - (\d+)', filename) or re.search(r'(\d{2,3})', filename)
        return f"{int(match.group(1)):02d}" if match else "01"

    def populate_source_tree(self):
        self.source_tree_model.clear()
        self.source_tree_model.setHorizontalHeaderLabels(['Original Files'])
        if not self.source_file_paths: return

        common_path = os.path.dirname(os.path.commonprefix(self.source_file_paths))
        root_item = self.source_tree_model.invisibleRootItem()
        folder_items = {common_path: root_item}

        for path in sorted(self.source_file_paths):
            parent_path = os.path.dirname(path)
            parent_item = root_item

            if parent_path in folder_items:
                parent_item = folder_items[parent_path]
            else:
                parts = os.path.relpath(parent_path, common_path).replace('\\', '/').split('/')
                current_item = root_item
                built_path = common_path
                for part in parts:
                    if part == '.': continue
                    built_path = os.path.join(built_path, part)
                    if built_path in folder_items:
                        current_item = folder_items[built_path]
                    else:
                        new_folder = QStandardItem(part)
                        new_folder.setData(built_path, Qt.UserRole)
                        current_item.appendRow(new_folder)
                        folder_items[built_path] = new_folder
                        current_item = new_folder
                parent_item = current_item

            file_item = QStandardItem(os.path.basename(path))
            file_item.setData(path, Qt.UserRole)
            parent_item.appendRow(file_item)

        self.source_tree.expandAll()

    def on_search_clicked(self):
        search_text = self.series_search_input.text()
        self.confirmed_series_title = search_text
        self.confirmed_title_label.setText(f"Confirmed Title: {self.confirmed_series_title}")

    def on_set_as_season(self):
        # This is the full implementation, temporarily disabled for stability
        print("Set as Season button clicked - functionality pending.")
        pass

    def guess_and_set_series_title(self):
        if not self.source_file_paths: return

        try:
            with open('v2/config/patterns.json', 'r') as f:
                patterns = json.load(f)
            cleaning_patterns = patterns.get("title_cleaning_patterns", [])
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"ERROR loading v2/config/patterns.json: {e}")
            cleaning_patterns = []

        first_path = self.source_file_paths[0]
        parent_dir = os.path.dirname(first_path)
        guess = os.path.basename(parent_dir)

        if guess.lower() == 'staging' and os.path.isfile(first_path):
            base = os.path.basename(first_path)
            guess = os.path.splitext(base)[0]

        cleaned_guess = guess
        for pattern in cleaning_patterns:
            cleaned_guess = re.sub(pattern, ' ', cleaned_guess, flags=re.IGNORECASE).strip()

        self.series_search_input.setText(cleaned_guess)