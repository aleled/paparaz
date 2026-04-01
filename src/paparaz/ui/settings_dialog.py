"""Settings dialog — clean form-based design with consistent sizing."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QWidget, QLabel, QLineEdit, QSpinBox, QDoubleSpinBox,
    QComboBox, QPushButton, QFileDialog,
    QColorDialog, QScrollArea, QFrame,
    QListWidget, QListWidgetItem, QStackedWidget, QSizePolicy,
    QToolButton, QSlider, QFontComboBox, QButtonGroup, QRadioButton,
    QCheckBox,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QFont, QIcon, QPixmap, QPainter, QPen, QBrush, QDesktopServices
from PySide6.QtCore import QUrl

from paparaz.core.settings import SettingsManager
from paparaz.ui.icons import combo_arrow_css
from paparaz.ui.app_theme import APP_THEMES, get_theme, build_dialog_qss

# ---------------------------------------------------------------------------
# Stylesheet
# ---------------------------------------------------------------------------

_BASE = """
QDialog { background: #0e0e18; color: #ccc; font-size: 12px; }

/* ── Sidebar ──────────────────────────────────────────────────────────── */
QListWidget {
    background: #111120; border: none;
    border-right: 1px solid #1e1e34; outline: 0;
    font-size: 12px;
}
QListWidget::item {
    padding: 7px 14px; border-radius: 0; color: #777;
    border-left: 3px solid transparent;
}
QListWidget::item:selected {
    background: #1a0f2a; color: #d0a0ff;
    border-left: 3px solid #9b30c8;
}
QListWidget::item:hover:!selected {
    background: #151528; color: #aaa;
}

/* ── Content area ─────────────────────────────────────────────────────── */
QScrollArea { border: none; background: transparent; }
QWidget#page { background: transparent; }

/* ── Section cards ────────────────────────────────────────────────────── */
QFrame#sectionCard {
    background: #12121e; border: 1px solid #1e1e34;
    border-radius: 6px; padding: 0;
}

/* ── Form labels (left column in QFormLayout) ─────────────────────────── */
QLabel { color: #aaa; font-size: 11px; }
QLabel#heading    { color: #eee; font-size: 14px; font-weight: bold; }
QLabel#sub        { color: #555; font-size: 10px; }
QLabel#sectionHdr { color: #666; font-size: 9px; font-weight: bold; letter-spacing: 1px;
                    padding: 4px 10px 3px 10px; }
QLabel#version    { color: #8822bb; font-size: 12px; font-weight: bold; }
QLabel#keyBadge   { color: #999; background: #181830; border: 1px solid #282848;
                    border-radius: 3px; padding: 1px 5px; font-size: 10px; }

/* ── Inputs — all same height/radius for consistency ──────────────────── */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QFontComboBox {
    background: #181830; color: #ddd; border: 1px solid #282848;
    border-radius: 4px; padding: 4px 8px;
    min-height: 24px; max-height: 24px; font-size: 11px;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border-color: #7722aa;
}
QComboBox { min-width: 60px; }
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background: #181830; color: #ccc; selection-background-color: #7722aa;
    font-size: 11px; border: 1px solid #282848;
}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    background: #222240; border: none; border-radius: 2px; width: 14px;
}

