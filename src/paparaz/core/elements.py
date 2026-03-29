"""Annotation element model. Every annotation is an element that can be selected, moved, resized, deleted."""

from __future__ import annotations
import math
from dataclasses import dataclass, field


# ── Module-level rotation helpers ────────────────────────────────────────────

def _rotate_point(pt: "QPointF", center: "QPointF", degrees: float) -> "QPointF":
    """Rotate *pt* around *center* by *degrees* (clock-wise positive)."""
    rad = math.radians(degrees)
    cos_r, sin_r = math.cos(rad), math.sin(rad)
    dx = pt.x() - center.x()
    dy = pt.y() - center.y()
    return QPointF(
        center.x() + dx * cos_r - dy * sin_r,
        center.y() + dx * sin_r + dy * cos_r,
    )


def _apply_rotation(painter: "QPainter", center: "QPointF", degrees: float):
    """Translate painter to *center*, rotate, translate back. Call inside save/restore."""
    cx, cy = center.x(), center.y()
    painter.translate(cx, cy)
    painter.rotate(degrees)
    painter.translate(-cx, -cy)
from enum import Enum, auto
from typing import Optional
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QPainterPath,
    QPolygonF, QTransform, QFontMetrics, QPixmap, QImage,
)
def _scale_blur(pix: "QPixmap", radius: float) -> "QPixmap":
    """Approximate Gaussian blur via three-pass downscale/upscale (always works)."""
    w, h = pix.width(), pix.height()
    r = max(1, int(radius))
    result = pix
    for _ in range(3):
        sw = max(1, result.width()  - r * 2)
        sh = max(1, result.height() - r * 2)
        small = result.scaled(
            sw, sh,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        result = small.scaled(
            result.width(), result.height(),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    return result


class ElementType(Enum):
    PEN = auto()
    BRUSH = auto()
    HIGHLIGHT = auto()
    LINE = auto()
    ARROW = auto()
    RECTANGLE = auto()
    ELLIPSE = auto()
    TEXT = auto()
    NUMBER = auto()
    MASK = auto()
    IMAGE = auto()
    STAMP = auto()


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
        if self.rotation:
            point = _rotate_point(point, self.bounding_rect().center(), -self.rotation)
        return self.bounding_rect().contains(point)

    def paint(self, painter: QPainter):
        raise NotImplementedError

    # --- Selection colors (Flameshot purple style) ---
    SEL_COLOR       = QColor(116, 0, 150)       # #740096
    SEL_COLOR_LIGHT = QColor(116, 0, 150, 60)
    SEL_ROT_COLOR   = QColor(0, 188, 140)       # teal for rotation handle
    SEL_HANDLE_SIZE = 12
    SEL_BORDER_WIDTH = 2
    ROT_HANDLE_OFFSET = 30   # px above top-center

    def paint_selection(self, painter: QPainter):
        if not self.selected:
            return
        center = self.bounding_rect().center()

        painter.save()
        if self.rotation:
            _apply_rotation(painter, center, self.rotation)

        rect    = self.bounding_rect()
        p       = self.SEL_PADDING
        sel_rect = rect.adjusted(-p, -p, p, p)

        # Tinted overlay
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.SEL_COLOR_LIGHT)
        painter.drawRect(sel_rect)

        # Purple border
        painter.setPen(QPen(self.SEL_COLOR, self.SEL_BORDER_WIDTH))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(sel_rect)

        # White inner border
        painter.setPen(QPen(QColor(255, 255, 255, 100), 1))
        painter.drawRect(rect.adjusted(-3, -3, 3, 3))

        # Resize handles (indices 0-7)
        hs = self.SEL_HANDLE_SIZE / 2
        for hx, hy in self._handle_positions()[:8]:
            painter.setPen(QPen(QColor("white"), 2))
            painter.setBrush(self.SEL_COLOR)
            painter.drawEllipse(QPointF(hx, hy), hs, hs)

        # Rotation handle (index 8): teal circle above top-center, connected by line
        rcx = sel_rect.center().x()
        rty = sel_rect.top()
        rhy = rty - self.ROT_HANDLE_OFFSET
        painter.setPen(QPen(self.SEL_COLOR, 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawLine(QPointF(rcx, rty), QPointF(rcx, rhy))
        painter.setPen(QPen(QColor("white"), 2))
        painter.setBrush(self.SEL_ROT_COLOR)
        painter.drawEllipse(QPointF(rcx, rhy), hs, hs)

        painter.restore()

        # Info badge (drawn in world space so it doesn't spin with the element)
        self._paint_info_badge(painter, rect, center)

    def _paint_info_badge(self, painter: QPainter, rect: QRectF, center: QPointF = None):
        """Draw a floating info badge showing size and rotation."""
        if center is None:
            center = rect.center()
        w    = int(rect.width())
        h    = int(rect.height())
        text = f"{w}\u00d7{h}"
        if self.rotation:
            text += f"  {self.rotation:.0f}°"

        font = QFont("Arial", 9)
        painter.setFont(font)
        fm   = QFontMetrics(font)
        tw   = fm.horizontalAdvance(text) + 12
        th   = fm.height() + 6

        # Position badge below the element regardless of rotation
        bx = center.x() - tw / 2
        by = rect.bottom() + self.SEL_PADDING + self.ROT_HANDLE_OFFSET + 4
        badge_rect = QRectF(bx, by, tw, th)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 200))
        painter.drawRoundedRect(badge_rect, 4, 4)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, text)

    SEL_PADDING = 5

    def _handle_positions(self) -> list[tuple[float, float]]:
        """8 resize handles + 1 rotation handle (index 8) in element-local space."""
        r = self.bounding_rect().adjusted(
            -self.SEL_PADDING, -self.SEL_PADDING,
            self.SEL_PADDING, self.SEL_PADDING,
        )
        return [
            (r.left(),     r.top()),
            (r.center().x(), r.top()),
            (r.right(),    r.top()),
            (r.left(),     r.center().y()),
            (r.right(),    r.center().y()),
            (r.left(),     r.bottom()),
            (r.center().x(), r.bottom()),
            (r.right(),    r.bottom()),
            # Rotation handle
            (r.center().x(), r.top() - self.ROT_HANDLE_OFFSET),
        ]

    def handle_at(self, point: QPointF, tolerance: float = 14) -> Optional[int]:
        """Check if *point* is near any handle. Returns handle index or None."""
        if not self.selected:
            return None
        # Inverse-rotate the test point into element-local space
        test = point
        if self.rotation:
            test = _rotate_point(point, self.bounding_rect().center(), -self.rotation)
        for i, (hx, hy) in enumerate(self._handle_positions()):
            if abs(test.x() - hx) < tolerance and abs(test.y() - hy) < tolerance:
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
        """Paint a blurred shadow copy of the element, then the element itself."""
        if not self.style.shadow.enabled:
            paint_fn(painter)
            return

        blur_r = max(0.0, self.style.shadow.blur_radius)
        ox = self.style.shadow.offset_x
        oy = self.style.shadow.offset_y
        shadow_color = QColor(self.style.shadow.color)

        # Render element into an offscreen pixmap using the shadow colour
        pad = max(8, int(blur_r * 2.5) + 4)
        bounds = self.bounding_rect()
        pix_w = max(4, int(bounds.width())  + pad * 2)
        pix_h = max(4, int(bounds.height()) + pad * 2)

        shadow_pix = QPixmap(pix_w, pix_h)
        shadow_pix.fill(Qt.GlobalColor.transparent)

        sp = QPainter(shadow_pix)
        sp.setRenderHint(QPainter.RenderHint.Antialiasing)
        sp.translate(pad - bounds.x(), pad - bounds.y())
        old_fg = self.style.foreground_color
        old_bg = self.style.background_color
        self.style.foreground_color = shadow_color.name(QColor.NameFormat.HexRgb)
        self.style.background_color = shadow_color.name(QColor.NameFormat.HexRgb)
        sp.setOpacity(shadow_color.alphaF())
        paint_fn(sp)
        self.style.foreground_color = old_fg
        self.style.background_color = old_bg
        sp.end()

        # Blur via repeated downscale/upscale (guaranteed to work on all platforms)
        if blur_r >= 1.0:
            shadow_pix = _scale_blur(shadow_pix, blur_r)

        # Composite blurred shadow behind main element
        painter.save()
        painter.drawPixmap(
            int(bounds.x() + ox - pad),
            int(bounds.y() + oy - pad),
            shadow_pix,
        )
        painter.restore()

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
        if self.rotation:
            point = _rotate_point(point, self.bounding_rect().center(), -self.rotation)
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
        if self.rotation:
            painter.save()
            _apply_rotation(painter, self.bounding_rect().center(), self.rotation)
            self._paint_shadow(painter, self._paint_stroke)
            painter.restore()
        else:
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


