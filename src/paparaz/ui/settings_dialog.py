"""Settings dialog — modern sidebar navigation."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QWidget, QLabel, QLineEdit, QSpinBox, QDoubleSpinBox,
    QComboBox, QPushButton, QFileDialog,
    QColorDialog, QGroupBox, QScrollArea, QFrame,
    QListWidget, QListWidgetItem, QStackedWidget, QSizePolicy,
    QToolButton, QSlider, QFontComboBox, QButtonGroup, QRadioButton,
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
QDialog { background: #0f0f1a; color: #ddd; font-size: 12px; }

/* ── Sidebar ─────────────────────────────────────────────────────────────── */
QListWidget {
    background: #13131f; border: none;
    border-right: 1px solid #222236; outline: 0;
}
QListWidget::item {
    padding: 0; border-radius: 0; color: #888;
    min-height: 48px;
}
QListWidget::item:selected {
    background: #1d0b30; color: #e0b0ff;
    border-left: 3px solid #9b30c8;
}
QListWidget::item:hover:!selected {
    background: #18182c; color: #bbb;
}

/* ── Content area ─────────────────────────────────────────────────────────── */
QScrollArea { border: none; background: transparent; }
QWidget#page { background: transparent; }

/* ── Card groups ─────────────────────────────────────────────────────────── */
QGroupBox {
    background: #13131f; border: 1px solid #222236;
    border-radius: 8px; margin-top: 24px; padding: 16px 14px 12px 14px;
    font-size: 10px; font-weight: bold; letter-spacing: 1.2px;
    color: #555;
}
QGroupBox::title {
    subcontrol-origin: margin; subcontrol-position: top left;
    left: 12px; top: 0px; padding: 0 6px;
    background: #0f0f1a; color: #555;
}

/* ── Inputs ──────────────────────────────────────────────────────────────── */
QLineEdit, QSpinBox, QComboBox, QDoubleSpinBox {
    background: #1a1a2e; color: #ddd; border: 1px solid #2a2a45;
    border-radius: 6px; padding: 6px 10px; min-height: 28px; font-size: 12px;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QDoubleSpinBox:focus {
    border-color: #8800bb; background: #1c0f2a;
}
QComboBox::drop-down { border: none; width: 22px; }
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    background: #252540; border: none; border-radius: 2px; width: 16px;
}

/* ── Sliders ─────────────────────────────────────────────────────────────── */
QSlider::groove:horizontal {
    height: 4px; background: #2a2a45; border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #8800bb; width: 14px; height: 14px;
    margin: -5px 0; border-radius: 7px; border: 2px solid #1a1a2e;
}
QSlider::handle:horizontal:hover { background: #aa33dd; }
QSlider::sub-page:horizontal { background: #8800bb; border-radius: 2px; }

/* ── Toggle settings (on/off boolean options) ────────────────────────────── */
QPushButton#toggleSetting {
    background: #13131f; border: 1px solid #2a2a45;
    border-radius: 6px; color: #555; text-align: left;
    padding: 8px 14px; font-size: 12px; min-height: 32px; font-weight: 400;
}
QPushButton#toggleSetting:hover { border-color: #555577; color: #999; }
QPushButton#toggleSetting:checked {
    background: #1d0b30; border-color: #8800bb; color: #e0b0ff;
    border-left: 3px solid #8800bb;
}
QPushButton#toggleSetting:checked:hover { background: #250d3a; }

/* ── Buttons ─────────────────────────────────────────────────────────────── */
QPushButton {
    background: #740096; color: white; border: none;
    border-radius: 6px; padding: 8px 22px; font-weight: 600; font-size: 12px;
    letter-spacing: 0.3px;
}
QPushButton:hover   { background: #9e2ac0; }
QPushButton:pressed { background: #5a0074; }

QPushButton#secondary {
    background: #1a1a2e; color: #888; border: 1px solid #2a2a45;
    padding: 8px 18px; font-weight: 400;
}
QPushButton#secondary:hover { background: #222240; color: #ccc; }

QPushButton#danger {
    background: transparent; color: #cc5555; border: 1px solid #5a1515;
    padding: 8px 16px; font-weight: 400; border-radius: 6px;
}
QPushButton#danger:hover { background: #2a0808; color: #ff7777; }

QPushButton#colorBtn {
    min-width: 34px; max-width: 34px; min-height: 28px; max-height: 28px;
    border: 2px solid #3a3a5a; border-radius: 6px; padding: 0;
}
QPushButton#colorBtn:hover { border-color: #8800bb; }

QPushButton#iconBtn {
    background: #1a1a2e; border: 2px solid #2a2a45;
    border-radius: 8px; padding: 4px;
}
QPushButton#iconBtn:checked { border-color: #8800bb; background: #1d0b30; }
QPushButton#iconBtn:hover   { border-color: #8800bb; }

QPushButton#themeCard {
    background: #13131f; border: 2px solid #222236;
    border-radius: 10px; padding: 8px; text-align: left; color: #aaa;
    min-width: 110px; max-width: 130px; min-height: 80px;
}
QPushButton#themeCard:checked { border-color: #8800bb; background: #1d0b30; color: #e0b0ff; }
QPushButton#themeCard:hover   { border-color: #555577; }

QToolButton#themeCard {
    background: #13131f; border: 2px solid #222236;
    border-radius: 10px; padding: 10px 8px 8px 8px; color: #aaa;
    font-size: 11px; font-weight: 600;
    min-width: 110px; max-width: 140px; min-height: 88px;
}
QToolButton#themeCard:checked { border-color: #8800bb; background: #1d0b30; color: #e0b0ff; }
QToolButton#themeCard:hover:!checked { border-color: #555577; }

/* ── Labels ──────────────────────────────────────────────────────────────── */
QLabel            { color: #bbb; font-size: 12px; }
QLabel#heading    { color: #fff; font-size: 18px; font-weight: bold; }
QLabel#sub        { color: #555; font-size: 11px; margin-top: 2px; }
QLabel#sectionLbl { color: #666; font-size: 10px; font-weight: bold; letter-spacing: 1px;
                    margin-top: 18px; margin-bottom: 4px; }
QLabel#version    { color: #8800bb; font-size: 14px; font-weight: bold; }
QLabel#keyBadge   { color: #999; background: #1a1a2e; border: 1px solid #2a2a45;
                    border-radius: 4px; padding: 2px 6px; font-size: 11px; }

/* ── Bottom bar ──────────────────────────────────────────────────────────── */
QFrame#bottomBar { background: #0d0d18; border-top: 1px solid #1e1e38; }
"""


