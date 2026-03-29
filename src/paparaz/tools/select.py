"""Selection tool: click to select, drag to move, handles to resize/rotate all element types."""

import math
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QMouseEvent, QKeyEvent, QPainter, QColor, QPen
from paparaz.tools.base import BaseTool, ToolType
from paparaz.core.elements import (
    AnnotationElement, TextElement, NumberElement, StampElement,
    PenElement, BrushElement, LineElement, ArrowElement,
    RectElement, EllipseElement, MaskElement, ImageElement,
)
from paparaz.core.history import Command

# Handle index 8 is the rotation handle
_ROTATION_HANDLE = 8


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
        # Stored original state for resize/rotate
        self._orig_rect = None
        self._orig_start = None
        self._orig_end = None
        self._orig_points = None
        self._orig_position = None
        self._orig_size = None
        self._orig_font_size = None
        self._orig_rotation = 0.0
        # Rubber-band multi-select
        self._rubber_active = False
        self._rubber_start = QPointF()
        self._rubber_rect = QRectF()
        self._multi_selected: list[AnnotationElement] = []
        # Stored originals for multi-move undo
        self._multi_orig_positions: list[dict] = []

    def on_press(self, pos: QPointF, event: QMouseEvent):
        if event.button() == Qt.MouseButton.RightButton:
            return  # handled by canvas contextMenuEvent

        # Shift+click: toggle element in/out of multi-selection
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            for elem in reversed(self.canvas.elements):
                if elem.visible and not elem.locked and elem.contains_point(pos):
                    if elem in self._multi_selected:
                        self._multi_selected.remove(elem)
                    else:
                        # Pull in the current single selection if not already in the group
                        if (self.canvas.selected_element
                                and self.canvas.selected_element not in self._multi_selected):
                            self._multi_selected.append(self.canvas.selected_element)
                        self._multi_selected.append(elem)
                    self.canvas.select_multiple(self._multi_selected)
                    return
            return  # shift+click on empty space: do nothing

        # Check resize handles on currently selected element
        if self.canvas.selected_element:
            handle = self.canvas.selected_element.handle_at(pos)
            if handle is not None:
                self._resizing = True
                self._handle_index = handle
                self._drag_start = pos
                self._store_original(self.canvas.selected_element)
                return

        # Check if any multi-selected element is under cursor (for group move)
        if self._multi_selected:
            for elem in reversed(self._multi_selected):
                if elem.visible and elem.contains_point(pos):
                    self._dragging = True
                    self._drag_start = pos
                    self._multi_orig_positions = [
                        self._capture_geometry(e) for e in self._multi_selected
                    ]
                    return

        clicked = None
        for elem in reversed(self.canvas.elements):
            if elem.visible and not elem.locked and elem.contains_point(pos):
                clicked = elem
                break

        if clicked:
            self._multi_selected.clear()
            self.canvas.select_element(clicked)
            self._store_original(clicked)
            self._dragging = True
            self._drag_start = pos
        else:
            # Start rubber-band selection
            self._multi_selected.clear()
            self.canvas.select_element(None)
            self._rubber_active = True
            self._rubber_start = pos
            self._rubber_rect = QRectF(pos, pos)

    def on_double_click(self, pos: QPointF, event: QMouseEvent):
        for elem in reversed(self.canvas.elements):
            if elem.visible and not elem.locked and elem.contains_point(pos):
                if isinstance(elem, TextElement):
                    self.canvas.request_text_edit.emit(elem)
                    return
                break

    def on_move(self, pos: QPointF, event: QMouseEvent):
        if self._rubber_active:
            self._rubber_rect = QRectF(self._rubber_start, pos).normalized()
            self.canvas.update()
        elif self._dragging and self._multi_selected:
            # Move all multi-selected elements
            dx = pos.x() - self._drag_start.x()
            dy = pos.y() - self._drag_start.y()
            for elem in self._multi_selected:
                elem.move_by(dx, dy)
            self._drag_start = pos
            self.canvas.update()
        elif self._dragging and self.canvas.selected_element:
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
        # Rubber-band rectangle
        if self._rubber_active and not self._rubber_rect.isNull():
            painter.setPen(QPen(QColor(116, 0, 150, 200), 1.5, Qt.PenStyle.DashLine))
            painter.setBrush(QColor(116, 0, 150, 20))
            painter.drawRect(self._rubber_rect)
            return

        if self._hovered_element and not self._hovered_element.selected:
            rect = self._hovered_element.bounding_rect()
            painter.setPen(QPen(QColor(116, 0, 150, 100), 1.5, Qt.PenStyle.DotLine))
            painter.setBrush(QColor(116, 0, 150, 15))
            painter.drawRect(rect.adjusted(-3, -3, 3, 3))

    def on_release(self, pos: QPointF, event: QMouseEvent):
        if event.button() == Qt.MouseButton.RightButton:
            return
        if self._rubber_active:
            self._rubber_active = False
            rb = self._rubber_rect
            if rb.width() > 5 and rb.height() > 5:
                found = [
                    e for e in self.canvas.elements
                    if e.visible and not e.locked and rb.intersects(e.bounding_rect())
                ]
                if found:
                    self._multi_selected = found
                    self.canvas.select_multiple(found)
                else:
                    self._multi_selected.clear()
            self._rubber_rect = QRectF()
            self.canvas.update()
            return

        if self._dragging and self._multi_selected:
            # Record undo for multi-move
            elems = list(self._multi_selected)
            origs = list(self._multi_orig_positions)
            finals = [self._capture_geometry(e) for e in elems]
            if any(o != f for o, f in zip(origs, finals)):
                def do(es=elems, fs=finals):
                    for e, f in zip(es, fs):
                        self._restore_geometry(e, f)
                    self.canvas.update()
                def undo(es=elems, os=origs):
                    for e, o in zip(es, os):
                        self._restore_geometry(e, o)
                    self.canvas.update()
                self.canvas.history.record(Command("Move", do, undo))

        elif (self._dragging or self._resizing) and self.canvas.selected_element:
            elem = self.canvas.selected_element
            orig = self._capture_orig()
            final = self._capture_geometry(elem)
            if orig and orig != final:
                action = "Resize" if self._resizing else "Move"
                def do(e=elem, f=final):
                    self._restore_geometry(e, f)
                    self.canvas.update()
                def undo(e=elem, o=orig):
                    self._restore_geometry(e, o)
                    self.canvas.update()
                self.canvas.history.record(Command(action, do, undo))

        self._dragging = False
        self._resizing = False
        self._handle_index = None
        self._multi_orig_positions.clear()

    def on_key_press(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Delete:
            if self._multi_selected:
                for elem in list(self._multi_selected):
                    self.canvas.delete_element(elem)
                self._multi_selected.clear()
            elif self.canvas.selected_element:
                self.canvas.delete_element(self.canvas.selected_element)

    def on_deactivate(self):
        super().on_deactivate()
        self._hovered_element = None
        self._rubber_active = False
        self._rubber_rect = QRectF()
        self._multi_selected.clear()

    # --- Geometry capture/restore for undo ---

    def _capture_orig(self) -> dict | None:
        """Build a geometry snapshot from the stored _orig_* fields."""
        snap = {}
        if self._orig_rect is not None:
            snap['rect'] = QRectF(self._orig_rect)
        if self._orig_start is not None:
            snap['start'] = QPointF(self._orig_start)
        if self._orig_end is not None:
            snap['end'] = QPointF(self._orig_end)
        if self._orig_points is not None:
            snap['points'] = [QPointF(p) for p in self._orig_points]
        if self._orig_position is not None:
            snap['position'] = QPointF(self._orig_position)
        if self._orig_size is not None:
            snap['size'] = self._orig_size
        snap['rotation'] = self._orig_rotation
        return snap if snap else None

    def _capture_geometry(self, elem: AnnotationElement) -> dict:
        """Capture current geometry of elem into a snapshot dict."""
        snap = {}
        if hasattr(elem, 'rect') and not isinstance(elem, (LineElement, ArrowElement)):
            snap['rect'] = QRectF(elem.rect)
        if isinstance(elem, (LineElement, ArrowElement)):
            snap['start'] = QPointF(elem.start)
            snap['end'] = QPointF(elem.end)
        if isinstance(elem, (PenElement, BrushElement)):
            snap['points'] = [QPointF(p) for p in elem.points]
        if isinstance(elem, NumberElement):
            snap['position'] = QPointF(elem.position)
            snap['size'] = elem.size
        snap['rotation'] = elem.rotation
        return snap

    def _restore_geometry(self, elem: AnnotationElement, snap: dict):
        """Apply a geometry snapshot to elem."""
        if 'rect' in snap and hasattr(elem, 'rect'):
            elem.rect = QRectF(snap['rect'])
        if 'start' in snap:
            elem.start = QPointF(snap['start'])
        if 'end' in snap:
            elem.end = QPointF(snap['end'])
        if 'points' in snap:
            elem.points = [QPointF(p) for p in snap['points']]
        if 'position' in snap and isinstance(elem, NumberElement):
            elem.position = QPointF(snap['position'])
        if 'size' in snap and isinstance(elem, NumberElement):
            elem.size = snap['size']
        if 'rotation' in snap:
            elem.rotation = snap['rotation']

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
        if isinstance(elem, NumberElement):
            self._orig_position = QPointF(elem.position)
            self._orig_size = elem.size
        self._orig_font_size = elem.style.font_size if isinstance(elem, TextElement) else None
        self._orig_rotation = elem.rotation

    def _resize_element(self, pos: QPointF):
        """Resize using absolute deltas from the press position (_drag_start).
        _drag_start and _orig_* are never updated here — they are fixed anchors."""
        elem = self.canvas.selected_element
        if not elem:
            return

        h = self._handle_index
        # Absolute delta from when the resize drag started
        dx = pos.x() - self._drag_start.x()
        dy = pos.y() - self._drag_start.y()
        MIN_SIZE = 10

        # ---- Rotation handle (index 8) — works for all rotatable elements ----
        if h == _ROTATION_HANDLE:
            center = elem.bounding_rect().center()
            # Angle from center to current mouse position, offset by 90° so
            # the rotation handle at top == 0° (pointing up)
            angle = math.degrees(math.atan2(
                pos.y() - center.y(),
                pos.x() - center.x(),
            )) + 90.0
            # Snap to 15° increments when Shift is held (we can't check that here,
            # so we'll just apply directly; shift-snap can be added later)
            elem.rotation = angle % 360.0
            return

        # ---- Elements with a rect attribute (Rect, Ellipse, Mask, Image, Text, Stamp) ----
        if hasattr(elem, "rect") and not isinstance(elem, (LineElement, ArrowElement)):
            orig = self._orig_rect
            left   = orig.left()
            top    = orig.top()
            right  = orig.right()
            bottom = orig.bottom()

            if h in (0, 3, 5):   left   = orig.left()   + dx
            if h in (2, 4, 7):   right  = orig.right()  + dx
            if h in (0, 1, 2):   top    = orig.top()    + dy
            if h in (5, 6, 7):   bottom = orig.bottom() + dy

            # Clamp to minimum size without flipping sides
            if right - left < MIN_SIZE:
                if h in (0, 3, 5):
                    left = right - MIN_SIZE   # left dragged past right
                else:
                    right = left + MIN_SIZE   # right dragged past left
            if bottom - top < MIN_SIZE:
                if h in (0, 1, 2):
                    top = bottom - MIN_SIZE   # top dragged past bottom
                else:
                    bottom = top + MIN_SIZE

            elem.rect = QRectF(left, top, right - left, bottom - top)
            return

        # ---- Line / Arrow: drag endpoints absolutely ----
        if isinstance(elem, (LineElement, ArrowElement)):
            if h in (0, 3):
                elem.start = QPointF(self._orig_start.x() + dx, self._orig_start.y() + dy)
            elif h in (2, 4, 7):
                elem.end = QPointF(self._orig_end.x() + dx, self._orig_end.y() + dy)
            elif h == 1:
                elem.start = QPointF(self._orig_start.x(), self._orig_start.y() + dy)
            elif h == 6:
                elem.end = QPointF(self._orig_end.x(), self._orig_end.y() + dy)
            elif h == 5:
                elem.start = QPointF(self._orig_start.x() + dx, self._orig_start.y() + dy)
            return

        # ---- Pen / Brush: scale all points relative to original bounding rect ----
        if isinstance(elem, (PenElement, BrushElement)) and self._orig_points:
            xs = [p.x() for p in self._orig_points]
            ys = [p.y() for p in self._orig_points]
            if not xs or not ys:
                return
            orig_br = QRectF(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
            if orig_br.width() < 1 or orig_br.height() < 1:
                return

            left   = orig_br.left()
            top    = orig_br.top()
            right  = orig_br.right()
            bottom = orig_br.bottom()

            if h in (0, 3, 5):   left   = orig_br.left()   + dx
            if h in (2, 4, 7):   right  = orig_br.right()  + dx
            if h in (0, 1, 2):   top    = orig_br.top()    + dy
            if h in (5, 6, 7):   bottom = orig_br.bottom() + dy

            new_w = right - left
            new_h = bottom - top
            if new_w < MIN_SIZE or new_h < MIN_SIZE:
                return  # hold at current size, don't flip or collapse

            sx = new_w / orig_br.width()
            sy = new_h / orig_br.height()
            elem.points = [
                QPointF(left + (p.x() - orig_br.left()) * sx,
                        top  + (p.y() - orig_br.top())  * sy)
                for p in self._orig_points
            ]
            return

        # ---- Number: resize circle from corner handles ----
        if isinstance(elem, NumberElement) and self._orig_size is not None:
            if h in (0, 2, 5, 7):
                diag = (dx + dy) / 2
                elem.size = max(16, self._orig_size + diag)
            return
