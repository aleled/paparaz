# PapaRaZ Test Plan

## Current State
- **653 tests** across 4 files, all passing (~14s)
- Framework: pytest + PySide6 headless widget testing
- No external display or browser required
- See `docs/QA_FINDINGS.md` for bugs found and issue backlog

### Test Files
| File | Tests | Focus |
|------|-------|-------|
| `test_tools_and_properties.py` | 121 | Unit tests — element geometry, tool creation, property undo, canvas ops, clipboard, snap engine |
| `test_functional.py` | 296 | Integration — tool switching, element lifecycle, text editing, copy/paste, undo/redo, layers, crop, recovery, slice, eyedropper, magnifier, export, canvas resize, TOOL_SECTIONS |
| `test_ui_ux.py` | 143 | Widget — toolbar layout, editor structure, side panel modes, settings dialog, layers panel, theme system |
| `test_qa_extended.py` | 93 | Extended QA — smoke, boundary, negative, data integrity, state machine, performance, accessibility, signal safety, Phase B components, from_dict roundtrips, fix verification |

---

## Phase A: High Priority (Headless-Testable)

### A1. SliceTool (`special.py:1106-1292`)
- Activation / deactivation
- Region drawing (mousePress → mouseDrag → mouseRelease)
- Slice export (mocked file dialog)
- Cancel via Escape
- Multiple slices on same canvas

### A2. EyedropperTool (`special.py:1293-1462`)
- Color pick from canvas pixel
- Foreground vs background pick mode
- Auto-return to previous tool after pick
- Loupe rendering (paint method)
- Edge-of-canvas behavior

### A3. MagnifierTool (`special.py:1464-1517`)
- MagnifierElement creation
- Source rect → zoomed circle rendering
- Resize handles
- Move and delete
- Zoom factor property

### A4. CanvasResizeDialog
- Dialog creation and default values
- Width/height spinbox validation
- Aspect ratio lock toggle
- Apply produces correct canvas dimensions
- Cancel leaves canvas unchanged

### A5. SidePanel Deep Coverage (`side_panel.py`)
- All TOOL_SECTIONS mappings (every tool type shows correct sections)
- Color picker signal wiring
- Opacity slider range and signal
- Shadow section toggle and sub-widgets
- Line cap / join / dash dropdowns
- Font combo box for text tool

### A6. SVG Export & render_final (`export.py`)
- Export produces valid SVG XML
- All element types render to SVG
- render_final composites background + elements
- render_final respects element visibility
- render_final respects element opacity

---

## Phase B: Medium Priority

### B1. RegionSelector (`overlay.py`)
- Overlay covers full screen area
- Click-drag creates selection rectangle
- Escape cancels and closes overlay
- Selection signal emits correct QRect
- Multi-monitor coordinate handling

### B2. PinWindow
- Always-on-top flag set
- Displays provided pixmap
- Close on Escape
- Right-click context menu
- Drag to reposition

### B3. ColorPalette Widget
- Recent colors list population
- Color click emits signal
- Clear button empties palette
- Max palette size respected
- Persistence to settings

### B4. TrayIcon
- Icon creation without crash
- Menu items present (Capture, Open, Settings, Exit)
- Delay capture submenu (3s, 5s, 10s)
- Recent captures submenu

### B5. Theme Preset Builders (`app_theme.py`)
- All 5 themes parse without error
- Theme keys are consistent across all themes
- Applying theme updates widget stylesheets
- Theme switch preserves element state

---

## Phase C: Low Priority / Platform-Dependent

### C1. Capture Module (`capture.py`) — requires display
### C2. Monitor Detection (`monitors.py`) — platform-specific
### C3. App Lifecycle (`app.py`) — integration, needs tray
### C4. OCR (`winrt`) — Windows-only, needs winrt runtime
### C5. Updater (`updater.py`) — needs network
### C6. Startup / Icons / Stamps — trivial, low risk

---

## Test Conventions

### Helpers & Stubs (defined in each test file)
- **`make_canvas(w, h)`** — headless AnnotationCanvas with white QPixmap
- **`make_editor(w, h)`** — full EditorWindow without display
- **`_FakeEvent`** — left-click mouse stub (no modifiers)
- **`_ShiftEvent`** — left-click + Shift stub
- **`_RightClickEvent`** — right-click stub
- **`click(tool, pos)`** — press + release at pos
- **`drag(tool, start, end)`** — press at start, move to end, release
- **`key(tool, qt_key, text, mods)`** — simulate keypress via QKeyEvent
- **Settings isolation**: `SettingsManager(Path(tempfile.mktemp(suffix=".json")))`
- **Recovery isolation**: `monkeypatch.setattr(recovery, "RECOVERY_DIR", Path(tmpdir))`

