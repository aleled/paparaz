"""Theme preset system — 8 carefully tuned presets for light/dark document contexts."""

from __future__ import annotations
from dataclasses import dataclass

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QWidget, QFrame,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QFont, QPixmap, QBrush, QPainterPath

# ──────────────────────────────────────────────────────────────────────────────
# Preset definitions
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class ThemePreset:
    id: str
    name: str
    category: str           # "light" | "dark"
    tagline: str            # short description shown under name
    description: str        # tooltip / longer text
    # Canvas / element colours (ARGB hex where alpha matters)
    fg_color: str           # stroke / text colour
    bg_color: str           # fill / background colour
    text_bg_color: str      # text-element highlight box colour
    line_width: int
    opacity: float          # element-level opacity
    shadow_enabled: bool
    shadow_color: str
    shadow_offset_x: float
    shadow_offset_y: float
    shadow_blur: float
    font_family: str
    font_size: int
    # For preview rendering
    bg_preview: str         # preview card background


PRESETS: dict[str, ThemePreset] = {
    # ── LIGHT THEMES ─────────────────────────────────────────────────────────
    "light_review": ThemePreset(
        id="light_review",
        name="Review",
        category="light",
        tagline="Classic red-pen markup",
        description=(
            "Strong red strokes on white documents. The timeless editorial look — "
            "perfect for proofreading emails, PDFs, and office docs."
        ),
        fg_color="#CC2200",
        bg_color="#80FFCCCC",
        text_bg_color="#A0FFEEEE",
        line_width=2,
        opacity=1.0,
        shadow_enabled=False,
        shadow_color="#40000000",
        shadow_offset_x=3.0,
        shadow_offset_y=3.0,
        shadow_blur=4.0,
        font_family="Arial",
        font_size=14,
        bg_preview="#FFFFFF",
    ),
    "light_focus": ThemePreset(
        id="light_focus",
        name="Focus",
        category="light",
        tagline="Bold orange emphasis",
        description=(
            "Deep orange strokes with warm yellow highlight fill. "
            "High contrast on white/light backgrounds — great for presentations "
            "and sharing attention-grabbing callouts."
        ),
        fg_color="#E65100",
        bg_color="#C0FFE082",
        text_bg_color="#C0FFE082",
        line_width=3,
        opacity=1.0,
        shadow_enabled=False,
        shadow_color="#40000000",
        shadow_offset_x=3.0,
        shadow_offset_y=3.0,
        shadow_blur=4.0,
        font_family="Arial",
        font_size=14,
        bg_preview="#F5F5F5",
    ),
    "light_ink": ThemePreset(
        id="light_ink",
        name="Ink",
        category="light",
        tagline="Formal navy blue on white",
        description=(
            "Deep navy blue strokes evoke a premium pen-on-paper feel. "
            "Clean, professional, and easy to read in reports and documentation."
        ),
        fg_color="#1A237E",
        bg_color="#90C5CAE8",
        text_bg_color="#B0C5CAE8",
        line_width=2,
        opacity=1.0,
        shadow_enabled=False,
        shadow_color="#40000020",
        shadow_offset_x=2.0,
        shadow_offset_y=2.0,
        shadow_blur=3.0,
        font_family="Georgia",
        font_size=14,
        bg_preview="#FAFAFA",
    ),
    "light_highlight": ThemePreset(
        id="light_highlight",
        name="Highlight",
        category="light",
        tagline="Vivid yellow marker pen",
        description=(
            "Bright yellow fill and amber stroke — the classic highlighter. "
            "Perfect for marking up study notes, receipts, or any text-heavy image."
        ),
        fg_color="#F57F17",
        bg_color="#D0FFFF00",
        text_bg_color="#E0FFFF00",
        line_width=10,
        opacity=0.75,
        shadow_enabled=False,
        shadow_color="#40000000",
        shadow_offset_x=2.0,
        shadow_offset_y=2.0,
        shadow_blur=3.0,
        font_family="Arial",
        font_size=16,
        bg_preview="#FFFEF0",
    ),
    # ── DARK THEMES ──────────────────────────────────────────────────────────
    "dark_review": ThemePreset(
        id="dark_review",
        name="Review",
        category="dark",
        tagline="Warm amber on dark screens",
        description=(
            "Warm amber/yellow annotations that pop on dark backgrounds. "
            "Ideal for annotating dark-mode apps, IDE screenshots, or terminal output."
        ),
        fg_color="#FFD54F",
        bg_color="#50FFD54F",
        text_bg_color="#80FFD54F",
        line_width=2,
        opacity=1.0,
        shadow_enabled=False,
        shadow_color="#80000000",
        shadow_offset_x=3.0,
        shadow_offset_y=3.0,
        shadow_blur=5.0,
        font_family="Arial",
        font_size=14,
        bg_preview="#1E1E1E",
    ),
    "dark_focus": ThemePreset(
        id="dark_focus",
        name="Focus",
        category="dark",
        tagline="Neon green high-contrast",
        description=(
            "Vibrant green-cyan that punches through dark dashboards and slides. "
            "Shadow enabled for maximum legibility on very dark backgrounds."
        ),
        fg_color="#69F0AE",
        bg_color="#6069F0AE",
        text_bg_color="#8069F0AE",
        line_width=3,
        opacity=1.0,
        shadow_enabled=True,
        shadow_color="#80000000",
        shadow_offset_x=3.0,
        shadow_offset_y=3.0,
        shadow_blur=5.0,
        font_family="Arial",
        font_size=14,
        bg_preview="#212121",
    ),
    "dark_ocean": ThemePreset(
        id="dark_ocean",
        name="Ocean",
        category="dark",
        tagline="Electric cyan on deep blue",
        description=(
            "Cool electric-blue strokes on near-black. Calm yet precise — "
            "great for annotating dark dashboards, monitoring UIs, and night-mode docs."
        ),
        fg_color="#40C4FF",
        bg_color="#5040C4FF",
        text_bg_color="#7040C4FF",
        line_width=2,
        opacity=1.0,
        shadow_enabled=True,
        shadow_color="#80001833",
        shadow_offset_x=2.0,
        shadow_offset_y=3.0,
        shadow_blur=6.0,
        font_family="Consolas",
        font_size=13,
        bg_preview="#0A1929",
    ),
    "dark_flame": ThemePreset(
        id="dark_flame",
        name="Flame",
        category="dark",
        tagline="Urgent orange-red on black",
        description=(
            "Fiery deep-orange strokes with a glowing shadow. "
            "Use when annotations need to scream — errors, critical bugs, urgent issues."
        ),
        fg_color="#FF6D00",
        bg_color="#60FF6D00",
        text_bg_color="#80FF6D00",
        line_width=3,
        opacity=1.0,
        shadow_enabled=True,
        shadow_color="#80330000",
        shadow_offset_x=3.0,
        shadow_offset_y=3.0,
        shadow_blur=7.0,
        font_family="Arial",
        font_size=14,
        bg_preview="#1A0800",
    ),
}

