"""App-level UI themes for PapaRaZ.

Each theme is a dict of CSS color tokens.  build_tool_qss(theme) and
build_panel_qss(theme) produce the per-widget stylesheets used by
ToolStrip (toolbar.py) and SidePanel (side_panel.py).
apply_theme(app_widget, theme_id) applies a chosen theme globally.
"""

from __future__ import annotations

APP_THEMES: dict[str, dict] = {
    "dark": {
        "name": "Dark (default)",
        "bg1":  "#1e1e2e",
        "bg2":  "#2a2a3e",
        "bg3":  "#3a3a4e",
        "accent":         "#740096",
        "accent_hover":   "#9e2ac0",
        "accent_pressed": "#5a0074",
        "fg":        "#cccccc",
        "fg_bright": "#ffffff",
        "fg_dim":    "#888888",
        "border":    "#444444",
        "border2":   "#3a3a4e",
    },
    "midnight": {
        "name": "Midnight Blue",
        "bg1":  "#0d0d1a",
        "bg2":  "#171728",
        "bg3":  "#252538",
        "accent":         "#5500cc",
        "accent_hover":   "#7722ee",
        "accent_pressed": "#3a0099",
        "fg":        "#bbbbbb",
        "fg_bright": "#eeeeee",
        "fg_dim":    "#666666",
        "border":    "#333355",
        "border2":   "#252540",
    },
    "ocean": {
        "name": "Ocean",
        "bg1":  "#0a1520",
        "bg2":  "#142030",
        "bg3":  "#1e2f42",
        "accent":         "#0080cc",
        "accent_hover":   "#22aaee",
        "accent_pressed": "#005fa0",
        "fg":        "#c0d8f0",
        "fg_bright": "#e8f4ff",
        "fg_dim":    "#7090a8",
        "border":    "#2a4060",
        "border2":   "#1e3050",
    },
    "forest": {
        "name": "Forest",
        "bg1":  "#0d150d",
        "bg2":  "#182218",
        "bg3":  "#243024",
        "accent":         "#2e8b57",
        "accent_hover":   "#3daa6a",
        "accent_pressed": "#1e6640",
        "fg":        "#b8d8b8",
        "fg_bright": "#e0f0e0",
        "fg_dim":    "#6a8a6a",
        "border":    "#2a442a",
        "border2":   "#1e341e",
    },
    "warm": {
        "name": "Warm Dark",
        "bg1":  "#1a1208",
        "bg2":  "#261c0e",
        "bg3":  "#342a18",
        "accent":         "#cc6600",
        "accent_hover":   "#e07a10",
        "accent_pressed": "#994d00",
        "fg":        "#ddd0b0",
        "fg_bright": "#fff0d8",
        "fg_dim":    "#8a7855",
        "border":    "#443020",
        "border2":   "#342818",
    },
}


def _t(template: str, theme: dict) -> str:
    """Substitute {key} placeholders with theme values."""
    return template.format(**theme)


_TOOL_QSS_TEMPLATE = """
QWidget#toolStrip {{
    background: {bg1};
    border-right: 1px solid {border};
}}
QToolButton {{
    background: transparent; border: none;
    border-radius: 4px; padding: 3px;
    min-width: 32px; min-height: 32px;
    max-width: 32px; max-height: 32px;
    color: {fg};
}}
QToolButton:hover   {{ background: {bg3}; }}
QToolButton:checked {{ background: {accent}; }}
QToolButton:pressed {{ background: {accent_pressed}; }}
QToolButton:disabled {{ opacity: 0.3; }}
QToolButton[flat="true"] {{
    min-width: 28px; min-height: 28px;
    max-width: 28px; max-height: 28px;
}}
"""

