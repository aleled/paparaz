"""Settings dialog for PapaRaZ - hotkeys, defaults, theme, save directory."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QTabWidget,
    QWidget, QLabel, QLineEdit, QSpinBox, QCheckBox, QComboBox,
    QPushButton, QFileDialog, QColorDialog, QGroupBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from paparaz.core.settings import SettingsManager

DIALOG_STYLE = """
QDialog { background: #1a1a2e; color: #ddd; }
QTabWidget::pane { border: 1px solid #444; background: #1a1a2e; }
QTabBar::tab {
    background: #2a2a3e; color: #aaa; padding: 8px 16px;
    border: 1px solid #444; border-bottom: none; border-radius: 4px 4px 0 0;
}
QTabBar::tab:selected { background: #1a1a2e; color: #fff; }
QGroupBox {
    color: #aaa; font-weight: bold; border: 1px solid #444;
    border-radius: 4px; margin-top: 8px; padding-top: 16px;
}
QGroupBox::title { subcontrol-origin: margin; left: 10px; }
QLineEdit, QSpinBox, QComboBox {
    background: #2a2a3e; color: #ddd; border: 1px solid #444;
    border-radius: 4px; padding: 4px 8px;
}
QCheckBox { color: #ccc; spacing: 6px; }
QCheckBox::indicator {
    width: 16px; height: 16px; border: 1px solid #555;
    border-radius: 3px; background: #2a2a3e;
}
QCheckBox::indicator:checked { background: #740096; border-color: #740096; }
QPushButton {
    background: #740096; color: white; border: none;
    border-radius: 4px; padding: 8px 20px; font-weight: bold;
}
QPushButton:hover { background: #9e2ac0; }
QPushButton#secondary {
    background: #2a2a3e; color: #aaa; border: 1px solid #444;
}
QPushButton#secondary:hover { background: #3a3a4e; }
QPushButton#colorBtn {
    min-width: 30px; max-width: 30px; min-height: 24px; max-height: 24px;
    border: 2px solid #555; border-radius: 4px; padding: 0;
}
QLabel { color: #ccc; }
"""


class SettingsDialog(QDialog):
    """Settings dialog with tabs for General, Hotkeys, Tools, and About."""

    def __init__(self, settings_manager: SettingsManager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PapaRaZ Settings")
        self.setMinimumSize(500, 450)
        self.setStyleSheet(DIALOG_STYLE)
        self._sm = settings_manager
        self._s = settings_manager.settings

        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        layout.addWidget(tabs)

        tabs.addTab(self._build_general_tab(), "General")
        tabs.addTab(self._build_hotkeys_tab(), "Hotkeys")
        tabs.addTab(self._build_tools_tab(), "Tools")
        tabs.addTab(self._build_about_tab(), "About")

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondary")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save_and_close)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _build_general_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setSpacing(10)

        # Save directory
        dir_row = QHBoxLayout()
        self._save_dir = QLineEdit(self._s.save_directory or "")
        self._save_dir.setPlaceholderText("Default: user home")
        dir_row.addWidget(self._save_dir, 1)
        browse_btn = QPushButton("...")
        browse_btn.setObjectName("secondary")
        browse_btn.setMaximumWidth(40)
        browse_btn.clicked.connect(self._browse_save_dir)
        dir_row.addWidget(browse_btn)
        form.addRow("Save directory:", dir_row)

        # Default format
        self._format_combo = QComboBox()
        self._format_combo.addItems(["png", "jpg", "svg"])
        self._format_combo.setCurrentText(self._s.default_format)
        form.addRow("Default format:", self._format_combo)

        # JPG quality
        self._jpg_quality = QSpinBox()
        self._jpg_quality.setRange(10, 100)
        self._jpg_quality.setValue(self._s.jpg_quality)
        form.addRow("JPG quality:", self._jpg_quality)

        # Theme
        self._theme_combo = QComboBox()
        self._theme_combo.addItems(["dark"])
        self._theme_combo.setCurrentText(self._s.theme)
        form.addRow("Theme:", self._theme_combo)

        # Start on login
        self._start_login = QCheckBox("Start PapaRaZ on login")
        self._start_login.setChecked(self._s.start_on_login)
        form.addRow("", self._start_login)

        # Tray notification
        self._tray_notify = QCheckBox("Show tray notification on start")
        self._tray_notify.setChecked(self._s.show_tray_notification)
        form.addRow("", self._tray_notify)

        # Delay capture
        self._delay_spin = QSpinBox()
        self._delay_spin.setRange(0, 30)
        self._delay_spin.setValue(getattr(self._s, 'capture_delay', 0))
        self._delay_spin.setSuffix(" sec")
        self._delay_spin.setSpecialValueText("No delay")
        form.addRow("Capture delay:", self._delay_spin)

        return w

    def _build_hotkeys_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setSpacing(10)

        self._hk_fields = {}
        hk = self._s.hotkeys
        for name, label in [
            ("capture", "Capture screen"),
            ("undo", "Undo"),
            ("redo", "Redo"),
            ("save", "Save"),
            ("save_as", "Save As"),
            ("copy_clipboard", "Copy to clipboard"),
            ("delete", "Delete selected"),
        ]:
            field = QLineEdit(getattr(hk, name, ""))
            self._hk_fields[name] = field
            form.addRow(f"{label}:", field)

        return w

    def _build_tools_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setSpacing(10)

        td = self._s.tool_defaults

        # Foreground color
        fg_row = QHBoxLayout()
        self._fg_color = td.foreground_color
        self._fg_btn = QPushButton()
        self._fg_btn.setObjectName("colorBtn")
        self._fg_btn.setStyleSheet(f"background: {self._fg_color};")
        self._fg_btn.clicked.connect(lambda: self._pick_color("fg"))
        fg_row.addWidget(self._fg_btn)
        fg_row.addWidget(QLabel(self._fg_color))
        fg_row.addStretch()
        form.addRow("Foreground:", fg_row)

        # Background color
        bg_row = QHBoxLayout()
        self._bg_color = td.background_color
        self._bg_btn = QPushButton()
        self._bg_btn.setObjectName("colorBtn")
        self._bg_btn.setStyleSheet(f"background: {self._bg_color};")
        self._bg_btn.clicked.connect(lambda: self._pick_color("bg"))
        bg_row.addWidget(self._bg_btn)
        bg_row.addWidget(QLabel(self._bg_color))
        bg_row.addStretch()
        form.addRow("Background:", bg_row)

        # Line width
        self._line_width = QSpinBox()
        self._line_width.setRange(1, 50)
        self._line_width.setValue(td.line_width)
        form.addRow("Line width:", self._line_width)

        # Font
        self._font_family = QLineEdit(td.font_family)
        form.addRow("Font family:", self._font_family)

        self._font_size = QSpinBox()
        self._font_size.setRange(6, 120)
        self._font_size.setValue(td.font_size)
        form.addRow("Font size:", self._font_size)

        return w

    def _build_about_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addStretch()
        layout.addWidget(QLabel("<h2 style='color:#740096'>PapaRaZ</h2>"))
        layout.addWidget(QLabel("Version 0.5.0"))
        layout.addWidget(QLabel("Flameshot-inspired screen capture & annotation tool"))
        layout.addWidget(QLabel(""))
        layout.addWidget(QLabel("Built with Python + PySide6 (Qt 6)"))
        layout.addWidget(QLabel("Windows only | Win32 API for capture"))
        layout.addStretch()
        return w

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
                self._fg_btn.setStyleSheet(f"background: {self._fg_color};")
            else:
                self._bg_color = color.name()
                self._bg_btn.setStyleSheet(f"background: {self._bg_color};")

    def _save_and_close(self):
        s = self._s

        # General
        s.save_directory = self._save_dir.text()
        s.default_format = self._format_combo.currentText()
        s.jpg_quality = self._jpg_quality.value()
        s.theme = self._theme_combo.currentText()
        s.start_on_login = self._start_login.isChecked()
        s.show_tray_notification = self._tray_notify.isChecked()

        # Hotkeys
        for name, field in self._hk_fields.items():
            setattr(s.hotkeys, name, field.text())

        # Tool defaults
        s.tool_defaults.foreground_color = self._fg_color
        s.tool_defaults.background_color = self._bg_color
        s.tool_defaults.line_width = self._line_width.value()
        s.tool_defaults.font_family = self._font_family.text()
        s.tool_defaults.font_size = self._font_size.value()

        self._sm.save()
        self.accept()
