"""Update checker with in-app downloader.

Flow:
  1. Background thread hits GitHub API → finds newer version
  2. Extracts direct installer download URL from release assets
  3. Opens UpdateDownloadDialog — progress bar, background download, auto-launch
  4. On completion user clicks "Install Now" → installer launches, app closes

Call check_for_updates(parent) once on startup (silent=True).
Call check_for_updates_manual(parent) from menu / settings for explicit check.
"""

from __future__ import annotations

import os
import sys
import json
import tempfile
import threading
import urllib.request
import urllib.error
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QObject, Signal, QThread
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QMessageBox, QSizePolicy,
)
from PySide6.QtGui import QFont

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

__version__ = "0.9.7"

_GITHUB_API  = "https://api.github.com/repos/aleled/paparaz/releases/latest"
_RELEASES_PAGE = "https://github.com/aleled/paparaz/releases/latest"

_DIALOG_QSS = """
QDialog {
    background: #1a1a2e;
    color: #ccc;
    border: 1px solid #3a3a4e;
    border-radius: 6px;
}
QLabel { color: #ccc; background: transparent; }
QLabel#title  { color: #fff; font-size: 14px; font-weight: bold; }
QLabel#sub    { color: #aaa; font-size: 11px; }
QLabel#status { color: #888; font-size: 10px; }
QProgressBar {
    border: 1px solid #3a3a4e;
    border-radius: 4px;
    background: #2a2a3e;
    height: 14px;
    text-align: center;
    color: #fff;
    font-size: 10px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #740096, stop:1 #9e2ac0);
    border-radius: 3px;
}
QPushButton {
    background: #740096; color: #fff;
    border: none; border-radius: 4px;
    padding: 7px 20px; font-size: 12px;
    min-width: 100px;
}
QPushButton:hover   { background: #9300bb; }
QPushButton:disabled { background: #3a3a4e; color: #666; }
QPushButton#cancel  { background: #2a2a3e; color: #aaa; border: 1px solid #3a3a4e; }
QPushButton#cancel:hover { background: #3a3a4e; color: #fff; }
"""


# ── Download worker ───────────────────────────────────────────────────────────

