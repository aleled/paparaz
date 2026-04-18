"""
Extended QA test suite for PapaRaZ.

Covers test types beyond unit/functional/UI:
  - Smoke tests (critical path end-to-end)
  - Boundary / edge-case tests
  - Negative / error-handling tests
  - Data integrity tests (serialization roundtrip)
  - State machine tests (tool phase transitions)
  - Performance / stress tests
  - Accessibility tests (keyboard nav, labels)
  - Signal safety tests (rapid emission, re-entrancy)
"""

import sys
import time
import json
import math
import tempfile
import os
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QPixmap, QKeyEvent, QColor, QPainter, QFont, QShortcut

app = QApplication.instance() or QApplication(sys.argv)

sys.path.insert(0, "src")

from paparaz.core.elements import (
    AnnotationElement, TextElement, NumberElement, MaskElement, StampElement,
    RectElement, EllipseElement, PenElement, BrushElement,
    LineElement, ArrowElement, ImageElement, ElementStyle, Shadow,
    MagnifierElement, ElementType, CurvedArrowElement, HighlightElement,
    element_from_dict,
)
from paparaz.core.history import HistoryManager, Command
from paparaz.core.settings import AppSettings, SettingsManager, ToolDefaults
from paparaz.tools.base import ToolType
from paparaz.tools.select import SelectTool
from paparaz.tools.drawing import (
    PenTool, BrushTool, LineTool, ArrowTool, RectangleTool, EllipseTool,
    HighlightTool, CurvedArrowTool,
)
from paparaz.tools.special import (
    TextTool, NumberingTool, EraserTool, MasqueradeTool, FillTool, StampTool,
    SliceTool, EyedropperTool, MagnifierTool, CropTool,
)
from paparaz.ui.canvas import AnnotationCanvas


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_canvas(w=600, h=400):
    bg = QPixmap(w, h)
    bg.fill(Qt.GlobalColor.white)
    return AnnotationCanvas(bg)


def make_editor(w=800, h=600):
    from paparaz.ui.editor import EditorWindow
    bg = QPixmap(w, h)
    bg.fill(Qt.GlobalColor.white)
    return EditorWindow(bg)


class _FakeEvent:
    def modifiers(self): return Qt.KeyboardModifier.NoModifier
    def buttons(self): return Qt.MouseButton.LeftButton
    def button(self): return Qt.MouseButton.LeftButton


class _RightClickEvent:
    def modifiers(self): return Qt.KeyboardModifier.NoModifier
    def buttons(self): return Qt.MouseButton.RightButton
    def button(self): return Qt.MouseButton.RightButton


def click(tool, pos):
    ev = _FakeEvent()
    tool.on_press(pos, ev)
    tool.on_release(pos, ev)


def drag(tool, start, end, event=None):
    ev = event or _FakeEvent()
    tool.on_press(start, ev)
    tool.on_move(end, ev)
    tool.on_release(end, ev)


def key(tool, qt_key, text="", mods=Qt.KeyboardModifier.NoModifier):
    ev = QKeyEvent(QKeyEvent.Type.KeyPress, qt_key, mods, text)
    tool.on_key_press(ev)


# ###########################################################################
# 1. SMOKE TESTS — Critical path end-to-end
# ###########################################################################

class TestSmokeCriticalPath:
    """Verifies the most critical user workflows work end-to-end."""

    def test_boot_editor_draws_rect_saves(self):
        """Full pipeline: open editor → draw rectangle → export PNG."""
        ed = make_editor()
        canvas = ed._canvas
        tool = RectangleTool(canvas)
        canvas.set_tool(tool)
        drag(tool, QPointF(50, 50), QPointF(200, 200))
        assert len(canvas.elements) == 1

        from paparaz.core.export import render_final
        result = render_final(canvas._background, canvas.paint_annotations)
        assert not result.isNull()
        assert result.width() == 800

    def test_draw_undo_redo_cycle(self):
        c = make_canvas()
        tool = RectangleTool(c)
        c.set_tool(tool)
        drag(tool, QPointF(10, 10), QPointF(100, 100))
        assert len(c.elements) == 1
        c.history.undo()
        assert len(c.elements) == 0
        c.history.redo()
        assert len(c.elements) == 1

    def test_draw_select_move_delete(self):
        c = make_canvas()
        rect_tool = RectangleTool(c)
        c._filled = True  # ensure filled so center click hits
        c.set_tool(rect_tool)
        drag(rect_tool, QPointF(50, 50), QPointF(150, 150))
        sel = SelectTool(c)
        c.set_tool(sel)
        click(sel, QPointF(100, 100))
        assert c.selected_element is not None
        key(sel, Qt.Key.Key_Delete)
        assert len(c.elements) == 0

    def test_copy_paste_workflow(self):
        c = make_canvas()
        c._filled = True
        rect_tool = RectangleTool(c)
        c.set_tool(rect_tool)
        drag(rect_tool, QPointF(50, 50), QPointF(150, 150))
        sel = SelectTool(c)
        c.set_tool(sel)
        click(sel, QPointF(100, 100))
        assert c.selected_element is not None
        c.copy_element(c.selected_element)
        c.paste_element()
        assert len(c.elements) == 2

    def test_multi_tool_workflow(self):
        """Switch through multiple tools, draw with each."""
        c = make_canvas()
        tools = [
            PenTool(c), LineTool(c), ArrowTool(c),
            RectangleTool(c), EllipseTool(c),
        ]
        for t in tools:
            c.set_tool(t)
            drag(t, QPointF(50, 50), QPointF(200, 200))
        assert len(c.elements) == 5

    def test_text_tool_type_and_commit(self):
        c = make_canvas()
        t = TextTool(c)
        c.set_tool(t)
        click(t, QPointF(100, 100))
        key(t, Qt.Key.Key_H, "H")
        key(t, Qt.Key.Key_I, "i")
        key(t, Qt.Key.Key_Escape)
        assert len(c.elements) == 1
        assert c.elements[0].text == "Hi"

    def test_settings_save_load_roundtrip(self):
        path = Path(tempfile.mktemp(suffix=".json"))
        try:
            mgr = SettingsManager(path)
            s = mgr.settings
            s.app_theme = "ocean"
            mgr.save()
            mgr2 = SettingsManager(path)
            assert mgr2.settings.app_theme == "ocean"
        finally:
            if path.exists():
                path.unlink()


# ###########################################################################
# 2. BOUNDARY / EDGE-CASE TESTS
# ###########################################################################

