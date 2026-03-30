"""Update checker — compares current version against latest GitHub release.

Runs in a background thread so it never blocks the UI.
Call check_for_updates(parent_widget) once on startup.
"""

from __future__ import annotations

import threading
import urllib.request
import urllib.error
import json
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QMessageBox, QPushButton

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

__version__ = "0.8.0"

_GITHUB_API_URL = (
    "https://api.github.com/repos/aleled/paparaz/releases/latest"
)
_RELEASES_PAGE = "https://github.com/aleled/paparaz/releases"


def _parse_version(tag: str) -> tuple[int, ...]:
    """'v0.8.0' or '0.8.0' → (0, 8, 0)."""
    tag = tag.lstrip("v")
    try:
        return tuple(int(x) for x in tag.split("."))
    except ValueError:
        return (0,)


class _UpdateBridge(QObject):
    update_available = Signal(str, str)   # (latest_version, release_url)
    up_to_date       = Signal()
    check_failed     = Signal(str)        # error message


def check_for_updates(parent: "QWidget | None" = None, silent: bool = True) -> None:
    """Check for a newer release in a background thread.

    If a newer version is found, shows a non-blocking notification dialog.
    When *silent* is True (default), errors and "already up to date" are ignored.
    """
    bridge = _UpdateBridge(parent=parent)

    def _on_update_available(latest: str, url: str):
        _show_update_dialog(parent, latest, url)
        bridge.deleteLater()

    bridge.update_available.connect(_on_update_available)

    def _worker():
        try:
            req = urllib.request.Request(
                _GITHUB_API_URL,
                headers={"User-Agent": f"PapaRaZ/{__version__}"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())

            tag = data.get("tag_name", "")
            html_url = data.get("html_url", _RELEASES_PAGE)

            if not tag:
                return

            latest = _parse_version(tag)
            current = _parse_version(__version__)

            if latest > current:
                bridge.update_available.emit(tag.lstrip("v"), html_url)

        except Exception:
            pass  # network errors are silently ignored

    t = threading.Thread(target=_worker, daemon=True)
    # Keep bridge alive until the thread finishes (or dialog fires)
    _check_for_updates_refs.append((t, bridge))
    t.start()


# Keep references alive so GC doesn't collect them before the thread finishes
_check_for_updates_refs: list = []


def check_for_updates_manual(parent: "QWidget | None" = None) -> None:
    """User-triggered update check — always shows a result (update, up-to-date, or error)."""
    bridge = _UpdateBridge(parent=parent)

    def on_update(latest: str, url: str):
        _show_update_dialog(parent, latest, url)
        bridge.deleteLater()

    def on_up_to_date():
        msg = QMessageBox(parent)
        msg.setWindowTitle("Up to Date")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText(f"PapaRaZ v{__version__} is the latest version.")
        msg.setStyleSheet(
            "QMessageBox { background: #1e1e2e; color: #ccc; } "
            "QLabel { color: #ccc; } "
            "QPushButton { background: #740096; color: #fff; border: none; "
            "              padding: 5px 14px; border-radius: 3px; } "
        )
        msg.exec()
        bridge.deleteLater()

    def on_failed(err: str):
        msg = QMessageBox(parent)
        msg.setWindowTitle("Update Check Failed")
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setText("Could not check for updates.")
        msg.setInformativeText(err)
        msg.setStyleSheet(
            "QMessageBox { background: #1e1e2e; color: #ccc; } "
            "QLabel { color: #ccc; } "
            "QPushButton { background: #740096; color: #fff; border: none; "
            "              padding: 5px 14px; border-radius: 3px; } "
        )
        msg.exec()
        bridge.deleteLater()

    bridge.update_available.connect(on_update)
    bridge.up_to_date.connect(on_up_to_date)
    bridge.check_failed.connect(on_failed)

    def _worker():
        try:
            req = urllib.request.Request(
                _GITHUB_API_URL,
                headers={"User-Agent": f"PapaRaZ/{__version__}"},
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read())
            tag = data.get("tag_name", "")
            html_url = data.get("html_url", _RELEASES_PAGE)
            if not tag:
                bridge.check_failed.emit("No release tag found in GitHub response.")
                return
            latest = _parse_version(tag)
            current = _parse_version(__version__)
            if latest > current:
                bridge.update_available.emit(tag.lstrip("v"), html_url)
            else:
                bridge.up_to_date.emit()
        except Exception as exc:
            bridge.check_failed.emit(str(exc))

    t = threading.Thread(target=_worker, daemon=True)
    _check_for_updates_refs.append((t, bridge))
    t.start()


def _show_update_dialog(parent: "QWidget | None", latest: str, url: str):
    msg = QMessageBox(parent)
    msg.setWindowTitle("Update Available")
    msg.setIcon(QMessageBox.Icon.Information)
    msg.setText(f"PapaRaZ <b>v{latest}</b> is available.")
    msg.setInformativeText(
        f"You are running v{__version__}.<br>"
        "Download the new version from GitHub."
    )
    msg.setStyleSheet(
        "QMessageBox { background: #1e1e2e; color: #ccc; } "
        "QLabel { color: #ccc; } "
        "QPushButton { background: #740096; color: #fff; border: none; "
        "              padding: 5px 14px; border-radius: 3px; } "
        "QPushButton:hover { background: #9300bb; } "
    )
    download_btn = msg.addButton("Download", QMessageBox.ButtonRole.AcceptRole)
    msg.addButton("Later", QMessageBox.ButtonRole.RejectRole)
    msg.exec()
    if msg.clickedButton() == download_btn:
        import subprocess
        subprocess.Popen(["start", "", url], shell=True)