/* ── Sliders ──────────────────────────────────────────────────────────── */
QSlider::groove:horizontal {
    height: 3px; background: #282848; border-radius: 1px;
}
QSlider::handle:horizontal {
    background: #8822bb; width: 12px; height: 12px;
    margin: -5px 0; border-radius: 6px;
}
QSlider::handle:horizontal:hover { background: #aa44dd; }
QSlider::sub-page:horizontal { background: #8822bb; border-radius: 1px; }

/* ── Checkboxes — standard with themed colors ─────────────────────────── */
QCheckBox { color: #aaa; font-size: 11px; spacing: 8px; }
QCheckBox:hover { color: #ddd; }
QCheckBox::indicator {
    width: 14px; height: 14px; border-radius: 3px;
    background: #181830; border: 1px solid #383858;
}
QCheckBox::indicator:hover { border-color: #7722aa; }
QCheckBox::indicator:checked {
    background: #7722aa; border-color: #9944cc;
    image: url(%%CHECKMARK%%);
}

/* ── Radio buttons ────────────────────────────────────────────────────── */
QRadioButton { color: #aaa; font-size: 11px; spacing: 6px; }
QRadioButton:hover { color: #ddd; }
QRadioButton::indicator {
    width: 13px; height: 13px; border-radius: 7px;
    background: #181830; border: 1px solid #383858;
}
QRadioButton::indicator:checked {
    background: #7722aa; border-color: #9944cc;
}

/* ── Buttons ──────────────────────────────────────────────────────────── */
QPushButton {
    background: #7722aa; color: white; border: none;
    border-radius: 4px; padding: 5px 14px; font-weight: 600; font-size: 11px;
}
QPushButton:hover   { background: #9944cc; }
QPushButton:pressed { background: #5a0074; }

QPushButton#flat {
    background: transparent; color: #888; border: 1px solid #282848;
    padding: 4px 10px; font-weight: 400;
}
QPushButton#flat:hover { background: #1e1e34; color: #ccc; }

QPushButton#danger {
    background: transparent; color: #bb4444; border: 1px solid #441515;
    padding: 4px 10px; font-weight: 400; border-radius: 4px; font-size: 11px;
}
QPushButton#danger:hover { background: #1e0808; color: #ff6666; }

QPushButton#colorBtn {
    min-width: 28px; max-width: 28px; min-height: 22px; max-height: 22px;
    border: 1px solid #383858; border-radius: 3px; padding: 0;
}
QPushButton#colorBtn:hover { border-color: #7722aa; }

QToolButton#themeCard {
    background: #12121e; border: 2px solid #1e1e34;
    border-radius: 6px; padding: 4px 4px 2px 4px; color: #999;
    font-size: 9px; font-weight: 600;
    min-width: 80px; max-width: 100px; min-height: 52px;
}
QToolButton#themeCard:checked { border-color: #7722aa; background: #1a0f2a; color: #d0a0ff; }
QToolButton#themeCard:hover:!checked { border-color: #444466; }

QPushButton#iconBtn {
    background: #181830; border: 2px solid #282848;
    border-radius: 5px; padding: 2px;
}
QPushButton#iconBtn:checked { border-color: #7722aa; background: #1a0f2a; }
QPushButton#iconBtn:hover   { border-color: #7722aa; }

/* ── Bottom bar ───────────────────────────────────────────────────────── */
QFrame#bottomBar { background: #0b0b14; border-top: 1px solid #1e1e34; }

/* ── Separator ────────────────────────────────────────────────────────── */
QFrame#sep { background: #1e1e34; max-height: 1px; margin: 0 10px; }

/* ── QFormLayout alignment ────────────────────────────────────────────── */
QFormLayout { }
"""

# Standard widget widths
_W_SPIN     = 70   # spinboxes
_W_COMBO_SM = 80   # tiny combos (format: png/jpg/svg)
_W_COMBO    = 140  # short combos (panel mode, zoom, key)
_W_COMBO_LG = 240  # longer combos (stamp, preset, font)


def _checkmark_path() -> str:
    """Generate a small white checkmark PNG in the temp dir and return its path."""
    import tempfile, os
    path = os.path.join(tempfile.gettempdir(), "paparaz_check.png")
    if not os.path.exists(path):
        pix = QPixmap(14, 14)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor("#ffffff"))
        pen.setWidth(2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.drawLine(3, 7, 6, 10)
        p.drawLine(6, 10, 11, 4)
        p.end()
        pix.save(path, "PNG")
    return path.replace("\\", "/")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sep() -> QFrame:
    f = QFrame()
    f.setObjectName("sep")
    f.setFrameShape(QFrame.Shape.HLine)
    f.setFixedHeight(1)
    return f


def _scroll(inner: QWidget) -> QScrollArea:
    sa = QScrollArea()
    sa.setWidgetResizable(True)
    sa.setWidget(inner)
    sa.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    sa.setStyleSheet(
        "QScrollArea{border:none;background:transparent;}"
        "QScrollBar:vertical{background:#0e0e18;width:5px;margin:0;}"
        "QScrollBar::handle:vertical{background:#333;border-radius:2px;min-height:20px;}"
        "QScrollBar::handle:vertical:hover{background:#555;}"
        "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}"
    )
    return sa


def _page() -> tuple[QWidget, QVBoxLayout]:
    w = QWidget()
    w.setObjectName("page")
    v = QVBoxLayout(w)
    v.setContentsMargins(16, 12, 16, 12)
    v.setSpacing(0)
    return w, v


def _section(title: str) -> tuple[QFrame, QFormLayout]:
    """Card section with a header and a QFormLayout for consistent label:widget alignment."""
    card = QFrame()
    card.setObjectName("sectionCard")
    outer = QVBoxLayout(card)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(0)

    hdr = QLabel(title.upper())
    hdr.setObjectName("sectionHdr")
    outer.addWidget(hdr)

    form = QFormLayout()
    form.setContentsMargins(12, 4, 12, 10)
    form.setSpacing(6)
    form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
    outer.addLayout(form)
    return card, form


def _section_vbox(title: str) -> tuple[QFrame, QVBoxLayout]:
    """Card section with a VBox layout (for non-form content like theme cards)."""
    card = QFrame()
    card.setObjectName("sectionCard")
    outer = QVBoxLayout(card)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(0)

    hdr = QLabel(title.upper())
    hdr.setObjectName("sectionHdr")
    outer.addWidget(hdr)

    content = QVBoxLayout()
    content.setContentsMargins(12, 4, 12, 10)
    content.setSpacing(6)
    outer.addLayout(content)
    return card, content


def _toggle(label: str, checked: bool = False, tooltip: str = "") -> QCheckBox:
    cb = QCheckBox(label)
    cb.setChecked(checked)
    if tooltip:
        cb.setToolTip(tooltip)
    return cb


def _color_swatch(color: str) -> QPixmap:
    pix = QPixmap(18, 18)
    pix.fill(QColor(color))
    return pix


def _make_theme_swatch(tdata: dict) -> QIcon:
    pix = QPixmap(72, 24)
    p = QPainter(pix)
    band = 24
    for i, c in enumerate([tdata["bg1"], tdata["accent"], tdata["fg"]]):
        p.fillRect(i * band, 0, band, 24, QColor(c))
    p.end()
    return QIcon(pix)


def _make_spin(lo: int, hi: int, val: int, suffix: str = "") -> QSpinBox:
    sp = QSpinBox()
    sp.setRange(lo, hi)
    sp.setValue(val)
    if suffix:
        sp.setSuffix(suffix)
    sp.setFixedWidth(_W_SPIN)
    return sp


def _make_dspin(lo: float, hi: float, val: float, suffix: str = "",
                step: float = 0.5, decimals: int = 1) -> QDoubleSpinBox:
    sp = QDoubleSpinBox()
    sp.setRange(lo, hi)
    sp.setValue(val)
    sp.setSingleStep(step)
    sp.setDecimals(decimals)
    if suffix:
        sp.setSuffix(suffix)
    sp.setFixedWidth(_W_SPIN)
    return sp


def _make_combo(items: list[tuple[str, str]], width: int = _W_COMBO) -> QComboBox:
    cb = QComboBox()
    for text, data in items:
        cb.addItem(text, data)
    cb.setFixedWidth(width)
    return cb


def _slider_with_spin(lo: int, hi: int, val: int, suffix: str = "") -> tuple[QWidget, QSlider, QSpinBox]:
    """Slider + spinbox in a single row widget."""
    w = QWidget()
    row = QHBoxLayout(w)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(6)

    sl = QSlider(Qt.Orientation.Horizontal)
    sl.setRange(lo, hi)
    sl.setValue(val)

    sp = QSpinBox()
    sp.setRange(lo, hi)
    sp.setValue(val)
    if suffix:
        sp.setSuffix(suffix)
    sp.setFixedWidth(_W_SPIN)

    sl.valueChanged.connect(sp.setValue)
    sp.valueChanged.connect(sl.setValue)

    row.addWidget(sl, 1)
    row.addWidget(sp)
    return w, sl, sp


def _color_btn_widget(color: str) -> QPushButton:
    btn = QPushButton()
    btn.setObjectName("colorBtn")
    btn.setStyleSheet(f"background:{color};")
    return btn


# ---------------------------------------------------------------------------
# Main Dialog
# ---------------------------------------------------------------------------

class SettingsDialog(QDialog):

    def __init__(self, settings_manager: SettingsManager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings  —  PapaRaZ")
        self.setMinimumSize(640, 440)
        self.resize(720, 520)
        self.setWindowFlags(Qt.WindowType.Dialog)

        theme = get_theme(settings_manager.settings.app_theme)
        check_css = _BASE.replace("%%CHECKMARK%%", _checkmark_path())
        self.setStyleSheet(check_css + build_dialog_qss(theme) + combo_arrow_css())

        self._sm = settings_manager
        self._s  = settings_manager.settings

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # --- Sidebar ---
        self._nav = QListWidget()
        self._nav.setFixedWidth(140)
        self._nav.setIconSize(QSize(14, 14))
        self._nav.setSpacing(0)

        for label in ["Capture", "Appearance", "Tools", "Behavior", "Shortcuts", "About"]:
            item = QListWidgetItem(label)
            item.setSizeHint(QSize(140, 34))
            self._nav.addItem(item)

        self._nav.currentRowChanged.connect(self._switch_page)

        # --- Stack ---
        self._stack = QStackedWidget()
        self._pages = [
            self._build_capture(),
            self._build_appearance(),
            self._build_tools(),
            self._build_behavior(),
            self._build_shortcuts(),
            self._build_about(),
        ]
        for p in self._pages:
            self._stack.addWidget(p)

        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)
        right.addWidget(self._stack, 1)

        # Bottom bar
        bar = QFrame()
        bar.setObjectName("bottomBar")
        bar.setFixedHeight(42)
        bar_row = QHBoxLayout(bar)
        bar_row.setContentsMargins(12, 0, 12, 0)

        reset_btn = QPushButton("Reset tool memory")
        reset_btn.setObjectName("danger")
        reset_btn.setToolTip("Clear all saved per-tool property memory")
        reset_btn.clicked.connect(self._reset_tool_memory)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("flat")
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("Save")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save_and_close)

        bar_row.addWidget(reset_btn)
        bar_row.addStretch()
        bar_row.addWidget(cancel_btn)
        bar_row.addSpacing(8)
        bar_row.addWidget(save_btn)
        right.addWidget(bar)

        root.addWidget(self._nav)
        root.addLayout(right, 1)

        self._nav.setCurrentRow(0)

    def _switch_page(self, row: int):
        self._stack.setCurrentIndex(row)

    # -----------------------------------------------------------------------
    # Pages
    # -----------------------------------------------------------------------

    def _build_capture(self) -> QWidget:
        inner, vbox = _page()
        vbox.addWidget(QLabel("Capture & Save", objectName="heading"))
        vbox.addSpacing(8)

        # Save location
        card, form = _section("Save Location")
        dir_w = QWidget()
        dir_row = QHBoxLayout(dir_w)
        dir_row.setContentsMargins(0, 0, 0, 0)
        dir_row.setSpacing(4)
        self._save_dir = QLineEdit(self._s.save_directory or "")
        self._save_dir.setPlaceholderText("Default: Pictures folder")
        browse_btn = QPushButton("...")
        browse_btn.setObjectName("flat")
        browse_btn.setFixedSize(28, 26)
        browse_btn.clicked.connect(self._browse_save_dir)
        dir_row.addWidget(self._save_dir, 1)
        dir_row.addWidget(browse_btn)
        form.addRow("Directory", dir_w)

        self._format_combo = _make_combo(
            [("png", "png"), ("jpg", "jpg"), ("svg", "svg")], _W_COMBO_SM)
        self._format_combo.setCurrentText(self._s.default_format)
        form.addRow("Format", self._format_combo)

        self._jpg_quality = _make_spin(10, 100, self._s.jpg_quality, "%")
        form.addRow("JPG quality", self._jpg_quality)

        vbox.addWidget(card)
        vbox.addSpacing(8)

        # Filename pattern
        card2, form2 = _section("Filename Pattern")
        from paparaz.ui.filename_pattern_widget import FilenamePatternWidget
        self._fn_pattern_widget = FilenamePatternWidget()
        self._fn_pattern_widget.set_pattern(
            getattr(self._s, "filename_pattern", "{yyyy}-{MM}-{dd}_{HH}-{mm}-{ss}"))
        self._fn_pattern_widget.set_extension(self._s.default_format)
        self._format_combo.currentTextChanged.connect(self._fn_pattern_widget.set_extension)
        form2.addRow(self._fn_pattern_widget)

        self._subfolder_edit = QLineEdit(getattr(self._s, "subfolder_pattern", ""))
        self._subfolder_edit.setPlaceholderText("e.g. {yyyy}\\{MM}  (leave blank for none)")
        form2.addRow("Subfolder", self._subfolder_edit)

        cnt_w = QWidget()
        cnt_row = QHBoxLayout(cnt_w)
        cnt_row.setContentsMargins(0, 0, 0, 0)
        cnt_row.setSpacing(6)
        self._counter_spin = _make_spin(1, 999999, getattr(self._s, "save_counter", 1))
        rst_btn = QPushButton("Reset")
        rst_btn.setObjectName("flat")
        rst_btn.setFixedWidth(50)
        rst_btn.clicked.connect(lambda: self._counter_spin.setValue(1))
        cnt_row.addWidget(self._counter_spin)
        cnt_row.addWidget(rst_btn)
        cnt_row.addStretch()
        form2.addRow("Counter", cnt_w)

        self._auto_save_check = _toggle(
            "Auto-save silently (skip dialog)",
            getattr(self._s, "auto_save", False))
        form2.addRow("", self._auto_save_check)
        vbox.addWidget(card2)
        vbox.addSpacing(8)

        # Capture behavior
        card3, form3 = _section("Behavior")
        self._tray_notify = _toggle("Show tray notification when ready",
                                     self._s.show_tray_notification)
        form3.addRow("", self._tray_notify)

        self._delay_spin = _make_spin(0, 30, getattr(self._s, 'capture_delay', 0), " sec")
        self._delay_spin.setSpecialValueText("None")
        form3.addRow("Default delay", self._delay_spin)

        self._max_recent = _make_spin(1, 100, getattr(self._s, 'max_recent', 10))
        form3.addRow("Max recent", self._max_recent)
        vbox.addWidget(card3)
        vbox.addSpacing(8)

        # Output
        card4, form4 = _section("Output")
        self._png_compression = _make_spin(0, 9, getattr(self._s, 'png_compression', 6))
        self._png_compression.setToolTip("0 = fastest, 9 = smallest file")
        form4.addRow("PNG compression", self._png_compression)

        self._auto_copy = _toggle("Copy to clipboard after saving",
                                   getattr(self._s, 'auto_copy_on_save', False))
        form4.addRow("", self._auto_copy)

        self._open_after_save = _toggle("Open file in default app after saving",
                                         getattr(self._s, 'open_after_save', False))
        form4.addRow("", self._open_after_save)
        vbox.addWidget(card4)

        vbox.addStretch()
        return _scroll(inner)

    def _build_appearance(self) -> QWidget:
        inner, vbox = _page()
        vbox.addWidget(QLabel("Appearance", objectName="heading"))
        vbox.addSpacing(8)

        # Theme cards (non-form layout — use vbox section)
        card, lay = _section_vbox("UI Theme")
        self._selected_theme = getattr(self._s, 'app_theme', 'dark')
        self._theme_btns: dict[str, QToolButton] = {}

        cards_row = QHBoxLayout()
        cards_row.setSpacing(6)
        cards_row.setContentsMargins(0, 0, 0, 0)
        for tid, tdata in APP_THEMES.items():
            btn = QToolButton()
            btn.setObjectName("themeCard")
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            btn.setText(tdata["name"])
            btn.setIcon(_make_theme_swatch(tdata))
            btn.setIconSize(QSize(72, 24))
            btn.setChecked(tid == self._selected_theme)
            btn.clicked.connect(lambda checked, t=tid: self._select_theme(t))
            cards_row.addWidget(btn)
            self._theme_btns[tid] = btn
        cards_row.addStretch()
        lay.addLayout(cards_row)
        vbox.addWidget(card)
        vbox.addSpacing(8)

        # Tray icon
        card2, lay2 = _section_vbox("Tray Icon")
        from paparaz.ui.tray import TRAY_ICON_COLORS
        self._tray_color = getattr(self._s, 'tray_icon_color', '#E53935')
        icon_row = QHBoxLayout()
        icon_row.setSpacing(6)
        icon_row.setContentsMargins(0, 0, 0, 0)
        self._icon_btns: dict[str, QPushButton] = {}
        for hex_color, name in TRAY_ICON_COLORS.items():
            btn = QPushButton()
            btn.setObjectName("iconBtn")
            btn.setCheckable(True)
            btn.setFixedSize(28, 28)
            btn.setToolTip(name)
            pix = QPixmap(20, 20)
            pix.fill(Qt.GlobalColor.transparent)
            p = QPainter(pix)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setBrush(QBrush(QColor(hex_color)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(1, 1, 18, 18)
            p.end()
            btn.setIcon(QIcon(pix))
            btn.setIconSize(QSize(20, 20))
            btn.setChecked(hex_color == self._tray_color)
            btn.clicked.connect(lambda checked, c=hex_color: self._select_icon_color(c))
            icon_row.addWidget(btn)
            self._icon_btns[hex_color] = btn
        self._tray_color_lbl = QLabel(TRAY_ICON_COLORS.get(self._tray_color, ''))
        self._tray_color_lbl.setObjectName("sub")
        icon_row.addWidget(self._tray_color_lbl)
        icon_row.addStretch()
        lay2.addLayout(icon_row)
        vbox.addWidget(card2)
        vbox.addSpacing(8)

        # Recent colors
        card3, lay3 = _section_vbox("Recent Colors")
        recent = list(getattr(self._s, 'recent_colors', []))
        rc_row = QHBoxLayout()
        rc_row.setSpacing(3)
        rc_row.setContentsMargins(0, 0, 0, 0)
        for hex_c in recent[:16]:
            swatch = QLabel()
            swatch.setFixedSize(18, 18)
            swatch.setStyleSheet(
                f"background:{hex_c}; border:1px solid #444; border-radius:2px;")
            rc_row.addWidget(swatch)
        if not recent:
            rc_row.addWidget(QLabel("No recent colors yet.", objectName="sub"))
        rc_row.addStretch()
        clear_rc_btn = QPushButton("Clear")
        clear_rc_btn.setObjectName("flat")
        clear_rc_btn.setFixedWidth(50)
        clear_rc_btn.clicked.connect(self._clear_recent_colors)
        rc_row.addWidget(clear_rc_btn)
        lay3.addLayout(rc_row)
        vbox.addWidget(card3)
        vbox.addSpacing(8)

        # Default preset
        card4, form4 = _section("Default Annotation Preset")
        from paparaz.ui.theme_presets import PRESETS, PRESET_ORDER
        self._theme_preset_combo = QComboBox()
        self._theme_preset_combo.setFixedWidth(_W_COMBO_LG)
        self._theme_preset_combo.addItem("— None —", "")
        for pid in PRESET_ORDER:
            p = PRESETS[pid]
            self._theme_preset_combo.addItem(f"{p.name} — {p.tagline}", pid)
        current_pid = getattr(self._s, 'default_theme_preset', "")
        for i in range(self._theme_preset_combo.count()):
            if self._theme_preset_combo.itemData(i) == current_pid:
                self._theme_preset_combo.setCurrentIndex(i)
                break
        form4.addRow("Preset", self._theme_preset_combo)
        sub = QLabel("Applied automatically when the editor opens.")
        sub.setObjectName("sub")
        form4.addRow("", sub)
        vbox.addWidget(card4)

        vbox.addStretch()
        return _scroll(inner)

    def _build_tools(self) -> QWidget:
        inner, vbox = _page()
        vbox.addWidget(QLabel("Tool Defaults", objectName="heading"))
        vbox.addSpacing(8)

        td = self._s.tool_defaults

        # Colors
        card, form = _section("Colors")
        self._fg_color = td.foreground_color
        fg_w = QWidget()
        fg_row = QHBoxLayout(fg_w)
        fg_row.setContentsMargins(0, 0, 0, 0)
        fg_row.setSpacing(6)
        self._fg_btn = _color_btn_widget(self._fg_color)
        self._fg_btn.clicked.connect(lambda: self._pick_color("fg"))
        self._fg_lbl = QLabel(self._fg_color)
        self._fg_lbl.setObjectName("sub")
        fg_row.addWidget(self._fg_btn)
        fg_row.addWidget(self._fg_lbl)
        fg_row.addStretch()
        form.addRow("Foreground", fg_w)

        self._bg_color = td.background_color
        bg_w = QWidget()
        bg_row = QHBoxLayout(bg_w)
        bg_row.setContentsMargins(0, 0, 0, 0)
        bg_row.setSpacing(6)
        self._bg_btn = _color_btn_widget(self._bg_color)
        self._bg_btn.clicked.connect(lambda: self._pick_color("bg"))
        self._bg_lbl = QLabel(self._bg_color)
        self._bg_lbl.setObjectName("sub")
        bg_row.addWidget(self._bg_btn)
        bg_row.addWidget(self._bg_lbl)
        bg_row.addStretch()
        form.addRow("Background", bg_w)
        vbox.addWidget(card)
        vbox.addSpacing(8)

        # Stroke & font
        card2, form2 = _section("Stroke & Font")
        lw_w, lw_sl, self._line_width = _slider_with_spin(1, 50, td.line_width, " px")
        form2.addRow("Width", lw_w)

        self._font_family = QFontComboBox()
        self._font_family.setCurrentFont(QFont(td.font_family))
        self._font_family.setFixedWidth(_W_COMBO_LG)
        form2.addRow("Font", self._font_family)

        fs_w, fs_sl, self._font_size = _slider_with_spin(6, 120, td.font_size, " pt")
        form2.addRow("Size", fs_w)
        vbox.addWidget(card2)
        vbox.addSpacing(8)

        # Shadow
        card3, form3 = _section("Default Shadow")
        for attr, label, default in [
            ('shadow_default_offset_x', 'Offset X', 3.0),
            ('shadow_default_offset_y', 'Offset Y', 3.0),
            ('shadow_default_blur_x',   'Blur X',   5.0),
            ('shadow_default_blur_y',   'Blur Y',   5.0),
        ]:
            sp = _make_dspin(-50 if 'offset' in attr else 0, 50,
                             getattr(self._s, attr, default))
            form3.addRow(label, sp)
            setattr(self, f'_sh_{attr.split("_", 2)[-1]}', sp)
        vbox.addWidget(card3)
        vbox.addSpacing(8)

        # Specialized defaults
        card4, form4 = _section("Specialized Tools")
        hl_w = QWidget()
        hl_row = QHBoxLayout(hl_w)
        hl_row.setContentsMargins(0, 0, 0, 0)
        hl_row.setSpacing(6)
        self._hl_color = getattr(self._s, 'highlight_default_color', '#FFFF00')
        self._hl_color_btn = _color_btn_widget(self._hl_color)
        self._hl_color_btn.clicked.connect(lambda: self._pick_color("hl"))
        self._hl_color_lbl = QLabel(self._hl_color)
        self._hl_color_lbl.setObjectName("sub")
        hl_row.addWidget(self._hl_color_btn)
        hl_row.addWidget(self._hl_color_lbl)
        hl_row.addStretch()
        form4.addRow("Highlight", hl_w)

        hl_w2, hl_sl, self._hl_width = _slider_with_spin(
            4, 64, getattr(self._s, 'highlight_default_width', 16), " px")
        form4.addRow("Highlight width", hl_w2)

        self._blur_pixels = _make_spin(2, 50, getattr(self._s, 'default_blur_pixels', 10), " px")
        form4.addRow("Blur size", self._blur_pixels)

        from paparaz.ui.stamps import STAMPS
        self._stamp_combo = QComboBox()
        self._stamp_combo.setFixedWidth(_W_COMBO_LG)
        current_stamp = getattr(self._s, 'default_stamp_id', 'check')
        for sid, sdata in STAMPS.items():
            self._stamp_combo.addItem(sdata.get("name", sid), sid)
        for i in range(self._stamp_combo.count()):
            if self._stamp_combo.itemData(i) == current_stamp:
                self._stamp_combo.setCurrentIndex(i)
                break
        form4.addRow("Default stamp", self._stamp_combo)
        vbox.addWidget(card4)

        vbox.addStretch()
        return _scroll(inner)

    def _build_behavior(self) -> QWidget:
        inner, vbox = _page()
        vbox.addWidget(QLabel("Behavior", objectName="heading"))
        vbox.addSpacing(8)

        # Capture
        card, form = _section("Capture")
        self._hide_before_capture = _toggle(
            "Hide editor before taking a new screenshot",
            getattr(self._s, 'hide_editor_before_capture', True))
        form.addRow("", self._hide_before_capture)

        self._capture_cursor = _toggle(
            "Include mouse cursor in screenshots",
            getattr(self._s, 'capture_cursor', False))
        form.addRow("", self._capture_cursor)

        self._capture_sound = _toggle(
            "Play shutter sound on capture",
            getattr(self._s, 'capture_sound', False))
        form.addRow("", self._capture_sound)
        vbox.addWidget(card)
        vbox.addSpacing(8)

        # Editor
        card2, form2 = _section("Editor")
        self._confirm_close = _toggle(
            "Confirm before closing with unsaved work",
            getattr(self._s, 'confirm_close_unsaved', True))
        form2.addRow("", self._confirm_close)

        self._exit_on_close = _toggle(
            "Quit app when last editor closes",
            getattr(self._s, 'exit_on_close', False))
        form2.addRow("", self._exit_on_close)
        vbox.addWidget(card2)
        vbox.addSpacing(8)

        # Canvas
        card3, form3 = _section("Canvas Background")
        self._canvas_bg = getattr(self._s, 'canvas_background', 'dark')
        bg_w = QWidget()
        bg_row = QHBoxLayout(bg_w)
        bg_row.setContentsMargins(0, 0, 0, 0)
        bg_row.setSpacing(8)
        self._bg_radio_grp = QButtonGroup(self)
        for value, label in [
            ("dark",         "Dark"),
            ("checkerboard", "Checkerboard"),
            ("system",       "System"),
        ]:
            rb = QRadioButton(label)
            rb.setChecked(self._canvas_bg == value)
            rb.toggled.connect(lambda checked, v=value: self._on_canvas_bg_changed(v) if checked else None)
            self._bg_radio_grp.addButton(rb)
            bg_row.addWidget(rb)

        self._custom_bg_rb = QRadioButton("Custom")
        is_custom = self._canvas_bg not in ('dark', 'checkerboard', 'system')
        self._custom_bg_rb.setChecked(is_custom)
        self._bg_radio_grp.addButton(self._custom_bg_rb)
        bg_row.addWidget(self._custom_bg_rb)

        self._custom_bg_btn = _color_btn_widget(self._canvas_bg if is_custom else "#2a2a3e")
        self._custom_bg_btn.setEnabled(is_custom)
        self._custom_bg_btn.clicked.connect(self._pick_canvas_bg_color)
        bg_row.addWidget(self._custom_bg_btn)

        self._custom_bg_rb.toggled.connect(
            lambda checked: self._on_canvas_bg_changed(
                getattr(self, '_custom_bg_color', '#2a2a3e')) if checked else None)
        self._custom_bg_rb.toggled.connect(self._custom_bg_btn.setEnabled)
        self._custom_bg_color = self._canvas_bg if is_custom else "#2a2a3e"
        bg_row.addStretch()
        form3.addRow("Style", bg_w)
        vbox.addWidget(card3)
        vbox.addSpacing(8)

        # Panel & Zoom
        card4, form4 = _section("Panel & Zoom")
        self._panel_mode_combo = _make_combo(
            [("Auto", "auto"), ("Pinned", "pinned"), ("Hidden", "hidden")], _W_COMBO)
        cur_mode = getattr(self._s, 'default_panel_mode', 'auto')
        for i in range(self._panel_mode_combo.count()):
            if self._panel_mode_combo.itemData(i) == cur_mode:
                self._panel_mode_combo.setCurrentIndex(i)
                break
        form4.addRow("Panel mode", self._panel_mode_combo)

        self._zoom_combo = _make_combo(
            [("Fit", "fit"), ("100%", "100"), ("Fill", "fill"), ("Remember", "remember")],
            _W_COMBO)
        cur_zoom = getattr(self._s, 'default_zoom', 'fit')
        for i in range(self._zoom_combo.count()):
            if self._zoom_combo.itemData(i) == cur_zoom:
                self._zoom_combo.setCurrentIndex(i)
                break
        form4.addRow("Default zoom", self._zoom_combo)

        ah_w, ah_sl, self._auto_hide_spin = _slider_with_spin(
            1, 10, getattr(self._s, 'panel_auto_hide_ms', 3000) // 1000, " s")
        form4.addRow("Auto-hide delay", ah_w)

        self._zoom_factor_spin = _make_dspin(1.05, 1.30,
            getattr(self._s, 'zoom_scroll_factor', 1.1), "\u00d7", 0.05, 2)
        form4.addRow("Scroll factor", self._zoom_factor_spin)
        vbox.addWidget(card4)
        vbox.addSpacing(8)

        # Snap & Grid
        card_snap, form_snap = _section("Snap & Grid")
        self._snap_enabled = _toggle(
            "Enable snapping",
            getattr(self._s, 'snap_enabled', True))
        form_snap.addRow("", self._snap_enabled)

        self._snap_canvas = _toggle(
            "Snap to canvas edges & center",
            getattr(self._s, 'snap_to_canvas', True))
        form_snap.addRow("", self._snap_canvas)

        self._snap_elements = _toggle(
            "Snap to other elements",
            getattr(self._s, 'snap_to_elements', True))
        form_snap.addRow("", self._snap_elements)

        self._snap_threshold = _make_spin(2, 20,
            getattr(self._s, 'snap_threshold', 8), " px")
        form_snap.addRow("Threshold", self._snap_threshold)

        self._snap_grid = _toggle(
            "Snap to grid",
            getattr(self._s, 'snap_grid_enabled', False))
        form_snap.addRow("", self._snap_grid)

        self._grid_size = _make_spin(5, 100,
            getattr(self._s, 'snap_grid_size', 20), " px")
        form_snap.addRow("Grid size", self._grid_size)

        self._show_grid = _toggle(
            "Show grid overlay",
            getattr(self._s, 'show_grid', False))
        form_snap.addRow("", self._show_grid)
        vbox.addWidget(card_snap)
        vbox.addSpacing(8)

        # Recovery
        card5, form5 = _section("Auto-save & Recovery")
        self._auto_save_interval = _make_spin(
            0, 600, getattr(self._s, 'auto_save_interval', 60), " sec")
        self._auto_save_interval.setSpecialValueText("Off")
        form5.addRow("Interval", self._auto_save_interval)

        self._crash_recovery = _toggle(
            "Offer to restore unsaved work on next launch",
            getattr(self._s, 'crash_recovery', True))
        form5.addRow("", self._crash_recovery)
        vbox.addWidget(card5)

        vbox.addStretch()
        return _scroll(inner)

    def _make_hotkey_row(self, name: str, current: str) -> QWidget:
        parts = [p.strip() for p in current.split("+")] if current else []
        key_part = parts[-1] if parts else ""
        mods = set(parts[:-1]) if len(parts) > 1 else set()

        row = QHBoxLayout()
        row.setSpacing(4)
        row.setContentsMargins(0, 0, 0, 0)

        _mod_style = (
            "QToolButton { background: #181830; color: #777; border: 1px solid #282848;"
            " border-radius: 3px; padding: 1px 4px; font-size: 10px;"
            " min-height: 20px; max-height: 20px; }"
            "QToolButton:checked { background: #1a0f2a; color: #b0b0ee;"
            " border-color: #7722aa; }"
        )

        cb_ctrl  = QToolButton(); cb_ctrl.setText("Ctrl");  cb_ctrl.setCheckable(True)
        cb_ctrl.setChecked("Ctrl" in mods);  cb_ctrl.setStyleSheet(_mod_style)
        cb_alt   = QToolButton(); cb_alt.setText("Alt");    cb_alt.setCheckable(True)
        cb_alt.setChecked("Alt" in mods);    cb_alt.setStyleSheet(_mod_style)
        cb_shift = QToolButton(); cb_shift.setText("Shift"); cb_shift.setCheckable(True)
        cb_shift.setChecked("Shift" in mods); cb_shift.setStyleSheet(_mod_style)
        cb_win   = QToolButton(); cb_win.setText("Win");    cb_win.setCheckable(True)
        cb_win.setChecked("Win" in mods);    cb_win.setStyleSheet(_mod_style)

        for cb in (cb_ctrl, cb_alt, cb_shift, cb_win):
            row.addWidget(cb)

        key_combo = QComboBox()
        key_combo.setFixedWidth(110)
        _KEYS = [
            "PrintScreen",
            "F1", "F2", "F3", "F4", "F5", "F6",
            "F7", "F8", "F9", "F10", "F11", "F12",
            "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M",
            "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z",
            "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
            "Delete", "Insert", "Home", "End", "PageUp", "PageDown",
            "Space", "Tab", "Escape",
        ]
        key_combo.addItems(_KEYS)
        if key_part in _KEYS:
            key_combo.setCurrentText(key_part)
        elif key_part:
            key_combo.addItem(key_part)
            key_combo.setCurrentText(key_part)
        row.addWidget(key_combo)
        row.addStretch()

        self._hk_editors[name] = {
            "ctrl": cb_ctrl, "alt": cb_alt, "shift": cb_shift, "win": cb_win,
            "key": key_combo,
        }
        hidden = QLineEdit(current)
        hidden.hide()
        self._hk_fields[name] = hidden

        def _update_hidden(_=None, n=name):
            ed = self._hk_editors[n]
            parts = []
            if ed["ctrl"].isChecked(): parts.append("Ctrl")
            if ed["alt"].isChecked(): parts.append("Alt")
            if ed["shift"].isChecked(): parts.append("Shift")
            if ed["win"].isChecked(): parts.append("Win")
            parts.append(ed["key"].currentText())
            self._hk_fields[n].setText("+".join(parts))

        cb_ctrl.toggled.connect(_update_hidden)
        cb_alt.toggled.connect(_update_hidden)
        cb_shift.toggled.connect(_update_hidden)
        cb_win.toggled.connect(_update_hidden)
        key_combo.currentTextChanged.connect(_update_hidden)

        w = QWidget()
        w.setLayout(row)
        return w

    def _build_shortcuts(self) -> QWidget:
        inner, vbox = _page()
        vbox.addWidget(QLabel("Shortcuts", objectName="heading"))
        vbox.addWidget(QLabel("Changes take effect after restart.", objectName="sub"))
        vbox.addSpacing(8)

        # Capture hotkeys
        card, form = _section("Capture (Global)")
        self._hk_fields: dict[str, QLineEdit] = {}
        self._hk_editors: dict[str, dict] = {}
        hk = self._s.hotkeys
        for name, label in [
            ("capture",            "Region"),
            ("capture_fullscreen", "Full screen"),
            ("capture_window",     "Active window"),
            ("capture_repeat",     "Repeat last"),
        ]:
            form.addRow(label, self._make_hotkey_row(name, getattr(hk, name, "")))
        vbox.addWidget(card)
        vbox.addSpacing(8)

        # Editor shortcuts
        card2, form2 = _section("Editor")
        for name, label in [
            ("undo",           "Undo"),
            ("redo",           "Redo"),
            ("save",           "Save"),
            ("save_as",        "Save As"),
            ("copy_clipboard", "Copy"),
            ("delete",         "Delete"),
            ("select_all",     "Select all"),
        ]:
            form2.addRow(label, self._make_hotkey_row(name, getattr(hk, name, "")))
        vbox.addWidget(card2)
        vbox.addSpacing(8)

        # Fixed shortcuts reference
        card3, lay3 = _section_vbox("Reference (Fixed)")
        for label, keys in [
            ("Zoom in/out",     ["Ctrl+=", "Ctrl+\u2212"]),
            ("Zoom reset",      ["Ctrl+0"]),
            ("Pan",             ["Middle-click"]),
            ("Finalize text",   ["Ctrl+Enter"]),
            ("Multi-select",    ["Shift+click", "Rubber-band"]),
            ("Precision move",  ["Arrows", "+Shift \u00d710"]),
            ("Z-order",         ["Ctrl+]", "Ctrl+["]),
        ]:
            ref_row = QHBoxLayout()
            ref_row.setSpacing(6)
            ref_row.setContentsMargins(0, 0, 0, 0)
            lbl = QLabel(label)
            lbl.setFixedWidth(100)
            ref_row.addWidget(lbl)
            for k in keys:
                badge = QLabel(k)
                badge.setObjectName("keyBadge")
                ref_row.addWidget(badge)
            ref_row.addStretch()
            lay3.addLayout(ref_row)
        vbox.addWidget(card3)

        vbox.addStretch()
        return _scroll(inner)

    def _build_about(self) -> QWidget:
        inner, vbox = _page()

        title = QLabel("PapaRaZ")
        title.setStyleSheet("color: #8822bb; font-size: 18px; font-weight: bold;")
        vbox.addWidget(title)

        from paparaz.utils.updater import __version__
        vbox.addWidget(QLabel(f"v{__version__}  \u00b7  Screen Capture & Annotation"))
        vbox.addSpacing(8)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        for text, url, obj_name in [
            ("Website",  "https://github.com/aleled/paparaz", "flat"),
            ("Updates",  None, None),
            ("Issues",   "https://github.com/aleled/paparaz/issues", "flat"),
        ]:
            btn = QPushButton(text)
            if url:
                btn.setObjectName(obj_name)
                btn.clicked.connect(lambda checked, u=url: QDesktopServices.openUrl(QUrl(u)))
            else:
                btn.clicked.connect(self._check_now)
            btn.setFixedHeight(28)
            btn_row.addWidget(btn)
        btn_row.addStretch()
        vbox.addLayout(btn_row)
        vbox.addSpacing(8)

        # System
        card, form = _section("System")
        from paparaz.utils.startup import get_start_on_login
        self._start_login = _toggle("Launch at Windows login", get_start_on_login())
        form.addRow("", self._start_login)

        self._auto_update = _toggle("Check for updates on startup",
                                     getattr(self._s, 'auto_check_updates', True))
        form.addRow("", self._auto_update)
        vbox.addWidget(card)
        vbox.addSpacing(8)

        # Credits
        card2, form2 = _section("Credits")
        form2.addRow("Author", QLabel("Alejandro Lichtenfeld"))
        form2.addRow("License", QLabel("MIT"))
        vbox.addWidget(card2)
        vbox.addSpacing(8)

        # Built with
        card3, lay3 = _section_vbox("Built With")
        for lib, desc in [
            ("PySide6", "Qt 6 GUI"),
            ("Win32 ctypes", "DPI-aware capture"),
            ("winrt", "Windows OCR"),
            ("Pillow", "Image processing"),
            ("PyInstaller", "Packaging"),
        ]:
            lbl = QLabel(f"{lib}  \u2014  {desc}")
            lbl.setStyleSheet("color: #666; font-size: 10px;")
            lay3.addWidget(lbl)
        vbox.addWidget(card3)
        vbox.addSpacing(8)

        # License
        card4, lay4 = _section_vbox("License")
        license_text = QLabel(
            "MIT License \u00b7 Copyright (c) 2024 Alejandro Lichtenfeld\n\n"
            "Permission is hereby granted, free of charge, to any person obtaining a copy "
            "of this software and associated documentation files, to deal in the Software "
            "without restriction, including without limitation the rights to use, copy, "
            "modify, merge, publish, distribute, sublicense, and/or sell copies."
        )
        license_text.setWordWrap(True)
        license_text.setStyleSheet(
            "color: #555; font-size: 9px; font-family: Consolas, monospace;"
            " background: #0d0d16; border: 1px solid #1e1e34; border-radius: 3px;"
            " padding: 6px;")
        lay4.addWidget(license_text)
        vbox.addWidget(card4)

        vbox.addStretch()
        return _scroll(inner)

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _select_icon_color(self, color: str):
        self._tray_color = color
        from paparaz.ui.tray import TRAY_ICON_COLORS
        for hex_c, btn in self._icon_btns.items():
            btn.setChecked(hex_c == color)
        self._tray_color_lbl.setText(TRAY_ICON_COLORS.get(color, ''))

    def _clear_recent_colors(self):
        self._s.recent_colors = []
        self._sm.save()

    def _browse_save_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Select Save Directory")
        if d:
            self._save_dir.setText(d)

    def _pick_color(self, which: str):
        if which == "hl":
            current = self._hl_color
        elif which == "fg":
            current = self._fg_color
        else:
            current = self._bg_color
        color = QColorDialog.getColor(QColor(current), self)
        if color.isValid():
            if which == "fg":
                self._fg_color = color.name()
                self._fg_btn.setStyleSheet(f"background:{self._fg_color};")
                self._fg_lbl.setText(self._fg_color)
            elif which == "hl":
                self._hl_color = color.name()
                self._hl_color_btn.setStyleSheet(f"background:{self._hl_color};")
                self._hl_color_lbl.setText(self._hl_color)
            else:
                self._bg_color = color.name()
                self._bg_btn.setStyleSheet(f"background:{self._bg_color};")
                self._bg_lbl.setText(self._bg_color)

    def _reset_tool_memory(self):
        self._s.tool_properties.clear()
        self._sm.save()
        self.setWindowTitle("Settings  \u2014  PapaRaZ  [Tool memory cleared]")

    def _check_now(self):
        from paparaz.utils.updater import check_for_updates_manual
        check_for_updates_manual(parent=self)

    def _select_theme(self, theme_id: str):
        self._selected_theme = theme_id
        for tid, btn in self._theme_btns.items():
            btn.setChecked(tid == theme_id)
        self._on_theme_preview()

    def _on_theme_preview(self):
        theme_id = self._selected_theme
        if not theme_id:
            return
        theme = get_theme(theme_id)
        check_css = _BASE.replace("%%CHECKMARK%%", _checkmark_path())
        self.setStyleSheet(check_css + build_dialog_qss(theme) + combo_arrow_css())
        if self.parent() and hasattr(self.parent(), 'apply_app_theme'):
            self.parent().apply_app_theme(theme_id)

    def _on_canvas_bg_changed(self, value: str):
        self._canvas_bg = value

    def _pick_canvas_bg_color(self):
        c = QColorDialog.getColor(QColor(self._custom_bg_color), self, "Canvas Background Color")
        if c.isValid():
            self._custom_bg_color = c.name()
            self._custom_bg_btn.setStyleSheet(f"background:{self._custom_bg_color};")
            self._canvas_bg = self._custom_bg_color

    # -----------------------------------------------------------------------
    # Save
    # -----------------------------------------------------------------------

    def _save_and_close(self):
        s = self._s

        # Capture
        s.save_directory         = self._save_dir.text()
        s.default_format         = self._format_combo.currentData() or self._format_combo.currentText()
        s.jpg_quality            = self._jpg_quality.value()
        s.filename_pattern       = self._fn_pattern_widget.get_pattern()
        s.subfolder_pattern      = self._subfolder_edit.text()
        s.auto_save              = self._auto_save_check.isChecked()
        s.save_counter           = self._counter_spin.value()
        s.show_tray_notification = self._tray_notify.isChecked()
        s.max_recent             = self._max_recent.value()

        # Appearance
        s.app_theme              = self._selected_theme
        s.tray_icon_color        = self._tray_color
        s.default_theme_preset   = self._theme_preset_combo.currentData() or ""

        # Tools
        s.tool_defaults.foreground_color = self._fg_color
        s.tool_defaults.background_color = self._bg_color
        s.tool_defaults.line_width       = self._line_width.value()
        s.tool_defaults.font_family      = self._font_family.currentFont().family()
        s.tool_defaults.font_size        = self._font_size.value()
        s.shadow_default_offset_x        = self._sh_offset_x.value()
        s.shadow_default_offset_y        = self._sh_offset_y.value()
        s.shadow_default_blur_x          = self._sh_blur_x.value()
        s.shadow_default_blur_y          = self._sh_blur_y.value()
        s.highlight_default_color        = self._hl_color
        s.highlight_default_width        = self._hl_width.value()
        s.default_blur_pixels            = self._blur_pixels.value()
        s.default_stamp_id               = self._stamp_combo.currentData() or "check"

        # Output
        s.png_compression            = self._png_compression.value()
        s.auto_copy_on_save          = self._auto_copy.isChecked()
        s.open_after_save            = self._open_after_save.isChecked()

        # Behavior
        s.hide_editor_before_capture = self._hide_before_capture.isChecked()
        s.capture_cursor             = self._capture_cursor.isChecked()
        s.capture_sound              = self._capture_sound.isChecked()
        s.confirm_close_unsaved      = self._confirm_close.isChecked()
        s.exit_on_close              = self._exit_on_close.isChecked()
        s.canvas_background          = self._canvas_bg
        s.panel_auto_hide_ms         = self._auto_hide_spin.value() * 1000
        s.zoom_scroll_factor         = self._zoom_factor_spin.value()
        s.default_panel_mode         = self._panel_mode_combo.currentData() or "auto"
        s.default_zoom               = self._zoom_combo.currentData() or "fit"
        s.auto_save_interval         = self._auto_save_interval.value()
        s.crash_recovery             = self._crash_recovery.isChecked()
        s.snap_enabled               = self._snap_enabled.isChecked()
        s.snap_to_canvas             = self._snap_canvas.isChecked()
        s.snap_to_elements           = self._snap_elements.isChecked()
        s.snap_threshold             = self._snap_threshold.value()
        s.snap_grid_enabled          = self._snap_grid.isChecked()
        s.snap_grid_size             = self._grid_size.value()
        s.show_grid                  = self._show_grid.isChecked()

        # Shortcuts
        for name, field in self._hk_fields.items():
            setattr(s.hotkeys, name, field.text())

        # System
        s.auto_check_updates = self._auto_update.isChecked()
        s.start_on_login     = self._start_login.isChecked()
        from paparaz.utils.startup import set_start_on_login
        set_start_on_login(s.start_on_login)

        self._sm.save()

        # Apply theme and tray icon immediately
        if self.parent() and hasattr(self.parent(), 'apply_app_theme'):
            self.parent().apply_app_theme(s.app_theme)
        root = self.parent()
        while root and root.parent():
            root = root.parent()
        if root and hasattr(root, '_tray'):
            root._tray.set_icon_color(s.tray_icon_color)

        self.accept()