class _DownloadWorker(QObject):
    """Runs in a QThread — downloads a file and reports progress."""
    progress    = Signal(int, int)   # (bytes_done, total_bytes)
    finished    = Signal(str)        # local file path
    error       = Signal(str)        # error message

    def __init__(self, url: str, dest: str):
        super().__init__()
        self._url  = url
        self._dest = dest
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            req = urllib.request.Request(
                self._url,
                headers={"User-Agent": f"PapaRaZ/{__version__}"},
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                done  = 0
                chunk = 65536  # 64 KB chunks
                with open(self._dest, "wb") as f:
                    while True:
                        if self._cancelled:
                            return
                        buf = resp.read(chunk)
                        if not buf:
                            break
                        f.write(buf)
                        done += len(buf)
                        self.progress.emit(done, total)
            self.finished.emit(self._dest)
        except Exception as exc:
            self.error.emit(str(exc))


# ── Download dialog ───────────────────────────────────────────────────────────

class UpdateDownloadDialog(QDialog):
    """Shows download progress and launches the installer on completion."""

    def __init__(self, latest: str, download_url: str, parent: "QWidget | None" = None):
        super().__init__(parent)
        self.setWindowTitle("Update Available")
        self.setFixedWidth(420)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(_DIALOG_QSS)

        self._latest       = latest
        self._download_url = download_url
        self._dest_path    = None
        self._thread       = None
        self._worker       = None

        # ── Layout ────────────────────────────────────────────────────────────
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(10)

        title = QLabel(f"PapaRaZ v{latest} is available")
        title.setObjectName("title")
        layout.addWidget(title)

        sub = QLabel(f"You are running v{__version__}.  A new version is ready to download.")
        sub.setObjectName("sub")
        sub.setWordWrap(True)
        layout.addWidget(sub)

        layout.addSpacing(4)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFormat("Preparing download…")
        layout.addWidget(self._progress)

        self._status = QLabel("Starting…")
        self._status.setObjectName("status")
        layout.addWidget(self._status)

        layout.addSpacing(8)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._install_btn = QPushButton("Install Now")
        self._install_btn.setEnabled(False)
        self._install_btn.clicked.connect(self._launch_installer)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setObjectName("cancel")
        self._cancel_btn.clicked.connect(self._on_cancel)

        btn_row.addStretch()
        btn_row.addWidget(self._cancel_btn)
        btn_row.addWidget(self._install_btn)
        layout.addLayout(btn_row)

        # Start download immediately
        self._start_download()

    # ── Download ──────────────────────────────────────────────────────────────

    def _start_download(self):
        suffix = f"PapaRaZ_Setup_{self._latest}.exe"
        tmp_dir = tempfile.gettempdir()
        self._dest_path = os.path.join(tmp_dir, suffix)

        self._thread = QThread(self)
        self._worker = _DownloadWorker(self._download_url, self._dest_path)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)

        self._thread.start()

    def _on_progress(self, done: int, total: int):
        if total > 0:
            pct = int(done / total * 100)
            self._progress.setValue(pct)
            self._progress.setFormat(f"{pct}%")
            done_mb  = done  / 1_048_576
            total_mb = total / 1_048_576
            self._status.setText(f"{done_mb:.1f} MB / {total_mb:.1f} MB")
        else:
            done_mb = done / 1_048_576
            self._progress.setRange(0, 0)   # indeterminate
            self._status.setText(f"{done_mb:.1f} MB downloaded…")

    def _on_finished(self, path: str):
        self._progress.setRange(0, 100)
        self._progress.setValue(100)
        self._progress.setFormat("Download complete!")
        self._status.setText("Ready to install. Click Install Now to begin.")
        self._install_btn.setEnabled(True)
        self._cancel_btn.setText("Later")

    def _on_error(self, msg: str):
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFormat("Download failed")
        self._status.setText(f"Error: {msg}")
        self._cancel_btn.setText("Close")
        # Offer browser fallback
        self._install_btn.setText("Open Browser")
        self._install_btn.setEnabled(True)
        self._install_btn.clicked.disconnect()
        self._install_btn.clicked.connect(self._open_browser_fallback)

    def _on_cancel(self):
        if self._worker:
            self._worker.cancel()
        if self._thread:
            self._thread.quit()
        self.reject()

    # ── Install ───────────────────────────────────────────────────────────────

    def _launch_installer(self):
        if not self._dest_path or not os.path.exists(self._dest_path):
            self._on_error("Installer file not found.")
            return
        import subprocess
        # Launch installer detached — it will handle closing the app
        if sys.platform == "win32":
            subprocess.Popen(
                [self._dest_path],
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                close_fds=True,
            )
        else:
            subprocess.Popen([self._dest_path])
        # Close the app so the installer can replace the exe
        self.accept()
        from PySide6.QtWidgets import QApplication
        QApplication.instance().quit()

    def _open_browser_fallback(self):
        import subprocess
        subprocess.Popen(["start", "", _RELEASES_PAGE], shell=True)
        self.reject()

    def closeEvent(self, event):
        if self._worker:
            self._worker.cancel()
        if self._thread:
            self._thread.quit()
        super().closeEvent(event)


# ── API check helpers ─────────────────────────────────────────────────────────

class _UpdateBridge(QObject):
    update_available = Signal(str, str)   # (latest_version, download_url)
    up_to_date       = Signal()
    check_failed     = Signal(str)


def _get_installer_url(assets: list) -> str:
    """Find the Setup .exe asset URL, fallback to releases page."""
    for asset in assets:
        name = asset.get("name", "")
        if name.lower().startswith("paparaz_setup") and name.lower().endswith(".exe"):
            return asset.get("browser_download_url", _RELEASES_PAGE)
    return _RELEASES_PAGE


