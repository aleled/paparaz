"""Predefined stamp icons for the Stamp tool - transparent SVG renderers."""

from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import QByteArray

# Each stamp is a transparent SVG at 64x64 viewBox
STAMPS = {
    "check": {
        "label": "\u2713 Check",
        "svg": """<svg viewBox="0 0 64 64">
            <circle cx="32" cy="32" r="28" fill="#4CAF50" opacity="0.9"/>
            <path d="M20 33 L28 41 L44 23" stroke="white" stroke-width="5"
                  fill="none" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>""",
    },
    "cross": {
        "label": "\u2717 Cross",
        "svg": """<svg viewBox="0 0 64 64">
            <circle cx="32" cy="32" r="28" fill="#F44336" opacity="0.9"/>
            <path d="M22 22 L42 42 M42 22 L22 42" stroke="white" stroke-width="5"
                  fill="none" stroke-linecap="round"/>
        </svg>""",
    },
    "ok": {
        "label": "OK",
        "svg": """<svg viewBox="0 0 64 64">
            <rect x="4" y="14" width="56" height="36" rx="8" fill="#2196F3" opacity="0.9"/>
            <text x="32" y="40" text-anchor="middle" fill="white"
                  font-size="24" font-weight="bold" font-family="Arial">OK</text>
        </svg>""",
    },
    "bad": {
        "label": "BAD",
        "svg": """<svg viewBox="0 0 64 64">
            <rect x="4" y="14" width="56" height="36" rx="8" fill="#F44336" opacity="0.9"/>
            <text x="32" y="40" text-anchor="middle" fill="white"
                  font-size="22" font-weight="bold" font-family="Arial">BAD</text>
        </svg>""",
    },
    "approved": {
        "label": "APPROVED",
        "svg": """<svg viewBox="0 0 64 64" overflow="hidden">
            <rect x="2" y="16" width="60" height="32" rx="6"
                  fill="none" stroke="#4CAF50" stroke-width="3" opacity="0.9"/>
            <text x="32" y="37" text-anchor="middle" fill="#4CAF50"
                  font-size="11" font-weight="bold" font-family="Arial">APPROVED</text>
        </svg>""",
    },
    "rejected": {
        "label": "REJECTED",
        "svg": """<svg viewBox="0 0 64 64" overflow="hidden">
            <rect x="2" y="16" width="60" height="32" rx="6"
                  fill="none" stroke="#F44336" stroke-width="3" opacity="0.9"/>
            <text x="32" y="37" text-anchor="middle" fill="#F44336"
                  font-size="11" font-weight="bold" font-family="Arial">REJECTED</text>
        </svg>""",
    },
    "star": {
        "label": "\u2605 Star",
        "svg": """<svg viewBox="0 0 64 64">
            <polygon points="32,6 39,24 58,24 43,36 48,54 32,44 16,54 21,36 6,24 25,24"
                     fill="#FFC107" stroke="#FF9800" stroke-width="2" opacity="0.9"/>
        </svg>""",
    },
    "heart": {
        "label": "\u2665 Heart",
        "svg": """<svg viewBox="0 0 64 64">
            <path d="M32 56 C16 42 4 30 4 20 C4 12 10 6 18 6 C24 6 28 10 32 14
                     C36 10 40 6 46 6 C54 6 60 12 60 20 C60 30 48 42 32 56Z"
                  fill="#E91E63" opacity="0.9"/>
        </svg>""",
    },
    "warning": {
        "label": "\u26A0 Warning",
        "svg": """<svg viewBox="0 0 64 64">
            <polygon points="32,6 60,56 4,56" fill="#FF9800" stroke="#F57C00"
                     stroke-width="2" stroke-linejoin="round" opacity="0.9"/>
            <text x="32" y="48" text-anchor="middle" fill="white"
                  font-size="30" font-weight="bold" font-family="Arial">!</text>
        </svg>""",
    },
    "info": {
        "label": "\u24D8 Info",
        "svg": """<svg viewBox="0 0 64 64">
            <circle cx="32" cy="32" r="28" fill="#2196F3" opacity="0.9"/>
            <text x="32" y="24" text-anchor="middle" fill="white"
                  font-size="18" font-weight="bold" font-family="serif">i</text>
            <rect x="28" y="28" width="8" height="20" rx="2" fill="white"/>
        </svg>""",
    },
    "question": {
        "label": "? Question Mark",
        "svg": """<svg viewBox="0 0 64 64">
            <circle cx="32" cy="32" r="28" fill="#9C27B0" opacity="0.9"/>
            <text x="32" y="44" text-anchor="middle" fill="white"
                  font-size="34" font-weight="bold" font-family="Arial">?</text>
        </svg>""",
    },
    "thumbsup": {
        "label": "\U0001F44D Thumbs Up",
        "svg": """<svg viewBox="0 0 64 64">
            <circle cx="32" cy="32" r="28" fill="#4CAF50" opacity="0.85"/>
            <path d="M22 38 L22 28 L28 28 L32 18 L38 18 L38 28 L44 28 L44 44 L26 44 L22 38Z"
                  fill="white" stroke="white" stroke-width="1" stroke-linejoin="round"/>
        </svg>""",
    },
    "thumbsdown": {
        "label": "\U0001F44E Thumbs Down",
        "svg": """<svg viewBox="0 0 64 64">
            <circle cx="32" cy="32" r="28" fill="#F44336" opacity="0.85"/>
            <path d="M22 26 L22 36 L28 36 L32 46 L38 46 L38 36 L44 36 L44 20 L26 20 L22 26Z"
                  fill="white" stroke="white" stroke-width="1" stroke-linejoin="round"/>
        </svg>""",
    },
    "priority": {
        "label": "\u26A1 Priority",
        "svg": """<svg viewBox="0 0 64 64" overflow="hidden">
            <rect x="6" y="6" width="52" height="52" rx="8" fill="#FF5722" opacity="0.9"/>
            <text x="32" y="27" text-anchor="middle" fill="white"
                  font-size="11" font-weight="bold" font-family="Arial">HIGH</text>
            <text x="32" y="44" text-anchor="middle" fill="#FFEB3B"
                  font-size="11" font-weight="bold" font-family="Arial">PRIORITY</text>
        </svg>""",
    },
    "bug": {
        "label": "\U0001F41B Bug",
        "svg": """<svg viewBox="0 0 64 64" overflow="hidden">
            <circle cx="32" cy="36" r="20" fill="#F44336" opacity="0.85"/>
            <circle cx="32" cy="18" r="10" fill="#D32F2F"/>
            <text x="32" y="42" text-anchor="middle" fill="white"
                  font-size="13" font-weight="bold" font-family="Arial">BUG</text>
        </svg>""",
    },
    "note": {
        "label": "\U0001F4DD Note",
        "svg": """<svg viewBox="0 0 64 64">
            <rect x="10" y="6" width="44" height="52" rx="4" fill="#FFF9C4" opacity="0.95"
                  stroke="#FBC02D" stroke-width="2"/>
            <line x1="18" y1="20" x2="46" y2="20" stroke="#999" stroke-width="1.5"/>
            <line x1="18" y1="28" x2="46" y2="28" stroke="#999" stroke-width="1.5"/>
            <line x1="18" y1="36" x2="38" y2="36" stroke="#999" stroke-width="1.5"/>
        </svg>""",
    },
}

_renderers: dict[str, QSvgRenderer] = {}


def get_stamp_renderer(stamp_id: str) -> QSvgRenderer | None:
    """Get a cached SVG renderer for the given stamp ID."""
    if stamp_id not in _renderers:
        stamp = STAMPS.get(stamp_id)
        if not stamp:
            return None
        renderer = QSvgRenderer(QByteArray(stamp["svg"].encode()))
        _renderers[stamp_id] = renderer
    return _renderers[stamp_id]


def get_stamp_ids() -> list[str]:
    return list(STAMPS.keys())


def get_stamp_label(stamp_id: str) -> str:
    return STAMPS.get(stamp_id, {}).get("label", stamp_id)
