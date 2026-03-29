"""Flameshot-style floating toolbar with circular icon buttons."""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QToolButton, QButtonGroup,
    QFrame, QGraphicsDropShadowEffect, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QSize, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QFont

from paparaz.tools.base import ToolType
from paparaz.ui.icons import get_icon

# Flameshot design constants
UI_COLOR = "#740096"           # Default purple
UI_COLOR_ACTIVE = "#270032"    # Dark contrast (active tool)
BUTTON_SIZE = 40               # Circular button diameter
ICON_SIZE = 24                 # 60% of button
BUTTON_GAP = 10                # buttonSize / 4
SHADOW_BLUR = 5

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
]

ACTION_DEFS = [
    ("undo", "Undo (Ctrl+Z)"),
    ("redo", "Redo (Ctrl+Y)"),
    ("save", "Save (Ctrl+S)"),
    ("copy", "Copy to clipboard (Ctrl+C)"),
    ("paste", "Paste (Ctrl+V)"),
    ("pin", "Pin to screen (Ctrl+P)"),
    ("bring_front", "Bring to front (Ctrl+])"),
    ("send_back", "Send to back (Ctrl+[)"),
    ("close", "Close (Esc)"),
]


def _make_circle_btn_style(bg_color: str) -> str:
    radius = BUTTON_SIZE // 2
    return f"""
        QToolButton {{
            background-color: {bg_color};
            border: none;
            border-radius: {radius}px;
            padding: 0px;
            min-width: {BUTTON_SIZE}px;
            min-height: {BUTTON_SIZE}px;
            max-width: {BUTTON_SIZE}px;
            max-height: {BUTTON_SIZE}px;
        }}
        QToolButton:hover {{
            background-color: {_lighten(bg_color, 30)};
        }}
        QToolButton:checked {{
            background-color: {UI_COLOR_ACTIVE};
        }}
    """


def _lighten(hex_color: str, amount: int) -> str:
    c = QColor(hex_color)
    r = min(255, c.red() + amount)
    g = min(255, c.green() + amount)
    b = min(255, c.blue() + amount)
    return QColor(r, g, b).name()


class FlameshotToolbar(QWidget):
    """Circular-button toolbar matching Flameshot's visual design."""

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
        self.setObjectName("flameshot_toolbar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            QWidget#flameshot_toolbar {{
                background: transparent;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(BUTTON_GAP)

        # Tool buttons
        self._tool_group = QButtonGroup(self)
        self._tool_group.setExclusive(True)
        self._tool_buttons: dict[ToolType, QToolButton] = {}

        for tool_type, icon_name, tooltip in TOOL_DEFS:
            btn = self._make_tool_button(icon_name, tooltip, checkable=True)
            self._tool_group.addButton(btn)
            self._tool_buttons[tool_type] = btn
            layout.addWidget(btn)
            btn.clicked.connect(lambda checked, tt=tool_type: self.tool_selected.emit(tt))

        self._tool_buttons[ToolType.SELECT].setChecked(True)

        # Separator
        layout.addSpacing(BUTTON_GAP)

        # Action buttons
        action_signals = {
            "undo": self.undo_requested,
            "redo": self.redo_requested,
            "save": self.save_requested,
            "copy": self.copy_requested,
            "paste": self.paste_requested,
            "pin": self.pin_requested,
            "bring_front": self.bring_front_requested,
            "send_back": self.send_back_requested,
            "close": self.close_requested,
        }
        for icon_name, tooltip in ACTION_DEFS:
            btn = self._make_tool_button(icon_name, tooltip, checkable=False)
            layout.addWidget(btn)
            sig = action_signals.get(icon_name)
            if sig:
                btn.clicked.connect(sig.emit)

    def _make_tool_button(self, icon_name: str, tooltip: str, checkable: bool) -> QToolButton:
        btn = QToolButton()
        btn.setIcon(get_icon(icon_name, ICON_SIZE))
        btn.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        btn.setToolTip(tooltip)
        btn.setCheckable(checkable)
        btn.setFixedSize(BUTTON_SIZE, BUTTON_SIZE)
        btn.setStyleSheet(_make_circle_btn_style(UI_COLOR))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)

        # Drop shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(SHADOW_BLUR)
        shadow.setOffset(0, 0)
        shadow.setColor(QColor(0, 0, 0, 180))
        btn.setGraphicsEffect(shadow)

        return btn

    def set_active_tool(self, tool_type: ToolType):
        btn = self._tool_buttons.get(tool_type)
        if btn:
            btn.setChecked(True)
