"""Enhanced status bar with live info and detachable floating info window."""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QToolButton, QSizePolicy, QComboBox,
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QColor, QPainter, QPen


class StatusBar(QWidget):
    """Compact status bar showing mouse pos, selection size, canvas info, zoom."""

    detach_requested = Signal()
    zoom_requested = Signal(float)  # emitted when user picks a zoom level

    _ZOOM_PRESETS = ["25%", "50%", "75%", "100%", "125%", "150%", "200%", "300%", "400%", "Fit"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(22)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 0, 6, 0)
        lay.setSpacing(12)

        self._lbl_pos = QLabel("X:— Y:—")
        self._lbl_sel = QLabel("Sel: —")
        self._lbl_canvas = QLabel("Canvas: —")
        self._lbl_elems = QLabel("Elements: 0")

        # Editable zoom combo
        self._zoom_combo = QComboBox()
        self._zoom_combo.setEditable(True)
        self._zoom_combo.addItems(self._ZOOM_PRESETS)
        self._zoom_combo.setCurrentText("100%")
        self._zoom_combo.setFixedWidth(70)
        self._zoom_combo.setFixedHeight(18)
        self._zoom_combo.setStyleSheet(
            "QComboBox{color:rgba(255,255,255,200);background:#2a2a4e;"
            "border:1px solid #444;border-radius:3px;padding:0 4px;"
            "font-size:9px;font-family:'Segoe UI';}"
            "QComboBox::drop-down{border:none;width:12px;}"
            "QComboBox::down-arrow{image:none;}"
            "QComboBox QAbstractItemView{background:#1a1a2e;color:#ddd;"
            "border:1px solid #555;selection-background-color:#740096;}"
        )
        self._zoom_combo.lineEdit().returnPressed.connect(self._on_zoom_edited)
        self._zoom_combo.activated.connect(self._on_zoom_activated)

        font = QFont("Segoe UI", 9)
        style = "color: rgba(255,255,255,180); padding: 0; margin: 0;"
        for lbl in (self._lbl_pos, self._lbl_sel, self._lbl_canvas,
                    self._lbl_elems):
            lbl.setFont(font)
            lbl.setStyleSheet(style)
            lay.addWidget(lbl)

        lay.addWidget(self._zoom_combo)

        lay.addStretch()

        # Detach button
        self._detach_btn = QToolButton()
        self._detach_btn.setText("\u2197")  # ↗
        self._detach_btn.setToolTip("Detach to floating info window")
        self._detach_btn.setFixedSize(18, 18)
        self._detach_btn.setStyleSheet(
            "QToolButton{color:#aaa;background:transparent;border:none;font-size:12px;}"
            "QToolButton:hover{color:white;background:#555;border-radius:3px;}"
        )
        self._detach_btn.clicked.connect(self.detach_requested.emit)
        lay.addWidget(self._detach_btn)

    # ── Public update slots ─────────────────────────────────────────────────

    def update_mouse_pos(self, x: float, y: float):
        self._lbl_pos.setText(f"X:{x:.0f} Y:{y:.0f}")

    def update_selection(self, w: float, h: float):
        if w > 0 and h > 0:
            self._lbl_sel.setText(f"Sel: {w:.0f}\u00d7{h:.0f}")
        else:
            self._lbl_sel.setText("Sel: —")

    def update_canvas_size(self, w: int, h: int):
        self._lbl_canvas.setText(f"Canvas: {w}\u00d7{h}")

    def update_zoom(self, zoom: float):
        self._zoom_combo.blockSignals(True)
        self._zoom_combo.setCurrentText(f"{zoom * 100:.0f}%")
        self._zoom_combo.blockSignals(False)

    def _on_zoom_edited(self):
        """User typed a zoom value and pressed Enter."""
        text = self._zoom_combo.currentText().strip().rstrip("%").strip()
        try:
            val = float(text)
            if 10 <= val <= 1000:
                self.zoom_requested.emit(val / 100.0)
        except ValueError:
            pass

    def _on_zoom_activated(self, index: int):
        """User picked from the dropdown."""
        text = self._zoom_combo.itemText(index)
        if text == "Fit":
            self.zoom_requested.emit(-1.0)  # special value: fit to window
            return
        text = text.rstrip("%").strip()
        try:
            val = float(text)
            if 10 <= val <= 1000:
                self.zoom_requested.emit(val / 100.0)
        except ValueError:
            pass

    def update_element_count(self, count: int):
        self._lbl_elems.setText(f"Elements: {count}")

    def clear_mouse_pos(self):
        self._lbl_pos.setText("X:— Y:—")

    def clear_selection(self):
        self._lbl_sel.setText("Sel: —")


class InfoWindow(QWidget):
    """Floating detached info window — mirrors StatusBar data with comfortable text."""

    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PapaRaZ — Info")
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setMinimumSize(280, 160)
        self.resize(320, 180)

        self.setStyleSheet("background: #1a1a2e; border: 1px solid #3a3a4e; border-radius: 6px;")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(0)

        # Two columns
        self._left = QLabel()
        self._right = QLabel()
        font = QFont("Segoe UI", 12)
        style = "color: #ddd; padding: 0; margin: 0; line-height: 160%;"
        for lbl in (self._left, self._right):
            lbl.setFont(font)
            lbl.setStyleSheet(style)
            lbl.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            lay.addWidget(lbl)

        self._data = {
            "x": 0.0, "y": 0.0,
            "sel_w": 0.0, "sel_h": 0.0,
            "canvas_w": 0, "canvas_h": 0,
            "zoom": 1.0,
            "elems": 0,
        }
        self._refresh()

    def _refresh(self):
        d = self._data
        self._left.setText(
            f"Mouse X: {d['x']:.0f}\n"
            f"Mouse Y: {d['y']:.0f}\n"
            f"Canvas: {d['canvas_w']}\u00d7{d['canvas_h']}\n"
            f"Zoom: {d['zoom'] * 100:.0f}%"
        )
        sel = f"{d['sel_w']:.0f}\u00d7{d['sel_h']:.0f}" if d['sel_w'] > 0 else "—"
        self._right.setText(
            f"  Selection: {sel}\n"
            f"  Elements: {d['elems']}\n"
        )

    def update_mouse_pos(self, x: float, y: float):
        self._data["x"] = x
        self._data["y"] = y
        self._refresh()

    def update_selection(self, w: float, h: float):
        self._data["sel_w"] = w
        self._data["sel_h"] = h
        self._refresh()

    def update_canvas_size(self, w: int, h: int):
        self._data["canvas_w"] = w
        self._data["canvas_h"] = h
        self._refresh()

    def update_zoom(self, zoom: float):
        self._data["zoom"] = zoom
        self._refresh()

    def update_element_count(self, count: int):
        self._data["elems"] = count
        self._refresh()

    def clear_mouse_pos(self):
        self._data["x"] = 0
        self._data["y"] = 0
        self._refresh()

    def clear_selection(self):
        self._data["sel_w"] = 0
        self._data["sel_h"] = 0
        self._refresh()

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)
