"""Special tools: Text, Numbering, Eraser, Masquerade, Fill, Stamp, Slice - with hover previews."""

import math
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QMouseEvent, QKeyEvent, QPainter, QColor, QPen, QFont, QFontMetrics, QImage, QPixmap, QTransform
from paparaz.tools.base import BaseTool, ToolType
from paparaz.core.elements import (
    TextElement, NumberElement, MaskElement, StampElement, ImageElement, ElementStyle,
)


def _color_distance(c1: QColor, c2: QColor) -> int:
    """Manhattan distance in RGB space (0–765)."""
    return abs(c1.red() - c2.red()) + abs(c1.green() - c2.green()) + abs(c1.blue() - c2.blue())


class TextTool(BaseTool):
    """Rich text tool with hover preview, editing frame, and formatting.

    Typing is considered active while ``_active_text`` is not None.
    Call ``on_editing_changed(is_editing: bool)`` is fired on every transition
    so the editor can enable/disable shortcuts accordingly.
    """

    tool_type = ToolType.TEXT
    cursor = Qt.CursorShape.IBeamCursor

    def __init__(self, canvas):
        super().__init__(canvas)
        self._active_text: TextElement | None = None
        self.bold = False
        self.italic = False
        self.underline = False
        self.strikethrough = False
        self.alignment = Qt.AlignmentFlag.AlignLeft
        self.direction = Qt.LayoutDirection.LeftToRight
        self.bg_enabled = False
        self.bg_color = "#FFFF00"
        # Assigned by the editor; called with True when editing starts, False when done.
        self.on_editing_changed = None

    # ------------------------------------------------------------------
    # Internal helpers – all _active_text mutations go through these
    # ------------------------------------------------------------------

    def _begin_editing(self, element: TextElement):
        """Set _active_text and fire on_editing_changed(True) if not already editing."""
        was_editing = self._active_text is not None
        self._active_text = element
        # Place cursor at end of existing text
        element.cursor_pos = len(element.text)
        element.sel_start = -1
        if not was_editing and self.on_editing_changed:
            self.on_editing_changed(True)

    def _end_editing(self):
        """Clear _active_text and fire on_editing_changed(False) if was editing."""
        was_editing = self._active_text is not None
        self._active_text = None
        if was_editing and self.on_editing_changed:
            self.on_editing_changed(False)

    # ------------------------------------------------------------------

    def on_press(self, pos: QPointF, event: QMouseEvent):
        if self._active_text:
            # Commit whatever was typed
            if self._active_text.text.strip():
                self._active_text.editing = False
                self.canvas.add_element(self._active_text)
            self._end_editing()
            self.canvas.set_preview(None)

        # Click on existing TextElement → re-edit it
        for elem in reversed(self.canvas.elements):
            if isinstance(elem, TextElement) and elem.visible and elem.contains_point(pos):
                self.canvas.elements.remove(elem)
                elem.editing = True
                self._begin_editing(elem)
                self.canvas.set_preview(elem)
                self.canvas.setFocus()
                return

        # Start a new text element
        style = self.canvas.current_style()
        elem = TextElement(pos, "", style)
        elem.editing = True
        self._apply_formatting(elem)
        self._begin_editing(elem)
        self.canvas.set_preview(elem)
        self.canvas.setFocus()

    def on_key_press(self, event: QKeyEvent):
        if not self._active_text:
            return
        key = event.key()
        mods = event.modifiers()
        elem = self._active_text
        text = elem.text
        cp = elem.cursor_pos
        sel = elem.sel_range()
        shift = bool(mods & Qt.KeyboardModifier.ShiftModifier)
        ctrl = bool(mods & Qt.KeyboardModifier.ControlModifier)

        # --- Navigation & Selection ---
        if key in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Home, Qt.Key.Key_End):
            if key == Qt.Key.Key_Left:
                new_cp = max(0, cp - 1)
            elif key == Qt.Key.Key_Right:
                new_cp = min(len(text), cp + 1)
            elif key == Qt.Key.Key_Home:
                new_cp = 0
            else:  # End
                new_cp = len(text)

            if shift:
                if elem.sel_start < 0:
                    elem.sel_start = cp  # anchor where we were
                elem.cursor_pos = new_cp
            else:
                # Collapse selection: jump to appropriate end
                if sel and not shift:
                    lo, hi = sel
                    elem.cursor_pos = lo if key == Qt.Key.Key_Left else hi
                else:
                    elem.cursor_pos = new_cp
                elem.sel_start = -1

            self.canvas.set_preview(elem)
            return

        # --- Ctrl combos ---
        if ctrl:
            if key == Qt.Key.Key_A:
                elem.sel_start = 0
                elem.cursor_pos = len(text)
                self.canvas.set_preview(elem)
                return
            if key == Qt.Key.Key_C or key == Qt.Key.Key_X:
                if sel:
                    lo, hi = sel
                    from PySide6.QtWidgets import QApplication as _QApp
                    _QApp.clipboard().setText(text[lo:hi])
                    if key == Qt.Key.Key_X:
                        elem.text = text[:lo] + text[hi:]
                        elem.cursor_pos = lo
                        elem.sel_start = -1
                        elem.auto_size()
                self.canvas.set_preview(elem)
                return
            if key == Qt.Key.Key_V:
                from PySide6.QtWidgets import QApplication as _QApp
                paste = _QApp.clipboard().text()
                if paste:
                    if sel:
                        lo, hi = sel
                        elem.text = text[:lo] + paste + text[hi:]
                        elem.cursor_pos = lo + len(paste)
                    else:
                        elem.text = text[:cp] + paste + text[cp:]
                        elem.cursor_pos = cp + len(paste)
                    elem.sel_start = -1
                    elem.auto_size()
                self.canvas.set_preview(elem)
                return

        # --- Commit / Cancel ---
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if ctrl:
                self._finalize()
                return
            # Insert newline at cursor
            if sel:
                lo, hi = sel
                elem.text = text[:lo] + "\n" + text[hi:]
                elem.cursor_pos = lo + 1
                elem.sel_start = -1
            else:
                elem.text = text[:cp] + "\n" + text[cp:]
                elem.cursor_pos = cp + 1
            elem.auto_size()
            self.canvas.set_preview(elem)
            return
        if key == Qt.Key.Key_Escape:
            self._finalize()
            return

        # --- Delete ---
        if key == Qt.Key.Key_Backspace:
            if sel:
                lo, hi = sel
                elem.text = text[:lo] + text[hi:]
                elem.cursor_pos = lo
                elem.sel_start = -1
            elif cp > 0:
                elem.text = text[:cp - 1] + text[cp:]
                elem.cursor_pos = cp - 1
            elem.auto_size()
            self.canvas.set_preview(elem)
            return
        if key == Qt.Key.Key_Delete:
            if sel:
                lo, hi = sel
                elem.text = text[:lo] + text[hi:]
                elem.cursor_pos = lo
                elem.sel_start = -1
            elif cp < len(text):
                elem.text = text[:cp] + text[cp + 1:]
            elem.auto_size()
            self.canvas.set_preview(elem)
            return

        # --- Regular character ---
        char = event.text()
        if not (char and char.isprintable()):
            return
        if sel:
            lo, hi = sel
            elem.text = text[:lo] + char + text[hi:]
            elem.cursor_pos = lo + len(char)
            elem.sel_start = -1
        else:
            elem.text = text[:cp] + char + text[cp:]
            elem.cursor_pos = cp + len(char)

        elem.auto_size()
        self.canvas.set_preview(elem)

    def paint_hover(self, painter: QPainter):
        """Show a ghost text area at cursor position before clicking."""
        if self._active_text or not self._hover_pos:
            return
        style = self.canvas.current_style()
        font = QFont(style.font_family, style.font_size)
        fm = QFontMetrics(font)
        w = max(fm.horizontalAdvance("Type here...") + 16, 80)
        h = fm.height() + 8
        rect = QRectF(self._hover_pos.x(), self._hover_pos.y() - h, w, h)

        # Ghost text area
        painter.setPen(QPen(QColor(116, 0, 150, 120), 1, Qt.PenStyle.DashLine))
        painter.setBrush(QColor(116, 0, 150, 15))
        painter.drawRoundedRect(rect, 4, 4)

        # Ghost text
        painter.setFont(font)
        painter.setPen(QColor(150, 150, 150, 100))
        painter.drawText(QPointF(self._hover_pos.x() + 4, self._hover_pos.y() - 4), "T")

    def start_editing(self, element: TextElement):
        """Begin re-editing an existing text element (called from double-click)."""
        if element in self.canvas.elements:
            self.canvas.elements.remove(element)
        element.editing = True
        element.auto_size()  # ensure box fits existing text before cursor appears
        # Sync tool state FROM the element (don't overwrite its formatting)
        self.bold = element.bold
        self.italic = element.italic
        self.underline = element.underline
        self.strikethrough = element.strikethrough
        self.alignment = element.alignment
        self.direction = element.direction
        self.bg_enabled = element.bg_enabled
        self.bg_color = element.bg_color
        self._begin_editing(element)
        self.canvas.set_preview(element)
        self.canvas.setFocus()
        self.canvas.update()

    def _finalize(self):
        if self._active_text and self._active_text.text.strip():
            self._active_text.editing = False
            self.canvas.add_element(self._active_text)
        self._end_editing()
        self.canvas.set_preview(None)

    def _apply_formatting(self, elem: TextElement):
        elem.bold = self.bold
        elem.italic = self.italic
        elem.underline = self.underline
        elem.strikethrough = self.strikethrough
        elem.alignment = self.alignment
        elem.direction = self.direction
        elem.bg_enabled = self.bg_enabled
        elem.bg_color = self.bg_color

    def set_bold(self, enabled: bool):
        self.bold = enabled
        if self._active_text:
            self._active_text.bold = enabled
            self.canvas.set_preview(self._active_text)

    def set_italic(self, enabled: bool):
        self.italic = enabled
        if self._active_text:
            self._active_text.italic = enabled
            self.canvas.set_preview(self._active_text)

    def set_underline(self, enabled: bool):
        self.underline = enabled
        if self._active_text:
            self._active_text.underline = enabled
            self.canvas.set_preview(self._active_text)

    def set_alignment(self, align: str):
        mapping = {
            "left": Qt.AlignmentFlag.AlignLeft,
            "center": Qt.AlignmentFlag.AlignCenter,
            "right": Qt.AlignmentFlag.AlignRight,
        }
        self.alignment = mapping.get(align, Qt.AlignmentFlag.AlignLeft)
        if self._active_text:
            self._active_text.alignment = self.alignment
            self.canvas.set_preview(self._active_text)

    def set_direction(self, direction: str):
        self.direction = (
            Qt.LayoutDirection.RightToLeft if direction == "rtl"
            else Qt.LayoutDirection.LeftToRight
        )
        if self._active_text:
            self._active_text.direction = self.direction
            self.canvas.set_preview(self._active_text)

    def set_bg_enabled(self, enabled: bool):
        self.bg_enabled = enabled
        if self._active_text:
            self._active_text.bg_enabled = enabled
            self.canvas.set_preview(self._active_text)

    def set_bg_color(self, color: str):
        self.bg_color = color
        if self._active_text:
            self._active_text.bg_color = color
            self.canvas.set_preview(self._active_text)

    def on_deactivate(self):
        self._finalize()
        super().on_deactivate()


