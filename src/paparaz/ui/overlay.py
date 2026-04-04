"""Full-screen overlay for region selection on a single monitor.

Captures and overlays only the monitor the cursor is on, avoiding
DPI scaling mismatches between monitors.
"""

from PySide6.QtWidgets import QWidget, QLabel
from PySide6.QtCore import Qt, QRect, QPoint, QRectF, Signal
from PySide6.QtGui import (
    QPainter, QColor, QPixmap, QCursor, QPen, QRegion, QScreen, QFont,
    QFontMetrics,
)

UI_COLOR = QColor(116, 0, 150)
OVERLAY_COLOR = QColor(0, 0, 0, 190)
HANDLE_SIZE = 6          # Small crisp squares instead of big circles
HELP_BG = QColor(0, 0, 0, 160)
HELP_TEXT_COLOR = QColor(200, 200, 200)
HELP_KEY_COLOR = QColor(180, 140, 255)     # Highlight for key names

# Magnifier loupe settings
LOUPE_DISPLAY_DEFAULT = 140  # Default widget pixel size of the loupe square
LOUPE_DISPLAY_MIN = 80       # Minimum loupe display size
LOUPE_DISPLAY_MAX = 320      # Maximum loupe display size
LOUPE_DISPLAY_STEP = 20      # Alt+scroll step
LOUPE_SRC_DEFAULT = 11    # Default source pixels (odd for center pixel)
LOUPE_SRC_MIN = 5         # Minimum source pixels (max zoom in)
LOUPE_SRC_MAX = 51        # Maximum source pixels (max zoom out)
LOUPE_OFFSET = 24         # Distance from cursor to loupe top-left
LOUPE_BG = QColor(20, 20, 30, 240)
LOUPE_BORDER = QColor(116, 0, 150, 200)
LOUPE_GRID = QColor(255, 255, 255, 40)
LOUPE_CROSS = QColor(255, 80, 80, 200)
LOUPE_AXIS = QColor(80, 200, 255, 100)  # X/Y axis lines through center


