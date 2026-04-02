# PapaRaZ - Changelog

## [0.9.7] - 2026-04-02

### Element Serialization
- Added `from_dict()` classmethod to all 12 element types for JSON deserialization
- New `element_from_dict()` factory function with `_ELEMENT_CLASS_MAP` type registry
- Full roundtrip: `to_dict()` → JSON → `from_dict()` for all element types
- Enables future .papraz project file format and session recovery from JSON

### Robustness Fixes
- Guard `set_tool(None)` — no longer crashes, silently returns
- Guard `copy_element(None)` — no longer crashes, silently returns
- Color validation in `ElementStyle` — invalid color strings fall back to defaults (`#FF0000` fg, `#FFFFFF` bg)
- Fixed `RectElement`/`EllipseElement` positional arg trap in side panel preview builder

### EyedropperTool Improvements
- Added `_sample_color_from_pixmap()` fallback — reads directly from canvas background
- `_sample_color()` and `_sample_area()` now try screen grab first, then fall back to background pixmap
- Tool is now fully testable in headless environments

### Test Suite Expansion
- **653 tests** across 4 files, all passing (~14s)
- 29 new from_dict roundtrip tests covering all element types
- 9 fix verification tests for guards, color validation, eyedropper fallback
- 3 color case-sensitivity test fixes
- Updated QA_FINDINGS.md — all issues marked FIXED
- Updated TEST_PLAN.md with accurate test counts

---

## [0.9.6] - 2026-04-01

### Multiple Capture Modes
- **Ctrl+PrintScreen**: Capture full screen (instant, no overlay)
- **Alt+PrintScreen**: Capture active window
- **Shift+PrintScreen**: Repeat last captured region
- All three hotkeys are configurable in Settings → Shortcuts

### Settings — Behavior Page Enhancements
- "Exit app when last editor closes" toggle (vs stay in tray)
- Include mouse cursor in captures toggle
- Capture shutter sound toggle
- Default panel mode on open (Auto / Pinned / Hidden)
- Default zoom level on open (Fit / 100% / Fill / Remember last)

### Settings — Output
- PNG compression level (0–9) in Capture page
- Auto-copy to clipboard after every save
- Open saved file in default app after save

### Settings — Appearance
- Recent colors display with "Clear all" button
- Max recent captures spinbox in Capture page

### Settings — Tools
- Highlight default color and width configurable
- Default stamp ID selectable
- Default blur pixel size configurable
- Tool defaults wired into HighlightTool, StampTool, MasqueradeTool

### Editor
- Window geometry (position + size) persisted across sessions
- Default zoom applied on open (Fit/100%/Fill/Remember)
- Zoom level saved on close when "Remember" mode is active
- Filename preview now accent-colored and format-aware

### Hotkeys UX Overhaul
- Shortcuts page split into "Capture Hotkeys (global)" and "Editor Shortcuts" sections
- Modifier checkboxes (Shift/Ctrl/Alt) as styled toggle buttons + key dropdown per action
- Replaces freeform text input with structured, error-proof hotkey editor

### License & Credits
- About page now shows full MIT license text in monospace styled label
- Third-party credits section: PySide6, Pillow, PyInstaller, winrt

### Layers Panel
- Floating panel with element list in z-order (top = front)
- Drag-and-drop reordering via QListWidget InternalMove
- Move up / move down / delete buttons
- Element type icons and names for each layer entry
- Toggled via toolbar "Layers" action button

### Magnifier Tool (G)
- Drag to select source region, creates zoomed callout annotation
- MagnifierElement renders 2× magnified content from canvas background
- Border, zoom label ("2×"), and dashed source indicator overlay
- Crosshair hover preview while positioning

### Light Theme
- New "light" theme added to APP_THEMES: bright backgrounds, dark text, purple accent
- Selectable in Settings → Appearance alongside existing dark/midnight/ocean/forest/warm themes

### Auto-Save / Crash Recovery
- Periodic recovery snapshots saved to `~/.paparaz/recovery/` (configurable interval, default 60s)
- On startup: detects recovery files, offers restore via QMessageBox
- Recovery files cleaned up on normal editor close
- Settings: auto-save interval spinbox + crash recovery toggle in Behavior page

### Bug Fixes
- Fix: editors hidden before capture now properly re-shown after successful capture (not just on cancel)
- Fix: PNG save now respects compression level setting

---

## [0.9.5] - 2026-03-31

