"""PapaRaZ project file format (.papraz).

File layout: base64(zlib(JSON))
JSON schema:
  {
    "version": 1,
    "background": "<base64 PNG bytes>",
    "elements": [...],
    "meta": {"width": N, "height": N, "filename": "...", "dpr": 1.0}
  }
"""

from __future__ import annotations

import base64
import json
import zlib
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QPixmap, QImage

from paparaz.core.elements import element_from_dict

if TYPE_CHECKING:
    from paparaz.ui.canvas import AnnotationCanvas

FORMAT_VERSION = 1


def _pixmap_to_b64(pixmap: QPixmap) -> str:
    """Encode a QPixmap as a base64 PNG string."""
    buf = QByteArray()
    buffer = QBuffer(buf)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    pixmap.save(buffer, "PNG")
    buffer.close()
    return base64.b64encode(bytes(buf)).decode("ascii")


def _b64_to_pixmap(b64: str) -> QPixmap:
    """Decode a base64 PNG string back to a QPixmap."""
    raw = base64.b64decode(b64)
    pix = QPixmap()
    pix.loadFromData(raw, "PNG")
    return pix


def save_project(path: str, canvas: "AnnotationCanvas", filename: str = "") -> None:
    """Serialize canvas state to a .papraz file at *path*.

    Args:
        path: Destination file path (should end in .papraz).
        canvas: The AnnotationCanvas to serialize.
        filename: Optional original screenshot filename stored in metadata.
    """
    bg = canvas._background
    doc = {
        "version": FORMAT_VERSION,
        "background": _pixmap_to_b64(bg),
        "elements": [e.to_dict() for e in canvas.elements],
        "meta": {
            "width": bg.width(),
            "height": bg.height(),
            "filename": filename,
            "dpr": bg.devicePixelRatio(),
        },
    }
    raw = json.dumps(doc, ensure_ascii=True).encode("utf-8")
    compressed = zlib.compress(raw, level=6)
    blob = base64.b64encode(compressed)
    Path(path).write_bytes(blob)


def load_project(path: str, canvas: "AnnotationCanvas") -> dict:
    """Deserialize a .papraz file and restore canvas state.

    Clears existing elements and background, then loads the saved state.
    Returns the meta dict from the file.

    Args:
        path: Path to the .papraz file.
        canvas: The AnnotationCanvas to restore into.
    """
    blob = Path(path).read_bytes()
    compressed = base64.b64decode(blob)
    raw = zlib.decompress(compressed)
    doc = json.loads(raw.decode("utf-8"))

    version = doc.get("version", 1)
    if version > FORMAT_VERSION:
        raise ValueError(
            f"Project file version {version} is newer than supported ({FORMAT_VERSION}). "
            "Please upgrade PapaRaZ."
        )

    # Restore background
    bg = _b64_to_pixmap(doc["background"])
    if bg.isNull():
        raise ValueError("Project file contains an invalid or corrupt background image.")
    canvas._background = bg

    # Clear existing elements (bypass history — this is a full load)
    canvas.elements.clear()
    canvas.selected_element = None

    # Restore elements
    for d in doc.get("elements", []):
        elem = element_from_dict(d)
        if elem is not None:
            canvas.elements.append(elem)

    canvas.elements_changed.emit()
    canvas.update()

    return doc.get("meta", {})
