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

    # ── Transparent-background variants ──────────────────────────────────────
    "check_t": {
        "label": "\u2713 Check (clear)",
        "svg": """<svg viewBox="0 0 64 64">
            <path d="M12 33 L26 47 L52 18" stroke="#4CAF50" stroke-width="7"
                  fill="none" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>""",
    },
    "cross_t": {
        "label": "\u2717 Cross (clear)",
        "svg": """<svg viewBox="0 0 64 64">
            <path d="M16 16 L48 48 M48 16 L16 48" stroke="#F44336" stroke-width="7"
                  fill="none" stroke-linecap="round"/>
        </svg>""",
    },
    "ok_t": {
        "label": "OK (clear)",
        "svg": """<svg viewBox="0 0 64 64">
            <text x="32" y="46" text-anchor="middle" fill="#2196F3"
                  font-size="36" font-weight="bold" font-family="Arial">OK</text>
        </svg>""",
    },
    "bad_t": {
        "label": "BAD (clear)",
        "svg": """<svg viewBox="0 0 64 64">
            <text x="32" y="44" text-anchor="middle" fill="#F44336"
                  font-size="30" font-weight="bold" font-family="Arial">BAD</text>
        </svg>""",
    },
    "info_t": {
        "label": "\u24D8 Info (clear)",
        "svg": """<svg viewBox="0 0 64 64">
            <circle cx="32" cy="32" r="27" fill="none" stroke="#2196F3" stroke-width="3.5"/>
            <text x="32" y="24" text-anchor="middle" fill="#2196F3"
                  font-size="18" font-weight="bold" font-family="serif">i</text>
            <rect x="28" y="28" width="8" height="20" rx="2" fill="#2196F3"/>
        </svg>""",
    },
    "question_t": {
        "label": "? Question (clear)",
        "svg": """<svg viewBox="0 0 64 64">
            <circle cx="32" cy="32" r="27" fill="none" stroke="#9C27B0" stroke-width="3.5"/>
            <text x="32" y="45" text-anchor="middle" fill="#9C27B0"
                  font-size="34" font-weight="bold" font-family="Arial">?</text>
        </svg>""",
    },
    "thumbsup_t": {
        "label": "\U0001F44D Thumbs Up (clear)",
        "svg": """<svg viewBox="0 0 64 64">
            <path d="M22 38 L22 28 L28 28 L32 18 L38 18 L38 28 L44 28 L44 44 L26 44 L22 38Z"
                  fill="#4CAF50" stroke="#388E3C" stroke-width="1.5"
                  stroke-linejoin="round"/>
        </svg>""",
    },
    "thumbsdown_t": {
        "label": "\U0001F44E Thumbs Down (clear)",
        "svg": """<svg viewBox="0 0 64 64">
            <path d="M22 26 L22 36 L28 36 L32 46 L38 46 L38 36 L44 36 L44 20 L26 20 L22 26Z"
                  fill="#F44336" stroke="#C62828" stroke-width="1.5"
                  stroke-linejoin="round"/>
        </svg>""",
    },
    "priority_t": {
        "label": "\u26A1 Priority (clear)",
        "svg": """<svg viewBox="0 0 64 64">
            <text x="32" y="29" text-anchor="middle" fill="#FF5722"
                  font-size="15" font-weight="bold" font-family="Arial">HIGH</text>
            <text x="32" y="47" text-anchor="middle" fill="#FF5722"
                  font-size="14" font-weight="bold" font-family="Arial">PRIORITY</text>
        </svg>""",
    },
    "bug_t": {
        "label": "\U0001F41B Bug (clear)",
        "svg": """<svg viewBox="0 0 64 64">
            <text x="32" y="44" text-anchor="middle" fill="#F44336"
                  font-size="32" font-weight="bold" font-family="Arial">BUG</text>
        </svg>""",
    },

    # ── Extra text stamps ─────────────────────────────────────────────────────
    "wip": {
        "label": "WIP",
        "svg": """<svg viewBox="0 0 64 64">
            <rect x="2" y="16" width="60" height="32" rx="6"
                  fill="none" stroke="#FF9800" stroke-width="3" stroke-dasharray="6 3"/>
            <text x="32" y="37" text-anchor="middle" fill="#FF9800"
                  font-size="14" font-weight="bold" font-family="Arial">WIP</text>
        </svg>""",
    },
    "draft": {
        "label": "DRAFT",
        "svg": """<svg viewBox="0 0 64 64">
            <rect x="2" y="16" width="60" height="32" rx="6"
                  fill="none" stroke="#9E9E9E" stroke-width="3" stroke-dasharray="6 3"/>
            <text x="32" y="37" text-anchor="middle" fill="#9E9E9E"
                  font-size="13" font-weight="bold" font-family="Arial">DRAFT</text>
        </svg>""",
    },
    "todo": {
        "label": "TODO",
        "svg": """<svg viewBox="0 0 64 64">
            <rect x="2" y="16" width="60" height="32" rx="6"
                  fill="none" stroke="#03A9F4" stroke-width="3"/>
            <text x="32" y="37" text-anchor="middle" fill="#03A9F4"
                  font-size="14" font-weight="bold" font-family="Arial">TODO</text>
        </svg>""",
    },
    "done": {
        "label": "DONE",
        "svg": """<svg viewBox="0 0 64 64">
            <rect x="2" y="16" width="60" height="32" rx="6"
                  fill="none" stroke="#4CAF50" stroke-width="3"/>
            <text x="32" y="37" text-anchor="middle" fill="#4CAF50"
                  font-size="14" font-weight="bold" font-family="Arial">DONE</text>
        </svg>""",
    },
    "fix": {
        "label": "FIX",
        "svg": """<svg viewBox="0 0 64 64">
            <rect x="2" y="16" width="60" height="32" rx="6"
                  fill="none" stroke="#FF5722" stroke-width="3"/>
            <text x="32" y="37" text-anchor="middle" fill="#FF5722"
                  font-size="16" font-weight="bold" font-family="Arial">FIX</text>
        </svg>""",
    },
    "new": {
        "label": "\u2605 NEW",
        "svg": """<svg viewBox="0 0 64 64">
            <polygon points="32,4 37,22 56,22 41,33 46,51 32,41 18,51 23,33 8,22 27,22"
                     fill="#FF5722" stroke="#BF360C" stroke-width="1.5"/>
            <text x="32" y="36" text-anchor="middle" fill="white"
                  font-size="11" font-weight="bold" font-family="Arial">NEW</text>
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
