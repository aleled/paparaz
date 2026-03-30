"""Frameless aero-style editor - canvas with floating toolbar, no window chrome."""

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QToolButton,
    QLabel, QFileDialog, QApplication, QMessageBox,
)
from PySide6.QtCore import Qt, Signal, QPoint, QRectF, QPointF, QEvent, QSize, QTimer
from PySide6.QtGui import QPixmap, QKeySequence, QShortcut, QPainter, QColor, QCursor

from paparaz.ui.icons import get_icon

from paparaz.ui.canvas import AnnotationCanvas
from paparaz.ui.toolbar import MultiEdgeToolbar
from paparaz.ui.side_panel import SidePanel
from paparaz.tools.base import ToolType
from paparaz.tools.select import SelectTool
from paparaz.tools.drawing import (
    PenTool, BrushTool, HighlightTool, LineTool, ArrowTool, RectangleTool, EllipseTool,
)
from paparaz.tools.special import (
    TextTool, NumberingTool, EraserTool, MasqueradeTool, FillTool, StampTool, CropTool, SliceTool,
)
from paparaz.core.export import save_png, save_jpg, save_svg, copy_to_clipboard
from paparaz.core.elements import (
    NumberElement, AnnotationElement, TextElement,
    RectElement, EllipseElement, MaskElement, NumberElement as NumElem, StampElement,
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
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(120, 80)

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

        # Track current tool type for per-tool property persistence
        self._current_tool_type = ToolType.SELECT

        # Debounced save timer: writes settings ~2s after the last property change
        self._settings_save_timer = QTimer(self)
        self._settings_save_timer.setSingleShot(True)
        self._settings_save_timer.setInterval(2000)
        self._settings_save_timer.timeout.connect(self._flush_tool_properties)

        # Always-visible pinned close button at top-right corner
        self._close_btn_overlay = QToolButton(self)
        self._close_btn_overlay.setIcon(get_icon("close", 14))
        self._close_btn_overlay.setIconSize(QSize(14, 14))
        self._close_btn_overlay.setFixedSize(26, 26)
        self._close_btn_overlay.setToolTip("Close (Esc)")
        self._close_btn_overlay.setStyleSheet(
            "QToolButton{background:#740096;border:none;border-radius:13px;padding:0;}"
            "QToolButton:hover{background:#c03fdd;}"
        )
        self._close_btn_overlay.clicked.connect(self._confirm_close)

        # Status label at bottom (minimal)
        self._status = QLabel("V:Select  P:Pen  B:Brush  H:Highlight  L:Line  A:Arrow  R:Rect  E:Ellipse  T:Text  N:Num  S:Stamp  X:Erase  M:Blur  C:Crop")
        self._status.setStyleSheet("color: rgba(255,255,255,100); font-size: 9px; padding: 2px;")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status)

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
            ToolType.LINE:      LineTool(self._canvas),
            ToolType.ARROW:     ArrowTool(self._canvas),
            ToolType.RECTANGLE: RectangleTool(self._canvas),
            ToolType.ELLIPSE:   EllipseTool(self._canvas),
            ToolType.TEXT:      self._text_tool,
            ToolType.NUMBERING: self._numbering_tool,
            ToolType.ERASER:    EraserTool(self._canvas),
            ToolType.MASQUERADE:self._masquerade_tool,
            ToolType.FILL:      FillTool(self._canvas),
            ToolType.STAMP:     self._stamp_tool,
            ToolType.CROP:      self._crop_tool,
            ToolType.SLICE:     self._slice_tool,
        }

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

        self._setup_shortcuts()
        self._on_tool_selected(ToolType.SELECT)
        NumberElement.reset_counter()

        # Apply saved app theme
        if self._settings_manager:
            self.apply_app_theme(self._settings_manager.settings.app_theme)

        # Auto-copy the raw capture to clipboard when the editor opens
        copy_to_clipboard(screenshot)

    def paintEvent(self, event):
        """Draw semi-transparent dark background behind canvas."""
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor(10, 10, 20, 220))
        p.setPen(QColor(116, 0, 150, 150))
        p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 8, 8)
        p.end()

    # --- Border resize cursor + drag: event filter installed on every child widget ---

    _EDGE_MARGIN = 8
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

    def eventFilter(self, obj, event):
        et = event.type()

        if et == QEvent.Type.MouseMove:
            gpos = QCursor.pos()
            edge = self._edge_at(gpos)
            # Use QApplication.mouseButtons() — more reliable than event.buttons()
            # which can lag after system resize / menu dismiss.
            if edge and not QApplication.mouseButtons():
                shape = self._CURSOR_MAP.get(edge, Qt.CursorShape.ArrowCursor)
                # Always restore+set instead of changeOverrideCursor:
                # changeOverrideCursor silently does nothing if the stack was
                # externally cleared (e.g. after a QMenu closes).
                if self._border_cursor_on:
                    QApplication.restoreOverrideCursor()
                QApplication.setOverrideCursor(shape)
                self._border_cursor_on = True
            elif self._border_cursor_on:
                QApplication.restoreOverrideCursor()
                self._border_cursor_on = False

        elif et == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            gpos = event.globalPosition().toPoint()
            edge = self._edge_at(gpos)
            if edge and obj is not getattr(self, "_close_btn_overlay", None):
                if self._border_cursor_on:
                    QApplication.restoreOverrideCursor()
                    self._border_cursor_on = False
                self.windowHandle().startSystemResize(edge)
                return True  # consume — don't pass to canvas/toolbar
            # Title-bar drag (no border)
            lpos = self.mapFromGlobal(gpos)
            if lpos.y() < 40:
                self._drag_pos = gpos - self.frameGeometry().topLeft()

        elif et == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = None

        elif et == QEvent.Type.MouseMove and event.buttons() & Qt.MouseButton.LeftButton:
            if self._drag_pos is not None:
                self.move(QCursor.pos() - self._drag_pos)

        return False  # never consume — only side-effects

    # --- Window drag fallback (when mouse is directly on EditorWindow, not a child) ---

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if event.position().y() < 40:
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = None
        super().mouseReleaseEvent(event)

    # --- Tool selection ---

    def _on_tool_selected(self, tool_type: ToolType):
        # Save departing tool's props before switching
        if hasattr(self, '_current_tool_type') and not self._canvas.selected_element:
            self._save_tool_properties(self._current_tool_type)
        tool = self._tools.get(tool_type)
        if tool:
            self._canvas.set_tool(tool)
            self._multi_toolbar.set_active_tool(tool_type)
            self._current_tool_type = tool_type
            if not self._canvas.selected_element:
                self._side_panel.update_for_tool(tool_type)
                self._load_tool_properties(tool_type)

    # --- Element selection -> side panel ---

    def _on_element_selected(self, element):
        self._side_panel.on_element_selected(element)

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
        if "font_size" in props:        c._font_size = int(props["font_size"])
        # Sync panel UI without firing signals
        self._side_panel.apply_properties_silent(props)

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
        # Place the floating side panel near the canvas on first show (screen coords)
        if not self._panel_initially_placed:
            self._panel_initially_placed = True
            canvas_global = self._canvas.mapToGlobal(QPoint(0, 0))
            self._side_panel.move(canvas_global.x() + 4, canvas_global.y() + 4)

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
        # Apply background color to editor root
        bg = theme["bg1"]
        self.setStyleSheet(f"QWidget#editorRoot {{ background: {bg}; }}")

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
            "L": ToolType.LINE,      "A": ToolType.ARROW,
            "R": ToolType.RECTANGLE, "E": ToolType.ELLIPSE,
            "T": ToolType.TEXT,      "N": ToolType.NUMBERING,
            "X": ToolType.ERASER,    "M": ToolType.MASQUERADE,
            "S": ToolType.STAMP,     "C": ToolType.CROP,
            "F": ToolType.FILL,      "Z": ToolType.SLICE,
        }
        for key, tt in tool_keys.items():
            sc(key, lambda _tt=tt: self._on_tool_selected(_tt))

        # Wire text-tool editing state changes → enable/disable all shortcuts
        self._text_tool.on_editing_changed = self._on_text_editing_changed

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

    def _confirm_close(self):
        if not self._canvas.elements and not self._canvas._preview_element:
            self.close()
            return
        msg = QMessageBox(self)
        msg.setWindowTitle("Close Editor")
        msg.setText("Close the editor?")
        msg.setInformativeText("Unsaved annotations will be lost.")
        msg.setStyleSheet("QMessageBox{background:#1a1a2e;color:#ddd;} QLabel{color:#ddd;}")

        copy_btn   = msg.addButton("Copy to clipboard & Exit", QMessageBox.ButtonRole.AcceptRole)
        exit_btn   = msg.addButton("Exit",            QMessageBox.ButtonRole.DestructiveRole)
        cancel_btn = msg.addButton("Cancel",          QMessageBox.ButtonRole.RejectRole)
        msg.setDefaultButton(cancel_btn)
        msg.exec()

        clicked = msg.clickedButton()
        if clicked is copy_btn:
            copy_to_clipboard(self._canvas.render_to_pixmap())
            self.close()
        elif clicked is exit_btn:
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

        path = Path(path)
        ext = path.suffix.lower()

        if ext == ".svg":
            save_svg(self._canvas._background, str(path), self._canvas.paint_annotations)
        elif ext in (".jpg", ".jpeg"):
            save_jpg(pix, str(path), jpg_q)
        else:
            save_png(pix, str(path))

        # Increment persistent counter
        if s:
            s.save_counter = counter + 1
            sm.add_recent(str(path))   # also saves settings

        self.file_saved.emit(str(path))

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
        if getattr(self, "_border_cursor_on", False):
            QApplication.restoreOverrideCursor()
            self._border_cursor_on = False
        # Persist current tool's properties on close
        self._settings_save_timer.stop()
        if not self._canvas.selected_element:
            self._save_tool_properties(self._current_tool_type)
        if self._settings_manager:
            self._settings_manager.save()
        # Close the independent side panel (parent=None so it outlives us otherwise)
        if hasattr(self, "_side_panel"):
            self._side_panel.hide()
            self._side_panel.deleteLater()
        self.closed.emit()
        super().closeEvent(event)
