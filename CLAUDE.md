# CLAUDE.md — PapaRaZ Development Context

## Quick Start
- `python -m pytest tests/ -x -q` — run all tests (653+, ~10s)
- `python -m paparaz` — run the app from source
- Version bumps: update `src/paparaz/__init__.py`, `pyproject.toml`, `src/paparaz/utils/updater.py`

## Architecture
- PySide6/Qt desktop app, Windows-only (Win32 ctypes for capture, hotkeys, cursor)
- Element-based object model — every annotation is a discrete selectable object
- Tools in `tools/` (BaseTool subclasses), elements in `core/elements.py`
- Editor window is frameless with custom chrome (paintEvent, opaque palette)

## Key Patterns
- `canvas.selected_element` — committed element currently selected
- `_text_tool._active_text` — text element in preview/editing mode (NOT in selected_element)
- Side panel property changes must route to BOTH selected_element AND active preview element
- `auto_size()` must be called after any change affecting text layout (font, bold, size)
- `_rotate_point(pt, center, -rotation)` to un-rotate canvas coords into element-local space
- Elements use `ElementStyle` dataclass; `_make_font()` builds QFont from style

## Gotchas
- **Alt key on Windows**: Alt modifier gets intercepted by OS even on frameless windows. Use Shift or Ctrl instead.
- **replace_all=true**: Dangerous when the target string is a substring of other identifiers (e.g., constant names vs instance vars). Always verify scope.
- **QFont(-1)**: Default QFont() gives point size -1. Always guard with `max(1, size)`.
- **WA_TranslucentBackground**: Causes resize flickering on Windows due to DWM compositor clearing. Use opaque palette instead.
- **DPI multi-monitor**: Qt logical pixels != physical pixels. Use Win32 EnumDisplayMonitors for true coordinates.
- **Preview vs committed**: During tool editing, element is in preview (set_preview), not in canvas.elements. Property signals from side panel won't reach it via canvas.selected_element.

## Testing
- Tests in `tests/test_*.py`, 653+ tests across 4 files
- Tests use QApplication singleton — `conftest.py` handles setup
- Always run tests after changes: `python -m pytest tests/ -x -q`
- Test counts to update when adding tools: N_TOOLS, N_TOTAL in test_ui_ux.py

## Release Process
1. Bump version in 3 files (see Quick Start)
2. Update README.md badge, CHANGELOG.md, PLAN.md
3. `git commit`, `git tag v{VERSION}`, `git push origin main --tags`
4. `GH_TOKEN=... gh release create v{VERSION} --title "..." --notes "..."`

## File Layout
- `src/paparaz/core/elements.py` — all element types (TextElement, ImageElement, etc.)
- `src/paparaz/tools/special.py` — TextTool, FillTool, NumberingTool, StampTool, etc.
- `src/paparaz/tools/drawing.py` — PenTool, LineTool, RectTool, MeasureTool, etc.
- `src/paparaz/ui/editor.py` — main editor window, signal wiring, save/export
- `src/paparaz/ui/overlay.py` — capture region selector with magnifier loupe
- `src/paparaz/ui/side_panel.py` — floating properties panel
- `src/paparaz/app.py` — app controller (tray, hotkeys, capture orchestration)