def _sep() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet("color: #2a2a45; margin: 4px 0;")
    return f


def _scroll(inner: QWidget) -> QScrollArea:
    sa = QScrollArea()
    sa.setWidgetResizable(True)
    sa.setWidget(inner)
    sa.setObjectName("page")
    return sa


def _page() -> tuple[QWidget, QVBoxLayout]:
    w = QWidget()
    w.setObjectName("page")
    v = QVBoxLayout(w)
    v.setContentsMargins(28, 20, 28, 20)
    v.setSpacing(0)
    return w, v


def _grp(title: str) -> tuple[QGroupBox, QFormLayout]:
    g = QGroupBox(title.upper())
    f = QFormLayout(g)
    f.setContentsMargins(0, 12, 0, 8)
    f.setSpacing(10)
    f.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    return g, f


def _color_swatch(color: str) -> QPixmap:
    pix = QPixmap(22, 22)
    pix.fill(QColor(color))
    return pix


def _make_theme_swatch(tdata: dict) -> QIcon:
    """Three-band color icon showing bg/accent/fg for a theme."""
    pix = QPixmap(96, 34)
    p = QPainter(pix)
    band = 32
    for i, c in enumerate([tdata["bg1"], tdata["accent"], tdata["fg"]]):
        p.fillRect(i * band, 0, band, 34, QColor(c))
    # right-most leftover
    p.fillRect(3 * band, 0, pix.width() - 3 * band, 34, QColor(tdata["fg"]))
    p.end()
    return QIcon(pix)


def _nav_item(color: str, label: str, subtitle: str) -> QWidget:
    """Custom sidebar item widget: thin color bar + two-line label."""
    w = QWidget()
    w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    row = QHBoxLayout(w)
    row.setContentsMargins(14, 0, 8, 0)
    row.setSpacing(12)

    bar = QFrame()
    bar.setFixedSize(3, 28)
    bar.setStyleSheet(f"background: {color}; border-radius: 1px;")
    row.addWidget(bar)

    col = QVBoxLayout()
    col.setSpacing(1)
    name_lbl = QLabel(label)
    name_lbl.setStyleSheet("color: #ccc; font-size: 12px; font-weight: 600; background: transparent;")
    sub_lbl = QLabel(subtitle)
    sub_lbl.setStyleSheet("color: #555; font-size: 10px; background: transparent;")
    col.addWidget(name_lbl)
    col.addWidget(sub_lbl)
    row.addLayout(col)
    row.addStretch()
    return w


def _slider_row(min_v: int, max_v: int, value: int, suffix: str = "") -> tuple[QSlider, QSpinBox]:
    """Linked horizontal slider + spinbox pair."""
    sl = QSlider(Qt.Orientation.Horizontal)
    sl.setRange(min_v, max_v)
    sl.setValue(value)

    sp = QSpinBox()
    sp.setRange(min_v, max_v)
    sp.setValue(value)
    if suffix:
        sp.setSuffix(suffix)
    sp.setFixedWidth(70)

    sl.valueChanged.connect(sp.setValue)
    sp.valueChanged.connect(sl.setValue)
    return sl, sp


# ---------------------------------------------------------------------------
# Main Dialog
# ---------------------------------------------------------------------------

