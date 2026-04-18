"""Drawing tools: Pen, Brush, Highlight, Line, Arrow, CurvedArrow, Rectangle, Ellipse."""

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QMouseEvent, QPainter, QColor, QPen
from paparaz.tools.base import BaseTool, ToolType
from paparaz.core.history import Command
from paparaz.core.elements import (
    PenElement, BrushElement, HighlightElement, LineElement, ArrowElement,
    CurvedArrowElement, RectElement, EllipseElement, MeasureElement, ElementStyle,
)


class PenTool(BaseTool):
    tool_type = ToolType.PEN

    def __init__(self, canvas):
        super().__init__(canvas)
        self._current: PenElement | None = None

    def on_deactivate(self):
        """Discard any in-progress stroke when the tool is switched away."""
        self._current = None
        self.canvas.set_preview(None)
        super().on_deactivate()

    def on_press(self, pos: QPointF, event: QMouseEvent):
        style = self.canvas.current_style()
        self._current = PenElement(style)
        self._current.add_point(pos)

    def on_move(self, pos: QPointF, event: QMouseEvent):
        if self._current:
            self._current.add_point(pos)
            self.canvas.set_preview(self._current)

    def on_release(self, pos: QPointF, event: QMouseEvent):
        if self._current and len(self._current.points) >= 2:
            elem = self._current
            self.canvas.add_element(elem)
        self._current = None
        self.canvas.set_preview(None)


class HighlightTool(BaseTool):
    """Wide semi-transparent flat-cap marker strokes."""
    tool_type = ToolType.HIGHLIGHT

    # Default style values applied when no saved properties exist.
    # With Multiply blend mode the colour should be fully opaque — transparency
    # comes from the blend, not from alpha.  Classic highlighter yellow.
    DEFAULT_COLOR = "#FFFF00"
    DEFAULT_WIDTH = 16

    @property
    def _effective_color(self):
        sm = getattr(self.canvas, '_settings_manager', None)
        if sm:
            return getattr(sm.settings, 'highlight_default_color', self.DEFAULT_COLOR)
        return self.DEFAULT_COLOR

    @property
    def _effective_width(self):
        sm = getattr(self.canvas, '_settings_manager', None)
        if sm:
            return getattr(sm.settings, 'highlight_default_width', self.DEFAULT_WIDTH)
        return self.DEFAULT_WIDTH

    def __init__(self, canvas):
        super().__init__(canvas)
        self._current: HighlightElement | None = None

    def on_activate(self):
        # Seed canvas state with highlight defaults only if nothing saved
        if not getattr(self.canvas, "_highlight_defaults_set", False):
            if self.canvas._fg_color in ("#FF0000", "#ff0000"):  # untouched default
                self.canvas._fg_color = self._effective_color
            if self.canvas._line_width <= 3.0:
                self.canvas._line_width = float(self._effective_width)
            self.canvas._highlight_defaults_set = True

    def on_deactivate(self):
        """Discard any in-progress stroke when the tool is switched away."""
        self._current = None
        self.canvas.set_preview(None)
        super().on_deactivate()

    def on_press(self, pos: QPointF, event: QMouseEvent):
        style = self.canvas.current_style()
        self._current = HighlightElement(style)
        self._current.add_point(pos)

    def on_move(self, pos: QPointF, event: QMouseEvent):
        if self._current:
            self._current.add_point(pos)
            self.canvas.set_preview(self._current)

    def on_release(self, pos: QPointF, event: QMouseEvent):
        if self._current and len(self._current.points) >= 2:
            self.canvas.add_element(self._current)
        self._current = None
        self.canvas.set_preview(None)


class BrushTool(BaseTool):
    tool_type = ToolType.BRUSH

    def __init__(self, canvas):
        super().__init__(canvas)
        self._current: BrushElement | None = None

    def on_deactivate(self):
        """Discard any in-progress stroke when the tool is switched away."""
        self._current = None
        self.canvas.set_preview(None)
        super().on_deactivate()

    def on_press(self, pos: QPointF, event: QMouseEvent):
        style = self.canvas.current_style()
        self._current = BrushElement(style)
        self._current.add_point(pos)

    def on_move(self, pos: QPointF, event: QMouseEvent):
        if self._current:
            self._current.add_point(pos)
            self.canvas.set_preview(self._current)

    def on_release(self, pos: QPointF, event: QMouseEvent):
        if self._current and len(self._current.points) >= 2:
            self.canvas.add_element(self._current)
        self._current = None
        self.canvas.set_preview(None)


