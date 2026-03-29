"""Dialog for resizing the annotation canvas."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QSpinBox, QDoubleSpinBox, QPushButton, QToolButton, QDialogButtonBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon

from paparaz.ui.icons import get_icon


DIALOG_STYLE = """
QDialog { background: #1a1a2e; color: #ddd; }
QLabel  { color: #ddd; }
QSpinBox, QDoubleSpinBox {
    background: #2a2a3e; color: #ddd; border: 1px solid #555;
    border-radius: 4px; padding: 2px 6px; min-width: 70px;
}
QPushButton {
    background: #740096; color: white; border: none;
    border-radius: 4px; padding: 6px 18px;
}
QPushButton:hover { background: #9e2ac0; }
QPushButton[flat="true"] { background: transparent; color: #aaa; }
QPushButton[flat="true"]:hover { background: #333; }
QToolButton {
    background: #2a2a3e; border: 1px solid #555; border-radius: 4px;
    padding: 2px; min-width: 24px; min-height: 24px;
    max-width: 24px; max-height: 24px;
}
QToolButton:hover { background: #3a3a4e; }
QToolButton:checked { background: #740096; border-color: #740096; }
"""


class CanvasResizeDialog(QDialog):
    """Dialog to set canvas width and height, with % mode and aspect ratio lock."""

    def __init__(self, current_w: int, current_h: int, parent=None):
        super().__init__(parent)
        self._orig_w = current_w
        self._orig_h = current_h
        self._aspect_locked = True
        self._updating = False  # guard against recursive signal loops

        self.setWindowTitle("Resize Canvas")
        self.setStyleSheet(DIALOG_STYLE)
        self.setWindowFlags(
            self.windowFlags() | Qt.WindowType.FramelessWindowHint
        )
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        # Title
        title = QLabel("Resize Canvas")
        title.setStyleSheet("font-size: 12px; font-weight: bold; color: #fff;")
        layout.addWidget(title)

        # Mode toggle row
        mode_row = QHBoxLayout()
        self._px_btn = QPushButton("px")
        self._pct_btn = QPushButton("%")
        for btn in (self._px_btn, self._pct_btn):
            btn.setCheckable(True)
            btn.setFixedWidth(40)
            btn.setStyleSheet(
                "QPushButton{background:#2a2a3e;color:#aaa;border:1px solid #555;"
                "border-radius:4px;padding:3px 8px;}"
                "QPushButton:checked{background:#740096;color:#fff;border-color:#740096;}"
                "QPushButton:hover:!checked{background:#3a3a4e;}"
            )
        self._px_btn.setChecked(True)
        self._px_btn.clicked.connect(lambda: self._set_mode("px"))
        self._pct_btn.clicked.connect(lambda: self._set_mode("pct"))
        mode_row.addWidget(QLabel("Unit:"))
        mode_row.addWidget(self._px_btn)
        mode_row.addWidget(self._pct_btn)
        mode_row.addStretch()
        layout.addLayout(mode_row)

        # Width row
        w_row = QHBoxLayout()
        w_row.addWidget(QLabel("Width:"))
        self._w_spin = QSpinBox()
        self._w_spin.setRange(1, 32000)
        self._w_spin.setValue(current_w)
        self._w_pct_spin = QDoubleSpinBox()
        self._w_pct_spin.setRange(1.0, 10000.0)
        self._w_pct_spin.setDecimals(1)
        self._w_pct_spin.setSuffix(" %")
        self._w_pct_spin.setValue(100.0)
        self._w_pct_spin.hide()
        w_row.addWidget(self._w_spin)
        w_row.addWidget(self._w_pct_spin)
        self._w_unit_label = QLabel("px")
        w_row.addWidget(self._w_unit_label)

        # Lock button between W and H
        self._lock_btn = QToolButton()
        self._lock_btn.setCheckable(True)
        self._lock_btn.setChecked(True)
        self._lock_btn.setToolTip("Lock aspect ratio")
        self._lock_btn.setIcon(get_icon("link", 14))
        self._lock_btn.toggled.connect(self._on_lock_toggled)
        w_row.addWidget(self._lock_btn)
        layout.addLayout(w_row)

        # Height row
        h_row = QHBoxLayout()
        h_row.addWidget(QLabel("Height:"))
        self._h_spin = QSpinBox()
        self._h_spin.setRange(1, 32000)
        self._h_spin.setValue(current_h)
        self._h_pct_spin = QDoubleSpinBox()
        self._h_pct_spin.setRange(1.0, 10000.0)
        self._h_pct_spin.setDecimals(1)
        self._h_pct_spin.setSuffix(" %")
        self._h_pct_spin.setValue(100.0)
        self._h_pct_spin.hide()
        h_row.addWidget(self._h_spin)
        h_row.addWidget(self._h_pct_spin)
        self._h_unit_label = QLabel("px")
        h_row.addWidget(self._h_unit_label)
        h_row.addSpacing(24 + 2)  # align with lock btn space in w_row
        layout.addLayout(h_row)

        # Current size info
        self._info_label = QLabel(f"Current: {current_w} × {current_h} px")
        self._info_label.setStyleSheet("color: #666; font-size: 9px;")
        layout.addWidget(self._info_label)

        # Buttons
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        # Connect value change signals
        self._w_spin.valueChanged.connect(self._on_w_px_changed)
        self._h_spin.valueChanged.connect(self._on_h_px_changed)
        self._w_pct_spin.valueChanged.connect(self._on_w_pct_changed)
        self._h_pct_spin.valueChanged.connect(self._on_h_pct_changed)

    # --- Mode ---

    def _set_mode(self, mode: str):
        is_pct = mode == "pct"
        self._px_btn.setChecked(not is_pct)
        self._pct_btn.setChecked(is_pct)

        if is_pct:
            # Sync current px values to pct before switching
            self._updating = True
            self._w_pct_spin.setValue(self._w_spin.value() / self._orig_w * 100.0)
            self._h_pct_spin.setValue(self._h_spin.value() / self._orig_h * 100.0)
            self._updating = False

        self._w_spin.setVisible(not is_pct)
        self._h_spin.setVisible(not is_pct)
        self._w_pct_spin.setVisible(is_pct)
        self._h_pct_spin.setVisible(is_pct)
        unit_text = "%" if is_pct else "px"
        self._w_unit_label.setText(unit_text)
        self._h_unit_label.setText(unit_text)

    # --- Aspect lock ---

    def _on_lock_toggled(self, locked: bool):
        self._aspect_locked = locked
        self._lock_btn.setIcon(get_icon("link" if locked else "unlink", 14))

    # --- Value change handlers ---

    def _on_w_px_changed(self, val: int):
        if self._updating or not self._aspect_locked or self._orig_w == 0:
            return
        self._updating = True
        new_h = max(1, round(val * self._orig_h / self._orig_w))
        self._h_spin.setValue(new_h)
        self._updating = False

    def _on_h_px_changed(self, val: int):
        if self._updating or not self._aspect_locked or self._orig_h == 0:
            return
        self._updating = True
        new_w = max(1, round(val * self._orig_w / self._orig_h))
        self._w_spin.setValue(new_w)
        self._updating = False

    def _on_w_pct_changed(self, val: float):
        if self._updating or not self._aspect_locked:
            return
        self._updating = True
        self._h_pct_spin.setValue(val)
        # Keep px spinboxes in sync
        self._w_spin.setValue(max(1, round(self._orig_w * val / 100.0)))
        self._h_spin.setValue(max(1, round(self._orig_h * val / 100.0)))
        self._updating = False

    def _on_h_pct_changed(self, val: float):
        if self._updating or not self._aspect_locked:
            return
        self._updating = True
        self._w_pct_spin.setValue(val)
        self._w_spin.setValue(max(1, round(self._orig_w * val / 100.0)))
        self._h_spin.setValue(max(1, round(self._orig_h * val / 100.0)))
        self._updating = False

    # --- Result ---

    def get_size(self) -> tuple[int, int]:
        """Return (width, height) in pixels chosen by the user."""
        if self._pct_btn.isChecked():
            w = max(1, round(self._orig_w * self._w_pct_spin.value() / 100.0))
            h = max(1, round(self._orig_h * self._h_pct_spin.value() / 100.0))
            return w, h
        return self._w_spin.value(), self._h_spin.value()
