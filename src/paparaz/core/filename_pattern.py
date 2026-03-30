"""Filename pattern engine for PapaRaZ.

Token syntax: {token} or {token:width}

Supported tokens:
  Date/Time : {yyyy} {yy} {MM} {dd} {HH} {mm} {ss} {unix}
  Counter   : {n}  {n:4}  (width optional, default 4)
  Random    : {r}  {r:8}  (width optional, default 8)
  Context   : {title} {app} {host} {user}
  Image     : {w} {h}  (pixel dimensions — provided at resolve time)

Usage:
    from paparaz.core.filename_pattern import resolve, preview, TOKENS

    name = resolve("{yyyy}-{MM}-{dd}_{HH}-{mm}-{ss}", counter=1)
    sample = preview("{yyyy}-{MM}-{dd}_{HH}-{mm}-{ss}")
"""

from __future__ import annotations

import re
import os
import random
import string
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# ── token catalogue (used by UI picker) ──────────────────────────────────────

TOKENS: list[dict] = [
    # category, token text, description
    {"cat": "Date",    "token": "{yyyy}",  "desc": "4-digit year"},
    {"cat": "Date",    "token": "{yy}",    "desc": "2-digit year"},
    {"cat": "Date",    "token": "{MM}",    "desc": "Month (01-12)"},
    {"cat": "Date",    "token": "{dd}",    "desc": "Day (01-31)"},
    {"cat": "Time",    "token": "{HH}",    "desc": "Hour 24h (00-23)"},
    {"cat": "Time",    "token": "{mm}",    "desc": "Minute (00-59)"},
    {"cat": "Time",    "token": "{ss}",    "desc": "Second (00-59)"},
    {"cat": "Time",    "token": "{unix}",  "desc": "Unix timestamp"},
    {"cat": "Counter", "token": "{n}",     "desc": "Auto counter (4 digits)"},
    {"cat": "Counter", "token": "{n:6}",   "desc": "Auto counter (6 digits)"},
    {"cat": "Random",  "token": "{r}",     "desc": "8 random chars"},
    {"cat": "Context", "token": "{title}", "desc": "Active window title"},
    {"cat": "Context", "token": "{app}",   "desc": "Active app name"},
    {"cat": "Context", "token": "{host}",  "desc": "Computer name"},
    {"cat": "Context", "token": "{user}",  "desc": "Windows username"},
    {"cat": "Image",   "token": "{w}",     "desc": "Image width (px)"},
    {"cat": "Image",   "token": "{h}",     "desc": "Image height (px)"},
]

PRESETS: list[dict] = [
    {"label": "Date-Time",          "pattern": "{yyyy}-{MM}-{dd}_{HH}-{mm}-{ss}"},
    {"label": "Date-Time + App",    "pattern": "{app}_{yyyy}-{MM}-{dd}_{HH}-{mm}-{ss}"},
    {"label": "Date-Time + Title",  "pattern": "{title}_{yyyy}-{MM}-{dd}_{HH}-{mm}-{ss}"},
    {"label": "Counter",            "pattern": "Screenshot_{n:4}"},
    {"label": "Unix timestamp",     "pattern": "{unix}"},
    {"label": "Custom",             "pattern": ""},   # placeholder for user input
]

_FORBIDDEN = re.compile(r'[\\/:*?"<>|]')
_TOKEN_RE  = re.compile(r'\{(\w+)(?::(\d+))?\}')


def _sanitize(text: str) -> str:
    """Strip characters illegal in Windows filenames."""
    return _FORBIDDEN.sub("_", text).strip().strip("._") or "untitled"


