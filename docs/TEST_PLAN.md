# PapaRaZ Test Plan

## Current State
- **625 tests** across 4 files, all passing (~11s)
- Framework: pytest + PySide6 headless widget testing
- No external display or browser required
- See `docs/QA_FINDINGS.md` for bugs found and issue backlog

### Test Files
| File | Tests | Focus |
|------|-------|-------|
| `test_tools_and_properties.py` | 121 | Unit tests — element geometry, tool creation, property undo, canvas ops, clipboard, snap engine |
| `test_functional.py` | 227 | Integration — tool switching, element lifecycle, text editing, copy/paste, undo/redo, layers, crop, recovery, slice, eyedropper, magnifier, export, canvas resize, TOOL_SECTIONS |
| `test_ui_ux.py` | 143 | Widget — toolbar layout, editor structure, side panel modes, settings dialog, layers panel, theme system |
| `test_qa_extended.py` | 134 | Extended QA — smoke, boundary, negative, data integrity, state machine, performance, accessibility, signal safety, Phase B components |

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

### Patterns
- **Event stubs**: `_FakeEvent(x, y)` / `_ShiftEvent(x, y)` for mouse simulation
- **Helpers**: `click(tool, x, y)`, `drag(tool, x1, y1, x2, y2)`, `key(tool, key, mods)`
- **Editor factory**: `make_editor(w, h)` for full EditorWindow without display
- **Settings isolation**: `SettingsManager(Path(tempfile.mktemp(suffix=".json")))`
- **Recovery isolation**: monkeypatch `RECOVERY_DIR` to temp directory

### Rules
1. Use `isHidden()` not `isVisible()` for widgets in hidden parent containers
2. Use `filled=True, style=ElementStyle()` for RectElement — never pass style as positional arg
3. Keep tests headless — no `show()`, no QApplication.exec()
4. Each test class gets its own canvas/editor instance
5. Clean up temp files in teardown

### Adding Tests for New Features
When implementing a new feature:
1. Add unit tests for the new element/tool class in `test_tools_and_properties.py`
2. Add functional interaction tests in `test_functional.py`
3. Add widget/UI tests in `test_ui_ux.py` if new UI components are introduced
4. Run full suite: `python -m pytest tests/ -v --tb=short`
5. Target: maintain >90% line coverage on testable modules

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

**Last updated**: 2026-04-02
**Version**: 0.9.6
