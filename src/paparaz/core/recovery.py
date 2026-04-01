"""Auto-save / crash recovery — periodic snapshots of editor canvas."""

from __future__ import annotations

import time
from pathlib import Path
from PySide6.QtGui import QPixmap


RECOVERY_DIR = Path.home() / ".paparaz" / "recovery"


def _ensure_dir():
    RECOVERY_DIR.mkdir(parents=True, exist_ok=True)


def save_snapshot(pixmap: QPixmap, editor_id: int) -> Path | None:
    """Save a recovery snapshot for a given editor. Returns the path."""
    _ensure_dir()
    path = RECOVERY_DIR / f"recovery_{editor_id}.png"
    if pixmap.save(str(path), "PNG"):
        return path
    return None


def get_recovery_files() -> list[Path]:
    """Return any existing recovery snapshot files."""
    _ensure_dir()
    return sorted(RECOVERY_DIR.glob("recovery_*.png"), key=lambda p: p.stat().st_mtime, reverse=True)


def clear_recovery(editor_id: int | None = None):
    """Remove recovery file(s). If editor_id is None, clear all."""
    _ensure_dir()
    if editor_id is not None:
        path = RECOVERY_DIR / f"recovery_{editor_id}.png"
        if path.exists():
            path.unlink()
    else:
        for f in RECOVERY_DIR.glob("recovery_*.png"):
            f.unlink()


def has_recovery() -> bool:
    """Check if there are any recovery files from a previous session."""
    return len(get_recovery_files()) > 0