class HighlightElement(PenElement):
    """Highlighter marker stroke — flat-cap, wide, semi-transparent (alpha from color)."""

    def __init__(self, style: Optional[ElementStyle] = None):
        super().__init__(style)
        self.element_type = ElementType.HIGHLIGHT

    def _make_pen(self) -> QPen:
        pen = QPen(QColor(self.style.foreground_color), self.style.line_width)
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        pen.setJoinStyle(Qt.PenJoinStyle.BevelJoin)
        pen.setStyle(Qt.PenStyle.SolidLine)
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
        if self.rotation:
            point = _rotate_point(point, self.bounding_rect().center(), -self.rotation)
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
        if self.rotation:
            painter.save()
            _apply_rotation(painter, self.bounding_rect().center(), self.rotation)
            self._paint_shadow(painter, self._paint_line)
            painter.restore()
        else:
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
        if self.rotation:
            point = _rotate_point(point, self.rect.normalized().center(), -self.rotation)
        if self.filled:
            return self.rect.normalized().contains(point)
        tolerance = max(self.style.line_width, 6)
        r = self.rect.normalized()
        near_left   = abs(point.x() - r.left())   < tolerance and r.top() - tolerance <= point.y() <= r.bottom() + tolerance
        near_right  = abs(point.x() - r.right())  < tolerance and r.top() - tolerance <= point.y() <= r.bottom() + tolerance
        near_top    = abs(point.y() - r.top())    < tolerance and r.left() - tolerance <= point.x() <= r.right() + tolerance
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
        if self.rotation:
            painter.save()
            _apply_rotation(painter, self.rect.normalized().center(), self.rotation)
            self._paint_shadow(painter, self._paint_rect)
            painter.restore()
        else:
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
        if self.rotation:
            point = _rotate_point(point, self.rect.normalized().center(), -self.rotation)
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
        if self.rotation:
            painter.save()
            _apply_rotation(painter, self.rect.normalized().center(), self.rotation)
            self._paint_shadow(painter, self._paint_ellipse)
            painter.restore()
        else:
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
        self.rect = QRectF(position.x(), position.y(), 150.0, 40.0)
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
        # Cursor and selection state (only meaningful during editing)
        self.cursor_pos: int = 0   # insertion point (0 = before first char)
        self.sel_start: int = -1   # -1 = no selection; otherwise anchor end

    @property
    def position(self) -> QPointF:
        return self.rect.topLeft()

    @position.setter
    def position(self, value: QPointF):
        self.rect = QRectF(value.x(), value.y(), self.rect.width(), self.rect.height())

    def _make_font(self) -> QFont:
        font = QFont(self.style.font_family, self.style.font_size)
        font.setBold(self.bold)
        font.setItalic(self.italic)
        font.setUnderline(self.underline)
        font.setStrikeOut(self.strikethrough)
        return font

    def bounding_rect(self) -> QRectF:
        return self.rect

    @staticmethod
    def _wrap_lines(text: str, fm: QFontMetrics, max_w: float) -> list:
        """Word-wrap `text` (which may contain \\n) into display lines <= max_w px wide."""
        if max_w <= 0:
            return (text or "").split("\n") or [""]
        result = []
        for raw in (text or "").split("\n"):
            if not raw:
                result.append("")
                continue
            words = raw.split(" ")
            current = words[0]
            for word in words[1:]:
                candidate = current + " " + word
                if fm.horizontalAdvance(candidate) <= max_w:
                    current = candidate
                else:
                    result.append(current)
                    current = word
            result.append(current)
        return result if result else [""]

    def _build_visual_lines(self, fm: QFontMetrics, max_w: float) -> list:
        """Return list of (line_str, char_start, char_end) for each visual line.

        char_start/char_end are indices into self.text.
        Accounts for word-wrapping within paragraphs and \\n separators.
        """
        result = []
        paragraphs = self.text.split("\n")
        pos = 0
        for pi, para in enumerate(paragraphs):
            if not para:
                result.append(("", pos, pos))
            else:
                words = para.split(" ")
                current = words[0]
                current_start = pos
                for word in words[1:]:
                    candidate = current + " " + word
                    if fm.horizontalAdvance(candidate) <= max_w:
                        current = candidate
                    else:
                        result.append((current, current_start, current_start + len(current)))
                        pos += len(current) + 1  # +1 for consumed space
                        current_start = pos
                        current = word
                result.append((current, current_start, current_start + len(current)))
                pos += len(current)
            if pi < len(paragraphs) - 1:
                pos += 1  # '\n' character
        return result

    def _cursor_to_vline(self, cursor_pos: int, vlines: list, fm: QFontMetrics) -> tuple:
        """Return (line_idx, x_offset) for cursor_pos in the visual lines list."""
        for li, (vl, vl_start, vl_end) in enumerate(vlines):
            if vl_start <= cursor_pos <= vl_end:
                x = fm.horizontalAdvance(vl[:cursor_pos - vl_start])
                return li, x
        # Cursor is past end of all lines (e.g. at len(text))
        if vlines:
            last = vlines[-1]
            return len(vlines) - 1, fm.horizontalAdvance(last[0])
        return 0, 0.0

    def sel_range(self) -> tuple[int, int] | None:
        """Return (lo, hi) of selection or None if no selection."""
        if self.sel_start < 0:
            return None
        lo, hi = min(self.sel_start, self.cursor_pos), max(self.sel_start, self.cursor_pos)
        if lo == hi:
            return None
        return lo, hi

    def auto_size(self):
        """Expand (or shrink) rect height to exactly fit all word-wrapped lines."""
        font = self._make_font()
        fm = QFontMetrics(font)
        pad = self.bg_padding if self.bg_enabled else 4
        max_w = max(1.0, self.rect.width() - 2 * pad)
        lines = self._wrap_lines(self.text, fm, max_w)
        needed = len(lines) * fm.height() + 2 * pad
        min_h  = fm.height() + 2 * pad
        self.rect = QRectF(self.rect.x(), self.rect.y(),
                           self.rect.width(), max(needed, min_h))

    def contains_point(self, point: QPointF) -> bool:
        if self.rotation:
            point = _rotate_point(point, self.rect.center(), -self.rotation)
        return self.rect.normalized().contains(point)

    def paint(self, painter: QPainter):
        if self.rotation and not self.editing:
            painter.save()
            _apply_rotation(painter, self.rect.center(), self.rotation)
            self._paint_text(painter)
            painter.restore()
            return
        self._paint_text(painter)

    def _paint_text(self, painter: QPainter):
        font = self._make_font()
        fm = QFontMetrics(font)
        rect = self.rect
        pad = self.bg_padding if self.bg_enabled else 4
        max_w = max(1.0, rect.width() - 2 * pad)
        lines = self._wrap_lines(self.text, fm, max_w)

        # Editing frame
        if self.editing:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(116, 0, 150, 20))
            painter.drawRoundedRect(rect.adjusted(-2, -2, 2, 2), 4, 4)
            painter.setPen(QPen(QColor(116, 0, 150, 180), 1.5, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(-2, -2, 2, 2), 4, 4)

        if not self.text:
            if self.editing:
                painter.setFont(font)
                painter.setPen(QColor(150, 150, 150, 120))
                painter.drawText(QPointF(rect.left() + pad, rect.top() + pad + fm.ascent()),
                                 "Type here...")
            return

        # Background
        if self.bg_enabled:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(self.bg_color))
            painter.drawRoundedRect(rect, 3, 3)

        painter.setFont(font)
        painter.setLayoutDirection(self.direction)

        for i, line in enumerate(lines):
            baseline_y = rect.top() + pad + fm.ascent() + i * fm.height()
            lw = fm.horizontalAdvance(line)

            if self.alignment == Qt.AlignmentFlag.AlignCenter:
                baseline_x = rect.left() + (rect.width() - lw) / 2
            elif self.alignment == Qt.AlignmentFlag.AlignRight:
                baseline_x = rect.right() - lw - pad
            else:
                baseline_x = rect.left() + pad

            # Shadow
            if self.style.shadow.enabled:
                painter.setPen(QColor(self.style.shadow.color))
                painter.drawText(
                    QPointF(baseline_x + self.style.shadow.offset_x,
                            baseline_y + self.style.shadow.offset_y),
                    line)

            # Text
            painter.setPen(QColor(self.style.foreground_color))
            painter.drawText(QPointF(baseline_x, baseline_y), line)

        # Selection highlight + cursor (editing mode only)
        if self.editing:
            vlines = self._build_visual_lines(fm, max_w)
            sel = self.sel_range()

            for li, (vl, vl_start, vl_end) in enumerate(vlines):
                base_y = rect.top() + pad + fm.ascent() + li * fm.height()
                lw = fm.horizontalAdvance(vl)
                if self.alignment == Qt.AlignmentFlag.AlignCenter:
                    line_x = rect.left() + (rect.width() - lw) / 2
                elif self.alignment == Qt.AlignmentFlag.AlignRight:
                    line_x = rect.right() - lw - pad
                else:
                    line_x = rect.left() + pad

                # Selection highlight for this line
                if sel:
                    lo, hi = sel
                    # Overlap between [lo,hi] and [vl_start, vl_end]
                    sel_lo = max(lo, vl_start) - vl_start
                    sel_hi = min(hi, vl_end) - vl_start
                    if 0 <= sel_lo < sel_hi <= len(vl):
                        sx = line_x + fm.horizontalAdvance(vl[:sel_lo])
                        sw = fm.horizontalAdvance(vl[sel_lo:sel_hi])
                        painter.setPen(Qt.PenStyle.NoPen)
                        painter.setBrush(QColor(116, 0, 150, 80))
                        painter.drawRect(QRectF(sx, base_y - fm.ascent(), sw, fm.height()))

            # Cursor at cursor_pos
            cli, cx_off = self._cursor_to_vline(self.cursor_pos, vlines, fm)
            vl, vl_start, vl_end = vlines[cli] if vlines else ("", 0, 0)
            lw = fm.horizontalAdvance(vl)
            base_y = rect.top() + pad + fm.ascent() + cli * fm.height()
            if self.alignment == Qt.AlignmentFlag.AlignCenter:
                line_x = rect.left() + (rect.width() - lw) / 2
            elif self.alignment == Qt.AlignmentFlag.AlignRight:
                line_x = rect.right() - lw - pad
            else:
                line_x = rect.left() + pad
            cx = line_x + cx_off
            painter.setPen(QPen(QColor(self.style.foreground_color), 2))
            painter.drawLine(QPointF(cx, base_y - fm.ascent()),
                             QPointF(cx, base_y + fm.descent()))

    def move_by(self, dx: float, dy: float):
        self.rect = QRectF(
            self.rect.x() + dx, self.rect.y() + dy,
            self.rect.width(), self.rect.height(),
        )

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["rect"] = (self.rect.x(), self.rect.y(), self.rect.width(), self.rect.height())
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

    def contains_point(self, point: QPointF) -> bool:
        if self.rotation:
            point = _rotate_point(point, self.position, -self.rotation)
        return self.bounding_rect().contains(point)

    def paint(self, painter: QPainter):
        if self.rotation:
            painter.save()
            _apply_rotation(painter, self.position, self.rotation)
            self._paint_number(painter)
            painter.restore()
        else:
            self._paint_number(painter)

    def _paint_number(self, painter: QPainter):
        rect = self.bounding_rect()
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
        if self.rotation:
            point = _rotate_point(point, self.rect.normalized().center(), -self.rotation)
        return self.rect.normalized().contains(point)

    def paint(self, painter: QPainter):
        if self.pixmap.isNull():
            return
        if self.rotation:
            painter.save()
            _apply_rotation(painter, self.rect.normalized().center(), self.rotation)
            self._paint_image(painter)
            painter.restore()
        else:
            self._paint_image(painter)

    def _paint_image(self, painter: QPainter):
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


