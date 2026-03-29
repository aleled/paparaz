"""Side panel with per-tool sub-settings, element property inspector, and global style controls."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QSpinBox, QComboBox, QPushButton, QToolButton, QButtonGroup,
    QColorDialog, QFrame, QCheckBox, QFontComboBox,
    QGraphicsDropShadowEffect, QScrollArea, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont

from paparaz.tools.base import ToolType
from paparaz.ui.icons import get_icon
from paparaz.core.elements import (
    AnnotationElement, TextElement, RectElement, EllipseElement,
    MaskElement, NumberElement, ElementType,
)

PANEL_WIDTH = 200

PANEL_STYLE = """
QWidget#sidePanel {
    background: #1a1a2e;
    border-right: 1px solid #333;
}
QLabel {
    color: #bbb;
    font-size: 10px;
    padding: 0;
}
QLabel#sectionTitle {
    color: #777;
    font-size: 9px;
    font-weight: bold;
    padding: 4px 0 1px 0;
    border-bottom: 1px solid #2a2a3e;
    margin-bottom: 1px;
    text-transform: uppercase;
}
QLabel#editBanner {
    color: #fff;
    background: #740096;
    font-size: 10px;
    font-weight: bold;
    padding: 3px 6px;
    border-radius: 3px;
}
QSlider::groove:horizontal {
    height: 3px; background: #444; border-radius: 1px;
}
QSlider::handle:horizontal {
    background: #740096; width: 12px; height: 12px;
    margin: -4px 0; border-radius: 6px;
}
QSlider::handle:horizontal:hover { background: #9e2ac0; }
QSpinBox, QComboBox, QFontComboBox {
    background: #2a2a3e; color: #ddd;
    border: 1px solid #444; border-radius: 3px;
    padding: 2px 4px; font-size: 10px;
    max-height: 22px;
}
QSpinBox::up-button, QSpinBox::down-button {
    width: 14px; background: #333; border: none;
}
QComboBox::drop-down { border: none; width: 16px; }
QComboBox QAbstractItemView {
    background: #2a2a3e; color: #ddd;
    selection-background-color: #740096;
}
QPushButton#colorSwatch {
    border: 2px solid #555; border-radius: 3px;
    min-width: 24px; min-height: 24px;
    max-width: 24px; max-height: 24px;
}
QPushButton#colorSwatch:hover { border-color: #999; }
QCheckBox { color: #bbb; font-size: 10px; spacing: 4px; }
QCheckBox::indicator {
    width: 14px; height: 14px;
    border: 1px solid #555; border-radius: 2px;
    background: #2a2a3e;
}
QCheckBox::indicator:checked { background: #740096; border-color: #740096; }
QToolButton {
    background: #2a2a3e; border: 1px solid #444;
    border-radius: 3px; padding: 2px;
    min-width: 24px; min-height: 24px;
    max-width: 24px; max-height: 24px;
}
QToolButton:hover { background: #3a3a4e; }
QToolButton:checked { background: #740096; border-color: #740096; }
"""

# Which settings sections to show per tool type
TOOL_SECTIONS = {
    ToolType.SELECT:     {"stroke": False, "line_style": False, "fill": False, "effects": True, "text": False, "mask": False, "number": False},
    ToolType.PEN:        {"stroke": True,  "line_style": True,  "fill": False, "effects": True, "text": False, "mask": False, "number": False},
    ToolType.BRUSH:      {"stroke": True,  "line_style": False, "fill": False, "effects": True, "text": False, "mask": False, "number": False},
    ToolType.LINE:       {"stroke": True,  "line_style": True,  "fill": False, "effects": True, "text": False, "mask": False, "number": False},
    ToolType.ARROW:      {"stroke": True,  "line_style": True,  "fill": False, "effects": True, "text": False, "mask": False, "number": False},
    ToolType.RECTANGLE:  {"stroke": True,  "line_style": True,  "fill": True,  "effects": True, "text": False, "mask": False, "number": False},
    ToolType.ELLIPSE:    {"stroke": True,  "line_style": True,  "fill": True,  "effects": True, "text": False, "mask": False, "number": False},
    ToolType.TEXT:        {"stroke": False, "line_style": False, "fill": False, "effects": True, "text": True,  "mask": False, "number": False},
    ToolType.NUMBERING:  {"stroke": False, "line_style": False, "fill": False, "effects": True, "text": False, "mask": False, "number": True},
    ToolType.ERASER:     {"stroke": False, "line_style": False, "fill": False, "effects": False,"text": False, "mask": False, "number": False},
    ToolType.MASQUERADE: {"stroke": False, "line_style": False, "fill": False, "effects": True, "text": False, "mask": True,  "number": False},
    ToolType.FILL:       {"stroke": False, "line_style": False, "fill": False, "effects": False,"text": False, "mask": False, "number": False},
}


class SidePanel(QWidget):
    """Left-side panel with per-tool sub-settings and element property inspector."""

    # Style signals (affect both template and selected element)
    fg_color_changed = Signal(str)
    bg_color_changed = Signal(str)
    line_width_changed = Signal(float)
    font_family_changed = Signal(str)
    font_size_changed = Signal(int)
    shadow_toggled = Signal(bool)
    shadow_color_changed = Signal(str)
    shadow_offset_x_changed = Signal(float)
    shadow_offset_y_changed = Signal(float)
    shadow_blur_changed = Signal(float)
    opacity_changed = Signal(float)
    cap_style_changed = Signal(str)
    join_style_changed = Signal(str)
    dash_pattern_changed = Signal(str)
    # Shape-specific
    filled_toggled = Signal(bool)
    # Mask-specific
    pixel_size_changed = Signal(int)
    # Number-specific
    number_size_changed = Signal(float)
    number_text_color_changed = Signal(str)
    # Text-specific
    text_bold_changed = Signal(bool)
    text_italic_changed = Signal(bool)
    text_underline_changed = Signal(bool)
    text_strikethrough_changed = Signal(bool)
    text_alignment_changed = Signal(str)
    text_direction_changed = Signal(str)
    text_bg_enabled_changed = Signal(bool)
    text_bg_color_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidePanel")
        self.setStyleSheet(PANEL_STYLE)
        self.setFixedWidth(PANEL_WIDTH)

        self._fg_color = "#FF0000"
        self._bg_color = "#FFFFFF"
        self._text_bg_color = "#FFFF00"
        self._current_tool = ToolType.SELECT
        self._loading_element = False  # Prevent re-emitting signals during load

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll_widget = QWidget()
        self._layout = QVBoxLayout(scroll_widget)
        self._layout.setContentsMargins(8, 4, 8, 8)
        self._layout.setSpacing(2)
        scroll.setWidget(scroll_widget)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        # --- Edit mode banner (shown when element selected) ---
        self._edit_banner = QLabel("Editing selected element")
        self._edit_banner.setObjectName("editBanner")
        self._edit_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._edit_banner.hide()
        self._layout.addWidget(self._edit_banner)

        # --- COLOR section (always visible) ---
        self._layout.addWidget(self._section_title("COLOR"))
        color_row = QHBoxLayout()
        color_row.setSpacing(8)

        fg_col = QVBoxLayout()
        fg_col.setSpacing(2)
        fg_col.addWidget(QLabel("Foreground"))
        self._fg_btn = QPushButton()
        self._fg_btn.setObjectName("colorSwatch")
        self._update_swatch(self._fg_btn, self._fg_color)
        self._fg_btn.clicked.connect(self._pick_fg_color)
        fg_col.addWidget(self._fg_btn)
        color_row.addLayout(fg_col)

        bg_col = QVBoxLayout()
        bg_col.setSpacing(2)
        bg_col.addWidget(QLabel("Background"))
        self._bg_btn = QPushButton()
        self._bg_btn.setObjectName("colorSwatch")
        self._update_swatch(self._bg_btn, self._bg_color)
        self._bg_btn.clicked.connect(self._pick_bg_color)
        bg_col.addWidget(self._bg_btn)
        color_row.addLayout(bg_col)

        color_row.addStretch()
        self._layout.addLayout(color_row)

        # --- STROKE section (pen, brush, line, arrow, rect, ellipse) ---
        self._stroke_title = self._section_title("STROKE")
        self._layout.addWidget(self._stroke_title)

        width_row = QHBoxLayout()
        self._width_slider = QSlider(Qt.Orientation.Horizontal)
        self._width_slider.setRange(1, 50)
        self._width_slider.setValue(3)
        width_row.addWidget(self._width_slider, 1)
        self._width_spin = QSpinBox()
        self._width_spin.setRange(1, 50)
        self._width_spin.setValue(3)
        self._width_spin.setFixedWidth(55)
        width_row.addWidget(self._width_spin)
        self._stroke_row = self._wrap_layout(width_row)
        self._layout.addWidget(self._stroke_row)

        self._width_slider.valueChanged.connect(self._width_spin.setValue)
        self._width_spin.valueChanged.connect(self._width_slider.setValue)
        self._width_slider.valueChanged.connect(self._on_line_width)

        # --- LINE STYLE section (cap, join, dash) ---
        self._line_style_title = self._section_title("LINE STYLE")
        self._layout.addWidget(self._line_style_title)

        ls_layout = QVBoxLayout()
        ls_layout.setSpacing(4)

        # Dash pattern
        dash_row = QHBoxLayout()
        dash_row.addWidget(QLabel("Pattern"))
        self._dash_combo = QComboBox()
        for label, val in [("Solid", "solid"), ("Dash", "dash"), ("Dot", "dot"), ("Dash-Dot", "dashdot")]:
            self._dash_combo.addItem(label, val)
        self._dash_combo.currentIndexChanged.connect(
            lambda i: self._emit_if_not_loading(self.dash_pattern_changed, self._dash_combo.currentData())
        )
        dash_row.addWidget(self._dash_combo, 1)
        ls_layout.addLayout(dash_row)

        # Cap style
        cap_row = QHBoxLayout()
        cap_row.addWidget(QLabel("Cap"))
        self._cap_combo = QComboBox()
        for label, val in [("Round", "round"), ("Square", "square"), ("Flat", "flat")]:
            self._cap_combo.addItem(label, val)
        self._cap_combo.currentIndexChanged.connect(
            lambda i: self._emit_if_not_loading(self.cap_style_changed, self._cap_combo.currentData())
        )
        cap_row.addWidget(self._cap_combo, 1)
        ls_layout.addLayout(cap_row)

        # Join style
        join_row = QHBoxLayout()
        join_row.addWidget(QLabel("Join"))
        self._join_combo = QComboBox()
        for label, val in [("Round", "round"), ("Bevel", "bevel"), ("Miter", "miter")]:
            self._join_combo.addItem(label, val)
        self._join_combo.currentIndexChanged.connect(
            lambda i: self._emit_if_not_loading(self.join_style_changed, self._join_combo.currentData())
        )
        join_row.addWidget(self._join_combo, 1)
        ls_layout.addLayout(join_row)

        self._line_style_widget = self._wrap_layout(ls_layout)
        self._layout.addWidget(self._line_style_widget)

        # --- FILL section (rect, ellipse) ---
        self._fill_title = self._section_title("FILL")
        self._layout.addWidget(self._fill_title)

        self._filled_check = QCheckBox("Filled shape")
        self._filled_check.toggled.connect(
            lambda v: self._emit_if_not_loading(self.filled_toggled, v)
        )
        self._fill_widget = self._wrap_widget(self._filled_check)
        self._layout.addWidget(self._fill_widget)

        # --- TEXT section ---
        self._text_title = self._section_title("TEXT")
        self._layout.addWidget(self._text_title)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)

        self._font_combo = QFontComboBox()
        self._font_combo.setCurrentFont(QFont("Arial"))
        self._font_combo.currentFontChanged.connect(
            lambda f: self._emit_if_not_loading(self.font_family_changed, f.family())
        )
        text_layout.addWidget(self._font_combo)

        size_row = QHBoxLayout()
        size_row.addWidget(QLabel("Size"))
        self._font_size_spin = QSpinBox()
        self._font_size_spin.setRange(6, 120)
        self._font_size_spin.setValue(14)
        self._font_size_spin.valueChanged.connect(
            lambda v: self._emit_if_not_loading(self.font_size_changed, v)
        )
        size_row.addWidget(self._font_size_spin)
        text_layout.addLayout(size_row)

        # Formatting buttons
        fmt_row = QHBoxLayout()
        fmt_row.setSpacing(4)
        self._bold_btn = self._make_fmt_button("bold", "Bold")
        self._bold_btn.toggled.connect(lambda v: self._emit_if_not_loading(self.text_bold_changed, v))
        fmt_row.addWidget(self._bold_btn)

        self._italic_btn = self._make_fmt_button("italic", "Italic")
        self._italic_btn.toggled.connect(lambda v: self._emit_if_not_loading(self.text_italic_changed, v))
        fmt_row.addWidget(self._italic_btn)

        self._underline_btn = self._make_fmt_button("underline", "Underline")
        self._underline_btn.toggled.connect(lambda v: self._emit_if_not_loading(self.text_underline_changed, v))
        fmt_row.addWidget(self._underline_btn)

        self._strike_btn = self._make_fmt_button("strikethrough", "Strikethrough")
        self._strike_btn.toggled.connect(lambda v: self._emit_if_not_loading(self.text_strikethrough_changed, v))
        fmt_row.addWidget(self._strike_btn)

        fmt_row.addStretch()
        text_layout.addLayout(fmt_row)

        # Alignment
        align_row = QHBoxLayout()
        align_row.setSpacing(4)
        self._align_group = QButtonGroup(self)
        self._align_group.setExclusive(True)
        self._align_btns = {}
        for name, tooltip, val in [("align_left", "Left", "left"), ("align_center", "Center", "center"), ("align_right", "Right", "right")]:
            btn = self._make_fmt_button(name, tooltip)
            self._align_group.addButton(btn)
            self._align_btns[val] = btn
            btn.toggled.connect(lambda checked, v=val: self._emit_if_not_loading(self.text_alignment_changed, v) if checked else None)
            align_row.addWidget(btn)
        self._align_btns["left"].setChecked(True)

        align_row.addSpacing(8)
        self._dir_group = QButtonGroup(self)
        self._dir_group.setExclusive(True)
        self._ltr_btn = self._make_fmt_button("ltr", "Left to Right")
        self._dir_group.addButton(self._ltr_btn)
        self._ltr_btn.setChecked(True)
        self._ltr_btn.toggled.connect(lambda checked: self._emit_if_not_loading(self.text_direction_changed, "ltr") if checked else None)
        align_row.addWidget(self._ltr_btn)

        self._rtl_btn = self._make_fmt_button("rtl", "Right to Left")
        self._dir_group.addButton(self._rtl_btn)
        self._rtl_btn.toggled.connect(lambda checked: self._emit_if_not_loading(self.text_direction_changed, "rtl") if checked else None)
        align_row.addWidget(self._rtl_btn)

        align_row.addStretch()
        text_layout.addLayout(align_row)

        # Text background
        tb_row = QHBoxLayout()
        self._text_bg_check = QCheckBox("Background")
        self._text_bg_check.toggled.connect(lambda v: self._emit_if_not_loading(self.text_bg_enabled_changed, v))
        tb_row.addWidget(self._text_bg_check)
        self._text_bg_btn = QPushButton()
        self._text_bg_btn.setObjectName("colorSwatch")
        self._update_swatch(self._text_bg_btn, self._text_bg_color)
        self._text_bg_btn.clicked.connect(self._pick_text_bg_color)
        tb_row.addWidget(self._text_bg_btn)
        tb_row.addStretch()
        text_layout.addLayout(tb_row)

        self._text_widget = self._wrap_layout(text_layout)
        self._layout.addWidget(self._text_widget)

        # --- MASK section ---
        self._mask_title = self._section_title("PIXELATE")
        self._layout.addWidget(self._mask_title)

        mask_layout = QVBoxLayout()
        mask_layout.setSpacing(4)
        ps_row = QHBoxLayout()
        ps_row.addWidget(QLabel("Pixel size"))
        self._pixel_size_spin = QSpinBox()
        self._pixel_size_spin.setRange(2, 50)
        self._pixel_size_spin.setValue(10)
        self._pixel_size_spin.valueChanged.connect(
            lambda v: self._emit_if_not_loading(self.pixel_size_changed, v)
        )
        ps_row.addWidget(self._pixel_size_spin)
        mask_layout.addLayout(ps_row)

        ps_slider = QSlider(Qt.Orientation.Horizontal)
        ps_slider.setRange(2, 50)
        ps_slider.setValue(10)
        ps_slider.valueChanged.connect(self._pixel_size_spin.setValue)
        self._pixel_size_spin.valueChanged.connect(ps_slider.setValue)
        mask_layout.addWidget(ps_slider)

        self._mask_widget = self._wrap_layout(mask_layout)
        self._layout.addWidget(self._mask_widget)

        # --- NUMBER section ---
        self._number_title = self._section_title("MARKER")
        self._layout.addWidget(self._number_title)

        num_layout = QVBoxLayout()
        num_layout.setSpacing(4)

        # Circle size
        ns_row = QHBoxLayout()
        ns_row.addWidget(QLabel("Circle size"))
        self._number_size_spin = QSpinBox()
        self._number_size_spin.setRange(16, 80)
        self._number_size_spin.setValue(28)
        self._number_size_spin.valueChanged.connect(
            lambda v: self._emit_if_not_loading(self.number_size_changed, float(v))
        )
        ns_row.addWidget(self._number_size_spin)
        num_layout.addLayout(ns_row)

        # Number font
        nf_row = QHBoxLayout()
        nf_row.addWidget(QLabel("Font"))
        self._num_font_combo = QFontComboBox()
        self._num_font_combo.setCurrentFont(QFont("Arial"))
        self._num_font_combo.currentFontChanged.connect(
            lambda f: self._emit_if_not_loading(self.font_family_changed, f.family())
        )
        nf_row.addWidget(self._num_font_combo, 1)
        num_layout.addLayout(nf_row)

        # Number text color
        ntc_row = QHBoxLayout()
        ntc_row.addWidget(QLabel("Text color"))
        self._num_text_color = "#FFFFFF"
        self._num_text_color_btn = QPushButton()
        self._num_text_color_btn.setObjectName("colorSwatch")
        self._update_swatch(self._num_text_color_btn, self._num_text_color)
        self._num_text_color_btn.clicked.connect(self._pick_num_text_color)
        ntc_row.addWidget(self._num_text_color_btn)
        ntc_row.addStretch()
        num_layout.addLayout(ntc_row)

        self._number_widget = self._wrap_layout(num_layout)
        self._layout.addWidget(self._number_widget)

        # --- EFFECTS section ---
        self._effects_title = self._section_title("EFFECTS")
        self._layout.addWidget(self._effects_title)

        effects_layout = QVBoxLayout()
        effects_layout.setSpacing(4)

        # Opacity
        opacity_row = QHBoxLayout()
        opacity_row.addWidget(QLabel("Opacity"))
        self._opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._opacity_slider.setRange(10, 100)
        self._opacity_slider.setValue(100)
        opacity_row.addWidget(self._opacity_slider, 1)
        self._opacity_label = QLabel("100%")
        self._opacity_label.setFixedWidth(35)
        opacity_row.addWidget(self._opacity_label)
        effects_layout.addLayout(opacity_row)
        self._opacity_slider.valueChanged.connect(self._on_opacity)

        # Shadow toggle
        self._shadow_check = QCheckBox("Drop shadow")
        self._shadow_check.toggled.connect(lambda v: self._emit_if_not_loading(self.shadow_toggled, v))
        effects_layout.addWidget(self._shadow_check)

        # Shadow color
        sc_row = QHBoxLayout()
        sc_row.addWidget(QLabel("Shadow color"))
        self._shadow_color = "#80000000"
        self._shadow_color_btn = QPushButton()
        self._shadow_color_btn.setObjectName("colorSwatch")
        self._update_swatch(self._shadow_color_btn, "#000000")
        self._shadow_color_btn.clicked.connect(self._pick_shadow_color)
        sc_row.addWidget(self._shadow_color_btn)
        sc_row.addStretch()
        effects_layout.addLayout(sc_row)

        # Shadow offset X
        sox_row = QHBoxLayout()
        sox_row.addWidget(QLabel("Offset X"))
        self._shadow_ox_spin = QSpinBox()
        self._shadow_ox_spin.setRange(-30, 30)
        self._shadow_ox_spin.setValue(3)
        self._shadow_ox_spin.valueChanged.connect(
            lambda v: self._emit_if_not_loading(self.shadow_offset_x_changed, float(v))
        )
        sox_row.addWidget(self._shadow_ox_spin)
        effects_layout.addLayout(sox_row)

        # Shadow offset Y
        soy_row = QHBoxLayout()
        soy_row.addWidget(QLabel("Offset Y"))
        self._shadow_oy_spin = QSpinBox()
        self._shadow_oy_spin.setRange(-30, 30)
        self._shadow_oy_spin.setValue(3)
        self._shadow_oy_spin.valueChanged.connect(
            lambda v: self._emit_if_not_loading(self.shadow_offset_y_changed, float(v))
        )
        soy_row.addWidget(self._shadow_oy_spin)
        effects_layout.addLayout(soy_row)

        # Shadow blur
        sb_row = QHBoxLayout()
        sb_row.addWidget(QLabel("Blur"))
        self._shadow_blur_spin = QSpinBox()
        self._shadow_blur_spin.setRange(0, 30)
        self._shadow_blur_spin.setValue(5)
        self._shadow_blur_spin.valueChanged.connect(
            lambda v: self._emit_if_not_loading(self.shadow_blur_changed, float(v))
        )
        sb_row.addWidget(self._shadow_blur_spin)
        effects_layout.addLayout(sb_row)

        self._effects_widget = self._wrap_layout(effects_layout)
        self._layout.addWidget(self._effects_widget)

        self._layout.addStretch()

        # Initial visibility
        self.update_for_tool(ToolType.SELECT)

    # --- Helpers ---

    def _section_title(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sectionTitle")
        return label

    def _make_fmt_button(self, icon_name: str, tooltip: str) -> QToolButton:
        btn = QToolButton()
        btn.setIcon(get_icon(icon_name, 16))
        btn.setToolTip(tooltip)
        btn.setCheckable(True)
        btn.setFixedSize(24, 24)
        return btn

    def _wrap_layout(self, layout) -> QWidget:
        w = QWidget()
        w.setLayout(layout)
        return w

    def _wrap_widget(self, widget) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(widget)
        return w

    def _update_swatch(self, btn: QPushButton, color: str):
        btn.setStyleSheet(f"QPushButton#colorSwatch {{ background: {color}; }}")

    def _emit_if_not_loading(self, signal, value):
        if not self._loading_element:
            signal.emit(value)

    def _on_line_width(self, v: int):
        if not self._loading_element:
            self.line_width_changed.emit(float(v))

    def _on_opacity(self, v: int):
        self._opacity_label.setText(f"{v}%")
        if not self._loading_element:
            self.opacity_changed.emit(v / 100.0)

    # --- Tool visibility ---

    def update_for_tool(self, tool_type: ToolType):
        """Show/hide settings sections based on active tool."""
        self._current_tool = tool_type
        sections = TOOL_SECTIONS.get(tool_type, {})

        self._stroke_title.setVisible(sections.get("stroke", False))
        self._stroke_row.setVisible(sections.get("stroke", False))
        self._line_style_title.setVisible(sections.get("line_style", False))
        self._line_style_widget.setVisible(sections.get("line_style", False))
        self._fill_title.setVisible(sections.get("fill", False))
        self._fill_widget.setVisible(sections.get("fill", False))
        self._text_title.setVisible(sections.get("text", False))
        self._text_widget.setVisible(sections.get("text", False))
        self._mask_title.setVisible(sections.get("mask", False))
        self._mask_widget.setVisible(sections.get("mask", False))
        self._number_title.setVisible(sections.get("number", False))
        self._number_widget.setVisible(sections.get("number", False))
        self._effects_title.setVisible(sections.get("effects", False))
        self._effects_widget.setVisible(sections.get("effects", False))

    # --- Element property loading (edit mode) ---

    def load_element_properties(self, element: AnnotationElement | None):
        """Load a selected element's properties into the panel controls."""
        self._loading_element = True
        try:
            if element is None:
                self._edit_banner.hide()
                return

            self._edit_banner.show()
            s = element.style

            # Colors
            self._fg_color = s.foreground_color
            self._update_swatch(self._fg_btn, self._fg_color)
            self._bg_color = s.background_color
            self._update_swatch(self._bg_btn, self._bg_color)

            # Stroke
            self._width_slider.setValue(int(s.line_width))
            self._width_spin.setValue(int(s.line_width))

            # Line style
            self._set_combo_by_data(self._dash_combo, s.dash_pattern)
            self._set_combo_by_data(self._cap_combo, s.cap_style)
            self._set_combo_by_data(self._join_combo, s.join_style)

            # Effects
            self._shadow_check.setChecked(s.shadow.enabled)
            self._shadow_ox_spin.setValue(int(s.shadow.offset_x))
            self._shadow_oy_spin.setValue(int(s.shadow.offset_y))
            self._shadow_blur_spin.setValue(int(s.shadow.blur_radius))
            self._shadow_color = s.shadow.color
            sc = QColor(s.shadow.color)
            self._update_swatch(self._shadow_color_btn, sc.name())
            self._opacity_slider.setValue(int(s.opacity * 100))

            # Fill (for rect/ellipse)
            if isinstance(element, (RectElement, EllipseElement)):
                self._filled_check.setChecked(element.filled)

            # Mask
            if isinstance(element, MaskElement):
                self._pixel_size_spin.setValue(element.pixel_size)

            # Number
            if isinstance(element, NumberElement):
                self._number_size_spin.setValue(int(element.size))
                self._num_font_combo.setCurrentFont(QFont(s.font_family))
                self._num_text_color = element.text_color
                self._update_swatch(self._num_text_color_btn, element.text_color)

            # Text
            if isinstance(element, TextElement):
                self._font_combo.setCurrentFont(QFont(s.font_family))
                self._font_size_spin.setValue(s.font_size)
                self._bold_btn.setChecked(element.bold)
                self._italic_btn.setChecked(element.italic)
                self._underline_btn.setChecked(element.underline)
                self._strike_btn.setChecked(element.strikethrough)
                self._text_bg_check.setChecked(element.bg_enabled)
                self._text_bg_color = element.bg_color
                self._update_swatch(self._text_bg_btn, self._text_bg_color)
                # Alignment
                if element.alignment == Qt.AlignmentFlag.AlignCenter:
                    self._align_btns["center"].setChecked(True)
                elif element.alignment == Qt.AlignmentFlag.AlignRight:
                    self._align_btns["right"].setChecked(True)
                else:
                    self._align_btns["left"].setChecked(True)
                # Direction
                if element.direction == Qt.LayoutDirection.RightToLeft:
                    self._rtl_btn.setChecked(True)
                else:
                    self._ltr_btn.setChecked(True)

            # Show appropriate sections for the element type
            etype_to_tool = {
                ElementType.PEN: ToolType.PEN,
                ElementType.BRUSH: ToolType.BRUSH,
                ElementType.LINE: ToolType.LINE,
                ElementType.ARROW: ToolType.ARROW,
                ElementType.RECTANGLE: ToolType.RECTANGLE,
                ElementType.ELLIPSE: ToolType.ELLIPSE,
                ElementType.TEXT: ToolType.TEXT,
                ElementType.NUMBER: ToolType.NUMBERING,
                ElementType.MASK: ToolType.MASQUERADE,
                ElementType.IMAGE: ToolType.SELECT,
            }
            tool_for_elem = etype_to_tool.get(element.element_type, self._current_tool)
            self.update_for_tool(tool_for_elem)

        finally:
            self._loading_element = False

    def clear_element_properties(self):
        """Clear edit mode (no element selected)."""
        self._edit_banner.hide()
        self.update_for_tool(self._current_tool)

    def _set_combo_by_data(self, combo: QComboBox, data):
        for i in range(combo.count()):
            if combo.itemData(i) == data:
                combo.setCurrentIndex(i)
                return

    # --- Color pickers ---

    def _pick_fg_color(self):
        color = QColorDialog.getColor(QColor(self._fg_color), self, "Foreground Color",
                                       QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if color.isValid():
            self._fg_color = color.name()
            self._update_swatch(self._fg_btn, self._fg_color)
            self.fg_color_changed.emit(self._fg_color)

    def _pick_bg_color(self):
        color = QColorDialog.getColor(QColor(self._bg_color), self, "Background / Fill Color",
                                       QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if color.isValid():
            self._bg_color = color.name()
            self._update_swatch(self._bg_btn, self._bg_color)
            self.bg_color_changed.emit(self._bg_color)

    def _pick_text_bg_color(self):
        color = QColorDialog.getColor(QColor(self._text_bg_color), self, "Text Background Color",
                                       QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if color.isValid():
            self._text_bg_color = color.name()
            self._update_swatch(self._text_bg_btn, self._text_bg_color)
            self.text_bg_color_changed.emit(self._text_bg_color)

    def _pick_shadow_color(self):
        color = QColorDialog.getColor(QColor(self._shadow_color), self, "Shadow Color",
                                       QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if color.isValid():
            self._shadow_color = color.name(QColor.NameFormat.HexArgb)
            self._update_swatch(self._shadow_color_btn, color.name())
            if not self._loading_element:
                self.shadow_color_changed.emit(self._shadow_color)

    def _pick_num_text_color(self):
        color = QColorDialog.getColor(QColor(self._num_text_color), self, "Number Text Color")
        if color.isValid():
            self._num_text_color = color.name()
            self._update_swatch(self._num_text_color_btn, self._num_text_color)
            if not self._loading_element:
                self.number_text_color_changed.emit(self._num_text_color)
