#!/usr/bin/env python3
"""
JMAD Media Tool - Refactored V1
Main application entry point
"""
import sys
from PySide6.QtWidgets import QApplication
from presentation.main_window import MainWindow


def main():
    """Application entry point"""
    app = QApplication(sys.argv)

    # Set application metadata
    app.setApplicationName("JMAD Media Tool")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("JMAD")

    # TODO: Load and apply stylesheet
    # app.setStyleSheet(open("presentation/resources/styles.qss").read())

    # Create and show main window
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
