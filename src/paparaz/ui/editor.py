"""Main editor window - canvas, toolbar, side panel, z-order, pin, save-to-recent."""

from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QScrollArea, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFileDialog, QStatusBar, QApplication,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QKeySequence, QShortcut

from paparaz.ui.canvas import AnnotationCanvas
from paparaz.ui.toolbar import FlameshotToolbar
from paparaz.ui.side_panel import SidePanel
from paparaz.tools.base import ToolType
from paparaz.tools.select import SelectTool
from paparaz.tools.drawing import (
    PenTool, BrushTool, LineTool, ArrowTool, RectangleTool, EllipseTool,
)
from paparaz.tools.special import (
    TextTool, NumberingTool, EraserTool, MasqueradeTool, FillTool,
)
from paparaz.core.export import save_png, save_jpg, save_svg, copy_to_clipboard
from paparaz.core.elements import (
    NumberElement, AnnotationElement, TextElement,
    RectElement, EllipseElement, MaskElement, NumberElement as NumElem,
)

EDITOR_STYLE = """
QMainWindow { background: #0d0d1a; }
QScrollArea { background: #1a1a2e; border: none; }
QStatusBar {
    background: #1a1a2e; color: #888; font-size: 11px;
    border-top: 1px solid #333; padding: 2px 8px;
}
"""


