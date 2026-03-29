# PapaRaZ - Screen Capture & Annotation Tool

**Author:** Alejandro Lichtenfeld
**License:** MIT — see [LICENSE](LICENSE)

A lightweight, Flameshot-inspired screen capture and annotation utility for Windows. Every annotation is a discrete, selectable object with full property editing.

> **License note:** PapaRaZ is an independent Python/PySide6 reimplementation inspired by [Flameshot](https://flameshot.org) (GPL-3.0). No Flameshot source code was copied or adapted.

## Features

### Capture
- **Multi-monitor** screen capture via Win32 API (DPI-aware)
- **Region selector** with dark overlay, crosshair, dimension labels, purple handles
- **System tray** with global hotkey (PrintScreen)
- **Paste images** from clipboard (Ctrl+V) onto canvas

### 12 Annotation Tools
| Tool | Shortcut | Description |
|------|----------|-------------|
| Select | V | Click to select, drag to move, handles to resize/rotate, Delete to remove |
| Pen | P | Freehand drawing with configurable stroke |
| Brush | B | Soft semi-transparent strokes |
| Line | L | Straight lines (Shift = snap to 45deg) |
| Arrow | A | Lines with arrowheads |
| Rectangle | R | Outlined or filled rectangles (Shift = square) |
| Ellipse | E | Outlined or filled ellipses (Shift = circle) |
| Text | T | Rich text: font, size, bold/italic/underline, alignment, RTL/LTR, background |
| Numbering | N | Auto-incrementing numbered circle markers |
| Eraser | X | Click to delete elements (red highlight on hover) |
| Blur | M | Pixelate/blur sensitive regions |
| Fill | F | Fill shapes with background color |

### Object-Based Editing
- Every annotation is a selectable, movable, resizable element
- **Rotation**: drag the rotation handle (above selection) or use the side panel slider
- **Purple selection handles** with dimension badge (W x H, position)
- **Hover previews**: ghost shapes before placing, red highlight on eraser targets
- **Double-click** text elements to re-edit them
- **Property inspector**: selecting any element loads its properties into the side panel
- **Multi-select**: rubber-band drag or Shift+click to select multiple elements; group move, group delete
- **Right-click menu**: Copy, Duplicate, Delete on single elements; Recognize text (OCR) on multi-selection
- **Windows OCR**: select pen/brush strokes → right-click → Recognize text → inserts as TextElement (printed text)

### Per-Tool Properties (Side Panel)
| Property | Tools |
|----------|-------|
| Foreground / Background color | All |
| Stroke width (1-50px) | Pen, Brush, Line, Arrow, Rect, Ellipse |
| Line cap (round/square/flat) | Pen, Line, Arrow, Rect, Ellipse |
| Join style (round/bevel/miter) | Pen, Line, Arrow, Rect, Ellipse |
| Dash pattern (solid/dash/dot/dashdot) | Pen, Line, Arrow, Rect, Ellipse |
| Filled toggle | Rectangle, Ellipse |
| Font family, size, color | Text, Numbering |
| Bold, Italic, Underline, Strikethrough | Text |
| Alignment (L/C/R), Direction (LTR/RTL) | Text |
| Text background color | Text |
| Circle size, text color | Numbering |
| Pixel size (2-50px) | Blur/Masquerade |
| Shadow (toggle, color, offset X/Y, blur) | All drawing tools |
| Opacity (10-100%) | All drawing tools |

### Export
- **PNG**, **JPG** (quality selector), **SVG** (vector), **Clipboard**
- Undo/Redo (200-step history, Ctrl+Z / Ctrl+Y)

## Tech Stack
- Python 3.11+ / PySide6 (Qt 6)
- Win32 API via ctypes (screen capture, global hotkeys, multi-monitor)

## Quick Start
```bash
cd C:\working\print-scr
pip install -r requirements.txt
set PYTHONPATH=src
python -m paparaz
```

## Project Structure
```
src/paparaz/
    __main__.py, app.py          # Entry point, app controller
    core/
        capture.py               # Win32 multi-monitor capture
        elements.py              # 10 element types with shadow, style, serialization
        history.py               # Undo/Redo command pattern
        export.py                # PNG, JPG, SVG, clipboard
        settings.py              # JSON config (~/.paparaz/)
    ui/
        tray.py                  # System tray icon + menu
        overlay.py               # Flameshot-style region selector
        editor.py                # Main editor window
        canvas.py                # Annotation canvas (zoom, pan, render, context menu)
        toolbar.py               # Circular purple button toolbar (flow layout)
        side_panel.py            # Per-tool settings + property inspector (pin/auto/hidden)
        icons.py                 # 32 SVG Material Design icons
        app_theme.py             # 5 built-in QSS themes (dark/midnight/ocean/forest/warm)
        ocr.py                   # Windows OCR via winrt (threading bridge, result dialog)
    tools/
        base.py                  # BaseTool with hover/double-click
        select.py                # Select, move, resize, double-click edit
        drawing.py               # Pen, Brush, Line, Arrow, Rect, Ellipse
        special.py               # Text, Numbering, Eraser, Masquerade, Fill
    utils/
        hotkey.py                # Win32 global hotkey
        monitors.py              # Multi-monitor detection
```

## Documentation
- [Development Plan](docs/PLAN.md) - Phase-based roadmap with completion status
- [Architecture](docs/ARCHITECTURE.md) - System design and data flow
- [Tools Spec](docs/TOOLS_SPEC.md) - Tool behavior matrix and property reference
- [UI Spec](docs/UI_SPEC.md) - Visual design specification
- [Changelog](docs/CHANGELOG.md) - Version history