### Properties Panel — Complete UX Overhaul

#### Wider, Unclipped Layout
- `PANEL_WIDTH` raised from 186 → 260 px — all rows now have breathing room; nothing is clipped
- Cap / Join rows changed from a cramped single side-by-side layout to two stacked rows (`Cap: [combo]`, `Join: [combo]`), each with a full-width dropdown

#### New Header Bar (24 px → 40 px)
- **Title label** (13 px bold): shows "Properties" by default; dynamically updates to the selected element type ("Text", "Rectangle", "Arrow", etc.) when an element is selected
- **📌 Pin toggle** (40 × 28 px, clearly labeled): checked = panel stays open always (pinned); unchecked = panel auto-hides 3 s after deselect (auto). Tooltip explains both states. Replaces the tiny ambiguous cycle-mode button.
- **✕ Close** (28 × 28 px): hides the panel and sets hidden mode. Tooltip explains how to re-open via the grip tab on the canvas edge.
- Drag grip `⠿` on the left with `SizeAllCursor` and tooltip.
- All header buttons re-skinned on theme change to match current accent.

#### Element Preview Strip
- 80 px strip between the header and the property controls
- Renders the selected element scaled and centered using its own `paint()` method — correct colors, stroke weight, shadow, and rotation
- Shows "No selection" placeholder when nothing is selected
- Updates automatically whenever an element is selected or deselected

#### Format Buttons — Labeled
- Bold / Italic / Underline / Strikethrough buttons now show **B**, **I**, **U**, **S̶** text labels (matching font style) instead of being icon-only — users can now tell what they do without hovering
- Alignment buttons show `≡←`, `≡`, `≡→` symbols; direction buttons show `LTR` / `RTL` text
- All format buttons enlarged to 24–28 px

#### Recent Colors Section
- "RECENT COLORS" section title added above the palette with a tooltip: "Left-click to set foreground color · Right-click to set background color"
- Users no longer encounter an unlabeled row of checkerboard-backed swatches with no context

### Panel Initial Placement
- On first show the panel now appears **to the right of the editor window** (10 px gap) rather than overlapping the canvas working area
- Falls back to the left side if the right side has insufficient screen space

### Properties — Dependent Controls & Consolidation
- Shadow: single linked **Blur** slider by default; `≠` unlink button reveals independent **Blur X** / **Blur Y** sliders; auto-unlinks when an element with different X/Y blur values is loaded
- Text background and outline color swatches are **disabled (30% opacity)** when their toggle is OFF — visual affordance that they have no effect
- Outline width row **hides entirely** when outline is toggled OFF

### QCheckBox → Toggle Buttons (All Surfaces)
- Every `QCheckBox` in `side_panel.py` replaced with `QToolButton#toggleBtn` (checkable, labeled, 22 px tall) — eliminates confusion between color swatches and checkboxes that were indistinguishable side by side
- Every `QCheckBox` in `settings_dialog.py` replaced with `QPushButton#toggleSetting` (full-width, styled pill, left-aligned text, purple left-border when checked)

### Text Tool — Major Enhancement
- **Click-to-position cursor**: clicking inside an existing text element moves the cursor to the exact character position (maps click X/Y through `_build_visual_lines()` → line index → character offset, alignment-aware)
- **Resize handle**: purple grip on the right edge of the text box; drag horizontally to change the box width live
- **Up/Down navigation**: arrow keys move across visual lines preserving a `_nav_x_hint` (x-coordinate memory like a real text editor)
- **Word navigation**: Ctrl+Left/Right jumps word boundaries
- **Home/End**: moves to visual line start/end; Ctrl+Home/End jumps to document start/end
- **Font size** max raised from 72 → 120 pt
- **Hover preview**: shows "Aa" in the current font/color/style instead of a generic "T"

### Window Border Contrast
- Editor `paintEvent` draws multi-layer outline: outer dark shadow rings (black 100/50 alpha) + dark fill + theme accent border — window is now clearly distinct from any desktop background color

### Side Panel — Auto-Show on Tool Switch
- Panel auto-shows (if not in hidden mode) when switching to a tool that has configurable properties (any tool with color, stroke, effects, text, mask, number, stamp, or fill sections)

---

## [0.9.4] - 2026-03-31

### Precision Movement (Arrow Keys)
- Arrow keys move selected element(s) by **1 px** per press; **Shift + arrow** moves **10 px**
- Works for both single and multi-select; each move is undoable as a single Command
- Supported on all element types via `move_by(dx, dy)`

