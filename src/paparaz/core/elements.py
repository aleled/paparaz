"""Annotation element model. Every annotation is an element that can be selected, moved, resized, deleted."""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QPainterPath,
    QPolygonF, QTransform, QFontMetrics,
)


class ElementType(Enum):
    PEN = auto()
    BRUSH = auto()
    LINE = auto()
    ARROW = auto()
    RECTANGLE = auto()
    ELLIPSE = auto()
    TEXT = auto()
    NUMBER = auto()
    MASK = auto()
    IMAGE = auto()


# Line cap/join constants for UI
CAP_STYLES = {
    "round": Qt.PenCapStyle.RoundCap,
    "square": Qt.PenCapStyle.SquareCap,
    "flat": Qt.PenCapStyle.FlatCap,
}
JOIN_STYLES = {
    "round": Qt.PenJoinStyle.RoundJoin,
    "bevel": Qt.PenJoinStyle.BevelJoin,
    "miter": Qt.PenJoinStyle.MiterJoin,
}
DASH_PATTERNS = {
    "solid": Qt.PenStyle.SolidLine,
    "dash": Qt.PenStyle.DashLine,
    "dot": Qt.PenStyle.DotLine,
    "dashdot": Qt.PenStyle.DashDotLine,
}


@dataclass
class Shadow:
    enabled: bool = False
    offset_x: float = 3.0
    offset_y: float = 3.0
    blur_radius: float = 5.0
    color: str = "#80000000"


@dataclass
class ElementStyle:
    foreground_color: str = "#FF0000"
    background_color: str = "#FFFFFF"
    line_width: float = 3.0
    opacity: float = 1.0
    shadow: Shadow = field(default_factory=Shadow)
    font_family: str = "Arial"
    font_size: int = 14
    cap_style: str = "round"    # round, square, flat
    join_style: str = "round"   # round, bevel, miter
    dash_pattern: str = "solid" # solid, dash, dot, dashdot


