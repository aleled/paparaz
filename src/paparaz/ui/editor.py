"""Frameless aero-style editor - canvas with floating toolbar, no window chrome."""

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFileDialog, QApplication,
)
from PySide6.QtCore import Qt, Signal, QPoint, QRectF
from PySide6.QtGui import QPixmap, QKeySequence, QShortcut, QPainter, QColor

from paparaz.ui.canvas import AnnotationCanvas
from paparaz.ui.toolbar import FlameshotToolbar
from paparaz.ui.side_panel import SidePanel
from paparaz.tools.base import ToolType
from paparaz.tools.select import SelectTool
from paparaz.tools.drawing import (
    PenTool, BrushTool, LineTool, ArrowTool, RectangleTool, EllipseTool,
)
from paparaz.tools.special import (
    TextTool, NumberingTool, EraserTool, MasqueradeTool, FillTool, StampTool,
)
from paparaz.core.export import save_png, save_jpg, save_svg, copy_to_clipboard
from paparaz.core.elements import (
    NumberElement, AnnotationElement, TextElement,
    RectElement, EllipseElement, MaskElement, NumberElement as NumElem, StampElement,
)


class _PanelGripTab(QWidget):
    """Small vertical tab on canvas left edge to reveal hidden side panel."""

    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(14, 56)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Show properties panel")
        self.hide()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor(116, 0, 150, 210))
        p.setPen(Qt.PenStyle.NoPen)
        # Only round right corners
        p.drawRoundedRect(self.rect(), 5, 5)
        p.setBrush(QColor(255, 255, 255, 200))
        # Draw "›" chevron
        mid_y = self.height() // 2
        pts_x = self.width() // 2
        for dy in (-5, 0, 5):
            p.drawEllipse(pts_x - 1, mid_y + dy - 1, 3, 3)
        p.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()