class EditorWindow(QMainWindow):
    """Main annotation editor window with Flameshot-style UI."""

    closed = Signal()
    pin_requested = Signal(QPixmap, QPixmap, list)  # rendered, background, elements

    def __init__(self, screenshot: QPixmap, settings_manager=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PapaRaZ")
        self.setMinimumSize(480, 320)
        self.setStyleSheet(EDITOR_STYLE)
        self._settings_manager = settings_manager
        self._screenshot = screenshot

        central = QWidget()
        outer_layout = QVBoxLayout(central)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # Toolbar at top, centered
        self._toolbar = FlameshotToolbar()
        tc = QWidget()
        tc.setStyleSheet("background: #0d0d1a;")
        tc_layout = QHBoxLayout(tc)
        tc_layout.setContentsMargins(12, 8, 12, 8)
        tc_layout.addStretch()
        tc_layout.addWidget(self._toolbar)
        tc_layout.addStretch()
        outer_layout.addWidget(tc)

        # Body: side panel + scroll area
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self._side_panel = SidePanel()
        body.addWidget(self._side_panel)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(False)
        self._scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._canvas = AnnotationCanvas(screenshot)
        self._scroll.setWidget(self._canvas)
        body.addWidget(self._scroll, 1)

        outer_layout.addLayout(body, 1)

        # Status bar
        self._status = QStatusBar()
        self._tool_label = QLabel("Select")
        self._zoom_label = QLabel("100%")
        self._pos_label = QLabel("0, 0")
        self._hint_label = QLabel("Ctrl+Enter: finalize text | Middle-click: pan | Ctrl+]: bring front | Ctrl+[: send back")
        self._hint_label.setStyleSheet("color: #555;")
        self._status.addWidget(self._tool_label)
        self._status.addWidget(self._hint_label)
        self._status.addPermanentWidget(self._pos_label)
        self._status.addPermanentWidget(self._zoom_label)
        outer_layout.addWidget(self._status)

        self.setCentralWidget(central)

        # --- Tools ---
        self._text_tool = TextTool(self._canvas)
        self._masquerade_tool = MasqueradeTool(self._canvas)
        self._numbering_tool = NumberingTool(self._canvas)
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

        # Text tool signals - update tool state AND selected element
        self._side_panel.text_bold_changed.connect(self._on_text_bold)
        self._side_panel.text_italic_changed.connect(self._on_text_italic)
        self._side_panel.text_underline_changed.connect(self._on_text_underline)
        self._side_panel.text_strikethrough_changed.connect(self._on_strikethrough)
        self._side_panel.text_alignment_changed.connect(self._on_text_alignment)
        self._side_panel.text_direction_changed.connect(self._on_text_direction)
        self._side_panel.text_bg_enabled_changed.connect(self._on_text_bg_enabled)
        self._side_panel.text_bg_color_changed.connect(self._on_text_bg_color)

        # Canvas signals
        self._canvas.element_selected.connect(self._on_element_selected)
        self._canvas.request_text_edit.connect(self._on_text_edit_request)
        self._canvas.tool_changed.connect(
            lambda tt: self._tool_label.setText(tt.name.capitalize())
        )
        self._canvas.zoom_changed.connect(self._on_zoom_changed)
        self._canvas.setMouseTracking(True)

        self._setup_shortcuts()
        self._on_tool_selected(ToolType.SELECT)
        NumberElement.reset_counter()

    # --- Tool selection ---

    def _on_tool_selected(self, tool_type: ToolType):
        tool = self._tools.get(tool_type)
        if tool:
            self._canvas.set_tool(tool)
            self._toolbar.set_active_tool(tool_type)
            if not self._canvas.selected_element:
                self._side_panel.update_for_tool(tool_type)
            self._tool_label.setText(tool_type.name.capitalize())

    # --- Element selection ---

    def _on_element_selected(self, element):
        if element is not None:
            self._side_panel.load_element_properties(element)
        else:
            self._side_panel.clear_element_properties()

    def _on_text_edit_request(self, element):
        if isinstance(element, TextElement):
            self._on_tool_selected(ToolType.TEXT)
            self._text_tool.start_editing(element)
            self._canvas.select_element(None)
            self._status.showMessage("Editing text - Ctrl+Enter to finish", 3000)

    # --- Property handlers ---

    def _on_filled_toggled(self, filled: bool):
        elem = self._canvas.selected_element
        if isinstance(elem, (RectElement, EllipseElement)):
            elem.filled = filled
            self._canvas.update()

    def _on_pixel_size_changed(self, size: int):
        self._masquerade_tool.pixel_size = size
        elem = self._canvas.selected_element
        if isinstance(elem, MaskElement):
            elem.pixel_size = size
            self._canvas.update()

    def _on_number_size_changed(self, size: float):
        self._numbering_tool.marker_size = size
        elem = self._canvas.selected_element
        if isinstance(elem, NumElem):
            elem.size = size
            self._canvas.update()

    def _on_number_text_color_changed(self, color: str):
        self._numbering_tool.text_color = color
        elem = self._canvas.selected_element
        if isinstance(elem, NumElem):
            elem.text_color = color
            self._canvas.update()

    # --- Text property handlers: update tool + selected element ---

    def _on_text_bold(self, enabled: bool):
        self._text_tool.set_bold(enabled)
        elem = self._canvas.selected_element
        if isinstance(elem, TextElement):
            elem.bold = enabled
            self._canvas.update()

    def _on_text_italic(self, enabled: bool):
        self._text_tool.set_italic(enabled)
        elem = self._canvas.selected_element
        if isinstance(elem, TextElement):
            elem.italic = enabled
            self._canvas.update()

    def _on_text_underline(self, enabled: bool):
        self._text_tool.set_underline(enabled)
        elem = self._canvas.selected_element
        if isinstance(elem, TextElement):
            elem.underline = enabled
            self._canvas.update()

    def _on_strikethrough(self, enabled: bool):
        self._text_tool.strikethrough = enabled
        if self._text_tool._active_text:
            self._text_tool._active_text.strikethrough = enabled
            self._canvas.set_preview(self._text_tool._active_text)
        elem = self._canvas.selected_element
        if isinstance(elem, TextElement):
            elem.strikethrough = enabled
            self._canvas.update()

    def _on_text_alignment(self, align: str):
        self._text_tool.set_alignment(align)
        elem = self._canvas.selected_element
        if isinstance(elem, TextElement):
            from PySide6.QtCore import Qt
            mapping = {
                "left": Qt.AlignmentFlag.AlignLeft,
                "center": Qt.AlignmentFlag.AlignCenter,
                "right": Qt.AlignmentFlag.AlignRight,
            }
            elem.alignment = mapping.get(align, Qt.AlignmentFlag.AlignLeft)
            self._canvas.update()

    def _on_text_direction(self, direction: str):
        self._text_tool.set_direction(direction)
        elem = self._canvas.selected_element
        if isinstance(elem, TextElement):
            from PySide6.QtCore import Qt
            elem.direction = (
                Qt.LayoutDirection.RightToLeft if direction == "rtl"
                else Qt.LayoutDirection.LeftToRight
            )
            self._canvas.update()

    def _on_text_bg_enabled(self, enabled: bool):
        self._text_tool.set_bg_enabled(enabled)
        elem = self._canvas.selected_element
        if isinstance(elem, TextElement):
            elem.bg_enabled = enabled
            self._canvas.update()

    def _on_text_bg_color(self, color: str):
        self._text_tool.set_bg_color(color)
        elem = self._canvas.selected_element
        if isinstance(elem, TextElement):
            elem.bg_color = color
            self._canvas.update()

    def _on_zoom_changed(self, zoom: float):
        self._zoom_label.setText(f"{int(zoom * 100)}%")

    # --- Shortcuts ---

    def _setup_shortcuts(self):
        shortcuts = {
            "Ctrl+Z": self._canvas.history.undo,
            "Ctrl+Y": self._canvas.history.redo,
            "Ctrl+Shift+Z": self._canvas.history.redo,
            "Ctrl+S": self._save_as,
            "Ctrl+Shift+S": self._save_as,
            "Ctrl+C": self._copy_to_clipboard,
            "Ctrl+V": self._paste,
            # Z-order
            "Ctrl+]": self._canvas.bring_to_front,
            "Ctrl+[": self._canvas.send_to_back,
            "Ctrl+Shift+]": self._canvas.move_up,
            "Ctrl+Shift+[": self._canvas.move_down,
            # Pin
            "Ctrl+P": self._pin_current,
            # Tools
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
            # Zoom
            "Ctrl+=": lambda: self._canvas.set_zoom(self._canvas.zoom * 1.25),
            "Ctrl+-": lambda: self._canvas.set_zoom(self._canvas.zoom * 0.8),
            "Ctrl+0": lambda: self._canvas.set_zoom(1.0),
        }
        for key, callback in shortcuts.items():
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(callback)

        esc = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        esc.activated.connect(lambda: self._on_tool_selected(ToolType.SELECT))

    # --- Save / Copy / Paste / Pin ---

    def _save_as(self):
        save_dir = ""
        if self._settings_manager:
            save_dir = self._settings_manager.settings.save_directory
        default_path = Path(save_dir) if save_dir else Path.home()

        path, _ = QFileDialog.getSaveFileName(
            self, "Save Capture",
            str(default_path / "capture.png"),
            "PNG (*.png);;JPEG (*.jpg *.jpeg);;SVG (*.svg);;All Files (*)",
        )
        if not path:
            return
        pixmap = self._canvas.render_to_pixmap()
        if path.lower().endswith(".svg"):
            save_svg(self._canvas._background, path, self._canvas.paint_annotations)
        elif path.lower().endswith((".jpg", ".jpeg")):
            quality = 90
            if self._settings_manager:
                quality = self._settings_manager.settings.jpg_quality
            save_jpg(pixmap, path, quality)
        else:
            save_png(pixmap, path)

        # Add to recent captures
        if self._settings_manager:
            self._settings_manager.add_recent(path)

        self._status.showMessage(f"Saved to {path}", 3000)

    def _copy_to_clipboard(self):
        pixmap = self._canvas.render_to_pixmap()
        copy_to_clipboard(pixmap)
        self._status.showMessage("Copied to clipboard", 2000)

    def _paste(self):
        if self._canvas.paste_from_clipboard():
            self._on_tool_selected(ToolType.SELECT)
            self._status.showMessage("Pasted image from clipboard", 2000)

    def _pin_current(self):
        import copy
        rendered = self._canvas.render_to_pixmap()
        background = self._canvas._background.copy()
        elements = copy.copy(self._canvas.elements)
        self.pin_requested.emit(rendered, background, elements)
        self._status.showMessage("Pinned to screen", 2000)

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)