class AnnotationElement:
    """Base class for all annotation elements."""

    _counter = 0

    def __init__(self, element_type: ElementType, style: Optional[ElementStyle] = None):
        AnnotationElement._counter += 1
        self.id = AnnotationElement._counter
        self.element_type = element_type
        self.style = style or ElementStyle()
        self.selected = False
        self.visible = True
        self.locked = False
        self.rotation = 0.0

    def bounding_rect(self) -> QRectF:
        raise NotImplementedError

    def contains_point(self, point: QPointF) -> bool:
        return self.bounding_rect().contains(point)

    def paint(self, painter: QPainter):
        raise NotImplementedError

    # --- Selection colors (Flameshot purple style) ---
    SEL_COLOR = QColor(116, 0, 150)       # #740096
    SEL_COLOR_LIGHT = QColor(116, 0, 150, 60)
    SEL_HANDLE_SIZE = 12
    SEL_BORDER_WIDTH = 2

    def paint_selection(self, painter: QPainter):
        if not self.selected:
            return
        rect = self.bounding_rect()
        sel_rect = rect.adjusted(-5, -5, 5, 5)

        # Tinted overlay on bounding rect
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.SEL_COLOR_LIGHT)
        painter.drawRect(sel_rect)

        # Purple border
        painter.setPen(QPen(self.SEL_COLOR, self.SEL_BORDER_WIDTH))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(sel_rect)

        # White inner border for contrast
        painter.setPen(QPen(QColor(255, 255, 255, 100), 1))
        painter.drawRect(rect.adjusted(-3, -3, 3, 3))

        # Circular handles (Flameshot-style)
        hs = self.SEL_HANDLE_SIZE / 2
        for hx, hy in self._handle_positions():
            # White outline circle
            painter.setPen(QPen(QColor("white"), 2))
            painter.setBrush(self.SEL_COLOR)
            painter.drawEllipse(QPointF(hx, hy), hs, hs)

        # Dimension badge
        self._paint_info_badge(painter, rect)

    def _paint_info_badge(self, painter: QPainter, rect: QRectF):
        """Draw a floating info badge showing position and size."""
        w = int(rect.width())
        h = int(rect.height())
        x = int(rect.x())
        y = int(rect.y())
        text = f"{w}\u00d7{h}  ({x}, {y})"

        font = QFont("Arial", 9)
        painter.setFont(font)
        fm = QFontMetrics(font)
        tw = fm.horizontalAdvance(text) + 12
        th = fm.height() + 6

        # Position: below selection, centered
        bx = rect.center().x() - tw / 2
        by = rect.bottom() + 10
        badge_rect = QRectF(bx, by, tw, th)

        # Badge background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 200))
        painter.drawRoundedRect(badge_rect, 4, 4)

        # Badge text
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, text)

    def _handle_positions(self) -> list[tuple[float, float]]:
        r = self.bounding_rect()
        return [
            (r.left(), r.top()), (r.center().x(), r.top()), (r.right(), r.top()),
            (r.left(), r.center().y()), (r.right(), r.center().y()),
            (r.left(), r.bottom()), (r.center().x(), r.bottom()), (r.right(), r.bottom()),
        ]

    def handle_at(self, point: QPointF, tolerance: float = 10) -> Optional[int]:
        if not self.selected:
            return None
        for i, (hx, hy) in enumerate(self._handle_positions()):
            if abs(point.x() - hx) < tolerance and abs(point.y() - hy) < tolerance:
                return i
        return None

    def move_by(self, dx: float, dy: float):
        raise NotImplementedError

    def _make_pen(self) -> QPen:
        pen = QPen(QColor(self.style.foreground_color), self.style.line_width)
        pen.setCapStyle(CAP_STYLES.get(self.style.cap_style, Qt.PenCapStyle.RoundCap))
        pen.setJoinStyle(JOIN_STYLES.get(self.style.join_style, Qt.PenJoinStyle.RoundJoin))
        pen.setStyle(DASH_PATTERNS.get(self.style.dash_pattern, Qt.PenStyle.SolidLine))
        return pen

    def _paint_shadow(self, painter: QPainter, paint_fn):
        """Paint a shadow copy of the element, then the element itself."""
        if not self.style.shadow.enabled:
            paint_fn(painter)
            return
        # Save state, draw shadow offset copy
        painter.save()
        painter.translate(self.style.shadow.offset_x, self.style.shadow.offset_y)
        painter.setOpacity(painter.opacity() * 0.4)
        shadow_color = QColor(self.style.shadow.color)
        # Override pen/brush to shadow color
        old_fg = self.style.foreground_color
        old_bg = self.style.background_color
        self.style.foreground_color = shadow_color.name()
        self.style.background_color = shadow_color.name()
        paint_fn(painter)
        self.style.foreground_color = old_fg
        self.style.background_color = old_bg
        painter.restore()
        # Draw actual element
        paint_fn(painter)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.element_type.name,
            "style": {
                "foreground_color": self.style.foreground_color,
                "background_color": self.style.background_color,
                "line_width": self.style.line_width,
                "opacity": self.style.opacity,
                "font_family": self.style.font_family,
                "font_size": self.style.font_size,
                "cap_style": self.style.cap_style,
                "join_style": self.style.join_style,
                "dash_pattern": self.style.dash_pattern,
                "shadow": {
                    "enabled": self.style.shadow.enabled,
                    "offset_x": self.style.shadow.offset_x,
                    "offset_y": self.style.shadow.offset_y,
                    "blur_radius": self.style.shadow.blur_radius,
                    "color": self.style.shadow.color,
                },
            },
            "rotation": self.rotation,
            "visible": self.visible,
        }


class PenElement(AnnotationElement):
    """Freehand pen stroke."""

    def __init__(self, style: Optional[ElementStyle] = None):
        super().__init__(ElementType.PEN, style)
        self.points: list[QPointF] = []

    def add_point(self, point: QPointF):
        self.points.append(point)

    def bounding_rect(self) -> QRectF:
        if not self.points:
            return QRectF()
        xs = [p.x() for p in self.points]
        ys = [p.y() for p in self.points]
        pad = self.style.line_width / 2
        return QRectF(
            min(xs) - pad, min(ys) - pad,
            max(xs) - min(xs) + self.style.line_width,
            max(ys) - min(ys) + self.style.line_width,
        )

    def contains_point(self, point: QPointF) -> bool:
        tolerance = max(self.style.line_width, 6)
        for p in self.points:
            if (point - p).manhattanLength() < tolerance:
                return True
        return False

    def _paint_stroke(self, painter: QPainter):
        if len(self.points) < 2:
            return
        painter.setPen(self._make_pen())
        painter.setBrush(Qt.BrushStyle.NoBrush)
        path = QPainterPath(self.points[0])
        for p in self.points[1:]:
            path.lineTo(p)
        painter.drawPath(path)

    def paint(self, painter: QPainter):
        if len(self.points) < 2:
            return
        self._paint_shadow(painter, self._paint_stroke)

    def move_by(self, dx: float, dy: float):
        self.points = [QPointF(p.x() + dx, p.y() + dy) for p in self.points]

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["points"] = [(p.x(), p.y()) for p in self.points]
        return d


