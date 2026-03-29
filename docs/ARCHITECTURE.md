# PapaRaZ - Architecture

## High-Level Overview

```
+-------------------+     +------------------+     +-------------------+
|   System Tray     |---->|  Screen Capture  |---->|   Region Selector |
|   (Always running)|     |  (Win32 BitBlt)  |     |   (Dark overlay)  |
+-------------------+     +------------------+     +-------------------+
        |                         |                        |
        v                         v                        v
+-------------------+     +------------------+     +-------------------+
|   Global Hotkey   |     | Multi-Monitor    |     |   Editor Window   |
|   (Win32 API)     |     | (DPI-aware)      |     |   (Main UI)       |
+-------------------+     +------------------+     +-------------------+
                                                           |
                                               +-----------+-----------+
                                               |           |           |
                                               v           v           v
                                        +-----------+ +---------+ +---------+
                                        |  Toolbar  | |  Side   | | Canvas  |
                                        | (Circular | | Panel   | | (Zoom/  |
                                        |  buttons) | | (Props) | |  Pan)   |
                                        +-----------+ +---------+ +---------+
                                                           |           |
                                                           v           v
                                                   +-------------------+
                                                   | Tool System       |
                                                   | (12 tools, hover, |
                                                   |  double-click)    |
                                                   +-------------------+
                                                           |
                                                           v
                                                   +-------------------+
                                                   | Element Model     |
                                                   | (10 types, style, |
                                                   |  shadow, history) |
                                                   +-------------------+
                                                           |
                                                           v
                                                   +-------------------+
                                                   | Export System     |
                                                   | (PNG/JPG/SVG/CB) |
                                                   +-------------------+
```

## Actual Module Structure

```
src/paparaz/
    __init__.py              # Version, app name
    __main__.py              # Entry point (QApplication)
    app.py                   # PapaRazApp controller (tray, hotkey, capture, editor)

    core/
        __init__.py
        capture.py           # Win32 BitBlt multi-monitor capture (DPI-aware)
        elements.py          # 10 element types: Pen, Brush, Line, Arrow, Rect,
                             #   Ellipse, Text, Number, Mask, Image
                             # ElementStyle: colors, width, opacity, shadow,
                             #   font, cap/join/dash
        history.py           # Undo/Redo via Command pattern (200-step stack)
        export.py            # save_png, save_jpg, save_svg, copy_to_clipboard
        settings.py          # JSON config in ~/.paparaz/settings.json

    ui/
        __init__.py
        tray.py              # QSystemTrayIcon + context menu
        overlay.py           # Full-screen dark overlay with selection hole
        editor.py            # QMainWindow: toolbar + side panel + canvas + status bar
                             # Wires all signals between components
        canvas.py            # AnnotationCanvas: paint, zoom, pan, hover, double-click
                             # Style template + selected element live editing
        toolbar.py           # Flameshot-style circular purple buttons (40px, drop shadow)
        side_panel.py        # Per-tool settings sections + element property inspector
                             # Shadow controls, text controls, number controls
        icons.py             # 32 SVG Material Design icons (white on transparent)

    tools/
        __init__.py
        base.py              # BaseTool: press, move, release, hover, double_click,
                             #   paint_hover, activate, deactivate
        select.py            # Click-select, drag-move, handle-resize, double-click edit
        drawing.py           # PenTool, BrushTool, LineTool, ArrowTool,
                             #   RectangleTool, EllipseTool (all with Shift-constrain)
        special.py           # TextTool (rich text, re-edit), NumberingTool (ghost preview),
                             #   EraserTool (red hover), MasqueradeTool, FillTool (hover tint)

    utils/
        __init__.py
        hotkey.py            # Win32 RegisterHotKey + GetCurrentThreadId for clean stop
        monitors.py          # EnumDisplayMonitors + GetDpiForMonitor
```

## Key Design Decisions

### 1. Element-Based Model
Every annotation is an `AnnotationElement` subclass with: `paint()`, `paint_selection()`,
`contains_point()`, `bounding_rect()`, `move_by()`, `handle_at()`, `to_dict()`.
`_paint_shadow()` in the base class handles shadow rendering for all element types.

### 2. ElementStyle
Shared style dataclass: `foreground_color`, `background_color`, `line_width`, `opacity`,
`shadow` (Shadow dataclass with enabled/color/offset_x/offset_y/blur_radius),
`font_family`, `font_size`, `cap_style`, `join_style`, `dash_pattern`.

### 3. Command Pattern for Undo/Redo
All mutations (add, delete, move, modify) are wrapped in `Command` objects.
`HistoryManager` maintains undo/redo stacks up to 200 commands.

### 4. Tool System with Hover/Double-Click
`BaseTool` defines: `on_press()`, `on_move()`, `on_release()`, `on_hover()`,
`on_double_click()`, `paint_hover()`, `on_key_press()`, `on_activate()`, `on_deactivate()`.
Tools produce elements or modify existing ones. Only one tool active at a time.

### 5. Side Panel with Per-Tool Sections
`TOOL_SECTIONS` dict maps each `ToolType` to which UI sections are visible.
`load_element_properties()` reads a selected element and populates all controls.
`_loading_element` flag prevents signal re-emission during property load.

### 6. Signal Architecture
```
Toolbar  --tool_selected-->  Editor  --set_tool()-->  Canvas
SidePanel --property_changed-->  Editor  --canvas.set_*()-->  Canvas + Selected Element
Canvas  --element_selected-->  Editor  --load_element_properties()-->  SidePanel
Canvas  --request_text_edit-->  Editor  --text_tool.start_editing()-->  TextTool
```

### 7. Win32 API for Capture
`ctypes` + Win32 API (`BitBlt`, `GetDC`, `GetDIBits`) for reliable multi-monitor capture.
`SetProcessDpiAwareness(2)` for per-monitor DPI scaling.
`GetCurrentThreadId()` stored in `run()` for clean `PostThreadMessageW(WM_QUIT)` on stop.

## Data Flow

1. User presses PrintScreen
2. `GlobalHotkeyListener` thread fires `hotkey_pressed` signal
3. `PapaRazApp._start_capture()` calls `capture_all_screens()` via Win32 BitBlt
4. `RegionSelector` overlay appears (dark veil with selection hole)
5. User drags to select region, `region_selected` emitted
6. `EditorWindow` opens with cropped pixmap in `AnnotationCanvas`
7. User picks tool from toolbar -> side panel shows relevant settings
8. User draws -> tool creates elements via `canvas.add_element()` (with undo)
9. User selects element -> properties load into side panel -> live editing
10. User saves/copies via toolbar or Ctrl+S/Ctrl+C
