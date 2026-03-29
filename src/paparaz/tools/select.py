"""Selection tool: click to select, drag to move, handles to resize all element types."""

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QMouseEvent, QKeyEvent, QPainter, QColor, QPen
from paparaz.tools.base import BaseTool, ToolType
from paparaz.core.elements import (
    AnnotationElement, TextElement, NumberElement, StampElement,
    PenElement, BrushElement, LineElement, ArrowElement,
    RectElement, EllipseElement, MaskElement, ImageElement,
)


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
        # Stored original state for resize
        self._orig_rect = None
        self._orig_start = None
        self._orig_end = None
        self._orig_points = None
        self._orig_position = None
        self._orig_size = None

    def on_press(self, pos: QPointF, event: QMouseEvent):
        if self.canvas.selected_element:
            handle = self.canvas.selected_element.handle_at(pos)
            if handle is not None:
                self._resizing = True
                self._handle_index = handle
                self._drag_start = pos
                self._store_original(self.canvas.selected_element)
                return

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
        for elem in reversed(self.canvas.elements):
            if elem.visible and not elem.locked and elem.contains_point(pos):
                if isinstance(elem, TextElement):
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
            self.canvas.update()

    def on_hover(self, pos: QPointF):
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
            self.canvas.delete_element(self.canvas.selected_element)

    def on_deactivate(self):
        super().on_deactivate()
        self._hovered_element = None

    # --- Resize logic for ALL element types ---

    def _store_original(self, elem: AnnotationElement):
        """Store original geometry before resize begins."""
        self._orig_rect = QRectF(elem.bounding_rect())
        if hasattr(elem, "rect"):
            self._orig_rect = QRectF(elem.rect)
        if isinstance(elem, (LineElement, ArrowElement)):
            self._orig_start = QPointF(elem.start)
            self._orig_end = QPointF(elem.end)
        if isinstance(elem, (PenElement, BrushElement)):
            self._orig_points = [QPointF(p) for p in elem.points]
        if isinstance(elem, (TextElement, NumberElement)):
            self._orig_position = QPointF(elem.position)
        if isinstance(elem, NumberElement):
            self._orig_size = elem.size

    def _resize_element(self, pos: QPointF):
        elem = self.canvas.selected_element
        if not elem:
            return

        h = self._handle_index
        dx = pos.x() - self._drag_start.x()
        dy = pos.y() - self._drag_start.y()

        # Elements with a rect attribute (Rect, Ellipse, Mask, Image)
        if hasattr(elem, "rect") and not isinstance(elem, (LineElement, ArrowElement)):
            orig = self._orig_rect
            new_rect = QRectF(orig)
            if h in (0, 3, 5):  # Left handles
                new_rect.setLeft(orig.left() + (pos.x() - self._drag_start.x()))
            if h in (2, 4, 7):  # Right handles
                new_rect.setRight(orig.right() + (pos.x() - self._drag_start.x()))
            if h in (0, 1, 2):  # Top handles
                new_rect.setTop(orig.top() + (pos.y() - self._drag_start.y()))
            if h in (5, 6, 7):  # Bottom handles
                new_rect.setBottom(orig.bottom() + (pos.y() - self._drag_start.y()))
            # Enforce minimum size
            if new_rect.width() < 5:
                new_rect.setWidth(5)
            if new_rect.height() < 5:
                new_rect.setHeight(5)
            elem.rect = new_rect
            self._orig_rect = QRectF(new_rect)
            self._drag_start = pos
            return

        # Line / Arrow: drag endpoints
        if isinstance(elem, (LineElement, ArrowElement)):
            if h in (0, 3):  # Start side handles
                elem.start = QPointF(elem.start.x() + dx, elem.start.y() + dy)
            elif h in (2, 4, 7):  # End side handles
                elem.end = QPointF(elem.end.x() + dx, elem.end.y() + dy)
            elif h == 1:  # Top-center: move both Y
                elem.start = QPointF(elem.start.x(), elem.start.y() + dy)
                elem.end = QPointF(elem.end.x(), elem.end.y() + dy)
            elif h == 6:  # Bottom-center: move both Y
                elem.start = QPointF(elem.start.x(), elem.start.y() + dy)
                elem.end = QPointF(elem.end.x(), elem.end.y() + dy)
            elif h == 5:  # Bottom-left
                elem.start = QPointF(elem.start.x() + dx, elem.start.y() + dy)
            self._drag_start = pos
            return

        # Pen / Brush: scale all points relative to bounding rect
        if isinstance(elem, (PenElement, BrushElement)) and self._orig_points:
            orig_br = QRectF()
            xs = [p.x() for p in self._orig_points]
            ys = [p.y() for p in self._orig_points]
            if xs and ys:
                orig_br = QRectF(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))

            if orig_br.width() < 1 or orig_br.height() < 1:
                self._drag_start = pos
                return

            new_br = QRectF(orig_br)
            if h in (0, 3, 5):
                new_br.setLeft(orig_br.left() + (pos.x() - self._drag_start.x()))
            if h in (2, 4, 7):
                new_br.setRight(orig_br.right() + (pos.x() - self._drag_start.x()))
            if h in (0, 1, 2):
                new_br.setTop(orig_br.top() + (pos.y() - self._drag_start.y()))
            if h in (5, 6, 7):
                new_br.setBottom(orig_br.bottom() + (pos.y() - self._drag_start.y()))

            if new_br.width() < 5 or new_br.height() < 5:
                self._drag_start = pos
                return

            sx = new_br.width() / orig_br.width()
            sy = new_br.height() / orig_br.height()
            new_points = []
            for p in self._orig_points:
                nx = new_br.left() + (p.x() - orig_br.left()) * sx
                ny = new_br.top() + (p.y() - orig_br.top()) * sy
                new_points.append(QPointF(nx, ny))
            elem.points = new_points
            self._orig_points = [QPointF(p) for p in new_points]
            self._drag_start = pos
            return

        # Text: move position (text can't really "resize" but can be repositioned via handles)
        if isinstance(elem, TextElement):
            if h in (0, 3, 5):  # Left handles: move position X
                elem.position = QPointF(elem.position.x() + dx, elem.position.y())
            if h in (0, 1, 2):  # Top handles: move position Y
                elem.position = QPointF(elem.position.x(), elem.position.y() + dy)
            self._drag_start = pos
            return

        # Number: resize circle
        if isinstance(elem, NumberElement):
            # Use diagonal handles to resize
            if h in (0, 2, 5, 7):  # Corner handles
                delta = max(dx, dy) if (dx + dy) > 0 else min(dx, dy)
                elem.size = max(16, elem.size + delta)
            self._drag_start = pos
            return
