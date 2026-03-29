"""Full-screen overlay for region selection - Flameshot-style dark overlay with selection hole."""

from PySide6.QtWidgets import QWidget, QLabel
from PySide6.QtCore import Qt, QRect, QPoint, QSize, Signal
from PySide6.QtGui import QPainter, QColor, QPixmap, QCursor, QFont, QPen, QRegion


# Flameshot colors
UI_COLOR = QColor(116, 0, 150)        # #740096 purple
OVERLAY_COLOR = QColor(0, 0, 0, 190)  # ~75% black overlay
HANDLE_COLOR = UI_COLOR
HANDLE_SIZE = 24                       # buttonBaseSize * 0.6
BORDER_WIDTH = 1


class RegionSelector(QWidget):
    """Full-screen overlay with Flameshot-style dark veil and selection hole."""

    region_selected = Signal(QRect)
    selection_cancelled = Signal()

    def __init__(self, screenshot: QPixmap, screen_offset: QPoint = QPoint(0, 0)):
        super().__init__()
        self._screenshot = screenshot
        self._screen_offset = screen_offset
        self._start = QPoint()
        self._end = QPoint()
        self._selecting = False
        self._selection = QRect()
        self._has_selection = False

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setGeometry(
            screen_offset.x(), screen_offset.y(),
            screenshot.width(), screenshot.height(),
        )

        # Dimension label
        self._dim_label = QLabel(self)
        self._dim_label.setStyleSheet(
            "background: rgba(116,0,150,220); color: white; padding: 4px 10px; "
            "border-radius: 4px; font-size: 12px; font-weight: bold;"
        )
        self._dim_label.hide()

        # Coordinate label
        self._coord_label = QLabel(self)
        self._coord_label.setStyleSheet(
            "background: rgba(0,0,0,180); color: #aaa; padding: 3px 8px; "
            "border-radius: 3px; font-size: 10px;"
        )
        self._coord_label.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw the full screenshot
        painter.drawPixmap(0, 0, self._screenshot)

        if self._has_selection and not self._selection.isNull():
            sel = self._selection.normalized()

            # Dark overlay OUTSIDE the selection (Flameshot's signature "hole" effect)
            overlay_region = QRegion(self.rect()).subtracted(QRegion(sel))
            painter.setClipRegion(overlay_region)
            painter.fillRect(self.rect(), OVERLAY_COLOR)
            painter.setClipping(False)

            # Selection border (purple)
            painter.setPen(QPen(UI_COLOR, BORDER_WIDTH))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(sel)

            # Resize handles (purple circles at corners and midpoints)
            painter.setPen(QPen(QColor("white"), 1))
            painter.setBrush(UI_COLOR)
            hs = HANDLE_SIZE // 2
            handles = self._get_handle_positions(sel)
            for hx, hy in handles:
                painter.drawEllipse(QPoint(hx, hy), hs, hs)
        else:
            # No selection yet - full dark overlay
            painter.fillRect(self.rect(), OVERLAY_COLOR)

            # Crosshair at cursor
            pos = self.mapFromGlobal(QCursor.pos())
            painter.setPen(QPen(UI_COLOR, 1, Qt.PenStyle.DashLine))
            painter.drawLine(pos.x(), 0, pos.x(), self.height())
            painter.drawLine(0, pos.y(), self.width(), pos.y())

            # Coordinate readout near cursor
            self._coord_label.setText(f"{pos.x() + self._screen_offset.x()}, {pos.y() + self._screen_offset.y()}")
            self._coord_label.adjustSize()
            self._coord_label.move(pos.x() + 15, pos.y() + 15)
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
                screen_rect = QRect(
                    self._selection.x() + self._screen_offset.x(),
                    self._selection.y() + self._screen_offset.y(),
                    self._selection.width(),
                    self._selection.height(),
                )
                self.region_selected.emit(screen_rect)
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
                screen_rect = QRect(
                    self._selection.x() + self._screen_offset.x(),
                    self._selection.y() + self._screen_offset.y(),
                    self._selection.width(),
                    self._selection.height(),
                )
                self.region_selected.emit(screen_rect)
                self.close()

    def _update_dim_label(self):
        if self._selection.isNull():
            self._dim_label.hide()
            return
        sel = self._selection.normalized()
        text = f"{sel.width()} \u00d7 {sel.height()}"
        self._dim_label.setText(text)
        self._dim_label.adjustSize()

        # Position below selection, centered
        lx = sel.center().x() - self._dim_label.width() // 2
        ly = sel.bottom() + 10
        if ly + self._dim_label.height() > self.height():
            ly = sel.top() - self._dim_label.height() - 10
        self._dim_label.move(max(0, lx), max(0, ly))
        self._dim_label.show()