### Selection UX Overhaul
- **Transparent selection overlay** — removed the opaque tinted fill; bounding box is now a thin 1px border only
- **Smaller square handles** — resize handles reduced from 12 px circles to 7 px white squares with accent border
- **Theme-aware accent** — selection border, handles, and rotation handle all use the current app theme accent color
- `set_selection_accent(hex)` module-level function updates `AnnotationElement.SEL_COLOR` at runtime
- Called automatically on every theme change and on editor startup

### Eraser Hover — Theme Aware
- Eraser circle hover preview now uses the app theme accent color instead of hardcoded red
- Consistent with selection accent, adapts instantly on theme switch

### Settings Dialog — Major Overhaul
- **Sidebar** — replaced emoji+text items with custom per-item widgets: 3 px color indicator bar + bold label + subdued subtitle
- **Appearance page** — visual `QToolButton` theme cards replace the flat dropdown; each card shows a 3-band color swatch (bg / accent / fg) with the theme name below; live preview on click
- **Tools page** — line width and font size now use a linked `QSlider` + `QSpinBox` pair for drag-or-type editing
- **Shortcuts page** — fixed shortcut labels now use styled `keyBadge` pill labels; multi-key combos shown as separate badge chips
- `_BASE` stylesheet is now correctly applied (was defined but unused since v0.9.2); provides sidebar, card, badge, and slider styles on top of the theme-aware `build_dialog_qss` layer

### Stamps — 32 Total (+16 New)
- **10 transparent-background variants** — same graphic as existing stamps, solid background removed:
  `check_t`, `cross_t`, `ok_t`, `bad_t`, `info_t`, `question_t`, `thumbsup_t`, `thumbsdown_t`, `priority_t`, `bug_t`
- **6 new utility text stamps** — dashed/solid outlined text labels for workflow annotation:
  `wip` (dashed orange), `draft` (dashed gray), `todo` (blue), `done` (green), `fix` (red), `new` (orange starburst)

### Docs Cleanup
- Removed all remaining Flameshot references from `PLAN.md`, `ARCHITECTURE.md`, `UI_SPEC.md`, `CHANGELOG.md`

---

## [0.9.3] - 2026-03-30

### Curved Arrow Tool (Q)
- **`CurvedArrowElement`** — quadratic Bezier curve with an arrowhead at the end point
- Three-click workflow: click to set start → click to set end → move mouse to bend the curve → click to commit
- Arrowhead aligns to the curve tangent at the end point (control → end direction), not the raw start→end angle
- Escape cancels at any phase; Enter commits during the control-point phase
- Phase indicator dots and hint labels drawn near the cursor during each phase
- Full shadow, opacity, stroke width/style, and effects panel support
- Keyboard shortcut **Q**

### Eyedropper Tool (I)
- **`EyedropperTool`** — samples any pixel from the screen (screenshot + drawn annotations)
- Left-click → set foreground colour; right-click → set background colour
- Live magnifying loupe: 80 px circle, 10× zoom, contrasting ring, crosshair, hex colour label beneath
- Samples from `QScreen.grabWindow(0, x, y, 1, 1)` (composed screen, not canvas pixmap)
- Auto-returns to the previously active tool after picking
- Sampled colour added to recent colours palette automatically
- Keyboard shortcut **I**

### Text Outline / Stroke
- `TextElement` gains `stroke_enabled`, `stroke_color`, `stroke_width` fields
- Draw order: shadow → stroke path → fill text (ensures stroke is visible under fill)
- Stroke drawn via `QPainterPath.addText()` + `strokePath()` with `stroke_width * 2` (centred stroke, outer half visible)
- Side panel TEXT section: "Outline" checkbox + colour swatch + width slider (0.5–10 px in 0.5 steps)
- Syncs from selected TextElement when re-editing; serialized to `to_dict()`

### Installer: Force-Kill Before Install
- `PrepareToInstall()` Pascal function in Inno Setup script runs before file copy
- First `taskkill /im PapaRaZ.exe` (graceful), waits 1s, then `taskkill /f /im PapaRaZ.exe` (force)
- Prevents "file in use" errors when upgrading over a running instance

