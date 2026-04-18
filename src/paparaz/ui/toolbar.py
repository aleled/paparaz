"""Multi-edge toolbar: top strip (horizontal), right strip (vertical), bottom strip (horizontal).

All 22 buttons (13 tool + 9 action) are distributed across these strips based on available space.
The MultiEdgeToolbar itself is a plain manager object (not a QWidget). The three ToolStrip
widgets are placed directly in the EditorWindow layout.
"""

from PySide6.QtWidgets import (
    QWidget, QToolButton, QButtonGroup,
    QMenu, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QSize, QObject, QPoint
from PySide6.QtGui import QColor, QPainter

from paparaz.tools.base import ToolType
from paparaz.ui.icons import get_icon

UI_COLOR = "#740096"
UI_COLOR_ACTIVE = "#270032"
BTN = 32          # Button diameter
ICON = 24         # Icon size (matches SVG viewBox for crisp render)
GAP = 6           # Gap between buttons
MARGIN = 4        # Widget margin
SEP = GAP * 2     # Extra gap between tool group and action group

# Current theme colors — updated by apply_theme(); used when building new buttons
_THEME_ACCENT        = UI_COLOR
_THEME_ACCENT_HOVER  = "#9e2ac0"
_THEME_ACCENT_PRESS  = UI_COLOR_ACTIVE
_THEME_BG3           = "#3a3a4e"


def _btn_qss() -> str:
    """Generate button QSS from current theme colors."""
    return (
        f"QToolButton{{"
        f"background:transparent;border:none;"
        f"border-radius:{BTN // 2}px;padding:0;"
        f"min-width:{BTN}px;min-height:{BTN}px;"
        f"max-width:{BTN}px;max-height:{BTN}px;}}"
        f"QToolButton:hover{{background:{_THEME_ACCENT_HOVER};}}"
        f"QToolButton:checked{{background:{_THEME_ACCENT};}}"
        f"QToolButton:pressed{{background:{_THEME_ACCENT_PRESS};}}"
    )


def _overflow_qss() -> str:
    return (
        f"QToolButton{{"
        f"background:{_THEME_BG3};border:none;"
        f"border-radius:{BTN // 2}px;padding:0;"
        f"min-width:{BTN}px;min-height:{BTN}px;"
        f"max-width:{BTN}px;max-height:{BTN}px;"
        f"color:white;font-weight:bold;font-size:16px;}}"
        f"QToolButton:hover{{background:{_THEME_ACCENT_HOVER};}}"
        f"QToolButton::menu-indicator{{width:0;height:0;}}"
    )

TOOL_DEFS = [
    (ToolType.SELECT,    "select",    "Select (V)"),
    (ToolType.PEN,       "pen",       "Pen (P)"),
    (ToolType.BRUSH,     "brush",     "Brush (B)"),
    (ToolType.HIGHLIGHT, "highlight", "Highlight (H)"),
    (ToolType.LINE,         "line",         "Line (L)"),
    (ToolType.ARROW,        "arrow",        "Arrow (A)"),
    (ToolType.CURVED_ARROW, "curved_arrow", "Curved Arrow (Q)"),
    (ToolType.RECTANGLE,    "rectangle",    "Rect (R)"),
    (ToolType.ELLIPSE,   "ellipse",   "Ellipse (E)"),
    (ToolType.TEXT,      "text",      "Text (T)"),
    (ToolType.NUMBERING, "number",    "Number (N)"),
    (ToolType.ERASER,    "eraser",    "Eraser (X)"),
    (ToolType.MASQUERADE,"blur",      "Blur (M)"),
    (ToolType.FILL,      "fill",      "Fill (F)"),
    (ToolType.STAMP,     "star",      "Stamp (S)"),
    (ToolType.CROP,        "crop",        "Crop (C)"),
    (ToolType.SLICE,       "slice",       "Slice (Z)"),
    (ToolType.EYEDROPPER,  "eyedropper",  "Eyedropper (I)"),
    (ToolType.MAGNIFIER,   "magnifier",   "Magnifier (G)"),
    (ToolType.MEASURE,     "measure",     "Measure (D)"),
]

ACTION_DEFS = [
    ("undo",          "Undo (Ctrl+Z)"),
    ("redo",          "Redo (Ctrl+Y)"),
    ("save",          "Save (Ctrl+S)"),
    ("copy",          "Copy (Ctrl+C)"),
    ("paste",         "Paste (Ctrl+V)"),
    ("pin",           "Pin (Ctrl+P)"),
    ("bring_front",   "Front (Ctrl+])"),
    ("send_back",     "Back (Ctrl+[)"),
    ("resize_canvas", "Resize Canvas"),
    ("layers",        "Layers Panel"),
    ("palette",       "Theme Presets"),
    ("settings",      "Settings"),
]

N_TOOLS  = len(TOOL_DEFS)
N_ACTIONS = len(ACTION_DEFS)
N_TOTAL  = N_TOOLS + N_ACTIONS

# BTN_STYLE / OVERFLOW_STYLE are now generated via _btn_qss() / _overflow_qss()
# to allow dynamic theming — see apply_theme() on MultiEdgeToolbar.

MENU_STYLE = """
QMenu {
    background-color: #1a1a2e;
    color: #ddd;
    border: 1px solid #555;
    padding: 4px;
}
QMenu::item {
    padding: 4px 16px;
    border-radius: 3px;
    background-color: transparent;
}
QMenu::item:selected {
    background-color: #740096;
    color: white;
}
QMenu::separator {
    background-color: #444;
    height: 1px;
    margin: 2px 8px;
}
"""


# Tools that have configurable properties (show 3-dot indicator)
_TOOLS_WITH_PROPS = {
    ToolType.PEN, ToolType.BRUSH, ToolType.HIGHLIGHT, ToolType.LINE, ToolType.ARROW,
    ToolType.RECTANGLE, ToolType.ELLIPSE, ToolType.TEXT,
    ToolType.NUMBERING, ToolType.MASQUERADE, ToolType.FILL, ToolType.STAMP,
}


class _ToolBtn(QToolButton):
    """QToolButton with an optional 3-dot indicator for tools that have properties."""

    def __init__(self, has_props: bool = False, parent=None):
        super().__init__(parent)
        self._has_props = has_props

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._has_props:
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setBrush(QColor(255, 255, 255, 180))
            p.setPen(Qt.PenStyle.NoPen)
            cx = self.width() // 2
            y = self.height() - 6
            for dx in (-4, 0, 4):
                p.drawEllipse(cx + dx - 1, y - 1, 3, 3)
            p.end()


class ToolStrip(QWidget):
    """Horizontal or vertical strip that holds a subset of buttons.

    Buttons are placed manually with setGeometry.
    Fixed height (horizontal) or fixed width (vertical) = BTN + 2*MARGIN.
    """

    STRIP_SIZE = BTN + 2 * MARGIN  # thickness of the strip

    def __init__(self, orientation: Qt.Orientation, parent=None):
        super().__init__(parent)
        self._orientation = orientation
        self._buttons: list[QToolButton] = []
        self._sep_local_idx: int = -1
        self._overflow_btn: QToolButton | None = None

        self.setStyleSheet("background: transparent;")
        self.setAttribute(Qt.WidgetAttribute.WA_AlwaysShowToolTips, True)
        if orientation == Qt.Orientation.Horizontal:
            self.setFixedHeight(self.STRIP_SIZE)
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        else:
            self.setFixedWidth(self.STRIP_SIZE)
            self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

    def set_buttons(self, buttons: list, sep_local_idx: int = -1,
                    overflow_btn: QToolButton | None = None):
        """Assign buttons to this strip and re-layout."""
        # Hide all current buttons first
        for b in self._buttons:
            b.hide()
        self._buttons = buttons
        self._sep_local_idx = sep_local_idx
        self._overflow_btn = overflow_btn
        self._layout_buttons()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._layout_buttons()

    def showEvent(self, event):
        super().showEvent(event)
        self._layout_buttons()

    def _layout_buttons(self):
        if not self._buttons:
            if self._overflow_btn:
                self._overflow_btn.hide()
            return

        horiz = self._orientation == Qt.Orientation.Horizontal

        if horiz:
            pos = MARGIN
            for i, btn in enumerate(self._buttons):
                if i == self._sep_local_idx:
                    pos += SEP
                btn.setGeometry(pos, MARGIN, BTN, BTN)
                btn.show()
                pos += BTN + GAP
            # Place overflow button at end if present
            if self._overflow_btn:
                pos += SEP
                self._overflow_btn.setGeometry(pos, MARGIN, BTN, BTN)
                self._overflow_btn.show()
            else:
                pass  # already hidden by caller
        else:
            pos = MARGIN
            for i, btn in enumerate(self._buttons):
                if i == self._sep_local_idx:
                    pos += SEP
                btn.setGeometry(MARGIN, pos, BTN, BTN)
                btn.show()
                pos += BTN + GAP


class MultiEdgeToolbar(QObject):
    """Manages button creation and distribution across top/right/bottom strips.

    This is NOT a QWidget - it is a plain manager. The three ToolStrip widgets
    are placed directly in the EditorWindow layout.
    """

    tool_selected = Signal(ToolType)
    undo_requested = Signal()
    redo_requested = Signal()
    save_requested = Signal()
    copy_requested = Signal()
    paste_requested = Signal()
    pin_requested = Signal()
    bring_front_requested = Signal()
    send_back_requested = Signal()
    close_requested = Signal()
    resize_canvas_requested = Signal()
    crop_requested = Signal()
    theme_preset_requested = Signal()
    settings_requested = Signal()
    layers_requested = Signal()
    tool_props_requested = Signal(ToolType, QPoint)

    def __init__(self, parent=None):
        super().__init__(parent)

        # The three strips - parent will add them to its layout
        self.top_strip = ToolStrip(Qt.Orientation.Horizontal)
        self.right_strip = ToolStrip(Qt.Orientation.Vertical)
        self.bottom_strip = ToolStrip(Qt.Orientation.Horizontal)

        self.right_strip.hide()
        self.bottom_strip.hide()

        # Build button list: tool buttons first, then action buttons
        self._tool_group = QButtonGroup(self)
        self._tool_group.setExclusive(True)
        self._tool_buttons: dict[ToolType, QToolButton] = {}
        self._buttons: list[QToolButton] = []

        # Action signal mapping
        self._action_signals: dict[str, Signal] = {}

        self._build_buttons()

        # Overflow button attached to top strip
        self._overflow_btn = QToolButton(self.top_strip)
        self._overflow_btn.setText("\u22ef")
        self._overflow_btn.setFixedSize(BTN, BTN)
        self._overflow_btn.setStyleSheet(_overflow_qss())
        self._overflow_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._overflow_btn.hide()

        self._overflow_menu = QMenu(self.top_strip)
        self._overflow_menu.setStyleSheet(MENU_STYLE)

    def _build_buttons(self):
        """Create all tool and action buttons."""
        # --- Tool buttons ---
        for tool_type, icon_name, tooltip in TOOL_DEFS:
            btn = self._make_btn(icon_name, tooltip, checkable=True,
                                 parent_strip=self.top_strip, tool_type=tool_type)
            self._tool_group.addButton(btn)
            self._tool_buttons[tool_type] = btn
            self._buttons.append(btn)
            btn.clicked.connect(lambda checked, tt=tool_type: self.tool_selected.emit(tt))
            # Right-click quick props
            btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            btn.customContextMenuRequested.connect(
                lambda pos, b=btn, tt=tool_type: self._show_quick_props(b, tt)
            )

        self._tool_buttons[ToolType.SELECT].setChecked(True)

        # Map action key -> signal
        self._action_signals = {
            "undo":          self.undo_requested,
            "redo":          self.redo_requested,
            "save":          self.save_requested,
            "copy":          self.copy_requested,
            "paste":         self.paste_requested,
            "pin":           self.pin_requested,
            "bring_front":   self.bring_front_requested,
            "send_back":     self.send_back_requested,
            "resize_canvas": self.resize_canvas_requested,
            "layers":        self.layers_requested,
            "close":         self.close_requested,
            "theme_preset":  self.theme_preset_requested,
            "settings":      self.settings_requested,
        }

        # --- Action buttons ---
        # ACTION_DEFS has (icon_name, tooltip). We need to match by position to signal.
        action_signal_keys = [
            "undo", "redo", "save", "copy", "paste",
            "pin", "bring_front", "send_back", "resize_canvas", "layers",
            "theme_preset", "settings",
        ]
        for (icon_name, tooltip), sig_key in zip(ACTION_DEFS, action_signal_keys):
            btn = self._make_btn(icon_name, tooltip, checkable=False,
                                 parent_strip=self.top_strip)
            self._buttons.append(btn)
            sig = self._action_signals.get(sig_key)
            if sig:
                btn.clicked.connect(sig.emit)

    def _make_btn(self, icon_name: str, tooltip: str, checkable: bool,
                  parent_strip: ToolStrip, tool_type: ToolType | None = None) -> QToolButton:
        has_props = tool_type in _TOOLS_WITH_PROPS if tool_type is not None else False
        btn = _ToolBtn(has_props=has_props, parent=parent_strip) if checkable else QToolButton(parent_strip)
        btn.setIcon(get_icon(icon_name, ICON))
        btn.setIconSize(QSize(ICON, ICON))
        btn.setToolTip(tooltip)
        btn.setCheckable(checkable)
        btn.setFixedSize(BTN, BTN)
        btn.setStyleSheet(_btn_qss())
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        # WA_AlwaysShowToolTips ensures tooltips show on frameless windows
        btn.setAttribute(Qt.WidgetAttribute.WA_AlwaysShowToolTips, True)
        btn.hide()
        return btn

    def _show_quick_props(self, btn: QToolButton, tool_type: ToolType):
        """Emit signal so editor can show the floating properties panel."""
        if tool_type in _TOOLS_WITH_PROPS:
            # Position: to the right of the button (or below if horizontal strip)
            global_pos = btn.mapToGlobal(QPoint(btn.width() + 4, 0))
            self.tool_props_requested.emit(tool_type, global_pos)

    def set_active_tool(self, tool_type: ToolType):
        btn = self._tool_buttons.get(tool_type)
        if btn:
            btn.setChecked(True)

    def apply_theme(self, theme: dict):
        """Re-style all buttons with theme colors."""
        global _THEME_ACCENT, _THEME_ACCENT_HOVER, _THEME_ACCENT_PRESS, _THEME_BG3
        _THEME_ACCENT       = theme.get("accent",         "#740096")
        _THEME_ACCENT_HOVER = theme.get("accent_hover",   "#9e2ac0")
        _THEME_ACCENT_PRESS = theme.get("accent_pressed", "#270032")
        _THEME_BG3          = theme.get("bg3",            "#3a3a4e")
        btn_qss  = _btn_qss()
        over_qss = _overflow_qss()
        for btn in self._buttons:
            btn.setStyleSheet(btn_qss)
        self._overflow_btn.setStyleSheet(over_qss)

    # -----------------------------------------------------------------------
    # Layout / distribution
    # -----------------------------------------------------------------------

    def relayout(self, editor_w: int, editor_h: int, side_panel_w: int):
        """Distribute buttons across strips based on available space."""
        cell = BTN + GAP
        # Reserve space for the always-visible overlay close button (26px + 6px margin + gap)
        CLOSE_BTN_RESERVE = BTN + MARGIN  # ~40px on the right
        top_avail = editor_w - side_panel_w - 2 * MARGIN - CLOSE_BTN_RESERVE

        if top_avail <= 0:
            return

        n_top_only = max(0, (top_avail + GAP) // cell)

        if n_top_only >= N_TOTAL:
            # All buttons fit in the top strip — no overflow button needed
            self._distribute(N_TOTAL, 0, 0)
            self.right_strip.hide()
            self.bottom_strip.hide()
            return

        # When overflow is needed, reserve extra space for the "…" button itself
        OVERFLOW_RESERVE = BTN + SEP  # 32 + 12 = 44px
        top_avail_with_overflow = max(0, top_avail - OVERFLOW_RESERVE)

        right_strip_w = BTN + 3 * MARGIN
        n_top_r = max(0, (top_avail_with_overflow - right_strip_w + GAP) // cell)

        # Body height estimate: editor_h minus (top strip) minus (status bar ~24) minus margins ~12
        body_h = editor_h - (BTN + 2 * MARGIN) - 24 - 12
        n_right = max(0, (body_h - 2 * MARGIN + GAP) // cell)

        if n_top_r + n_right >= N_TOTAL:
            # Top + right is enough
            self._distribute(n_top_r, N_TOTAL - n_top_r, 0)
            self.right_strip.show()
            self.bottom_strip.hide()
            return

        # Need bottom strip as well
        body_h_adj = body_h - BTN - 3 * MARGIN
        n_right_adj = max(0, (body_h_adj + GAP) // cell)
        n_bottom = max(0, (top_avail_with_overflow - right_strip_w + GAP) // cell)
        n_top_b = n_top_r  # same width as top when right visible

        self._distribute(n_top_b, n_right_adj, n_bottom)
        self.right_strip.show()
        self.bottom_strip.show()

    def _distribute(self, n_top: int, n_right: int, n_bottom: int):
        """Slice self._buttons into three groups and assign to strips."""
        total = N_TOTAL

        # Clamp so we don't exceed button count
        n_top = min(n_top, total)
        n_right = min(n_right, total - n_top)
        n_bottom_actual = total - n_top - n_right
        # If n_bottom was specified as 0 and there are leftovers, they go to overflow
        if n_bottom == 0:
            overflow = self._buttons[n_top + n_right:]
            n_bottom_actual = 0
        else:
            overflow = self._buttons[n_top + n_right + n_bottom_actual:]
            n_bottom_actual = min(n_bottom, total - n_top - n_right)

        top_btns = self._buttons[:n_top]
        right_btns = self._buttons[n_top:n_top + n_right]
        bottom_btns = self._buttons[n_top + n_right:n_top + n_right + n_bottom_actual]
        overflow_btns = self._buttons[n_top + n_right + n_bottom_actual:]

        # Calculate separator indices for each strip
        def sep_idx(start: int, count: int) -> int:
            end = start + count
            if start < N_TOOLS <= end:
                return N_TOOLS - start
            return -1

        # Reparent buttons to the correct strip if needed
        for btn in top_btns:
            btn.setParent(self.top_strip)
        for btn in right_btns:
            btn.setParent(self.right_strip)
        for btn in bottom_btns:
            btn.setParent(self.bottom_strip)

        # Hide all overflow buttons (they go to the overflow menu)
        for btn in overflow_btns:
            btn.hide()

        # Rebuild overflow menu
        self._overflow_menu.clear()
        if overflow_btns:
            for i, btn in enumerate(overflow_btns):
                act = self._overflow_menu.addAction(btn.icon(), btn.toolTip())
                # Re-connect: we need to fire the button's signal
                # We do it by connecting to clicked on the hidden button
                act.triggered.connect(btn.click)
            self._overflow_btn.setMenu(self._overflow_menu)
        else:
            self._overflow_btn.setMenu(None)

        # Assign to strips
        self.top_strip.set_buttons(
            top_btns,
            sep_idx(0, n_top),
            self._overflow_btn if overflow_btns else None,
        )
        self.right_strip.set_buttons(
            right_btns,
            sep_idx(n_top, n_right),
        )
        self.bottom_strip.set_buttons(
            bottom_btns,
            sep_idx(n_top + n_right, n_bottom_actual),
        )

        # Hide overflow btn if no overflow
        if not overflow_btns:
            self._overflow_btn.hide()

        # Show/hide right and bottom strips based on content
        if not right_btns:
            self.right_strip.hide()
        if not bottom_btns:
            self.bottom_strip.hide()
