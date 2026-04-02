# PapaRaZ QA Findings Report

**Date**: 2026-04-02
**Version**: 0.9.7
**Test Suite**: 653 tests across 4 files, all passing (~14s)

---

## Summary

Comprehensive QA testing covering 10+ test types (unit, functional, UI/UX, smoke, boundary, negative, data integrity, state machine, performance, accessibility, signal safety, Phase B components) uncovered **3 confirmed bugs** and **8 issues/improvements**. All actionable issues have been resolved.

---

## Bugs Found & Fixed

### BUG-1: RectElement/EllipseElement positional arg trap in side_panel.py (FIXED)
- **Severity**: Medium
- **Location**: `src/paparaz/ui/side_panel.py:1313,1318`
- **Issue**: `RectElement(QRectF(...), style)` passes ElementStyle as the `filled` parameter (expects bool).
- **Impact**: Side panel preview elements rendered with default style instead of user's chosen style.
- **Fix**: Changed to `RectElement(QRectF(...), filled=self._filled_check.isChecked(), style=style)`. Same for EllipseElement.
- **Status**: **FIXED** and tested.

### BUG-2: `set_tool(None)` crashes with AttributeError (FIXED)
- **Severity**: Low
- **Location**: `src/paparaz/ui/canvas.py` — `set_tool()` method
- **Issue**: No guard against `None` being passed as a tool.
- **Fix**: Added `if tool is None: return` guard at top of `set_tool()`.
- **Status**: **FIXED** and tested (`test_set_tool_none_is_noop`).

### BUG-3: PenElement constructor mismatch vs test assumptions (API clarity)
- **Severity**: Info
- **Issue**: Constructor signatures are non-obvious without reading source. Documented in TEST_PLAN.md "Constructor Gotchas" section.
- **Status**: **DOCUMENTED** — no code change needed.

---

## Issues / Improvements — Resolution Status

### ISSUE-1: No `from_dict()` deserialization — **FIXED**
- **Priority**: High
- **Fix**: Added `from_dict()` classmethod to all 12 element types + `element_from_dict()` factory with `_ELEMENT_CLASS_MAP` type registry.
- **Verification**: 20+ roundtrip tests in `TestFromDictRoundtrip`.

### ISSUE-2: No history depth limit — **ALREADY IMPLEMENTED**
- **Priority**: Medium (was)
- **Finding**: `HistoryManager` already has `max_size=200` depth limiting. No action needed.
- **Status**: Not a bug.

### ISSUE-3: `canvas.copy_element(None)` crashes — **FIXED**
- **Priority**: Low
- **Fix**: Added `if elem is None: return` guard in `copy_element()`.
- **Verification**: `test_copy_element_none_is_noop`.

### ISSUE-4: Toolbar buttons not distributed until layout triggered
- **Priority**: Info
- **Status**: Works correctly when displayed. No action needed.

### ISSUE-5: EyedropperTool headless limitation — **FIXED**
- **Priority**: Medium
- **Fix**: Added `_sample_color_from_pixmap()` fallback that reads directly from `canvas._background`. `_sample_color()` and `_sample_area()` now try screen grab first, then fall back to background pixmap.
- **Verification**: `test_eyedropper_fallback_reads_background`.

### ISSUE-6: Invalid color strings accepted by ElementStyle — **FIXED**
- **Priority**: Low
- **Fix**: Added `_validate_color()` function and `__post_init__()` on `ElementStyle`. Invalid colors fall back to defaults (`#FF0000` for foreground, `#FFFFFF` for background).
- **Verification**: `test_color_validation_invalid_falls_back`, `test_color_validation_invalid_bg_falls_back`.

### ISSUE-7: SliceTool rotated path untestable headless
- **Priority**: Info
- **Status**: Axis-aligned path is fully tested. Rotated slices need manual visual QA.

### ISSUE-8: No keyboard-only canvas navigation
- **Priority**: Low
- **Status**: Future feature — Tab to cycle elements, arrow keys to nudge. Not yet implemented.

---

## Test Coverage by Type

| Test Type | File | Tests | Findings |
|---|---|---|---|
| Unit | `test_tools_and_properties.py` | 121 | — |
| Functional | `test_functional.py` | 296 | BUG-1 |
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
| Fix Verification | `test_qa_extended.py` | 29 | — |

---

## Remaining Backlog

1. **ISSUE-9**: Error dialogs appear behind always-on-top windows — OS error popups (e.g., "Unsupported 16-Bit Application") render behind PapaRaZ's always-on-top editor/installer, making them invisible. Investigate using `Qt.WindowStaysOnTopHint` management or bringing error dialogs to front.
2. **ISSUE-10**: Platform compatibility — app is Windows-only (Win32 capture, winrt OCR, registry auto-start). Consider cross-platform abstractions or at minimum document platform requirements clearly. Add platform detection guards for graceful failures on unsupported OS.
3. **ISSUE-8**: Keyboard canvas navigation — accessibility improvement (future feature)
4. **ISSUE-7**: Manual visual QA for rotated slices — verification task