### In-App Update Downloader
- `UpdateDownloadDialog` replaces the old "Open Browser" link
- Streams the installer in 64 KB chunks via `urllib.request`, shows a progress bar
- "Install Now" button: launches installer detached (`subprocess.Popen DETACHED_PROCESS`) then calls `QApplication.quit()`
- Falls back to "Open Browser" if download fails

### Release Pipeline Fix
- `release.bat` now reads version dynamically from `pyproject.toml` via `findstr`
- Step 6: loads `GH_TOKEN` from `.env`, finds `gh.exe`, uploads installer to GitHub release with `--clobber`
- Prevents missing-installer on GitHub releases (was omitting the `.exe` asset)

---

## [0.9.2] - 2026-03-30

### Rotation-Aware Resize (All Element Types)
- **Rect / Ellipse**: Two-step algorithm — (1) inverse-rotate canvas delta into element-local frame, (2) translate rect so the opposite (anchor) corner stays fixed in canvas space. Previously, dragging any edge deformed all sides.
- **Line / Arrow**: Screen-space solution — rotate endpoints to screen coords, move only the dragged endpoint, recompute the midpoint (new rotation center), inverse-rotate back. The anchor endpoint is mathematically guaranteed not to drift.
- **Pen / Brush**: Same local-delta + anchor correction as Rect/Ellipse applied to the entire scaled point set.

### Highlight Tool — True Highlighter Effect
- `CompositionMode_Multiply` blend mode: `result = src × dst` — background always 100% visible, highlights feel like a real marker
- Default width raised to **16 px** (was 3 px)
- Default color **#FFFF00** (fully opaque yellow) — transparency comes from the Multiply blend, not from alpha
- Independent defaults from other tools; set only on first activation so user changes persist

### Shadow — Independent Blur Axes
- `Shadow.blur_radius` split into `blur_x: float` and `blur_y: float` — directional shadow spread (e.g. wide horizontal shadow with tight vertical)
- Side panel shows **BlX** and **BlY** sliders (0-40) instead of a single Blur slider
- `_scale_blur(pix, rx, ry)`: separate horizontal/vertical downscale passes for anisotropic blur
- `canvas.set_shadow_blur_x()` / `set_shadow_blur_y()` setters added
- Backward-compatible settings migration: old `shadow_default_blur` maps to both axes on load

### 0px Stroke — Borderless Filled Shapes
- `_make_pen()` returns `QPen(Qt.PenStyle.NoPen)` when `line_width <= 0`
- Width slider minimum changed from 1 → 0 px
- Enables fully borderless filled rectangles and ellipses

### Fill Opacity Fix
- Filled shapes no longer appear semi-transparent at 100% opacity
- Root cause: `QColor` from `background_color` hex string could carry an embedded alpha value; `c.setAlpha(255)` now strips it before setting the fill brush
- Element-level opacity slider remains the sole transparency control

### Recent Colors Palette
- `RecentColorsPalette` widget added to side panel COLOR section
- Left-click a swatch → set foreground; right-click → set background
- Palette auto-populated as you pick colors via the Fg / Bg / shadow / text-bg pickers
- Persisted to `~/.paparaz/settings.json` via `recent_colors` field

### Side Panel — Reorganized Layout
- **STROKE section** merges width slider + LINE STYLE (dash/cap/join) as a collapsible sub-row — only one section heading instead of two
- **Shadow color** button moved inline with the Shadow checkbox — no extra row
- **BlX / BlY** sliders replace single Blur slider within the shadow details block
- All sections use `spacing=2` for tighter, more scannable layout
- Width slider minimum → 0 (borderless fill)

### HiDPI Toolbar Icons
- `svg_to_icon()` now creates both 1× and 2× pixmaps (`setDevicePixelRatio(2.0)`) and calls `QIcon.addPixmap()` for both
- Render hints: `Antialiasing + SmoothPixmapTransform` on both passes
- Icons are sharp on 125 %, 150 %, 200 % display scaling

### Transparent Toolbar Buttons
- Default button background changed from `#270032` to `transparent` — only the canvas has a background fill
- Hover and active states retain purple accent tint

### Theme Live Preview in Settings
- Settings dialog theme combo now re-styles both the dialog itself and the running editor window immediately on change (before clicking Save)
- `_on_theme_preview()` wired to `currentIndexChanged`

### Side Panel — Detach / Drag Fix
- `SidePanel(parent=None)` — panel is now a true OS-level top-level window, not a child of the editor
- Fixes: pressing the panel header to drag was triggering the editor's resize border filter (installed via `findChildren(QWidget)`)
- Panel coordinates use screen space directly; no more `mapFromGlobal` drift

