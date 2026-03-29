"""Always-on-top floating pin window for screenshots."""

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QMenu
from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtGui import QPixmap, QPainter, QAction


class PinWindow(QWidget):
    """Frameless, always-on-top window displaying a pinned screenshot."""

    closed = Signal()

    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self._pixmap = pixmap
        self._drag_pos = QPoint()
        self._scale = 1.0

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)

        self._label = QLabel(self)
        self._label.setPixmap(pixmap)
        self._label.setScaledContents(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self._label)

        self.setStyleSheet("QWidget { background: #1a1a2e; border: 2px solid #740096; }")
        self.resize(pixmap.width() + 4, pixmap.height() + 4)

    def _context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: #2a2a3e; color: #ddd; border: 1px solid #444; }
            QMenu::item:selected { background: #740096; }
        """)

        scale_menu = menu.addMenu("Scale")
        for pct in [50, 75, 100, 150, 200]:
            act = scale_menu.addAction(f"{pct}%")
            act.triggered.connect(lambda checked, s=pct / 100: self._set_scale(s))

        menu.addSeparator()
        close_act = menu.addAction("Close")
        close_act.triggered.connect(self.close)
        menu.exec(self.mapToGlobal(pos))

    def _set_scale(self, scale: float):
        self._scale = scale
        w = int(self._pixmap.width() * scale) + 4
        h = int(self._pixmap.height() * scale) + 4
        self.resize(w, h)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)
