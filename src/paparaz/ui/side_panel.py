"""Compact side panel - sliders instead of spinboxes, per-tool sections, property inspector."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QComboBox, QPushButton, QToolButton, QButtonGroup,
    QColorDialog, QFontComboBox,
    QScrollArea,
)
from PySide6.QtCore import Qt, Signal, QTimer, QPoint, QRect, QEvent, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap, QIcon, QPalette, QPen

from paparaz.tools.base import ToolType
from paparaz.ui.icons import get_icon, combo_arrow_css
from paparaz.ui.color_palette import RecentColorsPalette
from paparaz.core.elements import (
    AnnotationElement, TextElement, RectElement, EllipseElement,
    MaskElement, NumberElement, ElementType, HighlightElement,
    PenElement, BrushElement, LineElement, ArrowElement,
    ElementStyle, Shadow,
)
from PySide6.QtCore import QPointF, QRectF

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


PANEL_WIDTH = 260

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
}
QLabel { color: #aaa; font-size: 11px; padding: 0; margin: 0; }
QLabel#sectionTitle {
    color: #666; font-size: 10px; font-weight: bold;
    padding: 6px 0 4px 0; text-transform: uppercase;
    border-bottom: 1px solid #2a2a4a;
    margin-top: 2px;
}
QLabel#editBanner {
    color: #fff; background: #740096; font-size: 11px; font-weight: bold;
    padding: 2px 4px; border-radius: 2px;
}
QLabel#valLabel { color: #999; font-size: 11px; min-width: 32px; text-align: right; }
QSlider { min-height: 20px; max-height: 22px; }
QSlider::groove:horizontal { height: 4px; background: #444; border-radius: 2px; }
QSlider::handle:horizontal {
    background: #740096; width: 14px; height: 14px;
    margin: -5px 0; border-radius: 7px;
}
QSlider::handle:horizontal:hover { background: #9e2ac0; }
QSlider::sub-page:horizontal { background: #740096; border-radius: 2px; }
QSlider:disabled { opacity: 0.35; }
QComboBox, QFontComboBox {
    background: #2a2a3e; color: #ccc;
    border: 1px solid #3a3a4e; border-radius: 3px;
    padding: 3px 6px; font-size: 11px; min-height: 24px;
}
QComboBox QAbstractItemView {
    background: #2a2a3e; color: #ccc;
    selection-background-color: #740096; font-size: 11px;
}
QPushButton#colorSwatch {
    border: 1px solid #555; border-radius: 3px;
    min-width: 24px; min-height: 24px;
    max-width: 24px; max-height: 24px;
}
QPushButton#colorSwatch:hover { border-color: #999; }
QPushButton#colorSwatch:disabled { opacity: 0.30; }
QToolButton {
    background: #2a2a3e; border: 1px solid #3a3a4e;
    border-radius: 3px; padding: 1px;
    min-width: 24px; min-height: 24px;
    max-width: 24px; max-height: 24px;
}
QToolButton:hover { background: #3a3a4e; }
QToolButton:checked { background: #740096; border-color: #740096; }
QToolButton:disabled { opacity: 0.30; }
QToolButton#toggleBtn {
    min-width: 46px; max-width: 92px; min-height: 22px; max-height: 22px;
    font-size: 10px; padding: 0 6px; border-radius: 3px; color: #888; text-align: center;
}
QToolButton#toggleBtn:hover { color: #ccc; }
QToolButton#toggleBtn:checked { color: #fff; }
QToolButton#unlinkBtn {
    min-width: 20px; max-width: 20px; min-height: 20px; max-height: 20px;
    font-size: 10px; padding: 0; border-radius: 3px; color: #888;
}
QToolButton#unlinkBtn:checked { background: #740096; color: #fff; border-color: #740096; }
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
    ToolType.LINE:         _sec(color=True,  stroke=True,  line_style=True,  effects=True),
    ToolType.ARROW:        _sec(color=True,  stroke=True,  line_style=True,  effects=True),
    ToolType.CURVED_ARROW: _sec(color=True,  stroke=True,  line_style=True,  effects=True),
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
        self.resize(PANEL_WIDTH, 400)
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
        self._auto_hide_timer.setInterval(AUTO_HIDE_DELAY_MS)  # may be overridden by set_auto_hide_ms()
        self._auto_hide_timer.timeout.connect(self._do_auto_hide)

        # Fade animation for show/hide
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(150)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._fade_anim.finished.connect(self._on_fade_finished)
        self._fade_target_visible = True

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
        scroll.setStyleSheet(
            "QScrollArea{border:none;background:#1a1a2e;}"
            "QScrollBar:vertical{background:#1a1a2e;width:6px;margin:0;}"
            "QScrollBar::handle:vertical{background:#444;border-radius:3px;min-height:20px;}"
            "QScrollBar::handle:vertical:hover{background:#666;}"
            "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}"
        )
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Make the scroll viewport opaque so it doesn't bleed through to the canvas
        vp = scroll.viewport()
        vp_pal = vp.palette()
        vp_pal.setColor(QPalette.ColorRole.Window, QColor("#1a1a2e"))
        vp.setPalette(vp_pal)
        vp.setAutoFillBackground(True)
        sw = QWidget()
        sw.setMaximumWidth(PANEL_WIDTH)
        self._scroll_widget = sw
        sw_pal = sw.palette()
        sw_pal.setColor(QPalette.ColorRole.Window, QColor("#1a1a2e"))
        sw.setPalette(sw_pal)
        sw.setAutoFillBackground(True)
        self._layout = QVBoxLayout(sw)
        self._layout.setContentsMargins(8, 4, 8, 8)
        self._layout.setSpacing(2)
        scroll.setWidget(sw)

        # ── Header bar ───────────────────────────────────────────────────
        self._header = QWidget()
        self._header.setObjectName("panelHeader")
        self._header.setFixedHeight(32)
        self._header.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        hdr_layout = QHBoxLayout(self._header)
        hdr_layout.setContentsMargins(6, 2, 6, 2)
        hdr_layout.setSpacing(4)

        # Drag grip indicator
        _drag_grip = QLabel("⠿")
        _drag_grip.setStyleSheet("color:#444; font-size:15px; padding:0; background:transparent;")
        _drag_grip.setCursor(Qt.CursorShape.SizeAllCursor)
        _drag_grip.setToolTip("Drag to move panel")
        hdr_layout.addWidget(_drag_grip)

        # Title: shows "Properties" or current element type
        self._title_label = QLabel("Properties")
        self._title_label.setStyleSheet(
            "color:#dddddd; font-size:13px; font-weight:bold; padding:0; background:transparent;"
        )
        hdr_layout.addWidget(self._title_label)
        hdr_layout.addStretch()

        # Pin toggle — when checked the panel stays open always
        _pin_style = (
            "QToolButton{background:#2a2a3e;border:1px solid #3a3a4e;"
            "border-radius:4px;color:#888;font-size:10px;padding:1px 5px;min-width:36px;min-height:24px;}"
            "QToolButton:hover{background:#3a3a4e;color:#ccc;}"
            "QToolButton:checked{background:#740096;border-color:#9e2ac0;color:#fff;}"
        )
        self._pin_btn = QToolButton()
        self._pin_btn.setText("📌 Pin")
        self._pin_btn.setCheckable(True)
        self._pin_btn.setStyleSheet(_pin_style)
        self._pin_btn.setToolTip(
            "Pin panel open\n"
            "ON  – panel stays visible even when nothing is selected\n"
            "OFF – panel auto-hides 3 s after you deselect"
        )
        self._pin_btn.toggled.connect(self._on_pin_toggled)
        hdr_layout.addWidget(self._pin_btn)

        # Close button
        _close_style = (
            "QToolButton{background:#2a2a3e;border:1px solid #3a3a4e;"
            "border-radius:4px;color:#888;font-size:12px;padding:0;"
            "min-width:24px;min-height:24px;max-width:24px;max-height:24px;}"
            "QToolButton:hover{background:#8b0000;border-color:#cc3333;color:#fff;}"
        )
        self._pin_close_btn = QToolButton()
        self._pin_close_btn.setText("✕")
        self._pin_close_btn.setStyleSheet(_close_style)
        self._pin_close_btn.setToolTip("Close panel\n(reopen via the grip tab on the canvas edge)")
        self._pin_close_btn.clicked.connect(self._on_close_clicked)
        hdr_layout.addWidget(self._pin_close_btn)

        # ── Element preview strip ─────────────────────────────────────────
        self._preview_label = QLabel()
        self._preview_label.setFixedHeight(60)
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_label.setStyleSheet(
            "background:#111827; border-bottom:1px solid #2a2a4a; color:#444; font-size:10px;"
        )
        self._preview_label.setText("No selection")
        self._preview_label.hide()  # hidden until element is selected
        self._preview_element = None

        # Drag support: track mouse on header background to move the panel
        self._drag_offset = None
        self._header.installEventFilter(self)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._header)
        outer.addWidget(self._preview_label)
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
        cr.addWidget(QLabel("Color"))
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
        recent_lbl = self._section_title("RECENT COLORS")
        recent_lbl.setToolTip("Left-click to set foreground color · Right-click to set background color")
        color_layout.addWidget(recent_lbl)
        self._recent_palette = RecentColorsPalette(parent=self)
        self._recent_palette.fg_requested.connect(self._apply_palette_fg)
        self._recent_palette.bg_requested.connect(self._apply_palette_bg)
        self._recent_palette.changed.connect(lambda: self.recent_colors_changed.emit(self._recent_palette.get_colors()))
        color_layout.addWidget(self._recent_palette)
        self._color_widget = self._wrap_layout(color_layout)
        self._layout.addWidget(self._color_widget)

        # ─── STROKE (width + line style merged) ──────────────────────────
        stroke_layout = QVBoxLayout()
        stroke_layout.setSpacing(3)
        stroke_layout.setContentsMargins(0, 0, 0, 0)
        stroke_layout.addWidget(self._section_title("STROKE"))
        self._width_slider, self._width_label, self._stroke_row = self._make_slider_row("Width", 0, 50, 3, "px")
        self._width_slider.valueChanged.connect(self._on_line_width)
        stroke_layout.addWidget(self._stroke_row)
        # Dash / Cap / Join — shown only when line_style is enabled for the tool
        ls_inner = QVBoxLayout()
        ls_inner.setSpacing(3)
        ls_inner.setContentsMargins(0, 0, 0, 0)
        self._dash_combo = self._make_combo([("Solid","solid"),("Dash","dash"),("Dot","dot"),("Dash·Dot","dashdot")])
        self._dash_combo.currentIndexChanged.connect(lambda i: self._emit_if_not_loading(self.dash_pattern_changed, self._dash_combo.currentData()))
        ls_inner.addWidget(self._dash_combo)
        self._cap_combo = self._make_combo([("Round","round"),("Square","square"),("Flat","flat")])
        self._cap_combo.setToolTip("Line cap style")
        self._cap_combo.currentIndexChanged.connect(lambda i: self._emit_if_not_loading(self.cap_style_changed, self._cap_combo.currentData()))
        self._join_combo = self._make_combo([("Round","round"),("Bevel","bevel"),("Miter","miter")])
        self._join_combo.setToolTip("Line join style")
        self._join_combo.currentIndexChanged.connect(lambda i: self._emit_if_not_loading(self.join_style_changed, self._join_combo.currentData()))
        cap_row = QHBoxLayout()
        cap_row.setSpacing(6)
        cap_row.addWidget(QLabel("Cap"))
        cap_row.addWidget(self._cap_combo)
        ls_inner.addLayout(cap_row)
        join_row = QHBoxLayout()
        join_row.setSpacing(6)
        join_row.addWidget(QLabel("Join"))
        join_row.addWidget(self._join_combo)
        ls_inner.addLayout(join_row)
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
        self._filled_check = QToolButton()
        self._filled_check.setObjectName("toggleBtn")
        self._filled_check.setText("Filled shape")
        self._filled_check.setCheckable(True)
        self._filled_check.setMaximumWidth(PANEL_WIDTH - 12)
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
        tl.setSpacing(3)
        self._font_combo = QFontComboBox()
        self._font_combo.setCurrentFont(QFont("Arial"))
        self._font_combo.currentFontChanged.connect(lambda f: self._emit_if_not_loading(self.font_family_changed, f.family()))
        tl.addWidget(self._font_combo)
        self._font_size_slider, self._font_size_label, fs_row = self._make_slider_row("Size", 6, 120, 14, "pt")
        tl.addWidget(fs_row)
        self._font_size_slider.valueChanged.connect(lambda v: self._emit_if_not_loading(self.font_size_changed, v))
        fr = QHBoxLayout()
        fr.setSpacing(3)
        self._bold_btn = self._fmt_btn("bold", "Bold", label="B", bold=True)
        self._bold_btn.toggled.connect(lambda v: self._emit_if_not_loading(self.text_bold_changed, v))
        self._italic_btn = self._fmt_btn("italic", "Italic", label="I", italic=True)
        self._italic_btn.toggled.connect(lambda v: self._emit_if_not_loading(self.text_italic_changed, v))
        self._underline_btn = self._fmt_btn("underline", "Underline", label="U", underline=True)
        self._underline_btn.toggled.connect(lambda v: self._emit_if_not_loading(self.text_underline_changed, v))
        self._strike_btn = self._fmt_btn("strikethrough", "Strikethrough", label="S̶")
        self._strike_btn.toggled.connect(lambda v: self._emit_if_not_loading(self.text_strikethrough_changed, v))
        for b in [self._bold_btn, self._italic_btn, self._underline_btn, self._strike_btn]:
            fr.addWidget(b)
        fr.addStretch()
        tl.addLayout(fr)
        ar = QHBoxLayout()
        ar.setSpacing(3)
        self._align_group = QButtonGroup(self)
        self._align_group.setExclusive(True)
        self._align_btns = {}
        for n, t, v, lbl in [("align_left","Left","left","≡←"),("align_center","Center","center","≡"),("align_right","Right","right","≡→")]:
            b = self._fmt_btn(n, t, label=lbl)
            self._align_group.addButton(b)
            self._align_btns[v] = b
            b.toggled.connect(lambda checked, val=v: self._emit_if_not_loading(self.text_alignment_changed, val) if checked else None)
            ar.addWidget(b)
        self._align_btns["left"].setChecked(True)
        ar.addSpacing(6)
        self._dir_group = QButtonGroup(self)
        self._dir_group.setExclusive(True)
        self._ltr_btn = self._fmt_btn("ltr", "Left-to-right text direction", label="LTR")
        self._rtl_btn = self._fmt_btn("rtl", "Right-to-left text direction", label="RTL")
        self._dir_group.addButton(self._ltr_btn)
        self._dir_group.addButton(self._rtl_btn)
        self._ltr_btn.setChecked(True)
        self._ltr_btn.toggled.connect(lambda c: self._emit_if_not_loading(self.text_direction_changed, "ltr") if c else None)
        self._rtl_btn.toggled.connect(lambda c: self._emit_if_not_loading(self.text_direction_changed, "rtl") if c else None)
        ar.addWidget(self._ltr_btn)
        ar.addWidget(self._rtl_btn)
        ar.addStretch()
        tl.addLayout(ar)
        # Text background toggle + color (swatch greyed when toggle is OFF)
        tbr = QHBoxLayout()
        tbr.setSpacing(4)
        self._text_bg_btn = self._color_btn(self._text_bg_color, self._pick_text_bg_color, "Text background color")
        self._text_bg_btn.setEnabled(False)
        self._text_bg_check = QToolButton()
        self._text_bg_check.setObjectName("toggleBtn")
        self._text_bg_check.setText("Bg")
        self._text_bg_check.setCheckable(True)
        self._text_bg_check.toggled.connect(lambda v: self._emit_if_not_loading(self.text_bg_enabled_changed, v))
        self._text_bg_check.toggled.connect(self._text_bg_btn.setEnabled)
        tbr.addWidget(self._text_bg_check)
        tbr.addWidget(self._text_bg_btn)
        tbr.addStretch()
        tl.addLayout(tbr)
        # Outline toggle + color (swatch greyed when toggle is OFF) + width (hidden when OFF)
        self._text_stroke_color = "#000000"
        tsr = QHBoxLayout()
        tsr.setSpacing(4)
        self._text_stroke_btn = self._color_btn(self._text_stroke_color, self._pick_text_stroke_color, "Outline color")
        self._text_stroke_btn.setEnabled(False)
        self._text_stroke_check = QToolButton()
        self._text_stroke_check.setObjectName("toggleBtn")
        self._text_stroke_check.setText("Outline")
        self._text_stroke_check.setCheckable(True)
        self._text_stroke_check.toggled.connect(lambda v: self._emit_if_not_loading(self.text_stroke_enabled_changed, v))
        self._text_stroke_check.toggled.connect(self._text_stroke_btn.setEnabled)
        tsr.addWidget(self._text_stroke_check)
        tsr.addWidget(self._text_stroke_btn)
        tsr.addStretch()
        tl.addLayout(tsr)
        self._text_stroke_width_slider, self._text_stroke_width_label, tsw_row = \
            self._make_slider_row("Width", 1, 20, 4, "")
        self._text_stroke_width_slider.valueChanged.connect(
            lambda v: self._emit_if_not_loading(self.text_stroke_width_changed, v * 0.5))
        self._text_stroke_width_widget = tsw_row
        self._text_stroke_width_widget.hide()
        self._text_stroke_check.toggled.connect(self._text_stroke_width_widget.setVisible)
        self._text_stroke_check.toggled.connect(lambda: QTimer.singleShot(0, self._adjust_height))
        tl.addWidget(self._text_stroke_width_widget)
        self._text_widget = self._wrap_layout(tl)
        self._layout.addWidget(self._text_widget)

        # ─── MARKER (Numbering) ───────────────────────────────────────────
        self._number_title = self._section_title("MARKER")
        self._layout.addWidget(self._number_title)
        nl = QVBoxLayout()
        nl.setSpacing(3)
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
        sl.setSpacing(3)
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
        el.setSpacing(3)
        self._opacity_slider, self._opacity_label, op_w = self._make_slider_row("Opac", 10, 100, 100, "%")
        self._opacity_slider.valueChanged.connect(self._on_opacity)
        el.addWidget(op_w)
        self._rotation_slider, self._rotation_label, rot_w = self._make_slider_row("Rot°", 0, 359, 0, "°")
        self._rotation_slider.valueChanged.connect(lambda v: self._emit_if_not_loading(self.rotation_changed, float(v)))
        el.addWidget(rot_w)

        # Shadow toggle
        sh_row = QHBoxLayout()
        sh_row.setSpacing(6)
        self._shadow_check = QToolButton()
        self._shadow_check.setObjectName("toggleBtn")
        self._shadow_check.setText("Shadow")
        self._shadow_check.setCheckable(True)
        self._shadow_check.toggled.connect(lambda v: self._emit_if_not_loading(self.shadow_toggled, v))
        sh_row.addWidget(self._shadow_check)
        self._shadow_color_btn = self._color_btn("#000000", self._pick_shadow_color, "Shadow color")
        sh_row.addWidget(self._shadow_color_btn)
        sh_row.addStretch()
        el.addLayout(sh_row)

        # Shadow details — shown when shadow enabled
        sd = QVBoxLayout()
        sd.setSpacing(3)
        sd.setContentsMargins(6, 2, 0, 0)
        self._shadow_ox_slider, self._shadow_ox_label, sox_w = self._make_slider_row("Off X", -30, 30, 3, "")
        self._shadow_ox_slider.valueChanged.connect(lambda v: self._emit_if_not_loading(self.shadow_offset_x_changed, float(v)))
        self._shadow_oy_slider, self._shadow_oy_label, soy_w = self._make_slider_row("Off Y", -30, 30, 3, "")
        self._shadow_oy_slider.valueChanged.connect(lambda v: self._emit_if_not_loading(self.shadow_offset_y_changed, float(v)))
        sd.addWidget(sox_w)
        sd.addWidget(soy_w)
        # Blur — linked (default) with optional unlink for separate X/Y axes
        blur_hbox = QHBoxLayout()
        blur_hbox.setSpacing(3)
        self._shadow_blur_slider, self._shadow_blur_label, sbl_w = self._make_slider_row("Blur", 0, 40, 5, "")
        self._shadow_blur_slider.valueChanged.connect(self._on_shadow_blur_linked)
        self._shadow_unlink_btn = QToolButton()
        self._shadow_unlink_btn.setObjectName("unlinkBtn")
        self._shadow_unlink_btn.setText("≠")
        self._shadow_unlink_btn.setCheckable(True)
        self._shadow_unlink_btn.setToolTip("Unlink X/Y blur axes for independent control")
        self._shadow_unlink_btn.toggled.connect(self._on_shadow_unlink_toggled)
        blur_hbox.addWidget(sbl_w, 1)
        blur_hbox.addWidget(self._shadow_unlink_btn)
        self._shadow_blur_linked_widget = self._wrap_layout(blur_hbox)
        sd.addWidget(self._shadow_blur_linked_widget)
        # Separate X/Y blur sliders (hidden unless unlinked)
        self._shadow_blur_x_slider, self._shadow_blur_x_label, sbx_w = self._make_slider_row("Blur X", 0, 40, 5, "")
        self._shadow_blur_x_slider.valueChanged.connect(lambda v: self._emit_if_not_loading(self.shadow_blur_x_changed, float(v)))
        self._shadow_blur_y_slider, self._shadow_blur_y_label, sby_w = self._make_slider_row("Blur Y", 0, 40, 5, "")
        self._shadow_blur_y_slider.valueChanged.connect(lambda v: self._emit_if_not_loading(self.shadow_blur_y_changed, float(v)))
        self._shadow_blur_xy_widget = QWidget()
        xy_vbox = QVBoxLayout(self._shadow_blur_xy_widget)
        xy_vbox.setContentsMargins(0, 0, 0, 0)
        xy_vbox.setSpacing(3)
        xy_vbox.addWidget(sbx_w)
        xy_vbox.addWidget(sby_w)
        self._shadow_blur_xy_widget.hide()
        sd.addWidget(self._shadow_blur_xy_widget)
        self._shadow_details_widget = self._wrap_layout(sd)
        self._shadow_details_widget.hide()
        self._shadow_check.toggled.connect(self._shadow_details_widget.setVisible)
        self._shadow_check.toggled.connect(lambda: QTimer.singleShot(0, self._adjust_height))
        el.addWidget(self._shadow_details_widget)

        self._effects_widget = self._wrap_layout(el)
        self._layout.addWidget(self._effects_widget)

        self._layout.addStretch()
        self.update_for_tool(ToolType.SELECT)

        # Theme colors used by paintEvent (defaults match the hardcoded dark theme)
        self._theme_bg = QColor(26, 26, 46)
        self._theme_border = QColor(60, 60, 90)

        # Live preview: refresh the preview strip whenever any property changes
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(30)  # debounce 30ms
        self._preview_timer.timeout.connect(self._do_preview_refresh)
        for sig in (
            self.fg_color_changed, self.bg_color_changed,
            self.line_width_changed, self.font_family_changed,
            self.font_size_changed, self.opacity_changed,
            self.cap_style_changed, self.join_style_changed,
            self.dash_pattern_changed, self.filled_toggled,
            self.shadow_toggled, self.shadow_color_changed,
            self.shadow_offset_x_changed, self.shadow_offset_y_changed,
            self.shadow_blur_x_changed, self.shadow_blur_y_changed,
            self.rotation_changed,
            self.pixel_size_changed, self.fill_tolerance_changed,
            self.number_size_changed, self.number_text_color_changed,
            self.stamp_size_changed,
            self.text_bold_changed, self.text_italic_changed,
            self.text_underline_changed, self.text_strikethrough_changed,
            self.text_alignment_changed, self.text_direction_changed,
            self.text_bg_enabled_changed, self.text_bg_color_changed,
            self.text_stroke_enabled_changed, self.text_stroke_color_changed,
            self.text_stroke_width_changed,
        ):
            sig.connect(lambda *_, s=sig: self._schedule_preview_refresh())

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
            if self._shadow_unlink_btn.isChecked():
                props["shadow_blur_x"] = self._shadow_blur_x_slider.value()
                props["shadow_blur_y"] = self._shadow_blur_y_slider.value()
            else:
                v = self._shadow_blur_slider.value()
                props["shadow_blur_x"] = v
                props["shadow_blur_y"] = v
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
            _bx = int(props.get("shadow_blur_x", props.get("shadow_blur", self._shadow_blur_slider.value())))
            _by = int(props.get("shadow_blur_y", props.get("shadow_blur", self._shadow_blur_slider.value())))
            if "shadow_blur_x" in props or "shadow_blur_y" in props or "shadow_blur" in props:
                self._shadow_blur_x_slider.setValue(_bx)
                self._shadow_blur_y_slider.setValue(_by)
                if _bx == _by:
                    self._shadow_unlink_btn.setChecked(False)
                    self._shadow_blur_slider.setValue(_bx)
                else:
                    self._shadow_unlink_btn.setChecked(True)
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
                v = bool(props["text_bg_enabled"])
                self._text_bg_check.setChecked(v)
                self._text_bg_btn.setEnabled(v)
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
        lbl.setFixedWidth(36)
        row.addWidget(lbl)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(lo, hi)
        slider.setValue(default)
        row.addWidget(slider, 1)
        val_lbl = QLabel(f"{default}{suffix}")
        val_lbl.setObjectName("valLabel")
        val_lbl.setFixedWidth(34)
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

    def _fmt_btn(self, icon_name: str, tooltip: str, label: str = "", bold: bool = False, italic: bool = False, underline: bool = False) -> QToolButton:
        btn = QToolButton()
        btn.setToolTip(tooltip)
        btn.setCheckable(True)
        if label:
            btn.setText(label)
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
            f = btn.font()
            if bold:
                f.setBold(True)
            if italic:
                f.setItalic(True)
            if underline:
                f.setUnderline(True)
            f.setPointSize(11)
            btn.setFont(f)
            btn.setFixedSize(28, 24)
        else:
            btn.setIcon(get_icon(icon_name, 14))
            btn.setFixedSize(24, 24)
        return btn

    def _wrap_layout(self, layout) -> QWidget:
        w = QWidget()
        layout.setContentsMargins(0, 0, 0, 0)
        w.setLayout(layout)
        return w

    def _wrap_widget(self, widget) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(0)
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

    def _on_shadow_blur_linked(self, v: int):
        """Linked blur slider: update both X and Y to the same value."""
        self._shadow_blur_x_slider.blockSignals(True)
        self._shadow_blur_y_slider.blockSignals(True)
        self._shadow_blur_x_slider.setValue(v)
        self._shadow_blur_y_slider.setValue(v)
        self._shadow_blur_x_slider.blockSignals(False)
        self._shadow_blur_y_slider.blockSignals(False)
        if not self._loading_element:
            self.shadow_blur_x_changed.emit(float(v))
            self.shadow_blur_y_changed.emit(float(v))

    def _on_shadow_unlink_toggled(self, unlinked: bool):
        """Show/hide linked vs separate blur sliders."""
        self._shadow_blur_linked_widget.setVisible(not unlinked)
        self._shadow_blur_xy_widget.setVisible(unlinked)
        if unlinked:
            # Sync separate sliders to current linked value
            v = self._shadow_blur_slider.value()
            self._shadow_blur_x_slider.blockSignals(True)
            self._shadow_blur_y_slider.blockSignals(True)
            self._shadow_blur_x_slider.setValue(v)
            self._shadow_blur_y_slider.setValue(v)
            self._shadow_blur_x_slider.blockSignals(False)
            self._shadow_blur_y_slider.blockSignals(False)
        else:
            # Sync linked to x value
            self._shadow_blur_slider.blockSignals(True)
            self._shadow_blur_slider.setValue(self._shadow_blur_x_slider.value())
            self._shadow_blur_slider.blockSignals(False)

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
        # Show tool sample preview when no element is selected
        if self._preview_element is None:
            QTimer.singleShot(0, self._refresh_tool_preview)
        else:
            QTimer.singleShot(0, self._adjust_height)

    # --- Element property loading ---

    def load_element_properties(self, element: AnnotationElement | None):
        self._loading_element = True
        try:
            if element is None:
                self._edit_banner.hide()
                return

            self._edit_banner.show()
            self._preview_label.show()
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
            _bx, _by = int(s.shadow.blur_x), int(s.shadow.blur_y)
            self._shadow_blur_x_slider.setValue(_bx)
            self._shadow_blur_y_slider.setValue(_by)
            if _bx == _by:
                self._shadow_unlink_btn.setChecked(False)
                self._shadow_blur_slider.setValue(_bx)
            else:
                self._shadow_unlink_btn.setChecked(True)
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
                self._text_bg_btn.setEnabled(element.bg_enabled)
                self._text_bg_color = element.bg_color
                self._update_swatch(self._text_bg_btn, element.bg_color)
                self._text_stroke_check.setChecked(element.stroke_enabled)
                self._text_stroke_btn.setEnabled(element.stroke_enabled)
                self._text_stroke_width_widget.setVisible(element.stroke_enabled)
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
            self._refresh_preview(element)
            # Update title to show element type
            _etype_names = {
                ElementType.PEN: "Pen stroke", ElementType.BRUSH: "Brush stroke",
                ElementType.HIGHLIGHT: "Highlight", ElementType.LINE: "Line",
                ElementType.ARROW: "Arrow", ElementType.RECTANGLE: "Rectangle",
                ElementType.ELLIPSE: "Ellipse", ElementType.TEXT: "Text",
                ElementType.NUMBER: "Number badge", ElementType.MASK: "Mask / Mosaic",
                ElementType.IMAGE: "Image", ElementType.STAMP: "Stamp",
            }
            self._title_label.setText(_etype_names.get(element.element_type, "Properties"))
        finally:
            self._loading_element = False

    def clear_element_properties(self):
        self._edit_banner.hide()
        self._preview_element = None
        self._title_label.setText("Properties")
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

        # Re-skin header buttons and title
        self._pin_btn.setStyleSheet(
            f"QToolButton{{background:{bg2};border:1px solid {brd};"
            f"border-radius:4px;color:{fg_dim};font-size:10px;padding:1px 5px;"
            f"min-width:36px;min-height:24px;}}"
            f"QToolButton:hover{{background:{bg3};color:{fg};}}"
            f"QToolButton:checked{{background:{acc};border-color:{acc};color:{fg_br};}}"
        )
        self._pin_close_btn.setStyleSheet(
            f"QToolButton{{background:{bg2};border:1px solid {brd};"
            f"border-radius:4px;color:{fg};font-size:12px;padding:0;"
            f"min-width:24px;min-height:24px;max-width:24px;max-height:24px;}}"
            f"QToolButton:hover{{background:#8b0000;border-color:#cc3333;color:{fg_br};}}"
        )
        self._title_label.setStyleSheet(
            f"color:{fg_br};font-size:13px;font-weight:bold;padding:0;background:transparent;"
        )
        self._preview_label.setStyleSheet(
            f"background:{bg1};border-bottom:1px solid {brd};color:{fg_dim};font-size:10px;"
        )

        # Update scroll area + content widget palette so they match
        bg_color = QColor(bg1)
        self._scroll.setStyleSheet(
            f"QScrollArea{{border:none;background:{bg1};}}"
            f"QScrollBar:vertical{{background:{bg1};width:6px;margin:0;}}"
            f"QScrollBar::handle:vertical{{background:{brd};border-radius:3px;min-height:20px;}}"
            f"QScrollBar::handle:vertical:hover{{background:{fg_dim};}}"
            f"QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{{height:0;}}"
        )
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

    def set_auto_hide_ms(self, ms: int):
        """Override the auto-hide delay (default 3000 ms)."""
        self._auto_hide_timer.setInterval(max(500, ms))

    def set_mode(self, mode: str):
        """Set panel mode: 'auto', 'pinned', or 'hidden'."""
        self._mode = mode
        # Sync pin button without re-triggering toggled signal
        self._pin_btn.blockSignals(True)
        self._pin_btn.setChecked(mode == "pinned")
        self._pin_btn.blockSignals(False)
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

    def _on_pin_toggled(self, checked: bool):
        """Pin button toggled: pinned mode when checked, auto mode when unchecked."""
        self.set_mode("pinned" if checked else "auto")

    def _on_close_clicked(self):
        """Hide button clicked — switch to hidden mode."""
        self.set_mode("hidden")

    def _schedule_preview_refresh(self):
        """Debounced preview refresh — called when any property signal fires."""
        self._preview_timer.start()

    def _do_preview_refresh(self):
        """Timer callback: re-render the current preview element or tool sample."""
        if self._preview_element is not None:
            self._refresh_preview(self._preview_element)
        else:
            self._refresh_tool_preview()

    def _current_style(self) -> ElementStyle:
        """Build an ElementStyle from the panel's current widget values."""
        return ElementStyle(
            foreground_color=self._fg_color,
            background_color=self._bg_color,
            line_width=float(self._width_slider.value()),
            opacity=self._opacity_slider.value() / 100.0,
            font_family=self._font_combo.currentText(),
            font_size=self._font_size_slider.value(),
            shadow=Shadow(
                enabled=self._shadow_check.isChecked(),
                offset_x=float(self._shadow_ox_slider.value()),
                offset_y=float(self._shadow_oy_slider.value()),
                blur_x=float(self._shadow_blur_x_slider.value()),
                blur_y=float(self._shadow_blur_y_slider.value()),
                color=self._shadow_color,
            ),
            cap_style=self._cap_combo.currentData() or "round",
            join_style=self._join_combo.currentData() or "round",
            dash_pattern=self._dash_combo.currentData() or "solid",
        )

    def _build_tool_sample(self) -> AnnotationElement | None:
        """Create a small sample element representing the current tool + settings."""
        t = self._current_tool
        style = self._current_style()

        if t in (ToolType.PEN, ToolType.BRUSH, ToolType.HIGHLIGHT):
            if t == ToolType.HIGHLIGHT:
                elem = HighlightElement(style)
            elif t == ToolType.BRUSH:
                elem = BrushElement(style)
            else:
                elem = PenElement(style)
            # Draw a gentle wave
            for i in range(30):
                x = 10 + i * 3
                y = 30 + (10 if i % 6 < 3 else -10) * (0.5 if i < 5 or i > 25 else 1)
                elem.add_point(QPointF(x, y))
            return elem

        if t in (ToolType.LINE, ToolType.ARROW):
            elem = (ArrowElement if t == ToolType.ARROW else LineElement)(
                QPointF(10, 40), QPointF(100, 15), style)
            return elem

        if t == ToolType.RECTANGLE:
            elem = RectElement(QRectF(10, 8, 90, 40), style)
            elem.filled = self._filled_check.isChecked()
            return elem

        if t == ToolType.ELLIPSE:
            elem = EllipseElement(QRectF(10, 8, 90, 40), style)
            elem.filled = self._filled_check.isChecked()
            return elem

        if t == ToolType.TEXT:
            elem = TextElement(QPointF(10, 10), "Sample", style)
            elem.bold = self._bold_btn.isChecked()
            elem.italic = self._italic_btn.isChecked()
            elem.underline = self._underline_btn.isChecked()
            return elem

        if t == ToolType.NUMBERING:
            elem = NumberElement(QPointF(55, 28), size=float(self._num_size_slider.value()),
                                text_color=self._num_text_color, style=style)
            return elem

        return None

    def _refresh_tool_preview(self):
        """Generate and render a sample element for the current tool."""
        sample = self._build_tool_sample()
        if sample is None:
            self._preview_label.hide()
            QTimer.singleShot(0, self._adjust_height)
            return
        self._preview_label.show()
        # Render the sample without storing it as _preview_element
        pw = max(self.width() - 4, 100)
        ph = 56
        pix = QPixmap(pw, ph)
        pix.fill(QColor("#111827"))
        try:
            br = sample.bounding_rect()
            if br.width() >= 1 and br.height() >= 1:
                margin = 12
                scale = min((pw - margin * 2) / br.width(),
                            (ph - margin * 2) / br.height(), 4.0)
                p = QPainter(pix)
                p.setRenderHint(QPainter.RenderHint.Antialiasing)
                tx = (pw - br.width() * scale) / 2 - br.x() * scale
                ty = (ph - br.height() * scale) / 2 - br.y() * scale
                p.translate(tx, ty)
                p.scale(scale, scale)
                sample.paint(p)
                p.end()
        except Exception:
            pass
        self._preview_label.setPixmap(pix)
        self._preview_label.setText("")
        QTimer.singleShot(0, self._adjust_height)

    def _refresh_preview(self, element=None):
        """Render a scaled thumbnail of *element* into the preview strip."""
        self._preview_element = element
        pw = max(self.width() - 4, 100)
        ph = 56  # preview_label height minus border
        pix = QPixmap(pw, ph)
        pix.fill(QColor("#111827"))
        if element is None:
            self._preview_label.setPixmap(pix)
            self._preview_label.setText("No selection")
            return
        try:
            br = element.bounding_rect()
            if br.width() < 1 or br.height() < 1:
                self._preview_label.setPixmap(pix)
                self._preview_label.setText("—")
                return
            margin = 12
            scale = min((pw - margin * 2) / br.width(),
                        (ph - margin * 2) / br.height(),
                        4.0)
            p = QPainter(pix)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            tx = (pw - br.width() * scale) / 2 - br.x() * scale
            ty = (ph - br.height() * scale) / 2 - br.y() * scale
            p.translate(tx, ty)
            p.scale(scale, scale)
            element.paint(p)
            p.end()
        except Exception:
            pass
        self._preview_label.setPixmap(pix)
        self._preview_label.setText("")

    def _adjust_height(self):
        """Resize panel height to fit visible content, capped by available screen height."""
        # Header + preview + scroll content
        header_h = self._header.sizeHint().height()
        preview_h = self._preview_label.height() if self._preview_label.isVisible() else 0
        content_h = self._scroll_widget.sizeHint().height()
        ideal = header_h + preview_h + content_h + 12  # 12 = margins
        # Cap to 85% of screen height
        screen = None
        try:
            from PySide6.QtWidgets import QApplication
            scr = QApplication.screenAt(self.pos())
            if scr:
                screen = scr.availableGeometry()
            else:
                screen = QApplication.primaryScreen().availableGeometry()
        except Exception:
            pass
        max_h = int(screen.height() * 0.85) if screen else 900
        min_h = 200
        new_h = max(min_h, min(ideal, max_h))
        self.resize(self.width(), new_h)

    def show(self):
        """Fade in the panel."""
        if self.isVisible() and self._fade_target_visible:
            return
        self._fade_target_visible = True
        self._fade_anim.stop()
        self.setWindowOpacity(0.0)
        super().show()
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()

    def hide(self):
        """Fade out the panel."""
        if not self.isVisible():
            return
        self._fade_target_visible = False
        self._fade_anim.stop()
        self._fade_anim.setStartValue(self.windowOpacity())
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.start()

    def _on_fade_finished(self):
        if not self._fade_target_visible:
            super().hide()
            self.setWindowOpacity(1.0)

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
