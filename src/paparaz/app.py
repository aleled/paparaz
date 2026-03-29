"""Main application controller - orchestrates tray, hotkey, capture, editor, pin, settings."""

from PySide6.QtWidgets import QApplication, QFileDialog
from PySide6.QtCore import QObject, QPoint, QRect, QTimer
from PySide6.QtGui import QPixmap

from paparaz.core.capture import capture_all_screens, capture_region
from paparaz.core.settings import SettingsManager
from paparaz.ui.tray import TrayIcon
from paparaz.ui.overlay import RegionSelector
from paparaz.ui.editor import EditorWindow
from paparaz.ui.pin_window import PinWindow
from paparaz.ui.settings_dialog import SettingsDialog
from paparaz.utils.hotkey import GlobalHotkeyListener
from paparaz.utils.monitors import get_virtual_screen_geometry


class PapaRazApp(QObject):
    """Main application controller."""

    def __init__(self, app: QApplication):
        super().__init__()
        self._app = app
        self._settings = SettingsManager()

        # UI components
        self._tray = TrayIcon()
        self._overlay = None
        self._editor = None
        self._full_capture = None
        self._pin_windows: list[PinWindow] = []

        # Hotkey listener
        self._hotkey_listener = GlobalHotkeyListener()
        self._capture_hk_id = self._hotkey_listener.register(
            self._settings.settings.hotkeys.capture
        )

        # Connect signals
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
        """Capture after a delay (countdown)."""
        self._tray.show_message("PapaRaZ", f"Capturing in {seconds} seconds...")
        QTimer.singleShot(seconds * 1000, self._start_capture)

    def _start_capture(self):
        if self._editor:
            self._editor.hide()

        self._full_capture = capture_all_screens()

        self._overlay = RegionSelector(self._full_capture)
        self._overlay.region_selected.connect(self._on_region_selected)
        self._overlay.selection_cancelled.connect(self._on_selection_cancelled)
        self._overlay.showFullScreen()

    def _on_region_selected(self, rect: QRect):
        if self._overlay:
            self._overlay.close()
            self._overlay = None

        if self._full_capture:
            # The overlay works in Qt logical pixels. The capture is in physical pixels.
            # Compute the virtual desktop in both coordinate systems to find the scale factor.
            virtual_rect = QRect()
            for screen in QApplication.screens():
                virtual_rect = virtual_rect.united(screen.geometry())

            logical_w = virtual_rect.width()
            logical_h = virtual_rect.height()
            phys_w = self._full_capture.width()
            phys_h = self._full_capture.height()

            # Scale selection from logical to physical pixel coords
            sx = phys_w / logical_w if logical_w > 0 else 1.0
            sy = phys_h / logical_h if logical_h > 0 else 1.0

            px = int((rect.x() - virtual_rect.x()) * sx)
            py = int((rect.y() - virtual_rect.y()) * sy)
            pw = int(rect.width() * sx)
            ph = int(rect.height() * sy)

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
        self._editor.showMaximized()

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
        """Create an always-on-top floating pin with resume-edit capability."""
        pin = PinWindow(rendered, background=background, elements=elements)
        pin.closed.connect(lambda: self._pin_windows.remove(pin) if pin in self._pin_windows else None)
        pin.edit_requested.connect(self._resume_editing_pin)
        pin.show()
        self._pin_windows.append(pin)

    def _resume_editing_pin(self, pin_window):
        """Resume editing a pinned screenshot in a new editor."""
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