class StampElement(AnnotationElement):
    """Predefined stamp/icon annotation (checkmark, X, OK, etc.)."""

    def __init__(self, stamp_id: str = "check", position: QPointF = QPointF(),
                 size: float = 48, style: Optional[ElementStyle] = None):
        super().__init__(ElementType.STAMP, style)
        self.stamp_id = stamp_id
        self.size = size
        self.rect = QRectF(position.x() - size / 2, position.y() - size / 2, size, size)
        self._renderer = None

    def bounding_rect(self) -> QRectF:
        return self.rect.normalized()

    def contains_point(self, point: QPointF) -> bool:
        if self.rotation:
            point = _rotate_point(point, self.rect.normalized().center(), -self.rotation)
        return self.rect.normalized().contains(point)

    def paint(self, painter: QPainter):
        if self.rotation:
            painter.save()
            _apply_rotation(painter, self.rect.normalized().center(), self.rotation)
            self._paint_stamp(painter)
            painter.restore()
        else:
            self._paint_stamp(painter)

    def _paint_stamp(self, painter: QPainter):
        from paparaz.ui.stamps import get_stamp_renderer
        r = self.rect.normalized()
        if self.style.shadow.enabled:
            painter.save()
            painter.translate(self.style.shadow.offset_x, self.style.shadow.offset_y)
            painter.setOpacity(painter.opacity() * 0.3)
            renderer = get_stamp_renderer(self.stamp_id)
            if renderer:
                renderer.render(painter, r)
            painter.restore()
        renderer = get_stamp_renderer(self.stamp_id)
        if renderer:
            renderer.render(painter, r)

    def move_by(self, dx: float, dy: float):
        self.rect = QRectF(
            self.rect.x() + dx, self.rect.y() + dy,
            self.rect.width(), self.rect.height(),
        )

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["stamp_id"] = self.stamp_id
        d["rect"] = (self.rect.x(), self.rect.y(), self.rect.width(), self.rect.height())
        return d