class LineTool(BaseTool):
    tool_type = ToolType.LINE
    _MIN_LENGTH_SQ = 4  # discard lines shorter than 2 px

    def __init__(self, canvas):
        super().__init__(canvas)
        self._current: LineElement | None = None

    def on_deactivate(self):
        """Discard in-progress line when the tool is switched away."""
        self._current = None
        self.canvas.set_preview(None)
        super().on_deactivate()

    def on_press(self, pos: QPointF, event: QMouseEvent):
        style = self.canvas.current_style()
        self._current = LineElement(pos, pos, style)

    def on_move(self, pos: QPointF, event: QMouseEvent):
        if self._current:
            end = pos
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                end = self._snap_angle(self._current.start, pos)
            self._current.end = end
            self.canvas.set_preview(self._current)

    def on_release(self, pos: QPointF, event: QMouseEvent):
        if self._current:
            dx = self._current.end.x() - self._current.start.x()
            dy = self._current.end.y() - self._current.start.y()
            if dx * dx + dy * dy >= self._MIN_LENGTH_SQ:
                self.canvas.add_element(self._current)
        self._current = None
        self.canvas.set_preview(None)

    def _snap_angle(self, start: QPointF, end: QPointF) -> QPointF:
        import math
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        angle = math.atan2(dy, dx)
        snap = round(angle / (math.pi / 4)) * (math.pi / 4)
        length = math.sqrt(dx * dx + dy * dy)
        return QPointF(
            start.x() + length * math.cos(snap),
            start.y() + length * math.sin(snap),
        )


class ArrowTool(LineTool):
    tool_type = ToolType.ARROW

    def on_press(self, pos: QPointF, event: QMouseEvent):
        style = self.canvas.current_style()
        self._current = ArrowElement(pos, pos, style)


class RectangleTool(BaseTool):
    tool_type = ToolType.RECTANGLE
    _MIN_SIZE = 3  # discard rects smaller than 3x3 px

    def __init__(self, canvas):
        super().__init__(canvas)
        self._start: QPointF | None = None
        self._current: RectElement | None = None

    def on_deactivate(self):
        """Discard in-progress rect when the tool is switched away."""
        self._current = None
        self._start = None
        self.canvas.set_preview(None)
        super().on_deactivate()

    def on_press(self, pos: QPointF, event: QMouseEvent):
        style = self.canvas.current_style()
        self._start = pos
        self._current = RectElement(QRectF(pos, pos), getattr(self.canvas, "_filled", False), style)

    def on_move(self, pos: QPointF, event: QMouseEvent):
        if self._current is not None and self._start is not None:
            end = pos
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                # Constrain to square
                dx = pos.x() - self._start.x()
                dy = pos.y() - self._start.y()
                side = max(abs(dx), abs(dy))
                end = QPointF(
                    self._start.x() + (side if dx >= 0 else -side),
                    self._start.y() + (side if dy >= 0 else -side),
                )
            self._current.rect = QRectF(self._start, end)
            self.canvas.set_preview(self._current)

    def on_release(self, pos: QPointF, event: QMouseEvent):
        if self._current:
            r = self._current.rect.normalized()
            if r.width() >= self._MIN_SIZE and r.height() >= self._MIN_SIZE:
                self.canvas.add_element(self._current)
        self._current = None
        self._start = None
        self.canvas.set_preview(None)


class EllipseTool(BaseTool):
    tool_type = ToolType.ELLIPSE
    _MIN_SIZE = 3  # discard ellipses smaller than 3x3 px

    def __init__(self, canvas):
        super().__init__(canvas)
        self._start: QPointF | None = None
        self._current: EllipseElement | None = None

    def on_deactivate(self):
        """Discard in-progress ellipse when the tool is switched away."""
        self._current = None
        self._start = None
        self.canvas.set_preview(None)
        super().on_deactivate()

    def on_press(self, pos: QPointF, event: QMouseEvent):
        style = self.canvas.current_style()
        self._start = pos
        self._current = EllipseElement(QRectF(pos, pos), getattr(self.canvas, "_filled", False), style)

    def on_move(self, pos: QPointF, event: QMouseEvent):
        if self._current is not None and self._start is not None:
            end = pos
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                dx = pos.x() - self._start.x()
                dy = pos.y() - self._start.y()
                side = max(abs(dx), abs(dy))
                end = QPointF(
                    self._start.x() + (side if dx >= 0 else -side),
                    self._start.y() + (side if dy >= 0 else -side),
                )
            self._current.rect = QRectF(self._start, end)
            self.canvas.set_preview(self._current)

    def on_release(self, pos: QPointF, event: QMouseEvent):
        if self._current:
            r = self._current.rect.normalized()
            if r.width() >= self._MIN_SIZE and r.height() >= self._MIN_SIZE:
                self.canvas.add_element(self._current)
        self._current = None
        self._start = None
        self.canvas.set_preview(None)