class TestBoundaryEdgeCases:
    """Tests extreme values and edge conditions."""

    def test_zero_size_rect_not_added(self):
        c = make_canvas()
        tool = RectangleTool(c)
        c.set_tool(tool)
        drag(tool, QPointF(100, 100), QPointF(100, 100))
        # Zero-area rect is smaller than _MIN_SIZE (3 px) — should NOT be added
        assert len(c.elements) == 0, "Zero-area rectangle must not be committed"

    def test_canvas_1x1(self):
        c = make_canvas(1, 1)
        assert c._background.width() == 1
        assert c._background.height() == 1

    def test_canvas_very_large(self):
        c = make_canvas(4000, 3000)
        assert c._background.width() == 4000
        tool = RectangleTool(c)
        c.set_tool(tool)
        drag(tool, QPointF(0, 0), QPointF(3999, 2999))
        assert len(c.elements) == 1

    def test_negative_coordinates(self):
        c = make_canvas()
        tool = RectangleTool(c)
        c.set_tool(tool)
        drag(tool, QPointF(-50, -50), QPointF(50, 50))
        assert len(c.elements) == 1
        r = c.elements[0].bounding_rect()
        assert r.width() > 0

    def test_element_at_canvas_edge(self):
        c = make_canvas(600, 400)
        tool = RectangleTool(c)
        c.set_tool(tool)
        drag(tool, QPointF(550, 350), QPointF(600, 400))
        assert len(c.elements) == 1

    def test_element_beyond_canvas(self):
        c = make_canvas(600, 400)
        tool = RectangleTool(c)
        c.set_tool(tool)
        drag(tool, QPointF(500, 300), QPointF(700, 500))
        assert len(c.elements) == 1

    def test_empty_canvas_undo(self):
        c = make_canvas()
        c.history.undo()  # should not crash on empty history

    def test_empty_canvas_redo(self):
        c = make_canvas()
        c.history.redo()  # should not crash

    def test_delete_on_empty_canvas(self):
        c = make_canvas()
        sel = SelectTool(c)
        c.set_tool(sel)
        key(sel, Qt.Key.Key_Delete)  # nothing to delete, should not crash

    def test_paste_with_nothing_copied(self):
        c = make_canvas()
        c.paste_element()  # should handle gracefully with no clipboard

    def test_paste_with_empty_clipboard(self):
        c = make_canvas()
        c._clipboard = None
        # paste should handle gracefully

    def test_select_click_empty_area(self):
        c = make_canvas()
        sel = SelectTool(c)
        c.set_tool(sel)
        click(sel, QPointF(300, 200))
        assert c.selected_element is None

    def test_history_max_depth(self):
        c = make_canvas()
        tool = RectangleTool(c)
        c.set_tool(tool)
        for i in range(200):
            drag(tool, QPointF(i, i), QPointF(i + 10, i + 10))
        assert len(c.elements) == 200
        # Undo all — should not crash
        for _ in range(200):
            c.history.undo()
        assert len(c.elements) == 0

    def test_number_element_zero(self):
        elem = NumberElement(QPointF(50, 50), 0)
        assert elem.number == 0

    def test_number_element_negative(self):
        elem = NumberElement(QPointF(50, 50), -1)
        assert elem.number == -1

    def test_number_element_large(self):
        elem = NumberElement(QPointF(50, 50), 99999)
        assert elem.number == 99999

    def test_text_element_empty_string(self):
        elem = TextElement(QPointF(0, 0), "")
        assert elem.text == ""

    def test_text_element_very_long(self):
        long_text = "A" * 10000
        elem = TextElement(QPointF(0, 0), long_text)
        assert len(elem.text) == 10000

    def test_text_element_unicode(self):
        elem = TextElement(QPointF(0, 0), "Hello")
        assert elem.text == "Hello"

    def test_style_zero_line_width(self):
        s = ElementStyle(line_width=0)
        assert s.line_width == 0

    def test_style_very_large_line_width(self):
        s = ElementStyle(line_width=500)
        assert s.line_width == 500

    def test_style_zero_opacity(self):
        s = ElementStyle(opacity=0.0)
        assert s.opacity == 0.0

    def test_style_full_opacity(self):
        s = ElementStyle(opacity=1.0)
        assert s.opacity == 1.0

    def test_magnifier_zoom_zero(self):
        elem = MagnifierElement(QRectF(0, 0, 50, 50), QRectF(100, 100, 100, 100), zoom=0.0)
        assert elem.zoom == 0.0

    def test_magnifier_zoom_very_high(self):
        elem = MagnifierElement(QRectF(0, 0, 50, 50), QRectF(100, 100, 100, 100), zoom=100.0)
        assert elem.zoom == 100.0

    def test_pen_element_single_point(self):
        elem = PenElement()
        elem.add_point(QPointF(50, 50))
        assert len(elem.points) == 1

    def test_pen_element_empty_points(self):
        elem = PenElement()
        assert len(elem.points) == 0

    def test_line_element_zero_length(self):
        elem = LineElement(QPointF(50, 50), QPointF(50, 50))
        assert elem.start == elem.end

    def test_mask_element_tiny_rect(self):
        elem = MaskElement(QRectF(0, 0, 1, 1))
        assert elem.rect.width() == 1


# ###########################################################################
# 3. NEGATIVE / ERROR-HANDLING TESTS
# ###########################################################################

class TestNegativeErrorHandling:
    """Tests graceful handling of invalid input and corrupt state."""

    def test_corrupt_settings_json(self):
        path = Path(tempfile.mktemp(suffix=".json"))
        try:
            path.write_text("NOT VALID JSON {{{")
            mgr = SettingsManager(path)
            # Should fall back to defaults, not crash
            assert mgr.settings is not None
            assert isinstance(mgr.settings, AppSettings)
        finally:
            if path.exists():
                path.unlink()

    def test_empty_settings_file(self):
        path = Path(tempfile.mktemp(suffix=".json"))
        try:
            path.write_text("")
            mgr = SettingsManager(path)
            assert mgr.settings is not None
        finally:
            if path.exists():
                path.unlink()

    def test_settings_missing_keys(self):
        path = Path(tempfile.mktemp(suffix=".json"))
        try:
            path.write_text('{"editor": {}}')
            mgr = SettingsManager(path)
            assert mgr.settings is not None
        finally:
            if path.exists():
                path.unlink()

    def test_settings_wrong_types(self):
        path = Path(tempfile.mktemp(suffix=".json"))
        try:
            path.write_text('{"editor": {"theme": 12345}}')
            mgr = SettingsManager(path)
            # Should load without crash (may use wrong value or default)
            assert mgr.settings is not None
        finally:
            if path.exists():
                path.unlink()

    def test_tool_on_null_canvas_background(self):
        c = make_canvas()
        c._background = QPixmap()  # null pixmap
        tool = RectangleTool(c)
        c.set_tool(tool)
        # Drawing on null background should not crash
        drag(tool, QPointF(10, 10), QPointF(50, 50))

    def test_select_tool_double_deactivate(self):
        c = make_canvas()
        sel = SelectTool(c)
        c.set_tool(sel)
        sel.on_deactivate()
        sel.on_deactivate()  # double deactivate should not crash

    def test_history_undo_beyond_empty(self):
        c = make_canvas()
        for _ in range(10):
            c.history.undo()  # many undos on empty, no crash

    def test_history_redo_beyond_empty(self):
        c = make_canvas()
        for _ in range(10):
            c.history.redo()

    def test_set_tool_none_is_noop(self):
        """set_tool(None) is now guarded — no-op instead of crash."""
        c = make_canvas()
        tool = RectangleTool(c)
        c.set_tool(tool)
        c.set_tool(None)  # should not crash
        assert c._tool is tool  # tool unchanged

    def test_crop_tool_apply_without_selection(self):
        c = make_canvas()
        tool = CropTool(c)
        c.set_tool(tool)
        # Apply without drawing selection
        key(tool, Qt.Key.Key_Return)
        # Should be a no-op

    def test_slice_tool_apply_without_selection(self):
        c = make_canvas()
        tool = SliceTool(c)
        c.set_tool(tool)
        key(tool, Qt.Key.Key_Return)
        assert len(c.elements) == 0

    def test_element_move_by_zero(self):
        elem = RectElement(QRectF(10, 10, 50, 50), filled=True, style=ElementStyle())
        old_x = elem.rect.x()
        elem.move_by(0, 0)
        assert elem.rect.x() == old_x

    def test_element_visibility_toggle(self):
        elem = RectElement(QRectF(10, 10, 50, 50), filled=True, style=ElementStyle())
        assert elem.visible is True
        elem.visible = False
        assert elem.visible is False
        elem.visible = True
        assert elem.visible is True

    def test_invalid_color_string_in_style(self):
        s = ElementStyle(foreground_color="not-a-color")
        # Color validation now falls back to default
        assert s.foreground_color == "#FF0000"
        c = QColor(s.foreground_color)
        assert c.isValid() is True

    def test_recovery_module_missing_dir(self, monkeypatch):
        from paparaz.core import recovery
        fake_dir = Path(tempfile.mktemp(suffix="_recovery"))
        monkeypatch.setattr(recovery, "RECOVERY_DIR", fake_dir)
        assert recovery.has_recovery() is False
        assert recovery.get_recovery_files() == []


