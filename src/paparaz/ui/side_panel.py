"""Compact side panel - sliders instead of spinboxes, per-tool sections, property inspector."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QComboBox, QPushButton, QToolButton, QButtonGroup,
    QColorDialog, QCheckBox, QFontComboBox,
    QScrollArea,
)
from PySide6.QtCore import Qt, Signal, QTimer, QPoint, QRect, QEvent
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap, QIcon, QPalette, QPen

from paparaz.tools.base import ToolType
from paparaz.ui.icons import get_icon, combo_arrow_css
from paparaz.ui.color_palette import RecentColorsPalette
from paparaz.core.elements import (
    AnnotationElement, TextElement, RectElement, EllipseElement,
    MaskElement, NumberElement, ElementType, HighlightElement,
)

def _make_swatch_pixmap(color_str: str, size: int = 16) -> QPixmap:
    """Draw a checkerboard-backed color swatch so alpha is visible."""
    c = QColor(color_str)
    pix = QPixmap(size, size)
    p = QPainter(pix)
    cs = 4  # checker square size
    light, dark = QColor(180, 180, 180), QColor(100, 100, 100)
    for row in range(0, size, cs):
        for col in range(0, size, cs):
            p.fillRect(col, row, cs, cs, light if (row // cs + col // cs) % 2 == 0 else dark)
    p.fillRect(0, 0, size, size, c)
    p.end()
    return pix


PANEL_WIDTH = 186

AUTO_HIDE_DELAY_MS = 3000  # ms before auto-hide triggers after deselect

PANEL_STYLE = """
QWidget#sidePanel {
    background: #1a1a2e;
    border: 1px solid #3a3a4e;
    border-radius: 4px;
}
QWidget#panelHeader {
    background: #111122;
    border-bottom: 1px solid #444;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    cursor: move;
}
QLabel { color: #aaa; font-size: 11px; padding: 0; margin: 0; }
QLabel#sectionTitle {
    color: #666; font-size: 10px; font-weight: bold;
    padding: 3px 0 1px 0; text-transform: uppercase;
}
QLabel#editBanner {
    color: #fff; background: #740096; font-size: 11px; font-weight: bold;
    padding: 2px 4px; border-radius: 2px;
}
QLabel#valLabel { color: #999; font-size: 11px; min-width: 28px; }
QSlider { max-height: 18px; }
QSlider::groove:horizontal { height: 3px; background: #444; border-radius: 1px; }
QSlider::handle:horizontal {
    background: #740096; width: 12px; height: 12px;
    margin: -5px 0; border-radius: 6px;
}
QSlider::handle:horizontal:hover { background: #9e2ac0; }
QComboBox, QFontComboBox {
    background: #2a2a3e; color: #ccc;
    border: 1px solid #3a3a4e; border-radius: 2px;
    padding: 2px 4px; font-size: 11px; max-height: 22px;
}
/* combo_arrow_css injected at runtime */
QComboBox QAbstractItemView {
    background: #2a2a3e; color: #ccc;
    selection-background-color: #740096; font-size: 11px;
}
QPushButton#colorSwatch {
    border: 1px solid #555; border-radius: 2px;
    min-width: 22px; min-height: 22px;
    max-width: 22px; max-height: 22px;
}
QPushButton#colorSwatch:hover { border-color: #999; }
QCheckBox { color: #aaa; font-size: 11px; spacing: 4px; }
QCheckBox::indicator {
    width: 14px; height: 14px;
    border: 1px solid #555; border-radius: 2px; background: #2a2a3e;
}
QCheckBox::indicator:checked { background: #740096; border-color: #740096; }
QToolButton {
    background: #2a2a3e; border: 1px solid #3a3a4e;
    border-radius: 2px; padding: 1px;
    min-width: 22px; min-height: 22px;
    max-width: 22px; max-height: 22px;
}
QToolButton:hover { background: #3a3a4e; }
QToolButton:checked { background: #740096; border-color: #740096; }
"""

def _sec(color=True, bg=True, stroke=False, line_style=False, fill=False,
         effects=False, text=False, mask=False, number=False, stamp=False, fill_tol=False):
    """bg=False hides the Bg swatch in the COLOR row (used when tool has its own bg control)."""
    return dict(color=color, bg=bg, stroke=stroke, line_style=line_style, fill=fill,
                effects=effects, text=text, mask=mask, number=number, stamp=stamp,
                fill_tol=fill_tol)

TOOL_SECTIONS = {
    # color  stroke  line   fill   fx     text   mask   num    stamp
    ToolType.SELECT:     _sec(color=False),
    ToolType.PEN:        _sec(color=True,  stroke=True,  line_style=True,  effects=True),
    ToolType.BRUSH:      _sec(color=True,  stroke=True,                    effects=True),
    ToolType.HIGHLIGHT:  _sec(color=True,  bg=False, stroke=True,          effects=True),
    ToolType.LINE:       _sec(color=True,  stroke=True,  line_style=True,  effects=True),
    ToolType.ARROW:      _sec(color=True,  stroke=True,  line_style=True,  effects=True),
    ToolType.RECTANGLE:  _sec(color=True,  stroke=True,  line_style=True,  fill=True,  effects=True),
    ToolType.ELLIPSE:    _sec(color=True,  stroke=True,  line_style=True,  fill=True,  effects=True),
    ToolType.TEXT:       _sec(color=True,  bg=False,                        effects=True, text=True),
    ToolType.NUMBERING:  _sec(color=True,  bg=False,                        effects=True, number=True),
    ToolType.ERASER:     _sec(color=False),
    ToolType.MASQUERADE: _sec(color=False,                                              mask=True),
    ToolType.FILL:       _sec(color=True, bg=False, fill_tol=True),
    ToolType.STAMP:      _sec(color=False,                                 effects=True, stamp=True),
    ToolType.CROP:        _sec(color=False),
    ToolType.SLICE:       _sec(color=False),
    ToolType.EYEDROPPER:  _sec(color=False),
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
    shadow_blur_x_changed = Signal(float)
    shadow_blur_y_changed = Signal(float)
    rotation_changed = Signal(float)
    opacity_changed = Signal(float)
    cap_style_changed = Signal(str)
    join_style_changed = Signal(str)
    dash_pattern_changed = Signal(str)
    filled_toggled = Signal(bool)
    pixel_size_changed = Signal(int)
    fill_tolerance_changed = Signal(int)
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
    text_stroke_enabled_changed = Signal(bool)
    text_stroke_color_changed = Signal(str)
    text_stroke_width_changed = Signal(float)
    mode_changed = Signal(str)   # 'auto', 'pinned', 'hidden'
    recent_colors_changed = Signal(list)  # emitted when palette changes

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidePanel")
        # Make a true top-level window so it can float outside the editor
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Window
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setStyleSheet(PANEL_STYLE + combo_arrow_css())
        self.setFixedWidth(PANEL_WIDTH)
        self.resize(PANEL_WIDTH, 500)
        # Floating overlay: must own its background paint explicitly
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_AlwaysShowToolTips, True)

        # Mode: 'auto' = show on select / hide on deselect after delay
        #       'pinned' = always visible
        #       'hidden' = always hidden (grip tab in editor)
        self._mode = "auto"

        # Auto-hide timer for 'auto' mode
        self._auto_hide_timer = QTimer(self)
        self._auto_hide_timer.setSingleShot(True)
        self._auto_hide_timer.setInterval(AUTO_HIDE_DELAY_MS)
        self._auto_hide_timer.timeout.connect(self._do_auto_hide)

        self._fg_color = "#FF0000"
        self._bg_color = "#FFFFFF"
        self._text_bg_color = "#FFFF00"
        self._shadow_color = "#80000000"
        self._num_text_color = "#FFFFFF"
        self._current_tool = ToolType.SELECT
        self._loading_element = False

        scroll = QScrollArea(self)
        self._scroll = scroll
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;background:#1a1a2e;}")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Make the scroll viewport opaque so it doesn't bleed through to the canvas
        vp = scroll.viewport()
        vp_pal = vp.palette()
        vp_pal.setColor(QPalette.ColorRole.Window, QColor("#1a1a2e"))
        vp.setPalette(vp_pal)
        vp.setAutoFillBackground(True)
        sw = QWidget()
        self._scroll_widget = sw
        sw_pal = sw.palette()
        sw_pal.setColor(QPalette.ColorRole.Window, QColor("#1a1a2e"))
        sw.setPalette(sw_pal)
        sw.setAutoFillBackground(True)
        self._layout = QVBoxLayout(sw)
        self._layout.setContentsMargins(6, 3, 6, 6)
        self._layout.setSpacing(1)
        scroll.setWidget(sw)

        # Header bar: mode toggle + close button
        self._header = QWidget()
        self._header.setObjectName("panelHeader")
        self._header.setFixedHeight(24)
        self._header.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        hdr_layout = QHBoxLayout(self._header)
        hdr_layout.setContentsMargins(4, 2, 4, 2)
        hdr_layout.setSpacing(2)

        self._mode_btn = QToolButton()
        self._mode_btn.setFixedSize(50, 18)
        self._mode_btn.setStyleSheet(
            "QToolButton{background:#2a2a3e;border:1px solid #3a3a4e;"
            "border-radius:3px;color:#aaa;font-size:8px;padding:0;}"
            "QToolButton:hover{background:#3a3a4e;color:#fff;}"
        )
        self._mode_btn.setToolTip("Cycle panel mode: auto → pinned → hidden")
        self._mode_btn.clicked.connect(self._cycle_mode)
        hdr_layout.addWidget(self._mode_btn)
        hdr_layout.addStretch()

        self._pin_close_btn = QToolButton()
        self._pin_close_btn.setText("×")
        self._pin_close_btn.setFixedSize(18, 18)
        self._pin_close_btn.setStyleSheet(
            "QToolButton{background:#2a2a3e;border:1px solid #3a3a4e;"
            "border-radius:3px;color:#aaa;font-size:11px;padding:0;}"
            "QToolButton:hover{background:#740096;color:#fff;border-color:#740096;}"
        )
        self._pin_close_btn.setToolTip("Hide panel")
        self._pin_close_btn.clicked.connect(self._on_close_clicked)
        hdr_layout.addWidget(self._pin_close_btn)

        # Drag label in header centre (shows user they can drag here)
        self._drag_label = QLabel("⠿ Properties")
        self._drag_label.setStyleSheet(
            "color: #555; font-size: 9px; padding: 0; background: transparent;"
        )
        self._drag_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hdr_layout.insertWidget(1, self._drag_label)

        self._update_mode_btn_text()

        # Drag support: track mouse on header background to move the panel
        self._drag_offset = None
        self._header.installEventFilter(self)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._header)
        outer.addWidget(scroll)

        # Edit banner
        self._edit_banner = QLabel("Editing element")
        self._edit_banner.setObjectName("editBanner")
        self._edit_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._edit_banner.hide()
        self._layout.addWidget(self._edit_banner)

        # ─── COLOR ───────────────────────────────────────────────────────
        color_layout = QVBoxLayout()
        color_layout.setSpacing(2)
        color_layout.setContentsMargins(0, 0, 0, 0)
        color_layout.addWidget(self._section_title("COLOR"))
        cr = QHBoxLayout()
        cr.setSpacing(4)
        self._fg_btn = self._color_btn(self._fg_color, self._pick_fg_color, "Fg color (click)")
        self._bg_btn = self._color_btn(self._bg_color, self._pick_bg_color, "Bg / fill color (click)")
        cr.addWidget(QLabel("Fg"))
        cr.addWidget(self._fg_btn)
        cr.addSpacing(8)
        self._bg_color_container = QWidget()
        bg_sub = QHBoxLayout(self._bg_color_container)
        bg_sub.setContentsMargins(0, 0, 0, 0)
        bg_sub.setSpacing(4)
        bg_sub.addWidget(QLabel("Bg"))
        bg_sub.addWidget(self._bg_btn)
        cr.addWidget(self._bg_color_container)
        cr.addStretch()
        color_layout.addLayout(cr)
        self._recent_palette = RecentColorsPalette(parent=self)
        self._recent_palette.fg_requested.connect(self._apply_palette_fg)
        self._recent_palette.bg_requested.connect(self._apply_palette_bg)
        self._recent_palette.changed.connect(lambda: self.recent_colors_changed.emit(self._recent_palette.get_colors()))
        color_layout.addWidget(self._recent_palette)
        self._color_widget = self._wrap_layout(color_layout)
        self._layout.addWidget(self._color_widget)

        # ─── STROKE (width + line style merged) ──────────────────────────
        stroke_layout = QVBoxLayout()
        stroke_layout.setSpacing(2)
        stroke_layout.setContentsMargins(0, 0, 0, 0)
        stroke_layout.addWidget(self._section_title("STROKE"))
        self._width_slider, self._width_label, self._stroke_row = self._make_slider_row("Width", 0, 50, 3, "px")
        self._width_slider.valueChanged.connect(self._on_line_width)
        stroke_layout.addWidget(self._stroke_row)
        # Dash / Cap / Join — shown only when line_style is enabled for the tool
        ls_inner = QVBoxLayout()
        ls_inner.setSpacing(2)
        ls_inner.setContentsMargins(0, 0, 0, 0)
        self._dash_combo = self._make_combo([("Solid","solid"),("Dash","dash"),("Dot","dot"),("Dash·Dot","dashdot")])
        self._dash_combo.currentIndexChanged.connect(lambda i: self._emit_if_not_loading(self.dash_pattern_changed, self._dash_combo.currentData()))
        ls_inner.addWidget(self._dash_combo)
        r2 = QHBoxLayout()
        r2.setSpacing(3)
        self._cap_combo = self._make_combo([("Round","round"),("Square","square"),("Flat","flat")])
        self._cap_combo.setToolTip("Line cap style")
        self._cap_combo.currentIndexChanged.connect(lambda i: self._emit_if_not_loading(self.cap_style_changed, self._cap_combo.currentData()))
        self._join_combo = self._make_combo([("Round","round"),("Bevel","bevel"),("Miter","miter")])
        self._join_combo.setToolTip("Line join style")
        self._join_combo.currentIndexChanged.connect(lambda i: self._emit_if_not_loading(self.join_style_changed, self._join_combo.currentData()))
        r2.addWidget(QLabel("Cap"))
        r2.addWidget(self._cap_combo)
        r2.addSpacing(4)
        r2.addWidget(QLabel("Join"))
        r2.addWidget(self._join_combo)
        ls_inner.addLayout(r2)
        self._line_style_widget = self._wrap_layout(ls_inner)
        stroke_layout.addWidget(self._line_style_widget)
        self._stroke_widget = self._wrap_layout(stroke_layout)
        # Title alias so update_for_tool can toggle the whole stroke section
        self._stroke_title = self._section_title("")   # placeholder — hidden by stroke_widget visibility
        self._line_style_title = self._section_title("")  # placeholder
        self._layout.addWidget(self._stroke_widget)

        # ─── FILL ────────────────────────────────────────────────────────
        self._fill_title = self._section_title("FILL")
        self._layout.addWidget(self._fill_title)
        self._filled_check = QCheckBox("Filled shape")
        self._filled_check.toggled.connect(lambda v: self._emit_if_not_loading(self.filled_toggled, v))
        self._fill_widget = self._wrap_widget(self._filled_check)
        self._layout.addWidget(self._fill_widget)

        # ─── FLOOD FILL TOLERANCE ─────────────────────────────────────────
        self._fill_tol_title = self._section_title("FLOOD FILL")
        self._layout.addWidget(self._fill_tol_title)
        self._tol_slider, self._tol_label, self._fill_tol_widget = self._make_slider_row("Tol", 0, 100, 15, "%")
        self._tol_slider.valueChanged.connect(lambda v: self._emit_if_not_loading(self.fill_tolerance_changed, v))
        self._layout.addWidget(self._fill_tol_widget)

        # ─── TEXT ────────────────────────────────────────────────────────
        self._text_title = self._section_title("TEXT")
        self._layout.addWidget(self._text_title)
        tl = QVBoxLayout()
        tl.setSpacing(2)
        self._font_combo = QFontComboBox()
        self._font_combo.setCurrentFont(QFont("Arial"))
        self._font_combo.currentFontChanged.connect(lambda f: self._emit_if_not_loading(self.font_family_changed, f.family()))
        tl.addWidget(self._font_combo)
        self._font_size_slider, self._font_size_label, fs_row = self._make_slider_row("Size", 6, 72, 14, "pt")
        tl.addWidget(fs_row)
        self._font_size_slider.valueChanged.connect(lambda v: self._emit_if_not_loading(self.font_size_changed, v))
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
        ar.addSpacing(6)
        self._dir_group = QButtonGroup(self)
        self._dir_group.setExclusive(True)
        self._ltr_btn = self._fmt_btn("ltr", "Left-to-right")
        self._rtl_btn = self._fmt_btn("rtl", "Right-to-left")
        self._dir_group.addButton(self._ltr_btn)
        self._dir_group.addButton(self._rtl_btn)
        self._ltr_btn.setChecked(True)
        self._ltr_btn.toggled.connect(lambda c: self._emit_if_not_loading(self.text_direction_changed, "ltr") if c else None)
        self._rtl_btn.toggled.connect(lambda c: self._emit_if_not_loading(self.text_direction_changed, "rtl") if c else None)
        ar.addWidget(self._ltr_btn)
        ar.addWidget(self._rtl_btn)
        ar.addStretch()
        tl.addLayout(ar)
        tbr = QHBoxLayout()
        tbr.setSpacing(3)
        self._text_bg_check = QCheckBox("Bg")
        self._text_bg_check.toggled.connect(lambda v: self._emit_if_not_loading(self.text_bg_enabled_changed, v))
        self._text_bg_btn = self._color_btn(self._text_bg_color, self._pick_text_bg_color, "Text background color")
        tbr.addWidget(self._text_bg_check)
        tbr.addWidget(self._text_bg_btn)
        tbr.addStretch()
        tl.addLayout(tbr)
        # Stroke / outline row
        self._text_stroke_color = "#000000"
        tsr = QHBoxLayout()
        tsr.setSpacing(3)
        self._text_stroke_check = QCheckBox("Outline")
        self._text_stroke_check.toggled.connect(lambda v: self._emit_if_not_loading(self.text_stroke_enabled_changed, v))
        self._text_stroke_btn = self._color_btn(self._text_stroke_color, self._pick_text_stroke_color, "Outline color")
        tsr.addWidget(self._text_stroke_check)
        tsr.addWidget(self._text_stroke_btn)
        tsr.addStretch()
        tl.addLayout(tsr)
        self._text_stroke_width_slider, self._text_stroke_width_label, tsw_row = \
            self._make_slider_row("Width", 1, 20, 4, "")
        self._text_stroke_width_slider.valueChanged.connect(
            lambda v: self._emit_if_not_loading(self.text_stroke_width_changed, v * 0.5))
        tl.addWidget(tsw_row)
        self._text_widget = self._wrap_layout(tl)
        self._layout.addWidget(self._text_widget)

        # ─── MARKER (Numbering) ───────────────────────────────────────────
        self._number_title = self._section_title("MARKER")
        self._layout.addWidget(self._number_title)
        nl = QVBoxLayout()
        nl.setSpacing(2)
        self._num_size_slider, self._num_size_label, ns_w = self._make_slider_row("Size", 16, 80, 16, "px")
        self._num_size_slider.valueChanged.connect(lambda v: self._emit_if_not_loading(self.number_size_changed, float(v)))
        nl.addWidget(ns_w)
        self._num_font_combo = QFontComboBox()
        self._num_font_combo.setCurrentFont(QFont("Arial"))
        self._num_font_combo.currentFontChanged.connect(lambda f: self._emit_if_not_loading(self.font_family_changed, f.family()))
        nl.addWidget(self._num_font_combo)
        ntc = QHBoxLayout()
        ntc.setSpacing(3)
        ntc.addWidget(QLabel("Text color"))
        self._num_text_color_btn = self._color_btn(self._num_text_color, self._pick_num_text_color, "Number text color")
        ntc.addWidget(self._num_text_color_btn)
        ntc.addStretch()
        nl.addLayout(ntc)
        self._number_widget = self._wrap_layout(nl)
        self._layout.addWidget(self._number_widget)

        # ─── PIXELATE ────────────────────────────────────────────────────
        self._mask_title = self._section_title("PIXELATE")
        self._layout.addWidget(self._mask_title)
        self._pixel_slider, self._pixel_label, self._mask_widget = self._make_slider_row("Block", 2, 50, 10, "px")
        self._pixel_slider.valueChanged.connect(lambda v: self._emit_if_not_loading(self.pixel_size_changed, v))
        self._layout.addWidget(self._mask_widget)

        # ─── STAMP ───────────────────────────────────────────────────────
        self._stamp_title = self._section_title("STAMP")
        self._layout.addWidget(self._stamp_title)
        sl = QVBoxLayout()
        sl.setSpacing(2)
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
        if stamp_row:
            stamp_row.addStretch()
        self._stamp_size_slider, self._stamp_size_label, ss_w = self._make_slider_row("Size", 24, 128, 48, "px")
        self._stamp_size_slider.valueChanged.connect(lambda v: self._emit_if_not_loading(self.stamp_size_changed, float(v)))
        sl.addWidget(ss_w)
        self._stamp_widget = self._wrap_layout(sl)
        self._layout.addWidget(self._stamp_widget)

        # ─── EFFECTS ─────────────────────────────────────────────────────
        self._effects_title = self._section_title("EFFECTS")
        self._layout.addWidget(self._effects_title)
        el = QVBoxLayout()
        el.setSpacing(2)
        self._opacity_slider, self._opacity_label, op_w = self._make_slider_row("Opac", 10, 100, 100, "%")
        self._opacity_slider.valueChanged.connect(self._on_opacity)
        el.addWidget(op_w)
        self._rotation_slider, self._rotation_label, rot_w = self._make_slider_row("Rot°", 0, 359, 0, "°")
        self._rotation_slider.valueChanged.connect(lambda v: self._emit_if_not_loading(self.rotation_changed, float(v)))
        el.addWidget(rot_w)

        # Shadow toggle
        sh_row = QHBoxLayout()
        sh_row.setSpacing(4)
        self._shadow_check = QCheckBox("Shadow")
        self._shadow_check.toggled.connect(lambda v: self._emit_if_not_loading(self.shadow_toggled, v))
        sh_row.addWidget(self._shadow_check)
        self._shadow_color_btn = self._color_btn("#000000", self._pick_shadow_color, "Shadow color")
        sh_row.addWidget(self._shadow_color_btn)
        sh_row.addStretch()
        el.addLayout(sh_row)

        # Shadow details — shown when shadow enabled
        sd = QVBoxLayout()
        sd.setSpacing(2)
        sd.setContentsMargins(6, 0, 0, 0)
        # Offset row: X and Y side by side
        off_row = QHBoxLayout()
        off_row.setSpacing(4)
        off_row.addWidget(QLabel("Off"))
        self._shadow_ox_slider, self._shadow_ox_label, sox_w = self._make_slider_row("X", -30, 30, 3, "")
        self._shadow_ox_slider.valueChanged.connect(lambda v: self._emit_if_not_loading(self.shadow_offset_x_changed, float(v)))
        self._shadow_oy_slider, self._shadow_oy_label, soy_w = self._make_slider_row("Y", -30, 30, 3, "")
        self._shadow_oy_slider.valueChanged.connect(lambda v: self._emit_if_not_loading(self.shadow_offset_y_changed, float(v)))
        sd.addWidget(sox_w)
        sd.addWidget(soy_w)
        # Blur row: separate X and Y blur
        self._shadow_blur_x_slider, self._shadow_blur_x_label, sbx_w = self._make_slider_row("BlX", 0, 40, 5, "")
        self._shadow_blur_x_slider.valueChanged.connect(lambda v: self._emit_if_not_loading(self.shadow_blur_x_changed, float(v)))
        self._shadow_blur_y_slider, self._shadow_blur_y_label, sby_w = self._make_slider_row("BlY", 0, 40, 5, "")
        self._shadow_blur_y_slider.valueChanged.connect(lambda v: self._emit_if_not_loading(self.shadow_blur_y_changed, float(v)))
        sd.addWidget(sbx_w)
        sd.addWidget(sby_w)
        self._shadow_details_widget = self._wrap_layout(sd)
        self._shadow_details_widget.hide()
        self._shadow_check.toggled.connect(self._shadow_details_widget.setVisible)
        el.addWidget(self._shadow_details_widget)

        self._effects_widget = self._wrap_layout(el)
        self._layout.addWidget(self._effects_widget)

        self._layout.addStretch()
        self.update_for_tool(ToolType.SELECT)

        # Theme colors used by paintEvent (defaults match the hardcoded dark theme)
        self._theme_bg = QColor(26, 26, 46)
        self._theme_border = QColor(60, 60, 90)

    def paintEvent(self, event):
        """Solid background with right-side separator (for docked layout)."""
        p = QPainter(self)
        p.setBrush(self._theme_bg)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(self.rect())
        # Right border separator
        p.setPen(QPen(self._theme_border, 1))
        p.drawLine(self.rect().topRight(), self.rect().bottomRight())
        p.end()

    # --- Per-tool property persistence ---

    def get_current_properties(self) -> dict:
        """Snapshot all currently visible property values for the active tool."""
        s = TOOL_SECTIONS.get(self._current_tool, {})
        props = {}
        if s.get("color"):
            props["foreground_color"] = self._fg_color
            props["background_color"] = self._bg_color
        if s.get("stroke"):
            props["line_width"] = self._width_slider.value()
        if s.get("line_style"):
            props["cap_style"] = self._cap_combo.currentData()
            props["join_style"] = self._join_combo.currentData()
            props["dash_pattern"] = self._dash_combo.currentData()
        if s.get("fill"):
            props["filled"] = self._filled_check.isChecked()
        if s.get("effects"):
            props["opacity"] = self._opacity_slider.value() / 100.0
            props["rotation"] = float(self._rotation_slider.value())
            props["shadow_enabled"] = self._shadow_check.isChecked()
            props["shadow_color"] = self._shadow_color
            props["shadow_offset_x"] = self._shadow_ox_slider.value()
            props["shadow_offset_y"] = self._shadow_oy_slider.value()
            props["shadow_blur_x"] = self._shadow_blur_x_slider.value()
            props["shadow_blur_y"] = self._shadow_blur_y_slider.value()
        if s.get("text"):
            props["font_family"] = self._font_combo.currentText()
            props["font_size"] = self._font_size_slider.value()
            props["text_bold"] = self._bold_btn.isChecked()
            props["text_italic"] = self._italic_btn.isChecked()
            props["text_underline"] = self._underline_btn.isChecked()
            props["text_strikethrough"] = self._strike_btn.isChecked()
            for v, b in self._align_btns.items():
                if b.isChecked():
                    props["text_alignment"] = v
                    break
            props["text_direction"] = "rtl" if self._rtl_btn.isChecked() else "ltr"
            props["text_bg_enabled"] = self._text_bg_check.isChecked()
            props["text_bg_color"] = self._text_bg_color
        if s.get("fill_tol"):
            props["fill_tolerance"] = self._tol_slider.value()
        if s.get("mask"):
            props["pixel_size"] = self._pixel_slider.value()
        if s.get("number"):
            props["number_size"] = self._num_size_slider.value()
            props["number_text_color"] = self._num_text_color
            props["number_font_family"] = self._num_font_combo.currentText()
        if s.get("stamp"):
            props["stamp_size"] = self._stamp_size_slider.value()
            checked = self._stamp_group.checkedButton()
            if checked:
                props["stamp_id"] = checked.toolTip().lower().replace(" ", "_")
        return props

    def apply_properties_silent(self, props: dict):
        """Apply a property dict to the panel UI without emitting change signals.
        Used when loading saved per-tool properties (no undo entries created)."""
        old = self._loading_element
        self._loading_element = True
        try:
            if "foreground_color" in props:
                self._fg_color = props["foreground_color"]
                self._update_swatch(self._fg_btn, self._fg_color)
            if "background_color" in props:
                self._bg_color = props["background_color"]
                self._update_swatch(self._bg_btn, self._bg_color)
            if "line_width" in props:
                self._width_slider.setValue(int(props["line_width"]))
            if "cap_style" in props:
                self._set_combo_data(self._cap_combo, props["cap_style"])
            if "join_style" in props:
                self._set_combo_data(self._join_combo, props["join_style"])
            if "dash_pattern" in props:
                self._set_combo_data(self._dash_combo, props["dash_pattern"])
            if "opacity" in props:
                self._opacity_slider.setValue(int(float(props["opacity"]) * 100))
            if "shadow_enabled" in props:
                self._shadow_check.setChecked(bool(props["shadow_enabled"]))
                self._shadow_details_widget.setVisible(bool(props["shadow_enabled"]))
            if "shadow_color" in props:
                self._shadow_color = props["shadow_color"]
                from PySide6.QtGui import QColor as _QColor
                self._update_swatch(self._shadow_color_btn, _QColor(props["shadow_color"]).name())
            if "rotation" in props:
                self._rotation_slider.setValue(int(float(props["rotation"])) % 360)
            if "shadow_offset_x" in props:
                self._shadow_ox_slider.setValue(int(props["shadow_offset_x"]))
            if "shadow_offset_y" in props:
                self._shadow_oy_slider.setValue(int(props["shadow_offset_y"]))
            if "shadow_blur_x" in props:
                self._shadow_blur_x_slider.setValue(int(props["shadow_blur_x"]))
            if "shadow_blur_y" in props:
                self._shadow_blur_y_slider.setValue(int(props["shadow_blur_y"]))
            # Legacy migration: single blur_radius maps to both axes
            if "shadow_blur" in props and "shadow_blur_x" not in props:
                self._shadow_blur_x_slider.setValue(int(props["shadow_blur"]))
                self._shadow_blur_y_slider.setValue(int(props["shadow_blur"]))
            if "font_family" in props:
                from PySide6.QtGui import QFont as _QFont
                self._font_combo.setCurrentFont(_QFont(props["font_family"]))
            if "font_size" in props:
                self._font_size_slider.setValue(int(props["font_size"]))
            if "text_bold" in props:
                self._bold_btn.setChecked(bool(props["text_bold"]))
            if "text_italic" in props:
                self._italic_btn.setChecked(bool(props["text_italic"]))
            if "text_underline" in props:
                self._underline_btn.setChecked(bool(props["text_underline"]))
            if "text_strikethrough" in props:
                self._strike_btn.setChecked(bool(props["text_strikethrough"]))
            if "text_alignment" in props:
                btn = self._align_btns.get(props["text_alignment"])
                if btn:
                    btn.setChecked(True)
            if "text_direction" in props:
                (self._rtl_btn if props["text_direction"] == "rtl" else self._ltr_btn).setChecked(True)
            if "text_bg_enabled" in props:
                self._text_bg_check.setChecked(bool(props["text_bg_enabled"]))
            if "text_bg_color" in props:
                self._text_bg_color = props["text_bg_color"]
                self._update_swatch(self._text_bg_btn, props["text_bg_color"])
            if "fill_tolerance" in props:
                self._tol_slider.setValue(int(props["fill_tolerance"]))
            if "pixel_size" in props:
                self._pixel_slider.setValue(int(props["pixel_size"]))
            if "number_size" in props:
                self._num_size_slider.setValue(int(props["number_size"]))
            if "number_text_color" in props:
                self._num_text_color = props["number_text_color"]
                self._update_swatch(self._num_text_color_btn, props["number_text_color"])
            if "number_font_family" in props:
                from PySide6.QtGui import QFont as _QFont
                self._num_font_combo.setCurrentFont(_QFont(props["number_font_family"]))
            if "stamp_size" in props:
                self._stamp_size_slider.setValue(int(props["stamp_size"]))
        finally:
            self._loading_element = old

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

    def _update_swatch(self, btn: QPushButton, color: str):
        pix = _make_swatch_pixmap(color)
        btn.setIcon(QIcon(pix))
        btn.setIconSize(pix.size())
        btn.setStyleSheet("QPushButton#colorSwatch { background: none; }")

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
        self._color_widget.setVisible(s.get("color", False))
        if s.get("color", False):
            self._bg_color_container.setVisible(s.get("bg", True))
        # Stroke section: show if stroke OR line_style
        show_stroke = s.get("stroke", False) or s.get("line_style", False)
        self._stroke_widget.setVisible(show_stroke)
        # Line style sub-section within stroke
        self._line_style_widget.setVisible(s.get("line_style", False))
        self._fill_title.setVisible(s.get("fill", False))
        self._fill_widget.setVisible(s.get("fill", False))
        self._fill_tol_title.setVisible(s.get("fill_tol", False))
        self._fill_tol_widget.setVisible(s.get("fill_tol", False))
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
            self._shadow_details_widget.setVisible(s.shadow.enabled)
            self._shadow_ox_slider.setValue(int(s.shadow.offset_x))
            self._shadow_oy_slider.setValue(int(s.shadow.offset_y))
            self._shadow_blur_x_slider.setValue(int(s.shadow.blur_x))
            self._shadow_blur_y_slider.setValue(int(s.shadow.blur_y))
            self._shadow_color = s.shadow.color
            self._update_swatch(self._shadow_color_btn, self._shadow_color)
            self._opacity_slider.setValue(int(s.opacity * 100))
            self._rotation_slider.setValue(int(getattr(element, 'rotation', 0.0)) % 360)

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
                self._text_stroke_check.setChecked(element.stroke_enabled)
                self._text_stroke_color = element.stroke_color
                self._update_swatch(self._text_stroke_btn, element.stroke_color)
                self._text_stroke_width_slider.setValue(int(element.stroke_width * 2))
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
                ElementType.HIGHLIGHT: ToolType.HIGHLIGHT,
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

    # --- Panel mode ---

    @property
    def mode(self) -> str:
        return self._mode

    def showEvent(self, event):
        super().showEvent(event)
        self.raise_()

    # ── Theme ─────────────────────────────────────────────────────────────────

    def apply_theme(self, theme: dict):
        """Apply an app_theme dict to panel stylesheet and repaint colors."""
        from paparaz.ui.app_theme import build_panel_qss
        from paparaz.ui.icons import combo_arrow_css
        self.setStyleSheet(build_panel_qss(theme) + combo_arrow_css())
        bg1    = theme.get("bg1",           "#1a1a2e")
        bg2    = theme.get("bg2",           "#2a2a3e")
        bg3    = theme.get("bg3",           "#3a3a4e")
        fg     = theme.get("fg",            "#cccccc")
        fg_br  = theme.get("fg_bright",     "#ffffff")
        fg_dim = theme.get("fg_dim",        "#888888")
        brd    = theme.get("border2",       "#3a3a4e")
        acc    = theme.get("accent",        "#740096")

        self._theme_bg = QColor(bg1)
        self._theme_border = QColor(theme.get("border", "#3c3c5a"))

        # Re-skin header buttons (they have per-widget QSS that overrides inheritance)
        self._mode_btn.setStyleSheet(
            f"QToolButton{{background:{bg2};border:1px solid {brd};"
            f"border-radius:3px;color:{fg_dim};font-size:8px;padding:0;}}"
            f"QToolButton:hover{{background:{bg3};color:{fg_br};}}"
        )
        self._pin_close_btn.setStyleSheet(
            f"QToolButton{{background:{bg2};border:1px solid {brd};"
            f"border-radius:3px;color:{fg};font-size:11px;padding:0;}}"
            f"QToolButton:hover{{background:{acc};color:{fg_br};border-color:{acc};}}"
        )
        self._drag_label.setStyleSheet(
            f"color:{fg_dim};font-size:9px;padding:0;background:transparent;"
        )

        # Update scroll area + content widget palette so they match
        bg_color = QColor(bg1)
        self._scroll.setStyleSheet(f"QScrollArea{{border:none;background:{bg1};}}")
        for w in (self._scroll.viewport(), self._scroll_widget):
            pal = w.palette()
            pal.setColor(QPalette.ColorRole.Window, bg_color)
            w.setPalette(pal)
        self.update()

    # ── Recent colors public API ──────────────────────────────────────────────

    def set_recent_colors(self, colors: list):
        """Load persisted recent colors into the palette (called at startup)."""
        self._recent_palette.set_colors(colors)

    def get_recent_colors(self) -> list:
        """Return current recent colors list for persistence."""
        return self._recent_palette.get_colors()

    # ── Mode ─────────────────────────────────────────────────────────────────

    def set_mode(self, mode: str):
        """Set panel mode: 'auto', 'pinned', or 'hidden'."""
        self._mode = mode
        self._update_mode_btn_text()
        self._auto_hide_timer.stop()
        if mode == "hidden":
            self.hide()
        elif mode == "pinned":
            self.show()
        # 'auto': visibility managed by on_element_selected
        self.mode_changed.emit(mode)

    def eventFilter(self, obj, event):
        """Drag the floating panel by pressing on the header background."""
        if obj is self._header:
            et = event.type()
            if et == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self._drag_offset = event.globalPosition().toPoint() - self.mapToGlobal(QPoint(0, 0))
            elif et == QEvent.Type.MouseMove and event.buttons() & Qt.MouseButton.LeftButton:
                if self._drag_offset is not None:
                    # Panel is a top-level window: move() uses screen coordinates
                    new_pos = event.globalPosition().toPoint() - self._drag_offset
                    self.move(new_pos)
            elif et == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
                self._drag_offset = None
        return False  # never consume — buttons still receive their own events

    def _cycle_mode(self):
        order = ["auto", "pinned", "hidden"]
        idx = order.index(self._mode)
        self.set_mode(order[(idx + 1) % len(order)])

    def _on_close_clicked(self):
        """Hide button clicked — switch to hidden mode."""
        self.set_mode("hidden")

    def _update_mode_btn_text(self):
        labels = {"auto": "● Auto", "pinned": "📌 Pin", "hidden": "✕ Hide"}
        self._mode_btn.setText(labels.get(self._mode, self._mode))

    def _do_auto_hide(self):
        if self._mode == "auto":
            self.hide()

    def on_element_selected(self, element):
        """Called by editor when element selection changes.
        Manages show/hide according to current mode.
        """
        self._auto_hide_timer.stop()
        if element is not None:
            self.load_element_properties(element)
            if self._mode in ("auto", "pinned"):
                self.show()
        else:
            self.clear_element_properties()
            if self._mode == "auto":
                self._auto_hide_timer.start()
            # pinned: stay visible; hidden: stay hidden

    # --- Color pickers ---

    def _pick_fg_color(self):
        c = QColorDialog.getColor(QColor(self._fg_color), self, "Foreground",
                                   QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if c.isValid():
            self._fg_color = c.name(QColor.NameFormat.HexArgb)
            self._update_swatch(self._fg_btn, self._fg_color)
            self._recent_palette.add_color(self._fg_color)
            self.fg_color_changed.emit(self._fg_color)

    def _pick_bg_color(self):
        c = QColorDialog.getColor(QColor(self._bg_color), self, "Background",
                                   QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if c.isValid():
            self._bg_color = c.name(QColor.NameFormat.HexArgb)
            self._update_swatch(self._bg_btn, self._bg_color)
            self._recent_palette.add_color(self._bg_color)
            self.bg_color_changed.emit(self._bg_color)

    def _pick_text_bg_color(self):
        c = QColorDialog.getColor(QColor(self._text_bg_color), self, "Text Background",
                                   QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if c.isValid():
            self._text_bg_color = c.name(QColor.NameFormat.HexArgb)
            self._update_swatch(self._text_bg_btn, self._text_bg_color)
            self._recent_palette.add_color(self._text_bg_color)
            self.text_bg_color_changed.emit(self._text_bg_color)

    def _pick_text_stroke_color(self):
        c = QColorDialog.getColor(QColor(self._text_stroke_color), self, "Outline Color")
        if c.isValid():
            self._text_stroke_color = c.name()
            self._update_swatch(self._text_stroke_btn, self._text_stroke_color)
            self._recent_palette.add_color(self._text_stroke_color)
            self._emit_if_not_loading(self.text_stroke_color_changed, self._text_stroke_color)

    def _pick_shadow_color(self):
        c = QColorDialog.getColor(QColor(self._shadow_color), self, "Shadow",
                                   QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if c.isValid():
            self._shadow_color = c.name(QColor.NameFormat.HexArgb)
            self._update_swatch(self._shadow_color_btn, self._shadow_color)
            self._recent_palette.add_color(self._shadow_color)
            if not self._loading_element:
                self.shadow_color_changed.emit(self._shadow_color)

    def _pick_num_text_color(self):
        c = QColorDialog.getColor(QColor(self._num_text_color), self, "Number Text",
                                  QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if c.isValid():
            self._num_text_color = c.name(QColor.NameFormat.HexArgb)
            self._update_swatch(self._num_text_color_btn, self._num_text_color)
            self._recent_palette.add_color(self._num_text_color)
            if not self._loading_element:
                self.number_text_color_changed.emit(self._num_text_color)

    def _apply_palette_fg(self, color: str):
        """Apply a color from the recent palette as foreground."""
        self._fg_color = color
        self._update_swatch(self._fg_btn, self._fg_color)
        self.fg_color_changed.emit(self._fg_color)

    def _apply_palette_bg(self, color: str):
        """Apply a color from the recent palette as background."""
        self._bg_color = color
        self._update_swatch(self._bg_btn, self._bg_color)
        self.bg_color_changed.emit(self._bg_color)
