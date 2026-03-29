"""Special tools: Text, Numbering, Eraser, Masquerade, Fill, Stamp - with hover previews."""

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QMouseEvent, QKeyEvent, QPainter, QColor, QPen, QFont, QFontMetrics
from paparaz.tools.base import BaseTool, ToolType
from paparaz.core.elements import (
    TextElement, NumberElement, MaskElement, StampElement, ElementStyle,
)


class TextTool(BaseTool):
    """Rich text tool with hover preview, editing frame, and formatting."""

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

    def on_press(self, pos: QPointF, event: QMouseEvent):
        if self._active_text:
            if self._active_text.text.strip():
                self._active_text.editing = False
                self.canvas.add_element(self._active_text)
            self._active_text = None
            self.canvas.set_preview(None)

        style = self.canvas.current_style()
        self._active_text = TextElement(pos, "", style)
        self._active_text.editing = True
        self._apply_formatting(self._active_text)
        self.canvas.set_preview(self._active_text)

    def on_key_press(self, event: QKeyEvent):
        if not self._active_text:
            return
        key = event.key()
        mods = event.modifiers()

        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if mods & Qt.KeyboardModifier.ControlModifier:
                self._finalize()
            else:
                self._active_text.text += "\n"
                self.canvas.set_preview(self._active_text)
        elif key == Qt.Key.Key_Backspace:
            self._active_text.text = self._active_text.text[:-1]
            self.canvas.set_preview(self._active_text)
        elif key == Qt.Key.Key_Escape:
            self._finalize()
        else:
            text = event.text()
            if text and text.isprintable():
                self._active_text.text += text
                self.canvas.set_preview(self._active_text)

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
        # Remove it from committed elements and make it the active preview
        if element in self.canvas.elements:
            self.canvas.elements.remove(element)
        element.editing = True
        self._active_text = element
        self._apply_formatting(element)
        self.canvas.set_preview(element)
        self.canvas.update()

    def _finalize(self):
        if self._active_text and self._active_text.text.strip():
            self._active_text.editing = False
            self.canvas.add_element(self._active_text)
        self._active_text = None
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
        self.marker_size = 28.0
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
    """Fill tool with hover highlight on target shape."""

    tool_type = ToolType.FILL
    cursor = Qt.CursorShape.PointingHandCursor

    def __init__(self, canvas):
        super().__init__(canvas)
        self._hovered_element = None

    def on_press(self, pos: QPointF, event: QMouseEvent):
        for elem in reversed(self.canvas.elements):
            if elem.visible and elem.contains_point(pos):
                if hasattr(elem, "filled"):
                    elem.filled = True
                    elem.style.background_color = self.canvas.current_style().background_color
                    self.canvas.update()
                break

    def on_hover(self, pos: QPointF):
        self._hover_pos = pos
        hovered = None
        for elem in reversed(self.canvas.elements):
            if elem.visible and elem.contains_point(pos) and hasattr(elem, "filled"):
                hovered = elem
                break
        if hovered != self._hovered_element:
            self._hovered_element = hovered
            self.canvas.update()

    def paint_hover(self, painter: QPainter):
        if not self._hovered_element:
            return
        rect = self._hovered_element.bounding_rect()
        fill_color = QColor(self.canvas.current_style().background_color)
        fill_color.setAlpha(50)
        painter.setPen(QPen(QColor(self.canvas.current_style().background_color), 2, Qt.PenStyle.DashLine))
        painter.setBrush(fill_color)
        painter.drawRect(rect.adjusted(-2, -2, 2, 2))

    def on_deactivate(self):
        self._hovered_element = None
        super().on_deactivate()


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
