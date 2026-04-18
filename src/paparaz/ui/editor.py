"""Frameless aero-style editor - canvas with floating toolbar, no window chrome."""

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QToolButton,
    QLabel, QFileDialog, QApplication, QMessageBox,
)
from PySide6.QtCore import Qt, Signal, QPoint, QRectF, QPointF, QEvent, QSize, QTimer
from PySide6.QtGui import QPixmap, QKeySequence, QShortcut, QPainter, QPen, QColor, QCursor

from paparaz.ui.icons import get_icon

from paparaz.ui.canvas import AnnotationCanvas
from paparaz.ui.toolbar import MultiEdgeToolbar
from paparaz.ui.side_panel import SidePanel
from paparaz.ui.layers_panel import LayersPanel
from paparaz.ui.status_bar import StatusBar, InfoWindow
from paparaz.tools.base import ToolType
from paparaz.tools.select import SelectTool
from paparaz.tools.drawing import (
    PenTool, BrushTool, HighlightTool, LineTool, ArrowTool, CurvedArrowTool,
    RectangleTool, EllipseTool, MeasureTool,
)
from paparaz.tools.special import (
    TextTool, NumberingTool, EraserTool, MasqueradeTool, FillTool, StampTool, CropTool, SliceTool,
    EyedropperTool, MagnifierTool,
)
from paparaz.core.export import save_png, save_jpg, save_svg, copy_to_clipboard
from paparaz.core.elements import (
    NumberElement, AnnotationElement, TextElement,
    RectElement, EllipseElement, MaskElement, NumberElement as NumElem, StampElement,
    set_selection_accent,
)
from paparaz.ui.canvas_resize_dialog import CanvasResizeDialog


