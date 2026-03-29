"""System tray icon and menu with recent captures and delay capture."""

from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QAction
from PySide6.QtCore import Signal, QObject


def create_default_icon() -> QIcon:
    pix = QPixmap(32, 32)
    pix.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#E53935"))
    painter.setPen(QColor("#B71C1C"))
    painter.drawRoundedRect(2, 2, 28, 28, 6, 6)
    painter.setPen(QColor("#FFFFFF"))
    painter.setFont(QFont("Arial", 11, QFont.Weight.Bold))
    painter.drawText(pix.rect(), 0x0084, "Pz")
    painter.end()
    return QIcon(pix)


class TrayIcon(QObject):
    capture_requested = Signal()
    delay_capture_requested = Signal(int)  # delay in seconds
    open_image_requested = Signal()
    open_recent_requested = Signal(str)  # file path
    settings_requested = Signal()
    quit_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._icon = QSystemTrayIcon(create_default_icon(), parent)
        self._icon.setToolTip("PapaRaZ - Screen Capture")
        self._recent_paths: list[str] = []
        self._build_menu()
        self._icon.activated.connect(self._on_activated)

    def _build_menu(self):
        self._menu = QMenu()
        self._menu.setStyleSheet("""
            QMenu { background: #2a2a3e; color: #ddd; border: 1px solid #444; }
            QMenu::item:selected { background: #740096; }
            QMenu::separator { background: #444; height: 1px; }
        """)

        capture_action = self._menu.addAction("Capture Screen")
        capture_action.triggered.connect(self.capture_requested.emit)

        # Delay capture submenu
        delay_menu = self._menu.addMenu("Delay Capture")
        for sec in [3, 5, 10]:
            act = delay_menu.addAction(f"{sec} seconds")
            act.triggered.connect(lambda checked, s=sec: self.delay_capture_requested.emit(s))

        open_action = self._menu.addAction("Open Image...")
        open_action.triggered.connect(self.open_image_requested.emit)

        # Recent captures submenu
        self._recent_menu = self._menu.addMenu("Recent Captures")
        self._recent_menu.setEnabled(False)

        self._menu.addSeparator()

        settings_action = self._menu.addAction("Settings")
        settings_action.triggered.connect(self.settings_requested.emit)

        self._menu.addSeparator()

        quit_action = self._menu.addAction("Quit")
        quit_action.triggered.connect(self.quit_requested.emit)

        self._icon.setContextMenu(self._menu)

    def update_recent(self, paths: list[str]):
        """Update the recent captures submenu."""
        self._recent_paths = paths
        self._recent_menu.clear()
        if not paths:
            self._recent_menu.setEnabled(False)
            return
        self._recent_menu.setEnabled(True)
        for path in paths[:10]:
            from pathlib import Path
            name = Path(path).name
            act = self._recent_menu.addAction(name)
            act.setToolTip(path)
            act.triggered.connect(lambda checked, p=path: self.open_recent_requested.emit(p))

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.capture_requested.emit()

    def show(self):
        self._icon.show()

    def show_message(self, title: str, message: str):
        self._icon.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 3000)
