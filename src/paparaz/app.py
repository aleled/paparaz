"""Main application controller - orchestrates tray, hotkey, capture, and editor."""

from PySide6.QtWidgets import QApplication, QFileDialog
from PySide6.QtCore import QObject, QPoint, QRect, QTimer
from PySide6.QtGui import QPixmap

from paparaz.core.capture import capture_all_screens, capture_region
from paparaz.core.settings import SettingsManager
from paparaz.ui.tray import TrayIcon
from paparaz.ui.overlay import RegionSelector
from paparaz.ui.editor import EditorWindow
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

        # Hotkey listener
        self._hotkey_listener = GlobalHotkeyListener()
        self._capture_hk_id = self._hotkey_listener.register(
            self._settings.settings.hotkeys.capture
        )

        # Connect signals
        self._tray.capture_requested.connect(self._start_capture)
        self._tray.open_image_requested.connect(self._open_image)
        self._tray.settings_requested.connect(self._show_settings)
        self._tray.quit_requested.connect(self._quit)
        self._hotkey_listener.hotkey_pressed.connect(self._on_hotkey)

    def start(self):
        self._tray.show()
        self._tray.show_message("PapaRaZ", "Ready! Press PrintScreen to capture.")
        self._hotkey_listener.start()

    def _on_hotkey(self, hk_id: int):
        if hk_id == self._capture_hk_id:
            # Small delay to let the hotkey release
            QTimer.singleShot(150, self._start_capture)

    def _start_capture(self):
        # Hide editor if open
        if self._editor:
            self._editor.hide()

        # Capture all screens
        self._full_capture = capture_all_screens()

        # Show region selector overlay
        vx, vy, vw, vh = get_virtual_screen_geometry()
        self._overlay = RegionSelector(
            self._full_capture,
            screen_offset=QPoint(vx, vy),
        )
        self._overlay.region_selected.connect(self._on_region_selected)
        self._overlay.selection_cancelled.connect(self._on_selection_cancelled)
        self._overlay.showFullScreen()

    def _on_region_selected(self, rect: QRect):
        if self._overlay:
            self._overlay.close()
            self._overlay = None

        if self._full_capture:
            # Adjust rect relative to virtual screen origin
            vx, vy, _, _ = get_virtual_screen_geometry()
            cropped = capture_region(
                self._full_capture,
                rect.x() - vx, rect.y() - vy,
                rect.width(), rect.height(),
            )
            self._open_editor(cropped)

    def _on_selection_cancelled(self):
        if self._overlay:
            self._overlay.close()
            self._overlay = None

    def _open_editor(self, pixmap: QPixmap):
        self._editor = EditorWindow(pixmap)
        self._editor.closed.connect(self._on_editor_closed)
        self._editor.showMaximized()

    def _on_editor_closed(self):
        self._editor = None

    def _open_image(self):
        path, _ = QFileDialog.getOpenFileName(
            None, "Open Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*)",
        )
        if path:
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                self._open_editor(pixmap)

    def _show_settings(self):
        # TODO: Settings dialog (Phase 5)
        pass

    def _quit(self):
        self._hotkey_listener.stop()
        if self._editor:
            self._editor.close()
        self._app.quit()