class NumberingTool(BaseTool):
    """Numbered marker with ghost circle hover preview."""

    tool_type = ToolType.NUMBERING

    def __init__(self, canvas):
        super().__init__(canvas)
        self.marker_size = 16.0
        self.text_color = ""  # Empty = auto-contrast

    def on_press(self, pos: QPointF, event: QMouseEvent):
        style = self.canvas.current_style()
        elem = NumberElement(pos, size=self.marker_size, text_color=self.text_color, style=style)
        self.canvas.add_element(elem)

    def paint_hover(self, painter: QPainter):
        """Show ghost circle at cursor before clicking."""
        if not self._hover_pos:
            return
        style = self.canvas.current_style()
        size = self.marker_size
        rect = QRectF(
            self._hover_pos.x() - size / 2, self._hover_pos.y() - size / 2,
            size, size,
        )
        # Ghost circle
        color = QColor(style.foreground_color)
        color.setAlpha(60)
        painter.setPen(QPen(QColor(style.foreground_color), 2))
        painter.setBrush(color)
        painter.drawEllipse(rect)

        # Ghost number
        painter.setPen(QColor(255, 255, 255, 150))
        font = QFont(style.font_family, int(size * 0.4), QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(NumberElement._next_number))


class EraserTool(BaseTool):
    """Eraser with hover highlight on target element."""

    tool_type = ToolType.ERASER
    cursor = Qt.CursorShape.PointingHandCursor

    def __init__(self, canvas):
        super().__init__(canvas)
        self._hovered_element = None

    def on_press(self, pos: QPointF, event: QMouseEvent):
        for elem in reversed(self.canvas.elements):
            if elem.visible and elem.contains_point(pos):
                self.canvas.delete_element(elem)
                self._hovered_element = None
                break

    def on_hover(self, pos: QPointF):
        self._hover_pos = pos
        hovered = None
        for elem in reversed(self.canvas.elements):
            if elem.visible and elem.contains_point(pos):
                hovered = elem
                break
        if hovered != self._hovered_element:
            self._hovered_element = hovered
            self.canvas.update()

    def paint_hover(self, painter: QPainter):
        """Highlight the element that would be erased (red tint)."""
        if not self._hovered_element:
            return
        rect = self._hovered_element.bounding_rect()
        painter.setPen(QPen(QColor(220, 50, 50, 180), 2))
        painter.setBrush(QColor(220, 50, 50, 30))
        painter.drawRect(rect.adjusted(-3, -3, 3, 3))

        # X icon
        painter.setPen(QPen(QColor(220, 50, 50, 200), 2))
        cx, cy = rect.center().x(), rect.center().y()
        s = 8
        painter.drawLine(QPointF(cx - s, cy - s), QPointF(cx + s, cy + s))
        painter.drawLine(QPointF(cx + s, cy - s), QPointF(cx - s, cy + s))

    def on_deactivate(self):
        self._hovered_element = None
        super().on_deactivate()