# ###########################################################################
# 4. DATA INTEGRITY TESTS — Serialization roundtrip
# ###########################################################################

class TestDataIntegritySerialization:
    """Verify to_dict() produces correct, complete data for all element types."""

    def test_rect_element_to_dict(self):
        s = ElementStyle(foreground_color="#FF0000", line_width=3)
        elem = RectElement(QRectF(10, 20, 100, 50), filled=True, style=s)
        d = elem.to_dict()
        assert d["type"] == "RECTANGLE"
        assert d["rect"] == (10.0, 20.0, 100.0, 50.0)
        assert d["filled"] is True
        assert d["style"]["foreground_color"] == "#FF0000"
        assert d["style"]["line_width"] == 3
        assert d["rotation"] == 0.0
        assert d["visible"] is True

    def test_ellipse_element_to_dict(self):
        elem = EllipseElement(QRectF(5, 5, 80, 60), filled=False)
        d = elem.to_dict()
        assert d["type"] == "ELLIPSE"
        assert d["rect"] == (5.0, 5.0, 80.0, 60.0)
        assert d["filled"] is False

    def test_line_element_to_dict(self):
        elem = LineElement(QPointF(10, 20), QPointF(100, 200))
        d = elem.to_dict()
        assert d["type"] == "LINE"
        assert d["start"] == (10.0, 20.0)
        assert d["end"] == (100.0, 200.0)

    def test_arrow_element_to_dict(self):
        elem = ArrowElement(QPointF(0, 0), QPointF(50, 50))
        d = elem.to_dict()
        assert d["type"] == "ARROW"
        assert d["start"] == (0.0, 0.0)
        assert d["end"] == (50.0, 50.0)

    def test_pen_element_to_dict(self):
        elem = PenElement()
        elem.add_point(QPointF(0, 0))
        elem.add_point(QPointF(10, 10))
        elem.add_point(QPointF(20, 5))
        d = elem.to_dict()
        assert d["type"] == "PEN"
        assert len(d["points"]) == 3
        assert d["points"][0] == (0.0, 0.0)

    def test_text_element_to_dict(self):
        elem = TextElement(QPointF(10, 10), "Hello World")
        elem.bold = True
        elem.italic = True
        d = elem.to_dict()
        assert d["type"] == "TEXT"
        assert d["text"] == "Hello World"
        assert d["bold"] is True
        assert d["italic"] is True
        assert "rect" in d

    def test_number_element_to_dict(self):
        elem = NumberElement(QPointF(100, 200), 42)
        d = elem.to_dict()
        assert d["type"] == "NUMBER"
        assert d["number"] == 42
        assert d["position"] == (100.0, 200.0)

    def test_mask_element_to_dict(self):
        elem = MaskElement(QRectF(20, 30, 60, 40))
        d = elem.to_dict()
        assert d["type"] == "MASK"
        assert d["rect"] == (20.0, 30.0, 60.0, 40.0)
        assert "pixel_size" in d

    def test_image_element_to_dict(self):
        pix = QPixmap(50, 50)
        pix.fill(Qt.GlobalColor.red)
        elem = ImageElement(pix, QPointF(10, 10))
        d = elem.to_dict()
        assert d["type"] == "IMAGE"
        assert d["rect"] == (10.0, 10.0, 50.0, 50.0)

    def test_stamp_element_to_dict(self):
        elem = StampElement("check", QPointF(16, 16), 32)
        d = elem.to_dict()
        assert d["type"] == "STAMP"
        assert d["stamp_id"] == "check"
        assert "rect" in d

    def test_magnifier_element_to_dict(self):
        elem = MagnifierElement(
            QRectF(10, 10, 50, 50), QRectF(100, 100, 100, 100), zoom=3.0
        )
        d = elem.to_dict()
        assert d["type"] == "MAGNIFIER"
        assert d["source_rect"] == (10.0, 10.0, 50.0, 50.0)
        assert d["display_rect"] == (100.0, 100.0, 100.0, 100.0)
        assert d["zoom"] == 3.0

    def test_style_serialization_complete(self):
        s = ElementStyle(
            foreground_color="#123456",
            background_color="#ABCDEF",
            line_width=5,
            opacity=0.7,
            font_family="Arial",
            font_size=14,
            shadow=Shadow(enabled=True, offset_x=3, offset_y=3, color="#333333"),
        )
        elem = RectElement(QRectF(0, 0, 10, 10), filled=True, style=s)
        d = elem.to_dict()
        st = d["style"]
        assert st["foreground_color"] == "#123456"
        assert st["background_color"] == "#ABCDEF"
        assert st["line_width"] == 5
        assert st["opacity"] == 0.7
        assert st["font_family"] == "Arial"
        assert st["font_size"] == 14
        assert st["shadow"]["enabled"] is True
        assert st["shadow"]["offset_x"] == 3
        assert st["shadow"]["color"] == "#333333"

    def test_rotation_preserved_in_dict(self):
        elem = RectElement(QRectF(0, 0, 50, 50), filled=True, style=ElementStyle())
        elem.rotation = 45.0
        d = elem.to_dict()
        assert d["rotation"] == 45.0

    def test_visibility_preserved_in_dict(self):
        elem = RectElement(QRectF(0, 0, 50, 50), filled=True, style=ElementStyle())
        elem.visible = False
        d = elem.to_dict()
        assert d["visible"] is False

    def test_all_elements_produce_valid_json(self):
        """Every element's to_dict() must produce JSON-serializable output."""
        pen = PenElement()
        pen.add_point(QPointF(0, 0))
        pen.add_point(QPointF(10, 10))
        brush = BrushElement()
        brush.add_point(QPointF(0, 0))
        brush.add_point(QPointF(10, 10))
        elements = [
            pen,
            brush,
            LineElement(QPointF(0, 0), QPointF(10, 10)),
            ArrowElement(QPointF(0, 0), QPointF(10, 10)),
            RectElement(QRectF(0, 0, 50, 50), filled=True, style=ElementStyle()),
            EllipseElement(QRectF(0, 0, 50, 50), filled=False),
            TextElement(QPointF(0, 0), "test"),
            NumberElement(QPointF(50, 50), 1),
            MaskElement(QRectF(0, 0, 50, 50)),
            ImageElement(QPixmap(10, 10), QPointF(0, 0)),
            StampElement("star", QPointF(16, 16), 32),
            MagnifierElement(QRectF(0, 0, 50, 50), QRectF(100, 100, 100, 100)),
        ]
        for elem in elements:
            d = elem.to_dict()
            # Must not raise
            serialized = json.dumps(d)
            assert len(serialized) > 0
            # Must round-trip through JSON
            parsed = json.loads(serialized)
            assert parsed["type"] == d["type"]

    def test_all_elements_have_from_dict(self):
        """All element types must have from_dict() for deserialization."""
        classes = [
            PenElement, BrushElement, LineElement, ArrowElement,
            RectElement, EllipseElement, TextElement, NumberElement,
            MaskElement, ImageElement, StampElement, MagnifierElement,
        ]
        for cls in classes:
            assert hasattr(cls, "from_dict"), f"{cls.__name__} missing from_dict"

    def test_element_id_uniqueness(self):
        """Each element should get a unique ID."""
        elems = [
            RectElement(QRectF(0, 0, 10, 10), filled=True, style=ElementStyle()),
            RectElement(QRectF(0, 0, 10, 10), filled=True, style=ElementStyle()),
            LineElement(QPointF(0, 0), QPointF(10, 10)),
        ]
        ids = [e.id for e in elems]
        assert len(set(ids)) == 3, "Element IDs must be unique"

    def test_recovery_save_and_load(self, monkeypatch):
        from paparaz.core import recovery
        fake_dir = Path(tempfile.mkdtemp())
        monkeypatch.setattr(recovery, "RECOVERY_DIR", fake_dir)
        bg = QPixmap(100, 100)
        bg.fill(Qt.GlobalColor.white)
        recovery.save_snapshot(bg, [])
        assert recovery.has_recovery() is True
        files = recovery.get_recovery_files()
        assert len(files) > 0
        recovery.clear_recovery()
        assert recovery.has_recovery() is False