class EditorWindow(QWidget):
    """Frameless aero-style editor - just canvas + floating toolbar + side panel."""

    closed = Signal()
    pin_requested = Signal(QPixmap, QPixmap, list)
    file_saved = Signal(str)

    def __init__(self, screenshot: QPixmap, settings_manager=None, parent=None,
                 capture_window_title: str = "", capture_app_name: str = ""):
        super().__init__(parent)
        self.setObjectName("editorRoot")
        self._settings_manager = settings_manager
        self._screenshot = screenshot
        self._drag_pos = None
        # Context for filename pattern tokens {title} and {app}
        self._capture_window_title = capture_window_title
        self._capture_app_name = capture_app_name

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Window    # Window (not Tool) so it survives focus loss
        )
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(120, 80)

        # Opaque window — avoids DWM compositor flicker during resize.
        # Rounded corners are painted but the window itself is fully opaque.
        self.setAutoFillBackground(True)
        pal = self.palette()
        pal.setColor(pal.ColorRole.Window, QColor(10, 10, 20))
        self.setPalette(pal)

        # Main layout: top toolbar, then body (side panel + canvas + right toolbar), then bottom toolbar, then status
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        # Multi-edge toolbar
        self._multi_toolbar = MultiEdgeToolbar(self)
        layout.addWidget(self._multi_toolbar.top_strip)

        # Body: canvas + right strip (side panel is a floating overlay, not in layout)
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(2)

        self._canvas = AnnotationCanvas(screenshot)
        body.addWidget(self._canvas, 1)

        body.addWidget(self._multi_toolbar.right_strip)

        layout.addLayout(body, 1)

        layout.addWidget(self._multi_toolbar.bottom_strip)

        # Floating side panel — fully independent top-level window (parent=None).
        # This prevents the editor's border-resize event filter from being installed
        # on the panel's children, which would intercept header drag as a resize.
        self._side_panel = SidePanel(parent=None)
        self._side_panel.hide()
        self._panel_initially_placed = False  # set True after first show + layout pass

        # Apply default panel mode from settings
        if self._settings_manager:
            panel_mode = getattr(self._settings_manager.settings, 'default_panel_mode', 'auto')
            self._side_panel.set_mode(panel_mode)

        # Layers panel (floating, hidden by default)
        self._layers_panel = LayersPanel(parent=None)
        self._layers_panel.hide()
        self._layers_panel.set_canvas(self._canvas)
        self._layers_panel.element_selected.connect(self._on_layer_element_selected)

        # Track current tool type for per-tool property persistence
        self._current_tool_type = ToolType.SELECT

        # Unsaved-changes tracking: True when canvas has been saved and not modified since
        self._was_saved = False
        self._canvas.elements_changed.connect(self._on_canvas_modified)

        # Debounced save timer: writes settings ~2s after the last property change
        self._settings_save_timer = QTimer(self)
        self._settings_save_timer.setSingleShot(True)
        self._settings_save_timer.setInterval(2000)
        self._settings_save_timer.timeout.connect(self._flush_tool_properties)

        # Auto-save recovery timer
        self._recovery_timer = QTimer(self)
        self._recovery_timer.timeout.connect(self._auto_save_recovery)
        interval = 0
        if self._settings_manager:
            interval = getattr(self._settings_manager.settings, 'auto_save_interval', 60)
        if interval > 0:
            self._recovery_timer.start(interval * 1000)

        # Always-visible pinned close button at top-right corner
        self._close_btn_overlay = QToolButton(self)
        self._close_btn_overlay.setIcon(get_icon("close", 14))
        self._close_btn_overlay.setIconSize(QSize(14, 14))
        self._close_btn_overlay.setFixedSize(26, 26)
        self._close_btn_overlay.setToolTip("Close (Esc)")
        self._close_btn_overlay.setStyleSheet(
            "QToolButton{background:transparent;border:none;border-radius:13px;padding:0;}"
            "QToolButton:hover{background:#cc2222;}"
            "QToolButton:pressed{background:#991111;}"
        )
        self._close_btn_overlay.clicked.connect(self._confirm_close)

        # Enhanced status bar
        self._status_bar = StatusBar(self)
        layout.addWidget(self._status_bar)

        # Shortcut hints (below status bar, tiny)
        self._shortcut_hint = QLabel("V:Select  P:Pen  B:Brush  H:Highlight  L:Line  A:Arrow  Q:CurvedArrow  R:Rect  E:Ellipse  T:Text  N:Num  S:Stamp  X:Erase  M:Blur  C:Crop  D:Measure")
        self._shortcut_hint.setStyleSheet("color: rgba(255,255,255,160); font-size: 11px; padding: 2px;")
        self._shortcut_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._shortcut_hint)

        # Detachable info window
        self._info_window: InfoWindow | None = None

        # --- Tools ---
        self._text_tool = TextTool(self._canvas)
        self._masquerade_tool = MasqueradeTool(self._canvas)
        self._numbering_tool = NumberingTool(self._canvas)
        self._stamp_tool = StampTool(self._canvas)
        self._crop_tool = CropTool(self._canvas)
        self._slice_tool = SliceTool(self._canvas)
        self._tools = {
            ToolType.SELECT:    SelectTool(self._canvas),
            ToolType.PEN:       PenTool(self._canvas),
            ToolType.BRUSH:     BrushTool(self._canvas),
            ToolType.HIGHLIGHT: HighlightTool(self._canvas),
            ToolType.LINE:         LineTool(self._canvas),
            ToolType.ARROW:        ArrowTool(self._canvas),
            ToolType.CURVED_ARROW: CurvedArrowTool(self._canvas),
            ToolType.RECTANGLE:    RectangleTool(self._canvas),
            ToolType.ELLIPSE:   EllipseTool(self._canvas),
            ToolType.TEXT:      self._text_tool,
            ToolType.NUMBERING: self._numbering_tool,
            ToolType.ERASER:    EraserTool(self._canvas),
            ToolType.MASQUERADE:self._masquerade_tool,
            ToolType.FILL:      FillTool(self._canvas),
            ToolType.STAMP:     self._stamp_tool,
            ToolType.CROP:       self._crop_tool,
            ToolType.SLICE:      self._slice_tool,
            ToolType.EYEDROPPER: EyedropperTool(self._canvas),
            ToolType.MAGNIFIER: MagnifierTool(self._canvas),
            ToolType.MEASURE:  MeasureTool(self._canvas),
        }

        # Wire specialized tool defaults from settings
        if self._settings_manager:
            _s = self._settings_manager.settings
            self._masquerade_tool.pixel_size = getattr(_s, 'default_blur_pixels', 10)
            self._stamp_tool.stamp_id = getattr(_s, 'default_stamp_id', 'check')

        # --- Toolbar signals ---
        self._multi_toolbar.tool_selected.connect(self._on_tool_selected)
        self._multi_toolbar.undo_requested.connect(self._canvas.history.undo)
        self._multi_toolbar.redo_requested.connect(self._canvas.history.redo)
        self._multi_toolbar.save_requested.connect(self._save_as)
        self._multi_toolbar.copy_requested.connect(self._copy_to_clipboard)
        self._multi_toolbar.paste_requested.connect(self._paste)
        self._multi_toolbar.pin_requested.connect(self._pin_current)
        self._multi_toolbar.bring_front_requested.connect(self._canvas.bring_to_front)
        self._multi_toolbar.send_back_requested.connect(self._canvas.send_to_back)
        self._multi_toolbar.close_requested.connect(self.close)
        self._multi_toolbar.tool_props_requested.connect(self._show_tool_props)
        self._multi_toolbar.resize_canvas_requested.connect(self._show_canvas_resize)
        self._multi_toolbar.crop_requested.connect(lambda: self._on_tool_selected(ToolType.CROP))
        self._multi_toolbar.theme_preset_requested.connect(self._show_theme_presets)
        self._multi_toolbar.settings_requested.connect(self._show_settings)
        self._multi_toolbar.layers_requested.connect(self._toggle_layers_panel)
        self._canvas.elements_changed.connect(self._on_elements_changed)

        # --- Side panel signals ---
        self._side_panel.fg_color_changed.connect(self._on_fg_color_changed)
        self._side_panel.bg_color_changed.connect(self._on_bg_color_changed)
        self._side_panel.line_width_changed.connect(self._canvas.set_line_width)
        self._side_panel.font_family_changed.connect(self._on_font_family_changed)
        self._side_panel.font_size_changed.connect(self._on_font_size_changed)
        self._side_panel.shadow_toggled.connect(self._canvas.set_shadow_enabled)
        self._side_panel.shadow_color_changed.connect(self._canvas.set_shadow_color)
        self._side_panel.shadow_offset_x_changed.connect(self._canvas.set_shadow_offset_x)
        self._side_panel.shadow_offset_y_changed.connect(self._canvas.set_shadow_offset_y)
        self._side_panel.shadow_blur_x_changed.connect(self._canvas.set_shadow_blur_x)
        self._side_panel.shadow_blur_y_changed.connect(self._canvas.set_shadow_blur_y)
        self._side_panel.opacity_changed.connect(self._canvas.set_opacity)
        self._side_panel.cap_style_changed.connect(self._canvas.set_cap_style)
        self._side_panel.join_style_changed.connect(self._canvas.set_join_style)
        self._side_panel.dash_pattern_changed.connect(self._canvas.set_dash_pattern)
        self._side_panel.filled_toggled.connect(self._on_filled_toggled)
        self._side_panel.fill_tolerance_changed.connect(self._on_fill_tolerance_changed)
        self._side_panel.pixel_size_changed.connect(self._on_pixel_size_changed)
        self._side_panel.number_size_changed.connect(self._on_number_size_changed)
        self._side_panel.number_text_color_changed.connect(self._on_number_text_color_changed)
        self._side_panel.number_style_changed.connect(self._on_number_style_changed)
        self._side_panel.number_reset_requested.connect(self._on_number_reset)
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
        self._side_panel.text_stroke_enabled_changed.connect(self._on_text_stroke_enabled)
        self._side_panel.text_stroke_color_changed.connect(self._on_text_stroke_color)
        self._side_panel.text_stroke_width_changed.connect(self._on_text_stroke_width)

        # Rotation slider -> update selected element
        self._side_panel.rotation_changed.connect(self._canvas.set_rotation)

        # Side panel mode changes
        self._side_panel.mode_changed.connect(self._on_panel_mode_changed)

        # Recent colors: load from settings + persist on change
        if self._settings_manager:
            self._side_panel.set_recent_colors(self._settings_manager.settings.recent_colors)
        self._side_panel.recent_colors_changed.connect(self._on_recent_colors_changed)

        # Auto-save tool properties whenever any value changes
        for sig in (
            self._side_panel.fg_color_changed, self._side_panel.bg_color_changed,
            self._side_panel.line_width_changed, self._side_panel.font_family_changed,
            self._side_panel.font_size_changed, self._side_panel.opacity_changed,
            self._side_panel.cap_style_changed, self._side_panel.join_style_changed,
            self._side_panel.dash_pattern_changed, self._side_panel.filled_toggled,
            self._side_panel.shadow_toggled, self._side_panel.shadow_color_changed,
            self._side_panel.shadow_offset_x_changed, self._side_panel.shadow_offset_y_changed,
            self._side_panel.shadow_blur_x_changed, self._side_panel.shadow_blur_y_changed,
            self._side_panel.pixel_size_changed,
            self._side_panel.fill_tolerance_changed,
            self._side_panel.number_size_changed, self._side_panel.number_text_color_changed,
            self._side_panel.number_style_changed,
            self._side_panel.stamp_selected, self._side_panel.stamp_size_changed,
            self._side_panel.text_bold_changed, self._side_panel.text_italic_changed,
            self._side_panel.text_underline_changed, self._side_panel.text_strikethrough_changed,
            self._side_panel.text_alignment_changed, self._side_panel.text_direction_changed,
            self._side_panel.text_bg_enabled_changed, self._side_panel.text_bg_color_changed,
        ):
            sig.connect(lambda *_: self._on_any_prop_changed())

        # Canvas signals
        self._canvas.element_selected.connect(self._on_element_selected)
        self._canvas.request_text_edit.connect(self._on_text_edit_request)
        self._canvas.zoom_changed.connect(self._on_zoom_changed)
        # Eyedropper: return to previous tool after pick, update side panel swatches
        self._canvas._eyedropper_done.connect(self._on_tool_selected)
        self._canvas.fg_color_picked.connect(self._on_eyedropper_fg)
        self._canvas.bg_color_picked.connect(self._on_eyedropper_bg)

        # Status bar signals
        self._canvas.mouse_moved.connect(self._on_mouse_moved)
        self._canvas.element_selected.connect(self._on_selection_for_status)
        self._canvas.elements_changed.connect(self._on_elements_for_status)
        self._canvas.zoom_changed.connect(self._status_bar.update_zoom)
        self._status_bar.detach_requested.connect(self._toggle_info_window)
        self._status_bar.zoom_requested.connect(self._on_zoom_input)
        # Initial canvas size
        bg = self._canvas._background
        if not bg.isNull():
            self._status_bar.update_canvas_size(bg.width(), bg.height())

        self._setup_shortcuts()
        self._on_tool_selected(ToolType.SELECT)
        NumberElement.reset_counter()

        # Apply saved app theme
        if self._settings_manager:
            self.apply_app_theme(self._settings_manager.settings.app_theme)
            canvas_bg = getattr(self._settings_manager.settings, 'canvas_background', 'dark')
            self._canvas.set_canvas_background(canvas_bg)
            # Apply snap settings
            s = self._settings_manager.settings
            self._canvas.snap_enabled = s.snap_enabled
            self._canvas.snap_to_canvas = s.snap_to_canvas
            self._canvas.snap_to_elements = s.snap_to_elements
            self._canvas.snap_threshold = s.snap_threshold
            self._canvas.snap_grid_enabled = s.snap_grid_enabled
            self._canvas.snap_grid_size = s.snap_grid_size
            self._canvas.show_grid = s.show_grid

        # Auto-copy the raw capture to clipboard when the editor opens
        copy_to_clipboard(screenshot)

    # Theme-driven chrome colors (updated by apply_app_theme)
    _chrome_bg = QColor(10, 10, 20)       # fully opaque — no transparency bleed
    _chrome_accent = QColor(116, 0, 150)  # border accent from theme

    def paintEvent(self, event):
        """Draw window chrome: opaque background fill + themed accent border."""
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect()
        # Full opaque background fill (auto-fill handles base, this covers edges)
        p.setBrush(self._chrome_bg)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(r)
        # Accent border from theme (2 px)
        p.setPen(QPen(self._chrome_accent, 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(r.adjusted(1, 1, -1, -1))
        p.end()

    # --- Border resize cursor + drag: event filter installed on every child widget ---

    _EDGE_MARGIN = 12  # px grab zone at each window edge for resize
    _CURSOR_MAP = {
        Qt.Edge.LeftEdge  | Qt.Edge.TopEdge:    Qt.CursorShape.SizeFDiagCursor,
        Qt.Edge.RightEdge | Qt.Edge.BottomEdge: Qt.CursorShape.SizeFDiagCursor,
        Qt.Edge.RightEdge | Qt.Edge.TopEdge:    Qt.CursorShape.SizeBDiagCursor,
        Qt.Edge.LeftEdge  | Qt.Edge.BottomEdge: Qt.CursorShape.SizeBDiagCursor,
        Qt.Edge.LeftEdge:                        Qt.CursorShape.SizeHorCursor,
        Qt.Edge.RightEdge:                       Qt.CursorShape.SizeHorCursor,
        Qt.Edge.TopEdge:                         Qt.CursorShape.SizeVerCursor,
        Qt.Edge.BottomEdge:                      Qt.CursorShape.SizeVerCursor,
    }

    def _edge_at(self, global_pos: QPoint) -> Qt.Edges:
        p = self.mapFromGlobal(global_pos)
        x, y, w, h = p.x(), p.y(), self.width(), self.height()
        M = self._EDGE_MARGIN
        edge = Qt.Edges()
        if x < M:     edge |= Qt.Edge.LeftEdge
        if x > w - M: edge |= Qt.Edge.RightEdge
        if y < M:     edge |= Qt.Edge.TopEdge
        if y > h - M: edge |= Qt.Edge.BottomEdge
        return edge

    def _install_border_filter(self):
        """Install event filter on self and all current child widgets.

        Safe to call repeatedly — Qt silently ignores duplicate installs on
        the same (object, filter) pair, so reparented buttons are covered
        without double-firing.
        """
        self.installEventFilter(self)
        for w in self.findChildren(QWidget):
            w.installEventFilter(self)

    def showEvent(self, event):
        super().showEvent(event)
        if not getattr(self, "_border_filter_installed", False):
            self._border_filter_installed = True
            self._border_cursor_on = False
        self._install_border_filter()
        if hasattr(self, "_close_btn_overlay"):
            m = 6
            self._close_btn_overlay.move(
                self.width() - self._close_btn_overlay.width() - m, m
            )
            self._close_btn_overlay.raise_()

    def _clear_border_cursor(self):
        """Safely clear the border override cursor if active."""
        if self._border_cursor_on:
            QApplication.restoreOverrideCursor()
            self._border_cursor_on = False

    def eventFilter(self, obj, event):
        et = event.type()

        # Clear stale override cursor when mouse leaves the window
        if et == QEvent.Type.Leave and obj is self:
            self._clear_border_cursor()
            return False

        if et == QEvent.Type.MouseMove:
            # Title-bar drag
            if event.buttons() & Qt.MouseButton.LeftButton and self._drag_pos is not None:
                new_pos = QCursor.pos() - self._drag_pos
                # Clamp to keep at least 80px visible on any screen edge
                screen = self.screen()
                if screen:
                    sg = screen.availableGeometry()
                    min_visible = 80
                    nx = max(sg.left() - self.width() + min_visible,
                             min(new_pos.x(), sg.right() - min_visible))
                    ny = max(sg.top(),
                             min(new_pos.y(), sg.bottom() - min_visible))
                    new_pos = QPoint(nx, ny)
                self.move(new_pos)
                return False
            # Border resize cursor (hover only, no buttons pressed)
            gpos = QCursor.pos()
            edge = self._edge_at(gpos)
            if edge and not QApplication.mouseButtons():
                shape = self._CURSOR_MAP.get(edge, Qt.CursorShape.ArrowCursor)
                self._clear_border_cursor()
                QApplication.setOverrideCursor(shape)
                self._border_cursor_on = True
            elif self._border_cursor_on:
                self._clear_border_cursor()

        elif et == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            gpos = event.globalPosition().toPoint()
            edge = self._edge_at(gpos)
            if edge and obj is not getattr(self, "_close_btn_overlay", None):
                self._clear_border_cursor()
                self.windowHandle().startSystemResize(edge)
                return True  # consume — don't pass to canvas/toolbar
            # Title-bar drag (no border)
            lpos = self.mapFromGlobal(gpos)
            if lpos.y() < 40:
                self._drag_pos = gpos - self.frameGeometry().topLeft()

        elif et == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = None
            # After system resize ends, ensure cursor is cleaned up
            self._clear_border_cursor()

        return False  # never consume — only side-effects

    # --- Window drag fallback (when mouse is directly on EditorWindow, not a child) ---

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if event.position().y() < 40:
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and self._drag_pos is not None:
            new_pos = event.globalPosition().toPoint() - self._drag_pos
            screen = self.screen()
            if screen:
                sg = screen.availableGeometry()
                min_visible = 80
                nx = max(sg.left() - self.width() + min_visible,
                         min(new_pos.x(), sg.right() - min_visible))
                ny = max(sg.top(),
                         min(new_pos.y(), sg.bottom() - min_visible))
                new_pos = QPoint(nx, ny)
            self.move(new_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = None
        super().mouseReleaseEvent(event)

    # --- Tool selection ---

    _PANEL_PROP_KEYS = {'color', 'stroke', 'effects', 'text', 'mask', 'number', 'stamp', 'fill', 'fill_tol'}

    def _on_tool_selected(self, tool_type: ToolType):
        # Save departing tool's props before switching
        if hasattr(self, '_current_tool_type') and not self._canvas.selected_element:
            self._save_tool_properties(self._current_tool_type)
        tool = self._tools.get(tool_type)
        if tool:
            # Deselect any element so the panel switches to the new tool's defaults
            if self._canvas.selected_element:
                self._canvas.select_element(None)
            self._canvas.set_tool(tool)
            self._multi_toolbar.set_active_tool(tool_type)
            self._current_tool_type = tool_type
            self._side_panel.update_for_tool(tool_type)
            self._load_tool_properties(tool_type)
            # Show panel whenever the new tool has configurable properties
            from paparaz.ui.side_panel import TOOL_SECTIONS
            s = TOOL_SECTIONS.get(tool_type, {})
            if any(s.get(k) for k in self._PANEL_PROP_KEYS) and self._side_panel._mode != "hidden":
                self._side_panel.show()

    # --- Element selection -> side panel ---

    def _on_element_selected(self, element):
        self._side_panel.on_element_selected(element)
        if hasattr(self, '_layers_panel') and self._layers_panel.isVisible():
            self._layers_panel.refresh()

    def _on_eyedropper_fg(self, color: str):
        """Eyedropper picked a foreground color — update side panel swatch + recent palette."""
        self._side_panel._fg_color = color
        self._side_panel._update_swatch(self._side_panel._fg_btn, color)
        self._side_panel._recent_palette.add_color(color)

    def _on_eyedropper_bg(self, color: str):
        """Eyedropper picked a background color — update side panel swatch + recent palette."""
        self._side_panel._bg_color = color
        self._side_panel._update_swatch(self._side_panel._bg_btn, color)
        self._side_panel._recent_palette.add_color(color)

    def _on_panel_mode_changed(self, mode: str):
        if mode == "hidden":
            self._side_panel.hide()

    def _on_recent_colors_changed(self, colors: list):
        """Persist recent colors to settings whenever the palette changes."""
        if self._settings_manager:
            self._settings_manager.settings.recent_colors = colors
            self._settings_manager.save()

    def _show_tool_props(self, tool_type: ToolType, global_pos: QPoint):
        """Show the floating props panel with the given tool's sections."""
        self._side_panel.update_for_tool(tool_type)
        self._load_tool_properties(tool_type)
        self._side_panel.show()

    # --- Per-tool property persistence ---

    def _load_tool_properties(self, tool_type: ToolType):
        """Apply saved properties for tool_type directly to canvas + panel UI."""
        if not self._settings_manager:
            return
        props = self._settings_manager.settings.tool_properties.get(tool_type.name, {})
        if not props:
            return
        # Update canvas template state directly (bypasses setters → no undo entries)
        c = self._canvas
        if "foreground_color" in props: c._fg_color = props["foreground_color"]
        if "background_color" in props: c._bg_color = props["background_color"]
        if "line_width" in props:       c._line_width = float(props["line_width"])
        if "opacity" in props:          c._opacity = float(props["opacity"])
        if "cap_style" in props:        c._cap_style = props["cap_style"]
        if "join_style" in props:       c._join_style = props["join_style"]
        if "dash_pattern" in props:     c._dash_pattern = props["dash_pattern"]
        if "shadow_enabled" in props:   c._shadow.enabled = bool(props["shadow_enabled"])
        if "shadow_color" in props:     c._shadow.color = props["shadow_color"]
        if "shadow_offset_x" in props:  c._shadow.offset_x = float(props["shadow_offset_x"])
        if "shadow_offset_y" in props:  c._shadow.offset_y = float(props["shadow_offset_y"])
        if "shadow_blur_x" in props:    c._shadow.blur_x = float(props["shadow_blur_x"])
        if "shadow_blur_y" in props:    c._shadow.blur_y = float(props["shadow_blur_y"])
        if "shadow_blur" in props and "shadow_blur_x" not in props:
            c._shadow.blur_x = float(props["shadow_blur"])
            c._shadow.blur_y = float(props["shadow_blur"])
        if "font_family" in props:      c._font_family = props["font_family"]
        if "font_size" in props:        c._font_size = max(1, int(props["font_size"]))
        # Sync panel UI without firing signals
        self._side_panel.apply_properties_silent(props)

        # ── Restore tool-instance fields that apply_properties_silent cannot reach
        # because signals are suppressed during silent loading.
        if tool_type == ToolType.NUMBERING:
            if "number_size" in props:
                self._numbering_tool.marker_size = float(props["number_size"])
            if "number_text_color" in props:
                self._numbering_tool.text_color = props["number_text_color"]
            if "number_style" in props:
                self._numbering_tool.number_style = props["number_style"]
        elif tool_type == ToolType.STAMP:
            if "stamp_id" in props:
                self._stamp_tool.stamp_id = props["stamp_id"]
            if "stamp_size" in props:
                self._stamp_tool.stamp_size = float(props["stamp_size"])
        elif tool_type == ToolType.MASQUERADE:
            if "pixel_size" in props:
                self._masquerade_tool.pixel_size = int(props["pixel_size"])
        elif tool_type == ToolType.FILL:
            if "fill_tolerance" in props:
                fill_tool = self._tools.get(ToolType.FILL)
                if fill_tool:
                    fill_tool.tolerance = int(props["fill_tolerance"])
        elif tool_type == ToolType.TEXT:
            tt = self._text_tool
            if "text_bold" in props:          tt.set_bold(bool(props["text_bold"]))
            if "text_italic" in props:        tt.set_italic(bool(props["text_italic"]))
            if "text_underline" in props:     tt.set_underline(bool(props["text_underline"]))
            if "text_strikethrough" in props: tt.strikethrough = bool(props["text_strikethrough"])
            if "text_alignment" in props:     tt.set_alignment(props["text_alignment"])
            if "text_direction" in props:     tt.set_direction(props["text_direction"])
            if "text_bg_enabled" in props:    tt.set_bg_enabled(bool(props["text_bg_enabled"]))
            if "text_bg_color" in props:      tt.set_bg_color(props["text_bg_color"])
            if "text_stroke_enabled" in props: tt.set_stroke_enabled(bool(props["text_stroke_enabled"]))
            if "text_stroke_color" in props:   tt.set_stroke_color(props["text_stroke_color"])
            if "text_stroke_width" in props:   tt.set_stroke_width(float(props["text_stroke_width"]))

    def _save_tool_properties(self, tool_type: ToolType):
        """Snapshot current panel state into the settings dict for tool_type."""
        if not self._settings_manager:
            return
        props = self._side_panel.get_current_properties()
        if props:
            self._settings_manager.settings.tool_properties[tool_type.name] = props

    def _flush_tool_properties(self):
        """Write settings to disk (called by debounce timer)."""
        if self._settings_manager:
            self._settings_manager.save()

    def _on_any_prop_changed(self):
        """Called by any property-change signal when no element is selected.
        Schedules a debounced settings save so the tool remembers its values."""
        if self._canvas.selected_element:
            return  # Only persist tool defaults, not element overrides
        self._save_tool_properties(self._current_tool_type)
        self._settings_save_timer.start()

    def showEvent(self, event):
        super().showEvent(event)
        # Initialise border-resize event filter (must happen after window is shown)
        if not getattr(self, "_border_filter_installed", False):
            self._border_filter_installed = True
            self._border_cursor_on = False
        self._install_border_filter()
        # Pin close button to top-right corner
        m = 6
        if hasattr(self, "_close_btn_overlay"):
            self._close_btn_overlay.move(
                self.width() - self._close_btn_overlay.width() - m, m
            )
            self._close_btn_overlay.raise_()
        # Place the floating side panel to the right of the editor (or left if no room)
        if not self._panel_initially_placed:
            self._panel_initially_placed = True
            editor_global = self.mapToGlobal(QPoint(0, 0))
            panel_w = self._side_panel.sizeHint().width() or 220
            gap = 10
            screen_rect = QApplication.primaryScreen().availableGeometry()
            panel_x = editor_global.x() + self.width() + gap
            if panel_x + panel_w > screen_rect.right():
                panel_x = max(screen_rect.left(), editor_global.x() - panel_w - gap)
            panel_h = self._side_panel.height()
            panel_y = max(screen_rect.top(), min(editor_global.y(), screen_rect.bottom() - panel_h))
            self._side_panel.move(panel_x, panel_y)
        # Apply default zoom on first show
        if not getattr(self, '_initial_zoom_applied', False):
            self._initial_zoom_applied = True
            self._apply_default_zoom()

    def _on_zoom_changed(self, zoom: float):
        """Adapt window size to fit the zoomed content, clamped to screen."""
        # Suppress during initial zoom — window was already sized correctly in _open_editor
        if getattr(self, '_applying_initial_zoom', False):
            return
        bg = self._canvas._background
        if bg.isNull():
            return
        # Desired canvas size at this zoom level
        img_w = int(bg.width() * zoom)
        img_h = int(bg.height() * zoom)
        # Account for toolbar/statusbar/margins chrome
        chrome_w = self.width() - self._canvas.width()
        chrome_h = self.height() - self._canvas.height()
        desired_w = img_w + chrome_w
        desired_h = img_h + chrome_h
        # Clamp to screen available geometry (leave 40px margin)
        screen = self.screen()
        if screen:
            sg = screen.availableGeometry()
            desired_w = max(400, min(desired_w, sg.width() - 40))
            desired_h = max(300, min(desired_h, sg.height() - 40))
        self.resize(desired_w, desired_h)

    def _on_zoom_input(self, zoom: float):
        """Handle manual zoom input from the status bar combo."""
        if zoom < 0:
            # "Fit" — compute zoom to fit canvas in current window
            bg = self._canvas._background
            if bg.isNull():
                return
            chrome_w = self.width() - self._canvas.width()
            chrome_h = self.height() - self._canvas.height()
            avail_w = max(100, self.width() - chrome_w)
            avail_h = max(100, self.height() - chrome_h)
            fit = min(avail_w / bg.width(), avail_h / bg.height())
            self._canvas.set_zoom(fit)
        else:
            self._canvas.set_zoom(zoom)

    def _apply_default_zoom(self):
        """Set zoom level based on user preference.

        The window geometry was already sized to fit the image in _open_editor, so we
        suppress the zoom-changed resize handler during this initial zoom application to
        avoid the window shrinking due to chrome-height estimation errors.
        """
        if not self._settings_manager:
            return
        s = self._settings_manager.settings
        mode = getattr(s, 'default_zoom', 'fit')
        bg = self._canvas._background
        self._applying_initial_zoom = True
        try:
            if mode == "100":
                self._canvas.set_zoom(1.0)
            elif mode == "fill":
                canvas_w = self._canvas.width()
                canvas_h = self._canvas.height()
                if bg.width() > 0 and bg.height() > 0:
                    z = max(canvas_w / bg.width(), canvas_h / bg.height())
                    self._canvas.set_zoom(z)
            elif mode == "remember":
                z = getattr(s, 'last_zoom_level', 1.0)
                self._canvas.set_zoom(max(0.1, min(10.0, z)))
            else:  # "fit" — default
                canvas_w = self._canvas.width()
                canvas_h = self._canvas.height()
                if bg.width() > 0 and bg.height() > 0:
                    z = min(canvas_w / bg.width(), canvas_h / bg.height(), 1.0)
                    self._canvas.set_zoom(z)
        finally:
            self._applying_initial_zoom = False

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._multi_toolbar.relayout(self.width(), self.height(), 0)
        # Pin close button to top-right
        m = 6
        if hasattr(self, "_close_btn_overlay"):
            self._close_btn_overlay.move(
                self.width() - self._close_btn_overlay.width() - m, m
            )
            self._close_btn_overlay.raise_()
        # Re-scan children so reparented buttons always have the border filter
        if getattr(self, "_border_filter_installed", False):
            self._install_border_filter()
        # Side panel is a free-floating top-level — no clamping needed

    def _on_text_edit_request(self, element):
        if isinstance(element, TextElement):
            self._on_tool_selected(ToolType.TEXT)
            self._text_tool.start_editing(element)
            self._canvas.select_element(None)

    # --- Theme presets ---

    def _show_settings(self):
        from paparaz.ui.settings_dialog import SettingsDialog
        dlg = SettingsDialog(self._settings_manager, parent=self)
        dlg.exec()

    def apply_app_theme(self, theme_id: str):
        """Apply a UI theme to the editor and its child widgets."""
        from paparaz.ui.app_theme import get_theme, build_tool_qss, build_panel_qss
        from paparaz.ui.icons import combo_arrow_css
        theme = get_theme(theme_id)
        # Apply to all toolbar buttons (strips are already transparent)
        if hasattr(self, '_multi_toolbar'):
            self._multi_toolbar.apply_theme(theme)
        # Apply to side panel (also stores theme for paintEvent)
        if hasattr(self, '_side_panel'):
            self._side_panel.apply_theme(theme)
        # Update chrome colors from theme
        self._chrome_bg = QColor(theme.get("bg1", "#1e1e2e"))
        self._chrome_accent = QColor(theme.get("accent", "#740096"))
        # Keep window palette in sync so auto-fill matches
        pal = self.palette()
        pal.setColor(pal.ColorRole.Window, self._chrome_bg)
        self.setPalette(pal)
        # Update selection handle + border accent color to match theme
        set_selection_accent(theme.get("accent", "#740096"))
        if hasattr(self, '_canvas'):
            self._canvas.update()
        # Apply background color to editor root
        bg = theme["bg1"]
        self.setStyleSheet(f"QWidget#editorRoot {{ background: {bg}; }}")
        # Apply settings-driven canvas/panel values
        if hasattr(self, '_settings_manager') and self._settings_manager:
            s = self._settings_manager.settings
            if hasattr(self, '_canvas'):
                self._canvas.set_canvas_background(getattr(s, 'canvas_background', 'dark'))
                self._canvas.set_zoom_scroll_factor(getattr(s, 'zoom_scroll_factor', 1.1))
                # Sync snap settings
                self._canvas.snap_enabled = s.snap_enabled
                self._canvas.snap_to_canvas = s.snap_to_canvas
                self._canvas.snap_to_elements = s.snap_to_elements
                self._canvas.snap_threshold = s.snap_threshold
                self._canvas.snap_grid_enabled = s.snap_grid_enabled
                self._canvas.snap_grid_size = s.snap_grid_size
                self._canvas.show_grid = s.show_grid
            if hasattr(self, '_side_panel'):
                self._side_panel.set_auto_hide_ms(getattr(s, 'panel_auto_hide_ms', 3000))

    def _show_theme_presets(self):
        from paparaz.ui.theme_presets import ThemePresetPopup
        sm = self._settings_manager
        current = sm.settings.default_theme_preset if sm else ""
        popup = ThemePresetPopup(current_preset_id=current, parent=self)
        popup.preset_applied.connect(self._apply_theme_preset)
        # Centre over editor
        popup.adjustSize()
        popup.move(
            self.x() + (self.width() - popup.width()) // 2,
            self.y() + (self.height() - popup.height()) // 2,
        )
        popup.exec()

    def _apply_theme_preset(self, preset_id: str):
        from paparaz.ui.theme_presets import PRESETS
        from paparaz.ui.side_panel import TOOL_SECTIONS
        preset = PRESETS.get(preset_id)
        if not preset:
            return
        c = self._canvas
        # Apply to canvas state
        c._fg_color = preset.fg_color
        c._bg_color = preset.bg_color
        c._line_width = float(preset.line_width)
        c._opacity = preset.opacity
        c._shadow.enabled = preset.shadow_enabled
        c._shadow.color = preset.shadow_color
        c._shadow.offset_x = preset.shadow_offset_x
        c._shadow.offset_y = preset.shadow_offset_y
        c._shadow.blur_x = preset.shadow_blur
        c._shadow.blur_y = preset.shadow_blur
        c._font_family = preset.font_family
        c._font_size = preset.font_size
        # Refresh side panel
        self._side_panel.apply_properties_silent({
            "foreground_color": preset.fg_color,
            "background_color": preset.bg_color,
            "line_width": preset.line_width,
            "opacity": preset.opacity,
            "shadow_enabled": preset.shadow_enabled,
            "shadow_color": preset.shadow_color,
            "shadow_offset_x": preset.shadow_offset_x,
            "shadow_offset_y": preset.shadow_offset_y,
            "shadow_blur": preset.shadow_blur,
            "font_family": preset.font_family,
            "font_size": preset.font_size,
            "text_bg_color": preset.text_bg_color,
        })
        # Persist to all tool slots so switching tools keeps the preset
        for tool_type, sections in TOOL_SECTIONS.items():
            key = tool_type.name
            props = self._settings_manager.settings.tool_properties.get(key, {}).copy() if self._settings_manager else {}
            if sections.get("color"):
                props["foreground_color"] = preset.fg_color
                if sections.get("bg", True):
                    props["background_color"] = preset.bg_color
            if sections.get("stroke"):
                props["line_width"] = float(preset.line_width)
            if sections.get("effects"):
                props["opacity"] = preset.opacity
                props["shadow_enabled"] = preset.shadow_enabled
                props["shadow_color"] = preset.shadow_color
                props["shadow_offset_x"] = preset.shadow_offset_x
                props["shadow_offset_y"] = preset.shadow_offset_y
                props["shadow_blur"] = preset.shadow_blur
            if sections.get("text") or sections.get("stroke"):
                props["font_family"] = preset.font_family
                props["font_size"] = preset.font_size
            if sections.get("text"):
                props["text_bg_color"] = preset.text_bg_color
            if self._settings_manager:
                self._settings_manager.settings.tool_properties[key] = props
        if self._settings_manager:
            self._settings_manager.settings.default_theme_preset = preset_id
            self._settings_manager.save()

    # --- Property handlers ---

    def _on_filled_toggled(self, filled):
        self._canvas.set_filled(filled)

    def _on_fill_tolerance_changed(self, tolerance: int):
        fill_tool = self._tools.get(ToolType.FILL)
        if fill_tool:
            fill_tool.tolerance = tolerance

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

    def _on_number_style_changed(self, style: str):
        self._numbering_tool.number_style = style
        elem = self._canvas.selected_element
        if isinstance(elem, NumElem):
            elem.number_style = style
            self._canvas.update()

    def _on_number_reset(self):
        NumElem.reset_counter()
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
        at = self._text_tool._active_text
        if at is not None:
            at.bold = v
            at.auto_size()
            self._canvas.set_preview(at)
        e = self._canvas.selected_element
        if isinstance(e, TextElement):
            e.bold = v
            e.auto_size()
            self._canvas.update()

    def _on_text_italic(self, v):
        self._text_tool.set_italic(v)
        at = self._text_tool._active_text
        if at is not None:
            at.italic = v
            at.auto_size()
            self._canvas.set_preview(at)
        e = self._canvas.selected_element
        if isinstance(e, TextElement):
            e.italic = v
            e.auto_size()
            self._canvas.update()

    def _on_text_underline(self, v):
        self._text_tool.set_underline(v)
        at = self._text_tool._active_text
        if at is not None:
            at.underline = v
            self._canvas.set_preview(at)
        e = self._canvas.selected_element
        if isinstance(e, TextElement):
            e.underline = v
            self._canvas.update()

    def _on_strikethrough(self, v):
        self._text_tool.strikethrough = v
        at = self._text_tool._active_text
        if at is not None:
            at.strikethrough = v
            self._canvas.set_preview(at)
        e = self._canvas.selected_element
        if isinstance(e, TextElement):
            e.strikethrough = v
            self._canvas.update()

    def _on_text_alignment(self, align):
        self._text_tool.set_alignment(align)
        # set_alignment already handles _active_text
        e = self._canvas.selected_element
        if isinstance(e, TextElement):
            m = {"left": Qt.AlignmentFlag.AlignLeft, "center": Qt.AlignmentFlag.AlignCenter, "right": Qt.AlignmentFlag.AlignRight}
            e.alignment = m.get(align, Qt.AlignmentFlag.AlignLeft)
            self._canvas.update()

    def _on_text_direction(self, d):
        self._text_tool.set_direction(d)
        # set_direction already handles _active_text
        e = self._canvas.selected_element
        if isinstance(e, TextElement):
            e.direction = Qt.LayoutDirection.RightToLeft if d == "rtl" else Qt.LayoutDirection.LeftToRight
            self._canvas.update()

    def _on_text_bg_enabled(self, v):
        self._text_tool.set_bg_enabled(v)
        # set_bg_enabled already handles _active_text
        e = self._canvas.selected_element
        if isinstance(e, TextElement):
            e.bg_enabled = v
            e.auto_size()
            self._canvas.update()

    def _on_text_bg_color(self, c):
        self._text_tool.set_bg_color(c)
        # set_bg_color already handles _active_text
        e = self._canvas.selected_element
        if isinstance(e, TextElement):
            e.bg_color = c
            self._canvas.update()

    def _on_text_stroke_enabled(self, v):
        self._text_tool.set_stroke_enabled(v)
        # set_stroke_enabled already handles _active_text
        e = self._canvas.selected_element
        if isinstance(e, TextElement):
            e.stroke_enabled = v
            self._canvas.update()

    def _on_text_stroke_color(self, c):
        self._text_tool.set_stroke_color(c)
        # set_stroke_color already handles _active_text
        e = self._canvas.selected_element
        if isinstance(e, TextElement):
            e.stroke_color = c
            self._canvas.update()

    def _on_text_stroke_width(self, w):
        self._text_tool.set_stroke_width(w)
        # set_stroke_width already handles _active_text
        e = self._canvas.selected_element
        if isinstance(e, TextElement):
            e.stroke_width = w
            self._canvas.update()

    def _on_fg_color_changed(self, color: str):
        self._canvas.set_foreground_color(color)
        at = self._text_tool._active_text
        if at is not None:
            at.style.foreground_color = color
            self._canvas.set_preview(at)

    def _on_bg_color_changed(self, color: str):
        self._canvas.set_background_color(color)
        at = self._text_tool._active_text
        if at is not None:
            at.style.background_color = color
            self._canvas.set_preview(at)

    def _on_font_family_changed(self, family: str):
        self._canvas.set_font_family(family)
        # Also apply to actively editing text element
        at = self._text_tool._active_text
        if at is not None:
            at.style.font_family = family
            at.auto_size()
            self._canvas.set_preview(at)

    def _on_font_size_changed(self, size: int):
        self._canvas.set_font_size(size)
        # Also apply to actively editing text element
        at = self._text_tool._active_text
        if at is not None:
            at.style.font_size = max(1, size)
            at.auto_size()
            self._canvas.set_preview(at)

    # --- Canvas resize dialog ---

    def _show_canvas_resize(self):
        dlg = CanvasResizeDialog(
            self._canvas._background.width(),
            self._canvas._background.height(),
            parent=self,
        )
        if dlg.exec():
            w, h = dlg.get_size()
            self._canvas.resize_canvas(w, h)

    # --- Auto-save recovery ---

    def _auto_save_recovery(self):
        """Periodically save a recovery snapshot."""
        from paparaz.core.recovery import save_snapshot
        pix = self._canvas.render_to_pixmap()
        save_snapshot(pix, id(self))

    # --- Layers panel ---

    def _toggle_layers_panel(self):
        if self._layers_panel.isVisible():
            self._layers_panel.hide()
        else:
            # Position to the left of the editor
            editor_global = self.mapToGlobal(QPoint(0, 0))
            panel_w = self._layers_panel.width()
            gap = 10
            screen_rect = QApplication.primaryScreen().availableGeometry()
            panel_x = editor_global.x() - panel_w - gap
            if panel_x < screen_rect.left():
                panel_x = editor_global.x() + self.width() + gap
            panel_y = max(screen_rect.top(), editor_global.y())
            self._layers_panel.move(panel_x, panel_y)
            self._layers_panel.resize(200, min(400, self.height()))
            self._layers_panel.show()
            self._layers_panel.refresh()

    def _on_elements_changed(self):
        if hasattr(self, '_layers_panel') and self._layers_panel.isVisible():
            self._layers_panel.refresh()

    # ── Status bar handlers ─────────────────────────────────────────────────

    def _on_mouse_moved(self, x: float, y: float):
        self._status_bar.update_mouse_pos(x, y)
        if self._info_window:
            self._info_window.update_mouse_pos(x, y)

    def _on_selection_for_status(self, element):
        if element and hasattr(element, 'bounding_rect'):
            r = element.bounding_rect()
            self._status_bar.update_selection(r.width(), r.height())
            if self._info_window:
                self._info_window.update_selection(r.width(), r.height())
        else:
            self._status_bar.clear_selection()
            if self._info_window:
                self._info_window.clear_selection()

    def _on_elements_for_status(self):
        count = len(self._canvas.elements)
        self._status_bar.update_element_count(count)
        if self._info_window:
            self._info_window.update_element_count(count)

    def _toggle_info_window(self):
        if self._info_window and self._info_window.isVisible():
            self._info_window.close()
            self._info_window = None
            return
        self._info_window = InfoWindow()
        self._info_window.closed.connect(self._on_info_window_closed)
        # Sync current state
        bg = self._canvas._background
        if not bg.isNull():
            self._info_window.update_canvas_size(bg.width(), bg.height())
        self._info_window.update_zoom(self._canvas.zoom)
        self._info_window.update_element_count(len(self._canvas.elements))
        sel = self._canvas.selected_element
        if sel and hasattr(sel, 'bounding_rect'):
            r = sel.bounding_rect()
            self._info_window.update_selection(r.width(), r.height())
        self._info_window.show()

    def _on_info_window_closed(self):
        self._info_window = None

    def _on_layer_element_selected(self, elem):
        if elem:
            self._canvas.select_element(elem)

    # --- Shortcuts ---

    def _setup_shortcuts(self):
        """Register all keyboard shortcuts.

        All shortcuts are stored in self._all_shortcuts so they can be bulk-disabled
        while the text tool has an active text entry (typing mode).
        """
        self._all_shortcuts: list[QShortcut] = []

        def sc(key, cb):
            s = QShortcut(QKeySequence(key), self)
            s.activated.connect(cb)
            self._all_shortcuts.append(s)
            return s

        sc("Ctrl+Z",       self._canvas.history.undo)
        sc("Ctrl+Y",       self._canvas.history.redo)
        sc("Ctrl+Shift+Z", self._canvas.history.redo)
        sc("Ctrl+S",       self._save_as)
        sc("Ctrl+Shift+S", lambda: self._save_as(force_dialog=False))
        sc("Ctrl+Shift+O", self._open_project)
        sc("Ctrl+Shift+P", self._save_project_as)
        sc("Ctrl+C",       self._copy_to_clipboard)
        sc("Ctrl+V",       self._paste)
        sc("Ctrl+]",       self._canvas.bring_to_front)
        sc("Ctrl+[",       self._canvas.send_to_back)
        sc("Ctrl+P",       self._pin_current)
        sc("Ctrl+=",       lambda: self._canvas.set_zoom(self._canvas.zoom * 1.25))
        sc("Ctrl+-",       lambda: self._canvas.set_zoom(self._canvas.zoom * 0.8))
        sc("Ctrl+0",       lambda: self._canvas.set_zoom(1.0))
        sc("Escape",       self._confirm_close)

        tool_keys = {
            "V": ToolType.SELECT,    "P": ToolType.PEN,
            "B": ToolType.BRUSH,     "H": ToolType.HIGHLIGHT,
            "L": ToolType.LINE,         "A": ToolType.ARROW,
            "Q": ToolType.CURVED_ARROW, "R": ToolType.RECTANGLE,
            "E": ToolType.ELLIPSE,      "T": ToolType.TEXT,
            "N": ToolType.NUMBERING,    "X": ToolType.ERASER,
            "M": ToolType.MASQUERADE,   "S": ToolType.STAMP,
            "C": ToolType.CROP,         "F": ToolType.FILL,
            "Z": ToolType.SLICE,        "I": ToolType.EYEDROPPER,
            "G": ToolType.MAGNIFIER,
            "D": ToolType.MEASURE,
        }
        for key, tt in tool_keys.items():
            sc(key, lambda _tt=tt: self._on_tool_selected(_tt))

        # Wire text-tool editing state changes → enable/disable all shortcuts
        self._text_tool.on_editing_changed = self._on_text_editing_changed
        # Wire text-tool Ctrl+B/I/U → sync side panel checkboxes
        self._text_tool.on_format_changed = self._on_text_format_shortcut

    def _on_text_format_shortcut(self, attr: str, value: bool):
        """Called when Ctrl+B/I/U is pressed in a text box — sync the side panel checkbox."""
        if attr == 'bold':
            self._side_panel.set_text_bold_silent(value)
        elif attr == 'italic':
            self._side_panel.set_text_italic_silent(value)
        elif attr == 'underline':
            self._side_panel.set_text_underline_silent(value)

    def _on_text_editing_changed(self, editing: bool):
        """Called by TextTool when typing starts (editing=True) or ends (editing=False).

        While typing is active every shortcut is disabled so that key events
        reach the canvas's keyPressEvent unimpeded.
        After typing is done all shortcuts are re-enabled.
        """
        for s in self._all_shortcuts:
            s.setEnabled(not editing)
        # Always ensure canvas has focus while editing so keys go to the right place
        if editing:
            self._canvas.setFocus()

    def _on_canvas_modified(self):
        """Mark as unsaved whenever the canvas changes (elements added/removed/moved)."""
        self._was_saved = False

    def _confirm_close(self):
        # No annotations at all → just close
        if not self._canvas.elements and not self._canvas._preview_element:
            self.close()
            return
        # Already saved, no changes since → close without prompting
        if self._was_saved:
            self.close()
            return
        # Respect the "confirm before closing" setting
        _sm = getattr(self, '_settings_manager', None)
        if _sm and not getattr(_sm.settings, 'confirm_close_unsaved', True):
            self.close()
            return
        msg = QMessageBox(self)
        msg.setWindowTitle("Close Editor")
        msg.setWindowFlags(msg.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setText("You have unsaved changes.")
        msg.setInformativeText(
            "Would you like to save before closing?"
        )
        msg.setStyleSheet(
            "QMessageBox { background: #1a1a2e; color: #ddd; }"
            "QLabel { color: #ddd; font-size: 12px; }"
            "QPushButton {"
            "  background: #2a2a4e; color: #ddd; border: 1px solid #555;"
            "  border-radius: 4px; padding: 6px 16px; font-size: 11px;"
            "}"
            "QPushButton:hover { background: #3a3a5e; }"
            "QPushButton:pressed { background: #1a1a3e; }"
            "QPushButton:default { border: 1px solid #740096; }"
        )

        save_btn   = msg.addButton("Save && Exit",   QMessageBox.ButtonRole.AcceptRole)
        discard_btn = msg.addButton("Discard && Exit", QMessageBox.ButtonRole.DestructiveRole)
        cancel_btn = msg.addButton("Cancel",           QMessageBox.ButtonRole.RejectRole)
        msg.setDefaultButton(save_btn)
        msg.exec()

        clicked = msg.clickedButton()
        if clicked is save_btn:
            self._save_as(force_dialog=True)
            # Only close if the save completed (was_saved becomes True)
            if self._was_saved:
                self.close()
        elif clicked is discard_btn:
            self.close()

    # --- Save / Copy / Paste / Pin ---

    def _save_as(self, force_dialog: bool = True):
        """Save the canvas.

        Generates a smart filename from the configured pattern and either:
        - Opens a Save As dialog with the generated name pre-filled (default), or
        - Saves silently if auto_save is enabled and force_dialog is False.
        """
        from paparaz.core.filename_pattern import build_save_path, resolve

        sm = self._settings_manager
        s = sm.settings if sm else None

        pattern      = s.filename_pattern     if s else "{yyyy}-{MM}-{dd}_{HH}-{mm}-{ss}"
        sub_pattern  = s.subfolder_pattern    if s else ""
        save_dir     = s.save_directory       if s else ""
        default_fmt  = s.default_format       if s else "png"
        jpg_q        = s.jpg_quality          if s else 90
        counter      = s.save_counter         if s else 1
        auto_save    = (s.auto_save and not force_dialog) if s else False

        pix = self._canvas.render_to_pixmap()
        w, h = pix.width(), pix.height()

        suggested = build_save_path(
            pattern=pattern,
            save_dir=save_dir or str(Path.home() / "Pictures" / "PapaRaZ"),
            subfolder_pattern=sub_pattern,
            ext=default_fmt,
            counter=counter,
            title=getattr(self, "_capture_window_title", ""),
            app=getattr(self, "_capture_app_name", ""),
            width=w,
            height=h,
        )

        if auto_save:
            path = str(suggested)
        else:
            path, _ = QFileDialog.getSaveFileName(
                self, "Save Screenshot",
                str(suggested),
                "PNG (*.png);;JPEG (*.jpg *.jpeg);;SVG (*.svg);;All (*)",
            )
            if not path:
                return
            # Remember the directory the user navigated to for next time
            if sm and s:
                chosen_dir = str(Path(path).parent)
                if chosen_dir != getattr(s, 'save_directory', ''):
                    s.save_directory = chosen_dir

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        ext = path.suffix.lower()

        png_comp = getattr(s, 'png_compression', 6) if s else 6

        if ext == ".svg":
            save_svg(self._canvas._background, str(path), self._canvas.paint_annotations)
        elif ext in (".jpg", ".jpeg"):
            save_jpg(pix, str(path), jpg_q)
        else:
            save_png(pix, str(path), compression=png_comp)

        # Increment persistent counter
        if s:
            s.save_counter = counter + 1
            sm.add_recent(str(path))   # also saves settings

        self._was_saved = True
        self.file_saved.emit(str(path))

        # Post-save actions
        if s and getattr(s, 'auto_copy_on_save', False):
            copy_to_clipboard(pix)
        if s and getattr(s, 'open_after_save', False):
            from PySide6.QtGui import QDesktopServices
            from PySide6.QtCore import QUrl
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

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

    # --- Project file (.papraz) ---

    def _save_project_as(self):
        """Save current session as a .papraz project file (Ctrl+Shift+P)."""
        from paparaz.core.project import save_project
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Project",
            str(Path.home() / "Pictures" / "PapaRaZ" / "untitled.papraz"),
            "PapaRaZ Project (*.papraz)",
        )
        if not path:
            return
        try:
            save_project(path, self._canvas)
            self.setWindowTitle(f"PapaRaZ — {Path(path).name}")
        except Exception as exc:
            QMessageBox.critical(self, "Save Project Failed", str(exc))

    def _open_project(self):
        """Open a .papraz project file and restore canvas state (Ctrl+Shift+O)."""
        from paparaz.core.project import load_project
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Project",
            str(Path.home() / "Pictures" / "PapaRaZ"),
            "PapaRaZ Project (*.papraz)",
        )
        if not path:
            return
        try:
            meta = load_project(path, self._canvas)
            self._canvas.set_zoom(1.0)
            # Sync status bar with restored canvas size
            bg = self._canvas._background
            self._status_bar.update_canvas_size(bg.width(), bg.height())
            self.setWindowTitle(f"PapaRaZ — {Path(path).name}")
            self._was_saved = False
        except Exception as exc:
            QMessageBox.critical(self, "Open Project Failed", str(exc))

    def closeEvent(self, event):
        if getattr(self, "_border_cursor_on", False):
            QApplication.restoreOverrideCursor()
            self._border_cursor_on = False
        # Stop recovery timer and clear recovery file
        self._recovery_timer.stop()
        from paparaz.core.recovery import clear_recovery
        clear_recovery(id(self))
        # Save window geometry and zoom level
        if self._settings_manager:
            g = self.geometry()
            self._settings_manager.settings.window_geometry = f"{g.x()},{g.y()},{g.width()},{g.height()}"
            if getattr(self._settings_manager.settings, 'default_zoom', 'fit') == 'remember':
                self._settings_manager.settings.last_zoom_level = self._canvas._zoom
        # Persist current tool's properties on close
        self._settings_save_timer.stop()
        if not self._canvas.selected_element:
            self._save_tool_properties(self._current_tool_type)
        if self._settings_manager:
            self._settings_manager.save()
        # Close the independent panels (parent=None so they outlive us otherwise)
        if hasattr(self, "_side_panel"):
            self._side_panel.hide()
            self._side_panel.deleteLater()
        if hasattr(self, "_layers_panel"):
            self._layers_panel.hide()
            self._layers_panel.deleteLater()
        self.closed.emit()
        super().closeEvent(event)