class MasqueradeTool(BaseTool):
    """Blur/pixelate with preview during drag."""

    tool_type = ToolType.MASQUERADE

    def __init__(self, canvas):
        super().__init__(canvas)
        self._start: QPointF | None = None
        self._current: MaskElement | None = None
        self.pixel_size = 10

    def on_press(self, pos: QPointF, event: QMouseEvent):
        style = self.canvas.current_style()
        self._start = pos
        self._current = MaskElement(QRectF(pos, pos), pixel_size=self.pixel_size, style=style)

    def on_move(self, pos: QPointF, event: QMouseEvent):
        if self._current and self._start:
            self._current.rect = QRectF(self._start, pos)
            self.canvas.set_preview(self._current)

    def on_release(self, pos: QPointF, event: QMouseEvent):
        if self._current and self._current.rect.normalized().width() > 5:
            self.canvas.add_element(self._current)
        self._current = None
        self._start = None
        self.canvas.set_preview(None)

    def paint_hover(self, painter: QPainter):
        """Show crosshair at cursor position."""
        if not self._hover_pos or self._current:
            return
        pos = self._hover_pos
        painter.setPen(QPen(QColor(180, 180, 180, 150), 1, Qt.PenStyle.DashLine))
        painter.drawLine(QPointF(pos.x() - 20, pos.y()), QPointF(pos.x() + 20, pos.y()))
        painter.drawLine(QPointF(pos.x(), pos.y() - 20), QPointF(pos.x(), pos.y() + 20))


