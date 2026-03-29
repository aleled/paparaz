"""Global hotkey registration using Win32 API."""

import ctypes
from ctypes import wintypes
from PySide6.QtCore import QThread, Signal

WM_HOTKEY = 0x0312
MOD_NONE = 0x0000
MOD_ALT = 0x0001
MOD_CTRL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008

VK_MAP = {
    "PrintScreen": 0x2C,
    "F1": 0x70, "F2": 0x71, "F3": 0x72, "F4": 0x73,
    "F5": 0x74, "F6": 0x75, "F7": 0x76, "F8": 0x77,
    "F9": 0x78, "F10": 0x79, "F11": 0x7A, "F12": 0x7B,
}

MOD_MAP = {
    "Ctrl": MOD_CTRL,
    "Alt": MOD_ALT,
    "Shift": MOD_SHIFT,
    "Win": MOD_WIN,
}


def parse_hotkey(hotkey_str: str) -> tuple[int, int]:
    """Parse a hotkey string like 'Ctrl+Shift+PrintScreen' into (modifiers, vk)."""
    parts = hotkey_str.split("+")
    modifiers = MOD_NONE
    vk = 0

    for part in parts:
        part = part.strip()
        if part in MOD_MAP:
            modifiers |= MOD_MAP[part]
        elif part in VK_MAP:
            vk = VK_MAP[part]
        elif len(part) == 1:
            vk = ord(part.upper())

    return modifiers, vk


class GlobalHotkeyListener(QThread):
    """Thread that listens for global hotkey events."""

    hotkey_pressed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hotkeys: dict[int, tuple[int, int]] = {}
        self._next_id = 1
        self._running = True

    def register(self, hotkey_str: str) -> int:
        """Register a hotkey. Returns the hotkey ID."""
        modifiers, vk = parse_hotkey(hotkey_str)
        hk_id = self._next_id
        self._next_id += 1
        self._hotkeys[hk_id] = (modifiers, vk)
        return hk_id

    def run(self):
        # Store native thread ID for stop()
        self._thread_id = ctypes.windll.kernel32.GetCurrentThreadId()

        # Register all hotkeys on this thread
        for hk_id, (mods, vk) in self._hotkeys.items():
            ctypes.windll.user32.RegisterHotKey(None, hk_id, mods, vk)

        msg = wintypes.MSG()
        while self._running:
            ret = ctypes.windll.user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if ret == 0 or ret == -1:
                break
            if msg.message == WM_HOTKEY:
                self.hotkey_pressed.emit(msg.wParam)

        # Unregister hotkeys
        for hk_id in self._hotkeys:
            ctypes.windll.user32.UnregisterHotKey(None, hk_id)

    def stop(self):
        self._running = False
        # Post WM_QUIT to unblock GetMessage using native thread ID
        if hasattr(self, '_thread_id') and self._thread_id:
            ctypes.windll.user32.PostThreadMessageW(
                self._thread_id, 0x0012, 0, 0  # WM_QUIT
            )
        self.wait(2000)
