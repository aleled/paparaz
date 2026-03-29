"""SVG icons for PapaRaZ tools - Material Design style, white on dark."""

from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtSvg import QSvgRenderer

# All icons are white, 24x24 viewBox, Material Design inspired
ICONS_SVG = {
    "select": """<svg viewBox="0 0 24 24"><path fill="white" d="M7 2l12 11.2-5.8.5 3.3 7.3-2.2 1-3.2-7.4L7 18.5z"/></svg>""",

    "pen": """<svg viewBox="0 0 24 24"><path fill="white" d="M20.71 7.04a1 1 0 000-1.41l-2.34-2.34a1 1 0 00-1.41 0l-1.84 1.83 3.75 3.75zM3 17.25V21h3.75L17.81 9.94l-3.75-3.75z"/></svg>""",

    "brush": """<svg viewBox="0 0 24 24"><path fill="white" d="M7 14c-1.66 0-3 1.34-3 3 0 1.31-1.16 2-2 2 .92 1.22 2.49 2 4 2 2.21 0 4-1.79 4-4 0-1.66-1.34-3-3-3zm13.71-9.37l-1.34-1.34a1 1 0 00-1.41 0L9 12.25 11.75 15l8.96-8.96a1 1 0 000-1.41z"/></svg>""",

    "line": """<svg viewBox="0 0 24 24"><path fill="white" stroke="white" stroke-width="2" d="M4 20L20 4"/></svg>""",

    "arrow": """<svg viewBox="0 0 24 24"><path fill="white" d="M4 20L20 4M20 4v8M20 4h-8"/><path stroke="white" stroke-width="2.5" stroke-linecap="round" fill="none" d="M4 20L20 4"/></svg>""",

    "rectangle": """<svg viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="14" rx="1" fill="none" stroke="white" stroke-width="2"/></svg>""",

    "ellipse": """<svg viewBox="0 0 24 24"><ellipse cx="12" cy="12" rx="9" ry="7" fill="none" stroke="white" stroke-width="2"/></svg>""",

    "text": """<svg viewBox="0 0 24 24"><path fill="white" d="M5 4v3h5.5v12h3V7H19V4z"/></svg>""",

    "number": """<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" fill="none" stroke="white" stroke-width="2"/><text x="12" y="16.5" text-anchor="middle" fill="white" font-size="13" font-weight="bold" font-family="Arial">1</text></svg>""",

    "eraser": """<svg viewBox="0 0 24 24"><path fill="white" d="M16.24 3.56l4.95 4.94a1.5 1.5 0 010 2.12l-7.78 7.78H17v2H7l-1.41-1.41a1.5 1.5 0 010-2.12L16.24 3.56zm-1.41 1.41L5.17 14.63l3.54 3.54 9.66-9.66z"/></svg>""",

    "blur": """<svg viewBox="0 0 24 24"><rect x="3" y="3" width="4" height="4" fill="white" opacity="0.9"/><rect x="10" y="3" width="4" height="4" fill="white" opacity="0.5"/><rect x="17" y="3" width="4" height="4" fill="white" opacity="0.9"/><rect x="3" y="10" width="4" height="4" fill="white" opacity="0.5"/><rect x="10" y="10" width="4" height="4" fill="white" opacity="0.9"/><rect x="17" y="10" width="4" height="4" fill="white" opacity="0.5"/><rect x="3" y="17" width="4" height="4" fill="white" opacity="0.9"/><rect x="10" y="17" width="4" height="4" fill="white" opacity="0.5"/><rect x="17" y="17" width="4" height="4" fill="white" opacity="0.9"/></svg>""",

    "fill": """<svg viewBox="0 0 24 24"><path fill="white" d="M16.56 8.94L7.62 0 6.21 1.41l2.38 2.38-5.15 5.15a1.49 1.49 0 000 2.12l5.5 5.5c.29.29.68.44 1.06.44s.77-.15 1.06-.44l5.5-5.5a1.49 1.49 0 000-2.12zM5.21 10L10 5.21 14.79 10zM19 11.5s-2 2.17-2 3.5a2 2 0 104 0c0-1.33-2-3.5-2-3.5z"/></svg>""",

    "undo": """<svg viewBox="0 0 24 24"><path fill="white" d="M12.5 8c-2.65 0-5.05 1-6.9 2.6L2 7v9h9l-3.62-3.62A8.49 8.49 0 0112.5 10c3.73 0 6.84 2.55 7.73 6l2.08-.68A10.52 10.52 0 0012.5 8z"/></svg>""",

    "redo": """<svg viewBox="0 0 24 24"><path fill="white" d="M18.4 10.6C16.55 9 14.15 8 11.5 8a10.52 10.52 0 00-9.81 7.32l2.08.68A8.46 8.46 0 0111.5 10c2.26 0 4.36.85 5.98 2.25L14 16h9V7z"/></svg>""",

    "save": """<svg viewBox="0 0 24 24"><path fill="white" d="M17 3H5a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2V7l-4-4zm-5 16a3 3 0 110-6 3 3 0 010 6zm3-10H5V5h10z"/></svg>""",

    "copy": """<svg viewBox="0 0 24 24"><path fill="white" d="M16 1H4a2 2 0 00-2 2v14h2V3h12zm3 4H8a2 2 0 00-2 2v14a2 2 0 002 2h11a2 2 0 002-2V7a2 2 0 00-2-2zm0 16H8V7h11z"/></svg>""",

    "close": """<svg viewBox="0 0 24 24"><path fill="white" d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>""",

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

    "paste": """<svg viewBox="0 0 24 24"><path fill="white" d="M19 2h-4.18C14.4.84 13.3 0 12 0c-1.3 0-2.4.84-2.82 2H5a2 2 0 00-2 2v16a2 2 0 002 2h14a2 2 0 002-2V4a2 2 0 00-2-2zm-7 0a1 1 0 110 2 1 1 0 010-2zm7 18H5V4h2v3h10V4h2z"/></svg>""",

    "zoom_in": """<svg viewBox="0 0 24 24"><path fill="white" d="M15.5 14h-.79l-.28-.27A6.47 6.47 0 0016 9.5 6.5 6.5 0 109.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14zm.5-7H9v2H7v1h2v2h1v-2h2V9h-2z"/></svg>""",

    "zoom_out": """<svg viewBox="0 0 24 24"><path fill="white" d="M15.5 14h-.79l-.28-.27A6.47 6.47 0 0016 9.5 6.5 6.5 0 109.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14zM7 9h5v1H7z"/></svg>""",

    "settings": """<svg viewBox="0 0 24 24"><path fill="white" d="M19.14 12.94a7.07 7.07 0 000-1.88l2.03-1.58a.49.49 0 00.12-.61l-1.92-3.32a.49.49 0 00-.59-.22l-2.39.96a7.04 7.04 0 00-1.62-.94l-.36-2.54a.48.48 0 00-.48-.41h-3.84a.48.48 0 00-.48.41l-.36 2.54a7.04 7.04 0 00-1.62.94l-2.39-.96a.49.49 0 00-.59.22L2.74 8.87a.48.48 0 00.12.61l2.03 1.58a7.07 7.07 0 000 1.88l-2.03 1.58a.49.49 0 00-.12.61l1.92 3.32a.49.49 0 00.59.22l2.39-.96c.5.38 1.04.7 1.62.94l.36 2.54a.48.48 0 00.48.41h3.84a.48.48 0 00.48-.41l.36-2.54a7.04 7.04 0 001.62-.94l2.39.96a.49.49 0 00.59-.22l1.92-3.32a.49.49 0 00-.12-.61zM12 15.6A3.6 3.6 0 1115.6 12 3.6 3.6 0 0112 15.6z"/></svg>""",
}


def svg_to_icon(svg_str: str, size: int = 24) -> QIcon:
    """Convert an SVG string to a QIcon."""
    renderer = QSvgRenderer(QByteArray(svg_str.encode()))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


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
