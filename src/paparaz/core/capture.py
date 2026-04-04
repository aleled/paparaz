"""Screen capture using Win32 API - single monitor under cursor, DPI-aware."""

import ctypes
from ctypes import wintypes
from PySide6.QtGui import QImage, QPixmap


def _ensure_dpi_aware():
    """Enable per-monitor DPI awareness."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass


def capture_region_native(x: int, y: int, width: int, height: int) -> QPixmap:
    """Capture a specific screen region using Win32 BitBlt (physical pixel coordinates)."""
    _ensure_dpi_aware()

    hdc_screen = ctypes.windll.user32.GetDC(None)
    hdc_mem = ctypes.windll.gdi32.CreateCompatibleDC(hdc_screen)
    hbmp = ctypes.windll.gdi32.CreateCompatibleBitmap(hdc_screen, width, height)
    old_bmp = ctypes.windll.gdi32.SelectObject(hdc_mem, hbmp)

    SRCCOPY = 0x00CC0020
    ctypes.windll.gdi32.BitBlt(
        hdc_mem, 0, 0, width, height,
        hdc_screen, x, y, SRCCOPY
    )

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
        buf, ctypes.byref(bmi), 0
    )

    ctypes.windll.gdi32.SelectObject(hdc_mem, old_bmp)
    ctypes.windll.gdi32.DeleteObject(hbmp)
    ctypes.windll.gdi32.DeleteDC(hdc_mem)
    ctypes.windll.user32.ReleaseDC(None, hdc_screen)

    img = QImage(buf, width, height, width * 4, QImage.Format.Format_ARGB32)
    img = img.copy()  # Deep copy since buf will be freed

    return QPixmap.fromImage(img)


def _get_monitor_physical_rect(screen):
    """Get the physical pixel rect for a QScreen using Win32 EnumDisplayMonitors.

    QScreen.geometry() returns logical coordinates in the virtual desktop, and
    multiplying by devicePixelRatio is wrong when monitors have different DPR
    values or negative virtual-desktop offsets.  Win32 gives us the true
    physical coordinates that BitBlt expects.
    """
    import ctypes
    from ctypes import wintypes

    # Build a map: logical (x, y) → physical RECT for every monitor
    MONITORINFOEX = type('MONITORINFOEX', (ctypes.Structure,), {
        '_fields_': [
            ('cbSize', wintypes.DWORD),
            ('rcMonitor', wintypes.RECT),
            ('rcWork', wintypes.RECT),
            ('dwFlags', wintypes.DWORD),
            ('szDevice', ctypes.c_wchar * 32),
        ]
    })

    geo = screen.geometry()
    target_lx, target_ly = geo.x(), geo.y()
    target_lw, target_lh = geo.width(), geo.height()
    dpr = screen.devicePixelRatio()

    # Fallback: classic dpr multiplication
    best = (int(target_lx * dpr), int(target_ly * dpr),
            int(target_lw * dpr), int(target_lh * dpr))

    monitors = []
    MONITORENUMPROC = ctypes.WINFUNCTYPE(
        wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC,
        ctypes.POINTER(wintypes.RECT), wintypes.LPARAM,
    )

    def callback(hmon, hdc, lprect, lparam):
        mi = MONITORINFOEX()
        mi.cbSize = ctypes.sizeof(MONITORINFOEX)
        ctypes.windll.user32.GetMonitorInfoW(hmon, ctypes.byref(mi))
        r = mi.rcMonitor
        monitors.append((r.left, r.top, r.right - r.left, r.bottom - r.top))
        return True

    ctypes.windll.user32.EnumDisplayMonitors(
        None, None, MONITORENUMPROC(callback), 0)

    # Match: find the Win32 monitor whose physical size matches screen's dpr-scaled size
    phys_w_expected = int(target_lw * dpr)
    phys_h_expected = int(target_lh * dpr)
    for mx, my, mw, mh in monitors:
        if abs(mw - phys_w_expected) <= 2 and abs(mh - phys_h_expected) <= 2:
            # Verify position sanity: logical * dpr should be close to physical
            if abs(mx - int(target_lx * dpr)) < mw and abs(my - int(target_ly * dpr)) < mh:
                best = (mx, my, mw, mh)
                break

    return best


def capture_monitor(screen) -> QPixmap:
    """Capture a single QScreen in its native physical resolution."""
    _ensure_dpi_aware()
    phys_x, phys_y, phys_w, phys_h = _get_monitor_physical_rect(screen)
    return capture_region_native(phys_x, phys_y, phys_w, phys_h)


def capture_region(pixmap: QPixmap, x: int, y: int, w: int, h: int) -> QPixmap:
    """Crop a region from an existing capture."""
    return pixmap.copy(x, y, w, h)