def _fetch_latest() -> tuple[str, str]:
    """Returns (tag, installer_url). Raises on error."""
    req = urllib.request.Request(
        _GITHUB_API,
        headers={"User-Agent": f"PapaRaZ/{__version__}"},
    )
    with urllib.request.urlopen(req, timeout=8) as resp:
        data = json.loads(resp.read())
    tag           = data.get("tag_name", "")
    assets        = data.get("assets", [])
    installer_url = _get_installer_url(assets)
    return tag, installer_url


def _parse_version(tag: str) -> tuple[int, ...]:
    tag = tag.lstrip("v")
    try:
        return tuple(int(x) for x in tag.split("."))
    except ValueError:
        return (0,)


# ── Public API ────────────────────────────────────────────────────────────────

# Keep references alive so GC doesn't collect them before threads finish
_refs: list = []


def check_for_updates(parent: "QWidget | None" = None, silent: bool = True) -> None:
    """Startup check — silent on errors and when already up to date."""
    bridge = _UpdateBridge(parent)

    def _on_update(latest: str, url: str):
        _show_download_dialog(parent, latest, url)
        bridge.deleteLater()

    bridge.update_available.connect(_on_update)

    def _worker():
        try:
            tag, url = _fetch_latest()
            if tag and _parse_version(tag) > _parse_version(__version__):
                bridge.update_available.emit(tag.lstrip("v"), url)
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                pass  # silently ignore all errors on startup check
        except Exception:
            pass

    t = threading.Thread(target=_worker, daemon=True)
    _refs.append((t, bridge))
    t.start()


def check_for_updates_manual(parent: "QWidget | None" = None) -> None:
    """User-triggered check — always shows a result."""
    bridge = _UpdateBridge(parent)

    def _on_update(latest: str, url: str):
        _show_download_dialog(parent, latest, url)
        bridge.deleteLater()

    def _on_up_to_date():
        _info_box(parent, "Up to Date",
                  f"PapaRaZ v{__version__} is the latest version.",
                  QMessageBox.Icon.Information)
        bridge.deleteLater()

    def _on_failed(err: str):
        no_release = "404" in err or "No releases" in err
        _info_box(parent,
                  "No Releases Yet" if no_release else "Update Check Failed",
                  "You're on the latest build." if no_release else "Could not check for updates.",
                  QMessageBox.Icon.Information if no_release else QMessageBox.Icon.Warning,
                  detail=err)
        bridge.deleteLater()

    bridge.update_available.connect(_on_update)
    bridge.up_to_date.connect(_on_up_to_date)
    bridge.check_failed.connect(_on_failed)

    def _worker():
        try:
            tag, url = _fetch_latest()
            if not tag:
                bridge.check_failed.emit("No release tag found in GitHub response.")
                return
            if _parse_version(tag) > _parse_version(__version__):
                bridge.update_available.emit(tag.lstrip("v"), url)
            else:
                bridge.up_to_date.emit()
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                bridge.check_failed.emit("No releases have been published yet.")
            else:
                bridge.check_failed.emit(f"HTTP {exc.code}: {exc.reason}")
        except Exception as exc:
            bridge.check_failed.emit(str(exc))

    t = threading.Thread(target=_worker, daemon=True)
    _refs.append((t, bridge))
    t.start()


def _show_download_dialog(parent, latest: str, url: str):
    dlg = UpdateDownloadDialog(latest, url, parent)
    dlg.exec()


def _info_box(parent, title: str, text: str, icon, detail: str = ""):
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setIcon(icon)
    msg.setText(text)
    if detail:
        msg.setInformativeText(detail)
    msg.setStyleSheet(
        "QMessageBox{background:#1e1e2e;color:#ccc;}"
        "QLabel{color:#ccc;}"
        "QPushButton{background:#740096;color:#fff;border:none;"
        "            padding:5px 14px;border-radius:3px;}"
        "QPushButton:hover{background:#9300bb;}"
    )
    msg.exec()