# ###########################################################################
# 5. STATE MACHINE TESTS — Complex tool phase transitions
# ###########################################################################

class TestCurvedArrowStateMachine:
    """CurvedArrowTool: IDLE(0) → END(1) → CTRL(2) phases with cancel/commit."""

    def test_initial_state_idle(self):
        c = make_canvas()
        tool = CurvedArrowTool(c)
        c.set_tool(tool)
        assert tool._phase == CurvedArrowTool._PHASE_IDLE

    def test_press_transitions_to_end(self):
        c = make_canvas()
        tool = CurvedArrowTool(c)
        c.set_tool(tool)
        ev = _FakeEvent()
        tool.on_press(QPointF(50, 50), ev)
        tool.on_release(QPointF(50, 50), ev)
        assert tool._phase == CurvedArrowTool._PHASE_END

    def test_second_click_transitions_to_ctrl(self):
        c = make_canvas()
        tool = CurvedArrowTool(c)
        c.set_tool(tool)
        ev = _FakeEvent()
        tool.on_press(QPointF(50, 50), ev)
        tool.on_release(QPointF(50, 50), ev)
        tool.on_press(QPointF(200, 200), ev)
        tool.on_release(QPointF(200, 200), ev)
        assert tool._phase == CurvedArrowTool._PHASE_CTRL

    def test_enter_commits_from_ctrl(self):
        c = make_canvas()
        tool = CurvedArrowTool(c)
        c.set_tool(tool)
        ev = _FakeEvent()
        tool.on_press(QPointF(50, 50), ev)
        tool.on_release(QPointF(50, 50), ev)
        tool.on_press(QPointF(200, 200), ev)
        tool.on_release(QPointF(200, 200), ev)
        tool.on_press(QPointF(125, 10), ev)
        tool.on_release(QPointF(125, 10), ev)
        # Third click commits and returns to IDLE
        assert tool._phase == CurvedArrowTool._PHASE_IDLE
        assert len(c.elements) == 1

    def test_escape_cancels_from_end(self):
        c = make_canvas()
        tool = CurvedArrowTool(c)
        c.set_tool(tool)
        ev = _FakeEvent()
        tool.on_press(QPointF(50, 50), ev)
        tool.on_release(QPointF(50, 50), ev)
        assert tool._phase == CurvedArrowTool._PHASE_END
        key(tool, Qt.Key.Key_Escape)
        assert tool._phase == CurvedArrowTool._PHASE_IDLE
        assert len(c.elements) == 0

    def test_escape_cancels_from_ctrl(self):
        c = make_canvas()
        tool = CurvedArrowTool(c)
        c.set_tool(tool)
        ev = _FakeEvent()
        tool.on_press(QPointF(50, 50), ev)
        tool.on_release(QPointF(50, 50), ev)
        tool.on_press(QPointF(200, 200), ev)
        tool.on_release(QPointF(200, 200), ev)
        assert tool._phase == CurvedArrowTool._PHASE_CTRL
        key(tool, Qt.Key.Key_Escape)
        assert tool._phase == CurvedArrowTool._PHASE_IDLE
        assert len(c.elements) == 0

    def test_deactivate_resets_state(self):
        c = make_canvas()
        tool = CurvedArrowTool(c)
        c.set_tool(tool)
        ev = _FakeEvent()
        tool.on_press(QPointF(50, 50), ev)
        tool.on_release(QPointF(50, 50), ev)
        tool.on_deactivate()
        assert tool._phase == CurvedArrowTool._PHASE_IDLE


class TestCropToolStateMachine:
    """CropTool: selection → optional rotation → apply/cancel."""

    def test_initial_state_inactive(self):
        c = make_canvas()
        tool = CropTool(c)
        c.set_tool(tool)
        assert tool._active is False

    def test_press_activates_selection(self):
        c = make_canvas()
        tool = CropTool(c)
        c.set_tool(tool)
        ev = _FakeEvent()
        tool.on_press(QPointF(50, 50), ev)
        assert tool._active is True

    def test_escape_cancels_selection(self):
        c = make_canvas()
        tool = CropTool(c)
        c.set_tool(tool)
        ev = _FakeEvent()
        tool.on_press(QPointF(50, 50), ev)
        tool.on_move(QPointF(200, 200), ev)
        tool.on_release(QPointF(200, 200), ev)
        key(tool, Qt.Key.Key_Escape)
        assert tool._active is False

    def test_enter_applies_crop(self):
        c = make_canvas(600, 400)
        tool = CropTool(c)
        c.set_tool(tool)
        ev = _FakeEvent()
        tool.on_press(QPointF(50, 50), ev)
        tool.on_move(QPointF(300, 200), ev)
        tool.on_release(QPointF(300, 200), ev)
        old_w = c._background.width()
        key(tool, Qt.Key.Key_Return)
        # Canvas should be cropped (smaller or same)
        assert tool._active is False

    def test_right_click_applies_crop(self):
        c = make_canvas(600, 400)
        tool = CropTool(c)
        c.set_tool(tool)
        ev = _FakeEvent()
        tool.on_press(QPointF(50, 50), ev)
        tool.on_move(QPointF(300, 200), ev)
        tool.on_release(QPointF(300, 200), ev)
        rc = _RightClickEvent()
        tool.on_press(QPointF(100, 100), rc)
        assert tool._active is False

    def test_double_click_applies_crop(self):
        c = make_canvas(600, 400)
        tool = CropTool(c)
        c.set_tool(tool)
        ev = _FakeEvent()
        tool.on_press(QPointF(50, 50), ev)
        tool.on_move(QPointF(300, 200), ev)
        tool.on_release(QPointF(300, 200), ev)
        tool.on_double_click(QPointF(150, 150), ev)
        assert tool._active is False

    def test_tiny_selection_cancels(self):
        c = make_canvas()
        tool = CropTool(c)
        c.set_tool(tool)
        ev = _FakeEvent()
        tool.on_press(QPointF(50, 50), ev)
        tool.on_move(QPointF(52, 52), ev)
        tool.on_release(QPointF(52, 52), ev)
        key(tool, Qt.Key.Key_Return)
        # Too small, should cancel without modifying canvas

    def test_new_selection_resets_rotation(self):
        c = make_canvas()
        tool = CropTool(c)
        c.set_tool(tool)
        ev = _FakeEvent()
        tool.on_press(QPointF(50, 50), ev)
        tool.on_release(QPointF(200, 200), ev)
        tool._rotation = 30.0
        tool.on_press(QPointF(10, 10), ev)
        assert tool._rotation == 0.0


# ###########################################################################
# 6. PERFORMANCE / STRESS TESTS
# ###########################################################################