class SettingsDialog(QDialog):

    def __init__(self, settings_manager: SettingsManager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings  —  PapaRaZ")
        self.setMinimumSize(780, 560)
        self.resize(860, 600)
        self.setWindowFlags(Qt.WindowType.Dialog)  # no always-on-top
        # Build stylesheet: _BASE provides sidebar/card/badge rules; build_dialog_qss
        # overlays theme-specific colors (accent, bg, fg) on top of them.
        theme = get_theme(settings_manager.settings.app_theme)
        self.setStyleSheet(_BASE + build_dialog_qss(theme) + combo_arrow_css())

        self._sm = settings_manager
        self._s  = settings_manager.settings

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # --- Sidebar ---
        self._nav = QListWidget()
        self._nav.setFixedWidth(180)
        self._nav.setIconSize(QSize(18, 18))
        self._nav.setSpacing(2)

        _NAV_ITEMS = [
            ("#0088dd", "Capture",    "Screenshots & save"),
            ("#9922cc", "Appearance", "Theme & icons"),
            ("#22aa66", "Tools",      "Defaults & memory"),
            ("#cc6600", "Behavior",   "Window & editor"),
            ("#dd7700", "Shortcuts",  "Keyboard bindings"),
            ("#dd3366", "Presets",    "Style presets"),
            ("#0099bb", "Updates",    "Version & startup"),
            ("#666688", "About",      "Info & credits"),
        ]
        for color, label, subtitle in _NAV_ITEMS:
            item = QListWidgetItem()
            item.setSizeHint(QSize(180, 56))
            self._nav.addItem(item)
            self._nav.setItemWidget(item, _nav_item(color, label, subtitle))

        self._nav.currentRowChanged.connect(self._switch_page)

        # --- Stack ---
        self._stack = QStackedWidget()
        self._pages = [
            self._build_capture(),
            self._build_appearance(),
            self._build_tools(),
            self._build_behavior(),
            self._build_shortcuts(),
            self._build_presets(),
            self._build_updates(),
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
        bar.setFixedHeight(54)
        bar_row = QHBoxLayout(bar)
        bar_row.setContentsMargins(16, 10, 16, 10)

        reset_btn = QPushButton("Reset tool memory")
        reset_btn.setObjectName("danger")
        reset_btn.setToolTip("Clear all saved per-tool property memory")
        reset_btn.clicked.connect(self._reset_tool_memory)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondary")
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

        vbox.addWidget(QLabel("Capture", objectName="heading"))
        vbox.addSpacing(4)
        vbox.addWidget(QLabel("Configure how screenshots are captured and saved.", objectName="sub"))

        # Save location
        grp, form = _grp("Save Location")
        dir_row = QHBoxLayout()
        self._save_dir = QLineEdit(self._s.save_directory or "")
        self._save_dir.setPlaceholderText("Default: Pictures folder")
        dir_row.addWidget(self._save_dir, 1)
        browse_btn = QPushButton("…")
        browse_btn.setObjectName("secondary")
        browse_btn.setFixedWidth(36)
        browse_btn.clicked.connect(self._browse_save_dir)
        dir_row.addWidget(browse_btn)
        form.addRow("Directory:", dir_row)

        self._format_combo = QComboBox()
        self._format_combo.addItems(["png", "jpg", "svg"])
        self._format_combo.setCurrentText(self._s.default_format)
        form.addRow("Default format:", self._format_combo)

        self._jpg_quality = QSpinBox()
        self._jpg_quality.setRange(10, 100)
        self._jpg_quality.setValue(self._s.jpg_quality)
        self._jpg_quality.setSuffix("%")
        form.addRow("JPG quality:", self._jpg_quality)
        vbox.addWidget(grp)

        # Behavior
        grp2, form2 = _grp("Capture Behavior")
        self._tray_notify = QPushButton("Show tray notification when ready")
        self._tray_notify.setObjectName("toggleSetting")
        self._tray_notify.setCheckable(True)
        self._tray_notify.setChecked(self._s.show_tray_notification)
        form2.addRow("", self._tray_notify)

        self._delay_spin = QSpinBox()
        self._delay_spin.setRange(0, 30)
        self._delay_spin.setValue(getattr(self._s, 'capture_delay', 0))
        self._delay_spin.setSuffix(" sec")
        self._delay_spin.setSpecialValueText("No delay")
        form2.addRow("Default delay:", self._delay_spin)
        vbox.addWidget(grp2)

        # Filename Pattern
        from paparaz.ui.filename_pattern_widget import FilenamePatternWidget
        grp3, form3 = _grp("Filename Pattern")

        self._fn_pattern_widget = FilenamePatternWidget()
        self._fn_pattern_widget.set_pattern(
            getattr(self._s, "filename_pattern", "{yyyy}-{MM}-{dd}_{HH}-{mm}-{ss}")
        )
        form3.addRow(self._fn_pattern_widget)

        self._subfolder_edit = QLineEdit(getattr(self._s, "subfolder_pattern", ""))
        self._subfolder_edit.setPlaceholderText("e.g. {yyyy}\\{MM}  (leave blank for none)")
        form3.addRow("Subfolder:", self._subfolder_edit)

        self._auto_save_check = QPushButton("Auto-save silently (Ctrl+Shift+S skips dialog)")
        self._auto_save_check.setObjectName("toggleSetting")
        self._auto_save_check.setCheckable(True)
        self._auto_save_check.setChecked(getattr(self._s, "auto_save", False))
        form3.addRow("", self._auto_save_check)

        counter_row = QHBoxLayout()
        self._counter_spin = QSpinBox()
        self._counter_spin.setRange(1, 999999)
        self._counter_spin.setValue(getattr(self._s, "save_counter", 1))
        counter_row.addWidget(self._counter_spin)
        reset_counter_btn = QPushButton("Reset to 1")
        reset_counter_btn.setObjectName("secondary")
        reset_counter_btn.clicked.connect(lambda: self._counter_spin.setValue(1))
        counter_row.addWidget(reset_counter_btn)
        counter_row.addStretch()
        form3.addRow("Counter start:", counter_row)

        vbox.addWidget(grp3)

        vbox.addStretch()
        return _scroll(inner)

    def _build_appearance(self) -> QWidget:
        inner, vbox = _page()

        vbox.addWidget(QLabel("Appearance", objectName="heading"))
        vbox.addSpacing(4)
        vbox.addWidget(QLabel("Customize the look of the app and tray icon.", objectName="sub"))
        vbox.addSpacing(16)

        # ── UI Theme cards ────────────────────────────────────────────────────
        theme_section = QLabel("UI THEME", objectName="sectionLbl")
        vbox.addWidget(theme_section)
        vbox.addSpacing(8)

        self._selected_theme = getattr(self._s, 'app_theme', 'dark')
        self._theme_btns: dict[str, QToolButton] = {}

        cards_row = QHBoxLayout()
        cards_row.setSpacing(10)
        cards_row.setContentsMargins(0, 0, 0, 0)
        for tid, tdata in APP_THEMES.items():
            btn = QToolButton()
            btn.setObjectName("themeCard")
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            btn.setText(tdata["name"])
            btn.setIcon(_make_theme_swatch(tdata))
            btn.setIconSize(QSize(96, 34))
            btn.setChecked(tid == self._selected_theme)
            btn.clicked.connect(lambda checked, t=tid: self._select_theme(t))
            cards_row.addWidget(btn)
            self._theme_btns[tid] = btn
        cards_row.addStretch()

        cards_widget = QWidget()
        cards_widget.setLayout(cards_row)
        vbox.addWidget(cards_widget)
        vbox.addSpacing(20)

        # ── Tray icon color ───────────────────────────────────────────────────
        tray_section = QLabel("TRAY ICON COLOR", objectName="sectionLbl")
        vbox.addWidget(tray_section)
        vbox.addSpacing(8)

        from paparaz.ui.tray import TRAY_ICON_COLORS
        self._tray_color = getattr(self._s, 'tray_icon_color', '#E53935')
        icon_row = QHBoxLayout()
        icon_row.setSpacing(8)
        icon_row.setContentsMargins(0, 0, 0, 0)
        self._icon_btns: dict[str, QPushButton] = {}
        for hex_color, name in TRAY_ICON_COLORS.items():
            btn = QPushButton()
            btn.setObjectName("iconBtn")
            btn.setCheckable(True)
            btn.setFixedSize(38, 38)
            btn.setToolTip(name)
            pix = QPixmap(26, 26)
            pix.fill(Qt.GlobalColor.transparent)
            p = QPainter(pix)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setBrush(QBrush(QColor(hex_color)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(1, 1, 24, 24)
            p.end()
            btn.setIcon(QIcon(pix))
            btn.setIconSize(QSize(26, 26))
            btn.setChecked(hex_color == self._tray_color)
            btn.clicked.connect(lambda checked, c=hex_color: self._select_icon_color(c))
            icon_row.addWidget(btn)
            self._icon_btns[hex_color] = btn

        self._tray_color_lbl = QLabel(TRAY_ICON_COLORS.get(self._tray_color, ''))
        self._tray_color_lbl.setObjectName("sub")
        self._tray_color_lbl.setStyleSheet("margin-left: 8px;")
        icon_row.addWidget(self._tray_color_lbl)
        icon_row.addStretch()

        icon_row_w = QWidget()
        icon_row_w.setLayout(icon_row)
        vbox.addWidget(icon_row_w)
        vbox.addSpacing(20)

        # ── Default annotation preset ─────────────────────────────────────────
        preset_section = QLabel("DEFAULT ANNOTATION PRESET", objectName="sectionLbl")
        vbox.addWidget(preset_section)
        vbox.addSpacing(8)

        from paparaz.ui.theme_presets import PRESETS, PRESET_ORDER
        self._theme_preset_combo = QComboBox()
        self._theme_preset_combo.addItem("— None —", "")
        for pid in PRESET_ORDER:
            p = PRESETS[pid]
            self._theme_preset_combo.addItem(
                f"{p.category.capitalize()} · {p.name} — {p.tagline}", pid)
        current_pid = getattr(self._s, 'default_theme_preset', "")
        for i in range(self._theme_preset_combo.count()):
            if self._theme_preset_combo.itemData(i) == current_pid:
                self._theme_preset_combo.setCurrentIndex(i)
                break
        vbox.addWidget(self._theme_preset_combo)
        note = QLabel("Applied automatically when the editor opens.")
        note.setObjectName("sub")
        vbox.addWidget(note)

        vbox.addStretch()
        return _scroll(inner)

    def _build_tools(self) -> QWidget:
        inner, vbox = _page()

        vbox.addWidget(QLabel("Tools", objectName="heading"))
        vbox.addSpacing(4)
        vbox.addWidget(QLabel("Default properties applied to new annotation elements.", objectName="sub"))

        td = self._s.tool_defaults

        # Colors
        grp, form = _grp("Default Colors")
        self._fg_color = td.foreground_color
        self._fg_btn = QPushButton()
        self._fg_btn.setObjectName("colorBtn")
        self._fg_btn.setStyleSheet(f"background:{self._fg_color};")
        self._fg_btn.clicked.connect(lambda: self._pick_color("fg"))
        fg_row = QHBoxLayout()
        fg_row.addWidget(self._fg_btn)
        self._fg_lbl = QLabel(self._fg_color)
        fg_row.addWidget(self._fg_lbl)
        fg_row.addStretch()
        form.addRow("Foreground:", fg_row)

        self._bg_color = td.background_color
        self._bg_btn = QPushButton()
        self._bg_btn.setObjectName("colorBtn")
        self._bg_btn.setStyleSheet(f"background:{self._bg_color};")
        self._bg_btn.clicked.connect(lambda: self._pick_color("bg"))
        bg_row = QHBoxLayout()
        bg_row.addWidget(self._bg_btn)
        self._bg_lbl = QLabel(self._bg_color)
        bg_row.addWidget(self._bg_lbl)
        bg_row.addStretch()
        form.addRow("Background:", bg_row)
        vbox.addWidget(grp)

        # Stroke
        grp2, form2 = _grp("Stroke & Font")

        lw_sl, self._line_width = _slider_row(1, 50, td.line_width, " px")
        lw_row = QHBoxLayout()
        lw_row.addWidget(lw_sl, 1)
        lw_row.addWidget(self._line_width)
        form2.addRow("Line width:", lw_row)

        self._font_family = QFontComboBox()
        self._font_family.setCurrentFont(QFont(td.font_family))
        form2.addRow("Font family:", self._font_family)

        fs_sl, self._font_size = _slider_row(6, 120, td.font_size, " pt")
        fs_row = QHBoxLayout()
        fs_row.addWidget(fs_sl, 1)
        fs_row.addWidget(self._font_size)
        form2.addRow("Font size:", fs_row)
        vbox.addWidget(grp2)

        # Shadow defaults
        grp3, form3 = _grp("Default Shadow")
        self._sh_offset_x = QDoubleSpinBox()
        self._sh_offset_x.setRange(-50, 50)
        self._sh_offset_x.setSingleStep(0.5)
        self._sh_offset_x.setValue(getattr(self._s, 'shadow_default_offset_x', 3.0))
        self._sh_offset_x.setSuffix(" px")
        form3.addRow("Offset X:", self._sh_offset_x)

        self._sh_offset_y = QDoubleSpinBox()
        self._sh_offset_y.setRange(-50, 50)
        self._sh_offset_y.setSingleStep(0.5)
        self._sh_offset_y.setValue(getattr(self._s, 'shadow_default_offset_y', 3.0))
        self._sh_offset_y.setSuffix(" px")
        form3.addRow("Offset Y:", self._sh_offset_y)

        self._sh_blur_x = QDoubleSpinBox()
        self._sh_blur_x.setRange(0, 50)
        self._sh_blur_x.setSingleStep(0.5)
        self._sh_blur_x.setValue(getattr(self._s, 'shadow_default_blur_x', 5.0))
        self._sh_blur_x.setSuffix(" px")
        form3.addRow("Blur X:", self._sh_blur_x)

        self._sh_blur_y = QDoubleSpinBox()
        self._sh_blur_y.setRange(0, 50)
        self._sh_blur_y.setSingleStep(0.5)
        self._sh_blur_y.setValue(getattr(self._s, 'shadow_default_blur_y', 5.0))
        self._sh_blur_y.setSuffix(" px")
        form3.addRow("Blur Y:", self._sh_blur_y)
        vbox.addWidget(grp3)

        # Tool memory
        grp4, form4 = _grp("Tool Memory")
        saved = self._s.tool_properties
        count = len(saved)
        mem_lbl = QLabel(
            f"{count} tool(s) have saved properties: {', '.join(saved.keys())}"
            if count else "No saved tool properties yet."
        )
        mem_lbl.setWordWrap(True)
        form4.addRow("", mem_lbl)
        note = QLabel("Use 'Reset tool memory' (bottom-left) to clear all saved tool state.")
        note.setObjectName("sub")
        note.setWordWrap(True)
        form4.addRow("", note)
        vbox.addWidget(grp4)

        vbox.addStretch()
        return _scroll(inner)

    def _build_behavior(self) -> QWidget:
        inner, vbox = _page()

        vbox.addWidget(QLabel("Behavior", objectName="heading"))
        vbox.addSpacing(4)
        vbox.addWidget(QLabel("Control how the editor and capture flow behave.", objectName="sub"))

        # ── Capture behavior ──────────────────────────────────────────────────
        grp, form = _grp("Capture")

        self._hide_before_capture = QPushButton(
            "Hide editor window before taking a new screenshot")
        self._hide_before_capture.setObjectName("toggleSetting")
        self._hide_before_capture.setCheckable(True)
        self._hide_before_capture.setChecked(
            getattr(self._s, 'hide_editor_before_capture', True))
        self._hide_before_capture.setToolTip(
            "When you trigger a new capture, the editor hides first so it doesn't appear in the screenshot.")
        form.addRow("", self._hide_before_capture)
        vbox.addWidget(grp)

        # ── Editor behavior ───────────────────────────────────────────────────
        grp2, form2 = _grp("Editor")

        self._confirm_close = QPushButton(
            "Ask before closing with unsaved annotations")
        self._confirm_close.setObjectName("toggleSetting")
        self._confirm_close.setCheckable(True)
        self._confirm_close.setChecked(
            getattr(self._s, 'confirm_close_unsaved', True))
        self._confirm_close.setToolTip(
            "Show a confirmation dialog when closing the editor with unannotated/unsaved work.")
        form2.addRow("", self._confirm_close)
        vbox.addWidget(grp2)

        # ── Canvas background ─────────────────────────────────────────────────
        grp3, form3 = _grp("Canvas Background")
        note3 = QLabel("Color shown around the captured image when zoomed out.")
        note3.setObjectName("sub")
        note3.setWordWrap(True)
        form3.addRow("", note3)

        self._canvas_bg = getattr(self._s, 'canvas_background', 'dark')
        self._bg_radio_grp = QButtonGroup(self)

        _bg_options = [
            ("dark",          "Dark  (default)"),
            ("checkerboard",  "Checkerboard  (transparency grid)"),
            ("system",        "System window color"),
        ]
        for value, label in _bg_options:
            rb = QRadioButton(label)
            rb.setStyleSheet("color: #ccc; font-size: 12px;")
            rb.setChecked(self._canvas_bg == value)
            rb.toggled.connect(lambda checked, v=value: self._on_canvas_bg_changed(v) if checked else None)
            self._bg_radio_grp.addButton(rb)
            form3.addRow("", rb)

        # Custom color row
        custom_row = QHBoxLayout()
        self._custom_bg_rb = QRadioButton("Custom color:")
        self._custom_bg_rb.setStyleSheet("color: #ccc; font-size: 12px;")
        is_custom = self._canvas_bg not in ('dark', 'checkerboard', 'system')
        self._custom_bg_rb.setChecked(is_custom)
        self._bg_radio_grp.addButton(self._custom_bg_rb)
        custom_row.addWidget(self._custom_bg_rb)

        self._custom_bg_btn = QPushButton()
        self._custom_bg_btn.setObjectName("colorBtn")
        custom_color = self._canvas_bg if is_custom else "#2a2a3e"
        self._custom_bg_btn.setStyleSheet(f"background:{custom_color};")
        self._custom_bg_btn.setEnabled(is_custom)
        self._custom_bg_btn.clicked.connect(self._pick_canvas_bg_color)
        custom_row.addWidget(self._custom_bg_btn)
        custom_row.addStretch()

        self._custom_bg_rb.toggled.connect(
            lambda checked: self._on_canvas_bg_changed(
                getattr(self, '_custom_bg_color', '#2a2a3e')) if checked else None)
        self._custom_bg_rb.toggled.connect(self._custom_bg_btn.setEnabled)
        self._custom_bg_color = custom_color

        form3.addRow("", self._wrap_row(custom_row))
        vbox.addWidget(grp3)

        vbox.addStretch()
        return _scroll(inner)

    def _wrap_row(self, layout: QHBoxLayout) -> QWidget:
        w = QWidget()
        w.setLayout(layout)
        return w

    def _on_canvas_bg_changed(self, value: str):
        self._canvas_bg = value

    def _pick_canvas_bg_color(self):
        c = QColorDialog.getColor(QColor(self._custom_bg_color), self, "Canvas Background Color")
        if c.isValid():
            self._custom_bg_color = c.name()
            self._custom_bg_btn.setStyleSheet(f"background:{self._custom_bg_color};")
            self._canvas_bg = self._custom_bg_color

    def _build_shortcuts(self) -> QWidget:
        inner, vbox = _page()

        vbox.addWidget(QLabel("Shortcuts", objectName="heading"))
        vbox.addSpacing(4)
        vbox.addWidget(QLabel("Keyboard shortcuts. Changes take effect after restart.", objectName="sub"))

        grp, form = _grp("Global")
        self._hk_fields: dict[str, QLineEdit] = {}
        hk = self._s.hotkeys
        for name, label, hint in [
            ("capture",        "Capture screen",     "e.g. PrintScreen"),
            ("undo",           "Undo",               "Ctrl+Z"),
            ("redo",           "Redo",               "Ctrl+Y"),
            ("save",           "Save",               "Ctrl+S"),
            ("save_as",        "Save As",            "Ctrl+Shift+S"),
            ("copy_clipboard", "Copy to clipboard",  "Ctrl+C"),
            ("delete",         "Delete selected",    "Delete"),
            ("select_all",     "Select all",         "Ctrl+A"),
        ]:
            field = QLineEdit(getattr(hk, name, ""))
            field.setPlaceholderText(hint)
            self._hk_fields[name] = field
            form.addRow(f"{label}:", field)
        vbox.addWidget(grp)

        grp2, form2 = _grp("Editor (fixed)")
        for label, keys in [
            ("Undo / Redo",          ["Ctrl+Z", "Ctrl+Y"]),
            ("Zoom in / out",        ["Ctrl+=", "Ctrl+−"]),
            ("Zoom reset",           ["Ctrl+0"]),
            ("Pan",                  ["Middle-click drag"]),
            ("Finalize text",        ["Ctrl+Enter"]),
            ("Multi-select",         ["Shift+click", "Rubber-band"]),
            ("Delete selected",      ["Delete"]),
            ("Precision move",       ["Arrow keys", "+Shift ×10"]),
            ("Z-order front/back",   ["Ctrl+]", "Ctrl+["]),
            ("Z-order up/down",      ["Ctrl+Shift+]", "Ctrl+Shift+["]),
            ("Copy / Paste",         ["Ctrl+C", "Ctrl+V"]),
        ]:
            badge_row = QHBoxLayout()
            badge_row.setSpacing(4)
            badge_row.setContentsMargins(0, 0, 0, 0)
            for k in keys:
                badge = QLabel(k)
                badge.setObjectName("keyBadge")
                badge_row.addWidget(badge)
            badge_row.addStretch()
            badge_w = QWidget()
            badge_w.setLayout(badge_row)
            form2.addRow(f"{label}:", badge_w)
        vbox.addWidget(grp2)

        vbox.addStretch()
        return _scroll(inner)

    def _build_presets(self) -> QWidget:
        inner, vbox = _page()

        vbox.addWidget(QLabel("Presets", objectName="heading"))
        vbox.addSpacing(4)
        vbox.addWidget(QLabel("Built-in annotation style presets. Applied from the toolbar palette button.", objectName="sub"))

        from paparaz.ui.theme_presets import PRESETS, PRESET_ORDER, _draw_preview
        for pid in PRESET_ORDER:
            preset = PRESETS[pid]
            grp = QGroupBox(f"{preset.category.upper()}  ·  {preset.name}  —  {preset.tagline}")
            row = QHBoxLayout(grp)
            row.setSpacing(16)

            pix_lbl = QLabel()
            pix_lbl.setPixmap(_draw_preview(preset, 120, 72))
            pix_lbl.setFixedSize(120, 72)
            row.addWidget(pix_lbl)

            detail = QVBoxLayout()
            detail.setSpacing(3)
            for label, value in [
                ("Line width", f"{preset.line_width} px"),
                ("Opacity", f"{preset.opacity:.0%}"),
                ("Font", f"{preset.font_family} {preset.font_size}pt"),
                ("Shadow", f"{'On' if preset.shadow_enabled else 'Off'}  "
                           f"offset ({preset.shadow_offset_x:.0f}, {preset.shadow_offset_y:.0f})  "
                           f"blur {preset.shadow_blur:.0f}px"),
            ]:
                l = QLabel(f"<span style='color:#555;'>{label}:</span> "
                           f"<span style='color:#aaa;'>{value}</span>")
                l.setTextFormat(Qt.TextFormat.RichText)
                l.setStyleSheet("font-size:11px;")
                detail.addWidget(l)

            for hex_c in [preset.fg_color, preset.bg_color, preset.text_bg_color]:
                c = QColor(hex_c)
                swatches_row = QHBoxLayout() if hex_c == preset.fg_color else None
                if swatches_row:
                    for hc in [preset.fg_color, preset.bg_color, preset.text_bg_color]:
                        cc = QColor(hc)
                        sw = QLabel()
                        swpix = QPixmap(14, 14)
                        swpix.fill(cc)
                        sw.setPixmap(swpix)
                        sw.setFixedSize(16, 16)
                        sw.setToolTip(hc)
                        swatches_row.addWidget(sw)
                    swatches_row.addStretch()
                    detail.addLayout(swatches_row)
                break

            row.addLayout(detail)
            row.addStretch()
            vbox.addWidget(grp)

        vbox.addStretch()
        return _scroll(inner)

    def _build_updates(self) -> QWidget:
        inner, vbox = _page()

        vbox.addWidget(QLabel("Updates", objectName="heading"))
        vbox.addSpacing(4)

        from paparaz.utils.updater import __version__
        ver_lbl = QLabel(f"Current version:  v{__version__}", objectName="version")
        vbox.addWidget(ver_lbl)
        vbox.addSpacing(8)

        grp, form = _grp("Update Checking")
        self._auto_update = QPushButton("Check for updates automatically on startup")
        self._auto_update.setObjectName("toggleSetting")
        self._auto_update.setCheckable(True)
        self._auto_update.setChecked(getattr(self._s, 'auto_check_updates', True))
        form.addRow("", self._auto_update)

        check_now_btn = QPushButton("Check Now")
        check_now_btn.setFixedWidth(130)
        check_now_btn.clicked.connect(self._check_now)
        form.addRow("", check_now_btn)
        vbox.addWidget(grp)

        grp2, form2 = _grp("System")
        from paparaz.utils.startup import get_start_on_login
        self._start_login = QPushButton("Launch PapaRaZ at Windows login")
        self._start_login.setObjectName("toggleSetting")
        self._start_login.setCheckable(True)
        self._start_login.setChecked(get_start_on_login())
        form2.addRow("", self._start_login)
        vbox.addWidget(grp2)

        vbox.addStretch()
        return _scroll(inner)

    def _build_about(self) -> QWidget:
        inner, vbox = _page()

        title = QLabel("PapaRaZ", objectName="heading")
        f = title.font()
        f.setPointSize(22)
        f.setBold(True)
        title.setFont(f)
        title.setStyleSheet("color: #740096;")
        vbox.addWidget(title)

        from paparaz.utils.updater import __version__
        vbox.addWidget(QLabel(f"Version {__version__}  ·  Screen Capture & Annotation for Windows"))
        vbox.addSpacing(16)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        website_btn = QPushButton("🌐  Website")
        website_btn.setObjectName("secondary")
        website_btn.setFixedHeight(34)
        website_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://github.com/aleled/paparaz")))
        btn_row.addWidget(website_btn)

        updates_btn = QPushButton("🔄  Check for Updates")
        updates_btn.setFixedHeight(34)
        updates_btn.clicked.connect(self._check_now)
        btn_row.addWidget(updates_btn)

        issues_btn = QPushButton("🐛  Report Issue")
        issues_btn.setObjectName("secondary")
        issues_btn.setFixedHeight(34)
        issues_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://github.com/aleled/paparaz/issues")))
        btn_row.addWidget(issues_btn)
        btn_row.addStretch()

        btn_row_w = QWidget()
        btn_row_w.setLayout(btn_row)
        vbox.addWidget(btn_row_w)
        vbox.addSpacing(12)
        vbox.addWidget(_sep())
        vbox.addSpacing(8)

        for label, value in [
            ("Author",  "<b>Alejandro Lichtenfeld</b>"),
            ("License", "MIT License"),
        ]:
            lbl = QLabel(f"<span style='color:#555;'>{label}:</span>  {value}")
            lbl.setTextFormat(Qt.TextFormat.RichText)
            vbox.addWidget(lbl)

        vbox.addSpacing(12)
        vbox.addWidget(_sep())
        vbox.addSpacing(8)

        vbox.addWidget(QLabel("Built with:"))
        for line in [
            "Python 3.11+",
            "PySide6 (Qt 6) — GUI framework",
            "Win32 API via ctypes — DPI-aware capture & global hotkeys",
            "winrt — Windows OCR integration",
            "Pillow — image processing & icon generation",
            "PyInstaller — Windows executable packaging",
        ]:
            lbl = QLabel(f"  · {line}")
            lbl.setStyleSheet("color: #666; font-size: 11px;")
            vbox.addWidget(lbl)

        vbox.addSpacing(12)
        vbox.addWidget(_sep())
        vbox.addSpacing(8)

        ack = QLabel(
            "PapaRaZ is an independent screen-capture and annotation tool built from scratch "
            "in Python with PySide6. MIT License."
        )
        ack.setWordWrap(True)
        ack.setStyleSheet("color: #555; font-size: 11px;")
        vbox.addWidget(ack)

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

    def _browse_save_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Select Save Directory")
        if d:
            self._save_dir.setText(d)

    def _pick_color(self, which: str):
        current = self._fg_color if which == "fg" else self._bg_color
        color = QColorDialog.getColor(QColor(current), self)
        if color.isValid():
            if which == "fg":
                self._fg_color = color.name()
                self._fg_btn.setStyleSheet(f"background:{self._fg_color};")
                self._fg_lbl.setText(self._fg_color)
            else:
                self._bg_color = color.name()
                self._bg_btn.setStyleSheet(f"background:{self._bg_color};")
                self._bg_lbl.setText(self._bg_color)

    def _reset_tool_memory(self):
        self._s.tool_properties.clear()
        self._sm.save()
        self.setWindowTitle("Settings  —  PapaRaZ  [Tool memory cleared]")

    def _check_now(self):
        from paparaz.utils.updater import check_for_updates_manual
        check_for_updates_manual(parent=self)

    def _select_theme(self, theme_id: str):
        """Called when user clicks a theme card — live-preview it."""
        self._selected_theme = theme_id
        for tid, btn in self._theme_btns.items():
            btn.setChecked(tid == theme_id)
        self._on_theme_preview()

    def _on_theme_preview(self):
        """Live-preview the chosen theme: re-style this dialog and the editor."""
        theme_id = self._selected_theme
        if not theme_id:
            return
        theme = get_theme(theme_id)
        self.setStyleSheet(_BASE + build_dialog_qss(theme) + combo_arrow_css())
        if self.parent() and hasattr(self.parent(), 'apply_app_theme'):
            self.parent().apply_app_theme(theme_id)

    # -----------------------------------------------------------------------
    # Save
    # -----------------------------------------------------------------------

    def _save_and_close(self):
        s = self._s

        # Capture
        s.save_directory         = self._save_dir.text()
        s.default_format         = self._format_combo.currentText()
        s.jpg_quality            = self._jpg_quality.value()
        s.filename_pattern       = self._fn_pattern_widget.get_pattern()
        s.subfolder_pattern      = self._subfolder_edit.text()
        s.auto_save              = self._auto_save_check.isChecked()
        s.save_counter           = self._counter_spin.value()
        s.show_tray_notification = self._tray_notify.isChecked()

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

        # Behavior
        s.hide_editor_before_capture = self._hide_before_capture.isChecked()
        s.confirm_close_unsaved      = self._confirm_close.isChecked()
        s.canvas_background          = self._canvas_bg

        # Shortcuts
        for name, field in self._hk_fields.items():
            setattr(s.hotkeys, name, field.text())

        # Updates / System
        s.auto_check_updates = self._auto_update.isChecked()
        s.start_on_login     = self._start_login.isChecked()
        from paparaz.utils.startup import set_start_on_login
        set_start_on_login(s.start_on_login)

        self._sm.save()

        # Apply theme and tray icon immediately
        if self.parent() and hasattr(self.parent(), 'apply_app_theme'):
            self.parent().apply_app_theme(s.app_theme)
        # Update tray icon color via app
        root = self.parent()
        while root and root.parent():
            root = root.parent()
        if root and hasattr(root, '_tray'):
            root._tray.set_icon_color(s.tray_icon_color)

        self.accept()
