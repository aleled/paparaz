"""Screen capture using Win32 API for reliable multi-monitor support."""

import ctypes
from ctypes import wintypes
from PySide6.QtGui import QImage, QPixmap
from paparaz.utils.monitors import get_virtual_screen_geometry


def capture_all_screens() -> QPixmap:
    """Capture the entire virtual screen (all monitors)."""
    # DPI awareness
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass

    x, y, width, height = get_virtual_screen_geometry()

    hdc_screen = ctypes.windll.user32.GetDC(None)
    hdc_mem = ctypes.windll.gdi32.CreateCompatibleDC(hdc_screen)
    hbmp = ctypes.windll.gdi32.CreateCompatibleBitmap(hdc_screen, width, height)
    old_bmp = ctypes.windll.gdi32.SelectObject(hdc_mem, hbmp)

    # BitBlt from screen to memory DC
    SRCCOPY = 0x00CC0020
    ctypes.windll.gdi32.BitBlt(
        hdc_mem, 0, 0, width, height,
        hdc_screen, x, y, SRCCOPY
    )

    # Get bitmap data
    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize", wintypes.DWORD),
            ("biWidth", ctypes.c_long),
            ("biHeight", ctypes.c_long),
            ("biPlanes", wintypes.WORD),
            ("biBitCount", wintypes.WORD),
            ("biCompression", wintypes.DWORD),
            ("biSizeImage", wintypes.DWORD),
            ("biXPelsPerMeter", ctypes.c_long),
            ("biYPelsPerMeter", ctypes.c_long),
            ("biClrUsed", wintypes.DWORD),
            ("biClrImportant", wintypes.DWORD),
        ]

    bmi = BITMAPINFOHEADER()
    bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.biWidth = width
    bmi.biHeight = -height  # Top-down DIB
    bmi.biPlanes = 1
    bmi.biBitCount = 32
    bmi.biCompression = 0  # BI_RGB

    buf_size = width * height * 4
    buf = ctypes.create_string_buffer(buf_size)

    ctypes.windll.gdi32.GetDIBits(
        hdc_mem, hbmp, 0, height,
        buf, ctypes.byref(bmi), 0  # DIB_RGB_COLORS
    )

    # Cleanup GDI objects
    ctypes.windll.gdi32.SelectObject(hdc_mem, old_bmp)
    ctypes.windll.gdi32.DeleteObject(hbmp)
    ctypes.windll.gdi32.DeleteDC(hdc_mem)
    ctypes.windll.user32.ReleaseDC(None, hdc_screen)

    # Convert BGRA buffer to QImage
    img = QImage(buf, width, height, width * 4, QImage.Format.Format_ARGB32)
    # QImage references the buffer, so we need a deep copy
    img = img.copy()

    return QPixmap.fromImage(img)


def capture_region(pixmap: QPixmap, x: int, y: int, w: int, h: int) -> QPixmap:
    """Crop a region from an existing capture."""
    return pixmap.copy(x, y, w, h)