class EditorWindow(QWidget):
    """Frameless aero-style editor - just canvas + floating toolbar + side panel."""

    closed = Signal()
    pin_requested = Signal(QPixmap, QPixmap, list)

    def __init__(self, screenshot: QPixmap, settings_manager=None, parent=None):
        super().__init__(parent)
        self._settings_manager = settings_manager
        self._screenshot = screenshot
        self._drag_pos = QPoint()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Main layout: toolbar on top, then canvas+panel side by side
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        # Toolbar row — full width so flow layout can use all available space
        self._toolbar = FlameshotToolbar()
        layout.addWidget(self._toolbar)

        # Body: optional side panel + canvas
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(2)

        self._side_panel = SidePanel()
        self._side_panel.hide()  # Hidden by default (auto mode, no selection)
        body.addWidget(self._side_panel)

        self._canvas = AnnotationCanvas(screenshot)
        body.addWidget(self._canvas, 1)

        layout.addLayout(body, 1)

        # Grip tab — shown when side panel is in 'hidden' mode
        self._grip_tab = _PanelGripTab(self)
        self._grip_tab.clicked.connect(self._on_grip_tab_clicked)

        # Status label at bottom (minimal)
        self._status = QLabel("V:Select  P:Pen  B:Brush  L:Line  A:Arrow  R:Rect  E:Ellipse  T:Text  N:Num  S:Stamp  X:Erase  M:Blur")
        self._status.setStyleSheet("color: rgba(255,255,255,100); font-size: 9px; padding: 2px;")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status)

        # --- Tools ---
        self._text_tool = TextTool(self._canvas)
        self._masquerade_tool = MasqueradeTool(self._canvas)
        self._numbering_tool = NumberingTool(self._canvas)
        self._stamp_tool = StampTool(self._canvas)
        self._tools = {
            ToolType.SELECT: SelectTool(self._canvas),
            ToolType.PEN: PenTool(self._canvas),
            ToolType.BRUSH: BrushTool(self._canvas),
            ToolType.LINE: LineTool(self._canvas),
            ToolType.ARROW: ArrowTool(self._canvas),
            ToolType.RECTANGLE: RectangleTool(self._canvas),
            ToolType.ELLIPSE: EllipseTool(self._canvas),
            ToolType.TEXT: self._text_tool,
            ToolType.NUMBERING: self._numbering_tool,
            ToolType.ERASER: EraserTool(self._canvas),
            ToolType.MASQUERADE: self._masquerade_tool,
            ToolType.FILL: FillTool(self._canvas),
            ToolType.STAMP: self._stamp_tool,
        }

        # --- Toolbar signals ---
        self._toolbar.tool_selected.connect(self._on_tool_selected)
        self._toolbar.undo_requested.connect(self._canvas.history.undo)
        self._toolbar.redo_requested.connect(self._canvas.history.redo)
        self._toolbar.save_requested.connect(self._save_as)
        self._toolbar.copy_requested.connect(self._copy_to_clipboard)
        self._toolbar.paste_requested.connect(self._paste)
        self._toolbar.pin_requested.connect(self._pin_current)
        self._toolbar.bring_front_requested.connect(self._canvas.bring_to_front)
        self._toolbar.send_back_requested.connect(self._canvas.send_to_back)
        self._toolbar.close_requested.connect(self.close)

        # --- Side panel signals ---
        self._side_panel.fg_color_changed.connect(self._canvas.set_foreground_color)
        self._side_panel.bg_color_changed.connect(self._canvas.set_background_color)
        self._side_panel.line_width_changed.connect(self._canvas.set_line_width)
        self._side_panel.font_family_changed.connect(self._canvas.set_font_family)
        self._side_panel.font_size_changed.connect(self._canvas.set_font_size)
        self._side_panel.shadow_toggled.connect(self._canvas.set_shadow_enabled)
        self._side_panel.shadow_color_changed.connect(self._canvas.set_shadow_color)
        self._side_panel.shadow_offset_x_changed.connect(self._canvas.set_shadow_offset_x)
        self._side_panel.shadow_offset_y_changed.connect(self._canvas.set_shadow_offset_y)
        self._side_panel.shadow_blur_changed.connect(self._canvas.set_shadow_blur)
        self._side_panel.opacity_changed.connect(self._canvas.set_opacity)
        self._side_panel.cap_style_changed.connect(self._canvas.set_cap_style)
        self._side_panel.join_style_changed.connect(self._canvas.set_join_style)
        self._side_panel.dash_pattern_changed.connect(self._canvas.set_dash_pattern)
        self._side_panel.filled_toggled.connect(self._on_filled_toggled)
        self._side_panel.pixel_size_changed.connect(self._on_pixel_size_changed)
        self._side_panel.number_size_changed.connect(self._on_number_size_changed)
        self._side_panel.number_text_color_changed.connect(self._on_number_text_color_changed)
        self._side_panel.stamp_selected.connect(self._on_stamp_selected)
        self._side_panel.stamp_size_changed.connect(self._on_stamp_size_changed)

        # Text signals -> update tool + selected element
        self._side_panel.text_bold_changed.connect(self._on_text_bold)
        self._side_panel.text_italic_changed.connect(self._on_text_italic)
        self._side_panel.text_underline_changed.connect(self._on_text_underline)
        self._side_panel.text_strikethrough_changed.connect(self._on_strikethrough)
        self._side_panel.text_alignment_changed.connect(self._on_text_alignment)
        self._side_panel.text_direction_changed.connect(self._on_text_direction)
        self._side_panel.text_bg_enabled_changed.connect(self._on_text_bg_enabled)
        self._side_panel.text_bg_color_changed.connect(self._on_text_bg_color)

        # Side panel mode changes
        self._side_panel.mode_changed.connect(self._on_panel_mode_changed)

        # Canvas signals
        self._canvas.element_selected.connect(self._on_element_selected)
        self._canvas.request_text_edit.connect(self._on_text_edit_request)

        self._setup_shortcuts()
        self._on_tool_selected(ToolType.SELECT)
        NumberElement.reset_counter()

    def paintEvent(self, event):
        """Draw semi-transparent dark background behind canvas."""
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor(10, 10, 20, 220))
        p.setPen(QColor(116, 0, 150, 150))
        p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 8, 8)
        p.end()

    # --- Window drag (since frameless) ---

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Only drag from toolbar area (top 40px)
            if event.position().y() < 40:
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and self._drag_pos and event.position().y() < 60:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    # --- Tool selection ---

    def _on_tool_selected(self, tool_type: ToolType):
        tool = self._tools.get(tool_type)
        if tool:
            self._canvas.set_tool(tool)
            self._toolbar.set_active_tool(tool_type)
            if not self._canvas.selected_element:
                self._side_panel.update_for_tool(tool_type)

    # --- Element selection -> side panel ---

    def _on_element_selected(self, element):
        # Delegate show/hide logic to panel based on its mode
        self._side_panel.on_element_selected(element)

    def _on_panel_mode_changed(self, mode: str):
        self._grip_tab.setVisible(mode == "hidden")
        if mode == "hidden":
            self._update_grip_tab_pos()

    def _on_grip_tab_clicked(self):
        """Grip tab clicked — switch panel back to auto mode and show it."""
        self._side_panel.set_mode("auto")
        elem = self._canvas.selected_element
        if elem:
            self._side_panel.on_element_selected(elem)
        else:
            self._side_panel.show()

    def _update_grip_tab_pos(self):
        """Position grip tab at the left edge of the canvas area."""
        canvas_geo = self._canvas.geometry()
        # Map canvas geometry to editor coordinates
        # canvas parent is the body layout widget which is the editor itself
        tab_h = self._grip_tab.height()
        x = canvas_geo.x()
        y = canvas_geo.y() + (canvas_geo.height() - tab_h) // 2
        self._grip_tab.move(x, y)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._grip_tab.isVisible():
            self._update_grip_tab_pos()

    def _on_text_edit_request(self, element):
        if isinstance(element, TextElement):
            self._on_tool_selected(ToolType.TEXT)
            self._text_tool.start_editing(element)
            self._canvas.select_element(None)

    # --- Property handlers ---

    def _on_filled_toggled(self, filled):
        elem = self._canvas.selected_element
        if isinstance(elem, (RectElement, EllipseElement)):
            elem.filled = filled
            self._canvas.update()

    def _on_pixel_size_changed(self, size):
        self._masquerade_tool.pixel_size = size
        elem = self._canvas.selected_element
        if isinstance(elem, MaskElement):
            elem.pixel_size = size
            self._canvas.update()

    def _on_number_size_changed(self, size):
        self._numbering_tool.marker_size = size
        elem = self._canvas.selected_element
        if isinstance(elem, NumElem):
            elem.size = size
            self._canvas.update()

    def _on_number_text_color_changed(self, color):
        self._numbering_tool.text_color = color
        elem = self._canvas.selected_element
        if isinstance(elem, NumElem):
            elem.text_color = color
            self._canvas.update()

    def _on_stamp_selected(self, stamp_id):
        self._stamp_tool.stamp_id = stamp_id
        e = self._canvas.selected_element
        if isinstance(e, StampElement):
            e.stamp_id = stamp_id
            self._canvas.update()

    def _on_stamp_size_changed(self, size):
        self._stamp_tool.stamp_size = size
        e = self._canvas.selected_element
        if isinstance(e, StampElement):
            cx, cy = e.rect.center().x(), e.rect.center().y()
            e.size = size
            e.rect = QRectF(cx - size / 2, cy - size / 2, size, size)
            self._canvas.update()

    def _on_text_bold(self, v):
        self._text_tool.set_bold(v)
        e = self._canvas.selected_element
        if isinstance(e, TextElement): e.bold = v; self._canvas.update()

    def _on_text_italic(self, v):
        self._text_tool.set_italic(v)
        e = self._canvas.selected_element
        if isinstance(e, TextElement): e.italic = v; self._canvas.update()

    def _on_text_underline(self, v):
        self._text_tool.set_underline(v)
        e = self._canvas.selected_element
        if isinstance(e, TextElement): e.underline = v; self._canvas.update()

    def _on_strikethrough(self, v):
        self._text_tool.strikethrough = v
        if self._text_tool._active_text:
            self._text_tool._active_text.strikethrough = v
            self._canvas.set_preview(self._text_tool._active_text)
        e = self._canvas.selected_element
        if isinstance(e, TextElement): e.strikethrough = v; self._canvas.update()

    def _on_text_alignment(self, align):
        self._text_tool.set_alignment(align)
        e = self._canvas.selected_element
        if isinstance(e, TextElement):
            m = {"left": Qt.AlignmentFlag.AlignLeft, "center": Qt.AlignmentFlag.AlignCenter, "right": Qt.AlignmentFlag.AlignRight}
            e.alignment = m.get(align, Qt.AlignmentFlag.AlignLeft)
            self._canvas.update()

    def _on_text_direction(self, d):
        self._text_tool.set_direction(d)
        e = self._canvas.selected_element
        if isinstance(e, TextElement):
            e.direction = Qt.LayoutDirection.RightToLeft if d == "rtl" else Qt.LayoutDirection.LeftToRight
            self._canvas.update()

    def _on_text_bg_enabled(self, v):
        self._text_tool.set_bg_enabled(v)
        e = self._canvas.selected_element
        if isinstance(e, TextElement): e.bg_enabled = v; self._canvas.update()

    def _on_text_bg_color(self, c):
        self._text_tool.set_bg_color(c)
        e = self._canvas.selected_element
        if isinstance(e, TextElement): e.bg_color = c; self._canvas.update()

    # --- Shortcuts ---

    def _setup_shortcuts(self):
        keys = {
            "Ctrl+Z": self._canvas.history.undo,
            "Ctrl+Y": self._canvas.history.redo,
            "Ctrl+Shift+Z": self._canvas.history.redo,
            "Ctrl+S": self._save_as,
            "Ctrl+C": self._copy_to_clipboard,
            "Ctrl+V": self._paste,
            "Ctrl+]": self._canvas.bring_to_front,
            "Ctrl+[": self._canvas.send_to_back,
            "Ctrl+P": self._pin_current,
            "V": lambda: self._on_tool_selected(ToolType.SELECT),
            "P": lambda: self._on_tool_selected(ToolType.PEN),
            "B": lambda: self._on_tool_selected(ToolType.BRUSH),
            "L": lambda: self._on_tool_selected(ToolType.LINE),
            "A": lambda: self._on_tool_selected(ToolType.ARROW),
            "R": lambda: self._on_tool_selected(ToolType.RECTANGLE),
            "E": lambda: self._on_tool_selected(ToolType.ELLIPSE),
            "T": lambda: self._on_tool_selected(ToolType.TEXT),
            "N": lambda: self._on_tool_selected(ToolType.NUMBERING),
            "X": lambda: self._on_tool_selected(ToolType.ERASER),
            "M": lambda: self._on_tool_selected(ToolType.MASQUERADE),
            "S": lambda: self._on_tool_selected(ToolType.STAMP),
            "Ctrl+=": lambda: self._canvas.set_zoom(self._canvas.zoom * 1.25),
            "Ctrl+-": lambda: self._canvas.set_zoom(self._canvas.zoom * 0.8),
            "Ctrl+0": lambda: self._canvas.set_zoom(1.0),
        }
        for key, cb in keys.items():
            s = QShortcut(QKeySequence(key), self)
            s.activated.connect(cb)
        esc = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        esc.activated.connect(self.close)

    # --- Save / Copy / Paste / Pin ---

    def _save_as(self):
        save_dir = ""
        if self._settings_manager:
            save_dir = self._settings_manager.settings.save_directory
        default_path = Path(save_dir) if save_dir else Path.home()
        path, _ = QFileDialog.getSaveFileName(
            self, "Save", str(default_path / "capture.png"),
            "PNG (*.png);;JPEG (*.jpg);;SVG (*.svg);;All (*)",
        )
        if not path:
            return
        pix = self._canvas.render_to_pixmap()
        if path.lower().endswith(".svg"):
            save_svg(self._canvas._background, path, self._canvas.paint_annotations)
        elif path.lower().endswith((".jpg", ".jpeg")):
            q = self._settings_manager.settings.jpg_quality if self._settings_manager else 90
            save_jpg(pix, path, q)
        else:
            save_png(pix, path)
        if self._settings_manager:
            self._settings_manager.add_recent(path)

    def _copy_to_clipboard(self):
        copy_to_clipboard(self._canvas.render_to_pixmap())

    def _paste(self):
        if self._canvas.paste_from_clipboard():
            self._on_tool_selected(ToolType.SELECT)

    def _pin_current(self):
        import copy
        rendered = self._canvas.render_to_pixmap()
        background = self._canvas._background.copy()
        elements = copy.copy(self._canvas.elements)
        self.pin_requested.emit(rendered, background, elements)

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)
