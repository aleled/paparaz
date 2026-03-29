"""Always-on-top floating pin window with resume editing, custom scale, ESC close."""

from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QMenu, QInputDialog, QApplication,
)
from PySide6.QtCore import Qt, QPoint, Signal, QSize
from PySide6.QtGui import QPixmap, QPainter, QKeyEvent, QWheelEvent, QShortcut, QKeySequence

MENU_STYLE = """
    QMenu { background: #2a2a3e; color: #ddd; border: 1px solid #444; padding: 4px; }
    QMenu::item { padding: 4px 20px; border-radius: 3px; }
    QMenu::item:selected { background: #740096; }
    QMenu::separator { background: #444; height: 1px; margin: 4px 8px; }
"""

INPUT_STYLE = """
    QInputDialog { background: #1a1a2e; color: #ddd; }
    QLabel { color: #ddd; }
    QLineEdit { background: #2a2a3e; color: #ddd; border: 1px solid #444;
                border-radius: 4px; padding: 4px; }
    QPushButton { background: #740096; color: white; border: none;
                  border-radius: 4px; padding: 6px 16px; }
    QPushButton:hover { background: #9e2ac0; }
"""


class PinWindow(QWidget):
    """Frameless, always-on-top window displaying a pinned screenshot.

    Supports:
    - Drag to move
    - Right-click context menu (scale presets, custom scale, edit, copy, close)
    - Ctrl+scroll to zoom
    - ESC to close
    - Resume editing via signal
    """

    closed = Signal()
    edit_requested = Signal(object)  # Emits this PinWindow instance

    def __init__(self, pixmap: QPixmap, background: QPixmap = None,
                 elements: list = None, parent=None):
        super().__init__(parent)
        self._pixmap = pixmap          # Rendered (flattened) image for display
        self.background = background   # Original background for re-editing
        self.elements = elements or [] # Annotation elements for re-editing
        self._drag_pos = QPoint()
        self._scale = 1.0
        self._base_w = pixmap.width()
        self._base_h = pixmap.height()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)

        self._label = QLabel(self)
        self._label.setScaledContents(True)
        self._update_display()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self._label)

        self.setStyleSheet("QWidget { background: #1a1a2e; border: 2px solid #740096; }")
        self._apply_size()

    def _update_display(self):
        """Update the label pixmap at current scale."""
        if self._scale == 1.0:
            self._label.setPixmap(self._pixmap)
        else:
            w = max(1, int(self._base_w * self._scale))
            h = max(1, int(self._base_h * self._scale))
            scaled = self._pixmap.scaled(
                w, h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._label.setPixmap(scaled)

    def _apply_size(self):
        """Resize window to fit the scaled pixmap."""
        w = max(1, int(self._base_w * self._scale)) + 4
        h = max(1, int(self._base_h * self._scale)) + 4
        self.setFixedSize(w, h)

    def _set_scale(self, scale: float):
        scale = max(0.1, min(5.0, scale))
        self._scale = scale
        self._update_display()
        self._apply_size()
        self.setWindowTitle(f"PapaRaZ Pin ({int(scale * 100)}%)")

    def _context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet(MENU_STYLE)

        # Edit
        edit_act = menu.addAction("Resume Editing")
        edit_act.triggered.connect(lambda: self.edit_requested.emit(self))

        # Copy to clipboard
        copy_act = menu.addAction("Copy to Clipboard")
        copy_act.triggered.connect(self._copy_to_clipboard)

        menu.addSeparator()

        # Scale presets
        scale_menu = menu.addMenu("Scale")
        for pct in [25, 50, 75, 100, 125, 150, 200, 300, 400]:
            act = scale_menu.addAction(f"{pct}%")
            if pct / 100.0 == self._scale:
                act.setEnabled(False)
            act.triggered.connect(lambda checked, s=pct / 100.0: self._set_scale(s))

        scale_menu.addSeparator()
        custom_act = scale_menu.addAction("Custom...")
        custom_act.triggered.connect(self._custom_scale)

        menu.addSeparator()

        # Close
        close_act = menu.addAction("Close (Esc)")
        close_act.triggered.connect(self.close)

        menu.exec(self.mapToGlobal(pos))

    def _custom_scale(self):
        dlg = QInputDialog(self)
        dlg.setStyleSheet(INPUT_STYLE)
        dlg.setWindowTitle("Custom Scale")
        dlg.setLabelText("Enter scale percentage (10-500):")
        dlg.setIntRange(10, 500)
        dlg.setIntValue(int(self._scale * 100))
        dlg.setIntStep(5)
        if dlg.exec():
            self._set_scale(dlg.intValue() / 100.0)

    def _copy_to_clipboard(self):
        QApplication.clipboard().setPixmap(self._pixmap)

    # --- Events ---

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event.key() == Qt.Key.Key_Plus or event.key() == Qt.Key.Key_Equal:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self._set_scale(self._scale * 1.15)
        elif event.key() == Qt.Key.Key_Minus:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self._set_scale(self._scale / 1.15)
        elif event.key() == Qt.Key.Key_0:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self._set_scale(1.0)
        else:
            super().keyPressEvent(event)

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            factor = 1.1 if delta > 0 else 0.9
            self._set_scale(self._scale * factor)
            event.accept()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)
