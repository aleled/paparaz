# PapaRaZ - Master Development Plan

## Vision
A minimal, fast, object-based screen capture and annotation tool for Windows.
Each annotation is a discrete object that can be selected, moved, resized, and deleted.

---

## Phase 1: Foundation (Core Infrastructure) - COMPLETE
**Goal**: Bootable app with screen capture and basic canvas.

- [x] 1.1 Project scaffolding (PySide6, entry point, packaging config)
- [x] 1.2 System tray integration with context menu
- [x] 1.3 Global hotkey registration (PrintScreen key via Windows API)
- [x] 1.4 Multi-monitor screen capture using Windows API (DPI-aware)
- [x] 1.5 Region selection overlay (click-drag to select area)
- [x] 1.6 Basic canvas/editor window displaying captured image
- [x] 1.7 Settings system (JSON-based config file in ~/.paparaz/)

---

## Phase 2: Object Model & Core Tools - COMPLETE
**Goal**: Element-based annotation system with essential drawing tools.

- [x] 2.1 Base `AnnotationElement` class (position, bounds, selection, serialization)
- [x] 2.2 Selection system (click to select, handles for resize, Delete key to remove)
- [x] 2.3 Pen tool (freehand drawing as polyline element)
- [x] 2.4 Brush tool (thicker, softer freehand strokes)
- [x] 2.5 Line tool (straight line element, Shift=snap 45deg)
- [x] 2.6 Arrow tool (line with arrowhead, Shift=snap 45deg)
- [x] 2.7 Rectangle tool (outlined and filled, Shift=square)
- [x] 2.8 Ellipse tool (outlined and filled, Shift=circle)
- [x] 2.9 Text tool (click to place, inline editing, rich formatting)
- [x] 2.10 Numbering tool (auto-incrementing numbered markers)

---

## Phase 3: Advanced Tools & Properties - COMPLETE
**Goal**: Fill, erase, masquerade, and property editing for elements.

- [x] 3.1 Color picker (foreground + background with alpha)
- [x] 3.2 Line width control (slider 1-50px + spinbox)
- [x] 3.3 Fill tool (fills shapes with background color)
- [x] 3.4 Eraser tool (click to delete elements, red hover highlight)
- [x] 3.5 Masquerade/blur tool (pixelate region, configurable pixel size 2-50)
- [x] 3.6 Shadow system (toggle, color picker, offset X/Y, blur radius)
- [x] 3.7 Property inspector (selecting element loads all properties into side panel)
- [x] 3.8 Font/size/color for text tool + font/color for number markers
- [x] 3.9 Line cap style (round/square/flat)
- [x] 3.10 Join style (round/bevel/miter)
- [x] 3.11 Dash pattern (solid/dash/dot/dashdot)
- [x] 3.12 Filled shape toggle for rect/ellipse
- [x] 3.13 Opacity slider (10-100%)

---

## Phase 4: History, Save/Load, Clipboard - COMPLETE
**Goal**: Undo/redo, file operations, clipboard support.

- [x] 4.1 Undo/Redo system (command pattern, 200-step stack)
- [x] 4.2 Save to PNG
- [x] 4.3 Save to JPG (quality selector)
- [x] 4.4 Export to SVG (vector export of annotations)
- [x] 4.5 Copy to clipboard
- [x] 4.6 Load image for annotation (open existing image)
- [x] 4.7 Paste from clipboard (Ctrl+V, images become ImageElement)
- [x] 4.8 Auto-save / crash recovery

---

## Phase 5: UI Polish & UX - COMPLETE
**Goal**: Minimal toolbar, zoom, keyboard shortcuts.

