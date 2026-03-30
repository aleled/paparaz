"""SVG icons for PapaRaZ tools - crisp, colored, 24x24 viewBox."""

import os
import tempfile

from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtSvg import QSvgRenderer

# Written once at import time; used in stylesheets via file URL
_ARROW_TEMP_PATH: str = ""


def _ensure_arrow_file() -> str:
    """Write the down-arrow SVG to a temp file and return the path (cached)."""
    global _ARROW_TEMP_PATH
    if _ARROW_TEMP_PATH and os.path.exists(_ARROW_TEMP_PATH):
        return _ARROW_TEMP_PATH
    svg = ICONS_SVG.get("down_arrow", "")
    if not svg:
        return ""
    try:
        fd, path = tempfile.mkstemp(prefix="paparaz_arrow_", suffix=".svg")
        with os.fdopen(fd, "w") as f:
            f.write(svg)
        _ARROW_TEMP_PATH = path.replace("\\", "/")
    except OSError:
        _ARROW_TEMP_PATH = ""
    return _ARROW_TEMP_PATH


def combo_arrow_css() -> str:
    """Return a QSS snippet that provides a visible down-arrow for QComboBox."""
    path = _ensure_arrow_file()
    if path:
        return (
            "QComboBox::drop-down { border: none; border-left: 1px solid #444; width: 16px; }"
            f"QComboBox::down-arrow {{ image: url({path}); width: 8px; height: 5px; }}"
        )
    # Fallback: rely on Qt default (may be invisible on dark themes)
    return "QComboBox::drop-down { border: none; width: 14px; }"

