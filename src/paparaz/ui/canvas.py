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
from paparaz.tools.select import SelectTool, _HANDLE_CURSORS


def _clone_element(elem: AnnotationElement) -> AnnotationElement:
    """Shallow-copy an element, deep-copying all Qt value types and style."""
    import copy
    new = copy.copy(elem)
    new.style = copy.copy(elem.style)
    if hasattr(elem, 'rect'):
        new.rect = QRectF(elem.rect)
    if hasattr(elem, 'start'):
        new.start = QPointF(elem.start)
    if hasattr(elem, 'end'):
        new.end = QPointF(elem.end)
    if hasattr(elem, 'points'):
        new.points = [QPointF(p) for p in elem.points]
    if hasattr(elem, 'position'):
        new.position = QPointF(elem.position)
    if hasattr(elem, 'pixmap') and elem.pixmap is not None:
        new.pixmap = QPixmap(elem.pixmap)
    return new


class AnnotationCanvas(QWidget):
    """Widget that displays the captured image and handles annotation drawing."""

    tool_changed = Signal(ToolType)
    element_selected = Signal(object)  # AnnotationElement or None
    elements_changed = Signal()        # elements list was modified (add/remove/reorder)
    zoom_changed = Signal(float)
    request_text_edit = Signal(object)  # TextElement to re-edit
    _eyedropper_done = Signal(object)   # ToolType — return-to-prev-tool signal
    fg_color_picked = Signal(str)       # eyedropper fg pick
    bg_color_picked = Signal(str)       # eyedropper bg pick

    def __init__(self, background: QPixmap, parent=None):
        super().__init__(parent)
        self._background = background
        self._canvas_bg: str = "dark"   # "dark" | "checkerboard" | "system" | hex color
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
        self._filled = False

        # Zoom/pan
        self._zoom_scroll_factor = 1.1
        self._zoom = 1.0
        self._pan_offset = QPointF(0, 0)
        self._panning = False
        self._pan_start = QPointF()

        self._element_clipboard: Optional[AnnotationElement] = None
        self._click_press_pos = QPointF()  # for click-to-deselect detection
        # Snap configuration (set by editor from settings)
        self.snap_enabled: bool = True
        self.snap_to_canvas: bool = True
        self.snap_to_elements: bool = True
        self.snap_threshold: int = 8
        self.snap_grid_enabled: bool = False
        self.snap_grid_size: int = 20
        self.show_grid: bool = False
        self._snap_guides: list = []   # current snap guide lines to render
        # Handle-intercept: lets any tool resize/rotate the selected element
        self._handle_select = SelectTool(self)
        self._handle_active = False  # True while a handle drag is in progress
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAcceptDrops(True)
        self._update_size()

    def _update_size(self):
        # Do not constrain the canvas widget to background size;
        # the editor window can be freely resized and the canvas clips to fit.
        pass

    def set_tool(self, tool: BaseTool):
        if tool is None:
            return
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
                blur_x=self._shadow.blur_x,
                blur_y=self._shadow.blur_y,
                color=self._shadow.color,
            ),
            cap_style=self._cap_style,
            join_style=self._join_style,
            dash_pattern=self._dash_pattern,
        )

    # --- Style setters ---

    def _record_style_attr(self, key: str, attr: str, old_val, new_val):
        """Record an already-applied elem.style.<attr> change for undo."""
        elem = self.selected_element
        if not elem:
            return
        def do():
            if elem in self.elements:
                setattr(elem.style, attr, new_val); self.update()
        def undo():
            if elem in self.elements:
                setattr(elem.style, attr, old_val); self.update()
        self.history.record(Command(key, do, undo), f"{key}_{id(elem)}")

    def _record_shadow_attr(self, key: str, attr: str, old_val, new_val):
        """Record an already-applied elem.style.shadow.<attr> change for undo."""
        elem = self.selected_element
        if not elem:
            return
        def do():
            if elem in self.elements:
                setattr(elem.style.shadow, attr, new_val); self.update()
        def undo():
            if elem in self.elements:
                setattr(elem.style.shadow, attr, old_val); self.update()
        self.history.record(Command(key, do, undo), f"{key}_{id(elem)}")

    def set_canvas_background(self, bg: str):
        """Set the canvas surround color. 'dark'=default, 'checkerboard', 'system', or a hex color."""
        self._canvas_bg = bg
        self.update()

    def set_zoom_scroll_factor(self, factor: float):
        """Set the scroll wheel zoom multiplier (1.05 – 1.3)."""
        self._zoom_scroll_factor = max(1.05, min(1.3, factor))

    def _paint_canvas_background(self, painter: QPainter):
        """Fill the area behind/around the screenshot with the configured background."""
        bg = self._canvas_bg
        r = self.rect()
        if bg == "checkerboard":
            cs = 16
            light = QColor(55, 55, 55)
            dark_c = QColor(38, 38, 38)
            for row in range(0, r.height(), cs):
                for col in range(0, r.width(), cs):
                    painter.fillRect(
                        col, row, cs, cs,
                        light if (row // cs + col // cs) % 2 == 0 else dark_c
                    )
        elif bg == "system":
            painter.fillRect(r, self.palette().color(self.backgroundRole()))
        elif bg not in ("dark", ""):
            painter.fillRect(r, QColor(bg))
        # "dark" — Qt paints the widget palette background automatically

    def set_foreground_color(self, color: str):
        self._fg_color = color
        if self.selected_element:
            old = self.selected_element.style.foreground_color
            self.selected_element.style.foreground_color = color
            self._record_style_attr("Fg color", "foreground_color", old, color)
            self.update()

    def set_background_color(self, color: str):
        self._bg_color = color
        if self.selected_element:
            old = self.selected_element.style.background_color
            self.selected_element.style.background_color = color
            self._record_style_attr("Bg color", "background_color", old, color)
            self.update()

    def set_line_width(self, width: float):
        self._line_width = width
        if self.selected_element:
            old = self.selected_element.style.line_width
            self.selected_element.style.line_width = width
            self._record_style_attr("Line width", "line_width", old, width)
            self.update()

    def set_font_family(self, family: str):
        self._font_family = family
        if self.selected_element:
            old = self.selected_element.style.font_family
            self.selected_element.style.font_family = family
            self._record_style_attr("Font", "font_family", old, family)
            self.update()

    def set_font_size(self, size: int):
        self._font_size = size
        if self.selected_element:
            old = self.selected_element.style.font_size
            self.selected_element.style.font_size = size
            self._record_style_attr("Font size", "font_size", old, size)
            self.update()

    def set_shadow_enabled(self, enabled: bool):
        self._shadow.enabled = enabled
        if self.selected_element:
            old = self.selected_element.style.shadow.enabled
            self.selected_element.style.shadow.enabled = enabled
            self._record_shadow_attr("Shadow", "enabled", old, enabled)
            self.update()

    def set_shadow_color(self, color: str):
        self._shadow.color = color
        if self.selected_element:
            old = self.selected_element.style.shadow.color
            self.selected_element.style.shadow.color = color
            self._record_shadow_attr("Shadow color", "color", old, color)
            self.update()

    def set_shadow_offset_x(self, offset: float):
        self._shadow.offset_x = offset
        if self.selected_element:
            old = self.selected_element.style.shadow.offset_x
            self.selected_element.style.shadow.offset_x = offset
            self._record_shadow_attr("Shadow X", "offset_x", old, offset)
            self.update()

    def set_shadow_offset_y(self, offset: float):
        self._shadow.offset_y = offset
        if self.selected_element:
            old = self.selected_element.style.shadow.offset_y
            self.selected_element.style.shadow.offset_y = offset
            self._record_shadow_attr("Shadow Y", "offset_y", old, offset)
            self.update()

    def set_shadow_blur(self, blur: float):
        self._shadow.blur_x = blur
        self._shadow.blur_y = blur
        if self.selected_element:
            old_x = self.selected_element.style.shadow.blur_x
            old_y = self.selected_element.style.shadow.blur_y
            self.selected_element.style.shadow.blur_x = blur
            self.selected_element.style.shadow.blur_y = blur
            self._record_shadow_attr("Shadow blur X", "blur_x", old_x, blur)
            self._record_shadow_attr("Shadow blur Y", "blur_y", old_y, blur)
            self.update()

    def set_shadow_blur_x(self, v: float):
        self._shadow.blur_x = v
        elem = self.selected_element
        if elem:
            elem.style.shadow.blur_x = v
            self.update()

    def set_shadow_blur_y(self, v: float):
        self._shadow.blur_y = v
        elem = self.selected_element
        if elem:
            elem.style.shadow.blur_y = v
            self.update()

    def set_opacity(self, opacity: float):
        self._opacity = opacity
        if self.selected_element:
            old = self.selected_element.style.opacity
            self.selected_element.style.opacity = opacity
            self._record_style_attr("Opacity", "opacity", old, opacity)
            self.update()

    def set_rotation(self, degrees: float):
        if self.selected_element:
            old = self.selected_element.rotation
            new = degrees % 360.0
            self.selected_element.rotation = new
            if old != new:
                elem = self.selected_element
                from paparaz.core.history import Command
                self.history.record(Command(
                    "Rotate",
                    lambda e=elem, v=new: setattr(e, 'rotation', v) or self.update(),
                    lambda e=elem, v=old: setattr(e, 'rotation', v) or self.update(),
                ))
            self.update()

    def set_cap_style(self, cap: str):
        self._cap_style = cap
        if self.selected_element:
            old = self.selected_element.style.cap_style
            self.selected_element.style.cap_style = cap
            self._record_style_attr("Cap style", "cap_style", old, cap)
            self.update()

    def set_join_style(self, join: str):
        self._join_style = join
        if self.selected_element:
            old = self.selected_element.style.join_style
            self.selected_element.style.join_style = join
            self._record_style_attr("Join style", "join_style", old, join)
            self.update()

    def set_dash_pattern(self, pattern: str):
        self._dash_pattern = pattern
        if self.selected_element:
            old = self.selected_element.style.dash_pattern
            self.selected_element.style.dash_pattern = pattern
            self._record_style_attr("Dash", "dash_pattern", old, pattern)
            self.update()

    def set_filled(self, filled: bool):
        self._filled = filled
        if self.selected_element and hasattr(self.selected_element, "filled"):
            self.selected_element.filled = filled
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
                    return True

        if mime and mime.hasText():
            text = mime.text().strip()
            if text:
                pos = QPointF(
                    self._background.width() / 2 - 75,
                    self._background.height() / 2 - 20,
                )
                elem = TextElement(pos, text, self.current_style())
                self.add_element(elem)
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

    def add_element(self, element: AnnotationElement, auto_select: bool = True):
        elem = element

        def do():
            self.elements.append(elem)
            self.update()
            self.elements_changed.emit()

        def undo():
            if elem in self.elements:
                self.elements.remove(elem)
            if self.selected_element == elem:
                self.selected_element = None
                self.element_selected.emit(None)
            self.update()
            self.elements_changed.emit()

        cmd = Command(f"Add {elem.element_type.name}", do, undo)
        self.history.execute(cmd)
        # Auto-select the just-drawn element so user can tweak properties
        if auto_select:
            self.select_element(elem)

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
            self.elements_changed.emit()

        def undo():
            self.elements.insert(min(index, len(self.elements)), elem)
            self.update()
            self.elements_changed.emit()

        cmd = Command(f"Delete {elem.element_type.name}", do, undo)
        self.history.execute(cmd)

    def select_element(self, element: Optional[AnnotationElement]):
        # Clear any multi-selection first
        for e in self.elements:
            e.selected = False
        self.selected_element = element
        if element:
            element.selected = True
        self.element_selected.emit(element)
        self.update()

    def select_multiple(self, elements: list):
        """Select a list of elements (rubber-band multi-select)."""
        for e in self.elements:
            e.selected = False
        self.selected_element = None
        for e in elements:
            e.selected = True
        if len(elements) == 1:
            self.selected_element = elements[0]
            self.element_selected.emit(elements[0])
        else:
            self.element_selected.emit(None)
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
                self.elements_changed.emit()
            def undo():
                if elem in self.elements:
                    self.elements.remove(elem)
                    self.elements.insert(min(old_idx, len(self.elements)), elem)
                self.update()
                self.elements_changed.emit()
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
                self.elements_changed.emit()
            def undo():
                if elem in self.elements:
                    self.elements.remove(elem)
                    self.elements.insert(min(old_idx, len(self.elements)), elem)
                self.update()
                self.elements_changed.emit()
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

        # Canvas background fill (area around/behind the screenshot when zoomed out)
        self._paint_canvas_background(painter)

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

        # Grid overlay
        if self.show_grid and self.snap_grid_size > 0:
            self._paint_grid(painter)

        # Selection handles (always on top)
        for elem in self.elements:
            if elem.selected:
                elem.paint_selection(painter)

        # Snap guide lines (on top of everything)
        if self._snap_guides:
            self._paint_snap_guides(painter)

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

    def _paint_grid(self, painter: QPainter):
        """Draw a subtle grid overlay."""
        gs = self.snap_grid_size
        if gs < 4:
            return
        pen = QPen(QColor(255, 255, 255, 25), 0)  # thin, semi-transparent
        painter.setPen(pen)
        w = self._background.width()
        h = self._background.height()
        x = gs
        while x < w:
            painter.drawLine(int(x), 0, int(x), h)
            x += gs
        y = gs
        while y < h:
            painter.drawLine(0, int(y), w, int(y))
            y += gs

    def _paint_snap_guides(self, painter: QPainter):
        """Draw snap alignment guide lines."""
        pen = QPen(QColor(0, 200, 255, 180), 0)
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        for g in self._snap_guides:
            if g.orientation == "v":
                painter.drawLine(int(g.value), int(g.start), int(g.value), int(g.end))
            else:
                painter.drawLine(int(g.start), int(g.value), int(g.end), int(g.value))

    def canvas_rect(self) -> QRectF:
        """Return the background image rect (canvas coordinate space)."""
        return QRectF(0, 0, self._background.width(), self._background.height())

    def _is_handle_tool(self) -> bool:
        """True when the active tool is NOT select (select handles its own handles)."""
        return bool(self._tool and self._tool.tool_type != ToolType.SELECT)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return
        self._click_press_pos = event.position()  # track for click-to-deselect
        if self._tool:
            pos = self._screen_to_canvas(event.position())
            # Intercept: if a non-select tool is active but cursor is on a handle,
            # delegate resize/rotate to the hidden SelectTool.
            if (self._is_handle_tool() and self.selected_element
                    and event.button() == Qt.MouseButton.LeftButton):
                # Use tight tolerance so drawing near a selected element
                # starts a new element instead of resizing the old one.
                handle = self.selected_element.handle_at(pos, tolerance=8)
                if handle is not None:
                    self._handle_active = True
                    self._handle_select.on_press(pos, event)
                    return
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
        if self._handle_active:
            pos = self._screen_to_canvas(event.position())
            self._handle_select.on_move(pos, event)
            return
        if self._tool:
            pos = self._screen_to_canvas(event.position())
            # If buttons pressed: tool drag. Otherwise: hover.
            if event.buttons() != Qt.MouseButton.NoButton:
                self._tool.on_move(pos, event)
            else:
                # Show handle cursors even when a non-select tool is active
                if self._is_handle_tool() and self.selected_element:
                    handle = self.selected_element.handle_at(pos, tolerance=8)
                    if handle is not None:
                        self.setCursor(_HANDLE_CURSORS.get(
                            handle, Qt.CursorShape.ArrowCursor))
                        return
                    # Restore tool cursor when leaving handles
                    if self.cursor().shape() != self._tool.cursor:
                        self.setCursor(self._tool.cursor)
                self._tool.on_hover(pos)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = False
            self.setCursor(self._tool.cursor if self._tool else Qt.CursorShape.ArrowCursor)
            return
        if self._handle_active:
            pos = self._screen_to_canvas(event.position())
            self._handle_select.on_release(pos, event)
            self._handle_active = False
            # Restore the active tool's cursor
            if self._tool:
                self.setCursor(self._tool.cursor)
            return
        if self._tool:
            pos = self._screen_to_canvas(event.position())
            self._tool.on_release(pos, event)
            # Click-to-deselect: if user clicked (not dragged) on empty area,
            # deselect any selected element regardless of active tool.
            if (self.selected_element
                    and event.button() == Qt.MouseButton.LeftButton
                    and hasattr(self, '_click_press_pos')):
                delta = event.position() - self._click_press_pos
                is_click = abs(delta.x()) < 4 and abs(delta.y()) < 4
                if is_click:
                    hit = any(
                        e.visible and not e.locked and e.contains_point(pos)
                        for e in self.elements
                    )
                    if not hit:
                        self.select_element(None)

    def contextMenuEvent(self, event):
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QContextMenuEvent

        # Only show for SELECT tool (crop/slice handle right-click themselves)
        if not self._tool or self._tool.tool_type != ToolType.SELECT:
            event.ignore()
            return

        canvas_pos = self._screen_to_canvas(QPointF(event.pos()))

        clicked_elem = None
        for elem in reversed(self.elements):
            if elem.visible and not elem.locked and elem.contains_point(canvas_pos):
                clicked_elem = elem
                break

        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background: #1e1e2e; color: #ccc; border: 1px solid #555; "
            "        font-size: 12px; padding: 2px; } "
            "QMenu::item { padding: 5px 20px 5px 12px; } "
            "QMenu::item:selected { background: #740096; color: #fff; } "
            "QMenu::separator { background: #444; height: 1px; margin: 3px 8px; }"
        )

        copy_act = dup_act = del_act = paste_elem_act = paste_img_act = None
        ocr_act = del_multi_act = None

        # Multi-selection menu (rubber-band or shift+click)
        multi = getattr(self._tool, '_multi_selected', [])
        if len(multi) > 1:
            ocr_act = menu.addAction(f"Recognize text (OCR)  [{len(multi)} objects]")
            menu.addSeparator()
            del_multi_act = menu.addAction(f"Delete {len(multi)} selected objects")
        elif clicked_elem:
            if clicked_elem is not self.selected_element:
                self.select_element(clicked_elem)
            copy_act = menu.addAction("Copy")
            dup_act  = menu.addAction("Duplicate")
            menu.addSeparator()
            del_act  = menu.addAction("Delete")

        if self._element_clipboard:
            if menu.actions():
                menu.addSeparator()
            paste_elem_act = menu.addAction("Paste")

        clipboard = QApplication.clipboard()
        cb_pix = clipboard.pixmap()
        if cb_pix and not cb_pix.isNull():
            if menu.actions():
                menu.addSeparator()
            paste_img_act = menu.addAction("Paste image from clipboard")

        if not menu.actions():
            return

        action = menu.exec(event.globalPos())
        if action is None:
            return
        if ocr_act and action == ocr_act:
            from paparaz.ui.ocr import ocr_selected_elements
            ocr_selected_elements(self, list(multi))
        elif del_multi_act and action == del_multi_act:
            from paparaz.core.history import Command
            to_del = [e for e in list(multi) if e in self.elements]
            indices = {id(e): self.elements.index(e) for e in to_del}
            def _do(es=to_del):
                for e in es:
                    if e in self.elements:
                        self.elements.remove(e)
                    e.selected = False
                self.selected_element = None
                self.element_selected.emit(None)
                self.update()
            def _undo(es=to_del, idx=indices):
                for e in reversed(es):
                    i = idx[id(e)]
                    self.elements.insert(min(i, len(self.elements)), e)
                self.update()
            self.history.execute(Command("Delete selected", _do, _undo))
            multi.clear()
        elif copy_act and action == copy_act:
            self.copy_element(clicked_elem)
        elif dup_act and action == dup_act:
            new = _clone_element(clicked_elem)
            new.move_by(20, 20)
            self.add_element(new)
        elif del_act and action == del_act:
            self.delete_element(clicked_elem)
        elif paste_elem_act and action == paste_elem_act:
            self.paste_element()
        elif paste_img_act and action == paste_img_act:
            self.paste_from_clipboard()

    def keyPressEvent(self, event: QKeyEvent):
        if self._tool:
            self._tool.on_key_press(event)
        super().keyPressEvent(event)

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            factor = self._zoom_scroll_factor if delta > 0 else (1.0 / self._zoom_scroll_factor)
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

    # --- Canvas resize / crop ---

    def resize_canvas(self, new_w: int, new_h: int):
        """Create a new canvas of given size, centered on old content. Undoable."""
        old_bg = QPixmap(self._background)

        def do():
            new_bg = QPixmap(new_w, new_h)
            new_bg.fill(QColor(255, 255, 255))
            p = QPainter(new_bg)
            ox = (new_w - old_bg.width()) // 2
            oy = (new_h - old_bg.height()) // 2
            p.drawPixmap(ox, oy, old_bg)
            p.end()
            for elem in self.elements:
                elem.move_by(ox, oy)
            self._background = new_bg
            self._update_size()
            self.update()

        def undo():
            # Compute the same offset that do() used, then reverse it
            ox = (self._background.width() - old_bg.width()) // 2
            oy = (self._background.height() - old_bg.height()) // 2
            for elem in self.elements:
                elem.move_by(-ox, -oy)
            self._background = QPixmap(old_bg)
            self._update_size()
            self.update()

        self.history.execute(Command("Resize canvas", do, undo))

    def copy_element(self, elem: AnnotationElement):
        """Store a clone of elem in the internal element clipboard."""
        if elem is None:
            return
        self._element_clipboard = _clone_element(elem)

    def paste_element(self):
        """Paste the previously copied element, offset by 20px."""
        if self._element_clipboard is None:
            return
        new = _clone_element(self._element_clipboard)
        new.move_by(20, 20)
        self.add_element(new)

    def crop_canvas(self, rect: QRectF):
        """Crop the canvas to given rect (in canvas coordinates). Undoable."""
        old_bg = QPixmap(self._background)
        bg_rect = QRectF(0, 0, old_bg.width(), old_bg.height())
        crop = rect.intersected(bg_rect).toRect()
        if crop.width() < 1 or crop.height() < 1:
            return
        ox, oy = -crop.x(), -crop.y()

        def do():
            for elem in self.elements:
                elem.move_by(ox, oy)
            self._background = old_bg.copy(crop)
            self._update_size()
            self.update()

        def undo():
            for elem in self.elements:
                elem.move_by(-ox, -oy)
            self._background = QPixmap(old_bg)
            self._update_size()
            self.update()

        self.history.execute(Command("Crop canvas", do, undo))
