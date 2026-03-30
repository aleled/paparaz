"""Settings dialog — modern sidebar navigation."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QWidget, QLabel, QLineEdit, QSpinBox, QDoubleSpinBox,
    QCheckBox, QComboBox, QPushButton, QFileDialog,
    QColorDialog, QGroupBox, QScrollArea, QFrame,
    QListWidget, QListWidgetItem, QStackedWidget, QSizePolicy,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QFont, QIcon, QPixmap, QPainter

from paparaz.core.settings import SettingsManager
from paparaz.ui.icons import combo_arrow_css
from paparaz.ui.app_theme import APP_THEMES, get_theme, build_dialog_qss

# ---------------------------------------------------------------------------
# Stylesheet
# ---------------------------------------------------------------------------

_BASE = """
QDialog { background: #13131f; color: #ddd; font-size: 12px; }

/* Sidebar */
QListWidget {
    background: #1a1a2e; border: none; border-right: 1px solid #2a2a45;
    outline: 0; font-size: 12px; color: #aaa;
}
QListWidget::item {
    padding: 10px 14px; border-radius: 0;
}
QListWidget::item:selected {
    background: #2a1040; color: #fff; border-left: 3px solid #740096;
}
QListWidget::item:hover:!selected { background: #1e1e38; color: #ccc; }

/* Content area */
QScrollArea { border: none; background: transparent; }
QWidget#page { background: transparent; }

/* Groups */
QGroupBox {
    color: #666; font-size: 10px; font-weight: bold; letter-spacing: 1px;
    border: none; border-top: 1px solid #2a2a45;
    margin-top: 18px; padding-top: 14px;
}
QGroupBox::title {
    subcontrol-origin: margin; left: 0; top: -1px;
    padding: 0 6px 0 0; color: #555;
}

/* Inputs */
QLineEdit, QSpinBox, QComboBox, QDoubleSpinBox {
    background: #1e1e38; color: #ddd; border: 1px solid #2e2e50;
    border-radius: 5px; padding: 5px 9px; min-height: 26px; font-size: 12px;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QDoubleSpinBox:focus {
    border-color: #740096; background: #221030;
}
QComboBox::drop-down { border: none; width: 22px; }
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    background: #2a2a45; border: none; border-radius: 2px; width: 16px;
}

/* Checkboxes */
QCheckBox { color: #ccc; spacing: 8px; }
QCheckBox::indicator {
    width: 16px; height: 16px; border: 1px solid #444; border-radius: 4px; background: #1e1e38;
}
QCheckBox::indicator:checked { background: #740096; border-color: #740096; }

/* Buttons */
QPushButton {
    background: #740096; color: white; border: none;
    border-radius: 5px; padding: 7px 20px; font-weight: bold; font-size: 12px;
}
QPushButton:hover  { background: #9e2ac0; }
QPushButton:pressed { background: #5a0074; }

QPushButton#secondary {
    background: #1e1e38; color: #aaa; border: 1px solid #2e2e50;
    padding: 7px 16px; font-weight: normal;
}
QPushButton#secondary:hover { background: #262645; color: #ddd; }

QPushButton#danger {
    background: #3a0a0a; color: #ff8080; border: 1px solid #6b1010;
    padding: 7px 16px; font-weight: normal;
}
QPushButton#danger:hover { background: #5a1010; color: #ffaaaa; }

QPushButton#colorBtn {
    min-width: 28px; max-width: 28px; min-height: 24px; max-height: 24px;
    border: 2px solid #444; border-radius: 4px; padding: 0;
}
QPushButton#colorBtn:hover { border-color: #888; }

QPushButton#iconBtn {
    background: #1e1e38; border: 2px solid #2e2e50;
    border-radius: 6px; padding: 4px;
}
QPushButton#iconBtn:checked, QPushButton#iconBtn:hover { border-color: #740096; }

/* Labels */
QLabel { color: #ccc; font-size: 12px; }
QLabel#heading { color: #fff; font-size: 16px; font-weight: bold; }
QLabel#sub { color: #666; font-size: 11px; }
QLabel#version { color: #740096; font-size: 13px; font-weight: bold; }

/* Bottom bar */
QFrame#bottomBar { background: #1a1a2e; border-top: 1px solid #2a2a45; }
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
        # Build stylesheet: use the currently saved app theme, falling back to _BASE
        theme = get_theme(settings_manager.settings.app_theme)
        self.setStyleSheet(build_dialog_qss(theme) + combo_arrow_css())

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

        sections = [
            ("📸", "Capture"),
            ("🎨", "Appearance"),
            ("✏️", "Tools"),
            ("⌨️", "Shortcuts"),
            ("🎭", "Presets"),
            ("🔄", "Updates"),
            ("ℹ️",  "About"),
        ]
        for icon, label in sections:
            item = QListWidgetItem(f"  {icon}  {label}")
            item.setSizeHint(QSize(180, 42))
            self._nav.addItem(item)

        self._nav.currentRowChanged.connect(self._switch_page)

        # --- Stack ---
        self._stack = QStackedWidget()
        self._pages = [
            self._build_capture(),
            self._build_appearance(),
            self._build_tools(),
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
        self._tray_notify = QCheckBox("Show tray notification when ready")
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

        self._auto_save_check = QCheckBox("Auto-save silently (Ctrl+Shift+S skips dialog)")
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

        # UI Theme
        grp, form = _grp("UI Theme")
        self._theme_combo = QComboBox()
        for tid, tdata in APP_THEMES.items():
            self._theme_combo.addItem(tdata["name"], tid)
        idx = self._theme_combo.findData(getattr(self._s, 'app_theme', 'dark'))
        if idx >= 0:
            self._theme_combo.setCurrentIndex(idx)
        self._theme_combo.currentIndexChanged.connect(self._on_theme_preview)
        form.addRow("App theme:", self._theme_combo)
        vbox.addWidget(grp)

        # Tray icon color
        grp2, form2 = _grp("Tray Icon")
        from paparaz.ui.tray import TRAY_ICON_COLORS
        self._tray_color = getattr(self._s, 'tray_icon_color', '#E53935')
        icon_row = QHBoxLayout()
        icon_row.setSpacing(8)
        self._icon_btns: dict[str, QPushButton] = {}
        for hex_color, name in TRAY_ICON_COLORS.items():
            btn = QPushButton()
            btn.setObjectName("iconBtn")
            btn.setCheckable(True)
            btn.setFixedSize(36, 36)
            btn.setToolTip(name)
            pix = QPixmap(24, 24)
            pix.fill(QColor(hex_color))
            btn.setIcon(QIcon(pix))
            btn.setIconSize(QSize(22, 22))
            btn.setChecked(hex_color == self._tray_color)
            btn.clicked.connect(lambda checked, c=hex_color: self._select_icon_color(c))
            icon_row.addWidget(btn)
            self._icon_btns[hex_color] = btn
        icon_row.addStretch()
        self._tray_color_lbl = QLabel(TRAY_ICON_COLORS.get(self._tray_color, ''))
        self._tray_color_lbl.setObjectName("sub")
        icon_row.addWidget(self._tray_color_lbl)
        form2.addRow("Icon color:", icon_row)
        vbox.addWidget(grp2)

        # Default annotation theme preset
        grp3, form3 = _grp("Default Annotation Preset")
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
        form3.addRow("Preset:", self._theme_preset_combo)
        note = QLabel("Applied automatically when the editor opens.")
        note.setObjectName("sub")
        form3.addRow("", note)
        vbox.addWidget(grp3)

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
        self._line_width = QSpinBox()
        self._line_width.setRange(1, 50)
        self._line_width.setValue(td.line_width)
        self._line_width.setSuffix(" px")
        form2.addRow("Line width:", self._line_width)

        self._font_family = QLineEdit(td.font_family)
        form2.addRow("Font family:", self._font_family)

        self._font_size = QSpinBox()
        self._font_size.setRange(6, 120)
        self._font_size.setValue(td.font_size)
        self._font_size.setSuffix(" pt")
        form2.addRow("Font size:", self._font_size)
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

        self._sh_blur = QDoubleSpinBox()
        self._sh_blur.setRange(0, 50)
        self._sh_blur.setSingleStep(0.5)
        self._sh_blur.setValue(getattr(self._s, 'shadow_default_blur', 5.0))
        self._sh_blur.setSuffix(" px")
        form3.addRow("Blur radius:", self._sh_blur)
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
        ]:
            field = QLineEdit(getattr(hk, name, ""))
            field.setPlaceholderText(hint)
            self._hk_fields[name] = field
            form.addRow(f"{label}:", field)
        vbox.addWidget(grp)

        grp2, form2 = _grp("Editor (fixed)")
        for label, keys in [
            ("Undo / Redo",          "Ctrl+Z / Ctrl+Y"),
            ("Zoom in / out",        "Ctrl+= / Ctrl+−"),
            ("Zoom reset",           "Ctrl+0"),
            ("Pan",                  "Middle-click drag"),
            ("Finalize text",        "Ctrl+Enter"),
            ("Multi-select",         "Shift+click / Rubber-band"),
            ("Delete selected",      "Delete"),
            ("Z-order front/back",   "Ctrl+] / Ctrl+["),
            ("Z-order up/down",      "Ctrl+Shift+] / Ctrl+Shift+["),
            ("Copy / Paste",         "Ctrl+C / Ctrl+V"),
        ]:
            lbl = QLabel(keys)
            lbl.setStyleSheet("color:#888; font-size:11px;")
            form2.addRow(f"{label}:", lbl)
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
        self._auto_update = QCheckBox("Check for updates automatically on startup")
        self._auto_update.setChecked(getattr(self._s, 'auto_check_updates', True))
        form.addRow("", self._auto_update)

        check_now_btn = QPushButton("Check Now")
        check_now_btn.setFixedWidth(130)
        check_now_btn.clicked.connect(self._check_now)
        form.addRow("", check_now_btn)
        vbox.addWidget(grp)

        grp2, form2 = _grp("System")
        from paparaz.utils.startup import get_start_on_login
        self._start_login = QCheckBox("Launch PapaRaZ at Windows login")
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
            "Inspired by <a href='https://flameshot.org' style='color:#740096;'>Flameshot</a> (GPLv3). "
            "PapaRaZ is an independent Python/PySide6 reimplementation — "
            "no Flameshot source code was copied or adapted."
        )
        ack.setOpenExternalLinks(True)
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

    def _on_theme_preview(self):
        """Live-preview the chosen theme: re-style this dialog and the editor."""
        theme_id = self._theme_combo.currentData()
        if not theme_id:
            return
        theme = get_theme(theme_id)
        self.setStyleSheet(build_dialog_qss(theme) + combo_arrow_css())
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
        s.app_theme              = self._theme_combo.currentData()
        s.tray_icon_color        = self._tray_color
        s.default_theme_preset   = self._theme_preset_combo.currentData() or ""

        # Tools
        s.tool_defaults.foreground_color = self._fg_color
        s.tool_defaults.background_color = self._bg_color
        s.tool_defaults.line_width       = self._line_width.value()
        s.tool_defaults.font_family      = self._font_family.text()
        s.tool_defaults.font_size        = self._font_size.value()
        s.shadow_default_offset_x        = self._sh_offset_x.value()
        s.shadow_default_offset_y        = self._sh_offset_y.value()
        s.shadow_default_blur            = self._sh_blur.value()

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