class FillTool(BaseTool):
    """Flood-fill tool: samples rendered canvas colors and fills contiguous regions."""

    tool_type = ToolType.FILL
    cursor = Qt.CursorShape.CrossCursor

    # Max pixels to fill before stopping (prevents freezing on solid-color regions)
    MAX_FILL_PIXELS = 600_000

    def __init__(self, canvas):
        super().__init__(canvas)
        # tolerance 0–100: allowed per-channel deviation (0=exact match, 100=max)
        self.tolerance: int = 15

    def on_press(self, pos: QPointF, event: QMouseEvent):
        self._do_flood_fill(pos)

    def _do_flood_fill(self, pos: QPointF):
        # Render current canvas state (background + all annotation elements)
        canvas_pixmap = self.canvas.render_to_pixmap()
        src = canvas_pixmap.toImage().convertToFormat(QImage.Format.Format_ARGB32)
        w, h = src.width(), src.height()

        ix, iy = int(pos.x()), int(pos.y())
        if not (0 <= ix < w and 0 <= iy < h):
            return

        # Target color under click
        target = QColor(src.pixel(ix, iy))
        # Use foreground color as fill color (always fully opaque)
        fill_qcolor = QColor(self.canvas.current_style().foreground_color)
        fill_qcolor.setAlpha(255)

        # Skip if fill color is visually identical to target
        if _color_distance(target, fill_qcolor) == 0:
            return

        # Scale tolerance 0-100 → 0-255 per-channel average deviation
        # (tolerance=15 ≈ 38 per channel, tolerance=30 ≈ 76 per channel)
        tol = int(self.tolerance * 2.55)

        # BFS with visited bytearray (avoids set overhead)
        visited = bytearray(w * h)
        queue: list[tuple[int, int]] = [(ix, iy)]
        visited[iy * w + ix] = 1
        filled: list[tuple[int, int]] = []
        max_px = self.MAX_FILL_PIXELS

        while queue and len(filled) < max_px:
            x, y = queue.pop()
            filled.append((x, y))
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if 0 <= nx < w and 0 <= ny < h and not visited[ny * w + nx]:
                    visited[ny * w + nx] = 1
                    nc = QColor(src.pixel(nx, ny))
                    if _color_distance(nc, target) <= tol:
                        queue.append((nx, ny))

        if not filled:
            return

        # Paint filled pixels directly onto the canvas background (avoids alpha
        # compositing artifacts that occur when using a transparent overlay image).
        old_bg = self.canvas._background
        bg_img = old_bg.toImage().convertToFormat(QImage.Format.Format_ARGB32)
        fill_rgba = fill_qcolor.rgba()
        for fx, fy in filled:
            bg_img.setPixel(fx, fy, fill_rgba)

        new_bg = QPixmap.fromImage(bg_img)
        old_bg_copy = QPixmap(old_bg)

        from paparaz.core.history import Command

        def do():
            self.canvas._background = new_bg
            self.canvas.update()

        def undo():
            self.canvas._background = QPixmap(old_bg_copy)
            self.canvas.update()

        self.canvas.history.execute(Command("Fill", do, undo))

    def paint_hover(self, painter: QPainter):
        """Show crosshair + fill color dot at cursor."""
        if not self._hover_pos:
            return
        pos = self._hover_pos
        fill_color = QColor(self.canvas.current_style().foreground_color)
        fill_color.setAlpha(255)
        painter.setPen(QPen(QColor(100, 100, 100, 150), 1, Qt.PenStyle.DashLine))
        painter.drawLine(QPointF(pos.x() - 16, pos.y()), QPointF(pos.x() + 16, pos.y()))
        painter.drawLine(QPointF(pos.x(), pos.y() - 16), QPointF(pos.x(), pos.y() + 16))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(fill_color)
        painter.drawEllipse(pos, 4, 4)


