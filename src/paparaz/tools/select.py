"""Selection tool: click to select, drag to move, handles to resize, double-click to edit text."""

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QMouseEvent, QKeyEvent, QPainter, QColor, QPen
from paparaz.tools.base import BaseTool, ToolType
from paparaz.core.elements import AnnotationElement, TextElement


class SelectTool(BaseTool):
    tool_type = ToolType.SELECT
    cursor = Qt.CursorShape.ArrowCursor

    def __init__(self, canvas):
        super().__init__(canvas)
        self._dragging = False
        self._resizing = False
        self._drag_start = QPointF()
        self._handle_index = None
        self._hovered_element: AnnotationElement | None = None

    def on_press(self, pos: QPointF, event: QMouseEvent):
        # Check if clicking a handle of selected element
        if self.canvas.selected_element:
            handle = self.canvas.selected_element.handle_at(pos)
            if handle is not None:
                self._resizing = True
                self._handle_index = handle
                self._drag_start = pos
                return

        # Try to select an element (reverse order = topmost first)
        clicked = None
        for elem in reversed(self.canvas.elements):
            if elem.visible and not elem.locked and elem.contains_point(pos):
                clicked = elem
                break

        if clicked:
            self.canvas.select_element(clicked)
            self._dragging = True
            self._drag_start = pos
        else:
            self.canvas.select_element(None)

    def on_double_click(self, pos: QPointF, event: QMouseEvent):
        """Double-click on a TextElement to re-enter editing mode."""
        for elem in reversed(self.canvas.elements):
            if elem.visible and not elem.locked and elem.contains_point(pos):
                if isinstance(elem, TextElement):
                    # Signal the editor to switch to text tool and start editing this element
                    self.canvas.request_text_edit.emit(elem)
                    return
                break

    def on_move(self, pos: QPointF, event: QMouseEvent):
        if self._dragging and self.canvas.selected_element:
            dx = pos.x() - self._drag_start.x()
            dy = pos.y() - self._drag_start.y()
            self.canvas.selected_element.move_by(dx, dy)
            self._drag_start = pos
            self.canvas.update()
        elif self._resizing and self.canvas.selected_element:
            self._resize_element(pos)
            self._drag_start = pos
            self.canvas.update()

    def on_hover(self, pos: QPointF):
        """Highlight elements under the cursor."""
        self._hover_pos = pos
        hovered = None
        for elem in reversed(self.canvas.elements):
            if elem.visible and not elem.locked and elem.contains_point(pos):
                hovered = elem
                break
        if hovered != self._hovered_element:
            self._hovered_element = hovered
            self.canvas.update()

    def paint_hover(self, painter: QPainter):
        """Draw a subtle highlight on the hovered (non-selected) element."""
        if self._hovered_element and not self._hovered_element.selected:
            rect = self._hovered_element.bounding_rect()
            painter.setPen(QPen(QColor(116, 0, 150, 100), 1.5, Qt.PenStyle.DotLine))
            painter.setBrush(QColor(116, 0, 150, 15))
            painter.drawRect(rect.adjusted(-3, -3, 3, 3))

    def on_release(self, pos: QPointF, event: QMouseEvent):
        self._dragging = False
        self._resizing = False
        self._handle_index = None

    def on_key_press(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Delete and self.canvas.selected_element:
            elem = self.canvas.selected_element
            self.canvas.delete_element(elem)

    def on_deactivate(self):
        super().on_deactivate()
        self._hovered_element = None

    def _resize_element(self, pos: QPointF):
        elem = self.canvas.selected_element
        if not elem or not hasattr(elem, "rect"):
            return

        dx = pos.x() - self._drag_start.x()
        dy = pos.y() - self._drag_start.y()
        r = elem.rect

        h = self._handle_index
        new_rect = QRectF(r)
        if h in (0, 3, 5):
            new_rect.setLeft(r.left() + dx)
        if h in (2, 4, 7):
            new_rect.setRight(r.right() + dx)
        if h in (0, 1, 2):
            new_rect.setTop(r.top() + dy)
        if h in (5, 6, 7):
            new_rect.setBottom(r.bottom() + dy)

        elem.rect = new_rect