ICONS_SVG = {
    # ── TOOL ICONS (colored for quick recognition) ────────────────────────────

    # Select — white arrow cursor, clean and sharp
    "select": """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path fill="#E0E0E0" stroke="#BDBDBD" stroke-width="0.5"
            d="M5 2 L5 18 L8.5 14.5 L11.8 21 L13.8 20 L10.5 13.5 L15 13.5 Z"/>
    </svg>""",

    # Pen — blue nib with detail
    "pen": """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path fill="#64B5F6" d="M19.3 5.7a2 2 0 00-2.83 0l-1.06 1.06 2.83 2.83 1.06-1.06a2 2 0 000-2.83z"/>
      <path fill="#90CAF9" d="M4 18.5V21h2.5l8.12-8.12-2.5-2.5z"/>
      <path fill="#42A5F5" d="M14.12 10.88l-2.5-2.5-6.12 6.12 2.5 2.5z"/>
      <path fill="#1565C0" d="M4 21h2.5l-2.5-2.5z"/>
    </svg>""",

    # Brush — purple bristle brush
    "brush": """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path fill="#CE93D8" d="M20.71 4.63l-1.34-1.34a1 1 0 00-1.41 0L9 12.25 11.75 15l8.96-8.96a1 1 0 000-1.41z"/>
      <path fill="#BA68C8" d="M9 12.25L6.25 15 8.5 17.25 11.75 15z"/>
      <circle cx="6" cy="17" r="3" fill="#AB47BC"/>
      <circle cx="6" cy="17" r="1.5" fill="#7B1FA2"/>
    </svg>""",

    # Highlight — yellow marker bar
    "highlight": """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <rect x="2" y="7" width="20" height="10" rx="2" fill="#FFF176" opacity="0.7"/>
      <rect x="2" y="7" width="20" height="10" rx="2" fill="none" stroke="#F9A825" stroke-width="1.5"/>
      <rect x="1" y="18.5" width="22" height="3" rx="1.5" fill="#F9A825"/>
      <path stroke="#E65100" stroke-width="2" stroke-linecap="round" fill="none" d="M6 12h12"/>
    </svg>""",

    # Line — white diagonal with round endpoints
    "line": """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <line x1="4" y1="20" x2="20" y2="4" stroke="#E0E0E0" stroke-width="2.5" stroke-linecap="round"/>
      <circle cx="4" cy="20" r="2" fill="#BDBDBD"/>
      <circle cx="20" cy="4" r="2" fill="#BDBDBD"/>
    </svg>""",

    # Arrow — orange arrow with solid head
    "arrow": """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <line x1="5" y1="19" x2="17" y2="7" stroke="#FFAB40" stroke-width="2.5" stroke-linecap="round"/>
      <polygon fill="#FFAB40" points="19,5 12,7 17,12"/>
    </svg>""",

    # Curved arrow — orange arc with arrowhead
    "curved_arrow": """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path d="M4 18 Q14 2 20 10" fill="none" stroke="#FFAB40" stroke-width="2.5" stroke-linecap="round"/>
      <polygon fill="#FFAB40" points="20,10 14,8 18,14"/>
    </svg>""",

    # Rectangle — teal outlined rect with brighter corners
    "rectangle": """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <rect x="3" y="5" width="18" height="14" rx="1.5" fill="none" stroke="#80DEEA" stroke-width="2"/>
      <rect x="3" y="5" width="4" height="4" fill="#26C6DA" opacity="0.6"/>
      <rect x="17" y="15" width="4" height="4" fill="#26C6DA" opacity="0.6"/>
    </svg>""",

    # Ellipse — green oval with axis cross
    "ellipse": """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <ellipse cx="12" cy="12" rx="9" ry="7" fill="none" stroke="#A5D6A7" stroke-width="2"/>
      <line x1="3" y1="12" x2="21" y2="12" stroke="#66BB6A" stroke-width="1" stroke-dasharray="2 2" opacity="0.6"/>
      <line x1="12" y1="5" x2="12" y2="19" stroke="#66BB6A" stroke-width="1" stroke-dasharray="2 2" opacity="0.6"/>
    </svg>""",

    # Text — white T-bar, clean
    "text": """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path fill="#F5F5F5" d="M4 5v3h7v11h2V8h7V5z"/>
      <rect x="7" y="19" width="10" height="1.5" rx="0.75" fill="#BDBDBD"/>
    </svg>""",

    # Number — purple circle with white 1
    "number": """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <circle cx="12" cy="12" r="9.5" fill="#9C27B0"/>
      <circle cx="12" cy="12" r="9.5" fill="none" stroke="#CE93D8" stroke-width="1"/>
      <text x="12" y="16.5" text-anchor="middle" fill="white" font-size="12"
            font-weight="bold" font-family="Arial, sans-serif">1</text>
    </svg>""",

    # Eraser — pink/peach eraser block
    "eraser": """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path fill="#EF9A9A" stroke="#E57373" stroke-width="0.5"
            d="M15.7 3.3a1.5 1.5 0 012.1 0l2.9 2.9a1.5 1.5 0 010 2.1L13.5 15.5 8.5 10.5z"/>
      <path fill="#FFCDD2" stroke="#EF9A9A" stroke-width="0.5"
            d="M8.5 10.5L3.5 15.5a1.5 1.5 0 000 2.1L5.9 20H12l5.7-5.7z"/>
      <rect x="3" y="20" width="18" height="1.5" rx="0.75" fill="#EF9A9A"/>
    </svg>""",

    # Blur — blue pixelation mosaic
    "blur": """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <rect x="2" y="2" width="6" height="6" rx="1" fill="#4FC3F7" opacity="0.95"/>
      <rect x="9" y="2" width="6" height="6" rx="1" fill="#29B6F6" opacity="0.5"/>
      <rect x="16" y="2" width="6" height="6" rx="1" fill="#4FC3F7" opacity="0.95"/>
      <rect x="2" y="9" width="6" height="6" rx="1" fill="#29B6F6" opacity="0.5"/>
      <rect x="9" y="9" width="6" height="6" rx="1" fill="#4FC3F7" opacity="0.95"/>
      <rect x="16" y="9" width="6" height="6" rx="1" fill="#29B6F6" opacity="0.5"/>
      <rect x="2" y="16" width="6" height="6" rx="1" fill="#4FC3F7" opacity="0.95"/>
      <rect x="9" y="16" width="6" height="6" rx="1" fill="#29B6F6" opacity="0.5"/>
      <rect x="16" y="16" width="6" height="6" rx="1" fill="#4FC3F7" opacity="0.95"/>
    </svg>""",

    # Fill — green paint bucket with drip
    "fill": """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path fill="#81C784" d="M15.5 8.5L7 0 5.5 1.5l2.2 2.2-4.8 4.8a1.4 1.4 0 000 2L8 15.5c.3.3.7.4 1 .4s.7-.1 1-.4l5-5a1.4 1.4 0 000-2zM4.8 9.5L9 5.3 13.2 9.5z"/>
      <path fill="#A5D6A7" d="M18 11s-2 2.2-2 3.5a2 2 0 004 0c0-1.3-2-3.5-2-3.5z"/>
      <rect x="2" y="20" width="20" height="2" rx="1" fill="#66BB6A"/>
    </svg>""",

    # Stamp — gold star with detail
    "star": """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <polygon fill="#FFD54F" stroke="#F9A825" stroke-width="0.5"
               points="12,2 14.9,8.3 22,9.3 17,14.1 18.2,21 12,17.8 5.8,21 7,14.1 2,9.3 9.1,8.3"/>
    </svg>""",

    # Crop — white crop-frame marks
    "crop": """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path stroke="#E0E0E0" stroke-width="2" stroke-linecap="round" fill="none"
            d="M6 2v14a2 2 0 002 2h14"/>
      <path stroke="#E0E0E0" stroke-width="2" stroke-linecap="round" fill="none"
            d="M2 6h14a2 2 0 012 2v14"/>
    </svg>""",

    # ── ACTION ICONS ─────────────────────────────────────────────────────────

    "undo": """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path fill="#90CAF9" d="M12.5 8c-2.65 0-5.05 1-6.9 2.6L2 7v9h9l-3.62-3.62A8.49 8.49 0 0112.5 10c3.73 0 6.84 2.55 7.73 6l2.08-.68A10.52 10.52 0 0012.5 8z"/>
    </svg>""",

    "redo": """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path fill="#90CAF9" d="M18.4 10.6C16.55 9 14.15 8 11.5 8a10.52 10.52 0 00-9.81 7.32l2.08.68A8.46 8.46 0 0111.5 10c2.26 0 4.36.85 5.98 2.25L14 16h9V7z"/>
    </svg>""",

    "save": """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path fill="#80CBC4" d="M17 3H5a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2V7l-4-4z"/>
      <rect x="7" y="3" width="6" height="5" rx="0.5" fill="#00897B"/>
      <rect x="5" y="13" width="14" height="7" rx="0.5" fill="#00897B"/>
    </svg>""",

    "copy": """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <rect x="8" y="7" width="13" height="15" rx="1.5" fill="none" stroke="#E0E0E0" stroke-width="1.5"/>
      <rect x="3" y="2" width="13" height="15" rx="1.5" fill="#424242" stroke="#9E9E9E" stroke-width="1.5"/>
    </svg>""",

    "close": """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <circle cx="12" cy="12" r="10" fill="#B71C1C" opacity="0.8"/>
      <path stroke="white" stroke-width="2" stroke-linecap="round"
            d="M8 8l8 8M16 8l-8 8"/>
    </svg>""",

    "paste": """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path fill="#BCAAA4" d="M19 2h-4.18A3.01 3.01 0 0012 0a3.01 3.01 0 00-2.82 2H5a2 2 0 00-2 2v16a2 2 0 002 2h14a2 2 0 002-2V4a2 2 0 00-2-2zm-7 0a1 1 0 110 2 1 1 0 010-2zm7 18H5V4h2v3h10V4h2z"/>
    </svg>""",

    "pin": """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path fill="#FFA726" d="M16 12V4h1V2H7v2h1v8l-2 2v2h5.2v6h1.6v-6H18v-2z"/>
    </svg>""",

    "bring_front": """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <rect x="8" y="2" width="14" height="14" rx="2" fill="#E3F2FD" stroke="#42A5F5" stroke-width="1.5"/>
      <rect x="2" y="8" width="14" height="14" rx="2" fill="#1A237E" stroke="#5C6BC0" stroke-width="1.5"/>
    </svg>""",

    "send_back": """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <rect x="2" y="8" width="14" height="14" rx="2" fill="#E3F2FD" stroke="#42A5F5" stroke-width="1.5"/>
      <rect x="8" y="2" width="14" height="14" rx="2" fill="#1A237E" stroke="#5C6BC0" stroke-width="1.5"/>
    </svg>""",

    "resize_canvas": """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path stroke="#80DEEA" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"
            d="M3 9V4h5M3 4l5.5 5.5"/>
      <path stroke="#80DEEA" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"
            d="M21 15v5h-5M21 21l-5.5-5.5"/>
      <rect x="8.5" y="8.5" width="7" height="7" rx="1" fill="none"
            stroke="#4DD0E1" stroke-width="1.5" stroke-dasharray="2.5 1.5"/>
    </svg>""",

    "palette": """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path fill="#F3E5F5" d="M12 3a9 9 0 100 18 4 4 0 004-4c0-.5-.1-1-.2-1.4A2 2 0 0117.5 14H19a3 3 0 003-3c0-4.4-4.03-8-9-8z"/>
      <circle cx="6.5" cy="11.5" r="1.5" fill="#F44336"/>
      <circle cx="9.5" cy="7.5" r="1.5" fill="#FF9800"/>
      <circle cx="14.5" cy="7.5" r="1.5" fill="#FFEB3B"/>
      <circle cx="17.5" cy="11.5" r="1.5" fill="#4CAF50"/>
    </svg>""",

    # ── PANEL ICONS ──────────────────────────────────────────────────────────

    "bold": """<svg viewBox="0 0 24 24"><path fill="white" d="M15.6 10.79A3.62 3.62 0 0017 8a4 4 0 00-4-4H7v16h7a3.84 3.84 0 003.84-3.84A3.84 3.84 0 0015.6 10.79zM10 6.5h3a1.5 1.5 0 010 3h-3zm3.5 11H10v-3h3.5a1.5 1.5 0 010 3z"/></svg>""",

    "italic": """<svg viewBox="0 0 24 24"><path fill="white" d="M10 4v3h2.21l-3.42 8H6v3h8v-3h-2.21l3.42-8H18V4z"/></svg>""",

    "underline": """<svg viewBox="0 0 24 24"><path fill="white" d="M12 17c3.31 0 6-2.69 6-6V3h-2.5v8c0 1.93-1.57 3.5-3.5 3.5S8.5 12.93 8.5 11V3H6v8c0 3.31 2.69 6 6 6zm-7 2v2h14v-2z"/></svg>""",

    "strikethrough": """<svg viewBox="0 0 24 24"><path fill="white" d="M10 19h4v-3h-4v3zM5 4v3h5v3h4V7h5V4H5zM3 14h18v-2H3v2z"/></svg>""",

    "align_left": """<svg viewBox="0 0 24 24"><path fill="white" d="M15 15H3v2h12v-2zm0-8H3v2h12V7zM3 13h18v-2H3v2zM3 21h18v-2H3v2zM3 3v2h18V3H3z"/></svg>""",

    "align_center": """<svg viewBox="0 0 24 24"><path fill="white" d="M7 15v2h10v-2H7zm-4 6h18v-2H3v2zm0-8h18v-2H3v2zm4-6v2h10V7H7zM3 3v2h18V3H3z"/></svg>""",

    "align_right": """<svg viewBox="0 0 24 24"><path fill="white" d="M3 21h18v-2H3v2zm6-4h12v-2H9v2zm-6-4h18v-2H3v2zm6-4h12V7H9v2zM3 3v2h18V3H3z"/></svg>""",

    "rtl": """<svg viewBox="0 0 24 24"><path fill="white" d="M10 10v5h2V4h2v11h2V4h2V2h-8C7.79 2 6 3.79 6 6s1.79 4 4 4zm-2 7v-3l-4 4 4 4v-3h12v-2H8z"/></svg>""",

    "ltr": """<svg viewBox="0 0 24 24"><path fill="white" d="M10 10v5h2V4h2v11h2V4h2V2h-8C7.79 2 6 3.79 6 6s1.79 4 4 4zm10 4l-4-4v3H4v2h12v3z"/></svg>""",

    "shadow": """<svg viewBox="0 0 24 24"><rect x="3" y="3" width="14" height="14" rx="2" fill="none" stroke="white" stroke-width="2"/><rect x="7" y="7" width="14" height="14" rx="2" fill="white" opacity="0.3"/></svg>""",

    "background": """<svg viewBox="0 0 24 24"><rect x="2" y="2" width="20" height="20" rx="3" fill="white" opacity="0.3"/><path fill="white" d="M5 4v3h5.5v12h3V7H19V4z"/></svg>""",

    "zoom_in": """<svg viewBox="0 0 24 24"><path fill="white" d="M15.5 14h-.79l-.28-.27A6.47 6.47 0 0016 9.5 6.5 6.5 0 109.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14zm.5-7H9v2H7v1h2v2h1v-2h2V9h-2z"/></svg>""",

    "zoom_out": """<svg viewBox="0 0 24 24"><path fill="white" d="M15.5 14h-.79l-.28-.27A6.47 6.47 0 0016 9.5 6.5 6.5 0 109.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14zM7 9h5v1H7z"/></svg>""",

    "eyedropper": """<svg viewBox="0 0 24 24"><path fill="white" d="M20.71 5.63l-2.34-2.34a1 1 0 00-1.41 0l-3.12 3.12-1.42-1.42-1.41 1.42 1.41 1.41-7.07 7.07a1 1 0 000 1.42l2.34 2.34a1 1 0 001.42 0l7.07-7.07 1.41 1.41 1.42-1.41-1.42-1.42 3.12-3.12a1 1 0 000-1.41z"/></svg>""",

    "timer": """<svg viewBox="0 0 24 24"><path fill="white" d="M15 1H9v2h6V1zm-4 13h2V8h-2v6zm8.03-6.61l1.42-1.42c-.43-.51-.9-.99-1.41-1.41l-1.42 1.42A8.962 8.962 0 0012 4c-4.97 0-9 4.03-9 9s4.03 9 9 9 9-4.03 9-9c0-2.12-.74-4.07-1.97-5.61zM12 20c-3.87 0-7-3.13-7-7s3.13-7 7-7 7 3.13 7 7-3.13 7-7 7z"/></svg>""",

    "settings": """<svg viewBox="0 0 24 24"><path fill="white" d="M19.14 12.94a7.07 7.07 0 000-1.88l2.03-1.58a.49.49 0 00.12-.61l-1.92-3.32a.49.49 0 00-.59-.22l-2.39.96a7.04 7.04 0 00-1.62-.94l-.36-2.54a.48.48 0 00-.48-.41h-3.84a.48.48 0 00-.48.41l-.36 2.54a7.04 7.04 0 00-1.62.94l-2.39-.96a.49.49 0 00-.59.22L2.74 8.87a.48.48 0 00.12.61l2.03 1.58a7.07 7.07 0 000 1.88l-2.03 1.58a.49.49 0 00-.12.61l1.92 3.32a.49.49 0 00.59.22l2.39-.96c.5.38 1.04.7 1.62.94l.36 2.54a.48.48 0 00.48.41h3.84a.48.48 0 00.48-.41l.36-2.54a7.04 7.04 0 001.62-.94l2.39.96a.49.49 0 00.59-.22l1.92-3.32a.49.49 0 00-.12-.61zM12 15.6A3.6 3.6 0 1115.6 12 3.6 3.6 0 0112 15.6z"/></svg>""",

    # Link (chain links locked) — aspect ratio lock
    "link": """<svg viewBox="0 0 24 24"><path fill="white" d="M3.9 12c0-1.71 1.39-3.1 3.1-3.1h4V7H7a5 5 0 000 10h4v-1.9H7c-1.71 0-3.1-1.39-3.1-3.1zM8 13h8v-2H8v2zm9-6h-4v1.9h4c1.71 0 3.1 1.39 3.1 3.1s-1.39 3.1-3.1 3.1h-4V17h4a5 5 0 000-10z"/></svg>""",

    # Unlink (broken chain) — aspect ratio unlocked
    "unlink": """<svg viewBox="0 0 24 24"><path fill="white" d="M17 7h-4v1.9h4c1.71 0 3.1 1.39 3.1 3.1s-1.39 3.1-3.1 3.1h-4V17h4a5 5 0 000-10zm-9.9 5c0-1.71 1.39-3.1 3.1-3.1h.5V7H10a5 5 0 000 10h.6v-1.9H10c-1.71 0-3.1-1.39-3.1-3.1zM8 13h3.5v-2H8v2zm8 0h.5v-2H16v2zM3 5.27L1.73 4l-.73.74L3.27 7H3v1.9h.5A5.01 5.01 0 002 12a5 5 0 005 5h.5v-1.9H7a3.1 3.1 0 01-3.1-3.1c0-.98.46-1.84 1.18-2.4L7.27 11.73 8.73 10.27 3 4.54V5.27z" opacity="0.8"/><line x1="3" y1="3" x2="21" y2="21" stroke="white" stroke-width="2" stroke-linecap="round" opacity="0.6"/></svg>""",

    # Down arrow — for combo box dropdown indicator
    "down_arrow": """<svg viewBox="0 0 10 6" xmlns="http://www.w3.org/2000/svg"><polygon fill="#aaa" points="0,0 10,0 5,6"/></svg>""",

    # Slice — scissors cutting a rectangle
    "slice": """<svg viewBox="0 0 24 24"><path fill="white" d="M9.64 7.64c.23-.5.36-1.05.36-1.64C10 4.01 8.99 3 7.5 3S5 4.01 5 5.5 6.01 8 7.5 8c.59 0 1.14-.13 1.64-.36L11 10l-1.86 1.86C8.64 11.63 8.09 11.5 7.5 11.5c-1.49 0-2.5 1.01-2.5 2.5S6.01 16.5 7.5 16.5 10 15.49 10 14c0-.59-.13-1.14-.36-1.64L12 10.5l6 6H4v2h16V5.5z" opacity="0.9"/><line x1="4" y1="4" x2="20" y2="20" stroke="rgba(255,200,0,0.5)" stroke-width="1.5" stroke-dasharray="3 2" stroke-linecap="round"/></svg>""",
}


def svg_to_icon(svg_str: str, size: int = 24) -> QIcon:
    """Convert an SVG string to a crisp QIcon with 1× and 2× pixmaps for HiDPI."""
    renderer = QSvgRenderer(QByteArray(svg_str.encode()))
    icon = QIcon()
    for scale in (1, 2):
        px = QPixmap(size * scale, size * scale)
        px.setDevicePixelRatio(scale)
        px.fill(Qt.GlobalColor.transparent)
        p = QPainter(px)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        renderer.render(p, QRectF(0, 0, size, size))
        p.end()
        icon.addPixmap(px)
    return icon


def get_icon(name: str, size: int = 24) -> QIcon:
    """Get a tool icon by name."""
    svg = ICONS_SVG.get(name, "")
    if not svg:
        return QIcon()
    return svg_to_icon(svg, size)


def get_colored_icon(name: str, color: str, size: int = 24) -> QIcon:
    """Get an icon with a custom color (replaces white)."""
    svg = ICONS_SVG.get(name, "")
    if not svg:
        return QIcon()
    svg = svg.replace('fill="white"', f'fill="{color}"')
    svg = svg.replace('stroke="white"', f'stroke="{color}"')
    return svg_to_icon(svg, size)
