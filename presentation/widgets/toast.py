"""Toast notification widget"""
from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QPoint
from PySide6.QtGui import QFont


class Toast(QLabel):
    """A simple toast notification widget"""

    def __init__(self, parent, message: str, duration: int = 2000, color: str = "#323232"):
        """Initialize toast

        Args:
            parent: Parent widget
            message: Message to display
            duration: Duration in milliseconds (default 2000)
            color: Background color (default #323232 dark gray)
        """
        super().__init__(message, parent)

        # Style the toast with custom color
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 12px;
            }}
        """)

        self.setAlignment(Qt.AlignCenter)
        self.setMinimumWidth(200)
        self.adjustSize()

        # Position at bottom center of parent
        parent_rect = parent.rect()
        x = (parent_rect.width() - self.width()) // 2
        y = parent_rect.height() - self.height() - 50
        self.move(x, y)

        # Show the toast
        self.show()

        # Auto-hide after duration
        QTimer.singleShot(duration, self.hide)

    @staticmethod
    def show_toast(parent, message: str, duration: int = 2000, color: str = "#323232"):
        """Show a toast notification

        Args:
            parent: Parent widget
            message: Message to display
            duration: Duration in milliseconds
            color: Background color (default #323232 dark gray)
        """
        toast = Toast(parent, message, duration, color)
        return toast