- [x] 5.1 Circular toolbar (purple buttons, white SVG icons, drop shadows)
- [x] 5.2 Zoom system (25%-400% presets + custom input + Ctrl+scroll)
- [x] 5.3 Keyboard shortcuts for all tools (V,P,B,L,A,R,E,T,N,X,M + Ctrl combos)
- [x] 5.4 Cursor changes per tool + hover previews (ghost shapes, highlights)
- [x] 5.5 Tooltip hints on all toolbar buttons
- [x] 5.6 Dark theme (#0d0d1a background, #1a1a2e panels, #740096 accent)
- [x] 5.7 Status bar (current tool, zoom level, cursor position, hints)
- [x] 5.8 Enhanced selection visuals (theme-aware border, square handles, dimension badge, transparent overlay)
- [x] 5.9 Per-tool side panel (sections auto-show/hide per active tool)
- [x] 5.10 Edit mode banner when element selected
- [x] 5.11 Double-click to re-edit text elements
- [x] 5.12 Region selector with dark overlay hole effect and purple handles
- [x] 5.13 Adaptive toolbar flow layout (wraps to multiple rows on narrow windows)
- [x] 5.14 Side panel pin/auto-hide/hidden modes with header bar and grip tab
- [x] 5.15 Light theme option
- [x] 5.16 Smooth animations and transitions

---

## Phase 6: Multi-Monitor & Advanced Features - IN PROGRESS
**Goal**: Robust multi-monitor support and power-user features.

- [x] 6.1 Multi-monitor aware capture (spans all screens, DPI-aware)
- [x] 6.2 Snap to edges/grid
- [x] 6.3 Copy/paste elements (right-click context menu: Copy, Duplicate, Paste)
- [x] 6.4 Drag and drop image onto canvas
- [x] 6.5 Recent captures gallery (tray submenu)
- [x] 6.6 Pin screenshot (always-on-top floating window)
- [x] 6.7 Crop/resize captured region after capture (CropTool with rotation support)
- [x] 6.8 Element z-order (bring to front, send to back, move up/down with undo)
- [x] 6.9 Delay capture (3/5/10 second timer via tray menu)
- [x] 6.10 Settings dialog (hotkeys, defaults, theme, shadow defaults, save directory)
- [x] 6.11 Element rotation (side panel slider, rotation handle, all element types)
- [x] 6.12 Multi-select (rubber-band + shift+click, group move, group delete, group OCR)
- [x] 6.13 App themes (5 built-in: dark/midnight/ocean/forest/warm, selectable in settings)
- [x] 6.14 Windows OCR (printed text recognition from selected elements via winrt)

---

## Phase 7: Packaging & Distribution - NEARLY COMPLETE
**Goal**: Installable Windows application.

- [x] 7.1 PyInstaller build configuration (paparaz.spec + build.bat)
- [x] 7.2 Windows installer (Inno Setup — installer/paparaz_setup.iss)
- [x] 7.3 Auto-start on login (Windows Registry HKCU\Run, toggled from Settings)
- [x] 7.4 Update checker (GitHub releases API, background thread, non-blocking dialog)
- [x] 7.5 Application icon (assets/paparaz.ico — 16/24/32/48/64/128/256 px, version_info.txt)
- [x] 7.6 Final testing and bug fixes

---

## Future Enhancements (Backlog)
- [x] Custom color palette / recent colors (side panel, labeled, persisted to settings)
- [x] Eyedropper / color grab tool — live loupe, fg/bg pick, auto-return to prev tool (I)
- [x] Text outline / stroke on text — QPainterPath, side panel Outline section
- [x] Curved arrows / Bezier curves — CurvedArrowElement, 3-click workflow, tangent arrowhead (Q)
- [x] Stamp/emoji tool (32 SVG stamps: 16 original + 10 transparent-bg variants + 6 utility text stamps: WIP, DRAFT, TODO, DONE, FIX, NEW)
- [x] Properties panel UX overhaul — 260 px wide, element preview strip, labeled format buttons, pin/close header, auto-show on tool switch
- [x] Text tool advanced editing — click-to-position cursor, resize handle, Up/Down nav with x-hint, word nav, Ctrl+Home/End
- [x] Window border contrast — multi-layer paintEvent outline so editor is distinct from any desktop
- [x] Installer: force-kill running PapaRaZ.exe before install (taskkill fallback in Inno Setup)
- [x] In-app update downloader (progress bar, auto-launch installer, fallback browser)
- [x] Layers panel (element z-ordering with drag)
- [x] Magnifier tool (zoom loupe callout — source rect + zoomed circle annotation)
- [x] Light theme option
- [ ] Video/GIF recording
- [ ] Upload to cloud (Imgur, custom endpoint)
- [ ] Plugin/extension system
- [ ] Localization (i18n)
- [ ] Accessibility (screen reader support)
- [x] Auto-save / crash recovery
- [x] Measure tool (distance + angle readout, shortcut D)
- [x] Status bar (mouse position, selection size, canvas dims, element count, zoom control)
- [x] Pixel-precise capture overlay (magnifier loupe, arrow-key precision, on-screen help)
- [x] System cursor capture as deletable element (Win32 GetCursorInfo pipeline)
- [x] Multi-monitor DPI fix (EnumDisplayMonitors for physical pixel coordinates)
- [x] Auto-populate recent captures (auto-save on capture, stale cleanup)
- [x] Text box long word wrapping (character-level break)
- [x] Live text property editing during active editing (font, size, color, bold, etc.)
- [x] Rotated text editing (maintain rotation, coordinate un-rotation for clicks/resize)
- [x] Resize flicker fix (opaque palette-based background)
- [x] Fill tool overlay fix (ImageElement on top, not behind)

### Settings — Behavior & Capture (PicPick-inspired gaps)
- [x] Multiple capture hotkeys: full-screen (Ctrl+PrtScn), active window (Alt+PrtScn), repeat last (Shift+PrtScn)
- [x] "Hide editor before capturing" — hide editor window so it doesn't appear in the new screenshot
- [x] "Confirm before closing with unsaved changes" — configurable close guard
- [x] "Exit app when closing editor" — vs keep running in tray (configurable toggle)
- [x] Remember editor window position and size across sessions
- [x] Include mouse cursor in captures — embed pointer in screenshot (on/off)
- [x] Capture sound — audible shutter feedback (on/off)

### Settings — Output
- [x] PNG compression level slider (0=fast/large .. 9=slow/small)
- [x] Auto-copy to clipboard after every save (silent, no dialog)
- [x] Open saved file in external app option

### Settings — Editor / Panel
- [x] Default zoom level on open: Fit / 100% / Fill / Remember last
- [x] Starting properties panel mode: Auto / Pinned / Hidden
- [x] Canvas background color: dark / system / checkerboard / custom solid color
- [x] Panel auto-hide delay configurable (1–10 sec slider)
- [x] Zoom scroll speed configurable (1.05–1.30×)

### Settings — Hotkeys UX Overhaul
- [x] Modifier checkboxes (Shift/Ctrl/Alt) + key dropdown per action (vs freeform text input)
- [x] Separate section for global capture hotkeys vs in-editor shortcuts

### Settings — About page
- [x] Action buttons: Website, Check for Updates, Report Issue (GitHub link)
- [x] License / credits section

### Settings — Tools Defaults
- [x] Highlight color and width configurable in settings
- [x] Default stamp ID configurable in settings
- [x] Default blur pixel size configurable in settings
- [x] Max recent captures configurable in settings

### Settings — Bugs to fix (from SETTINGS_PLAN.md)
- [x] Fix shadow blur display: currently shows single spinbox; needs separate Blur X / Blur Y widgets
- [x] Fix font family: QLineEdit → QFontComboBox
- [x] Add `select_all` hotkey to Shortcuts page
- [x] Recent colors view + Clear button in Appearance page
- [x] Filename live preview (accent colored, format-aware extension)

### Far future (Tier 10)
- [x] Project file format (.papraz) — save/load edits with full object state (`Ctrl+Shift+P` / `Ctrl+Shift+O`, zlib-compressed JSON, background + elements, 11 roundtrip tests)

---

## Status Legend
- [ ] Not started
- [x] Completed

- [x] HiDPI / Retina-sharp captures — `setDevicePixelRatio` instead of SmoothTransformation downscale (all capture paths + export)
- [x] Number marker label styles: numeric / alpha / roman / boxed — toggle buttons + reset counter in side panel
- [x] Text tool Ctrl+B/I/U shortcuts while editing
- [x] Recent colors palette redesigned to 2×8 grid (was overflowing single-row)
- [x] Crop rotation handle sign-error fix (handle always above box at any angle)
- [x] Editor close confirmation dialog (Save & Exit / Discard / Cancel)
- [x] Toolbar reserved space for close button + overflow indicator

- [x] .papraz project file format — save/load full annotated sessions (Ctrl+Shift+P/O)
- [x] Drawing tool bug fixes — normalized rect for Rect/EllipseTool, zero-length guard for CurvedArrow
- [x] elements.py refactoring — `_rotated_paint` / `_paint_offset_shadow` helpers extracted (-43 lines)
- [x] MeasureTool + MeasureElement test coverage — 77 new tests (was 0)
- [x] Test suite grown to 776 tests (+102 from 674)

## Current Status: v1.0.0 — first stable release, project file format, 776 tests, GitHub Pages
**Version**: 1.0.0
**Last updated**: 2026-04-18