### Constructor Gotchas (CRITICAL for future tests)

These caused repeated failures — always use keyword args:

```python
# Elements
RectElement(QRectF(...), filled=True, style=ElementStyle())   # NEVER positional style
EllipseElement(QRectF(...), filled=False, style=ElementStyle())
PenElement(style=ElementStyle())        # points via add_point(), NOT constructor
BrushElement(style=ElementStyle())      # same as PenElement (subclass)
TextElement(QPointF(x, y), "text")      # position is QPointF, NOT QRectF
StampElement("check", QPointF(x, y), 32)  # (stamp_id, position, size)
MagnifierElement(source_rect, display_rect, zoom=2.0)
NumberElement(QPointF(x, y), number)

# UI components
LayersPanel()                           # then panel.set_canvas(canvas)
CanvasResizeDialog(current_w, current_h)
RegionSelector(screenshot_pixmap, qscreen)

# Canvas API
canvas.copy_element(elem)              # NOT copy_selected()
canvas.paste_element()                 # NOT paste()
canvas.paint_annotations(painter)      # NOT _paint_elements()
canvas.set_tool(tool)                  # crashes on None — no guard

# Editor
editor._multi_toolbar                  # NOT _toolbar
editor._canvas

# Toolbar
toolbar._buttons                       # all buttons (list)
toolbar.top_strip / right_strip / bottom_strip  # NOT _top_strip

# Settings
settings.app_theme                     # NOT editor.theme
settings.theme                         # separate field (legacy?)

# CurvedArrowTool phases
CurvedArrowTool._PHASE_IDLE = 0       # int constants, NOT strings
CurvedArrowTool._PHASE_END = 1
CurvedArrowTool._PHASE_CTRL = 2

# History
canvas.history.can_undo                # property, NOT method()
```

### Rules
1. Use `isHidden()` not `isVisible()` for widgets in hidden parent containers
2. Use keyword args for `filled=` and `style=` on RectElement/EllipseElement
3. Keep tests headless — no `show()`, no `QApplication.exec()`
4. Each test class gets its own canvas/editor instance
5. Clean up temp files in teardown
6. For filled shapes that need center-click selection: set `canvas._filled = True` before drawing

### Test File Responsibilities

| File | When to add tests |
|------|-------------------|
| `test_tools_and_properties.py` | New element types, tool instantiation, property persistence, snap/geometry |
| `test_functional.py` | Tool workflows, element lifecycle, undo/redo, canvas operations, export |
| `test_ui_ux.py` | New UI widgets, dialog structure, side panel sections, toolbar changes |
| `test_qa_extended.py` | Smoke/boundary/negative/stress tests, state machines, serialization, Phase B+ |

### Adding Tests for New Features
When implementing a new feature:
1. Add unit tests for the new element/tool class in `test_tools_and_properties.py`
2. Add functional interaction tests in `test_functional.py`
3. Add widget/UI tests in `test_ui_ux.py` if new UI components are introduced
4. Add a smoke test in `test_qa_extended.py` for the critical path
5. Add boundary tests for edge cases (empty, zero-size, max values)
6. Run full suite: `python -m pytest tests/ -v --tb=short`
7. Target: maintain >90% line coverage on testable modules

---

## Run Commands

```bash
# Full suite
python -m pytest tests/ -v --tb=short

# Single file
python -m pytest tests/test_functional.py -v --tb=short

# Single class
python -m pytest tests/test_functional.py::TestCurvedArrowTool -v

# With coverage (requires pytest-cov)
python -m pytest tests/ --cov=src/paparaz --cov-report=term-missing
```

---

## Recommendations (from QA findings)

### Priority 1 — Do before v1.0
1. **Add `from_dict()` to all element types** — Without this, annotations can't be saved/restored from files. This blocks file format support and session recovery from JSON.
2. **Add history depth limit** — After long sessions, undo closures retain old pixmap references. Add a configurable max (e.g., 100) to prevent memory growth.
3. **Guard `set_tool(None)` and `copy_element(None)`** — Two one-line defensive fixes that prevent crashes.

### Priority 2 — Quality of life
4. **Eyedropper pixmap fallback** — Read from `canvas._background` directly instead of `screen.grabWindow()`. Makes the tool testable and avoids screen-grab issues on multi-monitor setups.
5. **Color validation in ElementStyle** — Reject invalid color strings at construction time rather than silently producing invalid QColors.

### Priority 3 — Future features
6. **Keyboard canvas navigation** — Tab to cycle elements, arrow keys to nudge. Important for accessibility.
7. **Rotated slice visual QA** — Needs manual testing on real display. Consider adding a golden-image test.

See `docs/QA_FINDINGS.md` for full details on each issue.

---

**Last updated**: 2026-04-02
**Version**: 0.9.7
