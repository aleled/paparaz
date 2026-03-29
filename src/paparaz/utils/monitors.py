"""Multi-monitor detection utilities for Windows."""

import ctypes
from ctypes import wintypes
from dataclasses import dataclass


@dataclass
class MonitorInfo:
    x: int
    y: int
    width: int
    height: int
    name: str
    is_primary: bool
    scale_factor: float = 1.0


def get_monitors() -> list[MonitorInfo]:
    """Get all connected monitors with their geometry and scale factors."""
    monitors = []

    # Enable DPI awareness
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor DPI aware
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass

    def _callback(hmonitor, hdc, lprect, lparam):
        info = ctypes.create_string_buffer(104)
        info_struct = ctypes.cast(info, ctypes.POINTER(ctypes.c_byte))
        ctypes.memmove(info_struct, ctypes.byref(ctypes.c_ulong(104)), 4)

        mi = wintypes.RECT()
        ctypes.windll.user32.GetMonitorInfoW(
            hmonitor,
            ctypes.cast(info_struct, ctypes.c_void_p)
        )

        rect = lprect.contents
        x, y = rect.left, rect.top
        w = rect.right - rect.left
        h = rect.bottom - rect.top

        # Get DPI scale
        scale = 1.0
        try:
            dpi_x = ctypes.c_uint()
            dpi_y = ctypes.c_uint()
            ctypes.windll.shcore.GetDpiForMonitor(
                hmonitor, 0, ctypes.byref(dpi_x), ctypes.byref(dpi_y)
            )
            scale = dpi_x.value / 96.0
        except (AttributeError, OSError):
            pass

        monitors.append(MonitorInfo(
            x=x, y=y, width=w, height=h,
            name=f"Monitor {len(monitors) + 1}",
            is_primary=(x == 0 and y == 0),
            scale_factor=scale,
        ))
        return True

    enum_callback = ctypes.WINFUNCTYPE(
        ctypes.c_bool,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.POINTER(wintypes.RECT),
        ctypes.c_void_p,
    )

    ctypes.windll.user32.EnumDisplayMonitors(
        None, None, enum_callback(_callback), 0
    )

    return monitors


def get_virtual_screen_geometry() -> tuple[int, int, int, int]:
    """Get the bounding rect of all monitors combined. Returns (x, y, width, height)."""
    SM_XVIRTUALSCREEN = 76
    SM_YVIRTUALSCREEN = 77
    SM_CXVIRTUALSCREEN = 78
    SM_CYVIRTUALSCREEN = 79

    x = ctypes.windll.user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    y = ctypes.windll.user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
    w = ctypes.windll.user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
    h = ctypes.windll.user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)

    return x, y, w, h