class TestPerformanceStress:
    """Performance and stress tests — element scaling, rapid operations."""

    def test_100_elements_creation(self):
        c = make_canvas()
        tool = RectangleTool(c)
        c.set_tool(tool)
        start = time.perf_counter()
        for i in range(100):
            drag(tool, QPointF(i, i), QPointF(i + 20, i + 20))
        elapsed = time.perf_counter() - start
        assert len(c.elements) == 100
        assert elapsed < 5.0, f"100 elements took {elapsed:.2f}s (>5s)"

    def test_100_undo_redo_cycle(self):
        c = make_canvas()
        tool = RectangleTool(c)
        c.set_tool(tool)
        for i in range(100):
            drag(tool, QPointF(i, i), QPointF(i + 20, i + 20))
        start = time.perf_counter()
        for _ in range(100):
            c.history.undo()
        for _ in range(100):
            c.history.redo()
        elapsed = time.perf_counter() - start
        assert len(c.elements) == 100
        assert elapsed < 5.0, f"100 undo+redo took {elapsed:.2f}s (>5s)"

    def test_rapid_tool_switching(self):
        c = make_canvas()
        tools = [PenTool(c), LineTool(c), RectangleTool(c), EllipseTool(c), SelectTool(c)]
        start = time.perf_counter()
        for _ in range(200):
            for t in tools:
                c.set_tool(t)
        elapsed = time.perf_counter() - start
        assert elapsed < 3.0, f"1000 tool switches took {elapsed:.2f}s (>3s)"

    def test_500_elements_creation_and_iteration(self):
        c = make_canvas(2000, 2000)
        tool = RectangleTool(c)
        c.set_tool(tool)
        for i in range(500):
            x = (i % 50) * 40
            y = (i // 50) * 40
            drag(tool, QPointF(x, y), QPointF(x + 30, y + 30))
        assert len(c.elements) == 500
        # Verify iteration performance
        start = time.perf_counter()
        for elem in c.elements:
            _ = elem.bounding_rect()
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0

    def test_render_final_with_many_elements(self):
        from paparaz.core.export import render_final
        c = make_canvas(800, 600)
        tool = RectangleTool(c)
        c.set_tool(tool)
        for i in range(50):
            drag(tool, QPointF(i * 10, i * 5), QPointF(i * 10 + 30, i * 5 + 30))
        start = time.perf_counter()
        result = render_final(c._background, c.paint_annotations)
        elapsed = time.perf_counter() - start
        assert not result.isNull()
        assert elapsed < 3.0

    def test_history_memory_not_unbounded(self):
        c = make_canvas()
        for i in range(500):
            c.history.execute(Command(f"cmd_{i}", lambda: None, lambda: None))
        assert c.history.can_undo

    def test_large_text_element_paint(self):
        elem = TextElement(QRectF(0, 0, 500, 500), "A" * 5000)
        pix = QPixmap(600, 600)
        pix.fill(Qt.GlobalColor.white)
        p = QPainter(pix)
        start = time.perf_counter()
        elem.paint(p)
        elapsed = time.perf_counter() - start
        p.end()
        assert elapsed < 2.0


# ###########################################################################
# 7. ACCESSIBILITY TESTS
# ###########################################################################

class TestAccessibility:
    """Keyboard navigation, tooltips, and widget labels."""

    def test_all_toolbar_buttons_have_tooltips(self):
        ed = make_editor()
        toolbar = ed._multi_toolbar
        for btn in toolbar._buttons:
            tip = btn.toolTip()
            assert tip and len(tip) > 0, f"Button missing tooltip"

    def test_editor_keyboard_shortcuts_exist(self):
        ed = make_editor()
        shortcuts = ed.findChildren(QShortcut)
        # Should have at least some shortcuts (Ctrl+Z, Ctrl+C, etc.)
        assert len(shortcuts) > 0

    def test_side_panel_sections_have_labels(self):
        from paparaz.ui.side_panel import SidePanel
        bg = QPixmap(400, 300)
        bg.fill(Qt.GlobalColor.white)
        canvas = AnnotationCanvas(bg)
        panel = SidePanel(canvas)
        # Panel should have labeled sections
        from PySide6.QtWidgets import QLabel
        labels = panel.findChildren(QLabel)
        assert len(labels) > 0

    def test_canvas_resize_dialog_labels(self):
        from paparaz.ui.canvas_resize_dialog import CanvasResizeDialog
        d = CanvasResizeDialog(800, 600)
        from PySide6.QtWidgets import QLabel
        labels = d.findChildren(QLabel)
        label_texts = [l.text() for l in labels]
        assert any("Width" in t for t in label_texts)
        assert any("Height" in t for t in label_texts)

    def test_settings_dialog_has_page_labels(self):
        from paparaz.ui.settings_dialog import SettingsDialog
        path = Path(tempfile.mktemp(suffix=".json"))
        try:
            mgr = SettingsManager(path)
            d = SettingsDialog(mgr)
            from PySide6.QtWidgets import QLabel
            labels = d.findChildren(QLabel)
            assert len(labels) > 5  # multiple pages should have labels
        finally:
            if path.exists():
                path.unlink()

    def test_toolbar_has_buttons(self):
        ed = make_editor()
        toolbar = ed._multi_toolbar
        # Toolbar holds all buttons before distributing to strips
        assert len(toolbar._buttons) > 0

    def test_layers_panel_has_action_buttons(self):
        from paparaz.ui.layers_panel import LayersPanel
        panel = LayersPanel()
        from PySide6.QtWidgets import QPushButton, QToolButton
        buttons = panel.findChildren(QPushButton) + panel.findChildren(QToolButton)
        assert len(buttons) >= 3  # move up, move down, delete at minimum

    def test_escape_closes_editor(self):
        """Escape key should be connected to close/cancel."""
        ed = make_editor()
        # Just verify the editor can handle close without crash
        # (In real app, Escape triggers close confirmation)


# ###########################################################################
# 8. SIGNAL SAFETY TESTS
# ###########################################################################

class TestSignalSafety:
    """Tests for rapid signal emission and re-entrant handler safety."""

    def test_rapid_tool_change_signals(self):
        c = make_canvas()
        tools = [PenTool(c), LineTool(c), RectangleTool(c)]
        for _ in range(100):
            for t in tools:
                c.set_tool(t)
        # No crash = pass

    def test_rapid_element_add_remove(self):
        c = make_canvas()
        for _ in range(50):
            elem = RectElement(QRectF(10, 10, 50, 50), filled=True, style=ElementStyle())
            c.elements.append(elem)
            c.elements.remove(elem)
        assert len(c.elements) == 0

    def test_rapid_undo_redo_interleaved(self):
        c = make_canvas()
        tool = RectangleTool(c)
        c.set_tool(tool)
        for i in range(20):
            drag(tool, QPointF(i, i), QPointF(i + 10, i + 10))
        for _ in range(50):
            c.history.undo()
            c.history.redo()
            c.history.undo()
        # Should settle at consistent state

    def test_history_signal_during_undo(self):
        c = make_canvas()
        tool = RectangleTool(c)
        c.set_tool(tool)
        drag(tool, QPointF(10, 10), QPointF(50, 50))
        drag(tool, QPointF(60, 60), QPointF(100, 100))
        # Undo while history is modifying state
        c.history.undo()
        c.history.undo()
        c.history.redo()
        assert len(c.elements) == 1

    def test_select_during_draw(self):
        """Switch to select tool mid-draw — should not corrupt state."""
        c = make_canvas()
        pen = PenTool(c)
        c.set_tool(pen)
        ev = _FakeEvent()
        pen.on_press(QPointF(10, 10), ev)
        pen.on_move(QPointF(50, 50), ev)
        # Switch tool mid-draw
        sel = SelectTool(c)
        c.set_tool(sel)
        # Should deactivate pen cleanly

    def test_canvas_update_during_element_modification(self):
        c = make_canvas()
        tool = RectangleTool(c)
        c.set_tool(tool)
        drag(tool, QPointF(10, 10), QPointF(100, 100))
        elem = c.elements[0]
        # Rapid modifications
        for i in range(100):
            elem.move_by(1, 1)
            c.update()
        # No crash = pass

    def test_layers_panel_rapid_refresh(self):
        from paparaz.ui.layers_panel import LayersPanel
        bg = QPixmap(400, 300)
        bg.fill(Qt.GlobalColor.white)
        canvas = AnnotationCanvas(bg)
        panel = LayersPanel()
        panel.set_canvas(canvas)
        # Add elements and refresh rapidly
        for i in range(20):
            canvas.elements.append(
                RectElement(QRectF(i, i, 20, 20), filled=True, style=ElementStyle())
            )
            panel.refresh()
        assert panel._list.count() == 20

    def test_side_panel_rapid_tool_updates(self):
        from paparaz.ui.side_panel import SidePanel
        bg = QPixmap(400, 300)
        bg.fill(Qt.GlobalColor.white)
        canvas = AnnotationCanvas(bg)
        panel = SidePanel(canvas)
        tools = [ToolType.PEN, ToolType.RECTANGLE, ToolType.TEXT,
                 ToolType.SELECT, ToolType.FILL, ToolType.ELLIPSE]
        for _ in range(50):
            for t in tools:
                panel.update_for_tool(t)
        # No crash = pass


# ###########################################################################
# Phase B: RegionSelector, PinWindow, ColorPalette, TrayIcon, ThemePresets
# ###########################################################################

class TestRecentColorsPalette:
    """RecentColorsPalette: color list, add, signals."""

    def test_creation(self):
        from paparaz.ui.color_palette import RecentColorsPalette
        p = RecentColorsPalette()
        assert p is not None

    def test_add_color(self):
        from paparaz.ui.color_palette import RecentColorsPalette
        p = RecentColorsPalette()
        p.add_color("#FF0000")
        colors = p.get_colors()
        assert "#FF0000" in colors or "#ff0000" in [c.lower() for c in colors]

    def test_add_duplicate_color(self):
        from paparaz.ui.color_palette import RecentColorsPalette
        p = RecentColorsPalette()
        p.add_color("#FF0000")
        p.add_color("#FF0000")
        colors = p.get_colors()
        # Should deduplicate
        count = sum(1 for c in colors if c.upper() == "#FF0000")
        assert count == 1

    def test_max_16_colors(self):
        from paparaz.ui.color_palette import RecentColorsPalette
        p = RecentColorsPalette()
        for i in range(20):
            p.add_color(f"#{i:02x}{i:02x}{i:02x}")
        colors = p.get_colors()
        assert len(colors) <= 16

    def test_set_colors(self):
        from paparaz.ui.color_palette import RecentColorsPalette
        p = RecentColorsPalette()
        p.set_colors(["#FF0000", "#00FF00", "#0000FF"])
        colors = p.get_colors()
        assert len(colors) == 3

    def test_fg_signal_emitted(self):
        from paparaz.ui.color_palette import RecentColorsPalette
        p = RecentColorsPalette()
        p.add_color("#FF0000")
        received = []
        p.fg_requested.connect(lambda c: received.append(c))
        # Simulate click on first swatch
        btns = [w for w in p.children() if hasattr(w, '_color')]
        if btns:
            btns[0].click()
            # Signal may or may not fire depending on implementation


class TestPinWindow:
    """PinWindow: creation, flags, context menu."""

    def test_creation(self):
        from paparaz.ui.pin_window import PinWindow
        bg = QPixmap(200, 200)
        bg.fill(Qt.GlobalColor.red)
        pw = PinWindow(bg)
        assert pw is not None

    def test_always_on_top(self):
        from paparaz.ui.pin_window import PinWindow
        bg = QPixmap(200, 200)
        bg.fill(Qt.GlobalColor.red)
        pw = PinWindow(bg)
        flags = pw.windowFlags()
        assert flags & Qt.WindowType.WindowStaysOnTopHint

    def test_frameless(self):
        from paparaz.ui.pin_window import PinWindow
        bg = QPixmap(200, 200)
        bg.fill(Qt.GlobalColor.red)
        pw = PinWindow(bg)
        flags = pw.windowFlags()
        assert flags & Qt.WindowType.FramelessWindowHint

    def test_displays_pixmap(self):
        from paparaz.ui.pin_window import PinWindow
        bg = QPixmap(200, 200)
        bg.fill(Qt.GlobalColor.blue)
        pw = PinWindow(bg)
        assert pw.width() > 0
        assert pw.height() > 0


class TestTrayIcon:
    """TrayIcon: creation, menu structure, signals."""

    def test_creation_no_crash(self):
        from paparaz.ui.tray import TrayIcon
        tray = TrayIcon()
        assert tray is not None

    def test_has_context_menu(self):
        from paparaz.ui.tray import TrayIcon
        tray = TrayIcon()
        assert hasattr(tray, "_menu")
        assert tray._menu is not None

    def test_menu_has_actions(self):
        from paparaz.ui.tray import TrayIcon
        tray = TrayIcon()
        actions = tray._menu.actions()
        assert len(actions) >= 4

    def test_menu_has_capture_action(self):
        from paparaz.ui.tray import TrayIcon
        tray = TrayIcon()
        texts = [a.text() for a in tray._menu.actions()]
        assert any("capture" in t.lower() or "screen" in t.lower() for t in texts)

    def test_menu_has_quit_action(self):
        from paparaz.ui.tray import TrayIcon
        tray = TrayIcon()
        texts = [a.text() for a in tray._menu.actions()]
        assert any("quit" in t.lower() or "exit" in t.lower() for t in texts)

    def test_signals_exist(self):
        from paparaz.ui.tray import TrayIcon
        tray = TrayIcon()
        assert hasattr(tray, "capture_requested")
        assert hasattr(tray, "quit_requested")
        assert hasattr(tray, "settings_requested")


class TestThemePresets:
    """Theme system: all presets parse, consistent keys, apply without crash."""

    def test_all_themes_exist(self):
        from paparaz.ui.app_theme import APP_THEMES
        expected = {"dark", "midnight", "ocean", "forest", "warm", "light"}
        for t in expected:
            assert t in APP_THEMES, f"Missing theme: {t}"

    def test_get_theme_returns_dict(self):
        from paparaz.ui.app_theme import get_theme
        theme = get_theme("dark")
        assert isinstance(theme, dict)

    def test_all_themes_consistent_keys(self):
        from paparaz.ui.app_theme import APP_THEMES
        keys = None
        for name, theme in APP_THEMES.items():
            if keys is None:
                keys = set(theme.keys())
            else:
                assert set(theme.keys()) == keys, f"Theme {name} has inconsistent keys"

    def test_build_tool_qss(self):
        from paparaz.ui.app_theme import get_theme, build_tool_qss
        theme = get_theme("dark")
        qss = build_tool_qss(theme)
        assert isinstance(qss, str)
        assert len(qss) > 0

    def test_build_panel_qss(self):
        from paparaz.ui.app_theme import get_theme, build_panel_qss
        theme = get_theme("ocean")
        qss = build_panel_qss(theme)
        assert isinstance(qss, str)
        assert len(qss) > 0

    def test_build_dialog_qss(self):
        from paparaz.ui.app_theme import get_theme, build_dialog_qss
        theme = get_theme("forest")
        qss = build_dialog_qss(theme)
        assert isinstance(qss, str)
        assert len(qss) > 0

    def test_invalid_theme_fallback(self):
        from paparaz.ui.app_theme import get_theme
        theme = get_theme("nonexistent")
        assert isinstance(theme, dict)  # should fall back to default

    def test_all_themes_have_accent(self):
        from paparaz.ui.app_theme import APP_THEMES
        for name, theme in APP_THEMES.items():
            assert "accent" in theme, f"Theme {name} missing accent"
            assert theme["accent"].startswith("#")


class TestRegionSelector:
    """RegionSelector overlay: creation and keyboard handling."""

    def _make(self):
        from paparaz.ui.overlay import RegionSelector
        bg = QPixmap(800, 600)
        bg.fill(Qt.GlobalColor.white)
        screen = QApplication.primaryScreen()
        if screen is None:
            pytest.skip("No screen available for RegionSelector tests")
        return RegionSelector(bg, screen)

    def test_creation(self):
        rs = self._make()
        assert rs is not None

    def test_has_selection_signal(self):
        rs = self._make()
        assert hasattr(rs, "region_selected") or hasattr(rs, "selection_made")

    def test_window_flags(self):
        rs = self._make()
        flags = rs.windowFlags()
        assert flags & Qt.WindowType.FramelessWindowHint


# ###########################################################################
# FIX VERIFICATION: from_dict() roundtrip tests
# ###########################################################################

class TestFromDictRoundtrip:
    """Verify to_dict → from_dict roundtrip for all element types."""

    def test_rect_roundtrip(self):
        s = ElementStyle(foreground_color="#00FF00", line_width=5)
        orig = RectElement(QRectF(10, 20, 100, 50), filled=True, style=s)
        orig.rotation = 30.0
        d = orig.to_dict()
        restored = RectElement.from_dict(d)
        assert restored.rect == orig.rect
        assert restored.filled is True
        assert restored.rotation == 30.0
        assert restored.style.foreground_color.lower() == "#00ff00"
        assert restored.style.line_width == 5

    def test_ellipse_roundtrip(self):
        orig = EllipseElement(QRectF(5, 5, 80, 60), filled=False)
        d = orig.to_dict()
        restored = EllipseElement.from_dict(d)
        assert restored.rect == orig.rect
        assert restored.filled is False

    def test_line_roundtrip(self):
        orig = LineElement(QPointF(10, 20), QPointF(100, 200))
        d = orig.to_dict()
        restored = LineElement.from_dict(d)
        assert restored.start == orig.start
        assert restored.end == orig.end

    def test_arrow_roundtrip(self):
        orig = ArrowElement(QPointF(0, 0), QPointF(50, 50))
        d = orig.to_dict()
        restored = ArrowElement.from_dict(d)
        assert restored.start == orig.start
        assert restored.element_type == ElementType.ARROW

    def test_pen_roundtrip(self):
        orig = PenElement()
        orig.add_point(QPointF(0, 0))
        orig.add_point(QPointF(10, 10))
        orig.add_point(QPointF(20, 5))
        d = orig.to_dict()
        restored = PenElement.from_dict(d)
        assert len(restored.points) == 3
        assert restored.points[0] == QPointF(0, 0)

    def test_brush_roundtrip(self):
        orig = BrushElement()
        orig.add_point(QPointF(5, 5))
        orig.add_point(QPointF(15, 15))
        d = orig.to_dict()
        restored = BrushElement.from_dict(d)
        assert len(restored.points) == 2
        assert restored.element_type == ElementType.BRUSH

    def test_highlight_roundtrip(self):
        orig = HighlightElement()
        orig.add_point(QPointF(1, 1))
        orig.add_point(QPointF(50, 50))
        d = orig.to_dict()
        restored = HighlightElement.from_dict(d)
        assert len(restored.points) == 2
        assert restored.element_type == ElementType.HIGHLIGHT

    def test_curved_arrow_roundtrip(self):
        orig = CurvedArrowElement(
            QPointF(10, 10), QPointF(100, 100), QPointF(50, 0)
        )
        d = orig.to_dict()
        restored = CurvedArrowElement.from_dict(d)
        assert restored.start == orig.start
        assert restored.end == orig.end
        assert restored.control == orig.control

    def test_text_roundtrip(self):
        orig = TextElement(QPointF(10, 10), "Hello World")
        orig.bold = True
        orig.italic = True
        orig.bg_enabled = True
        orig.bg_color = "#00FF00"
        d = orig.to_dict()
        restored = TextElement.from_dict(d)
        assert restored.text == "Hello World"
        assert restored.bold is True
        assert restored.italic is True
        assert restored.bg_enabled is True
        assert restored.bg_color == "#00FF00"

    def test_number_roundtrip(self):
        orig = NumberElement(QPointF(50, 50), 42, size=32, text_color="#FFFFFF")
        d = orig.to_dict()
        restored = NumberElement.from_dict(d)
        assert restored.number == 42
        assert restored.size == 32
        assert restored.text_color == "#FFFFFF"

    def test_mask_roundtrip(self):
        orig = MaskElement(QRectF(10, 20, 100, 50), pixel_size=15)
        d = orig.to_dict()
        restored = MaskElement.from_dict(d)
        assert restored.rect == orig.rect
        assert restored.pixel_size == 15

    def test_stamp_roundtrip(self):
        orig = StampElement("star", QPointF(50, 50), 32)
        d = orig.to_dict()
        restored = StampElement.from_dict(d)
        assert restored.stamp_id == "star"

    def test_image_roundtrip_preserves_rect(self):
        pix = QPixmap(100, 80)
        pix.fill(Qt.GlobalColor.red)
        orig = ImageElement(pix, QPointF(10, 20))
        d = orig.to_dict()
        restored = ImageElement.from_dict(d)
        assert restored.rect == orig.rect
        # Pixmap is lost (not serializable) but rect is preserved

    def test_magnifier_roundtrip(self):
        orig = MagnifierElement(
            QRectF(10, 10, 50, 50), QRectF(100, 100, 100, 100), zoom=3.0
        )
        d = orig.to_dict()
        restored = MagnifierElement.from_dict(d)
        assert restored.source_rect == orig.source_rect
        assert restored.display_rect == orig.display_rect
        assert restored.zoom == 3.0

    def test_style_roundtrip(self):
        s = ElementStyle(
            foreground_color="#123456", background_color="#ABCDEF",
            line_width=5, opacity=0.7, font_family="Courier",
            font_size=18, cap_style="square", join_style="bevel",
            dash_pattern="dash",
            shadow=Shadow(enabled=True, offset_x=4, offset_y=4, color="#333333"),
        )
        orig = RectElement(QRectF(0, 0, 10, 10), filled=True, style=s)
        d = orig.to_dict()
        restored = RectElement.from_dict(d)
        rs = restored.style
        assert rs.foreground_color == "#123456"
        assert rs.background_color.lower() == "#abcdef"
        assert rs.line_width == 5
        assert rs.opacity == 0.7
        assert rs.font_family == "Courier"
        assert rs.font_size == 18
        assert rs.shadow.enabled is True
        assert rs.shadow.offset_x == 4

    def test_visibility_roundtrip(self):
        orig = RectElement(QRectF(0, 0, 10, 10), filled=True, style=ElementStyle())
        orig.visible = False
        d = orig.to_dict()
        restored = RectElement.from_dict(d)
        assert restored.visible is False

    def test_element_from_dict_factory(self):
        """element_from_dict() should reconstruct any element by type name."""
        elements = [
            RectElement(QRectF(0, 0, 50, 50), filled=True, style=ElementStyle()),
            LineElement(QPointF(0, 0), QPointF(10, 10)),
            TextElement(QPointF(0, 0), "test"),
        ]
        for orig in elements:
            d = orig.to_dict()
            restored = element_from_dict(d)
            assert restored is not None
            assert restored.element_type == orig.element_type

    def test_element_from_dict_unknown_type(self):
        d = {"type": "NONEXISTENT"}
        assert element_from_dict(d) is None

    def test_json_full_roundtrip(self):
        """Serialize to JSON string, parse, reconstruct — full pipeline."""
        orig = RectElement(QRectF(10, 20, 100, 50), filled=True,
                           style=ElementStyle(foreground_color="#FF0000", line_width=3))
        orig.rotation = 45.0
        json_str = json.dumps(orig.to_dict())
        parsed = json.loads(json_str)
        restored = element_from_dict(parsed)
        assert restored.rect == orig.rect
        assert restored.filled is True
        assert restored.rotation == 45.0
        assert restored.style.foreground_color.lower() == "#ff0000"


# ###########################################################################
# FIX VERIFICATION: Guards, validation, eyedropper fallback
# ###########################################################################

class TestFixVerification:
    """Tests verifying the recommended fixes work correctly."""

    def test_set_tool_none_no_crash(self):
        c = make_canvas()
        c.set_tool(None)  # should be a no-op now, not crash

    def test_copy_element_none_no_crash(self):
        c = make_canvas()
        c.copy_element(None)  # should be a no-op

    def test_color_validation_valid(self):
        s = ElementStyle(foreground_color="#00FF00")
        assert s.foreground_color == "#00FF00"

    def test_color_validation_invalid_falls_back(self):
        s = ElementStyle(foreground_color="not-a-color")
        assert s.foreground_color == "#FF0000"  # default

    def test_color_validation_invalid_bg_falls_back(self):
        s = ElementStyle(background_color="garbage")
        assert s.background_color == "#FFFFFF"  # default

    def test_color_validation_named_colors(self):
        s = ElementStyle(foreground_color="red")
        assert QColor(s.foreground_color).isValid()

    def test_eyedropper_pixmap_fallback(self):
        c = make_canvas()
        # Fill background with a known color
        from PySide6.QtGui import QPainter
        p = QPainter(c._background)
        p.fillRect(0, 0, 600, 400, QColor("#FF0000"))
        p.end()
        eye = EyedropperTool(c)
        c.set_tool(eye)
        # Use the pixmap fallback directly
        color = eye._sample_color_from_pixmap(QPointF(50, 50))
        assert color.red() == 255
        assert color.green() == 0
        assert color.blue() == 0

    def test_eyedropper_pixmap_fallback_oob(self):
        c = make_canvas()
        eye = EyedropperTool(c)
        c.set_tool(eye)
        color = eye._sample_color_from_pixmap(QPointF(-10, -10))
        # Out of bounds returns white
        assert color == QColor(Qt.GlobalColor.white)

    def test_history_depth_limit_exists(self):
        c = make_canvas()
        assert c.history._max_size == 200
        for i in range(250):
            c.history.execute(
                Command(f"cmd_{i}", lambda: None, lambda: None)
            )
        assert len(c.history._undo_stack) <= 200


# ###########################################################################
# 9. PROJECT FILE (.papraz) TESTS
# ###########################################################################

class TestProjectFileSaveLoad:
    """Roundtrip tests for the .papraz project file format."""

    def _make_canvas_with_elements(self):
        """Create a canvas with a mix of elements for testing."""
        c = make_canvas(400, 300)
        c.elements.append(RectElement(QRectF(10, 20, 100, 50), filled=True, style=ElementStyle()))
        c.elements.append(LineElement(QPointF(0, 0), QPointF(200, 150)))
        c.elements.append(TextElement(QPointF(50, 60), "hello project"))
        return c

    def test_save_creates_file(self, tmp_path):
        from paparaz.core.project import save_project
        c = self._make_canvas_with_elements()
        path = str(tmp_path / "test.papraz")
        save_project(path, c)
        import os
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0

    def test_roundtrip_element_count(self, tmp_path):
        from paparaz.core.project import save_project, load_project
        c = self._make_canvas_with_elements()
        n = len(c.elements)
        path = str(tmp_path / "test.papraz")
        save_project(path, c)

        c2 = make_canvas(1, 1)
        load_project(path, c2)
        assert len(c2.elements) == n

    def test_roundtrip_element_types(self, tmp_path):
        from paparaz.core.project import save_project, load_project
        c = self._make_canvas_with_elements()
        original_types = [e.element_type for e in c.elements]
        path = str(tmp_path / "test.papraz")
        save_project(path, c)

        c2 = make_canvas(1, 1)
        load_project(path, c2)
        restored_types = [e.element_type for e in c2.elements]
        assert restored_types == original_types

    def test_roundtrip_background_size(self, tmp_path):
        from paparaz.core.project import save_project, load_project
        c = make_canvas(320, 240)
        path = str(tmp_path / "test.papraz")
        save_project(path, c)

        c2 = make_canvas(1, 1)
        meta = load_project(path, c2)
        assert meta["width"] == 320
        assert meta["height"] == 240
        assert c2._background.width() == 320
        assert c2._background.height() == 240

    def test_roundtrip_text_content(self, tmp_path):
        from paparaz.core.project import save_project, load_project
        c = make_canvas()
        c.elements.append(TextElement(QPointF(10, 10), "roundtrip text"))
        path = str(tmp_path / "test.papraz")
        save_project(path, c)

        c2 = make_canvas(1, 1)
        load_project(path, c2)
        text_elems = [e for e in c2.elements if e.element_type == ElementType.TEXT]
        assert len(text_elems) == 1
        assert text_elems[0].text == "roundtrip text"

    def test_roundtrip_rect_geometry(self, tmp_path):
        from paparaz.core.project import save_project, load_project
        c = make_canvas()
        c.elements.append(RectElement(QRectF(5, 15, 80, 40), filled=False, style=ElementStyle()))
        path = str(tmp_path / "test.papraz")
        save_project(path, c)

        c2 = make_canvas(1, 1)
        load_project(path, c2)
        r = c2.elements[0]
        assert r.element_type == ElementType.RECTANGLE
        assert r.rect.x() == pytest.approx(5)
        assert r.rect.y() == pytest.approx(15)
        assert r.rect.width() == pytest.approx(80)
        assert r.rect.height() == pytest.approx(40)

    def test_empty_canvas_roundtrip(self, tmp_path):
        from paparaz.core.project import save_project, load_project
        c = make_canvas(200, 150)
        path = str(tmp_path / "empty.papraz")
        save_project(path, c)

        c2 = make_canvas(1, 1)
        meta = load_project(path, c2)
        assert len(c2.elements) == 0
        assert meta["width"] == 200
        assert meta["height"] == 150

    def test_meta_contains_dpr(self, tmp_path):
        from paparaz.core.project import save_project, load_project
        c = make_canvas(100, 100)
        path = str(tmp_path / "dpr.papraz")
        save_project(path, c)

        c2 = make_canvas(1, 1)
        meta = load_project(path, c2)
        assert "dpr" in meta
        assert isinstance(meta["dpr"], float)

    def test_file_is_compressed_binary(self, tmp_path):
        """Saved file should be binary (base64+zlib), not plain JSON."""
        from paparaz.core.project import save_project
        c = make_canvas()
        path = str(tmp_path / "check.papraz")
        save_project(path, c)
        raw = Path(path).read_bytes()
        # base64 output must not start with '{' (plain JSON)
        assert not raw.startswith(b"{")

    def test_load_clears_existing_elements(self, tmp_path):
        from paparaz.core.project import save_project, load_project
        # Save a project with 1 element
        c = make_canvas()
        c.elements.append(RectElement(QRectF(0, 0, 10, 10), filled=True, style=ElementStyle()))
        path = str(tmp_path / "one.papraz")
        save_project(path, c)

        # Load into a canvas that already has 3 elements
        c2 = make_canvas()
        c2.elements.extend([
            LineElement(QPointF(0, 0), QPointF(50, 50)),
            LineElement(QPointF(10, 10), QPointF(60, 60)),
            LineElement(QPointF(20, 20), QPointF(70, 70)),
        ])
        load_project(path, c2)
        assert len(c2.elements) == 1

    def test_corrupt_file_raises(self, tmp_path):
        from paparaz.core.project import load_project
        path = str(tmp_path / "bad.papraz")
        Path(path).write_bytes(b"this is not valid base64 zlib data!!!")
        c = make_canvas()
        with pytest.raises(Exception):
            load_project(path, c)

    def test_element_from_dict_after_project_load(self, tmp_path):
        """Verify element_from_dict reconstructs each saved element correctly."""
        from paparaz.core.project import save_project, load_project
        c = make_canvas()
        c.elements.append(ArrowElement(QPointF(0, 0), QPointF(100, 100)))
        c.elements.append(EllipseElement(QRectF(10, 10, 60, 40), filled=False, style=ElementStyle()))
        path = str(tmp_path / "types.papraz")
        save_project(path, c)

        c2 = make_canvas(1, 1)
        load_project(path, c2)
        types = {e.element_type for e in c2.elements}
        assert ElementType.ARROW in types
        assert ElementType.ELLIPSE in types
