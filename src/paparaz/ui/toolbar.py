"""Flameshot-style toolbar - compact circular buttons with overflow menu."""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QToolButton, QButtonGroup,
    QGraphicsDropShadowEffect, QMenu,
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QColor

from paparaz.tools.base import ToolType
from paparaz.ui.icons import get_icon

UI_COLOR = "#740096"
UI_COLOR_ACTIVE = "#270032"
BTN = 32          # Button diameter (compact)
ICON = 18         # Icon size
GAP = 6           # Gap between buttons

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


class FlameshotToolbar(QWidget):
    """Compact circular-button toolbar with overflow for small windows."""

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

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(GAP)

        self._tool_group = QButtonGroup(self)
        self._tool_group.setExclusive(True)
        self._tool_buttons: dict[ToolType, QToolButton] = {}
        self._all_buttons: list[QToolButton] = []

        # Tool buttons
        for tool_type, icon_name, tooltip in TOOL_DEFS:
            btn = self._make_btn(icon_name, tooltip, True)
            self._tool_group.addButton(btn)
            self._tool_buttons[tool_type] = btn
            layout.addWidget(btn)
            self._all_buttons.append(btn)
            btn.clicked.connect(lambda checked, tt=tool_type: self.tool_selected.emit(tt))

        self._tool_buttons[ToolType.SELECT].setChecked(True)

        layout.addSpacing(GAP)

        # Action buttons
        action_signals = {
            "undo": self.undo_requested, "redo": self.redo_requested,
            "save": self.save_requested, "copy": self.copy_requested,
            "paste": self.paste_requested, "pin": self.pin_requested,
            "bring_front": self.bring_front_requested,
            "send_back": self.send_back_requested,
            "close": self.close_requested,
        }
        self._action_btns: list[tuple[QToolButton, str, str]] = []
        for icon_name, tooltip in ACTION_DEFS:
            btn = self._make_btn(icon_name, tooltip, False)
            layout.addWidget(btn)
            self._all_buttons.append(btn)
            self._action_btns.append((btn, icon_name, tooltip))
            sig = action_signals.get(icon_name)
            if sig:
                btn.clicked.connect(sig.emit)

        # Overflow "..." button (hidden by default, shown when too narrow)
        self._overflow_btn = QToolButton()
        self._overflow_btn.setText("\u22ef")
        self._overflow_btn.setFixedSize(BTN, BTN)
        self._overflow_btn.setStyleSheet(OVERFLOW_STYLE)
        self._overflow_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._overflow_btn.hide()
        layout.addWidget(self._overflow_btn)

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

    def resizeEvent(self, event):
        """Hide action buttons that don't fit and put them in overflow menu."""
        super().resizeEvent(event)
        avail = self.width() - 8  # margins
        # Tool buttons always visible (they have keyboard shortcuts as fallback)
        tool_width = len(TOOL_DEFS) * (BTN + GAP) + GAP  # tools + separator
        remaining = avail - tool_width - BTN - GAP  # reserve space for overflow btn

        overflow_items = []
        for btn, icon_name, tooltip in self._action_btns:
            needed = BTN + GAP
            if remaining >= needed:
                btn.show()
                remaining -= needed
            else:
                btn.hide()
                overflow_items.append((icon_name, tooltip))

        if overflow_items:
            self._overflow_btn.show()
            menu = QMenu(self)
            menu.setStyleSheet(MENU_STYLE)

            action_signals = {
                "undo": self.undo_requested, "redo": self.redo_requested,
                "save": self.save_requested, "copy": self.copy_requested,
                "paste": self.paste_requested, "pin": self.pin_requested,
                "bring_front": self.bring_front_requested,
                "send_back": self.send_back_requested,
                "close": self.close_requested,
            }
            for icon_name, tooltip in overflow_items:
                act = menu.addAction(get_icon(icon_name, 16), tooltip)
                sig = action_signals.get(icon_name)
                if sig:
                    act.triggered.connect(sig.emit)

            self._overflow_btn.setMenu(menu)
        else:
            self._overflow_btn.hide()
