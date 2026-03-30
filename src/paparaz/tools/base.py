"""Base tool interface. All drawing tools inherit from this."""

from __future__ import annotations
from enum import Enum, auto
from typing import TYPE_CHECKING, Optional
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QMouseEvent, QKeyEvent, QPainter

if TYPE_CHECKING:
    from paparaz.ui.canvas import AnnotationCanvas


class ToolType(Enum):
    SELECT = auto()
    PEN = auto()
    BRUSH = auto()
    HIGHLIGHT = auto()
    LINE = auto()
    ARROW = auto()
    RECTANGLE = auto()
    ELLIPSE = auto()
    TEXT = auto()
    NUMBERING = auto()
    FILL = auto()
    ERASER = auto()
    MASQUERADE = auto()
    STAMP = auto()
    CROP = auto()
    SLICE = auto()
    EYEDROPPER = auto()


class BaseTool:
    """Abstract base for all annotation tools."""

    tool_type: ToolType
    cursor: Qt.CursorShape = Qt.CursorShape.CrossCursor

    def __init__(self, canvas: AnnotationCanvas):
        self.canvas = canvas
        self._hover_pos: Optional[QPointF] = None

    def on_press(self, pos: QPointF, event: QMouseEvent):
        pass

    def on_move(self, pos: QPointF, event: QMouseEvent):
        pass

    def on_release(self, pos: QPointF, event: QMouseEvent):
        pass

    def on_double_click(self, pos: QPointF, event: QMouseEvent):
        """Called on double-click. Override in tools that need it."""
        pass

    def on_hover(self, pos: QPointF):
        """Called on mouse move when no buttons pressed. Update hover position."""
        self._hover_pos = pos
        self.canvas.update()

    def on_key_press(self, event: QKeyEvent):
        pass

    def paint_hover(self, painter: QPainter):
        """Paint hover preview (ghost, crosshair, highlight). Called from canvas."""
        pass

    def on_activate(self):
        pass

    def on_deactivate(self):
        self._hover_pos = None
