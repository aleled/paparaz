"""Windows OCR integration via winrt.

Usage:
    from paparaz.ui.ocr import ocr_selected_elements
    ocr_selected_elements(canvas, list_of_elements)

Requires:
    pip install winrt-Windows.Media.Ocr winrt-Windows.Graphics.Imaging
    pip install winrt-Windows.Storage winrt-Windows.Storage.Streams
"""

from __future__ import annotations

import asyncio
import os
import tempfile
import threading
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QTextEdit, QVBoxLayout,
)

if TYPE_CHECKING:
    from paparaz.ui.canvas import AnnotationCanvas

_DIALOG_STYLE = (
    "QDialog { background: #1e1e2e; color: #ccc; border: 1px solid #555; } "
    "QLabel { color: #aaa; font-size: 12px; } "
    "QTextEdit { background: #2a2a3e; color: #eee; border: 1px solid #555; "
    "            font-size: 13px; padding: 4px; } "
    "QPushButton { background: #740096; color: #fff; border: none; "
    "              padding: 5px 14px; border-radius: 3px; font-size: 12px; } "
    "QPushButton:hover { background: #9300bb; } "
)


# ---------------------------------------------------------------------------
# Render helpers
# ---------------------------------------------------------------------------

def _render_elements(elements: list) -> tuple[QPixmap | None, QRectF]:
    """Render *elements* onto a white pixmap sized to their union bounding rect."""
    union = QRectF()
    for elem in elements:
        union = union.united(elem.bounding_rect())
    if union.isEmpty():
        return None, union

    pad = 8
    union = union.adjusted(-pad, -pad, pad, pad)
    w, h = max(1, int(union.width())), max(1, int(union.height()))

    # Render at 3× scale — Windows OCR needs ~40 px per character height;
    # annotation strokes are typically small.
    SCALE = 3
    pix = QPixmap(w * SCALE, h * SCALE)
    pix.fill(Qt.GlobalColor.white)

    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.scale(SCALE, SCALE)
    p.translate(-union.x(), -union.y())
    for elem in elements:
        p.setOpacity(elem.style.opacity)
        elem.paint(p)
        p.setOpacity(1.0)
    p.end()

    return pix, union


# ---------------------------------------------------------------------------
# Bridge: lives in main thread, receives results from the OCR thread.
# Because the bridge object belongs to the main thread, emitting its signals
# from a worker thread automatically uses Qt's queued connection — the slot
# runs safely in the main thread's event loop.
# ---------------------------------------------------------------------------

class _ResultBridge(QObject):
    finished = Signal(str)
    error    = Signal(str)


# ---------------------------------------------------------------------------
# Async OCR function (runs inside threading.Thread)
# ---------------------------------------------------------------------------

async def _run_ocr_async(pixmap: QPixmap) -> str:
    try:
        import winrt.windows.media.ocr as WinOcr
        import winrt.windows.graphics.imaging as WinImaging
        import winrt.windows.storage as WinStorage
        import winrt.windows.globalization as WinGlob
        from winrt.windows.storage import FileAccessMode
    except ImportError as e:
        raise RuntimeError(
            f"Windows OCR requires the winrt packages.\n\n"
            f"Missing: {e}\n\n"
            f"Install with:\n"
            f"  pip install winrt-Windows.Media.Ocr winrt-Windows.Graphics.Imaging\n"
            f"  pip install winrt-Windows.Storage winrt-Windows.Globalization"
        )

    fd, tmp_path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    try:
        pixmap.save(tmp_path, "PNG")
        storage_file = await WinStorage.StorageFile.get_file_from_path_async(
            os.path.abspath(tmp_path)
        )
        stream  = await storage_file.open_async(FileAccessMode.READ)
        decoder = await WinImaging.BitmapDecoder.create_async(stream)
        bitmap  = await decoder.get_software_bitmap_async()

        # Try user profile languages first, then fall back to explicit en-US
        lang_tag = "user-profile"
        engine = WinOcr.OcrEngine.try_create_from_user_profile_languages()
        if engine is None:
            lang_tag = "en-US"
            lang = WinGlob.Language("en-US")
            engine = WinOcr.OcrEngine.try_create_from_language(lang)
        if engine is None:
            available = [
                l.language_tag
                for l in WinOcr.OcrEngine.get_available_recognizer_languages()
            ]
            lang_list = ", ".join(available) if available else "none"
            raise RuntimeError(
                f"No Windows OCR language pack found.\n\n"
                f"Available: {lang_list}\n\n"
                f"Install via: Settings → Time & Language → Language & region\n"
                f"→ your language → Language options → Optical character recognition → Download"
            )

        result = await engine.recognize_async(bitmap)
        lines = [line.text for line in result.lines]
        return "\n".join(lines), lang_tag
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _ocr_thread_func(pixmap: QPixmap, bridge: _ResultBridge):
    """Entry point for the worker thread — runs asyncio event loop to completion."""
    try:
        text, lang = asyncio.run(_run_ocr_async(pixmap))
        bridge.finished.emit(f"{lang}\x00{text}")   # pack lang+text, split on \x00
    except Exception as exc:
        bridge.error.emit(str(exc))


