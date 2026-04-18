<div align="center">

<img src="assets/banner.png" alt="PapaRaZ Banner" width="100%">

<br/>

### 🌐 [**aleled.github.io/paparaz**](https://aleled.github.io/paparaz/) — Download &amp; Feature Page

<br/>

[![Version](https://img.shields.io/badge/version-0.9.9-740096?style=flat-square)](https://github.com/aleled/paparaz/releases/latest)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%2B-0078D4?style=flat-square&logo=windows&logoColor=white)](https://github.com/aleled/paparaz/releases/latest)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![PySide6](https://img.shields.io/badge/PySide6-Qt6-41CD52?style=flat-square&logo=qt&logoColor=white)](https://doc.qt.io/qtforpython/)
[![License](https://img.shields.io/badge/license-MIT-22c55e?style=flat-square)](LICENSE)

**Capture. Annotate. Share. — All in one keystroke.**

[⬇️ Download Installer](https://github.com/aleled/paparaz/releases/latest) &nbsp;·&nbsp;
[📋 Changelog](docs/CHANGELOG.md) &nbsp;·&nbsp;
[🐛 Report Bug](https://github.com/aleled/paparaz/issues) &nbsp;·&nbsp;
[💡 Request Feature](https://github.com/aleled/paparaz/issues)

</div>

---

## ✨ What is PapaRaZ?

PapaRaZ is a **lightweight, object-based screen capture and annotation tool** for Windows, built from scratch in Python + PySide6.

Every annotation is a **discrete, selectable object** — not a flat paint layer. Click anything to re-select it, move it, resize it, rotate it or change its properties long after placing it.

---

## 🚀 Features at a Glance

| | Feature | Details |
|---|---|---|
| 📸 | **Instant Capture** | PrintScreen global hotkey — capture appears in under 100ms |
| 🖥️ | **Multi-monitor** | Win32 DPI-aware capture across all screens |
| 🎨 | **20 Annotation Tools** | Pen, Brush, Arrow, Line, Rect, Ellipse, Text, Number, Stamp, Eraser, Blur, Fill, Crop, Slice, Measure, Curved Arrow, Eyedropper, Magnifier, Highlight, Select |
| 🔖 | **32 Stamps** | Approved, Rejected, Priority, Bug, WIP, DRAFT, TODO, DONE, FIX, NEW and more (inc. transparent-bg variants) |
| 💾 | **Element Serialization** | Full JSON roundtrip — save and restore all annotations |
| 🔤 | **Windows OCR** | Select strokes → right-click → convert to editable text |
| ✂️ | **Crop & Slice** | Non-destructive crop or export sub-regions |
| 🌫️ | **Blur / Redact** | Pixelate sensitive regions |
| 🎯 | **Multi-select** | Rubber-band or Shift+click — group move, group delete, group OCR |
| 🎛️ | **Floating Properties Panel** | Element preview, drag freely, pin open or auto-hide on deselect |
| 🖥️ | **HiDPI / Retina-sharp** | Physical-pixel capture on 125–200% displays — no downscale blur |
| 💾 | **4 Export Formats** | PNG, JPG, SVG (vector), Clipboard — full-resolution output |
| 🔄 | **200-step Undo/Redo** | Full history — Ctrl+Z / Ctrl+Y |
| 🔔 | **System Tray** | Runs silently in background, auto-start on login |
| 🔁 | **Auto-updater** | Checks GitHub releases on startup |
| 🔍 | **Pixel-precise Capture** | Magnifier loupe, arrow-key precision, on-screen help |
| 🖱️ | **Cursor Capture** | System cursor captured as deletable element |
| 📊 | **Status Bar** | Live coords, selection size, zoom control, element count |
| 🎨 | **6 UI Themes** | Dark, Midnight, Ocean, Forest, Warm, Light |

---

## ⚡ Quick Start

### Option 1 — Installer (Recommended)

1. Download **[PapaRaZ_Setup_0.9.9.exe](https://github.com/aleled/paparaz/releases/latest)**
2. Run the installer
3. Press **PrintScreen** — start capturing

### Option 2 — Run from Source

```bash
git clone https://github.com/aleled/paparaz.git
cd paparaz
pip install -e .
python -m paparaz
```

> **Requirements:** Python 3.11+, Windows 10/11

---

## ⌨️ Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `PrintScreen` | Capture screen (global hotkey) |
| `V` | Select tool |
| `P` | Pen |
| `B` | Brush |
| `H` | Highlight |
| `L` | Line |
| `A` | Arrow |
| `R` | Rectangle |
| `E` | Ellipse |
| `T` | Text |
| `N` | Numbering |
| `S` | Stamp |
| `X` | Eraser |
| `M` | Blur / Masquerade |
| `C` | Crop |
| `Q` | Curved Arrow |
| `I` | Eyedropper |
| `G` | Magnifier |
| `D` | Measure |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |
| `Ctrl+C` | Copy to clipboard |
| `Ctrl+S` | Save as PNG |
| `Delete` | Delete selected element |
| `Shift+Click` | Add to multi-selection |
| `Esc` | Close editor |

---

## 🎨 Annotation Tools

<table>
<tr><th>Tool</th><th>Shortcut</th><th>Properties</th></tr>
<tr><td>🖱️ Select</td><td><code>V</code></td><td>Move · Resize · Rotate · Multi-select</td></tr>
<tr><td>✏️ Pen</td><td><code>P</code></td><td>Color · Width · Cap · Join · Dash · Shadow · Opacity</td></tr>
<tr><td>🖌️ Brush</td><td><code>B</code></td><td>Color · Width · Shadow · Opacity</td></tr>
<tr><td>🟡 Highlight</td><td><code>H</code></td><td>Color · Width · Opacity</td></tr>
<tr><td>📏 Line</td><td><code>L</code></td><td>Color · Width · Cap · Dash · Shadow</td></tr>
<tr><td>➡️ Arrow</td><td><code>A</code></td><td>Color · Width · Dash · Shadow</td></tr>
<tr><td>▭ Rectangle</td><td><code>R</code></td><td>Color · Fill · Width · Dash · Shadow</td></tr>
<tr><td>⭕ Ellipse</td><td><code>E</code></td><td>Color · Fill · Width · Dash · Shadow</td></tr>
<tr><td>🔤 Text</td><td><code>T</code></td><td>Font · Size · Bold · Italic · Underline (Ctrl+B/I/U) · Align · RTL · Background · Stroke</td></tr>
<tr><td>🔢 Numbering</td><td><code>N</code></td><td>Auto-increment markers · 4 styles (1·2·3 / a·b·c / I·II·III / boxed) · Reset counter · Size · Colors</td></tr>
<tr><td>🔖 Stamp</td><td><code>S</code></td><td>32 pre-built stamps (solid + transparent-bg + utility text) · Resizable · Rotatable</td></tr>
<tr><td>↩️ Curved Arrow</td><td><code>Q</code></td><td>Quadratic Bezier with tangent arrowhead · 3-click workflow</td></tr>
<tr><td>🔬 Eyedropper</td><td><code>I</code></td><td>Sample any pixel · Live 10× loupe · Sets fg or bg color</td></tr>
<tr><td>❌ Eraser</td><td><code>X</code></td><td>Click element to remove</td></tr>
<tr><td>🌫️ Blur</td><td><code>M</code></td><td>Pixelate regions · Adjustable block size</td></tr>
<tr><td>🪣 Fill</td><td><code>F</code></td><td>Flood-fill with background color · Tolerance</td></tr>
<tr><td>📐 Measure</td><td><code>D</code></td><td>Distance + angle measurement overlay</td></tr>
<tr><td>✂️ Crop</td><td><code>C</code></td><td>Non-destructive crop · Handles rotation</td></tr>
</table>

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| UI Framework | [PySide6](https://doc.qt.io/qtforpython/) (Qt 6) |
| Language | Python 3.11+ |
| Screen Capture | Win32 API via `ctypes` (BitBlt, DPI-aware) |
| Global Hotkey | Win32 `RegisterHotKey` |
| OCR | Windows.Media.Ocr via `winrt` |
| Auto-start | Windows Registry `HKCU\Run` |
| Packaging | [PyInstaller](https://pyinstaller.org) + [Inno Setup](https://jrsoftware.org) |

---

## 📁 Project Structure

```
src/paparaz/
├── __main__.py, app.py       # Entry point, app controller
├── core/
│   ├── capture.py            # Win32 multi-monitor capture
│   ├── elements.py           # 15 element types (shadow, style, serialization)
│   ├── history.py            # Undo/Redo (command pattern)
│   ├── export.py             # PNG, JPG, SVG, clipboard
│   └── settings.py           # JSON config persistence
├── ui/
│   ├── editor.py             # Main frameless editor window
│   ├── canvas.py             # Annotation canvas (zoom, pan, context menu)
│   ├── toolbar.py            # Multi-edge floating toolbar
│   ├── side_panel.py         # Floating property inspector (drag to reposition)
│   ├── tray.py               # System tray icon + menu
│   ├── overlay.py            # Region selector overlay (magnifier, arrow-key precision)
│   ├── status_bar.py         # Status bar (coords, zoom, element count)
│   ├── settings_dialog.py    # Modern settings (sidebar + 7 sections)
│   ├── stamps.py             # 16 SVG stamp definitions
│   ├── icons.py              # 32 SVG Material Design icons
│   ├── app_theme.py          # 5 built-in QSS themes
│   └── ocr.py                # Windows OCR threading bridge
├── tools/
│   ├── base.py               # BaseTool (hover, click, double-click)
│   ├── select.py             # Select, move, resize, rotate, multi-select
│   ├── drawing.py            # Pen, Brush, Highlight, Line, Arrow, Rect, Ellipse
│   └── special.py            # Text, Number, Eraser, Blur, Fill, Stamp, Crop, Slice
└── utils/
    ├── hotkey.py             # Win32 global hotkey listener
    ├── monitors.py           # Multi-monitor detection
    ├── updater.py            # GitHub releases update checker
    └── startup.py            # Auto-start on login (registry)
```

---

## 📖 Documentation

| Doc | Description |
|-----|-------------|
| [PLAN.md](docs/PLAN.md) | Phase-based roadmap with completion status |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design and data flow |
| [TOOLS_SPEC.md](docs/TOOLS_SPEC.md) | Tool behavior matrix and property reference |
| [UI_SPEC.md](docs/UI_SPEC.md) | Visual design specification |
| [CHANGELOG.md](docs/CHANGELOG.md) | Full version history |
| [TEST_PLAN.md](docs/TEST_PLAN.md) | Test suite guide and conventions |
| [QA_FINDINGS.md](docs/QA_FINDINGS.md) | QA findings report and backlog |
| [SETTINGS_PLAN.md](docs/SETTINGS_PLAN.md) | Settings dialog audit and plan |

---

## 🤝 Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you'd like to change.

---

## 📄 License

MIT — see [LICENSE](LICENSE)


---

<div align="center">
  <sub>Built with ❤️ by <a href="https://github.com/aleled">Alejandro Lichtenfeld</a> — Software & Network Engineer, Calella, Spain</sub>
</div>