def resolve(
    pattern: str,
    counter: int = 1,
    title: str = "",
    app: str = "",
    width: int = 0,
    height: int = 0,
    dt: Optional[datetime] = None,
) -> str:
    """Expand *pattern* into a concrete filename (no extension, no directory).

    Args:
        pattern : The pattern string, e.g. ``"{yyyy}-{MM}-{dd}_{HH}-{mm}-{ss}"``.
        counter : Current session counter value (persisted in settings).
        title   : Active window title at capture time.
        app     : Active process name at capture time (no .exe).
        width   : Canvas width in pixels (for {w}).
        height  : Canvas height in pixels (for {h}).
        dt      : datetime to use; defaults to now.
    """
    dt = dt or datetime.now()

    def _replace(m: re.Match) -> str:
        tok = m.group(1).lower()
        width_spec = int(m.group(2)) if m.group(2) else None

        if tok == "yyyy":   return dt.strftime("%Y")
        if tok == "yy":     return dt.strftime("%y")
        if tok == "mm":     return dt.strftime("%m")      # month
        if tok == "dd":     return dt.strftime("%d")
        if tok == "hh":     return dt.strftime("%H")
        if tok == "ss":     return dt.strftime("%S")
        if tok == "unix":   return str(int(time.time()))
        if tok == "n":
            w = width_spec or 4
            return str(counter).zfill(w)
        if tok == "r":
            w = width_spec or 8
            return "".join(random.choices(string.ascii_letters + string.digits, k=w))
        if tok == "title":
            return _sanitize(title)[:60] if title else "untitled"
        if tok == "app":
            return _sanitize(app)[:30] if app else "paparaz"
        if tok == "host":
            return _sanitize(os.environ.get("COMPUTERNAME", "pc"))
        if tok == "user":
            return _sanitize(os.environ.get("USERNAME", "user"))
        if tok == "w":      return str(width)
        if tok == "h":      return str(height)
        return m.group(0)   # unknown token — leave as-is

    # Special: {mm} is minute inside time context but month in date context.
    # Resolution: we match case-sensitively for MM=month vs mm=minute.
    # The _replace func above lowercases, so handle MM vs mm before lowercasing.
    def _replace_cs(m: re.Match) -> str:
        tok_raw = m.group(1)   # preserve original case for MM vs mm
        width_spec = int(m.group(2)) if m.group(2) else None
        tok = tok_raw.lower()

        if tok_raw == "MM": return dt.strftime("%m")     # month, uppercase MM
        if tok_raw == "mm": return dt.strftime("%M")     # minute, lowercase mm
        if tok == "yyyy":   return dt.strftime("%Y")
        if tok == "yy":     return dt.strftime("%y")
        if tok == "dd":     return dt.strftime("%d")
        if tok == "hh":     return dt.strftime("%H")
        if tok == "ss":     return dt.strftime("%S")
        if tok == "unix":   return str(int(time.time()))
        if tok == "n":
            w = width_spec or 4
            return str(counter).zfill(w)
        if tok == "r":
            w = width_spec or 8
            return "".join(random.choices(string.ascii_letters + string.digits, k=w))
        if tok == "title":
            return _sanitize(title)[:60] if title else "untitled"
        if tok == "app":
            return _sanitize(app)[:30] if app else "paparaz"
        if tok == "host":
            return _sanitize(os.environ.get("COMPUTERNAME", "pc"))
        if tok == "user":
            return _sanitize(os.environ.get("USERNAME", "user"))
        if tok == "w":      return str(width)
        if tok == "h":      return str(height)
        return m.group(0)

    result = _TOKEN_RE.sub(_replace_cs, pattern)
    # Final sanitize: strip any remaining forbidden chars from the full name
    result = _FORBIDDEN.sub("_", result).strip()
    return result or "capture"


def preview(pattern: str) -> str:
    """Return a sample expansion using current time and placeholder values."""
    return resolve(
        pattern,
        counter=1,
        title="Notepad",
        app="notepad",
        width=1920,
        height=1080,
    )


def build_save_path(
    pattern: str,
    save_dir: str,
    subfolder_pattern: str = "",
    ext: str = "png",
    counter: int = 1,
    title: str = "",
    app: str = "",
    width: int = 0,
    height: int = 0,
) -> Path:
    """Compose the full save path from pattern + directory + optional subfolder."""
    name = resolve(pattern, counter=counter, title=title, app=app,
                   width=width, height=height)
    base = Path(save_dir) if save_dir else Path.home() / "Pictures" / "PapaRaZ"

    if subfolder_pattern:
        sub = resolve(subfolder_pattern, counter=counter, title=title, app=app)
        # Sanitize subfolder components individually
        parts = re.split(r'[/\\]', sub)
        parts = [_FORBIDDEN.sub("_", p).strip() for p in parts if p.strip()]
        for p in parts:
            base = base / p

    base.mkdir(parents=True, exist_ok=True)

    # Avoid collisions: append (2), (3) etc if file already exists
    candidate = base / f"{name}.{ext}"
    if candidate.exists():
        i = 2
        while (base / f"{name} ({i}).{ext}").exists():
            i += 1
        candidate = base / f"{name} ({i}).{ext}"

    return candidate
