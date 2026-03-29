"""Drawing tools: Pen, Brush, Line, Arrow, Rectangle, Ellipse."""

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QMouseEvent
from paparaz.tools.base import BaseTool, ToolType
from paparaz.core.history import Command
from paparaz.core.elements import (
    PenElement, BrushElement, LineElement, ArrowElement,
    RectElement, EllipseElement, ElementStyle,
)


class PenTool(BaseTool):
    tool_type = ToolType.PEN

    def __init__(self, canvas):
        super().__init__(canvas)
        self._current: PenElement | None = None

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


class BrushTool(BaseTool):
    tool_type = ToolType.BRUSH

    def __init__(self, canvas):
        super().__init__(canvas)
        self._current: BrushElement | None = None

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

    def __init__(self, canvas):
        super().__init__(canvas)
        self._current: LineElement | None = None

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

    def __init__(self, canvas):
        super().__init__(canvas)
        self._start: QPointF | None = None
        self._current: RectElement | None = None

    def on_press(self, pos: QPointF, event: QMouseEvent):
        style = self.canvas.current_style()
        self._start = pos
        self._current = RectElement(QRectF(pos, pos), False, style)

    def on_move(self, pos: QPointF, event: QMouseEvent):
        if self._current and self._start:
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
            self.canvas.add_element(self._current)
        self._current = None
        self._start = None
        self.canvas.set_preview(None)


class EllipseTool(BaseTool):
    tool_type = ToolType.ELLIPSE

    def __init__(self, canvas):
        super().__init__(canvas)
        self._start: QPointF | None = None
        self._current: EllipseElement | None = None

    def on_press(self, pos: QPointF, event: QMouseEvent):
        style = self.canvas.current_style()
        self._start = pos
        self._current = EllipseElement(QRectF(pos, pos), False, style)

    def on_move(self, pos: QPointF, event: QMouseEvent):
        if self._current and self._start:
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
            self.canvas.add_element(self._current)
        self._current = None
        self._start = None
        self.canvas.set_preview(None)
