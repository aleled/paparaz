"""Selection tool: click to select, drag to move, handles to resize/rotate all element types."""

import math
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QMouseEvent, QKeyEvent, QPainter, QColor, QPen
from paparaz.tools.base import BaseTool, ToolType
from paparaz.core.elements import (
    AnnotationElement, TextElement, NumberElement, StampElement,
    PenElement, BrushElement, LineElement, ArrowElement,
    RectElement, EllipseElement, MaskElement, ImageElement,
    _rotate_point,
)
from paparaz.core.history import Command


def _rot(pt: QPointF, cx: float, cy: float, cos_r: float, sin_r: float) -> QPointF:
    """Rotate pt around (cx,cy) given pre-computed cos/sin."""
    dx = pt.x() - cx
    dy = pt.y() - cy
    return QPointF(cx + dx * cos_r - dy * sin_r, cy + dx * sin_r + dy * cos_r)


# For each handle index, which LOCAL point of orig_rect is the ANCHOR
# (the point that must not drift in canvas space during resize).
_ANCHOR_FN = {
    0: lambda r: QPointF(r.right(),      r.bottom()),       # TL dragged → BR anchored
    1: lambda r: QPointF(r.center().x(), r.bottom()),       # TC → BC
    2: lambda r: QPointF(r.left(),       r.bottom()),       # TR → BL
    3: lambda r: QPointF(r.right(),      r.center().y()),   # LM → RM
    4: lambda r: QPointF(r.left(),       r.center().y()),   # RM → LM
    5: lambda r: QPointF(r.right(),      r.top()),          # BL → TR
    6: lambda r: QPointF(r.center().x(), r.top()),          # BC → TC
    7: lambda r: QPointF(r.left(),       r.top()),          # BR → TL
}

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
        key = event.key()
        if key == Qt.Key.Key_Delete:
            if self._multi_selected:
                for elem in list(self._multi_selected):
                    self.canvas.delete_element(elem)
                self._multi_selected.clear()
            elif self.canvas.selected_element:
                self.canvas.delete_element(self.canvas.selected_element)

        elif key in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down):
            step = 10 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1
            dx = (-step if key == Qt.Key.Key_Left else step if key == Qt.Key.Key_Right else 0)
            dy = (-step if key == Qt.Key.Key_Up   else step if key == Qt.Key.Key_Down  else 0)

            if self._multi_selected:
                elems = list(self._multi_selected)
                origs = [self._capture_geometry(e) for e in elems]
                for e in elems:
                    e.move_by(dx, dy)
                finals = [self._capture_geometry(e) for e in elems]
                def _do(es=elems, fs=finals):
                    for e, f in zip(es, fs): self._restore_geometry(e, f)
                    self.canvas.update()
                def _undo(es=elems, os=origs):
                    for e, o in zip(es, os): self._restore_geometry(e, o)
                    self.canvas.update()
                self.canvas.history.record(Command("Move", _do, _undo))
                self.canvas.update()

            elif self.canvas.selected_element:
                elem = self.canvas.selected_element
                orig = self._capture_geometry(elem)
                elem.move_by(dx, dy)
                final = self._capture_geometry(elem)
                def _do(e=elem, f=final):
                    self._restore_geometry(e, f); self.canvas.update()
                def _undo(e=elem, o=orig):
                    self._restore_geometry(e, o); self.canvas.update()
                self.canvas.history.record(Command("Move", _do, _undo))
                self.canvas.update()

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
        """Resize the selected element.

        All deltas are computed in canvas space from _drag_start (the fixed anchor
        at the moment the drag began).  For rotated rect-based elements a two-step
        correction keeps the OPPOSITE handle stationary in canvas space:

          Step 1: convert canvas delta → element-local delta (inverse-rotate by R).
          Step 2: after updating the edge(s), translate the rect so that the anchor
                  point returns to its original canvas-space position.  This is needed
                  because changing one edge shifts the rect's center, and since
                  rotation is applied around that center, ALL canvas corners drift.

        Line/Arrow endpoints are already in canvas coordinates and have no rect-center
        dependency, so only the raw canvas delta is used for them.
        """
        elem = self.canvas.selected_element
        if not elem:
            return

        h = self._handle_index
        cdx = pos.x() - self._drag_start.x()   # canvas-space delta
        cdy = pos.y() - self._drag_start.y()
        MIN_SIZE = 10

        # ---- Rotation handle ----
        if h == _ROTATION_HANDLE:
            center = elem.bounding_rect().center()
            angle = math.degrees(math.atan2(
                pos.y() - center.y(), pos.x() - center.x()
            )) + 90.0
            elem.rotation = angle % 360.0
            return

        # ---- Rect-based elements ----
        if hasattr(elem, "rect") and not isinstance(elem, (LineElement, ArrowElement)):
            orig = self._orig_rect
            R    = self._orig_rotation

            # Step 1: convert canvas delta to element-local delta (inverse rotate by R).
            if R:
                rad   = math.radians(R)
                cos_r = math.cos(rad)
                sin_r = math.sin(rad)
                dx =  cdx * cos_r + cdy * sin_r   # dot with local-X axis
                dy = -cdx * sin_r + cdy * cos_r   # dot with local-Y axis
            else:
                dx, dy = cdx, cdy

            # Apply local delta to the edges that this handle controls.
            left   = orig.left()   + (dx if h in (0, 3, 5) else 0)
            right  = orig.right()  + (dx if h in (2, 4, 7) else 0)
            top    = orig.top()    + (dy if h in (0, 1, 2) else 0)
            bottom = orig.bottom() + (dy if h in (5, 6, 7) else 0)

            # Clamp so the rect never flips or collapses.
            if right - left < MIN_SIZE:
                if h in (0, 3, 5): left  = right - MIN_SIZE
                else:              right = left  + MIN_SIZE
            if bottom - top < MIN_SIZE:
                if h in (0, 1, 2): top    = bottom - MIN_SIZE
                else:              bottom = top    + MIN_SIZE

            new_rect = QRectF(left, top, right - left, bottom - top)

            # Step 2: anchor correction.
            # Changing an edge shifts the rect center in local space.  Because the
            # element is drawn by rotating around its center, ALL canvas-space corners
            # move — even the ones we didn't drag.  We correct by translating new_rect
            # so that the anchor (opposite) local point keeps the same canvas position.
            if R and h in _ANCHOR_FN:
                cos_r = math.cos(math.radians(R))
                sin_r = math.sin(math.radians(R))
                anchor_local = _ANCHOR_FN[h](orig)       # same local pos in old & new rect
                oc = orig.center()
                nc = new_rect.center()
                # Canvas pos of anchor before and after the edge change
                before = _rot(anchor_local, oc.x(), oc.y(), cos_r, sin_r)
                after  = _rot(anchor_local, nc.x(), nc.y(), cos_r, sin_r)
                # Shift the rect to cancel the drift
                new_rect = new_rect.translated(
                    before.x() - after.x(),
                    before.y() - after.y(),
                )

            elem.rect = new_rect
            return

        # ---- Line / Arrow ----
        if isinstance(elem, (LineElement, ArrowElement)):
            R = self._orig_rotation
            if R:
                # Screen-space approach: move one screen-space endpoint by the canvas
                # delta, keep the other endpoint's screen position fixed.
                # Key identity: the rotation center = midpoint(start,end) always maps
                # to itself on screen, so new_canvas_center = midpoint(new_screen_ss, new_screen_se).
                rad   = math.radians(R)
                cos_r = math.cos(rad)
                sin_r = math.sin(rad)
                oc_x = (self._orig_start.x() + self._orig_end.x()) / 2
                oc_y = (self._orig_start.y() + self._orig_end.y()) / 2
                # Screen positions of original endpoints
                ss = _rot(self._orig_start, oc_x, oc_y,  cos_r, sin_r)
                se = _rot(self._orig_end,   oc_x, oc_y,  cos_r, sin_r)
                # Which endpoint does this handle move?
                if h in (0, 1, 3, 5):
                    new_ss = QPointF(ss.x() + cdx, ss.y() + cdy)
                    new_se = se
                else:  # (2, 4, 6, 7)
                    new_ss = ss
                    new_se = QPointF(se.x() + cdx, se.y() + cdy)
                # New rotation center = midpoint of new screen positions
                nc_x = (new_ss.x() + new_se.x()) / 2
                nc_y = (new_ss.y() + new_se.y()) / 2
                # Inverse-rotate screen positions around new center to get canvas coords
                elem.start = _rot(new_ss, nc_x, nc_y, cos_r, -sin_r)
                elem.end   = _rot(new_se, nc_x, nc_y, cos_r, -sin_r)
            else:
                # No rotation: direct canvas-space delta on endpoints
                if h in (0, 3):
                    elem.start = QPointF(self._orig_start.x() + cdx, self._orig_start.y() + cdy)
                elif h in (2, 4, 7):
                    elem.end = QPointF(self._orig_end.x() + cdx, self._orig_end.y() + cdy)
                elif h == 1:
                    elem.start = QPointF(self._orig_start.x(), self._orig_start.y() + cdy)
                elif h == 6:
                    elem.end = QPointF(self._orig_end.x(), self._orig_end.y() + cdy)
                elif h == 5:
                    elem.start = QPointF(self._orig_start.x() + cdx, self._orig_start.y() + cdy)
            return

        # ---- Pen / Brush: scale all points proportionally ----
        if isinstance(elem, (PenElement, BrushElement)) and self._orig_points:
            xs = [p.x() for p in self._orig_points]
            ys = [p.y() for p in self._orig_points]
            if not xs or not ys:
                return
            orig_br = QRectF(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
            if orig_br.width() < 1 or orig_br.height() < 1:
                return

            R = self._orig_rotation
            if R:
                rad   = math.radians(R)
                cos_r = math.cos(rad)
                sin_r = math.sin(rad)
                # Convert canvas delta into element-local frame (inverse-rotate by R)
                dx =  cdx * cos_r + cdy * sin_r
                dy = -cdx * sin_r + cdy * cos_r
            else:
                dx, dy = cdx, cdy
                cos_r = sin_r = 0.0

            left   = orig_br.left()   + (dx if h in (0, 3, 5) else 0)
            right  = orig_br.right()  + (dx if h in (2, 4, 7) else 0)
            top    = orig_br.top()    + (dy if h in (0, 1, 2) else 0)
            bottom = orig_br.bottom() + (dy if h in (5, 6, 7) else 0)
            new_w  = right - left
            new_h  = bottom - top
            if new_w < MIN_SIZE or new_h < MIN_SIZE:
                return

            sx = new_w / orig_br.width()
            sy = new_h / orig_br.height()
            scaled = [
                QPointF(left + (p.x() - orig_br.left()) * sx,
                        top  + (p.y() - orig_br.top())  * sy)
                for p in self._orig_points
            ]

            # Anchor correction: the anchor corner drifts in canvas space when the
            # bounding-rect center shifts (rotation is applied around that center).
            # Translate all scaled points so the anchor stays at its original canvas pos.
            if R and h in _ANCHOR_FN:
                new_br = QRectF(left, top, new_w, new_h)
                anchor = _ANCHOR_FN[h](orig_br)   # same logical corner in old & new br
                oc = orig_br.center()
                nc = new_br.center()
                before = _rot(anchor, oc.x(), oc.y(), cos_r, sin_r)
                after  = _rot(anchor, nc.x(), nc.y(), cos_r, sin_r)
                tx = before.x() - after.x()
                ty = before.y() - after.y()
                scaled = [QPointF(p.x() + tx, p.y() + ty) for p in scaled]

            elem.points = scaled
            return

        # ---- Number marker ----
        if isinstance(elem, NumberElement) and self._orig_size is not None:
            if h in (0, 2, 5, 7):
                diag = (cdx + cdy) / 2
                elem.size = max(16, self._orig_size + diag)
            return
