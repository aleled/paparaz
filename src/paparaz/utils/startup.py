"""Windows auto-start on login via HKCU Run registry key."""

import sys
import winreg

_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_APP_NAME = "PapaRaZ"


def _exe_path() -> str:
    """Return the path that should be registered for auto-start.

    When running from a PyInstaller bundle, sys.executable is the .exe.
    When running from source, we register the Python interpreter + module flag.
    """
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    return f'"{sys.executable}" -m paparaz'


def set_start_on_login(enabled: bool) -> None:
    """Add or remove PapaRaZ from the Windows startup registry key."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            _REG_KEY,
            0,
            winreg.KEY_SET_VALUE,
        )
        with key:
            if enabled:
                winreg.SetValueEx(key, _APP_NAME, 0, winreg.REG_SZ, _exe_path())
            else:
                try:
                    winreg.DeleteValue(key, _APP_NAME)
                except FileNotFoundError:
                    pass  # already absent
    except OSError:
        pass  # silently ignore registry errors (e.g. sandboxed environments)


def get_start_on_login() -> bool:
    """Return True if PapaRaZ is registered to start on login."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            _REG_KEY,
            0,
            winreg.KEY_READ,
        )
        with key:
            winreg.QueryValueEx(key, _APP_NAME)
            return True
    except (OSError, FileNotFoundError):
        return False
