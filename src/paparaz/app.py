"""Main application controller - orchestrates tray, hotkey, capture, editor, pin, settings."""

from PySide6.QtWidgets import QApplication, QFileDialog
from PySide6.QtCore import QObject, QPoint, QRect, QTimer, Qt
from PySide6.QtGui import QPixmap, QCursor, QPainter

from paparaz.core.capture import capture_monitor, capture_region
from paparaz.core.settings import SettingsManager
from paparaz.ui.tray import TrayIcon
from paparaz.ui.overlay import RegionSelector
from paparaz.ui.editor import EditorWindow
from paparaz.ui.pin_window import PinWindow
from paparaz.ui.settings_dialog import SettingsDialog
from paparaz.utils.hotkey import GlobalHotkeyListener


class PapaRazApp(QObject):
    """Main application controller."""

    def __init__(self, app: QApplication):
        super().__init__()
        self._app = app
        self._settings = SettingsManager()

        self._tray = TrayIcon(icon_color=self._settings.settings.tray_icon_color)
        self._overlay = None
        self._editors: list[EditorWindow] = []
        self._full_capture = None
        self._capture_screen = None  # QScreen being captured
        self._pin_windows: list[PinWindow] = []

        self._hotkey_listener = GlobalHotkeyListener()
        self._capture_hk_id = self._hotkey_listener.register(
            self._settings.settings.hotkeys.capture
        )
        self._fullscreen_hk_id = self._hotkey_listener.register(
            self._settings.settings.hotkeys.capture_fullscreen
        )
        self._window_hk_id = self._hotkey_listener.register(
            self._settings.settings.hotkeys.capture_window
        )
        self._repeat_hk_id = self._hotkey_listener.register(
            self._settings.settings.hotkeys.capture_repeat
        )
        self._last_capture_rect = None  # for repeat-last-region

        self._tray.capture_requested.connect(self._start_capture)
        self._tray.delay_capture_requested.connect(self._delay_capture)
        self._tray.open_image_requested.connect(self._open_image)
        self._tray.open_recent_requested.connect(self._open_recent)
        self._tray.settings_requested.connect(self._show_settings)
        self._tray.check_updates_requested.connect(self._check_updates_manual)
        self._tray.quit_requested.connect(self._quit)
        self._hotkey_listener.hotkey_pressed.connect(self._on_hotkey)

    def start(self):
        self._tray.show()
        # Clean up stale entries (files that no longer exist)
        self._cleanup_recent_captures()
        self._tray.update_recent(self._settings.settings.recent_captures)
        if self._settings.settings.show_tray_notification:
            self._tray.show_message("PapaRaZ", "Ready! Press PrintScreen to capture.")
        self._hotkey_listener.start()
        # Check for updates silently after 3 s so UI is fully ready first
        QTimer.singleShot(3000, self._check_updates)
        # Check for crash recovery files
        if getattr(self._settings.settings, 'crash_recovery', True):
            QTimer.singleShot(500, self._check_recovery)

    def _check_recovery(self):
        """Check for crash recovery files and offer to restore."""
        from paparaz.core.recovery import has_recovery, get_recovery_files, clear_recovery
        if not has_recovery():
            return
        files = get_recovery_files()
        from PySide6.QtWidgets import QMessageBox
        msg = QMessageBox()
        msg.setWindowTitle("PapaRaZ — Crash Recovery")
        msg.setWindowFlags(msg.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        msg.setText(f"Found {len(files)} unsaved capture(s) from a previous session.")
        msg.setInformativeText("Would you like to restore them?")
        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.Yes)
        if msg.exec() == QMessageBox.StandardButton.Yes:
            for f in files:
                pix = QPixmap(str(f))
                if not pix.isNull():
                    self._open_editor(pix)
        # Always clear recovery files after handling
        clear_recovery()

    def _check_updates(self):
        if self._settings.settings.auto_check_updates:
            from paparaz.utils.updater import check_for_updates
            check_for_updates()

    def _check_updates_manual(self):
        """Explicit user-triggered update check — always runs, shows 'up to date' message."""
        from paparaz.utils.updater import check_for_updates_manual
        check_for_updates_manual()

    def _on_hotkey(self, hk_id: int):
        if hk_id == self._capture_hk_id:
            QTimer.singleShot(150, self._start_capture)
        elif hk_id == self._fullscreen_hk_id:
            QTimer.singleShot(150, self._capture_fullscreen)
        elif hk_id == self._window_hk_id:
            QTimer.singleShot(150, self._capture_active_window)
        elif hk_id == self._repeat_hk_id:
            QTimer.singleShot(150, self._capture_repeat_last)

    def _delay_capture(self, seconds: int):
        self._tray.show_message("PapaRaZ", f"Capturing in {seconds} seconds...")
        QTimer.singleShot(seconds * 1000, self._start_capture)

    def _start_capture(self):
        # Hide editor windows if the setting says so
        if getattr(self._settings.settings, 'hide_editor_before_capture', True):
            for ed in self._editors:
                if ed.isVisible():
                    ed.hide()

        # Find which monitor the cursor is on
        cursor_pos = QCursor.pos()
        target_screen = None
        for screen in QApplication.screens():
            if screen.geometry().contains(cursor_pos):
                target_screen = screen
                break
        if not target_screen:
            target_screen = QApplication.primaryScreen()

        self._capture_screen = target_screen

        # Capture only that monitor (physical pixels)
        self._full_capture = capture_monitor(target_screen)

        # Remember cursor position for element creation after region selection
        self._capture_cursor_pos = cursor_pos

        # Play shutter sound if enabled
        if getattr(self._settings.settings, 'capture_sound', False):
            self._play_shutter_sound()

        # Show overlay on that monitor only
        self._overlay = RegionSelector(self._full_capture, target_screen)
        self._overlay.region_selected.connect(self._on_region_selected)
        self._overlay.selection_cancelled.connect(self._on_selection_cancelled)
        self._overlay.showFullScreen()

    def _on_region_selected(self, rect: QRect):
        if self._overlay:
            self._overlay.close()
            self._overlay = None

        if self._full_capture and self._capture_screen:
            # rect is in widget-local logical pixels → convert to physical for cropping
            dpr = self._capture_screen.devicePixelRatio()
            px = int(rect.x() * dpr)
            py = int(rect.y() * dpr)
            pw = int(rect.width() * dpr)
            ph = int(rect.height() * dpr)

            cropped = capture_region(self._full_capture, px, py, pw, ph)

            # Downscale physical-pixel capture back to logical pixels so the editor
            # shows the content at exactly 100% visual scale (1 logical px = 1 canvas px).
            if dpr != 1.0:
                from PySide6.QtCore import Qt as _Qt
                lw = max(1, int(round(pw / dpr)))
                lh = max(1, int(round(ph / dpr)))
                cropped = cropped.scaled(
                    lw, lh,
                    _Qt.AspectRatioMode.IgnoreAspectRatio,
                    _Qt.TransformationMode.SmoothTransformation,
                )

            # Save for repeat-last-region
            self._last_capture_rect = rect
            self._last_capture_screen = self._capture_screen

            # Build cursor element (always — user can DEL to remove)
            cursor_elem = self._cursor_element_for_region(
                self._capture_screen,
                getattr(self, '_capture_cursor_pos', QCursor.pos()),
                rect)

            self._restore_hidden_editors()
            self._open_editor(cropped, cursor_element=cursor_elem)

    def _on_selection_cancelled(self):
        if self._overlay:
            self._overlay.close()
            self._overlay = None
        self._restore_hidden_editors()

    def _capture_fullscreen(self):
        """Capture the entire monitor under the cursor — no overlay, instant."""
        if getattr(self._settings.settings, 'hide_editor_before_capture', True):
            for ed in self._editors:
                if ed.isVisible():
                    ed.hide()

        cursor_pos = QCursor.pos()
        target_screen = None
        for screen in QApplication.screens():
            if screen.geometry().contains(cursor_pos):
                target_screen = screen
                break
        if not target_screen:
            target_screen = QApplication.primaryScreen()

        pixmap = capture_monitor(target_screen)
        self._capture_screen = target_screen

        if getattr(self._settings.settings, 'capture_sound', False):
            self._play_shutter_sound()

        # Downscale to logical pixels
        dpr = target_screen.devicePixelRatio()
        if dpr != 1.0:
            geo = target_screen.geometry()
            pixmap = pixmap.scaled(
                geo.width(), geo.height(),
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

        # Build cursor element (always — user can DEL to remove)
        cursor_elem = self._cursor_element_fullscreen(target_screen, cursor_pos)

        self._restore_hidden_editors()
        self._open_editor(pixmap, cursor_element=cursor_elem)

    def _capture_active_window(self):
        """Capture the currently active (foreground) window."""
        import ctypes
        from ctypes import wintypes

        if getattr(self._settings.settings, 'hide_editor_before_capture', True):
            for ed in self._editors:
                if ed.isVisible():
                    ed.hide()
            # Brief delay so the window behind becomes foreground
            QTimer.singleShot(200, self._do_capture_active_window)
        else:
            self._do_capture_active_window()

    def _do_capture_active_window(self):
        import ctypes
        from ctypes import wintypes

        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if not hwnd:
            self._restore_hidden_editors()
            return

        rect = wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
        x, y = rect.left, rect.top
        w = rect.right - rect.left
        h = rect.bottom - rect.top
        if w <= 0 or h <= 0:
            self._restore_hidden_editors()
            return

        from paparaz.core.capture import capture_region_native
        pixmap = capture_region_native(x, y, w, h)

        if getattr(self._settings.settings, 'capture_sound', False):
            self._play_shutter_sound()

        # Downscale if hi-DPI
        screen = QApplication.screenAt(QPoint(x + w // 2, y + h // 2))
        if screen:
            dpr = screen.devicePixelRatio()
            if dpr != 1.0:
                lw = max(1, int(round(w / dpr)))
                lh = max(1, int(round(h / dpr)))
                pixmap = pixmap.scaled(
                    lw, lh,
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )

        # Build cursor element if enabled
        # Build cursor element (always — user can DEL to remove)
        cursor_elem = None
        from PySide6.QtCore import QPointF
        from paparaz.core.elements import ImageElement
        cursor_pos = QCursor.pos()
        dpr_val = screen.devicePixelRatio() if screen else 1.0
        rel_x = (cursor_pos.x() - x) / dpr_val
        rel_y = (cursor_pos.y() - y) / dpr_val
        if 0 <= rel_x < pixmap.width() and 0 <= rel_y < pixmap.height():
            cursor_pix, hx, hy = self._capture_system_cursor()
            cursor_elem = ImageElement(cursor_pix, QPointF(rel_x - hx, rel_y - hy))

        self._restore_hidden_editors()
        self._open_editor(pixmap, cursor_element=cursor_elem)

    def _capture_repeat_last(self):
        """Re-capture the exact same region as the last selection."""
        if not self._last_capture_rect or not getattr(self, '_last_capture_screen', None):
            # No previous region — fall back to regular capture
            self._start_capture()
            return

        if getattr(self._settings.settings, 'hide_editor_before_capture', True):
            for ed in self._editors:
                if ed.isVisible():
                    ed.hide()

        screen = self._last_capture_screen
        pixmap = capture_monitor(screen)
        self._capture_screen = screen
        self._full_capture = pixmap
        cursor_pos = QCursor.pos()

        if getattr(self._settings.settings, 'capture_sound', False):
            self._play_shutter_sound()

        rect = self._last_capture_rect
        dpr = screen.devicePixelRatio()
        px = int(rect.x() * dpr)
        py = int(rect.y() * dpr)
        pw = int(rect.width() * dpr)
        ph = int(rect.height() * dpr)
        cropped = capture_region(pixmap, px, py, pw, ph)

        if dpr != 1.0:
            lw = max(1, int(round(pw / dpr)))
            lh = max(1, int(round(ph / dpr)))
            cropped = cropped.scaled(
                lw, lh,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

        # Build cursor element (always — user can DEL to remove)
        cursor_elem = self._cursor_element_for_region(screen, cursor_pos, rect)

        self._restore_hidden_editors()
        self._open_editor(cropped, cursor_element=cursor_elem)

    def _restore_hidden_editors(self):
        """Re-show editors that were hidden before capture."""
        for ed in self._editors:
            if not ed.isVisible():
                ed.show()

    @staticmethod
    def _capture_system_cursor() -> "tuple[QPixmap, int, int]":
        """Capture the actual system cursor image using Win32 API.

        Returns (pixmap, hotspot_x, hotspot_y).  The hotspot is the offset
        from the cursor image's top-left to the click point — the element
        must be placed at (cursor_pos - hotspot) so the tip aligns correctly.
        Falls back to a generic arrow if the API fails.
        """
        import ctypes
        from ctypes import wintypes
        from PySide6.QtGui import QImage, QPixmap as _QP

        hotspot_x, hotspot_y = 0, 0

        try:
            # --- GetCursorInfo ---
            class CURSORINFO(ctypes.Structure):
                _fields_ = [
                    ("cbSize", wintypes.DWORD),
                    ("flags", wintypes.DWORD),
                    ("hCursor", wintypes.HANDLE),
                    ("ptScreenPos", wintypes.POINT),
                ]

            ci = CURSORINFO()
            ci.cbSize = ctypes.sizeof(CURSORINFO)
            if not ctypes.windll.user32.GetCursorInfo(ctypes.byref(ci)):
                raise OSError("GetCursorInfo failed")

            # CURSOR_SHOWING = 0x00000001
            if not (ci.flags & 1):
                raise OSError("Cursor hidden")

            # Copy the cursor handle so we can query it
            hicon = ctypes.windll.user32.CopyIcon(ci.hCursor)
            if not hicon:
                raise OSError("CopyIcon failed")

            # --- GetIconInfo → hotspot + mask/color bitmaps ---
            class ICONINFO(ctypes.Structure):
                _fields_ = [
                    ("fIcon", wintypes.BOOL),
                    ("xHotspot", wintypes.DWORD),
                    ("yHotspot", wintypes.DWORD),
                    ("hbmMask", wintypes.HBITMAP),
                    ("hbmColor", wintypes.HBITMAP),
                ]

            ii = ICONINFO()
            if not ctypes.windll.user32.GetIconInfo(hicon, ctypes.byref(ii)):
                ctypes.windll.user32.DestroyIcon(hicon)
                raise OSError("GetIconInfo failed")

            hotspot_x = ii.xHotspot
            hotspot_y = ii.yHotspot

            # --- Render cursor via DrawIconEx onto a DIB section ---
            # Determine cursor size from the mask bitmap
            class BITMAP(ctypes.Structure):
                _fields_ = [
                    ("bmType", ctypes.c_long),
                    ("bmWidth", ctypes.c_long),
                    ("bmHeight", ctypes.c_long),
                    ("bmWidthBytes", ctypes.c_long),
                    ("bmPlanes", wintypes.WORD),
                    ("bmBitsPixel", wintypes.WORD),
                    ("bmBits", ctypes.c_void_p),
                ]

            bm = BITMAP()
            ctypes.windll.gdi32.GetObjectW(
                ii.hbmMask, ctypes.sizeof(BITMAP), ctypes.byref(bm))
            cur_w = bm.bmWidth
            # If no color bitmap, mask height is 2× (AND + XOR masks stacked)
            cur_h = bm.bmHeight // 2 if not ii.hbmColor else bm.bmHeight

            # Clean up GDI bitmaps from GetIconInfo
            if ii.hbmMask:
                ctypes.windll.gdi32.DeleteObject(ii.hbmMask)
            if ii.hbmColor:
                ctypes.windll.gdi32.DeleteObject(ii.hbmColor)

            # Create a 32-bit ARGB DIB to draw into
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
            bmi.biWidth = cur_w
            bmi.biHeight = -cur_h  # top-down
            bmi.biPlanes = 1
            bmi.biBitCount = 32
            bmi.biCompression = 0  # BI_RGB

            hdc_screen = ctypes.windll.user32.GetDC(None)
            hdc_mem = ctypes.windll.gdi32.CreateCompatibleDC(hdc_screen)
            bits_ptr = ctypes.c_void_p()
            hbmp = ctypes.windll.gdi32.CreateDIBSection(
                hdc_mem, ctypes.byref(bmi), 0,
                ctypes.byref(bits_ptr), None, 0)
            old_bmp = ctypes.windll.gdi32.SelectObject(hdc_mem, hbmp)

            # Clear to transparent black
            buf_size = cur_w * cur_h * 4
            ctypes.memset(bits_ptr, 0, buf_size)

            # DI_NORMAL = 0x0003 (DI_MASK | DI_IMAGE)
            ctypes.windll.user32.DrawIconEx(
                hdc_mem, 0, 0, hicon,
                cur_w, cur_h, 0, None, 0x0003)

            # Read pixels
            buf = (ctypes.c_ubyte * buf_size)()
            ctypes.memmove(buf, bits_ptr, buf_size)

            ctypes.windll.gdi32.SelectObject(hdc_mem, old_bmp)
            ctypes.windll.gdi32.DeleteObject(hbmp)
            ctypes.windll.gdi32.DeleteDC(hdc_mem)
            ctypes.windll.user32.ReleaseDC(None, hdc_screen)
            ctypes.windll.user32.DestroyIcon(hicon)

            # Fix alpha: DrawIconEx on a DIB sometimes leaves alpha=0 for
            # opaque pixels.  If every pixel has alpha==0 the cursor would be
            # invisible, so detect that and set alpha=255 for non-black pixels.
            has_alpha = False
            for i in range(3, buf_size, 4):
                if buf[i] != 0:
                    has_alpha = True
                    break
            if not has_alpha:
                for i in range(0, buf_size, 4):
                    b, g, r = buf[i], buf[i + 1], buf[i + 2]
                    if b or g or r:
                        buf[i + 3] = 255

            img = QImage(bytes(buf), cur_w, cur_h, cur_w * 4,
                         QImage.Format.Format_ARGB32)
            img = img.copy()
            pix = _QP.fromImage(img)
            if pix.isNull():
                raise OSError("Null pixmap")
            return pix, hotspot_x, hotspot_y

        except (OSError, Exception):
            # Fallback: generic arrow
            from PySide6.QtGui import QPainter, QPixmap as _QP, QPen, QBrush, QColor, QPolygonF
            from PySide6.QtCore import QPointF
            cursor_pix = _QP(32, 48)
            cursor_pix.fill(Qt.GlobalColor.transparent)
            cp = QPainter(cursor_pix)
            cp.setRenderHint(QPainter.RenderHint.Antialiasing)
            arrow = QPolygonF([
                QPointF(0, 0), QPointF(0, 36), QPointF(9, 28),
                QPointF(16, 44), QPointF(22, 40), QPointF(15, 25),
                QPointF(24, 24), QPointF(0, 0),
            ])
            cp.setPen(QPen(QColor("black"), 2))
            cp.setBrush(QBrush(QColor("white")))
            cp.drawPolygon(arrow)
            cp.end()
            return cursor_pix, 0, 0

    def _cursor_element_for_region(self, screen, cursor_pos: QPoint,
                                   region: QRect) -> "ImageElement | None":
        """Build an ImageElement for the mouse cursor, positioned relative to
        the cropped region.  Returns None if cursor is outside the region."""
        from PySide6.QtCore import QPointF
        from paparaz.core.elements import ImageElement

        geo = screen.geometry()
        # Cursor in logical pixels relative to the monitor
        cx = cursor_pos.x() - geo.x()
        cy = cursor_pos.y() - geo.y()

        # Check if cursor falls inside the captured region
        if not region.contains(QPoint(cx, cy)):
            return None

        # Position relative to the cropped region's top-left, adjusted for hotspot
        cursor_pix, hx, hy = self._capture_system_cursor()
        rel_x = cx - region.x() - hx
        rel_y = cy - region.y() - hy

        elem = ImageElement(cursor_pix, QPointF(rel_x, rel_y))
        return elem

    def _cursor_element_fullscreen(self, screen, cursor_pos: QPoint) -> "ImageElement | None":
        """Build an ImageElement for the mouse cursor on a fullscreen capture."""
        from PySide6.QtCore import QPointF
        from paparaz.core.elements import ImageElement

        geo = screen.geometry()
        cursor_pix, hx, hy = self._capture_system_cursor()
        cx = cursor_pos.x() - geo.x() - hx
        cy = cursor_pos.y() - geo.y() - hy

        elem = ImageElement(cursor_pix, QPointF(cx, cy))
        return elem

    def _play_shutter_sound(self):
        """Play a camera shutter sound effect."""
        try:
            import winsound
            # Use a system asterisk as a stand-in; a custom .wav could be added later
            winsound.MessageBeep(winsound.MB_OK)
        except Exception:
            pass

    def _open_editor(self, pixmap: QPixmap, elements: list = None,
                     cursor_element=None):
        editor = EditorWindow(pixmap, settings_manager=self._settings)
        self._editors.append(editor)
        editor.closed.connect(lambda e=editor: self._on_editor_closed(e))
        editor.pin_requested.connect(self._pin_screenshot)
        editor.file_saved.connect(self._on_file_saved)
        if elements:
            editor._canvas.elements = elements
            editor._canvas.update()

        # Insert cursor as a deletable element — selected by default
        if cursor_element is not None:
            editor._canvas.add_element(cursor_element, auto_select=False)
            editor._canvas.select_element(cursor_element)

        # Auto-save capture to recent so the tray menu is always populated
        self._auto_save_recent(pixmap)

        # Restore saved geometry or size to capture + toolbar chrome
        saved_geo = getattr(self._settings.settings, 'window_geometry', '')
        restored = False
        if saved_geo and len(self._editors) == 1:
            try:
                parts = [int(v) for v in saved_geo.split(',')]
                if len(parts) == 4:
                    x, y, w, h = parts
                    editor.setGeometry(x, y, max(w, 400), max(h, 250))
                    restored = True
            except (ValueError, TypeError):
                pass
        if not restored:
            screen = QApplication.primaryScreen()
            if screen:
                avail = screen.availableGeometry()
                chrome_w = 16
                chrome_h = 60
                win_w = min(pixmap.width() + chrome_w, avail.width() - 40)
                win_h = min(pixmap.height() + chrome_h, avail.height() - 40)
                win_w = max(win_w, 400)
                win_h = max(win_h, 250)
                offset = (len(self._editors) - 1) * 24
                x = avail.x() + (avail.width()  - win_w) // 2 + offset
                y = avail.y() + (avail.height() - win_h) // 2 + offset
                x = min(x, avail.right()  - win_w)
                y = min(y, avail.bottom() - win_h)
                editor.setGeometry(x, y, win_w, win_h)
        editor.show()

    def _auto_save_recent(self, pixmap: QPixmap):
        """Save capture to a temp directory and add to recent captures list."""
        from pathlib import Path
        from datetime import datetime
        recent_dir = Path.home() / ".paparaz" / "recent"
        recent_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        path = recent_dir / f"capture_{ts}.png"
        pixmap.save(str(path), "PNG")

        self._settings.add_recent(str(path))
        self._tray.update_recent(self._settings.settings.recent_captures)

        # Prune old recent files: keep only the latest max_recent
        max_keep = self._settings.settings.max_recent
        files = sorted(recent_dir.glob("capture_*.png"), key=lambda f: f.stat().st_mtime, reverse=True)
        for old in files[max_keep:]:
            try:
                # Only delete if no longer in recent list
                if str(old) not in self._settings.settings.recent_captures:
                    old.unlink()
            except OSError:
                pass

    def _on_file_saved(self, path: str):
        """Record saved file in recent captures and refresh tray menu."""
        self._settings.add_recent(path)
        self._tray.update_recent(self._settings.settings.recent_captures)

    def _on_editor_closed(self, editor: EditorWindow):
        if editor in self._editors:
            self._editors.remove(editor)
        if not self._editors and getattr(self._settings.settings, 'exit_on_close', False):
            QApplication.quit()

    def _open_image(self):
        path, _ = QFileDialog.getOpenFileName(
            None, "Open Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;All Files (*)",
        )
        if path:
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                self._open_editor(pixmap)

    def _cleanup_recent_captures(self):
        """Remove entries for files that no longer exist."""
        from pathlib import Path
        orig = self._settings.settings.recent_captures
        valid = [p for p in orig if Path(p).exists()]
        if len(valid) != len(orig):
            self._settings.settings.recent_captures = valid
            self._settings.save()

    def _open_recent(self, path: str):
        from pathlib import Path
        if Path(path).exists():
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                self._open_editor(pixmap)
                return
        # File missing — remove from recent list and notify
        if path in self._settings.settings.recent_captures:
            self._settings.settings.recent_captures.remove(path)
            self._settings.save()
            self._tray.update_recent(self._settings.settings.recent_captures)
        self._tray.show_message("PapaRaZ", f"File not found:\n{Path(path).name}")

    def _pin_screenshot(self, rendered: QPixmap, background: QPixmap, elements: list):
        pin = PinWindow(rendered, background=background, elements=elements)
        pin.closed.connect(lambda: self._pin_windows.remove(pin) if pin in self._pin_windows else None)
        pin.edit_requested.connect(self._resume_editing_pin)
        pin.show()
        self._pin_windows.append(pin)

    def _resume_editing_pin(self, pin_window):
        if pin_window.background and not pin_window.background.isNull():
            self._open_editor(pin_window.background, elements=pin_window.elements)
            pin_window.close()

    def _show_settings(self):
        dlg = SettingsDialog(self._settings)
        dlg.exec()

    def _quit(self):
        self._hotkey_listener.stop()
        for pin in list(self._pin_windows):
            pin.close()
        for editor in list(self._editors):
            editor.close()
        self._app.quit()