class StampTool(BaseTool):
    """Place predefined stamp icons (check, cross, OK, etc.) on the canvas."""

    tool_type = ToolType.STAMP
    cursor = Qt.CursorShape.CrossCursor

    def __init__(self, canvas):
        super().__init__(canvas)
        self.stamp_id = "check"
        self.stamp_size = 48.0

    def on_press(self, pos: QPointF, event: QMouseEvent):
        style = self.canvas.current_style()
        elem = StampElement(self.stamp_id, pos, self.stamp_size, style)
        self.canvas.add_element(elem)

    def paint_hover(self, painter: QPainter):
        """Show ghost stamp at cursor before clicking."""
        if not self._hover_pos:
            return
        from paparaz.ui.stamps import get_stamp_renderer
        s = self.stamp_size
        r = QRectF(self._hover_pos.x() - s / 2, self._hover_pos.y() - s / 2, s, s)
        painter.setOpacity(0.45)
        renderer = get_stamp_renderer(self.stamp_id)
        if renderer:
            renderer.render(painter, r)
        painter.setOpacity(1.0)


def _subtract_rect(outer: QRectF, inner: QRectF) -> list:
    """Return list of rects covering outer minus inner."""
    inner = inner.intersected(outer)
    if inner.isEmpty():
        return [outer]
    rects = []
    if inner.top() > outer.top():
        rects.append(QRectF(outer.left(), outer.top(), outer.width(), inner.top() - outer.top()))
    if inner.bottom() < outer.bottom():
        rects.append(QRectF(outer.left(), inner.bottom(), outer.width(), outer.bottom() - inner.bottom()))
    if inner.left() > outer.left():
        rects.append(QRectF(outer.left(), inner.top(), inner.left() - outer.left(), inner.height()))
    if inner.right() < outer.right():
        rects.append(QRectF(inner.right(), inner.top(), outer.right() - inner.right(), inner.height()))
    return rects


def _rotated_rect_corners(rect: QRectF, angle_deg: float) -> list:
    """Return the 4 corners of *rect* rotated by *angle_deg* around rect center."""
    cx, cy = rect.center().x(), rect.center().y()
    rad = math.radians(angle_deg)
    cos_r, sin_r = math.cos(rad), math.sin(rad)
    corners = [
        (rect.left(),  rect.top()),
        (rect.right(), rect.top()),
        (rect.right(), rect.bottom()),
        (rect.left(),  rect.bottom()),
    ]
    rotated = []
    for x, y in corners:
        dx, dy = x - cx, y - cy
        rotated.append(QPointF(cx + dx * cos_r - dy * sin_r,
                               cy + dx * sin_r + dy * cos_r))
    return rotated


def _draw_rotated_selection(painter: QPainter, rect: QRectF, angle_deg: float,
                             border_color: QColor, fill_color: QColor,
                             rot_handle_color: QColor):
    """Draw a rotated rubber-band rectangle with a rotation handle."""
    corners = _rotated_rect_corners(rect, angle_deg)

    # Fill + border
    painter.setPen(QPen(border_color, 1.5, Qt.PenStyle.DashLine))
    painter.setBrush(fill_color)
    from PySide6.QtGui import QPolygonF
    painter.drawPolygon(QPolygonF(corners))

    # Corner handles
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(border_color)
    for c in corners:
        painter.drawEllipse(c, 5, 5)

    # Rotation handle: 30px above top-center, in rotated space
    cx, cy = rect.center().x(), rect.center().y()
    # Top-center in local space
    top_cx = (rect.left() + rect.right()) / 2
    top_cy = rect.top()
    # Rotate top-center
    rad = math.radians(angle_deg)
    cos_r, sin_r = math.cos(rad), math.sin(rad)
    dx, dy = top_cx - cx, top_cy - cy
    rtcx = cx + dx * cos_r - dy * sin_r
    rtcy = cy + dx * sin_r + dy * cos_r
    # Rotation handle 30px further in the "up" direction (rotated)
    rhx = rtcx - sin_r * 30
    rhy = rtcy - cos_r * 30
    painter.setPen(QPen(border_color, 1.5))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawLine(QPointF(rtcx, rtcy), QPointF(rhx, rhy))
    painter.setPen(QPen(QColor("white"), 2))
    painter.setBrush(rot_handle_color)
    painter.drawEllipse(QPointF(rhx, rhy), 6, 6)
    return QPointF(rhx, rhy)   # return handle world position


def _capture_element_geom(elem) -> dict:
    """Capture all geometric data of an element into a plain dict."""
    from paparaz.core.elements import LineElement, ArrowElement, PenElement, BrushElement, NumberElement
    snap: dict = {'rotation': elem.rotation}
    if hasattr(elem, 'rect') and not isinstance(elem, (LineElement, ArrowElement)):
        snap['rect'] = QRectF(elem.rect)
    if isinstance(elem, (LineElement, ArrowElement)):
        snap['start'] = QPointF(elem.start)
        snap['end']   = QPointF(elem.end)
    if isinstance(elem, (PenElement, BrushElement)):
        snap['points'] = [QPointF(p) for p in elem.points]
    if isinstance(elem, NumberElement):
        snap['position'] = QPointF(elem.position)
    return snap


