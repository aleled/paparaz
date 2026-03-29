"""Full-screen overlay for region selection on a single monitor.

Captures and overlays only the monitor the cursor is on, avoiding
DPI scaling mismatches between monitors.
"""

from PySide6.QtWidgets import QWidget, QLabel
from PySide6.QtCore import Qt, QRect, QPoint, Signal
from PySide6.QtGui import QPainter, QColor, QPixmap, QCursor, QPen, QRegion, QScreen

UI_COLOR = QColor(116, 0, 150)
OVERLAY_COLOR = QColor(0, 0, 0, 190)
HANDLE_SIZE = 24


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

        # Scale capture (physical pixels) to screen's logical pixel size
        self._screenshot = screenshot.scaled(
            self._screen_geo.width(), self._screen_geo.height(),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

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
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self.setFocus()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.drawPixmap(0, 0, self._screenshot)

        if self._has_selection and not self._selection.isNull():
            sel = self._selection.normalized()

            overlay_region = QRegion(self.rect()).subtracted(QRegion(sel))
            painter.setClipRegion(overlay_region)
            painter.fillRect(self.rect(), OVERLAY_COLOR)
            painter.setClipping(False)

            painter.setPen(QPen(UI_COLOR, 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(sel)

            painter.setPen(QPen(QColor("white"), 1))
            painter.setBrush(UI_COLOR)
            hs = HANDLE_SIZE // 2
            for hx, hy in self._get_handle_positions(sel):
                painter.drawEllipse(QPoint(hx, hy), hs, hs)
        else:
            painter.fillRect(self.rect(), OVERLAY_COLOR)

            pos = self.mapFromGlobal(QCursor.pos())
            painter.setPen(QPen(UI_COLOR, 1, Qt.PenStyle.DashLine))
            painter.drawLine(pos.x(), 0, pos.x(), self.height())
            painter.drawLine(0, pos.y(), self.width(), pos.y())

            abs_x = pos.x() + self._screen_geo.x()
            abs_y = pos.y() + self._screen_geo.y()
            self._coord_label.setText(f"{abs_x}, {abs_y}")
            self._coord_label.adjustSize()
            self._coord_label.move(
                min(pos.x() + 15, self.width() - self._coord_label.width() - 5),
                min(pos.y() + 15, self.height() - self._coord_label.height() - 5),
            )
            self._coord_label.show()

        painter.end()

    def _get_handle_positions(self, r: QRect) -> list[tuple[int, int]]:
        cx, cy = r.center().x(), r.center().y()
        return [
            (r.left(), r.top()), (cx, r.top()), (r.right(), r.top()),
            (r.left(), cy), (r.right(), cy),
            (r.left(), r.bottom()), (cx, r.bottom()), (r.right(), r.bottom()),
        ]

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._start = event.pos()
            self._selecting = True
            self._has_selection = True
            self._coord_label.hide()
        elif event.button() == Qt.MouseButton.RightButton:
            self.selection_cancelled.emit()
            self.close()

    def mouseMoveEvent(self, event):
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
            if self._selection.width() > 5 and self._selection.height() > 5:
                self.region_selected.emit(self._selection)
                self.close()
            else:
                self._has_selection = False
                self._selection = QRect()
                self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.selection_cancelled.emit()
            self.close()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self._has_selection and not self._selection.isNull():
                self.region_selected.emit(self._selection)
                self.close()

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