class BrushElement(PenElement):
    """Soft brush stroke - like pen but with rounded, thicker, semi-transparent strokes."""

    def __init__(self, style: Optional[ElementStyle] = None):
        super().__init__(style)
        self.element_type = ElementType.BRUSH

    def _make_pen(self) -> QPen:
        pen = super()._make_pen()
        pen.setWidth(int(self.style.line_width * 2.5))
        color = QColor(self.style.foreground_color)
        color.setAlpha(120)
        pen.setColor(color)
        return pen


class LineElement(AnnotationElement):
    """Straight line."""

    def __init__(self, start: QPointF = QPointF(), end: QPointF = QPointF(),
                 style: Optional[ElementStyle] = None):
        super().__init__(ElementType.LINE, style)
        self.start = start
        self.end = end

    def bounding_rect(self) -> QRectF:
        pad = self.style.line_width / 2
        return QRectF(self.start, self.end).normalized().adjusted(-pad, -pad, pad, pad)

    def contains_point(self, point: QPointF) -> bool:
        tolerance = max(self.style.line_width, 6)
        dx = self.end.x() - self.start.x()
        dy = self.end.y() - self.start.y()
        length_sq = dx * dx + dy * dy
        if length_sq == 0:
            return (point - self.start).manhattanLength() < tolerance
        t = max(0, min(1, (
            (point.x() - self.start.x()) * dx + (point.y() - self.start.y()) * dy
        ) / length_sq))
        proj = QPointF(self.start.x() + t * dx, self.start.y() + t * dy)
        dist = math.sqrt((point.x() - proj.x()) ** 2 + (point.y() - proj.y()) ** 2)
        return dist < tolerance

    def _paint_line(self, painter: QPainter):
        painter.setPen(self._make_pen())
        painter.drawLine(self.start, self.end)

    def paint(self, painter: QPainter):
        self._paint_shadow(painter, self._paint_line)

    def move_by(self, dx: float, dy: float):
        self.start = QPointF(self.start.x() + dx, self.start.y() + dy)
        self.end = QPointF(self.end.x() + dx, self.end.y() + dy)

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["start"] = (self.start.x(), self.start.y())
        d["end"] = (self.end.x(), self.end.y())
        return d


class ArrowElement(LineElement):
    """Line with arrowhead."""

    def __init__(self, start: QPointF = QPointF(), end: QPointF = QPointF(),
                 style: Optional[ElementStyle] = None):
        super().__init__(start, end, style)
        self.element_type = ElementType.ARROW

    def _paint_line(self, painter: QPainter):
        pen = self._make_pen()
        painter.setPen(pen)
        painter.drawLine(self.start, self.end)

        dx = self.end.x() - self.start.x()
        dy = self.end.y() - self.start.y()
        length = math.sqrt(dx * dx + dy * dy)
        if length < 1:
            return

        arrow_size = max(12, self.style.line_width * 4)
        angle = math.atan2(dy, dx)

        p1 = QPointF(
            self.end.x() - arrow_size * math.cos(angle - math.pi / 6),
            self.end.y() - arrow_size * math.sin(angle - math.pi / 6),
        )
        p2 = QPointF(
            self.end.x() - arrow_size * math.cos(angle + math.pi / 6),
            self.end.y() - arrow_size * math.sin(angle + math.pi / 6),
        )

        painter.setBrush(QColor(self.style.foreground_color))
        painter.drawPolygon(QPolygonF([self.end, p1, p2]))