### Bug Fixes
- `QWidget#editorRoot` CSS selector now works (was never matching — `setObjectName("editorRoot")` added to editor `__init__`)
- Toolbar per-widget `setStyleSheet` override fixed: `apply_theme()` re-applies QSS to every button individually
- `_record_shadow_attr` not recording `blur_x` / `blur_y` history: added undo recording to both setters

---

## [0.9.0] - 2026-03-30

### Application Icon
- `assets/paparaz.ico` — multi-resolution icon (16/24/32/48/64/128/256 px)
- Purple rounded-rectangle "Pz" design matching the app accent theme
- Generated by `scripts/make_icon.py` (Pillow, LANCZOS supersampled)
- Embedded in PyInstaller exe and Inno Setup installer

### Auto-Start on Login
- `utils/startup.py` — reads/writes `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`
- Settings dialog checkbox now reflects the real registry state (not just the saved setting)
- Saving settings immediately applies the registry change
- Works from both source (`python -m paparaz`) and installed exe (`sys.frozen` detection)

### Update Checker
- `utils/updater.py` — checks GitHub releases API for newer version
- Runs in a background `threading.Thread` 3 seconds after startup (non-blocking)
- Shows styled dialog with "Download" (opens browser) and "Later" buttons only when an update is found
- Network errors silently ignored; no impact on startup time

### PyInstaller / Build
- `paparaz.spec` updated: icon, winrt hidden imports, version info, excludes bloat packages
- `version_info.txt` — Windows exe metadata (FileDescription, ProductName, Copyright, version tuples)
- `build.bat` updated: 3-step script (icon → pip → pyinstaller), clearer output

### Inno Setup Installer
- `installer/paparaz_setup.iss` — full Windows installer script
- Installs to `Program Files\PapaRaZ`, creates Start Menu group
- Optional: Desktop shortcut, auto-start on login (checkbox during install)
- Uninstall removes registry startup entry automatically
- Guards against missing `dist\PapaRaZ.exe` with a clear error at start of install

### New Files
- `assets/paparaz.ico` — application icon
- `version_info.txt` — PyInstaller Windows version info
- `scripts/make_icon.py` — icon generator script
- `installer/paparaz_setup.iss` — Inno Setup installer script
- `src/paparaz/utils/startup.py` — Windows Registry auto-start helper
- `src/paparaz/utils/updater.py` — GitHub release update checker

---

## [0.8.0] - 2026-03-29

### Rotation System
- **Element rotation** fully wired: side panel rotation slider → `canvas.set_rotation()` → all element types
- `_apply_rotation()` fixed to use explicit `cx, cy` floats (PySide6 overload resolution for `painter.translate`)
- **LineElement** and **PenElement/BrushElement** paint with rotation via `painter.save/translate/rotate/restore` + `else` branch for zero rotation
- `contains_point()` on Line/Pen/Brush applies inverse rotation before hit-test

### Slice Tool Rotation Fix
- Correct rotated pixel extraction using inverse QPainter transform (translate+rotate, not AABB)
- Background erasure uses `QPolygonF` for the actual rotated polygon shape (not a bounding rectangle)
- Right-click or Enter to confirm slice; result inserted as axis-aligned `ImageElement`

### Crop Tool Rotation Fix
- `_transform_element_geom()` rewritten with correct per-type rules:
  - **Rect elements**: preserve size, move center via `t.map(r.center())`, adjust rotation by `-crop_rotation`
  - **Line/Arrow** (start/end coords): transform coordinates, keep rotation **unchanged** (coords already encode orientation — no double-counting)
  - **Pen/Brush** (points): transform all points, keep rotation unchanged
  - **Number** (position): transform position, adjust rotation

### App Themes
- `ui/app_theme.py` — 5 built-in themes: `dark`, `midnight`, `ocean`, `forest`, `warm`
- QSS templates with `{accent}`, `{bg1}`, `{bg2}`, `{fg}`, `{border}` placeholders
- `build_tool_qss()`, `build_panel_qss()`, `build_dialog_qss()` per-surface builders
- Theme selector combo added to Settings → General tab
- `EditorWindow.apply_app_theme(theme_id)` applies theme on startup and on settings change

