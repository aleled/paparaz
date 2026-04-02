# PapaRaZ QA Findings Report

**Date**: 2026-04-02
**Version**: 0.9.6
**Test Suite**: 625 tests across 4 files, all passing (~11s)

---

## Summary

Comprehensive QA testing covering 10 test types (unit, functional, UI/UX, smoke, boundary, negative, data integrity, state machine, performance, accessibility, signal safety, Phase B components) uncovered **3 confirmed bugs** and **8 issues/improvements** worth addressing.

---

## Bugs Found & Fixed

### BUG-1: RectElement/EllipseElement positional arg trap in side_panel.py (FIXED)
- **Severity**: Medium
- **Location**: `src/paparaz/ui/side_panel.py:1313,1318`
- **Issue**: `RectElement(QRectF(...), style)` passes ElementStyle as the `filled` parameter (expects bool). Constructor is `RectElement(rect, filled=False, style=None)`.
- **Impact**: Side panel preview elements rendered with default style instead of user's chosen style. Shadow, color, and line width settings were silently ignored for preview rectangles and ellipses.
- **Fix**: Changed to `RectElement(QRectF(...), filled=self._filled_check.isChecked(), style=style)`. Same fix for EllipseElement.
- **Status**: Fixed and tested.

### BUG-2: `set_tool(None)` crashes with AttributeError (DOCUMENTED)
- **Severity**: Low
- **Location**: `src/paparaz/ui/canvas.py` — `set_tool()` method
- **Issue**: No guard against `None` being passed as a tool. Calling `set_tool(None)` triggers `AttributeError` when trying to access tool attributes.
- **Impact**: Only triggers if code explicitly passes None — unlikely in normal use but a defensive coding gap.
- **Status**: Documented in test (`test_set_tool_none_crashes`). Not fixed — low priority.

### BUG-3: PenElement constructor mismatch vs test assumptions (API clarity)
- **Severity**: Info
- **Issue**: PenElement takes `style` as first arg, not `points`. Points are added via `add_point()`. TextElement takes `QPointF` position, not `QRectF`. StampElement takes `(stamp_id, position, size)`, not `(stamp_id, rect)`.
- **Impact**: No production bug — only affected test code. But the constructors are non-obvious without reading source.

---

## Issues / Improvements to Tackle

### ISSUE-1: No `from_dict()` deserialization (Missing Feature)
- **Priority**: Medium
- **Details**: All 12 element types implement `to_dict()` but none have `from_dict()`. Elements serialize to JSON but cannot be reconstructed from that JSON.
- **Impact**: Cannot restore annotations from saved JSON files. Recovery module saves pixmap snapshots only.
- **Recommendation**: Add `from_dict()` class methods to all element types. Create an element factory: `element_from_dict(d: dict) -> AnnotationElement`.

### ISSUE-2: No history depth limit (Memory Risk)
- **Priority**: Medium
- **Details**: `HistoryManager` accepts unlimited commands. After 500+ operations, all undo/redo closures remain in memory.
- **Impact**: Extended editing sessions could consume significant memory from retained background pixmap references in undo closures.
- **Recommendation**: Add a configurable max history depth (e.g., 100) with oldest entries discarded.

### ISSUE-3: `canvas.copy_element(None)` crashes (Defensive Gap)
- **Priority**: Low
- **Details**: `_clone_element(None)` is called, which crashes.
- **Recommendation**: Add `if elem is None: return` guard.

### ISSUE-4: Toolbar buttons not distributed until layout triggered
- **Priority**: Info
- **Details**: `MultiEdgeToolbar._buttons` holds all buttons, but strips' `_buttons` remain empty until `resizeEvent` distributes them. Headless tests can't verify strip distribution.
- **Recommendation**: No action needed — works correctly when displayed.

### ISSUE-5: EyedropperTool headless limitation
- **Priority**: Info
- **Details**: `_sample_color()` uses `screen.grabWindow()` which returns fallback white in headless mode. Color accuracy cannot be verified without a display.
- **Recommendation**: Consider adding a `_sample_from_pixmap()` fallback that reads directly from the canvas background pixmap instead of screen capture.

### ISSUE-6: Invalid color strings accepted by ElementStyle
- **Priority**: Low
- **Details**: `ElementStyle(foreground_color="not-a-color")` doesn't validate. `QColor("not-a-color").isValid()` returns False but no error is raised.
- **Recommendation**: Add color validation in `ElementStyle.__post_init__()` or in the UI layer.

### ISSUE-7: SliceTool rotated path untestable headless
- **Priority**: Info
- **Details**: Rotated slice extraction involves inverse-rotation pixel rendering. Visual correctness can only be verified with display. Axis-aligned path is fully tested.
- **Recommendation**: Manual visual QA for rotated slices.

### ISSUE-8: No keyboard-only canvas navigation
- **Priority**: Low
- **Details**: Tab order and keyboard-only element selection is not implemented. Users must use mouse for all canvas interaction.
- **Recommendation**: Future feature — add Tab to cycle through elements, arrow keys to move selected element.

---

## Test Coverage by Type

| Test Type | File | Tests | Findings |
|---|---|---|---|
| Unit | `test_tools_and_properties.py` | 121 | — |
| Functional | `test_functional.py` | 227 | BUG-1 |
| UI/UX Widget | `test_ui_ux.py` | 143 | — |
| Smoke | `test_qa_extended.py` | 7 | — |
| Boundary/Edge | `test_qa_extended.py` | 28 | — |
| Negative/Error | `test_qa_extended.py` | 14 | BUG-2, ISSUE-6 |
| Data Integrity | `test_qa_extended.py` | 17 | ISSUE-1 |
| State Machine | `test_qa_extended.py` | 16 | — |
| Performance | `test_qa_extended.py` | 7 | ISSUE-2 |
| Accessibility | `test_qa_extended.py` | 8 | ISSUE-8 |
| Signal Safety | `test_qa_extended.py` | 8 | — |
| Phase B | `test_qa_extended.py` | 29 | — |

---

## Backlog (Prioritized)

1. **ISSUE-1**: Add `from_dict()` to all element types — enables file save/restore
2. **ISSUE-2**: Add history depth limit — prevents memory leaks in long sessions
3. **BUG-2**: Guard `set_tool(None)` — simple defensive fix
4. **ISSUE-3**: Guard `copy_element(None)` — simple defensive fix
5. **ISSUE-5**: Eyedropper pixmap fallback — improves testability
6. **ISSUE-6**: Color validation — prevents silent invalid colors
7. **ISSUE-8**: Keyboard canvas navigation — accessibility improvement
8. **ISSUE-7**: Manual visual QA for rotated slices — verification task
