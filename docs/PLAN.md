# PapaRaZ - Master Development Plan

## Vision
A minimal, fast, Flameshot-inspired screen capture and annotation tool for Windows.
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
- [ ] 4.8 Auto-save / crash recovery

---

## Phase 5: UI Polish & UX - COMPLETE
**Goal**: Flameshot-style minimal toolbar, zoom, keyboard shortcuts.

- [x] 5.1 Flameshot-style circular toolbar (purple buttons, white SVG icons, drop shadows)
- [x] 5.2 Zoom system (25%-400% presets + custom input + Ctrl+scroll)
- [x] 5.3 Keyboard shortcuts for all tools (V,P,B,L,A,R,E,T,N,X,M + Ctrl combos)
- [x] 5.4 Cursor changes per tool + hover previews (ghost shapes, highlights)
- [x] 5.5 Tooltip hints on all toolbar buttons
- [x] 5.6 Dark theme (#0d0d1a background, #1a1a2e panels, #740096 accent)
- [x] 5.7 Status bar (current tool, zoom level, cursor position, hints)
- [x] 5.8 Enhanced selection visuals (purple border, circular handles, dimension badge)
- [x] 5.9 Per-tool side panel (sections auto-show/hide per active tool)
- [x] 5.10 Edit mode banner when element selected
- [x] 5.11 Double-click to re-edit text elements
- [x] 5.12 Region selector with dark overlay hole effect and purple handles
- [ ] 5.13 Light theme option
- [ ] 5.14 Smooth animations and transitions

---

## Phase 6: Multi-Monitor & Advanced Features - IN PROGRESS
**Goal**: Robust multi-monitor support and power-user features.

- [x] 6.1 Multi-monitor aware capture (spans all screens, DPI-aware)
- [ ] 6.2 Snap to edges/grid
- [ ] 6.3 Copy/paste elements between captures
- [ ] 6.4 Drag and drop image onto canvas
- [ ] 6.5 Recent captures gallery
- [ ] 6.6 Pin screenshot (always-on-top floating window)
- [ ] 6.7 Crop/resize captured region after capture
- [ ] 6.8 Element z-order controls (bring to front, send to back)

---

## Phase 7: Packaging & Distribution
**Goal**: Installable Windows application.

- [ ] 7.1 PyInstaller / Nuitka build configuration
- [ ] 7.2 Windows installer (NSIS or Inno Setup)
- [ ] 7.3 Auto-start on login option
- [ ] 7.4 Update checker
- [ ] 7.5 Application icon and branding assets
- [ ] 7.6 Final testing and bug fixes

---

## Future Enhancements (Backlog)
- [ ] Settings dialog (configurable hotkeys, default colors, save directory)
- [ ] Custom color palette / recent colors
- [ ] Eyedropper / color grab tool
- [ ] Layers panel (element z-ordering with drag)
- [ ] Text outline / stroke on text
- [ ] Curved arrows / Bezier curves
- [ ] Stamp/emoji tool
- [ ] Magnifier tool (zoom lens while selecting)
- [ ] Delay capture (timer)
- [ ] Video/GIF recording
- [ ] Upload to cloud (Imgur, custom endpoint)
- [ ] Plugin/extension system
- [ ] Localization (i18n)
- [ ] Accessibility (screen reader support)
- [ ] Project file format (.papraz) to save/load edits with full object state

---

## Status Legend
- [ ] Not started
- [x] Completed

## Current Status: Phase 5 complete, Phase 6 in progress
**Version**: 0.5.0
**Last updated**: 2026-03-29