### Shadow Blur Fix
- `QGraphicsBlurEffect` through `scene.render()` is unreliable in PySide6 — replaced with `_scale_blur()`
- `_scale_blur()`: three-pass downscale/upscale approximation of Gaussian blur (no Qt scene required)
- `_paint_shadow()` on all elements now uses `_scale_blur()` — blur visually correct across all tools

### Shadow Settings Defaults
- `AppSettings` gains: `shadow_default_offset_x`, `shadow_default_offset_y`, `shadow_default_blur`
- Settings dialog → General tab: DEFAULT SHADOW group with spinboxes for X, Y, blur
- New elements inherit shadow defaults from settings

### Context Menu (Right-Click on Elements)
- Right-click any element in Select tool → **Copy**, **Duplicate**, **Delete**
- Right-click empty canvas → **Paste** (element clipboard) or **Paste image from clipboard**
- `canvas.copy_element()`, `canvas.paste_element()`, `_clone_element()` helpers
- SelectTool `on_press/on_release` return early on right-click (handled by `contextMenuEvent`)

### Multi-Select
- **Rubber-band** drag on empty canvas selects all intersecting elements → group move, group delete
- **Shift+click** adds/removes individual elements from the selection group
- Multi-select stored in `SelectTool._multi_selected: list`; `canvas.select_multiple()` updates `selected` flags
- Group move is undoable (before/after geometry snapshots for all elements)
- Delete key removes all multi-selected elements

### OCR — Recognize Handwriting/Text
- Right-click on multi-selection → **Recognize text (OCR) [N objects]**
- Selected elements rendered to white pixmap (3× scale for OCR accuracy) via `_render_elements()`
- Windows OCR via `winrt` packages (no cloud, no API key) — works well for **printed text**
- Background thread (`threading.Thread`) + `_ResultBridge` QObject for non-blocking UI
- Result dialog: editable text box before committing; orange warning if OCR returns empty
- On confirm: original elements deleted, `TextElement` inserted at same position — fully undoable
- Graceful error messages if `winrt` packages not installed (with exact `pip install` commands)
- **Note:** Windows OCR (`Windows.Media.Ocr`) recognizes printed text only; handwriting recognition requires a different engine (EasyOCR or OpenAI Vision — deferred)

### Frameless Aero Editor
- Editor window is frameless, sized to the captured region
- Custom title bar with drag, minimize, close

### Exit Button Rename
- "Exit & Copy" button renamed to "Copy to clipboard & Exit"

### New Files
- `ui/app_theme.py` — Theme QSS builder (5 built-in themes)
- `ui/ocr.py` — Windows OCR integration (winrt, threading bridge, result dialog)

---

## [0.7.0] - 2026-03-29

### Adaptive Toolbar (Flow Layout)
- **Toolbar wraps to multiple rows** when editor window is narrow — no more hidden buttons
- All 22 buttons (13 tools + 9 actions) flow row-by-row based on available width
- Extra visual gap separates tool group from action group
- Overflow "⋯" menu appears only when >3 rows would be needed (last resort)
- Toolbar takes full editor width; `heightForWidth()` ensures correct vertical allocation
- `_compute_flow()` helper cleanly computes per-button positions

### Side Panel — Pin / Auto-Hide / Hidden Modes
- **Header bar** added to side panel with mode toggle button + close button
- **Three modes** — cycle with header button or programmatically:
  - `auto` — shows on element select, auto-hides 3 seconds after deselect
  - `pinned` — always visible regardless of selection
  - `hidden` — always hidden; grip tab shown on canvas left edge
- `SidePanel.mode_changed` signal notifies editor of mode changes
- `SidePanel.on_element_selected(elem)` method centralizes show/hide logic
- `QTimer` (3 s, single-shot) drives auto-hide in `auto` mode

### Panel Grip Tab
- Small purple vertical tab appears on canvas left edge when panel is in `hidden` mode
- Clicking grip tab switches panel back to `auto` mode and reveals it
- Positioned dynamically in `EditorWindow.resizeEvent()`

### Bug Fixes / Improvements
- Single-monitor capture only (monitor under cursor) — prevents DPI distortion on multi-monitor setups
- `setMouseTracking(True)` on `RegionSelector` — fixes stuck crosshair cursor
- Handle hit-test now uses `SEL_PADDING=5` matching paint positions — resize handles work correctly
- Property changes update selected element immediately (no need to deselect and reselect)

---

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
- **Circular handles** (12px, purple fill, white outline) 
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

### UI Overhaul
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
