"""Compact side panel - sliders instead of spinboxes, per-tool sections, property inspector."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QComboBox, QPushButton, QToolButton, QButtonGroup,
    QColorDialog, QCheckBox, QFontComboBox,
    QScrollArea,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap, QIcon

from paparaz.tools.base import ToolType
from paparaz.ui.icons import get_icon
from paparaz.core.elements import (
    AnnotationElement, TextElement, RectElement, EllipseElement,
    MaskElement, NumberElement, ElementType,
)

PANEL_WIDTH = 186

PANEL_STYLE = """
QWidget#sidePanel { background: #1a1a2e; border-right: 1px solid #333; }
QLabel { color: #aaa; font-size: 9px; padding: 0; margin: 0; }
QLabel#sectionTitle {
    color: #666; font-size: 8px; font-weight: bold;
    padding: 3px 0 1px 0; text-transform: uppercase;
}
QLabel#editBanner {
    color: #fff; background: #740096; font-size: 9px; font-weight: bold;
    padding: 2px 4px; border-radius: 2px;
}
QLabel#valLabel { color: #999; font-size: 9px; min-width: 26px; }
QSlider { max-height: 16px; }
QSlider::groove:horizontal { height: 3px; background: #444; border-radius: 1px; }
QSlider::handle:horizontal {
    background: #740096; width: 10px; height: 10px;
    margin: -4px 0; border-radius: 5px;
}
QSlider::handle:horizontal:hover { background: #9e2ac0; }
QComboBox, QFontComboBox {
    background: #2a2a3e; color: #ccc;
    border: 1px solid #3a3a4e; border-radius: 2px;
    padding: 1px 3px; font-size: 9px; max-height: 18px;
}
QComboBox::drop-down { border: none; width: 14px; }
QComboBox QAbstractItemView {
    background: #2a2a3e; color: #ccc;
    selection-background-color: #740096; font-size: 9px;
}
QPushButton#colorSwatch {
    border: 1px solid #555; border-radius: 2px;
    min-width: 20px; min-height: 20px;
    max-width: 20px; max-height: 20px;
}
QPushButton#colorSwatch:hover { border-color: #999; }
QCheckBox { color: #aaa; font-size: 9px; spacing: 3px; }
QCheckBox::indicator {
    width: 12px; height: 12px;
    border: 1px solid #555; border-radius: 2px; background: #2a2a3e;
}
QCheckBox::indicator:checked { background: #740096; border-color: #740096; }
QToolButton {
    background: #2a2a3e; border: 1px solid #3a3a4e;
    border-radius: 2px; padding: 1px;
    min-width: 20px; min-height: 20px;
    max-width: 20px; max-height: 20px;
}
QToolButton:hover { background: #3a3a4e; }
QToolButton:checked { background: #740096; border-color: #740096; }
"""

TOOL_SECTIONS = {
    ToolType.SELECT:     {"stroke": False, "line_style": False, "fill": False, "effects": True, "text": False, "mask": False, "number": False, "stamp": False},
    ToolType.PEN:        {"stroke": True,  "line_style": True,  "fill": False, "effects": True, "text": False, "mask": False, "number": False, "stamp": False},
    ToolType.BRUSH:      {"stroke": True,  "line_style": False, "fill": False, "effects": True, "text": False, "mask": False, "number": False, "stamp": False},
    ToolType.LINE:       {"stroke": True,  "line_style": True,  "fill": False, "effects": True, "text": False, "mask": False, "number": False, "stamp": False},
    ToolType.ARROW:      {"stroke": True,  "line_style": True,  "fill": False, "effects": True, "text": False, "mask": False, "number": False, "stamp": False},
    ToolType.RECTANGLE:  {"stroke": True,  "line_style": True,  "fill": True,  "effects": True, "text": False, "mask": False, "number": False, "stamp": False},
    ToolType.ELLIPSE:    {"stroke": True,  "line_style": True,  "fill": True,  "effects": True, "text": False, "mask": False, "number": False, "stamp": False},
    ToolType.TEXT:        {"stroke": False, "line_style": False, "fill": False, "effects": True, "text": True,  "mask": False, "number": False, "stamp": False},
    ToolType.NUMBERING:  {"stroke": False, "line_style": False, "fill": False, "effects": True, "text": False, "mask": False, "number": True,  "stamp": False},
    ToolType.ERASER:     {"stroke": False, "line_style": False, "fill": False, "effects": False,"text": False, "mask": False, "number": False, "stamp": False},
    ToolType.MASQUERADE: {"stroke": False, "line_style": False, "fill": False, "effects": True, "text": False, "mask": True,  "number": False, "stamp": False},
    ToolType.FILL:       {"stroke": False, "line_style": False, "fill": False, "effects": False,"text": False, "mask": False, "number": False, "stamp": False},
    ToolType.STAMP:      {"stroke": False, "line_style": False, "fill": False, "effects": True, "text": False, "mask": False, "number": False, "stamp": True},
}


class SidePanel(QWidget):
    """Compact left-side panel with sliders, per-tool sections, property inspector."""

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
    filled_toggled = Signal(bool)
    pixel_size_changed = Signal(int)
    number_size_changed = Signal(float)
    number_text_color_changed = Signal(str)
    stamp_selected = Signal(str)
    stamp_size_changed = Signal(float)
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
        self._shadow_color = "#80000000"
        self._num_text_color = "#FFFFFF"
        self._current_tool = ToolType.SELECT
        self._loading_element = False

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        sw = QWidget()
        self._layout = QVBoxLayout(sw)
        self._layout.setContentsMargins(6, 3, 6, 6)
        self._layout.setSpacing(1)
        scroll.setWidget(sw)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        # Edit banner
        self._edit_banner = QLabel("Editing element")
        self._edit_banner.setObjectName("editBanner")
        self._edit_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._edit_banner.hide()
        self._layout.addWidget(self._edit_banner)

        # --- COLOR ---
        self._layout.addWidget(self._section_title("COLOR"))
        cr = QHBoxLayout()
        cr.setSpacing(4)
        self._fg_btn = self._color_btn(self._fg_color, self._pick_fg_color, "Fg")
        self._bg_btn = self._color_btn(self._bg_color, self._pick_bg_color, "Bg")
        cr.addWidget(QLabel("Fg"))
        cr.addWidget(self._fg_btn)
        cr.addSpacing(4)
        cr.addWidget(QLabel("Bg"))
        cr.addWidget(self._bg_btn)
        cr.addStretch()
        self._layout.addLayout(cr)

        # --- STROKE ---
        self._stroke_title = self._section_title("STROKE")
        self._layout.addWidget(self._stroke_title)
        self._width_slider, self._width_label, self._stroke_row = self._make_slider_row("Width", 1, 50, 3, "px")
        self._layout.addWidget(self._stroke_row)
        self._width_slider.valueChanged.connect(self._on_line_width)

        # --- LINE STYLE ---
        self._line_style_title = self._section_title("LINE")
        self._layout.addWidget(self._line_style_title)
        ls = QVBoxLayout()
        ls.setSpacing(1)
        self._dash_combo = self._make_combo([("Solid","solid"),("Dash","dash"),("Dot","dot"),("Dash·Dot","dashdot")])
        self._dash_combo.currentIndexChanged.connect(lambda i: self._emit_if_not_loading(self.dash_pattern_changed, self._dash_combo.currentData()))
        ls.addWidget(self._dash_combo)
        r2 = QHBoxLayout()
        r2.setSpacing(2)
        self._cap_combo = self._make_combo([("R","round"),("S","square"),("F","flat")])
        self._cap_combo.setToolTip("Cap: Round / Square / Flat")
        self._cap_combo.currentIndexChanged.connect(lambda i: self._emit_if_not_loading(self.cap_style_changed, self._cap_combo.currentData()))
        self._join_combo = self._make_combo([("R","round"),("B","bevel"),("M","miter")])
        self._join_combo.setToolTip("Join: Round / Bevel / Miter")
        self._join_combo.currentIndexChanged.connect(lambda i: self._emit_if_not_loading(self.join_style_changed, self._join_combo.currentData()))
        r2.addWidget(QLabel("Cap"))
        r2.addWidget(self._cap_combo)
        r2.addWidget(QLabel("Join"))
        r2.addWidget(self._join_combo)
        ls.addLayout(r2)
        self._line_style_widget = self._wrap_layout(ls)
        self._layout.addWidget(self._line_style_widget)

        # --- FILL ---
        self._fill_title = self._section_title("FILL")
        self._layout.addWidget(self._fill_title)
        self._filled_check = QCheckBox("Filled")
        self._filled_check.toggled.connect(lambda v: self._emit_if_not_loading(self.filled_toggled, v))
        self._fill_widget = self._wrap_widget(self._filled_check)
        self._layout.addWidget(self._fill_widget)

        # --- TEXT ---
        self._text_title = self._section_title("TEXT")
        self._layout.addWidget(self._text_title)
        tl = QVBoxLayout()
        tl.setSpacing(1)
        self._font_combo = QFontComboBox()
        self._font_combo.setCurrentFont(QFont("Arial"))
        self._font_combo.currentFontChanged.connect(lambda f: self._emit_if_not_loading(self.font_family_changed, f.family()))
        tl.addWidget(self._font_combo)
        self._font_size_slider, self._font_size_label, fs_row = self._make_slider_row("Size", 6, 72, 14, "pt")
        tl.addWidget(fs_row)
        self._font_size_slider.valueChanged.connect(lambda v: self._emit_if_not_loading(self.font_size_changed, v))

        # Format buttons row
        fr = QHBoxLayout()
        fr.setSpacing(2)
        self._bold_btn = self._fmt_btn("bold", "Bold")
        self._bold_btn.toggled.connect(lambda v: self._emit_if_not_loading(self.text_bold_changed, v))
        self._italic_btn = self._fmt_btn("italic", "Italic")
        self._italic_btn.toggled.connect(lambda v: self._emit_if_not_loading(self.text_italic_changed, v))
        self._underline_btn = self._fmt_btn("underline", "Underline")
        self._underline_btn.toggled.connect(lambda v: self._emit_if_not_loading(self.text_underline_changed, v))
        self._strike_btn = self._fmt_btn("strikethrough", "Strikethrough")
        self._strike_btn.toggled.connect(lambda v: self._emit_if_not_loading(self.text_strikethrough_changed, v))
        for b in [self._bold_btn, self._italic_btn, self._underline_btn, self._strike_btn]:
            fr.addWidget(b)
        fr.addStretch()
        tl.addLayout(fr)

        # Align + direction row
        ar = QHBoxLayout()
        ar.setSpacing(2)
        self._align_group = QButtonGroup(self)
        self._align_group.setExclusive(True)
        self._align_btns = {}
        for n, t, v in [("align_left","L","left"),("align_center","C","center"),("align_right","R","right")]:
            b = self._fmt_btn(n, t)
            self._align_group.addButton(b)
            self._align_btns[v] = b
            b.toggled.connect(lambda checked, val=v: self._emit_if_not_loading(self.text_alignment_changed, val) if checked else None)
            ar.addWidget(b)
        self._align_btns["left"].setChecked(True)
        ar.addSpacing(4)
        self._dir_group = QButtonGroup(self)
        self._dir_group.setExclusive(True)
        self._ltr_btn = self._fmt_btn("ltr", "LTR")
        self._rtl_btn = self._fmt_btn("rtl", "RTL")
        self._dir_group.addButton(self._ltr_btn)
        self._dir_group.addButton(self._rtl_btn)
        self._ltr_btn.setChecked(True)
        self._ltr_btn.toggled.connect(lambda c: self._emit_if_not_loading(self.text_direction_changed, "ltr") if c else None)
        self._rtl_btn.toggled.connect(lambda c: self._emit_if_not_loading(self.text_direction_changed, "rtl") if c else None)
        ar.addWidget(self._ltr_btn)
        ar.addWidget(self._rtl_btn)
        ar.addStretch()
        tl.addLayout(ar)

        # Text bg
        tbr = QHBoxLayout()
        tbr.setSpacing(3)
        self._text_bg_check = QCheckBox("Bg")
        self._text_bg_check.toggled.connect(lambda v: self._emit_if_not_loading(self.text_bg_enabled_changed, v))
        self._text_bg_btn = self._color_btn(self._text_bg_color, self._pick_text_bg_color, "")
        tbr.addWidget(self._text_bg_check)
        tbr.addWidget(self._text_bg_btn)
        tbr.addStretch()
        tl.addLayout(tbr)
        self._text_widget = self._wrap_layout(tl)
        self._layout.addWidget(self._text_widget)

        # --- MASK ---
        self._mask_title = self._section_title("PIXELATE")
        self._layout.addWidget(self._mask_title)
        self._pixel_slider, self._pixel_label, self._mask_widget = self._make_slider_row("Block", 2, 50, 10, "px")
        self._pixel_slider.valueChanged.connect(lambda v: self._emit_if_not_loading(self.pixel_size_changed, v))
        self._layout.addWidget(self._mask_widget)

        # --- NUMBER ---
        self._number_title = self._section_title("MARKER")
        self._layout.addWidget(self._number_title)
        nl = QVBoxLayout()
        nl.setSpacing(1)
        self._num_size_slider, self._num_size_label, ns_w = self._make_slider_row("Size", 16, 80, 28, "px")
        self._num_size_slider.valueChanged.connect(lambda v: self._emit_if_not_loading(self.number_size_changed, float(v)))
        nl.addWidget(ns_w)
        self._num_font_combo = QFontComboBox()
        self._num_font_combo.setCurrentFont(QFont("Arial"))
        self._num_font_combo.currentFontChanged.connect(lambda f: self._emit_if_not_loading(self.font_family_changed, f.family()))
        nl.addWidget(self._num_font_combo)
        ntc = QHBoxLayout()
        ntc.setSpacing(3)
        ntc.addWidget(QLabel("Color"))
        self._num_text_color_btn = self._color_btn(self._num_text_color, self._pick_num_text_color, "")
        ntc.addWidget(self._num_text_color_btn)
        ntc.addStretch()
        nl.addLayout(ntc)
        self._number_widget = self._wrap_layout(nl)
        self._layout.addWidget(self._number_widget)

        # --- STAMP ---
        self._stamp_title = self._section_title("STAMP")
        self._layout.addWidget(self._stamp_title)
        sl = QVBoxLayout()
        sl.setSpacing(2)
        # Stamp picker grid (flow layout with small icon buttons)
        from paparaz.ui.stamps import STAMPS, get_stamp_renderer
        self._stamp_group = QButtonGroup(self)
        self._stamp_group.setExclusive(True)
        stamp_row = None
        for i, (sid, sdata) in enumerate(STAMPS.items()):
            if i % 4 == 0:
                stamp_row = QHBoxLayout()
                stamp_row.setSpacing(2)
                sl.addLayout(stamp_row)
            btn = QToolButton()
            btn.setToolTip(sdata["label"])
            btn.setCheckable(True)
            btn.setFixedSize(32, 32)
            # Render stamp to icon
            pix = QPixmap(28, 28)
            pix.fill(Qt.GlobalColor.transparent)
            rp = QPainter(pix)
            r = get_stamp_renderer(sid)
            if r:
                r.render(rp)
            rp.end()
            btn.setIcon(QIcon(pix))
            btn.setIconSize(pix.size())
            btn.setStyleSheet("QToolButton{background:#2a2a3e;border:1px solid #3a3a4e;border-radius:4px;min-width:32px;min-height:32px;max-width:32px;max-height:32px;}QToolButton:hover{background:#3a3a4e;}QToolButton:checked{background:#740096;border-color:#740096;}")
            self._stamp_group.addButton(btn)
            stamp_row.addWidget(btn)
            btn.toggled.connect(lambda checked, s=sid: self._emit_if_not_loading(self.stamp_selected, s) if checked else None)
            if i == 0:
                btn.setChecked(True)
        # Pad last row
        if stamp_row:
            stamp_row.addStretch()
        # Stamp size
        self._stamp_size_slider, self._stamp_size_label, ss_w = self._make_slider_row("Size", 24, 128, 48, "px")
        self._stamp_size_slider.valueChanged.connect(lambda v: self._emit_if_not_loading(self.stamp_size_changed, float(v)))
        sl.addWidget(ss_w)
        self._stamp_widget = self._wrap_layout(sl)
        self._layout.addWidget(self._stamp_widget)

        # --- EFFECTS ---
        self._effects_title = self._section_title("EFFECTS")
        self._layout.addWidget(self._effects_title)
        el = QVBoxLayout()
        el.setSpacing(1)
        self._opacity_slider, self._opacity_label, op_w = self._make_slider_row("Opac", 10, 100, 100, "%")
        self._opacity_slider.valueChanged.connect(self._on_opacity)
        el.addWidget(op_w)
        self._shadow_check = QCheckBox("Shadow")
        self._shadow_check.toggled.connect(lambda v: self._emit_if_not_loading(self.shadow_toggled, v))
        el.addWidget(self._shadow_check)
        scr = QHBoxLayout()
        scr.setSpacing(3)
        scr.addWidget(QLabel("Color"))
        self._shadow_color_btn = self._color_btn("#000000", self._pick_shadow_color, "")
        scr.addWidget(self._shadow_color_btn)
        scr.addStretch()
        el.addLayout(scr)
        self._shadow_ox_slider, self._shadow_ox_label, sox_w = self._make_slider_row("X", -20, 20, 3, "")
        self._shadow_ox_slider.valueChanged.connect(lambda v: self._emit_if_not_loading(self.shadow_offset_x_changed, float(v)))
        el.addWidget(sox_w)
        self._shadow_oy_slider, self._shadow_oy_label, soy_w = self._make_slider_row("Y", -20, 20, 3, "")
        self._shadow_oy_slider.valueChanged.connect(lambda v: self._emit_if_not_loading(self.shadow_offset_y_changed, float(v)))
        el.addWidget(soy_w)
        self._shadow_blur_slider, self._shadow_blur_label, sb_w = self._make_slider_row("Blur", 0, 20, 5, "")
        self._shadow_blur_slider.valueChanged.connect(lambda v: self._emit_if_not_loading(self.shadow_blur_changed, float(v)))
        el.addWidget(sb_w)
        self._effects_widget = self._wrap_layout(el)
        self._layout.addWidget(self._effects_widget)

        self._layout.addStretch()
        self.update_for_tool(ToolType.SELECT)

    # --- Builders ---

    def _section_title(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("sectionTitle")
        return lbl

    def _make_slider_row(self, label: str, lo: int, hi: int, default: int, suffix: str):
        """Create compact: Label Slider Value row. Returns (slider, value_label, container_widget)."""
        row = QHBoxLayout()
        row.setSpacing(3)
        row.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(label)
        lbl.setFixedWidth(28)
        row.addWidget(lbl)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(lo, hi)
        slider.setValue(default)
        row.addWidget(slider, 1)
        val_lbl = QLabel(f"{default}{suffix}")
        val_lbl.setObjectName("valLabel")
        val_lbl.setFixedWidth(30)
        val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(val_lbl)
        slider.valueChanged.connect(lambda v: val_lbl.setText(f"{v}{suffix}"))
        w = QWidget()
        w.setLayout(row)
        return slider, val_lbl, w

    def _make_combo(self, items: list[tuple[str, str]]) -> QComboBox:
        cb = QComboBox()
        for label, val in items:
            cb.addItem(label, val)
        return cb

    def _color_btn(self, color: str, callback, tooltip: str) -> QPushButton:
        btn = QPushButton()
        btn.setObjectName("colorSwatch")
        btn.setToolTip(tooltip)
        self._update_swatch(btn, color)
        btn.clicked.connect(callback)
        return btn

    def _fmt_btn(self, icon_name: str, tooltip: str) -> QToolButton:
        btn = QToolButton()
        btn.setIcon(get_icon(icon_name, 14))
        btn.setToolTip(tooltip)
        btn.setCheckable(True)
        btn.setFixedSize(20, 20)
        return btn

    def _wrap_layout(self, layout) -> QWidget:
        w = QWidget()
        w.setLayout(layout)
        return w

    def _wrap_widget(self, widget) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.addWidget(widget)
        return w

    def _update_swatch(self, btn, color):
        btn.setStyleSheet(f"QPushButton#colorSwatch{{background:{color};}}")

    def _emit_if_not_loading(self, signal, value):
        if not self._loading_element:
            signal.emit(value)

    def _on_line_width(self, v):
        if not self._loading_element:
            self.line_width_changed.emit(float(v))

    def _on_opacity(self, v):
        if not self._loading_element:
            self.opacity_changed.emit(v / 100.0)

    # --- Visibility ---

    def update_for_tool(self, tool_type: ToolType):
        self._current_tool = tool_type
        s = TOOL_SECTIONS.get(tool_type, {})
        self._stroke_title.setVisible(s.get("stroke", False))
        self._stroke_row.setVisible(s.get("stroke", False))
        self._line_style_title.setVisible(s.get("line_style", False))
        self._line_style_widget.setVisible(s.get("line_style", False))
        self._fill_title.setVisible(s.get("fill", False))
        self._fill_widget.setVisible(s.get("fill", False))
        self._text_title.setVisible(s.get("text", False))
        self._text_widget.setVisible(s.get("text", False))
        self._mask_title.setVisible(s.get("mask", False))
        self._mask_widget.setVisible(s.get("mask", False))
        self._number_title.setVisible(s.get("number", False))
        self._number_widget.setVisible(s.get("number", False))
        self._stamp_title.setVisible(s.get("stamp", False))
        self._stamp_widget.setVisible(s.get("stamp", False))
        self._effects_title.setVisible(s.get("effects", False))
        self._effects_widget.setVisible(s.get("effects", False))

    # --- Element property loading ---

    def load_element_properties(self, element: AnnotationElement | None):
        self._loading_element = True
        try:
            if element is None:
                self._edit_banner.hide()
                return

            self._edit_banner.show()
            s = element.style

            self._fg_color = s.foreground_color
            self._update_swatch(self._fg_btn, self._fg_color)
            self._bg_color = s.background_color
            self._update_swatch(self._bg_btn, self._bg_color)

            self._width_slider.setValue(int(s.line_width))
            self._set_combo_data(self._dash_combo, s.dash_pattern)
            self._set_combo_data(self._cap_combo, s.cap_style)
            self._set_combo_data(self._join_combo, s.join_style)

            self._shadow_check.setChecked(s.shadow.enabled)
            self._shadow_ox_slider.setValue(int(s.shadow.offset_x))
            self._shadow_oy_slider.setValue(int(s.shadow.offset_y))
            self._shadow_blur_slider.setValue(int(s.shadow.blur_radius))
            self._shadow_color = s.shadow.color
            sc = QColor(s.shadow.color)
            self._update_swatch(self._shadow_color_btn, sc.name())
            self._opacity_slider.setValue(int(s.opacity * 100))

            if isinstance(element, (RectElement, EllipseElement)):
                self._filled_check.setChecked(element.filled)
            if isinstance(element, MaskElement):
                self._pixel_slider.setValue(element.pixel_size)
            if isinstance(element, NumberElement):
                self._num_size_slider.setValue(int(element.size))
                self._num_font_combo.setCurrentFont(QFont(s.font_family))
                self._num_text_color = element.text_color
                self._update_swatch(self._num_text_color_btn, element.text_color or "#FFFFFF")
            if isinstance(element, TextElement):
                self._font_combo.setCurrentFont(QFont(s.font_family))
                self._font_size_slider.setValue(s.font_size)
                self._bold_btn.setChecked(element.bold)
                self._italic_btn.setChecked(element.italic)
                self._underline_btn.setChecked(element.underline)
                self._strike_btn.setChecked(element.strikethrough)
                self._text_bg_check.setChecked(element.bg_enabled)
                self._text_bg_color = element.bg_color
                self._update_swatch(self._text_bg_btn, element.bg_color)
                if element.alignment == Qt.AlignmentFlag.AlignCenter:
                    self._align_btns["center"].setChecked(True)
                elif element.alignment == Qt.AlignmentFlag.AlignRight:
                    self._align_btns["right"].setChecked(True)
                else:
                    self._align_btns["left"].setChecked(True)
                if element.direction == Qt.LayoutDirection.RightToLeft:
                    self._rtl_btn.setChecked(True)
                else:
                    self._ltr_btn.setChecked(True)

            etype_map = {
                ElementType.PEN: ToolType.PEN, ElementType.BRUSH: ToolType.BRUSH,
                ElementType.LINE: ToolType.LINE, ElementType.ARROW: ToolType.ARROW,
                ElementType.RECTANGLE: ToolType.RECTANGLE, ElementType.ELLIPSE: ToolType.ELLIPSE,
                ElementType.TEXT: ToolType.TEXT, ElementType.NUMBER: ToolType.NUMBERING,
                ElementType.MASK: ToolType.MASQUERADE, ElementType.IMAGE: ToolType.SELECT,
                ElementType.STAMP: ToolType.STAMP,
            }
            self.update_for_tool(etype_map.get(element.element_type, self._current_tool))
        finally:
            self._loading_element = False

    def clear_element_properties(self):
        self._edit_banner.hide()
        self.update_for_tool(self._current_tool)

    def _set_combo_data(self, combo, data):
        for i in range(combo.count()):
            if combo.itemData(i) == data:
                combo.setCurrentIndex(i)
                return

    # --- Color pickers ---

    def _pick_fg_color(self):
        c = QColorDialog.getColor(QColor(self._fg_color), self, "Foreground",
                                   QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if c.isValid():
            self._fg_color = c.name()
            self._update_swatch(self._fg_btn, self._fg_color)
            self.fg_color_changed.emit(self._fg_color)

    def _pick_bg_color(self):
        c = QColorDialog.getColor(QColor(self._bg_color), self, "Background",
                                   QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if c.isValid():
            self._bg_color = c.name()
            self._update_swatch(self._bg_btn, self._bg_color)
            self.bg_color_changed.emit(self._bg_color)

    def _pick_text_bg_color(self):
        c = QColorDialog.getColor(QColor(self._text_bg_color), self, "Text Bg",
                                   QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if c.isValid():
            self._text_bg_color = c.name()
            self._update_swatch(self._text_bg_btn, self._text_bg_color)
            self.text_bg_color_changed.emit(self._text_bg_color)

    def _pick_shadow_color(self):
        c = QColorDialog.getColor(QColor(self._shadow_color), self, "Shadow",
                                   QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if c.isValid():
            self._shadow_color = c.name(QColor.NameFormat.HexArgb)
            self._update_swatch(self._shadow_color_btn, c.name())
            if not self._loading_element:
                self.shadow_color_changed.emit(self._shadow_color)

    def _pick_num_text_color(self):
        c = QColorDialog.getColor(QColor(self._num_text_color), self, "Number Text")
        if c.isValid():
            self._num_text_color = c.name()
            self._update_swatch(self._num_text_color_btn, self._num_text_color)
            if not self._loading_element:
                self.number_text_color_changed.emit(self._num_text_color)
