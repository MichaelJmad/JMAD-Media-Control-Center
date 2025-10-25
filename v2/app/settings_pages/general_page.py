from PySide6.QtWidgets import QWidget, QVBoxLayout, QCheckBox, QGroupBox, QFormLayout
from ..settings_manager import SettingsManager

class GeneralSettingsPage(QWidget):
    """The 'General' settings page."""

    def __init__(self, settings_manager: SettingsManager, parent=None):
        """Initializes the GeneralSettingsPage."""
        super().__init__(parent)
        self.settings_manager = settings_manager

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # System Behavior Group
        system_group = QGroupBox("System Behavior")
        system_layout = QFormLayout(system_group)

        self.start_with_windows_checkbox = QCheckBox("Start with Windows")
        self.minimize_to_tray_checkbox = QCheckBox("Minimize to System Tray")
        self.show_notifications_checkbox = QCheckBox("Show notification pop-ups for background tasks")

        system_layout.addRow(self.start_with_windows_checkbox)
        system_layout.addRow(self.minimize_to_tray_checkbox)
        system_layout.addRow(self.show_notifications_checkbox)

        layout.addWidget(system_group)
        layout.addStretch()

        self.load_settings()
        self.connect_signals()

    def load_settings(self):
        """Loads the settings from the SettingsManager and updates the UI."""
        self.start_with_windows_checkbox.setChecked(self.settings_manager.get("general.start_with_windows", False))
        self.minimize_to_tray_checkbox.setChecked(self.settings_manager.get("general.minimize_to_tray", False))
        self.show_notifications_checkbox.setChecked(self.settings_manager.get("general.show_notifications", True))

    def connect_signals(self):
        """Connects the UI element signals to the settings manager."""
        self.start_with_windows_checkbox.stateChanged.connect(
            lambda state: self.settings_manager.set("general.start_with_windows", state == 2)
        )
        self.minimize_to_tray_checkbox.stateChanged.connect(
            lambda state: self.settings_manager.set("general.minimize_to_tray", state == 2)
        )
        self.show_notifications_checkbox.stateChanged.connect(
            lambda state: self.settings_manager.set("general.show_notifications", state == 2)
        )
