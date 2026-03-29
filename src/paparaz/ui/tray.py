"""System tray icon and menu."""

from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PySide6.QtCore import Signal, QObject


def create_default_icon() -> QIcon:
    """Create a simple default tray icon programmatically."""
    pix = QPixmap(32, 32)
    pix.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#E53935"))
    painter.setPen(QColor("#B71C1C"))
    painter.drawRoundedRect(2, 2, 28, 28, 6, 6)
    painter.setPen(QColor("#FFFFFF"))
    painter.setFont(QFont("Arial", 11, QFont.Weight.Bold))
    painter.drawText(pix.rect(), 0x0084, "Pz")  # AlignCenter
    painter.end()
    return QIcon(pix)


class TrayIcon(QObject):
    capture_requested = Signal()
    open_image_requested = Signal()
    settings_requested = Signal()
    quit_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._icon = QSystemTrayIcon(create_default_icon(), parent)
        self._icon.setToolTip("PapaRaZ - Screen Capture")
        self._build_menu()
        self._icon.activated.connect(self._on_activated)

    def _build_menu(self):
        menu = QMenu()

        capture_action = menu.addAction("Capture Screen")
        capture_action.triggered.connect(self.capture_requested.emit)

        open_action = menu.addAction("Open Image...")
        open_action.triggered.connect(self.open_image_requested.emit)

        menu.addSeparator()

        settings_action = menu.addAction("Settings")
        settings_action.triggered.connect(self.settings_requested.emit)

        menu.addSeparator()

        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(self.quit_requested.emit)

        self._icon.setContextMenu(menu)

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.capture_requested.emit()

    def show(self):
        self._icon.show()

    def show_message(self, title: str, message: str):
        self._icon.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 3000)