def _transform_element_geom(snap: dict, t: QTransform, crop_rotation: float) -> dict:
    """Return a new snapshot with all points mapped through QTransform t.

    Rules:
    - rect elements: preserve size, move center, adjust rotation by -crop_rotation
    - line/arrow (start/end): transform coords, rotation UNCHANGED (coords encode orientation)
    - pen/brush (points): transform coords, rotation UNCHANGED
    - number (position): transform position, adjust rotation by -crop_rotation
    """
    coord_based = 'start' in snap or 'points' in snap
    if coord_based:
        new: dict = {'rotation': snap['rotation']}  # coords already encode orientation
    else:
        new: dict = {'rotation': (snap['rotation'] - crop_rotation) % 360.0}

    if 'rect' in snap:
        r = snap['rect']
        new_center = t.map(r.center())
        new['rect'] = QRectF(
            new_center.x() - r.width() / 2.0,
            new_center.y() - r.height() / 2.0,
            r.width(),
            r.height(),
        )
    if 'start' in snap:
        new['start'] = t.map(snap['start'])
    if 'end' in snap:
        new['end'] = t.map(snap['end'])
    if 'points' in snap:
        new['points'] = [t.map(p) for p in snap['points']]
    if 'position' in snap:
        new['position'] = t.map(snap['position'])
    return new


def _restore_element_geom(elem, snap: dict):
    """Apply a geometry snapshot to an element."""
    from paparaz.core.elements import LineElement, ArrowElement, PenElement, BrushElement, NumberElement
    if 'rect' in snap and hasattr(elem, 'rect') and not isinstance(elem, (LineElement, ArrowElement)):
        elem.rect = QRectF(snap['rect'])
    if 'start' in snap:
        elem.start = QPointF(snap['start'])
    if 'end' in snap:
        elem.end = QPointF(snap['end'])
    if 'points' in snap:
        elem.points = [QPointF(p) for p in snap['points']]
    if 'position' in snap and isinstance(elem, NumberElement):
        elem.position = QPointF(snap['position'])
    elem.rotation = snap.get('rotation', elem.rotation)


class _RotatableSelectionMixin:
    """Mixin for tools that have a rotatable rubber-band selection region."""

    ROT_HANDLE_OFFSET = 30

    def _init_rot(self):
        self._start = QPointF()
        self._end = QPointF()
        self._rotation = 0.0     # degrees
        self._active = False
        self._rotating = False   # True when dragging rotation handle
        self._rot_handle_pos = QPointF()
        self._drag_start = QPointF()
        self._rot_start_angle = 0.0

    def _rect(self) -> QRectF:
        return QRectF(self._start, self._end).normalized()

    def _rot_center(self) -> QPointF:
        return self._rect().center()

    def _is_near_rot_handle(self, pos: QPointF) -> bool:
        d = self._rot_handle_pos - pos
        return (d.x() ** 2 + d.y() ** 2) < 14 ** 2

    def _handle_rot_press(self, pos: QPointF) -> bool:
        """Returns True if pos hit the rotation handle."""
        if not self._active:
            return False
        if self._is_near_rot_handle(pos):
            self._rotating = True
            self._drag_start = pos
            return True
        return False

    def _handle_rot_move(self, pos: QPointF):
        if self._rotating:
            center = self._rot_center()
            angle = math.degrees(math.atan2(
                pos.y() - center.y(),
                pos.x() - center.x()
            )) + 90.0
            self._rotation = angle % 360.0

    def _handle_rot_release(self):
        self._rotating = False


