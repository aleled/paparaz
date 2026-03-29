"""Main application controller - orchestrates tray, hotkey, capture, editor, pin, settings."""

from PySide6.QtWidgets import QApplication, QFileDialog
from PySide6.QtCore import QObject, QPoint, QRect, QTimer
from PySide6.QtGui import QPixmap, QCursor

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

        self._tray = TrayIcon()
        self._overlay = None
        self._editor = None
        self._full_capture = None
        self._capture_screen = None  # QScreen being captured
        self._pin_windows: list[PinWindow] = []

        self._hotkey_listener = GlobalHotkeyListener()
        self._capture_hk_id = self._hotkey_listener.register(
            self._settings.settings.hotkeys.capture
        )

        self._tray.capture_requested.connect(self._start_capture)
        self._tray.delay_capture_requested.connect(self._delay_capture)
        self._tray.open_image_requested.connect(self._open_image)
        self._tray.open_recent_requested.connect(self._open_recent)
        self._tray.settings_requested.connect(self._show_settings)
        self._tray.quit_requested.connect(self._quit)
        self._hotkey_listener.hotkey_pressed.connect(self._on_hotkey)

    def start(self):
        self._tray.show()
        self._tray.update_recent(self._settings.settings.recent_captures)
        if self._settings.settings.show_tray_notification:
            self._tray.show_message("PapaRaZ", "Ready! Press PrintScreen to capture.")
        self._hotkey_listener.start()

    def _on_hotkey(self, hk_id: int):
        if hk_id == self._capture_hk_id:
            QTimer.singleShot(150, self._start_capture)

    def _delay_capture(self, seconds: int):
        self._tray.show_message("PapaRaZ", f"Capturing in {seconds} seconds...")
        QTimer.singleShot(seconds * 1000, self._start_capture)

    def _start_capture(self):
        if self._editor:
            self._editor.hide()

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
            # rect is in widget-local logical pixels
            # Scale to physical pixels in the capture
            dpr = self._capture_screen.devicePixelRatio()
            px = int(rect.x() * dpr)
            py = int(rect.y() * dpr)
            pw = int(rect.width() * dpr)
            ph = int(rect.height() * dpr)

            cropped = capture_region(self._full_capture, px, py, pw, ph)
            self._open_editor(cropped)

    def _on_selection_cancelled(self):
        if self._overlay:
            self._overlay.close()
            self._overlay = None

    def _open_editor(self, pixmap: QPixmap, elements: list = None):
        self._editor = EditorWindow(pixmap, settings_manager=self._settings)
        self._editor.closed.connect(self._on_editor_closed)
        self._editor.pin_requested.connect(self._pin_screenshot)
        if elements:
            self._editor._canvas.elements = elements
            self._editor._canvas.update()

        # Size window to fit capture + UI chrome, capped to screen
        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            # Add space for side panel (~186px), toolbar (~60px), status bar (~25px), borders
            chrome_w = 186 + 20
            chrome_h = 60 + 25 + 20
            win_w = min(pixmap.width() + chrome_w, avail.width())
            win_h = min(pixmap.height() + chrome_h, avail.height())
            # Don't go smaller than minimumSize
            win_w = max(win_w, 480)
            win_h = max(win_h, 320)
            # Center on screen
            x = avail.x() + (avail.width() - win_w) // 2
            y = avail.y() + (avail.height() - win_h) // 2
            self._editor.setGeometry(x, y, win_w, win_h)
        self._editor.show()

    def _on_editor_closed(self):
        self._editor = None

    def _open_image(self):
        path, _ = QFileDialog.getOpenFileName(
            None, "Open Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;All Files (*)",
        )
        if path:
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                self._open_editor(pixmap)

    def _open_recent(self, path: str):
        from pathlib import Path
        if Path(path).exists():
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                self._open_editor(pixmap)

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
        for pin in self._pin_windows:
            pin.close()
        if self._editor:
            self._editor.close()
        self._app.quit()