class RectElement(AnnotationElement):
    """Rectangle annotation."""

    def __init__(self, rect: QRectF = QRectF(), filled: bool = False,
                 style: Optional[ElementStyle] = None):
        super().__init__(ElementType.RECTANGLE, style)
        self.rect = rect
        self.filled = filled

    def bounding_rect(self) -> QRectF:
        pad = self.style.line_width / 2
        return self.rect.normalized().adjusted(-pad, -pad, pad, pad)

    def contains_point(self, point: QPointF) -> bool:
        if self.filled:
            return self.rect.normalized().contains(point)
        tolerance = max(self.style.line_width, 6)
        r = self.rect.normalized()
        near_left = abs(point.x() - r.left()) < tolerance and r.top() - tolerance <= point.y() <= r.bottom() + tolerance
        near_right = abs(point.x() - r.right()) < tolerance and r.top() - tolerance <= point.y() <= r.bottom() + tolerance
        near_top = abs(point.y() - r.top()) < tolerance and r.left() - tolerance <= point.x() <= r.right() + tolerance
        near_bottom = abs(point.y() - r.bottom()) < tolerance and r.left() - tolerance <= point.x() <= r.right() + tolerance
        return near_left or near_right or near_top or near_bottom

    def _paint_rect(self, painter: QPainter):
        painter.setPen(self._make_pen())
        if self.filled:
            painter.setBrush(QColor(self.style.background_color))
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(self.rect.normalized())

    def paint(self, painter: QPainter):
        self._paint_shadow(painter, self._paint_rect)

    def move_by(self, dx: float, dy: float):
        self.rect = QRectF(
            self.rect.x() + dx, self.rect.y() + dy,
            self.rect.width(), self.rect.height(),
        )

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["rect"] = (self.rect.x(), self.rect.y(), self.rect.width(), self.rect.height())
        d["filled"] = self.filled
        return d


class EllipseElement(AnnotationElement):
    """Ellipse/circle annotation."""

    def __init__(self, rect: QRectF = QRectF(), filled: bool = False,
                 style: Optional[ElementStyle] = None):
        super().__init__(ElementType.ELLIPSE, style)
        self.rect = rect
        self.filled = filled

    def bounding_rect(self) -> QRectF:
        pad = self.style.line_width / 2
        return self.rect.normalized().adjusted(-pad, -pad, pad, pad)

    def contains_point(self, point: QPointF) -> bool:
        r = self.rect.normalized()
        cx, cy = r.center().x(), r.center().y()
        rx, ry = r.width() / 2, r.height() / 2
        if rx == 0 or ry == 0:
            return False
        val = ((point.x() - cx) / rx) ** 2 + ((point.y() - cy) / ry) ** 2
        if self.filled:
            return val <= 1.0
        tolerance = max(self.style.line_width, 6) / min(rx, ry)
        return abs(val - 1.0) < tolerance

    def _paint_ellipse(self, painter: QPainter):
        painter.setPen(self._make_pen())
        if self.filled:
            painter.setBrush(QColor(self.style.background_color))
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(self.rect.normalized())

    def paint(self, painter: QPainter):
        self._paint_shadow(painter, self._paint_ellipse)

    def move_by(self, dx: float, dy: float):
        self.rect = QRectF(
            self.rect.x() + dx, self.rect.y() + dy,
            self.rect.width(), self.rect.height(),
        )

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["rect"] = (self.rect.x(), self.rect.y(), self.rect.width(), self.rect.height())
        d["filled"] = self.filled
        return d