class CropTool(_RotatableSelectionMixin, BaseTool):
    """Drag to select crop region (optionally rotated), Enter/double-click to apply."""
    tool_type = ToolType.CROP
    cursor = Qt.CursorShape.CrossCursor

    def __init__(self, canvas):
        BaseTool.__init__(self, canvas)
        self._init_rot()

    def on_press(self, pos, event):
        if event.button() == Qt.MouseButton.RightButton:
            if self._active:
                self._apply_crop()
            return
        if self._handle_rot_press(pos):
            return
        self._start = pos
        self._end = pos
        self._rotation = 0.0
        self._active = True

    def on_move(self, pos, event):
        if self._rotating:
            self._handle_rot_move(pos)
            self.canvas.update()
        elif self._active:
            self._end = pos
            self.canvas.update()

    def on_release(self, pos, event):
        if event.button() == Qt.MouseButton.RightButton:
            return
        if self._rotating:
            self._handle_rot_release()
        else:
            self._end = pos

    def on_double_click(self, pos, event):
        self._apply_crop()

    def on_key_press(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._apply_crop()
        elif event.key() == Qt.Key.Key_Escape:
            self._active = False
            self.canvas.update()

    def _apply_crop(self):
        if not self._active:
            return
        rect = self._rect()
        if rect.width() <= 5 or rect.height() <= 5:
            self._active = False
            return

        if abs(self._rotation) < 0.5:
            self.canvas.crop_canvas(rect)
            self._active = False
            return

        # --- Rotated crop ---
        # Extract exact pixels by inverse-rotating the background into a
        # rect.width × rect.height pixmap, and apply the same transform
        # to every element so annotations stay aligned with their content.
        rotation = self._rotation
        from PySide6.QtGui import QPainter as _P
        from paparaz.core.history import Command

        w, h = max(1, int(rect.width())), max(1, int(rect.height()))
        bg = self.canvas._background
        cx, cy = rect.center().x(), rect.center().y()

        # Build inverse-rotation transform: rotate-around-center then shift to origin
        t = QTransform()
        t.translate(w / 2.0, h / 2.0)
        t.rotate(-rotation)
        t.translate(-cx, -cy)

        # Render new background
        new_bg_pix = QPixmap(w, h)
        new_bg_pix.fill(Qt.GlobalColor.white)
        p = _P(new_bg_pix)
        p.setRenderHint(_P.RenderHint.SmoothPixmapTransform)
        p.setTransform(t)
        p.drawPixmap(QPointF(0, 0), bg)
        p.end()

        old_bg = QPixmap(bg)
        elems = list(self.canvas.elements)
        old_snaps = {id(e): _capture_element_geom(e) for e in elems}
        new_snaps = {id(e): _transform_element_geom(old_snaps[id(e)], t, rotation) for e in elems}

        def do(_new_bg=new_bg_pix, _elems=elems, _new=new_snaps):
            self.canvas._background = QPixmap(_new_bg)
            for e in _elems:
                _restore_element_geom(e, _new[id(e)])
            self.canvas._update_size()
            self.canvas.update()

        def undo(_old_bg=old_bg, _elems=elems, _old=old_snaps):
            self.canvas._background = QPixmap(_old_bg)
            for e in _elems:
                _restore_element_geom(e, _old[id(e)])
            self.canvas._update_size()
            self.canvas.update()

        self.canvas.history.execute(Command("Crop canvas", do, undo))
        self._active = False

    def paint_hover(self, painter):
        if not self._active:
            return
        rect = self._rect()
        rot_col  = QColor(0, 188, 140)
        self._rot_handle_pos = _draw_rotated_selection(
            painter, rect, self._rotation,
            QColor(116, 0, 150, 200), QColor(116, 0, 150, 30), rot_col,
        )
        # Darken outside crop area (only for non-rotated for simplicity)
        if abs(self._rotation) < 0.5:
            bg = self.canvas._background
            full = QRectF(0, 0, bg.width(), bg.height())
            painter.setBrush(QColor(0, 0, 0, 100))
            painter.setPen(Qt.PenStyle.NoPen)
            for r in _subtract_rect(full, rect):
                painter.drawRect(r)
        # Hint label
        painter.setPen(QColor(255, 255, 255, 200))
        painter.setFont(QFont("Arial", 9))
        w, h = int(rect.width()), int(rect.height())
        rot_txt = f"  {self._rotation:.0f}°" if abs(self._rotation) > 0.5 else ""
        painter.drawText(
            int(rect.x() + 4), int(rect.bottom() + 14),
            f"{w} × {h} px{rot_txt}  —  Enter / double-click / right-click to crop · Esc to cancel"
        )


class SliceTool(_RotatableSelectionMixin, BaseTool):
    """Slice a region out of the canvas background into a moveable ImageElement.

    Draw a selection, optionally rotate it with the teal handle, then press
    Enter / double-click / right-click to apply.  Escape cancels.

    Rotation: pixels are extracted by inverse-rotating the background into
    a rect-sized pixmap, so the resulting element contains exactly the rotated
    region's content (no AABB padding).
    """
    tool_type = ToolType.SLICE
    cursor = Qt.CursorShape.CrossCursor

    def __init__(self, canvas):
        BaseTool.__init__(self, canvas)
        self._init_rot()

    def on_press(self, pos, event):
        # Right-click when a selection exists → apply the slice
        if event.button() == Qt.MouseButton.RightButton:
            if self._active:
                self._apply_slice()
            return
        if self._handle_rot_press(pos):
            return
        self._start = pos
        self._end = pos
        self._rotation = 0.0
        self._active = True

    def on_move(self, pos, event):
        if self._rotating:
            self._handle_rot_move(pos)
            self.canvas.update()
        elif self._active:
            self._end = pos
            self.canvas.update()

    def on_release(self, pos, event):
        if event.button() == Qt.MouseButton.RightButton:
            return
        if self._rotating:
            self._handle_rot_release()
        elif self._active:
            self._end = pos
            self.canvas.update()

    def on_double_click(self, pos, event):
        self._apply_slice()

    def on_key_press(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._apply_slice()
        elif event.key() == Qt.Key.Key_Escape:
            self._cancel()

    def _cancel(self):
        self._active = False
        self.canvas.update()

    def _apply_slice(self):
        if not self._active:
            return
        rect = self._rect()
        if rect.width() < 4 or rect.height() < 4:
            self._cancel()
            return

        bg = self.canvas._background
        bg_rect = QRectF(0, 0, bg.width(), bg.height())
        rotation = self._rotation  # capture; self._rotation may change after _cancel()

        fill_qcolor = QColor(self.canvas._bg_color if hasattr(self.canvas, '_bg_color') else "#FFFFFF")
        fill_qcolor.setAlpha(255)

        from paparaz.core.history import Command
        from PySide6.QtGui import QPainter as _P, QPolygonF

        old_bg = QPixmap(bg)

        if abs(rotation) > 0.5:
            # ------------------------------------------------------------------
            # Rotated slice: extract exact pixels by inverse-rotating the bg
            # into a pixmap that matches the (unrotated) selection rectangle.
            # ------------------------------------------------------------------
            w, h = max(1, int(rect.width())), max(1, int(rect.height()))
            sliced_pix = QPixmap(w, h)
            sliced_pix.fill(Qt.GlobalColor.transparent)
            p = _P(sliced_pix)
            p.setRenderHint(_P.RenderHint.SmoothPixmapTransform)
            # Map bg so the selection's centre lands at (w/2, h/2), un-rotated
            cx, cy = rect.center().x(), rect.center().y()
            p.translate(w / 2.0, h / 2.0)
            p.rotate(-rotation)
            p.translate(-cx, -cy)
            p.drawPixmap(QPointF(0, 0), bg)
            p.end()

            # Place element at rect.topLeft() with the same rotation so it
            # visually "sits" in exactly the same spot as the selection.
            elem_pos = QPointF(rect.left(), rect.top())
            new_elem = ImageElement(sliced_pix, elem_pos)
            new_elem.rotation = rotation

            # Erase the rotated polygon from the background
            corners = _rotated_rect_corners(rect, rotation)
            poly = QPolygonF(corners)

            def do(
                _old=old_bg, _new_elem=new_elem, _poly=poly,
                _fill=fill_qcolor
            ):
                new_bg = QPixmap(_old)
                p2 = _P(new_bg)
                p2.setBrush(_fill)
                p2.setPen(Qt.PenStyle.NoPen)
                p2.drawPolygon(_poly)
                p2.end()
                self.canvas._background = new_bg
                self.canvas.elements.append(_new_elem)
                self.canvas.select_element(_new_elem)
                self.canvas._update_size()
                self.canvas.update()

        else:
            # ------------------------------------------------------------------
            # Axis-aligned slice: plain pixmap copy
            # ------------------------------------------------------------------
            clip = rect.intersected(bg_rect).toRect()
            if clip.width() < 1 or clip.height() < 1:
                self._cancel()
                return

            sliced_pix = bg.copy(clip)
            elem_pos = QPointF(clip.x(), clip.y())
            new_elem = ImageElement(sliced_pix, elem_pos)
            new_elem.rotation = 0.0

            def do(
                _old=old_bg, _new_elem=new_elem, _clip=clip,
                _fill=fill_qcolor
            ):
                new_bg = QPixmap(_old)
                p2 = _P(new_bg)
                p2.fillRect(_clip, _fill)
                p2.end()
                self.canvas._background = new_bg
                self.canvas.elements.append(_new_elem)
                self.canvas.select_element(_new_elem)
                self.canvas._update_size()
                self.canvas.update()

        new_elem.style = self.canvas.current_style()

        def undo(_old=old_bg, _new_elem=new_elem):
            if _new_elem in self.canvas.elements:
                self.canvas.elements.remove(_new_elem)
            self.canvas._background = QPixmap(_old)
            self.canvas.select_element(None)
            self.canvas._update_size()
            self.canvas.update()

        self.canvas.history.execute(Command("Slice", do, undo))
        self._cancel()

    def paint_hover(self, painter):
        if not self._active:
            return
        rect = self._rect()
        teal = QColor(0, 188, 140)
        self._rot_handle_pos = _draw_rotated_selection(
            painter, rect, self._rotation,
            QColor(255, 200, 0, 200), QColor(255, 200, 0, 20), teal,
        )
        # Size + hint label
        painter.setPen(QColor(255, 255, 255, 200))
        painter.setFont(QFont("Arial", 9))
        w, h = int(rect.width()), int(rect.height())
        rot_txt = f"  {self._rotation:.0f}°" if abs(self._rotation) > 0.5 else ""
        painter.drawText(
            int(rect.x() + 4), int(rect.bottom() + 14),
            f"{w} × {h} px{rot_txt}  —  Enter / double-click / right-click to slice · Esc to cancel"
        )
