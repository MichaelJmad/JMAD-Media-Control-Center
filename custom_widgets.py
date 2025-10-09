from PySide6.QtCore import Qt, QItemSelectionModel
from PySide6.QtWidgets import QTreeView

class CustomTreeView(QTreeView):
    """
    A custom QTreeView with specific selection behaviors.
    """

    def __init__(self, parent=None):
        """
        Initializes the CustomTreeView.
        """
        super().__init__(parent)

    def mousePressEvent(self, event):
        """
        Overrides the default mouse press event to implement custom
        selection logic.

        - Clicking an item toggles its selection state.
        - Clicking in a blank area clears the selection.
        """
        index = self.indexAt(event.pos())
        
        if index.isValid():
            # An item was clicked
            is_selected = self.selectionModel().isSelected(index)
            
            # Clear current selection before proceeding
            self.selectionModel().clear()
            
            if not is_selected:
                # If it wasn't selected before, select it now.
                # The flags ensure that this single action replaces the selection.
                self.selectionModel().select(index, QItemSelectionModel.Select)
        else:
            # No item was clicked, so clear the selection
            self.selectionModel().clear()
            
        # It's important to still call the base class implementation
        # to not break other functionalities like double-clicking to expand.
        # However, for this specific selection logic, we handle it fully.
        # super().mousePressEvent(event) # This might interfere, let's test without it first.