_PANEL_QSS_TEMPLATE = """
QWidget#sidePanel {{ background: transparent; }}
QWidget#panelHeader {{ background: {bg1}; border-bottom: 1px solid {border}; }}
QLabel {{ color: {fg_dim}; font-size: 11px; padding: 0; margin: 0; }}
QLabel#sectionTitle {{
    color: {fg_dim}; font-size: 10px; font-weight: bold;
    padding: 3px 0 1px 0; text-transform: uppercase;
}}
QLabel#editBanner {{
    color: {fg_bright}; background: {accent}; font-size: 11px; font-weight: bold;
    padding: 2px 4px; border-radius: 2px;
}}
QLabel#valLabel {{ color: {fg_dim}; font-size: 11px; min-width: 28px; }}
QSlider {{ max-height: 18px; }}
QSlider::groove:horizontal {{ height: 3px; background: {border}; border-radius: 1px; }}
QSlider::handle:horizontal {{
    background: {accent}; width: 12px; height: 12px;
    margin: -5px 0; border-radius: 6px;
}}
QSlider::handle:horizontal:hover {{ background: {accent_hover}; }}
QComboBox, QFontComboBox {{
    background: {bg2}; color: {fg};
    border: 1px solid {border2}; border-radius: 2px;
    padding: 2px 4px; font-size: 11px; max-height: 22px;
}}
QComboBox QAbstractItemView {{
    background: {bg2}; color: {fg};
    selection-background-color: {accent}; font-size: 11px;
}}
QPushButton#colorSwatch {{
    border: 1px solid {border}; border-radius: 2px;
    min-width: 22px; min-height: 22px;
    max-width: 22px; max-height: 22px;
}}
QPushButton#colorSwatch:hover {{ border-color: {fg}; }}
QCheckBox {{ color: {fg}; font-size: 11px; spacing: 4px; }}
QCheckBox::indicator {{
    width: 14px; height: 14px;
    border: 1px solid {border}; border-radius: 2px; background: {bg2};
}}
QCheckBox::indicator:checked {{ background: {accent}; border-color: {accent}; }}
QToolButton {{
    background: {bg2}; border: 1px solid {border2};
    border-radius: 2px; padding: 1px;
    min-width: 22px; min-height: 22px;
    max-width: 22px; max-height: 22px;
}}
QToolButton:hover    {{ background: {bg3}; }}
QToolButton:checked  {{ background: {accent}; border-color: {accent}; }}
"""

_EDITOR_QSS_TEMPLATE = """
QWidget#editorRoot {{
    background: {bg1};
}}
"""

_DIALOG_QSS_TEMPLATE = """
QDialog {{ background: {bg1}; color: {fg}; font-size: 12px; }}
QScrollArea {{ border: none; background: {bg1}; }}
QTabWidget::pane {{ border: 1px solid {border2}; background: {bg1}; border-radius: 0 4px 4px 4px; }}
QTabBar::tab {{
    background: {bg2}; color: {fg_dim}; padding: 8px 18px;
    border: 1px solid {border2}; border-bottom: none; border-radius: 4px 4px 0 0;
    min-width: 80px; font-size: 12px;
}}
QTabBar::tab:selected {{ background: {bg1}; color: {fg_bright}; border-bottom: 1px solid {bg1}; }}
QTabBar::tab:hover:!selected {{ background: {bg3}; color: {fg}; }}
QGroupBox {{
    color: {fg_dim}; font-size: 12px; font-weight: bold;
    border: 1px solid {border2}; border-radius: 6px;
    margin-top: 10px; padding: 12px 8px 8px 8px;
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; top: -1px; padding: 0 4px; }}
QLineEdit, QSpinBox, QComboBox, QDoubleSpinBox {{
    background: {bg2}; color: {fg}; border: 1px solid {border2};
    border-radius: 4px; padding: 5px 8px; min-height: 24px; font-size: 12px;
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QDoubleSpinBox:focus {{ border-color: {accent}; }}
QCheckBox {{ color: {fg}; spacing: 8px; font-size: 12px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px; border: 1px solid {border};
    border-radius: 3px; background: {bg2};
}}
QCheckBox::indicator:checked {{ background: {accent}; border-color: {accent}; }}
QPushButton {{
    background: {accent}; color: white; border: none;
    border-radius: 5px; padding: 8px 22px; font-weight: bold; font-size: 12px;
}}
QPushButton:hover {{ background: {accent_hover}; }}
QPushButton:pressed {{ background: {accent_pressed}; }}
QPushButton#secondary {{
    background: {bg2}; color: {fg_dim}; border: 1px solid {border2};
    padding: 8px 18px; font-weight: normal; font-size: 12px;
}}
QPushButton#secondary:hover {{ background: {bg3}; color: {fg}; }}
QPushButton#danger {{
    background: #6b1010; color: #ffaaaa; border: 1px solid #aa3333; font-size: 12px;
}}
QPushButton#danger:hover {{ background: #8b1818; color: #fff; }}
QLabel {{ color: {fg}; font-size: 12px; }}
QLabel#heading {{ color: {fg_bright}; font-size: 15px; font-weight: bold; }}
QLabel#subheading {{ color: {fg_dim}; font-size: 12px; }}
"""


def get_theme(theme_id: str) -> dict:
    return APP_THEMES.get(theme_id, APP_THEMES["dark"])


def build_tool_qss(theme: dict) -> str:
    return _t(_TOOL_QSS_TEMPLATE, theme)


def build_panel_qss(theme: dict) -> str:
    return _t(_PANEL_QSS_TEMPLATE, theme)


def build_dialog_qss(theme: dict) -> str:
    return _t(_DIALOG_QSS_TEMPLATE, theme)