# Ordered list for display (4 light, 4 dark — shown in 2-column grid)
PRESET_ORDER = [
    "light_review", "light_focus", "light_ink", "light_highlight",
    "dark_review",  "dark_focus",  "dark_ocean", "dark_flame",
]


# ──────────────────────────────────────────────────────────────────────────────
# Preview pixmap renderer  (320 × 192 — 2× larger)
# ──────────────────────────────────────────────────────────────────────────────

def _draw_preview(preset: ThemePreset, w: int = 320, h: int = 192) -> QPixmap:
    """Draw a representative preview of how the preset looks on its background.

    Always renders at the native 320×192 resolution then scales, so coordinates
    never overflow regardless of the requested output size.
    """
    NATIVE_W, NATIVE_H = 320, 192
    pix = QPixmap(NATIVE_W, NATIVE_H)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Background
    p.fillRect(0, 0, w, h, QColor(preset.bg_preview))

    fg = QColor(preset.fg_color)
    bg = QColor(preset.bg_color)
    tbg = QColor(preset.text_bg_color)

    lw = max(preset.line_width, 1)

    # Rectangle annotation (scaled ×2)
    rect_x, rect_y, rect_w, rect_h = 16, 20, 124, 72
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(bg)
    p.drawRect(rect_x, rect_y, rect_w, rect_h)
    pen = QPen(fg, lw)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(rect_x, rect_y, rect_w, rect_h)

    # Arrow (scaled ×2)
    p.setPen(QPen(fg, lw + 1, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawLine(164, 56, 230, 56)
    # Arrowhead
    p.setBrush(fg)
    p.setPen(Qt.PenStyle.NoPen)
    arrow = QPainterPath()
    arrow.moveTo(230, 56)
    arrow.lineTo(216, 48)
    arrow.lineTo(216, 64)
    arrow.closeSubpath()
    p.drawPath(arrow)

    # Highlight stroke (scaled ×2)
    hl_color = QColor(preset.fg_color)
    hl_color.setAlpha(60)
    p.setPen(QPen(hl_color, 24, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
    p.drawLine(16, 124, 144, 124)

    # Text with background box (scaled ×2)
    font_sz = max(preset.font_size, 8) if preset.font_size <= 20 else 14
    font = QFont(preset.font_family, font_sz)
    font.setBold(True)
    p.setFont(font)
    fm_h = 26
    label = "Sample Text"
    text_x, text_y = 164, 100
    text_w = 144
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(tbg)
    p.drawRoundedRect(text_x - 4, text_y - fm_h + 2, text_w, fm_h + 8, 4, 4)
    p.setPen(fg)
    p.drawText(text_x, text_y, label)

    # Line (scaled ×2)
    p.setPen(QPen(fg, lw))
    p.drawLine(16, 160, 290, 160)

    # Small numbered circle (new in v2)
    num_pen = QPen(fg, max(lw - 1, 1))
    p.setPen(num_pen)
    p.setBrush(bg)
    p.drawEllipse(260, 20, 36, 36)
    p.setPen(fg)
    num_font = QFont(preset.font_family, 14)
    num_font.setBold(True)
    p.setFont(num_font)
    p.drawText(260, 20, 36, 36, Qt.AlignmentFlag.AlignCenter, "1")

    # Faint grid lines on preview background
    grid_c = QColor(150, 150, 150, 20)
    p.setPen(QPen(grid_c, 1))
    for x in range(0, w, 40):
        p.drawLine(x, 0, x, h)
    for y in range(0, h, 40):
        p.drawLine(0, y, w, y)

    p.end()

    # Scale to requested size using smooth transform
    if w != NATIVE_W or h != NATIVE_H:
        pix = pix.scaled(
            w, h,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    return pix


# ──────────────────────────────────────────────────────────────────────────────
# Theme Preset Popup Dialog
# ──────────────────────────────────────────────────────────────────────────────

POPUP_STYLE = """
QDialog {
    background: #16162a;
    border: 1px solid #444466;
    border-radius: 8px;
}
QLabel#title {
    color: #ffffff;
    font-size: 16px;
    font-weight: bold;
}
QLabel#subtitle {
    color: #888;
    font-size: 11px;
}
QLabel#catLabel {
    color: #666;
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 1px;
}
QPushButton#closeBtn {
    background: transparent;
    color: #666;
    border: none;
    font-size: 16px;
    padding: 0;
}
QPushButton#closeBtn:hover { color: #fff; }
QPushButton#applyDefault {
    background: #252538;
    color: #aaa;
    border: 1px solid #3a3a5e;
    border-radius: 4px;
    padding: 6px 16px;
    font-size: 12px;
}
QPushButton#applyDefault:hover { background: #2e2e4e; color: #fff; }
"""

CARD_NORMAL = """
QWidget#presetCard {
    background: #1e1e35;
    border: 2px solid #2e2e4e;
    border-radius: 8px;
}
QWidget#presetCard:hover {
    border-color: #555588;
    background: #22223a;
}
"""

CARD_ACTIVE = """
QWidget#presetCard {
    background: #1e1e35;
    border: 2px solid #740096;
    border-radius: 8px;
}
"""


class _PresetCard(QWidget):
    clicked = Signal(str)

    PREVIEW_W = 210   # preview display size inside card
    PREVIEW_H = 126   # 16:9.6 ratio matching 320×192 aspect
    CARD_W    = PREVIEW_W + 16   # 226
    CARD_H    = PREVIEW_H + 58   # 184

    def __init__(self, preset: ThemePreset, active: bool, parent=None):
        super().__init__(parent)
        self.setObjectName("presetCard")
        self.setFixedSize(self.CARD_W, self.CARD_H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._preset_id = preset.id
        self._apply_style(active)

        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(8, 8, 8, 8)
        vbox.setSpacing(5)

        # Preview rendered at full quality, scaled to display size
        pix = _draw_preview(preset, self.PREVIEW_W, self.PREVIEW_H)
        img_lbl = QLabel()
        img_lbl.setPixmap(pix)
        img_lbl.setFixedSize(self.PREVIEW_W, self.PREVIEW_H)
        img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vbox.addWidget(img_lbl, 0, Qt.AlignmentFlag.AlignCenter)

        # Name row
        name_row = QHBoxLayout()
        name_row.setSpacing(4)
        name_lbl = QLabel(preset.name)
        name_lbl.setStyleSheet("color:#fff; font-size:12px; font-weight:bold;")
        name_row.addWidget(name_lbl)
        if active:
            dot = QLabel("●")
            dot.setStyleSheet("color:#740096; font-size:11px;")
            name_row.addWidget(dot)
        name_row.addStretch()
        if preset.shadow_enabled:
            shd = QLabel("shadow")
            shd.setStyleSheet(
                "color:#aaa; background:#2a2a4e; border:1px solid #444;"
                "border-radius:3px; font-size:9px; padding:1px 3px;"
            )
            name_row.addWidget(shd)
        vbox.addLayout(name_row)

        # Tagline + colour swatches
        bot = QHBoxLayout()
        bot.setSpacing(4)
        tag = QLabel(preset.tagline)
        tag.setStyleSheet("color:#888; font-size:10px;")
        tag.setWordWrap(False)
        bot.addWidget(tag, 1)
        for cs in [preset.fg_color, preset.bg_color]:
            sw = QLabel()
            sw.setFixedSize(12, 12)
            c = QColor(cs)
            sw.setStyleSheet(
                f"background:rgba({c.red()},{c.green()},{c.blue()},{c.alpha()});"
                "border:1px solid #444; border-radius:2px;"
            )
            bot.addWidget(sw)
        vbox.addLayout(bot)

    def _apply_style(self, active: bool):
        self.setStyleSheet(CARD_ACTIVE if active else CARD_NORMAL)

    def set_active(self, active: bool):
        self._apply_style(active)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._preset_id)

    def enterEvent(self, event):
        self.update()

    def leaveEvent(self, event):
        self.update()


class ThemePresetPopup(QDialog):
    """Floating popup showing 8 preset cards (4 light / 4 dark) with live previews."""

    preset_applied = Signal(str)   # emitted with preset ID when user applies one

    def __init__(self, current_preset_id: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Theme Presets")
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(POPUP_STYLE)
        self._current = current_preset_id
        self._cards: dict[str, _PresetCard] = {}
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        frame = QFrame()
        frame.setObjectName("popupFrame")
        frame.setStyleSheet(
            "QFrame#popupFrame {"
            "  background: #16162a;"
            "  border: 1px solid #444466;"
            "  border-radius: 10px;"
            "}"
        )
        outer.addWidget(frame)

        vbox = QVBoxLayout(frame)
        vbox.setContentsMargins(16, 14, 16, 16)
        vbox.setSpacing(12)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("Theme Presets")
        title.setObjectName("title")
        hdr.addWidget(title)
        hdr.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(24, 24)
        close_btn.clicked.connect(self.reject)
        hdr.addWidget(close_btn)
        vbox.addLayout(hdr)

        subtitle = QLabel(
            "Click a preset to apply globally — colours, line width, font, opacity, and shadow."
        )
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)
        vbox.addWidget(subtitle)

        # Grid layout:  4 columns × 2 rows
        #   col 0,1 = light presets   col 2,3 = dark presets
        #
        #   |  Review  |  Focus   |  Review  |  Focus   |
        #   |  Ink     |Highlight |  Ocean   |  Flame   |

        GAP = 10
        CW  = _PresetCard.CARD_W   # 226
        two_col_w = 2 * CW + GAP  # width of 2 cards + 1 gap

        # ── Category header row ──────────────────────────────
        hdr_row = QHBoxLayout()
        hdr_row.setSpacing(GAP)

        for label, color in [
            ("◑   LIGHT DOCUMENTS", "#AAAACC"),
            ("●   DARK DOCUMENTS",  "#666688"),
        ]:
            lbl = QLabel(label)
            lbl.setObjectName("catLabel")
            lbl.setStyleSheet(
                f"color:{color}; font-size:11px; font-weight:bold; letter-spacing:1px;"
            )
            lbl.setFixedWidth(two_col_w)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hdr_row.addWidget(lbl)

        vbox.addLayout(hdr_row)

        # ── Cards grid ──────────────────────────────────────
        light_ids = [pid for pid in PRESET_ORDER if PRESETS[pid].category == "light"]
        dark_ids  = [pid for pid in PRESET_ORDER if PRESETS[pid].category == "dark"]

        grid = QGridLayout()
        grid.setHorizontalSpacing(GAP)
        grid.setVerticalSpacing(GAP)
        grid.setContentsMargins(0, 0, 0, 0)

        # Place light presets in cols 0-1, dark in cols 2-3, across 2 rows
        for group_col, ids in enumerate([light_ids, dark_ids]):
            for i, pid in enumerate(ids):
                row = i // 2           # 0 or 1
                sub = i %  2           # 0 or 1
                col = group_col * 2 + sub
                preset = PRESETS[pid]
                card = _PresetCard(preset, active=(pid == self._current))
                card.clicked.connect(self._on_card_clicked)
                self._cards[pid] = card
                grid.addWidget(card, row, col)

        vbox.addLayout(grid)

        # Footer
        foot = QHBoxLayout()
        foot.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("applyDefault")
        cancel_btn.clicked.connect(self.reject)
        foot.addWidget(cancel_btn)
        vbox.addLayout(foot)

    def _on_card_clicked(self, preset_id: str):
        for pid, card in self._cards.items():
            card.set_active(pid == preset_id)
        self._current = preset_id
        self.preset_applied.emit(preset_id)
        self.accept()