# ---------------------------------------------------------------------------
# Result dialog
# ---------------------------------------------------------------------------

class _OcrResultDialog(QDialog):
    def __init__(self, text: str, lang: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Recognized Text")
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )
        self.setMinimumWidth(380)
        self.setStyleSheet(_DIALOG_STYLE)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        if text.strip():
            label = QLabel(f"Edit recognized text before inserting:  "
                           f"<span style='color:#666;font-size:11px;'>[{lang}]</span>")
            label.setTextFormat(Qt.TextFormat.RichText)
        else:
            label = QLabel(
                f"<span style='color:#f0a040;'>OCR ({lang}) returned no text.</span><br>"
                f"<span style='color:#888;font-size:11px;'>"
                f"Windows OCR works best on printed text.<br>"
                f"Type the text manually or cancel.</span>"
            )
            label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(label)

        self._edit = QTextEdit()
        self._edit.setPlainText(text)
        self._edit.setMinimumHeight(80)
        layout.addWidget(self._edit)

        btns = QHBoxLayout()
        btns.setSpacing(8)

        insert_btn = QPushButton("Insert as Text")
        insert_btn.setDefault(True)
        insert_btn.clicked.connect(self.accept)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(
            "QPushButton { background: #333; color: #aaa; border: none; "
            "padding: 5px 14px; border-radius: 3px; }"
            "QPushButton:hover { background: #444; color: #fff; }"
        )
        cancel_btn.clicked.connect(self.reject)

        btns.addStretch()
        btns.addWidget(cancel_btn)
        btns.addWidget(insert_btn)
        layout.addLayout(btns)

    def result_text(self) -> str:
        return self._edit.toPlainText().strip()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def ocr_selected_elements(canvas: "AnnotationCanvas", elements: list):
    """Render *elements*, OCR them, show confirmation, replace with TextElement."""
    if not elements:
        return

    pix, union_rect = _render_elements(elements)
    if pix is None:
        return

    # Bridge lives in the main thread; signals emitted from worker thread
    # are automatically queued and delivered on the main thread event loop.
    bridge = _ResultBridge(parent=canvas)

    def on_finished(payload: str):
        lang, _, text = payload.partition("\x00")
        _handle_result(canvas, text, lang, elements, union_rect)
        bridge.deleteLater()

    def on_error(msg: str):
        QMessageBox.critical(canvas, "OCR Error", msg)
        bridge.deleteLater()

    bridge.finished.connect(on_finished)
    bridge.error.connect(on_error)

    # Plain Python thread — no QThread event-loop interference
    t = threading.Thread(
        target=_ocr_thread_func,
        args=(pix, bridge),
        daemon=True,
    )
    # Keep a reference so GC doesn't collect it before it finishes
    canvas._ocr_bridge = bridge
    canvas._ocr_thread_ref = t
    t.start()


def _handle_result(
    canvas: "AnnotationCanvas",
    text: str,
    lang: str,
    elements: list,
    union_rect: QRectF,
):
    dlg = _OcrResultDialog(text or "", lang, parent=canvas)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return

    final_text = dlg.result_text()
    if not final_text:
        return

    from paparaz.core.elements import TextElement
    from paparaz.core.history import Command

    style = canvas.current_style()
    style.foreground_color = "#000000"
    style.opacity = 1.0
    style.font_size = max(style.font_size, 12)  # guard against <=0

    new_elem = TextElement(union_rect.topLeft(), final_text, style)
    new_elem.rect = QRectF(
        union_rect.x(),
        union_rect.y(),
        max(union_rect.width(), 150.0),
        40.0,
    )
    new_elem.auto_size()

    to_delete = [e for e in elements if e in canvas.elements]
    indices   = {id(e): canvas.elements.index(e) for e in to_delete}
    min_idx   = min(indices.values()) if indices else len(canvas.elements)

    def do():
        for e in to_delete:
            if e in canvas.elements:
                canvas.elements.remove(e)
            e.selected = False
        canvas.elements.insert(min(min_idx, len(canvas.elements)), new_elem)
        canvas.selected_element = None
        canvas.element_selected.emit(None)
        canvas.update()

    def undo():
        if new_elem in canvas.elements:
            canvas.elements.remove(new_elem)
        for e in reversed(to_delete):
            idx = indices[id(e)]
            canvas.elements.insert(min(idx, len(canvas.elements)), e)
        canvas.update()

    canvas.history.execute(Command("OCR Replace", do, undo))