class TextElement(AnnotationElement):
    """Rich text annotation with font, alignment, direction, background, and shadow."""

    def __init__(self, position: QPointF = QPointF(), text: str = "",
                 style: Optional[ElementStyle] = None):
        super().__init__(ElementType.TEXT, style)
        self.position = position
        self.text = text
        self.editing = False
        self.bold = False
        self.italic = False
        self.underline = False
        self.strikethrough = False
        self.alignment = Qt.AlignmentFlag.AlignLeft
        self.direction = Qt.LayoutDirection.LeftToRight
        self.bg_enabled = False
        self.bg_color = "#FFFF00"
        self.bg_padding = 4

    def _make_font(self) -> QFont:
        font = QFont(self.style.font_family, self.style.font_size)
        font.setBold(self.bold)
        font.setItalic(self.italic)
        font.setUnderline(self.underline)
        font.setStrikeOut(self.strikethrough)
        return font

    def bounding_rect(self) -> QRectF:
        font = self._make_font()
        fm = QFontMetrics(font)
        display = self.text if self.text else "Ag"
        lines = display.split("\n")
        max_w = max(fm.horizontalAdvance(line) for line in lines) if lines else 50
        line_h = fm.height()
        total_h = line_h * len(lines)
        pad = self.bg_padding if self.bg_enabled else 0
        return QRectF(
            self.position.x() - pad,
            self.position.y() - line_h - pad,
            max(max_w + pad * 2, 50),
            total_h + pad * 2,
        )

    def paint(self, painter: QPainter):
        font = self._make_font()
        fm = QFontMetrics(font)
        lines = self.text.split("\n") if self.text else []

        rect = self.bounding_rect()

        # Editing frame: visible border around text area while editing
        if self.editing:
            # Light fill to mark the text area
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(116, 0, 150, 20))
            painter.drawRoundedRect(rect.adjusted(-2, -2, 2, 2), 4, 4)
            # Dashed purple border
            painter.setPen(QPen(QColor(116, 0, 150, 180), 1.5, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(-2, -2, 2, 2), 4, 4)

        if not lines:
            # Show placeholder when editing with no text yet
            if self.editing:
                painter.setFont(font)
                painter.setPen(QColor(150, 150, 150, 120))
                painter.drawText(self.position, "Type here...")
            return

        # Background
        if self.bg_enabled:
            painter.setPen(Qt.PenStyle.NoPen)
            bg = QColor(self.bg_color)
            bg.setAlpha(200)
            painter.setBrush(bg)
            painter.drawRoundedRect(rect, 3, 3)

        # Shadow
        if self.style.shadow.enabled:
            shadow_color = QColor(self.style.shadow.color)
            painter.setFont(font)
            painter.setPen(shadow_color)
            for i, line in enumerate(lines):
                y = self.position.y() + i * fm.height() + self.style.shadow.offset_y
                x = self.position.x() + self.style.shadow.offset_x
                painter.drawText(QPointF(x, y), line)

        # Text
        painter.setFont(font)
        painter.setPen(QColor(self.style.foreground_color))
        painter.setLayoutDirection(self.direction)

        line_h = fm.height()
        for i, line in enumerate(lines):
            y = self.position.y() + i * line_h

            if self.alignment == Qt.AlignmentFlag.AlignCenter:
                lw = fm.horizontalAdvance(line)
                x = self.position.x() + (rect.width() - lw) / 2 - (self.bg_padding if self.bg_enabled else 0)
            elif self.alignment == Qt.AlignmentFlag.AlignRight:
                lw = fm.horizontalAdvance(line)
                x = self.position.x() + rect.width() - lw - (self.bg_padding * 2 if self.bg_enabled else 0)
            else:
                x = self.position.x()

            painter.drawText(QPointF(x, y), line)

        # Blinking cursor when editing
        if self.editing:
            last_line = lines[-1] if lines else ""
            cx = self.position.x() + fm.horizontalAdvance(last_line)
            cy_top = self.position.y() + (len(lines) - 1) * line_h - fm.ascent()
            cy_bot = cy_top + line_h
            painter.setPen(QPen(QColor(self.style.foreground_color), 2))
            painter.drawLine(QPointF(cx, cy_top), QPointF(cx, cy_bot))

    def move_by(self, dx: float, dy: float):
        self.position = QPointF(self.position.x() + dx, self.position.y() + dy)

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["position"] = (self.position.x(), self.position.y())
        d["text"] = self.text
        d["bold"] = self.bold
        d["italic"] = self.italic
        d["underline"] = self.underline
        d["strikethrough"] = self.strikethrough
        d["bg_enabled"] = self.bg_enabled
        d["bg_color"] = self.bg_color
        return d


class NumberElement(AnnotationElement):
    """Auto-incrementing numbered marker."""

    _next_number = 1

    @classmethod
    def reset_counter(cls):
        cls._next_number = 1

    def __init__(self, position: QPointF = QPointF(), number: Optional[int] = None,
                 size: float = 28, text_color: str = "",
                 style: Optional[ElementStyle] = None):
        super().__init__(ElementType.NUMBER, style)
        self.position = position
        self.size = size
        self.text_color = text_color  # Empty = auto-contrast
        if number is None:
            self.number = NumberElement._next_number
            NumberElement._next_number += 1
        else:
            self.number = number

    def _get_text_color(self) -> QColor:
        if self.text_color:
            return QColor(self.text_color)
        # Auto-contrast: white on dark, black on light
        fg = QColor(self.style.foreground_color)
        return QColor("#FFFFFF") if fg.lightness() < 128 else QColor("#000000")

    def bounding_rect(self) -> QRectF:
        return QRectF(
            self.position.x() - self.size / 2, self.position.y() - self.size / 2,
            self.size, self.size,
        )

    def paint(self, painter: QPainter):
        rect = self.bounding_rect()

        # Shadow
        if self.style.shadow.enabled:
            painter.save()
            painter.translate(self.style.shadow.offset_x, self.style.shadow.offset_y)
            painter.setOpacity(painter.opacity() * 0.4)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(self.style.shadow.color))
            painter.drawEllipse(rect)
            painter.restore()

        painter.setPen(QPen(QColor(self.style.foreground_color), 2))
        painter.setBrush(QColor(self.style.foreground_color))
        painter.drawEllipse(rect)

        painter.setPen(self._get_text_color())
        font = QFont(self.style.font_family, int(self.size * 0.45), QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(self.number))

    def move_by(self, dx: float, dy: float):
        self.position = QPointF(self.position.x() + dx, self.position.y() + dy)

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["position"] = (self.position.x(), self.position.y())
        d["number"] = self.number
        d["size"] = self.size
        d["text_color"] = self.text_color
        return d


