"""Export functionality: PNG, JPG, SVG, clipboard."""

from pathlib import Path
from PySide6.QtCore import QBuffer, QIODevice, QMimeData, QByteArray
from PySide6.QtGui import QPixmap, QImage, QPainter
from PySide6.QtWidgets import QApplication
from PySide6.QtSvg import QSvgGenerator


def save_png(pixmap: QPixmap, path: str) -> bool:
    return pixmap.save(path, "PNG")


def save_jpg(pixmap: QPixmap, path: str, quality: int = 90) -> bool:
    return pixmap.save(path, "JPEG", quality)


def save_svg(pixmap: QPixmap, path: str, paint_callback=None) -> bool:
    """Export as SVG. paint_callback(painter) draws annotations over the image."""
    generator = QSvgGenerator()
    generator.setFileName(path)
    generator.setSize(pixmap.size())
    generator.setViewBox(pixmap.rect())
    generator.setTitle("PapaRaZ Capture")

    painter = QPainter()
    painter.begin(generator)
    painter.drawPixmap(0, 0, pixmap)
    if paint_callback:
        paint_callback(painter)
    painter.end()
    return Path(path).exists()


def copy_to_clipboard(pixmap: QPixmap):
    """Copy pixmap to system clipboard."""
    clipboard = QApplication.clipboard()
    clipboard.setPixmap(pixmap)


def render_final(background: QPixmap, paint_callback=None) -> QPixmap:
    """Render the background with all annotations as a single pixmap."""
    result = QPixmap(background.size())
    painter = QPainter(result)
    painter.drawPixmap(0, 0, background)
    if paint_callback:
        paint_callback(painter)
    painter.end()
    return result
