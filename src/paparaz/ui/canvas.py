"""Main annotation canvas - renders background image and annotation elements."""

from __future__ import annotations
from typing import Optional

from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import (
    QPainter, QPixmap, QColor, QPen, QMouseEvent, QKeyEvent,
    QWheelEvent, QImage, QTransform,
)

from paparaz.core.elements import (
    AnnotationElement, ElementStyle, MaskElement, ImageElement, TextElement, Shadow,
)
from paparaz.core.history import HistoryManager, Command
from paparaz.tools.base import BaseTool, ToolType


class AnnotationCanvas(QWidget):
    """Widget that displays the captured image and handles annotation drawing."""

    tool_changed = Signal(ToolType)
    element_selected = Signal(object)  # AnnotationElement or None
    zoom_changed = Signal(float)
    request_text_edit = Signal(object)  # TextElement to re-edit

    def __init__(self, background: QPixmap, parent=None):
        super().__init__(parent)
        self._background = background
        self.elements: list[AnnotationElement] = []
        self._preview_element: Optional[AnnotationElement] = None
        self.selected_element: Optional[AnnotationElement] = None
        self._tool: Optional[BaseTool] = None
        self.history = HistoryManager(parent=self)

        # Style state (template for new elements)
        self._fg_color = "#FF0000"
        self._bg_color = "#FFFFFF"
        self._line_width = 3.0
        self._opacity = 1.0
        self._font_family = "Arial"
        self._font_size = 14
        self._shadow = Shadow()
        self._cap_style = "round"
        self._join_style = "round"
        self._dash_pattern = "solid"

        # Zoom/pan
        self._zoom = 1.0
        self._pan_offset = QPointF(0, 0)
        self._panning = False
        self._pan_start = QPointF()

        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAcceptDrops(True)
        self._update_size()

    def _update_size(self):
        w = int(self._background.width() * self._zoom)
        h = int(self._background.height() * self._zoom)
        self.setMinimumSize(w, h)

    def set_tool(self, tool: BaseTool):
        if self._tool:
            self._tool.on_deactivate()
        self._tool = tool
        self._tool.on_activate()
        self.setCursor(tool.cursor)
        self.tool_changed.emit(tool.tool_type)

    def current_style(self) -> ElementStyle:
        return ElementStyle(
            foreground_color=self._fg_color,
            background_color=self._bg_color,
            line_width=self._line_width,
            opacity=self._opacity,
            font_family=self._font_family,
            font_size=self._font_size,
            shadow=Shadow(
                enabled=self._shadow.enabled,
                offset_x=self._shadow.offset_x,
                offset_y=self._shadow.offset_y,
                blur_radius=self._shadow.blur_radius,
                color=self._shadow.color,
            ),
            cap_style=self._cap_style,
            join_style=self._join_style,
            dash_pattern=self._dash_pattern,
        )

    # --- Style setters ---

    def set_foreground_color(self, color: str):
        self._fg_color = color
        if self.selected_element:
            self.selected_element.style.foreground_color = color
            self.update()

    def set_background_color(self, color: str):
        self._bg_color = color
        if self.selected_element:
            self.selected_element.style.background_color = color
            self.update()

    def set_line_width(self, width: float):
        self._line_width = width
        if self.selected_element:
            self.selected_element.style.line_width = width
            self.update()

    def set_font_family(self, family: str):
        self._font_family = family
        if self.selected_element:
            self.selected_element.style.font_family = family
            self.update()

    def set_font_size(self, size: int):
        self._font_size = size
        if self.selected_element:
            self.selected_element.style.font_size = size
            self.update()

    def set_shadow_enabled(self, enabled: bool):
        self._shadow.enabled = enabled
        if self.selected_element:
            self.selected_element.style.shadow.enabled = enabled
            self.update()

    def set_shadow_color(self, color: str):
        self._shadow.color = color
        if self.selected_element:
            self.selected_element.style.shadow.color = color
            self.update()

    def set_shadow_offset_x(self, offset: float):
        self._shadow.offset_x = offset
        if self.selected_element:
            self.selected_element.style.shadow.offset_x = offset
            self.update()

    def set_shadow_offset_y(self, offset: float):
        self._shadow.offset_y = offset
        if self.selected_element:
            self.selected_element.style.shadow.offset_y = offset
            self.update()

    def set_shadow_blur(self, blur: float):
        self._shadow.blur_radius = blur
        if self.selected_element:
            self.selected_element.style.shadow.blur_radius = blur
            self.update()

    def set_opacity(self, opacity: float):
        self._opacity = opacity
        if self.selected_element:
            self.selected_element.style.opacity = opacity
            self.update()

    def set_cap_style(self, cap: str):
        self._cap_style = cap
        if self.selected_element:
            self.selected_element.style.cap_style = cap
            self.update()

    def set_join_style(self, join: str):
        self._join_style = join
        if self.selected_element:
            self.selected_element.style.join_style = join
            self.update()

    def set_dash_pattern(self, pattern: str):
        self._dash_pattern = pattern
        if self.selected_element:
            self.selected_element.style.dash_pattern = pattern
            self.update()

    # --- Paste ---

    def paste_from_clipboard(self):
        clipboard = QApplication.clipboard()
        pixmap = clipboard.pixmap()
        if pixmap and not pixmap.isNull():
            center = QPointF(
                self._background.width() / 2 - pixmap.width() / 2,
                self._background.height() / 2 - pixmap.height() / 2,
            )
            elem = ImageElement(pixmap, center)
            self.add_element(elem)
            self.select_element(elem)
            return True

        mime = clipboard.mimeData()
        if mime and mime.hasImage():
            img = mime.imageData()
            if img:
                pix = QPixmap.fromImage(img)
                if not pix.isNull():
                    center = QPointF(
                        self._background.width() / 2 - pix.width() / 2,
                        self._background.height() / 2 - pix.height() / 2,
                    )
                    elem = ImageElement(pix, center)
                    self.add_element(elem)
                    self.select_element(elem)
                    return True
        return False

    # --- Zoom ---

    def set_zoom(self, zoom: float):
        self._zoom = max(0.1, min(10.0, zoom))
        self._update_size()
        self.zoom_changed.emit(self._zoom)
        self.update()

    @property
    def zoom(self) -> float:
        return self._zoom

    # --- Element management ---

    def add_element(self, element: AnnotationElement):
        elem = element

        def do():
            self.elements.append(elem)
            self.update()

        def undo():
            if elem in self.elements:
                self.elements.remove(elem)
            self.update()

        cmd = Command(f"Add {elem.element_type.name}", do, undo)
        self.history.execute(cmd)

    def delete_element(self, element: AnnotationElement):
        elem = element
        index = self.elements.index(elem) if elem in self.elements else -1
        if index < 0:
            return

        def do():
            if elem in self.elements:
                self.elements.remove(elem)
            if self.selected_element == elem:
                self.selected_element = None
                self.element_selected.emit(None)
            self.update()

        def undo():
            self.elements.insert(min(index, len(self.elements)), elem)
            self.update()

        cmd = Command(f"Delete {elem.element_type.name}", do, undo)
        self.history.execute(cmd)

    def select_element(self, element: Optional[AnnotationElement]):
        if self.selected_element:
            self.selected_element.selected = False
        self.selected_element = element
        if element:
            element.selected = True
        self.element_selected.emit(element)
        self.update()

    # --- Z-order ---

    def bring_to_front(self):
        if self.selected_element and self.selected_element in self.elements:
            elem = self.selected_element
            old_idx = self.elements.index(elem)
            def do():
                if elem in self.elements:
                    self.elements.remove(elem)
                    self.elements.append(elem)
                self.update()
            def undo():
                if elem in self.elements:
                    self.elements.remove(elem)
                    self.elements.insert(min(old_idx, len(self.elements)), elem)
                self.update()
            self.history.execute(Command("Bring to front", do, undo))

    def send_to_back(self):
        if self.selected_element and self.selected_element in self.elements:
            elem = self.selected_element
            old_idx = self.elements.index(elem)
            def do():
                if elem in self.elements:
                    self.elements.remove(elem)
                    self.elements.insert(0, elem)
                self.update()
            def undo():
                if elem in self.elements:
                    self.elements.remove(elem)
                    self.elements.insert(min(old_idx, len(self.elements)), elem)
                self.update()
            self.history.execute(Command("Send to back", do, undo))

    def move_up(self):
        if self.selected_element and self.selected_element in self.elements:
            idx = self.elements.index(self.selected_element)
            if idx < len(self.elements) - 1:
                self.elements[idx], self.elements[idx + 1] = self.elements[idx + 1], self.elements[idx]
                self.update()

    def move_down(self):
        if self.selected_element and self.selected_element in self.elements:
            idx = self.elements.index(self.selected_element)
            if idx > 0:
                self.elements[idx], self.elements[idx - 1] = self.elements[idx - 1], self.elements[idx]
                self.update()

    # --- Drag & drop ---

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasImage():
            event.acceptProposedAction()

    def dropEvent(self, event):
        mime = event.mimeData()
        pos = self._screen_to_canvas(QPointF(event.position()))
        if mime.hasImage():
            img = mime.imageData()
            if img:
                pix = QPixmap.fromImage(img)
                if not pix.isNull():
                    elem = ImageElement(pix, pos)
                    self.add_element(elem)
                    self.select_element(elem)
                    return
        if mime.hasUrls():
            for url in mime.urls():
                path = url.toLocalFile()
                if path and path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')):
                    pix = QPixmap(path)
                    if not pix.isNull():
                        elem = ImageElement(pix, pos)
                        self.add_element(elem)
                        self.select_element(elem)
                        return

    def set_preview(self, element: Optional[AnnotationElement]):
        self._preview_element = element
        self.update()

    # --- Coordinate mapping ---

    def _screen_to_canvas(self, pos: QPointF) -> QPointF:
        return QPointF(
            (pos.x() - self._pan_offset.x()) / self._zoom,
            (pos.y() - self._pan_offset.y()) / self._zoom,
        )

    # --- Events ---

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        painter.translate(self._pan_offset)
        painter.scale(self._zoom, self._zoom)

        painter.drawPixmap(0, 0, self._background)

        # Mask elements first
        for elem in self.elements:
            if isinstance(elem, MaskElement) and elem.visible:
                self._paint_mask(painter, elem)

        # Non-mask elements
        for elem in self.elements:
            if not isinstance(elem, MaskElement) and elem.visible:
                painter.setOpacity(elem.style.opacity)
                elem.paint(painter)
                painter.setOpacity(1.0)

        # Preview element (during drawing)
        if self._preview_element:
            painter.setOpacity(0.85)
            self._preview_element.paint(painter)
            painter.setOpacity(1.0)

        # Tool hover preview (ghost, crosshair, highlight)
        if self._tool:
            self._tool.paint_hover(painter)

        # Selection handles (always on top)
        for elem in self.elements:
            if elem.selected:
                elem.paint_selection(painter)

        painter.end()

    def _paint_mask(self, painter: QPainter, mask: MaskElement):
        r = mask.rect.normalized().toRect()
        if r.width() < 1 or r.height() < 1:
            return
        region = self._background.copy(r)
        if region.isNull():
            return
        ps = mask.pixel_size
        small = region.scaled(
            max(1, r.width() // ps), max(1, r.height() // ps),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        pixelated = small.scaled(
            r.width(), r.height(),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        painter.setOpacity(mask.style.opacity)
        painter.drawPixmap(r.x(), r.y(), pixelated)
        painter.setOpacity(1.0)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return
        if self._tool:
            pos = self._screen_to_canvas(event.position())
            self._tool.on_press(pos, event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """Handle double-click for text re-editing."""
        if event.button() == Qt.MouseButton.LeftButton and self._tool:
            pos = self._screen_to_canvas(event.position())
            self._tool.on_double_click(pos, event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._panning:
            delta = event.position() - self._pan_start
            self._pan_offset += delta
            self._pan_start = event.position()
            self.update()
            return
        if self._tool:
            pos = self._screen_to_canvas(event.position())
            # If buttons pressed: tool drag. Otherwise: hover.
            if event.buttons() != Qt.MouseButton.NoButton:
                self._tool.on_move(pos, event)
            else:
                self._tool.on_hover(pos)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = False
            self.setCursor(self._tool.cursor if self._tool else Qt.CursorShape.ArrowCursor)
            return
        if self._tool:
            pos = self._screen_to_canvas(event.position())
            self._tool.on_release(pos, event)

    def keyPressEvent(self, event: QKeyEvent):
        if self._tool:
            self._tool.on_key_press(event)
        super().keyPressEvent(event)

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            factor = 1.1 if delta > 0 else 0.9
            self.set_zoom(self._zoom * factor)
            event.accept()
        else:
            super().wheelEvent(event)

    # --- Rendering for export ---

    def render_to_pixmap(self) -> QPixmap:
        result = QPixmap(self._background.size())
        painter = QPainter(result)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.drawPixmap(0, 0, self._background)

        for elem in self.elements:
            if isinstance(elem, MaskElement) and elem.visible:
                self._paint_mask(painter, elem)

        for elem in self.elements:
            if not isinstance(elem, MaskElement) and elem.visible:
                painter.setOpacity(elem.style.opacity)
                elem.paint(painter)
                painter.setOpacity(1.0)

        painter.end()
        return result

    def paint_annotations(self, painter: QPainter):
        for elem in self.elements:
            if elem.visible:
                painter.setOpacity(elem.style.opacity)
                elem.paint(painter)
                painter.setOpacity(1.0)
