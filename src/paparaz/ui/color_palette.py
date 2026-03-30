"""RecentColorsPalette — compact swatch bar of recently used colors.

Left-click  → apply as foreground color
Right-click → apply as background color

Usage:
    palette = RecentColorsPalette(colors=["#FF0000", "#00FF00"])
    palette.fg_requested.connect(my_fg_slot)
    palette.bg_requested.connect(my_bg_slot)
    palette.add_color("#0000FF")
    colors = palette.get_colors()   # for persistence
"""

from __future__ import annotations

from PySide6.QtWidgets import QWidget, QHBoxLayout, QToolButton, QSizePolicy, QMenu
from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtGui import QPixmap, QColor, QPainter, QIcon, QAction

MAX_RECENT = 16
SWATCH_SIZE = 18       # px, each swatch square
SWATCH_BORDER = 1

_EMPTY_COLOR = "#2a2a3e"


def _make_swatch(color_str: str, size: int = SWATCH_SIZE) -> QIcon:
    pix = QPixmap(size, size)
    p = QPainter(pix)
    # Checkerboard for transparent / semi-transparent colors
    cs = 4
    light, dark = QColor(170, 170, 170), QColor(100, 100, 100)
    for row in range(0, size, cs):
        for col in range(0, size, cs):
            p.fillRect(col, row, cs, cs, light if (row // cs + col // cs) % 2 == 0 else dark)
    c = QColor(color_str)
    p.fillRect(0, 0, size, size, c)
    # Border
    p.setPen(QColor(60, 60, 80))
    p.drawRect(0, 0, size - 1, size - 1)
    p.end()
    return QIcon(pix)


class _SwatchBtn(QToolButton):
    """Single color swatch button."""

    left_clicked  = Signal(str)
    right_clicked = Signal(str)

    def __init__(self, color: str = _EMPTY_COLOR, parent=None):
        super().__init__(parent)
        self._color = color
        self.setFixedSize(SWATCH_SIZE, SWATCH_SIZE)
        self.setIconSize(QSize(SWATCH_SIZE - 2, SWATCH_SIZE - 2))
        self.setStyleSheet(
            "QToolButton { border: none; padding: 0; margin: 0; background: transparent; }"
            "QToolButton:hover { border: 1px solid #740096; }"
        )
        self._refresh()

    def set_color(self, color: str):
        self._color = color
        self._refresh()

    def get_color(self) -> str:
        return self._color

    def _refresh(self):
        self.setIcon(_make_swatch(self._color))
        self.setToolTip(f"Fg: click  ·  Bg: right-click\n{self._color}")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.left_clicked.emit(self._color)
        elif event.button() == Qt.MouseButton.RightButton:
            self.right_clicked.emit(self._color)
        # Don't call super — suppress default toggle behaviour


class RecentColorsPalette(QWidget):
    """Horizontal bar of recently used color swatches."""

    fg_requested = Signal(str)   # left-click: set as foreground
    bg_requested = Signal(str)   # right-click: set as background
    changed      = Signal()      # emitted when color list changes (for persistence)

    def __init__(self, colors: list[str] | None = None, parent=None):
        super().__init__(parent)
        self._colors: list[str] = []

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self._btns: list[_SwatchBtn] = []
        for _ in range(MAX_RECENT):
            btn = _SwatchBtn(_EMPTY_COLOR, self)
            btn.left_clicked.connect(self.fg_requested)
            btn.right_clicked.connect(self.bg_requested)
            btn.setVisible(False)
            layout.addWidget(btn)
            self._btns.append(btn)

        layout.addStretch()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(SWATCH_SIZE + 4)

        if colors:
            for c in reversed(colors):
                self.add_color(c, emit=False)

    # ── Public API ───────────────────────────────────────────────────────────

    def add_color(self, color: str, emit: bool = True):
        """Prepend *color* to the palette, deduplicating and capping at MAX_RECENT."""
        color = color.strip().lower()
        if not color or not color.startswith("#"):
            return
        if color in self._colors:
            self._colors.remove(color)
        self._colors.insert(0, color)
        self._colors = self._colors[:MAX_RECENT]
        self._sync_buttons()
        if emit:
            self.changed.emit()

    def get_colors(self) -> list[str]:
        return list(self._colors)

    def set_colors(self, colors: list[str]):
        self._colors = [c.strip().lower() for c in colors if c][:MAX_RECENT]
        self._sync_buttons()

    # ── Internal ─────────────────────────────────────────────────────────────

    def _sync_buttons(self):
        for i, btn in enumerate(self._btns):
            if i < len(self._colors):
                btn.set_color(self._colors[i])
                btn.setVisible(True)
            else:
                btn.setVisible(False)
