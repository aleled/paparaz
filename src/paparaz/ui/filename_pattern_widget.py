"""FilenamePatternWidget — reusable widget for configuring the save filename pattern.

Shows:
  • Preset dropdown
  • Pattern text field (editable)
  • Live preview label  (updates on every keystroke)
  • Token picker buttons grouped by category
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QComboBox, QPushButton, QToolButton,
    QFrame, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont

from paparaz.core.filename_pattern import TOKENS, PRESETS, preview as fp_preview


_STYLE = """
QWidget#fnWidget { background: transparent; }

QLabel#fnSectionLbl {
    color: #666; font-size: 10px; font-weight: bold;
    text-transform: uppercase; padding: 0; margin: 0;
}
QLabel#fnPreviewLbl {
    color: #888; font-size: 11px; font-style: italic;
    padding: 2px 0; background: transparent;
}
QLabel#fnPreviewVal {
    color: #c080ff; font-size: 12px; font-family: Consolas, monospace;
    background: #111120; border: 1px solid #3a2a5e;
    border-radius: 3px; padding: 5px 8px;
}
QLineEdit#fnPatternEdit {
    background: #111120; color: #e0e0ff;
    border: 1px solid #3a3a5e; border-radius: 3px;
    padding: 4px 8px; font-size: 12px;
    font-family: Consolas, monospace;
    selection-background-color: #740096;
}
QLineEdit#fnPatternEdit:focus { border-color: #740096; }
QComboBox#fnPresetCombo {
    background: #1e1e34; color: #ccc;
    border: 1px solid #3a3a5e; border-radius: 3px;
    padding: 3px 8px; font-size: 11px; min-height: 24px;
}
QComboBox#fnPresetCombo QAbstractItemView {
    background: #1e1e34; color: #ccc;
    selection-background-color: #740096; font-size: 11px;
}
QPushButton#fnTokenBtn {
    background: #1e1e34; color: #9090c0;
    border: 1px solid #2a2a4e; border-radius: 3px;
    padding: 2px 6px; font-size: 10px; font-family: Consolas, monospace;
    min-height: 20px;
}
QPushButton#fnTokenBtn:hover {
    background: #2a1040; color: #c0c0ff; border-color: #740096;
}
QPushButton#fnTokenBtn:pressed { background: #740096; color: #fff; }
"""


class FilenamePatternWidget(QWidget):
    """Self-contained filename pattern editor."""

    pattern_changed = Signal(str)   # emits the current pattern on any change

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("fnWidget")
        self.setStyleSheet(_STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        # ── Preset row ───────────────────────────────────────────────────────
        preset_row = QHBoxLayout()
        preset_row.setSpacing(6)
        lbl = QLabel("Preset:")
        lbl.setObjectName("fnSectionLbl")
        lbl.setFixedWidth(46)
        preset_row.addWidget(lbl)

        self._preset_combo = QComboBox()
        self._preset_combo.setObjectName("fnPresetCombo")
        self._preset_combo.setMaximumWidth(240)
        for p in PRESETS:
            self._preset_combo.addItem(p["label"], p["pattern"])
        preset_row.addWidget(self._preset_combo)
        preset_row.addStretch()
        root.addLayout(preset_row)

        # ── Pattern input ────────────────────────────────────────────────────
        pat_lbl = QLabel("Pattern:")
        pat_lbl.setObjectName("fnSectionLbl")
        root.addWidget(pat_lbl)

        self._pattern_edit = QLineEdit()
        self._pattern_edit.setObjectName("fnPatternEdit")
        self._pattern_edit.setPlaceholderText("{yyyy}-{MM}-{dd}_{HH}-{mm}-{ss}")
        root.addWidget(self._pattern_edit)

        # ── Live preview ─────────────────────────────────────────────────────
        prev_lbl = QLabel("Preview (example):")
        prev_lbl.setObjectName("fnPreviewLbl")
        root.addWidget(prev_lbl)

        self._preview_val = QLabel("—")
        self._preview_val.setObjectName("fnPreviewVal")
        self._preview_val.setWordWrap(True)
        root.addWidget(self._preview_val)

        # ── Token pickers ────────────────────────────────────────────────────
        tok_lbl = QLabel("Insert token:")
        tok_lbl.setObjectName("fnSectionLbl")
        root.addWidget(tok_lbl)

        # Group tokens by category
        cats: dict[str, list[dict]] = {}
        for t in TOKENS:
            cats.setdefault(t["cat"], []).append(t)

        for cat, items in cats.items():
            row = QHBoxLayout()
            row.setSpacing(4)
            row.setContentsMargins(0, 0, 0, 0)

            cat_lbl = QLabel(f"{cat}:")
            cat_lbl.setObjectName("fnSectionLbl")
            cat_lbl.setFixedWidth(52)
            row.addWidget(cat_lbl)

            for item in items:
                btn = QPushButton(item["token"])
                btn.setObjectName("fnTokenBtn")
                btn.setToolTip(item["desc"])
                btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
                btn.clicked.connect(lambda _, tok=item["token"]: self._insert_token(tok))
                row.addWidget(btn)

            row.addStretch()
            root.addLayout(row)

        # ── Wire up signals ──────────────────────────────────────────────────
        self._preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        self._pattern_edit.textChanged.connect(self._on_pattern_changed)

        # Debounce preview refresh (don't call preview() on every keystroke)
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(250)
        self._preview_timer.timeout.connect(self._refresh_preview)

    # ── Public API ───────────────────────────────────────────────────────────

    def set_pattern(self, pattern: str):
        """Load a pattern from settings without triggering preset selection."""
        self._pattern_edit.blockSignals(True)
        self._pattern_edit.setText(pattern)
        self._pattern_edit.blockSignals(False)
        self._update_preset_combo(pattern)
        self._refresh_preview()

    def set_extension(self, ext: str):
        """Set the file extension shown in the preview (e.g. 'png', 'jpg')."""
        self._ext = f".{ext.lstrip('.')}" if ext else ".png"
        self._refresh_preview()

    def get_pattern(self) -> str:
        return self._pattern_edit.text().strip()

    # ── Internal ─────────────────────────────────────────────────────────────

    def _insert_token(self, token: str):
        """Insert token at cursor position in the pattern field."""
        edit = self._pattern_edit
        pos = edit.cursorPosition()
        text = edit.text()
        edit.setText(text[:pos] + token + text[pos:])
        edit.setCursorPosition(pos + len(token))
        edit.setFocus()

    def _on_preset_changed(self, idx: int):
        pattern = self._preset_combo.itemData(idx)
        if pattern is None or pattern == "":
            return
        self._pattern_edit.blockSignals(True)
        self._pattern_edit.setText(pattern)
        self._pattern_edit.blockSignals(False)
        self._refresh_preview()
        self.pattern_changed.emit(pattern)

    def _on_pattern_changed(self, text: str):
        self._update_preset_combo(text)
        self._preview_timer.start()
        self.pattern_changed.emit(text)

    def _update_preset_combo(self, pattern: str):
        """Highlight matching preset or select 'Custom'."""
        self._preset_combo.blockSignals(True)
        for i in range(self._preset_combo.count()):
            if self._preset_combo.itemData(i) == pattern:
                self._preset_combo.setCurrentIndex(i)
                self._preset_combo.blockSignals(False)
                return
        # Select the "Custom" item (last)
        self._preset_combo.setCurrentIndex(self._preset_combo.count() - 1)
        self._preset_combo.blockSignals(False)

    def _refresh_preview(self):
        pat = self._pattern_edit.text().strip()
        if not pat:
            self._preview_val.setText("—")
            return
        try:
            sample = fp_preview(pat)
            ext = getattr(self, '_ext', '.png')
            self._preview_val.setText(f"{sample}{ext}")
        except Exception as e:
            self._preview_val.setText(f"Error: {e}")