class RegionSelector(QWidget):
    """Full-screen overlay on a single monitor with dark veil and selection hole."""

    region_selected = Signal(QRect)  # Selection in widget-local coordinates
    selection_cancelled = Signal()

    def __init__(self, screenshot: QPixmap, screen: QScreen):
        super().__init__()
        self._screen = screen
        self._screen_geo = screen.geometry()  # Logical pixel geometry
        self._start = QPoint()
        self._end = QPoint()
        self._selecting = False
        self._selection = QRect()
        self._has_selection = False
        self._loupe_src = LOUPE_SRC_DEFAULT    # source pixels (Ctrl+scroll)
        self._loupe_display = LOUPE_DISPLAY_DEFAULT  # display size (Alt+scroll)
        self._arrow_loupe_pos: QPoint | None = None  # set by arrow keys for loupe
        self._pre_select_pos: QPoint | None = None   # arrow-key position before first click

        # Scale capture (physical pixels) to screen's logical pixel size
        self._screenshot = screenshot.scaled(
            self._screen_geo.width(), self._screen_geo.height(),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        # Keep a QImage copy for fast pixel sampling in the loupe
        self._src_image = self._screenshot.toImage()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.BypassWindowManagerHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

        # Position exactly on the target monitor
        self.setGeometry(self._screen_geo)

        # Labels
        self._dim_label = QLabel(self)
        self._dim_label.setStyleSheet(
            "background: rgba(116,0,150,220); color: white; padding: 4px 10px; "
            "border-radius: 4px; font-size: 12px; font-weight: bold;"
        )
        self._dim_label.hide()

        self._coord_label = QLabel(self)
        self._coord_label.setStyleSheet(
            "background: rgba(0,0,0,180); color: #aaa; padding: 3px 8px; "
            "border-radius: 3px; font-size: 10px;"
        )
        self._coord_label.hide()

    def showFullScreen(self):
        """Show as a normal window positioned exactly on the target monitor."""
        self.setGeometry(self._screen_geo)
        self.showNormal()
        self.setGeometry(self._screen_geo)
        self.raise_()
        self.activateWindow()
        self.setFocus()

    # ── Paint ────────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.drawPixmap(0, 0, self._screenshot)

        cur_pos = self.mapFromGlobal(QCursor.pos())

        if self._has_selection and not self._selection.isNull():
            sel = self._selection.normalized()

            # Dark overlay outside selection
            overlay_region = QRegion(self.rect()).subtracted(QRegion(sel))
            painter.setClipRegion(overlay_region)
            painter.fillRect(self.rect(), OVERLAY_COLOR)
            painter.setClipping(False)

            # Selection border
            painter.setPen(QPen(UI_COLOR, 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(sel)

            # Small square handles
            self._paint_handles(painter, sel)

            # Magnifier loupe — prefer arrow-key position, then mouse
            if self._arrow_loupe_pos is not None:
                self._paint_loupe(painter, self._arrow_loupe_pos)
            else:
                self._paint_loupe(painter, cur_pos)

            # Help text during drag
            if self._selecting:
                self._paint_help(painter, [
                    ("\u2190\u2191\u2192\u2193", "Fine-tune end point"),
                    ("Shift + \u2190\u2191\u2192\u2193", "Move 10px"),
                    ("Ctrl + Scroll", "Magnifier zoom"),
                    ("Shift + Scroll", "Magnifier size"),
                    ("Esc", "Cancel"),
                ])
        else:
            # Pre-selection: dark overlay + crosshair + loupe
            painter.fillRect(self.rect(), OVERLAY_COLOR)

            # Use arrow-key precision position if set, otherwise mouse
            draw_pos = self._pre_select_pos if self._pre_select_pos is not None else cur_pos

            painter.setPen(QPen(UI_COLOR, 1, Qt.PenStyle.DashLine))
            painter.drawLine(draw_pos.x(), 0, draw_pos.x(), self.height())
            painter.drawLine(0, draw_pos.y(), self.width(), draw_pos.y())

            abs_x = draw_pos.x() + self._screen_geo.x()
            abs_y = draw_pos.y() + self._screen_geo.y()
            self._coord_label.setText(f"{abs_x}, {abs_y}")
            self._coord_label.adjustSize()
            self._coord_label.move(
                min(draw_pos.x() + 15, self.width() - self._coord_label.width() - 5),
                min(draw_pos.y() + 15, self.height() - self._coord_label.height() - 5),
            )
            self._coord_label.show()

            self._paint_loupe(painter, draw_pos)

            # Help text — bottom-center
            self._paint_help(painter, [
                ("Click + Drag", "Select region"),
                ("\u2190\u2191\u2192\u2193", "Pixel-precise cursor"),
                ("Shift + \u2190\u2191\u2192\u2193", "Move 10px"),
                ("Ctrl + Scroll", "Magnifier zoom"),
                ("Shift + Scroll", "Magnifier size"),
                ("Right-click / Esc", "Cancel"),
            ])

        painter.end()

    # ── Handles ──────────────────────────────────────────────────────────────

    def _paint_handles(self, painter: QPainter, sel: QRect):
        """Draw small crisp square handles at the 8 control points."""
        hs = HANDLE_SIZE // 2
        painter.setPen(QPen(QColor("white"), 1))
        painter.setBrush(UI_COLOR)
        for hx, hy in self._get_handle_positions(sel):
            painter.drawRect(hx - hs, hy - hs, HANDLE_SIZE, HANDLE_SIZE)

    def _get_handle_positions(self, r: QRect) -> list[tuple[int, int]]:
        cx, cy = r.center().x(), r.center().y()
        return [
            (r.left(), r.top()), (cx, r.top()), (r.right(), r.top()),
            (r.left(), cy), (r.right(), cy),
            (r.left(), r.bottom()), (cx, r.bottom()), (r.right(), r.bottom()),
        ]

    # ── Magnifier loupe ─────────────────────────────────────────────────────

    def _paint_loupe(self, painter: QPainter, pos: QPoint):
        """Draw a pixel-grid magnifier loupe with X/Y axis lines near the cursor."""
        src = self._src_image
        sw, sh = src.width(), src.height()
        n = self._loupe_src  # source pixels (odd)
        half = n // 2
        cx, cy = pos.x(), pos.y()

        # Compute cell size so the loupe fits in self._loupe_display
        z = max(2, self._loupe_display // n)
        loupe_px = n * z  # actual rendered size

        # Position the loupe so it doesn't go off-screen or overlap the cursor
        lx = cx + LOUPE_OFFSET
        ly = cy + LOUPE_OFFSET
        if lx + loupe_px + 4 > self.width():
            lx = cx - LOUPE_OFFSET - loupe_px
        if ly + loupe_px + 28 > self.height():
            ly = cy - LOUPE_OFFSET - loupe_px - 24

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        # Background panel
        bg_rect = QRect(lx - 2, ly - 2, loupe_px + 4, loupe_px + 28)
        painter.setPen(QPen(LOUPE_BORDER, 2))
        painter.setBrush(LOUPE_BG)
        painter.drawRect(bg_rect)

        # Draw zoomed pixels
        for dy in range(n):
            for dx in range(n):
                sx = cx - half + dx
                sy = cy - half + dy
                if 0 <= sx < sw and 0 <= sy < sh:
                    color = QColor(src.pixel(sx, sy))
                else:
                    color = QColor(30, 30, 30)
                painter.fillRect(lx + dx * z, ly + dy * z, z, z, color)

        # Pixel grid lines (only when cells are large enough to see)
        if z >= 4:
            painter.setPen(QPen(LOUPE_GRID, 1))
            for i in range(1, n):
                painter.drawLine(lx + i * z, ly, lx + i * z, ly + loupe_px)
                painter.drawLine(lx, ly + i * z, lx + loupe_px, ly + i * z)

        # X/Y axis lines through center pixel
        axis_pen = QPen(LOUPE_AXIS, 1)
        painter.setPen(axis_pen)
        # Vertical axis (X) — runs through center column
        ax = lx + half * z + z // 2
        painter.drawLine(ax, ly, ax, ly + loupe_px)
        # Horizontal axis (Y) — runs through center row
        ay = ly + half * z + z // 2
        painter.drawLine(lx, ay, lx + loupe_px, ay)

        # Center crosshair (the pixel under cursor)
        cross_x = lx + half * z
        cross_y = ly + half * z
        painter.setPen(QPen(LOUPE_CROSS, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(cross_x, cross_y, z, z)

        # Coordinate + color text below loupe
        abs_x = cx + self._screen_geo.x()
        abs_y = cy + self._screen_geo.y()
        color_hex = ""
        if 0 <= cx < sw and 0 <= cy < sh:
            pc = QColor(src.pixel(cx, cy))
            color_hex = f"  #{pc.red():02X}{pc.green():02X}{pc.blue():02X}"

        font = QFont("Consolas", 9)
        painter.setFont(font)
        fm = QFontMetrics(font)
        text = f"{abs_x},{abs_y}{color_hex}"
        text_y = ly + loupe_px + 2
        painter.setPen(QColor(200, 200, 200))
        painter.drawText(lx + 3, text_y + fm.ascent(), text)

        painter.restore()

    # ── Mouse / wheel events ───────────────────────────────────────────────

    def wheelEvent(self, event):
        """Ctrl+scroll adjusts magnifier zoom, Shift+scroll adjusts magnifier size."""
        mods = event.modifiers()
        delta = event.angleDelta().y()
        if mods & Qt.KeyboardModifier.ControlModifier:
            # Ctrl+scroll: change source pixel count (zoom level)
            step = 2  # always keep odd
            if delta > 0:
                self._loupe_src = max(LOUPE_SRC_MIN, self._loupe_src - step)
            elif delta < 0:
                self._loupe_src = min(LOUPE_SRC_MAX, self._loupe_src + step)
            if self._loupe_src % 2 == 0:
                self._loupe_src += 1
            self.update()
            event.accept()
            return
        if mods & Qt.KeyboardModifier.ShiftModifier:
            # Shift+scroll: change display size (larger/smaller loupe)
            if delta > 0:
                self._loupe_display = min(LOUPE_DISPLAY_MAX,
                                          self._loupe_display + LOUPE_DISPLAY_STEP)
            elif delta < 0:
                self._loupe_display = max(LOUPE_DISPLAY_MIN,
                                          self._loupe_display - LOUPE_DISPLAY_STEP)
            self.update()
            event.accept()
            return
        super().wheelEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Use arrow-key precision position if set, otherwise mouse pos
            self._start = QPoint(self._pre_select_pos) if self._pre_select_pos else event.pos()
            self._pre_select_pos = None
            self._selecting = True
            self._has_selection = True
            self._coord_label.hide()
        elif event.button() == Qt.MouseButton.RightButton:
            self.selection_cancelled.emit()
            self.close()

    def mouseMoveEvent(self, event):
        self._arrow_loupe_pos = None  # mouse takes over from arrow keys
        self._pre_select_pos = None   # mouse takes over from pre-select arrows
        if self._selecting:
            self._end = event.pos()
            self._selection = QRect(self._start, self._end).normalized()
            self._update_dim_label()
            self.update()
        else:
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._selecting:
            self._selecting = False
            if self._selection.width() <= 5 or self._selection.height() <= 5:
                # Too small — discard
                self._has_selection = False
                self._selection = QRect()
                self.update()
            else:
                # Valid selection — emit immediately
                self.region_selected.emit(self._selection)
                self.close()

    def keyPressEvent(self, event):
        key = event.key()
        mods = event.modifiers()

        if key == Qt.Key.Key_Escape:
            self.selection_cancelled.emit()
            self.close()
        elif key in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down):
            if not self._has_selection:
                # Pre-selection: arrow keys move a virtual cursor for precision
                if self._pre_select_pos is None:
                    self._pre_select_pos = QPoint(self.mapFromGlobal(QCursor.pos()))
                step = 10 if mods & Qt.KeyboardModifier.ShiftModifier else 1
                dx = dy = 0
                if key == Qt.Key.Key_Left:    dx = -step
                elif key == Qt.Key.Key_Right: dx = step
                elif key == Qt.Key.Key_Up:    dy = -step
                elif key == Qt.Key.Key_Down:  dy = step
                self._pre_select_pos = QPoint(
                    max(0, min(self._pre_select_pos.x() + dx, self.width() - 1)),
                    max(0, min(self._pre_select_pos.y() + dy, self.height() - 1)),
                )
                self.update()
            elif self._selecting:
                # During drag: arrows fine-tune the end point
                step = 10 if mods & Qt.KeyboardModifier.ShiftModifier else 1
                dx = dy = 0
                if key == Qt.Key.Key_Left:    dx = -step
                elif key == Qt.Key.Key_Right: dx = step
                elif key == Qt.Key.Key_Up:    dy = -step
                elif key == Qt.Key.Key_Down:  dy = step
                self._end = QPoint(
                    max(0, min(self._end.x() + dx, self.width() - 1)),
                    max(0, min(self._end.y() + dy, self.height() - 1)),
                )
                self._arrow_loupe_pos = QPoint(self._end)
                self._selection = QRect(self._start, self._end).normalized()
                if self._selection.width() >= 1 and self._selection.height() >= 1:
                    self._update_dim_label()
                    self.update()

    # ── Help overlay ──────────────────────────────────────────────────────

    def _paint_help(self, painter: QPainter, lines: list[tuple[str, str]]):
        """Draw a compact help legend at the bottom-center of the screen."""
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        key_font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        desc_font = QFont("Segoe UI", 9)
        key_fm = QFontMetrics(key_font)
        desc_fm = QFontMetrics(desc_font)

        row_h = max(key_fm.height(), desc_fm.height()) + 4
        sep = 12   # gap between key and description
        col_gap = 24  # gap between columns

        # Measure each line
        items = []
        for key_text, desc_text in lines:
            kw = key_fm.horizontalAdvance(key_text)
            dw = desc_fm.horizontalAdvance(desc_text)
            items.append((key_text, desc_text, kw, dw))

        # Layout in two columns if > 4 items
        if len(items) > 4:
            mid = (len(items) + 1) // 2
            col1 = items[:mid]
            col2 = items[mid:]
        else:
            col1 = items
            col2 = []

        def col_width(col):
            if not col:
                return 0
            max_kw = max(kw for _, _, kw, _ in col)
            max_dw = max(dw for _, _, _, dw in col)
            return max_kw + sep + max_dw

        c1w = col_width(col1)
        c2w = col_width(col2)
        total_w = c1w + (col_gap + c2w if c2w else 0)
        n_rows = max(len(col1), len(col2))
        total_h = n_rows * row_h

        pad_x, pad_y = 16, 10
        box_w = total_w + pad_x * 2
        box_h = total_h + pad_y * 2
        bx = (self.width() - box_w) // 2
        by = self.height() - box_h - 20

        # Background box
        painter.setPen(QPen(QColor(80, 80, 100, 120), 1))
        painter.setBrush(HELP_BG)
        painter.drawRoundedRect(bx, by, box_w, box_h, 6, 6)

        def draw_col(col, x0, y0):
            if not col:
                return
            max_kw = max(kw for _, _, kw, _ in col)
            for i, (kt, dt, kw, dw) in enumerate(col):
                ty = y0 + i * row_h + key_fm.ascent() + 2
                # Key — right-aligned within max_kw
                painter.setFont(key_font)
                painter.setPen(HELP_KEY_COLOR)
                painter.drawText(x0 + max_kw - kw, ty, kt)
                # Description
                painter.setFont(desc_font)
                painter.setPen(HELP_TEXT_COLOR)
                painter.drawText(x0 + max_kw + sep, ty, dt)

        draw_col(col1, bx + pad_x, by + pad_y)
        if col2:
            draw_col(col2, bx + pad_x + c1w + col_gap, by + pad_y)

        painter.restore()

    def _update_dim_label(self):
        if self._selection.isNull():
            self._dim_label.hide()
            return
        sel = self._selection.normalized()
        text = f"{sel.width()} \u00d7 {sel.height()}"
        self._dim_label.setText(text)
        self._dim_label.adjustSize()
        lx = sel.center().x() - self._dim_label.width() // 2
        ly = sel.bottom() + 10
        if ly + self._dim_label.height() > self.height():
            ly = sel.top() - self._dim_label.height() - 10
        self._dim_label.move(max(0, lx), max(0, ly))
        self._dim_label.show()
