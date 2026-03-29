# PapaRaZ - Changelog

## [0.6.0] - 2026-03-29

### Phase 6: Advanced Features
- **Element z-order**: Bring to front (Ctrl+]), Send to back (Ctrl+[), Move up (Ctrl+Shift+]), Move down (Ctrl+Shift+[) with undo support
- **Drag & drop images**: Drop PNG/JPG/BMP/GIF/WebP from file explorer onto canvas
- **Pin screenshot**: Always-on-top floating window (Ctrl+P), draggable, right-click to scale or close
- **Recent captures**: Tray submenu shows last 10 saved captures, click to reopen
- **Delay capture**: 3/5/10 second countdown via tray menu

### Settings Dialog
- Full GUI settings accessible from tray menu
- **General tab**: Save directory, default format, JPG quality, capture delay, start on login, tray notifications
- **Hotkeys tab**: Configure all keyboard shortcuts
- **Tools tab**: Default foreground/background colors, line width, font family/size
- **About tab**: Version info

### Toolbar Additions
- **Pin button** with pushpin icon
- **Bring to front / Send to back** buttons with layering icons
- 5 new SVG icons: pin, eyedropper, bring_front, send_back, timer

### Tray Menu Enhancements
- Delay capture submenu (3s, 5s, 10s)
- Recent captures submenu with file names
- Dark styled context menu

### Packaging
- PyInstaller spec file (`paparaz.spec`) for single-exe build
- `build.bat` build script

### New Files
- `ui/pin_window.py` - Always-on-top pin window
- `ui/settings_dialog.py` - Settings dialog with tabs
- `paparaz.spec` - PyInstaller build config
- `build.bat` - Build script

---

## [0.5.0] - 2026-03-29

### Full Shadow Controls
- Shadow **color picker** with alpha channel support
- Shadow **offset X/Y** spinboxes (-30 to +30 px)
- Shadow **blur radius** spinbox (0-30 px)
- All shadow controls update selected elements live
- Canvas setters: `set_shadow_color()`, `set_shadow_offset_x()`, `set_shadow_offset_y()`, `set_shadow_blur()`

### NumberElement Text Controls
- Font family picker for number markers
- **Text color** picker (default: auto-contrast white/black against circle fill)
- `NumberElement.text_color` field with auto-contrast fallback when empty

### Bug Fixes
- Fixed **quit crash**: `GlobalHotkeyListener.stop()` now uses `kernel32.GetCurrentThreadId()` stored during `run()` (PySide6 removed `currentThreadId()`)
- Removed **deprecation warning**: `AA_EnableHighDpiScaling` setAttribute removed (always enabled in Qt6)

---

## [0.4.0] - 2026-03-29

### Enhanced Selection Visuals
- **Purple selection border** (2px, #740096) with white inner glow
- **Tinted overlay** on selected element bounding rect
- **Circular handles** (12px, purple fill, white outline) matching Flameshot style
- **Dimension badge**: floating black pill showing `W×H (X,Y)` below selected element

### Tool Hover Previews
- **Text tool**: Ghost dashed text box at cursor before clicking
- **Numbering tool**: Ghost circle showing next number at 40% opacity
- **Eraser tool**: Red highlight + X icon on element under cursor
- **Fill tool**: Color-tinted highlight on fillable shape under cursor
- **Masquerade tool**: Crosshair at cursor position
- **Select tool**: Dotted purple outline on non-selected hovered element

### Text Tool Improvements
- **Editing frame**: Purple dashed border + light tint around text area while editing
- **Placeholder**: "Type here..." shown in gray when editing empty text
- **Thicker cursor**: 2px cursor line
- **Multi-line**: Enter for newline, Ctrl+Enter to finalize

### Double-Click Text Re-editing
- Double-click any TextElement (in Select tool) to switch to Text tool and re-edit it
- Element pulled from committed list back into preview/editing mode
- `canvas.request_text_edit` signal wired through editor

### BaseTool Enhancements
- Added `on_hover(pos)`, `on_double_click(pos, event)`, `paint_hover(painter)` to base tool
- Canvas calls `on_hover()` on mousemove when no buttons pressed
- Canvas calls `paint_hover()` during `paintEvent()` after preview, before selection handles

---

## [0.3.0] - 2026-03-29

### Tool Consistency & Property System Overhaul

#### Shadow Painting on ALL Elements
- Pen, Brush, Line, Arrow, Rectangle, Ellipse all paint shadows via `_paint_shadow()`
- Number and Image elements also support shadow rendering

#### Per-Tool Settings in Side Panel
- **Pen/Brush/Line/Arrow**: Stroke width, line cap, join, dash pattern
- **Rectangle/Ellipse**: All stroke settings + filled shape toggle
- **Text**: Font, size, bold/italic/underline/strikethrough, alignment, RTL/LTR, background
- **Masquerade**: Pixel size slider (2-50px)
- **Numbering**: Independent circle size (16-80px)
- **Eraser/Fill**: No irrelevant settings shown
- Sections auto-show/hide per tool

#### Element Property Inspector
- Selecting an element loads its properties into the side panel
- Purple "Editing selected element" banner
- Signal-blocking during load prevents feedback loops
- Deselecting clears edit mode

#### Consistency Fixes
- Opacity stored in canvas template AND applied to new elements
- All setters consistently update template AND selected element
- Strikethrough signal connected
- Fill tool uses background color (not foreground)
- ElementStyle: added `cap_style`, `join_style`, `dash_pattern`

---

## [0.2.0] - 2026-03-29

### Flameshot UI Overhaul
- Circular toolbar buttons (40px purple, white SVG icons, drop shadows)
- 32 custom SVG Material Design icons
- Dark overlay region selector with hole effect
- Side panel with tool sub-settings

### Rich Text Tool
- Font family, size, bold/italic/underline/strikethrough
- Alignment (L/C/R), Direction (LTR/RTL)
- Text background color with toggle
- Multi-line support (Enter/Ctrl+Enter)

### Paste Support
- Ctrl+V pastes images as ImageElement

### Live Property Editing
- Side panel changes update selected element in real-time

---

## [0.1.0] - 2026-03-29

### Initial Release
- Project scaffolding (PySide6, pyproject.toml)
- System tray + global hotkey (PrintScreen)
- Multi-monitor screen capture (Win32 BitBlt, DPI-aware)
- Region selection overlay
- 12 annotation tools (Select, Pen, Brush, Line, Arrow, Rect, Ellipse, Text, Number, Fill, Eraser, Blur)
- Element-based object model (select, move, resize, delete)
- Undo/Redo (command pattern, 200-step)
- Export: PNG, JPG, SVG, clipboard
- Load existing images
- Zoom (25%-400% + custom + Ctrl+scroll)
- Middle-click pan
- Keyboard shortcuts
- Settings system (~/.paparaz/)
