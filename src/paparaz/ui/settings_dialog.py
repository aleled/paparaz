"""Settings dialog for PapaRaZ — General, Hotkeys, Tools, About."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QTabWidget,
    QWidget, QLabel, QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox, QComboBox,
    QPushButton, QFileDialog, QColorDialog, QGroupBox, QScrollArea,
    QFrame, QInputDialog, QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont

from paparaz.core.settings import SettingsManager
from paparaz.ui.icons import combo_arrow_css
from paparaz.ui.app_theme import APP_THEMES

DIALOG_STYLE = """
QDialog { background: #1a1a2e; color: #ddd; font-size: 12px; }
QScrollArea { border: none; background: #1a1a2e; }
QTabWidget::pane { border: 1px solid #3a3a5e; background: #1a1a2e; border-radius: 0 4px 4px 4px; }
QTabBar::tab {
    background: #252538; color: #888; padding: 8px 18px;
    border: 1px solid #3a3a5e; border-bottom: none; border-radius: 4px 4px 0 0;
    min-width: 80px; font-size: 12px;
}
QTabBar::tab:selected { background: #1a1a2e; color: #fff; border-bottom: 1px solid #1a1a2e; }
QTabBar::tab:hover:!selected { background: #2e2e4e; color: #bbb; }
QGroupBox {
    color: #888; font-size: 12px; font-weight: bold; letter-spacing: 0.5px;
    border: 1px solid #3a3a5e; border-radius: 6px;
    margin-top: 10px; padding: 12px 8px 8px 8px;
}
QGroupBox::title { subcontrol-origin: margin; left: 10px; top: -1px; padding: 0 4px; }
QLineEdit, QSpinBox, QComboBox, QDoubleSpinBox {
    background: #252538; color: #ddd; border: 1px solid #3a3a5e;
    border-radius: 4px; padding: 5px 8px; min-height: 24px; font-size: 12px;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QDoubleSpinBox:focus { border-color: #740096; }
QCheckBox { color: #ccc; spacing: 8px; font-size: 12px; }
QCheckBox::indicator {
    width: 16px; height: 16px; border: 1px solid #555;
    border-radius: 3px; background: #252538;
}
QCheckBox::indicator:checked { background: #740096; border-color: #740096; }
QPushButton {
    background: #740096; color: white; border: none;
    border-radius: 5px; padding: 8px 22px; font-weight: bold; font-size: 12px;
}
QPushButton:hover { background: #9e2ac0; }
QPushButton:pressed { background: #5a0074; }
QPushButton#secondary {
    background: #252538; color: #aaa; border: 1px solid #3a3a5e;
    padding: 8px 18px; font-weight: normal; font-size: 12px;
}
QPushButton#secondary:hover { background: #2e2e4e; color: #ddd; }
QPushButton#danger {
    background: #6b1010; color: #ffaaaa; border: 1px solid #aa3333; font-size: 12px;
}
QPushButton#danger:hover { background: #8b1818; color: #fff; }
QPushButton#colorBtn {
    min-width: 28px; max-width: 28px; min-height: 24px; max-height: 24px;
    border: 2px solid #555; border-radius: 4px; padding: 0;
}
QPushButton#colorBtn:hover { border-color: #999; }
QLabel { color: #ccc; font-size: 12px; }
QLabel#heading { color: #fff; font-size: 15px; font-weight: bold; }
QLabel#subheading { color: #888; font-size: 12px; }
QFrame#separator { color: #3a3a5e; }
"""


def _sep() -> QFrame:
    f = QFrame()
    f.setObjectName("separator")
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet("color: #3a3a5e;")
    return f


class SettingsDialog(QDialog):
    """Enhanced settings dialog — always on top, per-tool reset, author info."""

    def __init__(self, settings_manager: SettingsManager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PapaRaZ — Settings")
        self.setMinimumSize(540, 520)
        self.setStyleSheet(DIALOG_STYLE + combo_arrow_css())
        # Always appear above the editor canvas
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self._sm = settings_manager
        self._s = settings_manager.settings

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        tabs = QTabWidget()
        layout.addWidget(tabs, 1)

        tabs.addTab(self._build_general_tab(), "General")
        tabs.addTab(self._build_hotkeys_tab(), "Hotkeys")
        tabs.addTab(self._build_tools_tab(), "Tools")
        tabs.addTab(self._build_presets_tab(), "Presets")
        tabs.addTab(self._build_about_tab(), "About")

        # Button row
        btn_row = QHBoxLayout()
        reset_btn = QPushButton("Reset Tools to Default")
        reset_btn.setObjectName("danger")
        reset_btn.setToolTip("Clear all saved per-tool property memory")
        reset_btn.clicked.connect(self._reset_all_tool_properties)
        btn_row.addWidget(reset_btn)
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondary")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save_and_close)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    # -----------------------------------------------------------------------

    def _build_general_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        vbox = QVBoxLayout(inner)
        vbox.setSpacing(12)
        vbox.setContentsMargins(8, 8, 8, 8)

        # Save location group
        save_grp = QGroupBox("SAVE LOCATION")
        save_form = QFormLayout(save_grp)
        save_form.setSpacing(8)
        dir_row = QHBoxLayout()
        self._save_dir = QLineEdit(self._s.save_directory or "")
        self._save_dir.setPlaceholderText("Default: user home directory")
        dir_row.addWidget(self._save_dir, 1)
        browse_btn = QPushButton("…")
        browse_btn.setObjectName("secondary")
        browse_btn.setMaximumWidth(36)
        browse_btn.clicked.connect(self._browse_save_dir)
        dir_row.addWidget(browse_btn)
        save_form.addRow("Directory:", dir_row)

        self._format_combo = QComboBox()
        self._format_combo.addItems(["png", "jpg", "svg"])
        self._format_combo.setCurrentText(self._s.default_format)
        save_form.addRow("Default format:", self._format_combo)

        self._jpg_quality = QSpinBox()
        self._jpg_quality.setRange(10, 100)
        self._jpg_quality.setValue(self._s.jpg_quality)
        self._jpg_quality.setSuffix("%")
        save_form.addRow("JPG quality:", self._jpg_quality)
        vbox.addWidget(save_grp)

        # Behavior group
        behavior_grp = QGroupBox("BEHAVIOR")
        beh_form = QFormLayout(behavior_grp)
        beh_form.setSpacing(8)

        self._start_login = QCheckBox("Launch PapaRaZ at Windows login")
        from paparaz.utils.startup import get_start_on_login
        self._start_login.setChecked(get_start_on_login())
        beh_form.addRow("", self._start_login)

        self._tray_notify = QCheckBox("Show notification when ready")
        self._tray_notify.setChecked(self._s.show_tray_notification)
        beh_form.addRow("", self._tray_notify)

        self._delay_spin = QSpinBox()
        self._delay_spin.setRange(0, 30)
        self._delay_spin.setValue(getattr(self._s, 'capture_delay', 0))
        self._delay_spin.setSuffix(" sec")
        self._delay_spin.setSpecialValueText("No delay")
        beh_form.addRow("Capture delay:", self._delay_spin)
        vbox.addWidget(behavior_grp)

        # Theme preset group
        theme_grp = QGroupBox("DEFAULT THEME PRESET")
        theme_form = QFormLayout(theme_grp)
        theme_form.setSpacing(8)

        from paparaz.ui.theme_presets import PRESETS, PRESET_ORDER
        self._theme_preset_combo = QComboBox()
        self._theme_preset_combo.addItem("— None —", "")
        for pid in PRESET_ORDER:
            p = PRESETS[pid]
            self._theme_preset_combo.addItem(f"{p.category.capitalize()} · {p.name} — {p.tagline}", pid)
        current_pid = getattr(self._s, 'default_theme_preset', "")
        for i in range(self._theme_preset_combo.count()):
            if self._theme_preset_combo.itemData(i) == current_pid:
                self._theme_preset_combo.setCurrentIndex(i)
                break
        theme_form.addRow("Default preset:", self._theme_preset_combo)

        note = QLabel("Applied automatically when the editor opens. Can also be changed live from the toolbar palette button.")
        note.setObjectName("subheading")
        note.setWordWrap(True)
        theme_form.addRow("", note)
        vbox.addWidget(theme_grp)

        # Appearance group
        appearance_grp = QGroupBox("APPEARANCE")
        app_form = QFormLayout(appearance_grp)
        app_form.setSpacing(8)

        self._theme_combo = QComboBox()
        for tid, tdata in APP_THEMES.items():
            self._theme_combo.addItem(tdata["name"], tid)
        current_theme = getattr(self._s, 'app_theme', 'dark')
        idx = self._theme_combo.findData(current_theme)
        if idx >= 0:
            self._theme_combo.setCurrentIndex(idx)
        app_form.addRow("UI Theme:", self._theme_combo)
        vbox.addWidget(appearance_grp)

        # Default shadow group
        shadow_grp = QGroupBox("DEFAULT SHADOW")
        sh_form = QFormLayout(shadow_grp)
        sh_form.setSpacing(8)

        self._sh_offset_x = QDoubleSpinBox()
        self._sh_offset_x.setRange(-50, 50)
        self._sh_offset_x.setSingleStep(0.5)
        self._sh_offset_x.setValue(getattr(self._s, 'shadow_default_offset_x', 3.0))
        self._sh_offset_x.setSuffix(" px")
        sh_form.addRow("Offset X:", self._sh_offset_x)

        self._sh_offset_y = QDoubleSpinBox()
        self._sh_offset_y.setRange(-50, 50)
        self._sh_offset_y.setSingleStep(0.5)
        self._sh_offset_y.setValue(getattr(self._s, 'shadow_default_offset_y', 3.0))
        self._sh_offset_y.setSuffix(" px")
        sh_form.addRow("Offset Y:", self._sh_offset_y)

        self._sh_blur = QDoubleSpinBox()
        self._sh_blur.setRange(0, 50)
        self._sh_blur.setSingleStep(0.5)
        self._sh_blur.setValue(getattr(self._s, 'shadow_default_blur', 5.0))
        self._sh_blur.setSuffix(" px")
        sh_form.addRow("Blur radius:", self._sh_blur)

        vbox.addWidget(shadow_grp)

        vbox.addStretch()
        scroll.setWidget(inner)
        return scroll

    def _build_hotkeys_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        vbox = QVBoxLayout(inner)
        vbox.setContentsMargins(8, 8, 8, 8)
        vbox.setSpacing(12)

        hk_grp = QGroupBox("KEYBOARD SHORTCUTS")
        form = QFormLayout(hk_grp)
        form.setSpacing(8)

        self._hk_fields = {}
        hk = self._s.hotkeys
        for name, label, hint in [
            ("capture",        "Capture screen",     "e.g. PrintScreen"),
            ("undo",           "Undo",               "e.g. Ctrl+Z"),
            ("redo",           "Redo",               "e.g. Ctrl+Y"),
            ("save",           "Save",               "e.g. Ctrl+S"),
            ("save_as",        "Save As",            "e.g. Ctrl+Shift+S"),
            ("copy_clipboard", "Copy to clipboard",  "e.g. Ctrl+C"),
            ("delete",         "Delete selected",    "e.g. Delete"),
        ]:
            field = QLineEdit(getattr(hk, name, ""))
            field.setPlaceholderText(hint)
            self._hk_fields[name] = field
            form.addRow(f"{label}:", field)

        note = QLabel("Changes take effect after restart.")
        note.setObjectName("subheading")
        vbox.addWidget(hk_grp)
        vbox.addWidget(note)
        vbox.addStretch()
        scroll.setWidget(inner)
        return scroll

    def _build_tools_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        vbox = QVBoxLayout(inner)
        vbox.setContentsMargins(8, 8, 8, 8)
        vbox.setSpacing(12)

        # Global defaults (used as starting values for tools with no saved state)
        def_grp = QGroupBox("GLOBAL DEFAULTS")
        form = QFormLayout(def_grp)
        form.setSpacing(8)

        td = self._s.tool_defaults

        fg_row = QHBoxLayout()
        self._fg_color = td.foreground_color
        self._fg_btn = QPushButton()
        self._fg_btn.setObjectName("colorBtn")
        self._fg_btn.setStyleSheet(f"background:{self._fg_color};")
        self._fg_btn.clicked.connect(lambda: self._pick_color("fg"))
        self._fg_lbl = QLabel(self._fg_color)
        fg_row.addWidget(self._fg_btn)
        fg_row.addWidget(self._fg_lbl)
        fg_row.addStretch()
        form.addRow("Foreground color:", fg_row)

        bg_row = QHBoxLayout()
        self._bg_color = td.background_color
        self._bg_btn = QPushButton()
        self._bg_btn.setObjectName("colorBtn")
        self._bg_btn.setStyleSheet(f"background:{self._bg_color};")
        self._bg_btn.clicked.connect(lambda: self._pick_color("bg"))
        self._bg_lbl = QLabel(self._bg_color)
        bg_row.addWidget(self._bg_btn)
        bg_row.addWidget(self._bg_lbl)
        bg_row.addStretch()
        form.addRow("Background color:", bg_row)

        self._line_width = QSpinBox()
        self._line_width.setRange(1, 50)
        self._line_width.setValue(td.line_width)
        self._line_width.setSuffix(" px")
        form.addRow("Default line width:", self._line_width)

        self._font_family = QLineEdit(td.font_family)
        form.addRow("Default font:", self._font_family)

        self._font_size = QSpinBox()
        self._font_size.setRange(6, 120)
        self._font_size.setValue(td.font_size)
        self._font_size.setSuffix(" pt")
        form.addRow("Default font size:", self._font_size)
        vbox.addWidget(def_grp)

        # Saved tool states
        mem_grp = QGroupBox("SAVED TOOL MEMORY")
        mem_layout = QVBoxLayout(mem_grp)
        saved = self._s.tool_properties
        if saved:
            info = QLabel(f"{len(saved)} tool(s) have saved property memory: "
                          f"{', '.join(saved.keys())}")
            info.setWordWrap(True)
            mem_layout.addWidget(info)
        else:
            mem_layout.addWidget(QLabel("No saved tool properties yet."))
        note = QLabel('Use "Reset Tools to Default" (button below) to clear all saved memory.')
        note.setObjectName("subheading")
        note.setWordWrap(True)
        mem_layout.addWidget(note)
        vbox.addWidget(mem_grp)

        vbox.addStretch()
        scroll.setWidget(inner)
        return scroll

    def _build_presets_tab(self) -> QWidget:
        """Presets management tab: view, edit, add, delete presets."""
        from paparaz.ui.theme_presets import PRESETS, PRESET_ORDER, ThemePreset, _draw_preview
        import copy

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        vbox = QVBoxLayout(inner)
        vbox.setContentsMargins(8, 8, 8, 8)
        vbox.setSpacing(12)

        # Header note
        note = QLabel(
            "Built-in presets apply colours, line width, font, opacity and shadow globally to all tools. "
            "Select a preset below to preview its settings."
        )
        note.setObjectName("subheading")
        note.setWordWrap(True)
        vbox.addWidget(note)

        for pid in PRESET_ORDER:
            preset = PRESETS[pid]
            grp = QGroupBox(f"{preset.category.upper()} · {preset.name}  —  {preset.tagline}")
            form = QFormLayout(grp)
            form.setSpacing(6)

            # Preview thumbnail
            pix = _draw_preview(preset, 160, 96)
            pix_lbl = QLabel()
            pix_lbl.setPixmap(pix)
            pix_lbl.setFixedSize(160, 96)
            form.addRow("Preview:", pix_lbl)

            # Color fields (read-only display)
            for label, value in [
                ("Foreground:", preset.fg_color),
                ("Background:", preset.bg_color),
                ("Text bg:", preset.text_bg_color),
                ("Shadow color:", preset.shadow_color),
            ]:
                row = QHBoxLayout()
                swatch = QPushButton()
                swatch.setObjectName("colorBtn")
                c = QColor(value)
                swatch.setStyleSheet(
                    f"background: rgba({c.red()},{c.green()},{c.blue()},{c.alpha()});"
                    "min-width:22px; max-width:22px; min-height:20px; max-height:20px;"
                    "border:1px solid #555; border-radius:3px;"
                )
                swatch.setEnabled(False)
                lbl = QLabel(value)
                lbl.setStyleSheet("color:#888; font-size:10px;")
                row.addWidget(swatch)
                row.addWidget(lbl)
                row.addStretch()
                form.addRow(label, row)

            # Numeric properties
            for label, value in [
                ("Line width:", f"{preset.line_width} px"),
                ("Opacity:", f"{preset.opacity:.0%}"),
                ("Font:", f"{preset.font_family}, {preset.font_size}pt"),
                ("Shadow:", f"{'On' if preset.shadow_enabled else 'Off'}  offset ({preset.shadow_offset_x:.0f}, {preset.shadow_offset_y:.0f})  blur {preset.shadow_blur:.0f}px"),
            ]:
                info = QLabel(value)
                info.setStyleSheet("color:#ccc; font-size:10px;")
                form.addRow(label, info)

            vbox.addWidget(grp)

        vbox.addStretch()
        scroll.setWidget(inner)
        return scroll

    def _build_about_tab(self) -> QWidget:
        w = QWidget()
        vbox = QVBoxLayout(w)
        vbox.setContentsMargins(16, 16, 16, 16)
        vbox.setSpacing(8)

        title = QLabel("PapaRaZ")
        title.setObjectName("heading")
        f = title.font(); f.setPointSize(20); f.setBold(True); title.setFont(f)
        title.setStyleSheet("color: #740096;")
        vbox.addWidget(title)

        vbox.addWidget(QLabel("Version 0.6.0  ·  Screen Capture & Annotation for Windows"))
        vbox.addWidget(_sep())

        author_lbl = QLabel("Author:  <b>Alejandro Lichtenfeld</b>")
        author_lbl.setTextFormat(Qt.TextFormat.RichText)
        vbox.addWidget(author_lbl)

        vbox.addWidget(QLabel("License:  MIT License"))
        vbox.addWidget(_sep())

        vbox.addWidget(QLabel("Built with:"))
        for line in [
            "  · Python 3.11+",
            "  · PySide6 (Qt 6) — GUI framework",
            "  · Win32 API (pywin32 / ctypes) — DPI-aware capture",
            "  · Pillow — image processing",
        ]:
            vbox.addWidget(QLabel(line))

        vbox.addWidget(_sep())

        ack = QLabel(
            "Inspired by <a href='https://flameshot.org'>Flameshot</a> (GPLv3). "
            "PapaRaZ is an independent Python/PySide6 reimplementation; "
            "no Flameshot source code was copied or adapted."
        )
        ack.setOpenExternalLinks(True)
        ack.setWordWrap(True)
        ack.setStyleSheet("color: #888; font-size: 10px;")
        vbox.addWidget(ack)

        vbox.addStretch()
        return w

    # -----------------------------------------------------------------------

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

    def _reset_all_tool_properties(self):
        """Clear all per-tool saved property memory."""
        self._s.tool_properties.clear()
        self._sm.save()
        # Refresh the tab label
        saved = self._s.tool_properties
        # Rebuild tools tab would be complex; just show a brief status in title
        self.setWindowTitle("PapaRaZ — Settings  [Tool memory cleared]")

    def _save_and_close(self):
        s = self._s

        # General
        s.save_directory = self._save_dir.text()
        s.default_format = self._format_combo.currentText()
        s.jpg_quality = self._jpg_quality.value()
        s.start_on_login = self._start_login.isChecked()
        from paparaz.utils.startup import set_start_on_login
        set_start_on_login(s.start_on_login)
        s.show_tray_notification = self._tray_notify.isChecked()
        s.default_theme_preset = self._theme_preset_combo.currentData() or ""

        # Hotkeys
        for name, field in self._hk_fields.items():
            setattr(s.hotkeys, name, field.text())

        # Tool defaults
        s.tool_defaults.foreground_color = self._fg_color
        s.tool_defaults.background_color = self._bg_color
        s.tool_defaults.line_width = self._line_width.value()
        s.tool_defaults.font_family = self._font_family.text()
        s.tool_defaults.font_size = self._font_size.value()

        # Appearance + shadow defaults
        self._s.app_theme = self._theme_combo.currentData()
        self._s.shadow_default_offset_x = self._sh_offset_x.value()
        self._s.shadow_default_offset_y = self._sh_offset_y.value()
        self._s.shadow_default_blur = self._sh_blur.value()

        self._sm.save()
        # Apply theme immediately
        from paparaz.ui.app_theme import get_theme, build_dialog_qss
        theme = get_theme(self._s.app_theme)
        from paparaz.ui.icons import combo_arrow_css as _arrow_css
        self.setStyleSheet(build_dialog_qss(theme) + _arrow_css())
        # Signal parent to re-apply theme
        if self.parent() and hasattr(self.parent(), 'apply_app_theme'):
            self.parent().apply_app_theme(self._s.app_theme)
        self.accept()
