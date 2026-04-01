"""Layers panel — shows elements in z-order with drag reordering, visibility, lock toggles."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QToolButton, QListWidget, QListWidgetItem, QAbstractItemView,
    QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QColor, QIcon, QPixmap, QPainter, QFont

from paparaz.core.elements import AnnotationElement, ElementType


_ELEMENT_ICONS = {
    ElementType.PEN: "✏️",
    ElementType.BRUSH: "🖌️",
    ElementType.HIGHLIGHT: "🔆",
    ElementType.LINE: "╲",
    ElementType.ARROW: "➜",
    ElementType.CURVED_ARROW: "↩",
    ElementType.RECTANGLE: "▭",
    ElementType.ELLIPSE: "⬭",
    ElementType.TEXT: "T",
    ElementType.NUMBER: "#",
    ElementType.MASK: "▦",
    ElementType.IMAGE: "🖼️",
    ElementType.STAMP: "⊛",
    ElementType.MAGNIFIER: "🔍",
}

_ELEMENT_NAMES = {
    ElementType.PEN: "Pen",
    ElementType.BRUSH: "Brush",
    ElementType.HIGHLIGHT: "Highlight",
    ElementType.LINE: "Line",
    ElementType.ARROW: "Arrow",
    ElementType.CURVED_ARROW: "Curved Arrow",
    ElementType.RECTANGLE: "Rectangle",
    ElementType.ELLIPSE: "Ellipse",
    ElementType.TEXT: "Text",
    ElementType.NUMBER: "Number",
    ElementType.MASK: "Blur",
    ElementType.IMAGE: "Image",
    ElementType.STAMP: "Stamp",
    ElementType.MAGNIFIER: "Magnifier",
}

PANEL_WIDTH = 200


class LayersPanel(QWidget):
    """Floating layers panel showing all canvas elements in z-order."""

    element_selected = Signal(object)   # AnnotationElement or None
    visibility_changed = Signal()       # an element's visibility was toggled
    order_changed = Signal()            # z-order changed via drag

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window
                           | Qt.WindowType.WindowStaysOnTopHint)
        self.setFixedWidth(PANEL_WIDTH)
        self.setMinimumHeight(200)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self._canvas = None
        self._updating = False

        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        # Header
        hdr = QHBoxLayout()
        hdr.setContentsMargins(4, 2, 4, 2)
        title = QLabel("Layers")
        title.setStyleSheet("font-size: 12px; font-weight: bold; color: #ccc;")
        hdr.addWidget(title)
        hdr.addStretch()

        self._close_btn = QToolButton()
        self._close_btn.setText("✕")
        self._close_btn.setFixedSize(24, 24)
        self._close_btn.clicked.connect(self.hide)
        hdr.addWidget(self._close_btn)
        root.addLayout(hdr)

        # List
        self._list = QListWidget()
        self._list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self._list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._list.setSpacing(1)
        self._list.currentRowChanged.connect(self._on_row_selected)
        self._list.model().rowsMoved.connect(self._on_rows_moved)
        root.addWidget(self._list)

        # Bottom buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)

        self._up_btn = QToolButton()
        self._up_btn.setText("▲")
        self._up_btn.setToolTip("Move up (closer to front)")
        self._up_btn.setFixedSize(28, 24)
        self._up_btn.clicked.connect(self._move_up)
        btn_row.addWidget(self._up_btn)

        self._down_btn = QToolButton()
        self._down_btn.setText("▼")
        self._down_btn.setToolTip("Move down (closer to back)")
        self._down_btn.setFixedSize(28, 24)
        self._down_btn.clicked.connect(self._move_down)
        btn_row.addWidget(self._down_btn)

        btn_row.addStretch()

        self._del_btn = QToolButton()
        self._del_btn.setText("🗑")
        self._del_btn.setToolTip("Delete selected element")
        self._del_btn.setFixedSize(28, 24)
        self._del_btn.clicked.connect(self._delete_selected)
        btn_row.addWidget(self._del_btn)

        root.addLayout(btn_row)

        self._apply_style()

    def _apply_style(self):
        self.setStyleSheet("""
            LayersPanel {
                background: #13131f;
                border: 1px solid #2a2a4e;
                border-radius: 6px;
            }
            QListWidget {
                background: #0f0f1a;
                border: 1px solid #1e1e34;
                border-radius: 4px;
                color: #ccc;
                font-size: 11px;
            }
            QListWidget::item {
                padding: 4px 6px;
                border-bottom: 1px solid #1a1a2e;
            }
            QListWidget::item:selected {
                background: #2a1050;
                color: #e0e0ff;
            }
            QListWidget::item:hover {
                background: #1e1e34;
            }
            QToolButton {
                background: #1e1e34; color: #999;
                border: 1px solid #2a2a4e; border-radius: 3px;
                font-size: 12px;
            }
            QToolButton:hover {
                background: #2a1040; color: #c0c0ff;
                border-color: #740096;
            }
        """)

    def set_canvas(self, canvas):
        """Connect to a canvas to track its elements."""
        self._canvas = canvas
        self.refresh()

    def refresh(self):
        """Rebuild the list from current canvas elements."""
        if not self._canvas or self._updating:
            return
        self._updating = True
        current_elem = self._canvas.selected_element
        self._list.clear()

        # List in reverse order (top = front, bottom = back)
        for elem in reversed(self._canvas.elements):
            icon = _ELEMENT_ICONS.get(elem.element_type, "?")
            name = _ELEMENT_NAMES.get(elem.element_type, "Element")
            label = f"{icon}  {name} #{elem.id}"
            if not elem.visible:
                label += "  👁‍🗨"
            if elem.locked:
                label += "  🔒"

            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, elem)
            if not elem.visible:
                item.setForeground(QColor("#555"))
            self._list.addItem(item)

            if elem is current_elem:
                self._list.setCurrentItem(item)

        self._updating = False

    def _on_row_selected(self, row: int):
        if self._updating or row < 0:
            return
        item = self._list.item(row)
        if item:
            elem = item.data(Qt.ItemDataRole.UserRole)
            self.element_selected.emit(elem)

    def _on_rows_moved(self):
        """Handle drag-drop reorder in the list."""
        if not self._canvas or self._updating:
            return
        # Rebuild elements list from the visual order (reversed back)
        new_order = []
        for i in range(self._list.count()):
            item = self._list.item(i)
            elem = item.data(Qt.ItemDataRole.UserRole)
            new_order.append(elem)
        # List shows front-to-back, canvas stores back-to-front
        new_order.reverse()
        self._canvas.elements = new_order
        self._canvas.update()
        self.order_changed.emit()

    def _move_up(self):
        """Move selected element up (towards front)."""
        if not self._canvas:
            return
        row = self._list.currentRow()
        if row <= 0:
            return
        # In list: row 0 = front. Moving up in list = moving towards front.
        # In canvas: last index = front. So we need move_up on canvas.
        item = self._list.item(row)
        elem = item.data(Qt.ItemDataRole.UserRole)
        if elem in self._canvas.elements:
            idx = self._canvas.elements.index(elem)
            if idx < len(self._canvas.elements) - 1:
                self._canvas.elements[idx], self._canvas.elements[idx + 1] = \
                    self._canvas.elements[idx + 1], self._canvas.elements[idx]
                self._canvas.update()
                self.refresh()
                # Re-select
                for i in range(self._list.count()):
                    if self._list.item(i).data(Qt.ItemDataRole.UserRole) is elem:
                        self._list.setCurrentRow(i)
                        break

    def _move_down(self):
        """Move selected element down (towards back)."""
        if not self._canvas:
            return
        row = self._list.currentRow()
        if row < 0 or row >= self._list.count() - 1:
            return
        item = self._list.item(row)
        elem = item.data(Qt.ItemDataRole.UserRole)
        if elem in self._canvas.elements:
            idx = self._canvas.elements.index(elem)
            if idx > 0:
                self._canvas.elements[idx], self._canvas.elements[idx - 1] = \
                    self._canvas.elements[idx - 1], self._canvas.elements[idx]
                self._canvas.update()
                self.refresh()
                for i in range(self._list.count()):
                    if self._list.item(i).data(Qt.ItemDataRole.UserRole) is elem:
                        self._list.setCurrentRow(i)
                        break

    def _delete_selected(self):
        if not self._canvas:
            return
        row = self._list.currentRow()
        if row < 0:
            return
        item = self._list.item(row)
        elem = item.data(Qt.ItemDataRole.UserRole)
        if elem in self._canvas.elements:
            self._canvas.delete_element(elem)
            self.refresh()

    def toggle_visibility(self, elem: AnnotationElement):
        """Toggle an element's visibility."""
        elem.visible = not elem.visible
        if self._canvas:
            self._canvas.update()
        self.refresh()
        self.visibility_changed.emit()
