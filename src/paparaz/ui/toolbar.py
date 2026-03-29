"""Flameshot-style toolbar - adaptive flow layout, wraps to multiple rows."""

from PySide6.QtWidgets import (
    QWidget, QToolButton, QButtonGroup,
    QGraphicsDropShadowEffect, QMenu, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QColor

from paparaz.tools.base import ToolType
from paparaz.ui.icons import get_icon

UI_COLOR = "#740096"
UI_COLOR_ACTIVE = "#270032"
BTN = 32          # Button diameter
ICON = 18         # Icon size
GAP = 6           # Gap between buttons
MARGIN = 4        # Widget margin
SEP = GAP * 2     # Extra gap between tool group and action group

TOOL_DEFS = [
    (ToolType.SELECT, "select", "Select (V)"),
    (ToolType.PEN, "pen", "Pen (P)"),
    (ToolType.BRUSH, "brush", "Brush (B)"),
    (ToolType.LINE, "line", "Line (L)"),
    (ToolType.ARROW, "arrow", "Arrow (A)"),
    (ToolType.RECTANGLE, "rectangle", "Rect (R)"),
    (ToolType.ELLIPSE, "ellipse", "Ellipse (E)"),
    (ToolType.TEXT, "text", "Text (T)"),
    (ToolType.NUMBERING, "number", "Number (N)"),
    (ToolType.ERASER, "eraser", "Eraser (X)"),
    (ToolType.MASQUERADE, "blur", "Blur (M)"),
    (ToolType.FILL, "fill", "Fill (F)"),
    (ToolType.STAMP, "star", "Stamp (S)"),
]

ACTION_DEFS = [
    ("undo", "Undo (Ctrl+Z)"),
    ("redo", "Redo (Ctrl+Y)"),
    ("save", "Save (Ctrl+S)"),
    ("copy", "Copy (Ctrl+C)"),
    ("paste", "Paste (Ctrl+V)"),
    ("pin", "Pin (Ctrl+P)"),
    ("bring_front", "Front (Ctrl+])"),
    ("send_back", "Back (Ctrl+[)"),
    ("close", "Close (Esc)"),
]

N_TOOLS = len(TOOL_DEFS)
N_ACTIONS = len(ACTION_DEFS)

BTN_STYLE = f"""
QToolButton {{
    background-color: {UI_COLOR}; border: none;
    border-radius: {BTN // 2}px; padding: 0;
    min-width: {BTN}px; min-height: {BTN}px;
    max-width: {BTN}px; max-height: {BTN}px;
}}
QToolButton:hover {{ background-color: #9e2ac0; }}
QToolButton:checked {{ background-color: {UI_COLOR_ACTIVE}; }}
"""

OVERFLOW_STYLE = f"""
QToolButton {{
    background-color: #444; border: none;
    border-radius: {BTN // 2}px; padding: 0;
    min-width: {BTN}px; min-height: {BTN}px;
    max-width: {BTN}px; max-height: {BTN}px;
    color: white; font-weight: bold; font-size: 16px;
}}
QToolButton:hover {{ background-color: #666; }}
QToolButton::menu-indicator {{ width: 0; height: 0; }}
"""

MENU_STYLE = """
QMenu { background: #2a2a3e; color: #ddd; border: 1px solid #444; padding: 4px; }
QMenu::item { padding: 4px 16px; border-radius: 3px; }
QMenu::item:selected { background: #740096; }
QMenu::separator { background: #444; height: 1px; margin: 2px 8px; }
"""


def _compute_flow(avail_w: int, n_tools: int, n_actions: int) -> tuple[int, list[tuple[int, int]]]:
    """Compute row-wrapping positions for tool + action buttons.

    Returns (num_rows, positions) where positions is a flat list of (x, y)
    for each button in order: tool buttons first, then action buttons.
    An extra SEP gap is inserted between the two groups.
    """
    positions: list[tuple[int, int]] = []
    x = 0
    y = 0
    rows = 1
    total = n_tools + n_actions

    for i in range(total):
        # Insert separator gap between tool group and action group
        if i == n_tools and n_actions > 0:
            if x + SEP + BTN > avail_w and x > 0:
                # Separator causes overflow — start new row instead
                x = 0
                y += BTN + GAP
                rows += 1
            else:
                x += SEP

        # Wrap if this button won't fit
        if x + BTN > avail_w and x > 0:
            x = 0
            y += BTN + GAP
            rows += 1

        positions.append((x, y))
        x += BTN + GAP

    return rows, positions


class FlameshotToolbar(QWidget):
    """Compact circular-button toolbar that wraps to additional rows when narrow."""

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

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self._tool_group = QButtonGroup(self)
        self._tool_group.setExclusive(True)
        self._tool_buttons: dict[ToolType, QToolButton] = {}
        self._tool_btn_list: list[QToolButton] = []
        self._action_btn_list: list[tuple[QToolButton, str]] = []
        self._prev_h = -1

        for tool_type, icon_name, tooltip in TOOL_DEFS:
            btn = self._make_btn(icon_name, tooltip, True)
            btn.setParent(self)
            self._tool_group.addButton(btn)
            self._tool_buttons[tool_type] = btn
            self._tool_btn_list.append(btn)
            btn.clicked.connect(lambda checked, tt=tool_type: self.tool_selected.emit(tt))

        self._tool_buttons[ToolType.SELECT].setChecked(True)

        self._action_signals = {
            "undo": self.undo_requested, "redo": self.redo_requested,
            "save": self.save_requested, "copy": self.copy_requested,
            "paste": self.paste_requested, "pin": self.pin_requested,
            "bring_front": self.bring_front_requested,
            "send_back": self.send_back_requested,
            "close": self.close_requested,
        }
        for icon_name, tooltip in ACTION_DEFS:
            btn = self._make_btn(icon_name, tooltip, False)
            btn.setParent(self)
            self._action_btn_list.append((btn, icon_name))
            sig = self._action_signals.get(icon_name)
            if sig:
                btn.clicked.connect(sig.emit)

        self._overflow_btn = QToolButton(self)
        self._overflow_btn.setText("\u22ef")
        self._overflow_btn.setFixedSize(BTN, BTN)
        self._overflow_btn.setStyleSheet(OVERFLOW_STYLE)
        self._overflow_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._overflow_btn.hide()

    def _make_btn(self, icon_name: str, tooltip: str, checkable: bool) -> QToolButton:
        btn = QToolButton()
        btn.setIcon(get_icon(icon_name, ICON))
        btn.setIconSize(QSize(ICON, ICON))
        btn.setToolTip(tooltip)
        btn.setCheckable(checkable)
        btn.setFixedSize(BTN, BTN)
        btn.setStyleSheet(BTN_STYLE)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(4)
        shadow.setOffset(0, 0)
        shadow.setColor(QColor(0, 0, 0, 150))
        btn.setGraphicsEffect(shadow)
        return btn

    def set_active_tool(self, tool_type: ToolType):
        btn = self._tool_buttons.get(tool_type)
        if btn:
            btn.setChecked(True)

    # --- Size hints for height-for-width layout ---

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        avail = width - 2 * MARGIN
        if avail <= 0:
            return BTN + 2 * MARGIN
        n_vis_actions = self._n_visible_actions(avail)
        rows, _ = _compute_flow(avail, N_TOOLS, n_vis_actions)
        return rows * BTN + max(0, rows - 1) * GAP + 2 * MARGIN

    def sizeHint(self) -> QSize:
        # Ideal: single row with all buttons
        ideal_w = (N_TOOLS * (BTN + GAP) + SEP + N_ACTIONS * (BTN + GAP) - GAP
                   + 2 * MARGIN)
        return QSize(ideal_w, BTN + 2 * MARGIN)

    def minimumSizeHint(self) -> QSize:
        # Min: just fit all tool buttons in one row
        min_w = N_TOOLS * (BTN + GAP) - GAP + 2 * MARGIN
        return QSize(min_w, BTN + 2 * MARGIN)

    def _n_visible_actions(self, avail_w: int) -> int:
        """How many action buttons we can show (rest go to overflow)."""
        # We show all unless it would exceed 3 rows
        rows, _ = _compute_flow(avail_w, N_TOOLS, N_ACTIONS)
        if rows <= 3:
            return N_ACTIONS
        # Reduce actions until ≤3 rows (keep at least 0)
        for n in range(N_ACTIONS - 1, -1, -1):
            rows, _ = _compute_flow(avail_w, N_TOOLS, n)
            if rows <= 3:
                return n
        return 0

    # --- Layout ---

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._layout_buttons()

    def showEvent(self, event):
        super().showEvent(event)
        self._layout_buttons()

    def _layout_buttons(self):
        avail_w = self.width() - 2 * MARGIN
        if avail_w <= 0:
            return

        n_vis = self._n_visible_actions(avail_w)
        overflow_actions = self._action_btn_list[n_vis:]
        visible_actions = self._action_btn_list[:n_vis]

        _, positions = _compute_flow(avail_w, N_TOOLS, n_vis)
        all_visible = self._tool_btn_list + [b for b, _ in visible_actions]

        for i, btn in enumerate(all_visible):
            x, y = positions[i]
            btn.setGeometry(MARGIN + x, MARGIN + y, BTN, BTN)
            btn.show()

        # Hidden overflow action buttons
        for btn, _ in overflow_actions:
            btn.hide()

        if overflow_actions:
            # Place overflow button right after last visible button
            if positions:
                lx, ly = positions[-1]
                ox = lx + BTN + GAP + SEP
                if ox + BTN > avail_w:
                    ox = 0
                    ly += BTN + GAP
                self._overflow_btn.setGeometry(MARGIN + ox, MARGIN + ly, BTN, BTN)
            self._overflow_btn.show()
            menu = QMenu(self)
            menu.setStyleSheet(MENU_STYLE)
            for btn, icon_name in overflow_actions:
                act = menu.addAction(get_icon(icon_name, 16), btn.toolTip())
                sig = self._action_signals.get(icon_name)
                if sig:
                    act.triggered.connect(sig.emit)
            self._overflow_btn.setMenu(menu)
        else:
            self._overflow_btn.hide()

        # Adjust widget height without triggering infinite resize loop
        new_h = self.heightForWidth(self.width())
        if self._prev_h != new_h:
            self._prev_h = new_h
            self.setFixedHeight(new_h)
            self.updateGeometry()