class CurvedArrowTool(BaseTool):
    """Three-click curved arrow (quadratic Bezier with arrowhead).

    Click 1 — set start point
    Move    — ghost line to cursor
    Click 2 — set end point; curve bends as cursor moves
    Move    — control point tracks cursor; live curve preview
    Click 3 — commit element

    Esc cancels at any phase. Enter commits during phase 2.
    """

    tool_type = ToolType.CURVED_ARROW

    # Phase constants
    _PHASE_IDLE = 0   # waiting for first click
    _PHASE_END  = 1   # start set, waiting for end click
    _PHASE_CTRL = 2   # start+end set, waiting for control click

    def __init__(self, canvas):
        super().__init__(canvas)
        self._phase = self._PHASE_IDLE
        self._start: QPointF | None = None
        self._end:   QPointF | None = None
        self._preview: CurvedArrowElement | None = None

    # ── Activation ───────────────────────────────────────────────────────────

    def on_activate(self):
        self._reset()

    def on_deactivate(self):
        self._reset()

    def _reset(self):
        self._phase = self._PHASE_IDLE
        self._start = None
        self._end   = None
        self._preview = None
        self.canvas.set_preview(None)

    # ── Mouse events ─────────────────────────────────────────────────────────

    def on_press(self, pos: QPointF, event: QMouseEvent):
        if event.button() != Qt.MouseButton.LeftButton:
            return

        if self._phase == self._PHASE_IDLE:
            self._start = pos
            self._phase = self._PHASE_END
            style = self.canvas.current_style()
            self._preview = CurvedArrowElement(pos, pos, pos, style)
            self.canvas.set_preview(self._preview)

        elif self._phase == self._PHASE_END:
            self._end = pos
            self._phase = self._PHASE_CTRL
            style = self.canvas.current_style()
            self._preview = CurvedArrowElement(self._start, self._end, None, style)
            self.canvas.set_preview(self._preview)

        elif self._phase == self._PHASE_CTRL:
            if self._preview:
                self.canvas.add_element(self._preview)
            self._reset()

    def on_move(self, pos: QPointF, event: QMouseEvent):
        if self._phase == self._PHASE_END and self._preview:
            self._preview.end = pos
            self._preview.control = QPointF(
                (self._start.x() + pos.x()) / 2,
                (self._start.y() + pos.y()) / 2,
            )
            self.canvas.set_preview(self._preview)

    def on_hover(self, pos: QPointF):
        self._hover_pos = pos
        if self._phase == self._PHASE_CTRL and self._preview:
            self._preview.control = pos
            self.canvas.set_preview(self._preview)
        self.canvas.update()

    def on_key_press(self, event):
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self._reset()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self._phase == self._PHASE_CTRL and self._preview:
                self.canvas.add_element(self._preview)
                self._reset()

    # ── Hover paint ──────────────────────────────────────────────────────────

    def paint_hover(self, painter: QPainter):
        """Draw phase indicator dots and hint text near the cursor."""
        if self._phase == self._PHASE_IDLE:
            if self._hover_pos:
                painter.save()
                painter.setPen(QPen(QColor(255, 255, 255, 160), 1.5))
                painter.setBrush(QColor(116, 0, 150, 200))
                painter.drawEllipse(self._hover_pos, 5, 5)
                painter.restore()
            return

        if self._phase == self._PHASE_END and self._start and self._hover_pos:
            painter.save()
            painter.setPen(QPen(QColor(255, 171, 64, 200), 1.5))
            painter.setBrush(QColor(116, 0, 150, 180))
            painter.drawEllipse(self._start, 5, 5)
            painter.restore()
            _draw_curved_hint(painter, self._hover_pos, "Click to set end — Esc to cancel")

        elif self._phase == self._PHASE_CTRL and self._start and self._end:
            painter.save()
            painter.setPen(QPen(QColor(255, 171, 64, 200), 1.5))
            painter.setBrush(QColor(116, 0, 150, 180))
            painter.drawEllipse(self._start, 5, 5)
            painter.drawEllipse(self._end, 5, 5)
            if self._hover_pos:
                painter.setBrush(QColor(0, 188, 140, 200))
                painter.drawEllipse(self._hover_pos, 5, 5)
            painter.restore()
            if self._hover_pos:
                _draw_curved_hint(painter, self._hover_pos, "Click to commit — Enter commit — Esc cancel")


class MeasureTool(LineTool):
    """Dimension-line tool — draws a MeasureElement showing pixel distance."""
    tool_type = ToolType.MEASURE

    def on_press(self, pos: QPointF, event: QMouseEvent):
        style = self.canvas.current_style()
        self._current = MeasureElement(pos, pos, style)


def _draw_curved_hint(painter: QPainter, pos: QPointF, text: str):
    """Small translucent tooltip-style label near the cursor."""
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QFont, QFontMetrics
    font = QFont("Arial", 9)
    painter.save()
    painter.setFont(font)
    fm = QFontMetrics(font)
    tw = fm.horizontalAdvance(text) + 10
    th = fm.height() + 4
    bx = pos.x() + 14
    by = pos.y() - th - 4
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(0, 0, 0, 160))
    painter.drawRoundedRect(QRectF(bx, by, tw, th), 3, 3)
    painter.setPen(QColor(255, 255, 255, 220))
    painter.drawText(QRectF(bx, by, tw, th), Qt.AlignmentFlag.AlignCenter, text)
    painter.restore()