class MaskElement(AnnotationElement):
    """Blur/pixelate mask region."""

    def __init__(self, rect: QRectF = QRectF(), pixel_size: int = 10,
                 style: Optional[ElementStyle] = None):
        super().__init__(ElementType.MASK, style)
        self.rect = rect
        self.pixel_size = pixel_size

    def bounding_rect(self) -> QRectF:
        return self.rect.normalized()

    def paint(self, painter: QPainter):
        # Actual pixelation is handled by canvas. This draws the indicator overlay.
        r = self.rect.normalized()
        painter.setPen(QPen(QColor(180, 180, 180, 200), 1, Qt.PenStyle.DashLine))
        painter.setBrush(QColor(128, 128, 128, 80))
        painter.drawRect(r)

    def move_by(self, dx: float, dy: float):
        self.rect = QRectF(
            self.rect.x() + dx, self.rect.y() + dy,
            self.rect.width(), self.rect.height(),
        )

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["rect"] = (self.rect.x(), self.rect.y(), self.rect.width(), self.rect.height())
        d["pixel_size"] = self.pixel_size
        return d


class ImageElement(AnnotationElement):
    """Pasted image element (from clipboard or file)."""

    def __init__(self, pixmap=None, position: QPointF = QPointF(),
                 style: Optional[ElementStyle] = None):
        super().__init__(ElementType.IMAGE, style)
        from PySide6.QtGui import QPixmap as QP
        self.pixmap: QP = pixmap or QP()
        self.position = position
        self._width = float(self.pixmap.width()) if not self.pixmap.isNull() else 100.0
        self._height = float(self.pixmap.height()) if not self.pixmap.isNull() else 100.0
        self.rect = QRectF(position.x(), position.y(), self._width, self._height)

    def bounding_rect(self) -> QRectF:
        return self.rect.normalized()

    def contains_point(self, point: QPointF) -> bool:
        return self.rect.normalized().contains(point)

    def paint(self, painter: QPainter):
        if self.pixmap.isNull():
            return
        r = self.rect.normalized()
        if self.style.shadow.enabled:
            painter.save()
            painter.translate(self.style.shadow.offset_x, self.style.shadow.offset_y)
            painter.setOpacity(painter.opacity() * 0.3)
            painter.fillRect(r.toRect(), QColor(0, 0, 0))
            painter.restore()
        painter.drawPixmap(r.toRect(), self.pixmap)

    def move_by(self, dx: float, dy: float):
        self.rect = QRectF(
            self.rect.x() + dx, self.rect.y() + dy,
            self.rect.width(), self.rect.height(),
        )

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["rect"] = (self.rect.x(), self.rect.y(), self.rect.width(), self.rect.height())
        return d
