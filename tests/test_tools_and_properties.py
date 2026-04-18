"""
Granular tests for all annotation tools and their properties.

Covers:
  - Every tool type: Select, Pen, Brush, Line, Arrow, Rectangle, Ellipse,
    Text, Numbering, Eraser, Masquerade, Fill, Stamp, Crop
  - Property changes (color, line width, opacity, shadow, font, etc.)
  - Text: word-wrap, auto-size on Enter, backspace, multi-line
  - Undo / Redo for style changes, element add/delete, move, resize
  - Canvas: paste image, paste text, resize, crop
  - Per-tool property persistence (settings save/load)
  - Settings dialog: always on top, reset tools
"""

import sys
import copy
import pytest

# Must come before any PySide6 import
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QPixmap, QMouseEvent, QKeyEvent, QFontMetrics, QFont

app = QApplication.instance() or QApplication(sys.argv)

sys.path.insert(0, "src")

from paparaz.core.elements import (
    TextElement, NumberElement, MaskElement, StampElement,
    RectElement, EllipseElement, PenElement, BrushElement,
    LineElement, ArrowElement, CurvedArrowElement, ImageElement, ElementStyle, Shadow,
    MeasureElement,
)
from paparaz.core.history import HistoryManager, Command
from paparaz.core.settings import AppSettings, SettingsManager, ToolDefaults
from paparaz.tools.base import ToolType
from paparaz.tools.select import SelectTool
from paparaz.tools.drawing import (
    PenTool, BrushTool, LineTool, ArrowTool, RectangleTool, EllipseTool,
    MeasureTool, CurvedArrowTool,
)
from paparaz.tools.special import (
    TextTool, NumberingTool, EraserTool, MasqueradeTool, FillTool, StampTool,
)
from paparaz.ui.canvas import AnnotationCanvas
from paparaz.ui.side_panel import SidePanel


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_canvas(w=600, h=400):
    bg = QPixmap(w, h)
    bg.fill(Qt.GlobalColor.white)
    return AnnotationCanvas(bg)


def make_press_event(pos: QPointF, btn=Qt.MouseButton.LeftButton):
    """Simulate a mouse press at canvas-space pos (no actual Qt event needed)."""
    return None  # tools only need QPointF; event arg is unused for key logic


class _FakeEvent:
    """Minimal mouse-event stub with no modifiers and left button."""
    def modifiers(self):
        return Qt.KeyboardModifier.NoModifier
    def buttons(self):
        return Qt.MouseButton.LeftButton
    def button(self):
        return Qt.MouseButton.LeftButton


def click(tool, pos: QPointF):
    ev = _FakeEvent()
    tool.on_press(pos, ev)
    tool.on_release(pos, ev)


def drag(tool, start: QPointF, end: QPointF):
    ev = _FakeEvent()
    tool.on_press(start, ev)
    tool.on_move(end, ev)
    tool.on_release(end, ev)


def key(tool, qt_key, text="", mods=Qt.KeyboardModifier.NoModifier):
    """Simulate a key event on a tool."""
    ev = QKeyEvent(QKeyEvent.Type.KeyPress, qt_key, mods, text)
    tool.on_key_press(ev)


# ---------------------------------------------------------------------------
# 1. TextElement – word-wrap and auto-size
# ---------------------------------------------------------------------------

class TestTextWordWrap:
    def test_wrap_lines_short_text_no_wrap(self):
        fm = QFontMetrics(QFont("Arial", 14))
        lines = TextElement._wrap_lines("hello", fm, 500)
        assert lines == ["hello"]

    def test_wrap_lines_long_text_wraps(self):
        fm = QFontMetrics(QFont("Arial", 14))
        long = "the quick brown fox jumps over the lazy dog and keeps running"
        lines = TextElement._wrap_lines(long, fm, 150)
        assert len(lines) > 1
        for line in lines:
            assert fm.horizontalAdvance(line) <= 150 or " " not in line

    def test_wrap_lines_preserves_newlines(self):
        fm = QFontMetrics(QFont("Arial", 14))
        lines = TextElement._wrap_lines("line one\nline two\nline three", fm, 1000)
        assert lines == ["line one", "line two", "line three"]

    def test_wrap_lines_empty_text(self):
        fm = QFontMetrics(QFont("Arial", 14))
        lines = TextElement._wrap_lines("", fm, 200)
        assert lines == [""]

    def test_wrap_lines_explicit_newline_empty_segment(self):
        fm = QFontMetrics(QFont("Arial", 14))
        lines = TextElement._wrap_lines("a\n\nb", fm, 500)
        assert "" in lines  # the blank line must be preserved

    def test_auto_size_expands_height_for_long_text(self):
        elem = TextElement(QPointF(0, 0), "", ElementStyle())
        orig_h = elem.rect.height()
        elem.text = "word " * 30  # definitely wraps in 150px
        elem.auto_size()
        assert elem.rect.height() > orig_h

    def test_auto_size_expands_for_multiline(self):
        elem = TextElement(QPointF(0, 0), "a\nb\nc", ElementStyle())
        elem.auto_size()
        fm = QFontMetrics(QFont(elem.style.font_family, elem.style.font_size))
        # 3 lines must be taller than default 40px
        assert elem.rect.height() >= 3 * fm.height()

    def test_auto_size_shrinks_on_delete(self):
        elem = TextElement(QPointF(0, 0), "a\nb\nc\nd\ne", ElementStyle())
        elem.auto_size()
        tall = elem.rect.height()
        elem.text = "short"
        elem.auto_size()
        assert elem.rect.height() < tall

    def test_auto_size_preserves_width(self):
        elem = TextElement(QPointF(0, 0), "some text", ElementStyle())
        orig_w = elem.rect.width()
        elem.auto_size()
        assert elem.rect.width() == orig_w


# ---------------------------------------------------------------------------
# 2. TextTool – typing, Enter, Backspace, finalize
# ---------------------------------------------------------------------------

class TestTextTool:
    def setup_method(self):
        self.canvas = make_canvas()
        self.tool = TextTool(self.canvas)
        self.canvas.set_tool(self.tool)

    def _type(self, text):
        for ch in text:
            key(self.tool, Qt.Key.Key_unknown, ch)

    def test_click_creates_active_text(self):
        self.tool.on_press(QPointF(100, 100), None)
        assert self.tool._active_text is not None
        assert self.tool._active_text.editing is True

    def test_typing_appends_text(self):
        self.tool.on_press(QPointF(50, 50), None)
        self._type("hello")
        assert self.tool._active_text.text == "hello"

    def test_backspace_removes_last_char(self):
        self.tool.on_press(QPointF(50, 50), None)
        self._type("hello")
        key(self.tool, Qt.Key.Key_Backspace)
        assert self.tool._active_text.text == "hell"

    def test_backspace_empty_does_not_crash(self):
        self.tool.on_press(QPointF(50, 50), None)
        key(self.tool, Qt.Key.Key_Backspace)
        assert self.tool._active_text.text == ""

    def test_enter_inserts_newline(self):
        self.tool.on_press(QPointF(50, 50), None)
        self._type("line1")
        key(self.tool, Qt.Key.Key_Return, "\n")
        assert "\n" in self.tool._active_text.text

    def test_enter_auto_grows_height(self):
        self.tool.on_press(QPointF(50, 50), None)
        elem = self.tool._active_text
        initial_h = elem.rect.height()
        self._type("row1")
        key(self.tool, Qt.Key.Key_Return, "\n")
        self._type("row2")
        key(self.tool, Qt.Key.Key_Return, "\n")
        self._type("row3")
        assert elem.rect.height() > initial_h

    def test_long_line_auto_wraps_height(self):
        self.tool.on_press(QPointF(50, 50), None)
        elem = self.tool._active_text
        initial_h = elem.rect.height()
        self._type("word " * 20)  # long line, should wrap
        assert elem.rect.height() >= initial_h  # must not be smaller

    def test_ctrl_enter_finalizes(self):
        self.tool.on_press(QPointF(50, 50), None)
        self._type("done")
        key(self.tool, Qt.Key.Key_Return, "", Qt.KeyboardModifier.ControlModifier)
        assert self.tool._active_text is None
        assert len(self.canvas.elements) == 1

    def test_escape_finalizes_with_text(self):
        self.tool.on_press(QPointF(50, 50), None)
        self._type("escape test")
        key(self.tool, Qt.Key.Key_Escape)
        assert self.tool._active_text is None
        assert len(self.canvas.elements) == 1

    def test_escape_with_empty_text_discards(self):
        self.tool.on_press(QPointF(50, 50), None)
        key(self.tool, Qt.Key.Key_Escape)
        assert self.tool._active_text is None
        assert len(self.canvas.elements) == 0

    def test_second_click_finalizes_previous(self):
        self.tool.on_press(QPointF(50, 50), None)
        self._type("first")
        self.tool.on_press(QPointF(200, 200), None)
        # first element was committed
        assert any(isinstance(e, TextElement) and e.text == "first"
                   for e in self.canvas.elements)

    def test_double_click_existing_re_edits(self):
        self.tool.on_press(QPointF(50, 50), None)
        self._type("edit me")
        key(self.tool, Qt.Key.Key_Escape)
        elem = self.canvas.elements[-1]
        # re-edit via start_editing
        self.tool.start_editing(elem)
        assert self.tool._active_text is elem
        assert elem.editing is True

    def test_formatting_applied_to_new_element(self):
        self.tool.set_bold(True)
        self.tool.set_italic(True)
        self.tool.on_press(QPointF(50, 50), None)
        assert self.tool._active_text.bold is True
        assert self.tool._active_text.italic is True


# ---------------------------------------------------------------------------
# 3. Drawing tools – Pen, Brush, Line, Arrow, Rect, Ellipse
# ---------------------------------------------------------------------------

class TestDrawingTools:
    def setup_method(self):
        self.canvas = make_canvas()

    def _draw(self, ToolClass, start, end):
        tool = ToolClass(self.canvas)
        self.canvas.set_tool(tool)
        drag(tool, start, end)
        return self.canvas.elements[-1] if self.canvas.elements else None

    def test_pen_creates_element(self):
        elem = self._draw(PenTool, QPointF(10, 10), QPointF(100, 100))
        assert isinstance(elem, PenElement)
        assert len(elem.points) >= 2

    def test_brush_creates_element(self):
        elem = self._draw(BrushTool, QPointF(10, 10), QPointF(100, 100))
        assert isinstance(elem, BrushElement)

    def test_line_creates_element(self):
        elem = self._draw(LineTool, QPointF(10, 10), QPointF(200, 200))
        assert isinstance(elem, LineElement)
        assert elem.start == QPointF(10, 10)
        assert elem.end == QPointF(200, 200)

    def test_arrow_creates_element(self):
        elem = self._draw(ArrowTool, QPointF(0, 0), QPointF(150, 150))
        assert isinstance(elem, ArrowElement)

    def test_rectangle_creates_element(self):
        elem = self._draw(RectangleTool, QPointF(20, 20), QPointF(120, 80))
        assert isinstance(elem, RectElement)
        assert elem.rect.width() == pytest.approx(100)
        assert elem.rect.height() == pytest.approx(60)

    def test_ellipse_creates_element(self):
        elem = self._draw(EllipseTool, QPointF(20, 20), QPointF(120, 80))
        assert isinstance(elem, EllipseElement)
        assert elem.rect.width() == pytest.approx(100)

    def test_pen_respects_color(self):
        self.canvas._fg_color = "#00ff00"
        elem = self._draw(PenTool, QPointF(0, 0), QPointF(50, 50))
        assert elem.style.foreground_color == "#00ff00"

    def test_line_respects_line_width(self):
        self.canvas._line_width = 8.0
        elem = self._draw(LineTool, QPointF(0, 0), QPointF(100, 100))
        assert elem.style.line_width == pytest.approx(8.0)

    def test_rect_fill_toggle(self):
        tool = RectangleTool(self.canvas)
        self.canvas.set_tool(tool)
        self.canvas._filled = True  # canvas carries fill state, tools read it on press
        drag(tool, QPointF(10, 10), QPointF(100, 100))
        elem = self.canvas.elements[-1]
        assert elem.filled is True


# ---------------------------------------------------------------------------
# 4. Select tool – click select, move, resize, delete
# ---------------------------------------------------------------------------

class TestSelectTool:
    def setup_method(self):
        self.canvas = make_canvas()
        self.select = SelectTool(self.canvas)
        self.canvas.set_tool(self.select)
        # Pre-add a rect element
        self.elem = RectElement(QRectF(100, 100, 100, 60), filled=True, style=ElementStyle())
        self.canvas.elements.append(self.elem)

    def test_click_selects_element(self):
        click(self.select, QPointF(150, 130))
        assert self.canvas.selected_element is self.elem

    def test_click_empty_deselects(self):
        self.canvas.selected_element = self.elem
        self.elem.selected = True
        click(self.select, QPointF(10, 10))
        assert self.canvas.selected_element is None

    def test_drag_moves_element(self):
        click(self.select, QPointF(150, 130))  # select first
        orig_x = self.elem.rect.x()
        drag(self.select, QPointF(150, 130), QPointF(200, 130))
        assert self.elem.rect.x() == pytest.approx(orig_x + 50)

    def test_delete_key_removes_element(self):
        click(self.select, QPointF(150, 130))
        ev = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Delete,
                       Qt.KeyboardModifier.NoModifier)
        self.select.on_key_press(ev)
        assert self.elem not in self.canvas.elements

    def test_move_undo(self):
        click(self.select, QPointF(150, 130))
        orig_x = self.elem.rect.x()
        drag(self.select, QPointF(150, 130), QPointF(250, 130))
        assert self.elem.rect.x() != pytest.approx(orig_x)
        self.canvas.history.undo()
        assert self.elem.rect.x() == pytest.approx(orig_x)

    def test_resize_undo(self):
        click(self.select, QPointF(150, 130))  # select
        orig_rect = QRectF(self.elem.rect)
        # Grab bottom-right handle (handle 7) and drag
        handle_pos = QPointF(self.elem.rect.right(), self.elem.rect.bottom())
        drag(self.select, handle_pos, QPointF(handle_pos.x() + 40, handle_pos.y() + 30))
        self.canvas.history.undo()
        assert self.elem.rect.width() == pytest.approx(orig_rect.width())
        assert self.elem.rect.height() == pytest.approx(orig_rect.height())


# ---------------------------------------------------------------------------
# 5. Property changes – undo / redo
# ---------------------------------------------------------------------------

class TestPropertyUndo:
    def setup_method(self):
        self.canvas = make_canvas()
        self.elem = RectElement(QRectF(50, 50, 100, 80), filled=True, style=ElementStyle())
        self.canvas.elements.append(self.elem)
        self.canvas.selected_element = self.elem

    def test_fg_color_change_undoable(self):
        orig = self.elem.style.foreground_color
        self.canvas.set_foreground_color("#aabbcc")
        assert self.elem.style.foreground_color == "#aabbcc"
        self.canvas.history.undo()
        assert self.elem.style.foreground_color == orig

    def test_line_width_change_undoable(self):
        orig = self.elem.style.line_width
        self.canvas.set_line_width(12.0)
        self.canvas.history.undo()
        assert self.elem.style.line_width == pytest.approx(orig)

    def test_opacity_change_undoable(self):
        self.canvas.set_opacity(0.3)
        self.canvas.history.undo()
        assert self.elem.style.opacity == pytest.approx(1.0)

    def test_shadow_toggle_undoable(self):
        self.canvas.set_shadow_enabled(True)
        assert self.elem.style.shadow.enabled is True
        self.canvas.history.undo()
        assert self.elem.style.shadow.enabled is False

    def test_coalesced_slider_creates_one_undo_entry(self):
        start_depth = len(self.canvas.history._undo_stack)
        for v in range(1, 20):
            self.canvas.set_line_width(float(v))
        assert len(self.canvas.history._undo_stack) == start_depth + 1

    def test_redo_after_undo(self):
        self.canvas.set_foreground_color("#ff0000")
        self.canvas.set_foreground_color("#00ff00")
        self.canvas.history.undo()
        self.canvas.history.redo()
        assert self.elem.style.foreground_color == "#00ff00"

    def test_add_element_undoable(self):
        new_elem = RectElement(QRectF(200, 200, 50, 50), filled=True, style=ElementStyle())
        self.canvas.add_element(new_elem)
        assert new_elem in self.canvas.elements
        self.canvas.history.undo()
        assert new_elem not in self.canvas.elements

    def test_delete_element_undoable(self):
        self.canvas.history.undo()  # clear any prior
        self.canvas.delete_element(self.elem)
        assert self.elem not in self.canvas.elements
        self.canvas.history.undo()
        assert self.elem in self.canvas.elements


# ---------------------------------------------------------------------------
# 6. Canvas – resize and crop (undo)
# ---------------------------------------------------------------------------

class TestCanvasOperations:
    def setup_method(self):
        self.canvas = make_canvas(400, 300)
        self.elem = RectElement(QRectF(100, 100, 50, 50), filled=True, style=ElementStyle())
        self.canvas.elements.append(self.elem)

    def test_resize_canvas_changes_background_size(self):
        self.canvas.resize_canvas(800, 600)
        assert self.canvas._background.width() == 800
        assert self.canvas._background.height() == 600

    def test_resize_canvas_shifts_elements(self):
        orig_x = self.elem.rect.x()
        self.canvas.resize_canvas(800, 600)
        ox = (800 - 400) // 2
        assert self.elem.rect.x() == pytest.approx(orig_x + ox)

    def test_resize_canvas_undoable(self):
        self.canvas.resize_canvas(800, 600)
        orig_x = 100
        self.canvas.history.undo()
        assert self.canvas._background.width() == 400
        assert self.elem.rect.x() == pytest.approx(orig_x)

    def test_crop_canvas_reduces_size(self):
        self.canvas.crop_canvas(QRectF(50, 50, 200, 150))
        assert self.canvas._background.width() == 200
        assert self.canvas._background.height() == 150

    def test_crop_canvas_shifts_elements(self):
        self.canvas.crop_canvas(QRectF(50, 50, 300, 250))
        # elem at 100,100 should now be at 50,50
        assert self.elem.rect.x() == pytest.approx(50)

    def test_crop_canvas_undoable(self):
        orig_w = self.canvas._background.width()
        self.canvas.crop_canvas(QRectF(10, 10, 200, 150))
        self.canvas.history.undo()
        assert self.canvas._background.width() == orig_w
        assert self.elem.rect.x() == pytest.approx(100)


# ---------------------------------------------------------------------------
# 7. Paste from clipboard
# ---------------------------------------------------------------------------

class TestClipboardPaste:
    def setup_method(self):
        self.canvas = make_canvas()

    def test_paste_text_creates_text_element(self):
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QClipboard
        QApplication.clipboard().setText("pasted text")
        result = self.canvas.paste_from_clipboard()
        assert result is True
        text_elems = [e for e in self.canvas.elements if isinstance(e, TextElement)]
        assert len(text_elems) == 1
        assert text_elems[0].text == "pasted text"

    def test_paste_image_creates_image_element(self):
        from PySide6.QtWidgets import QApplication
        pix = QPixmap(50, 50)
        pix.fill(Qt.GlobalColor.red)
        QApplication.clipboard().setPixmap(pix)
        result = self.canvas.paste_from_clipboard()
        assert result is True
        img_elems = [e for e in self.canvas.elements if isinstance(e, ImageElement)]
        assert len(img_elems) == 1


# ---------------------------------------------------------------------------
# 8. Numbering tool
# ---------------------------------------------------------------------------

class TestNumberingTool:
    def setup_method(self):
        self.canvas = make_canvas()
        NumberElement.reset_counter()
        self.tool = NumberingTool(self.canvas)
        self.canvas.set_tool(self.tool)

    def test_click_creates_numbered_element(self):
        click(self.tool, QPointF(100, 100))
        assert len(self.canvas.elements) == 1
        assert isinstance(self.canvas.elements[0], NumberElement)
        assert self.canvas.elements[0].number == 1

    def test_auto_increment(self):
        click(self.tool, QPointF(50, 50))
        click(self.tool, QPointF(150, 50))
        click(self.tool, QPointF(250, 50))
        numbers = [e.number for e in self.canvas.elements]
        assert numbers == [1, 2, 3]

    def test_delete_and_undo_preserves_count(self):
        click(self.tool, QPointF(50, 50))
        click(self.tool, QPointF(150, 50))
        self.canvas.delete_element(self.canvas.elements[-1])
        self.canvas.history.undo()
        assert len(self.canvas.elements) == 2


# ---------------------------------------------------------------------------
# 9. Stamp tool
# ---------------------------------------------------------------------------

class TestStampTool:
    def setup_method(self):
        self.canvas = make_canvas()
        self.tool = StampTool(self.canvas)
        self.canvas.set_tool(self.tool)

    def test_click_creates_stamp_element(self):
        click(self.tool, QPointF(100, 100))
        assert len(self.canvas.elements) == 1
        assert isinstance(self.canvas.elements[0], StampElement)

    def test_stamp_id_applied(self):
        self.tool.stamp_id = "star"
        click(self.tool, QPointF(100, 100))
        assert self.canvas.elements[0].stamp_id == "star"

    def test_stamp_size_applied(self):
        self.tool.stamp_size = 80
        click(self.tool, QPointF(100, 100))
        assert self.canvas.elements[0].size == pytest.approx(80)


# ---------------------------------------------------------------------------
# 10. Masquerade (blur) tool
# ---------------------------------------------------------------------------

class TestMasqueradeTool:
    def setup_method(self):
        self.canvas = make_canvas()
        self.tool = MasqueradeTool(self.canvas)
        self.canvas.set_tool(self.tool)

    def test_drag_creates_mask_element(self):
        drag(self.tool, QPointF(50, 50), QPointF(200, 150))
        assert len(self.canvas.elements) == 1
        assert isinstance(self.canvas.elements[0], MaskElement)

    def test_pixel_size_applied(self):
        self.tool.pixel_size = 20
        drag(self.tool, QPointF(50, 50), QPointF(200, 150))
        assert self.canvas.elements[0].pixel_size == 20


# ---------------------------------------------------------------------------
# 11. History – coalescing
# ---------------------------------------------------------------------------

class TestHistoryCoalescing:
    def test_coalesce_key_merges_entries(self):
        h = HistoryManager()
        log = []
        for i in range(10):
            val = i * 5
            old = 0
            def do(v=val): log.append(("do", v))
            def undo(v=old): log.append(("undo", v))
            h.record(Command(f"val={val}", do, undo), coalesce_key="test_val")
        assert len(h._undo_stack) == 1

    def test_different_keys_not_merged(self):
        h = HistoryManager()
        for i, k in enumerate(["a", "b", "c"]):
            h.record(Command(k, lambda: None, lambda: None), coalesce_key=k)
        assert len(h._undo_stack) == 3

    def test_undo_after_coalesce_restores_original(self):
        h = HistoryManager()
        state = {"v": 0}
        for i in range(5):
            captured_new = i
            h.record(
                Command(f"set {i}",
                        lambda v=captured_new: state.update(v=v),
                        lambda: state.update(v=0)),
                coalesce_key="v")
        h.undo()
        assert state["v"] == 0

    def test_redo_applies_latest_value(self):
        h = HistoryManager()
        state = {"v": 0}
        for i in range(1, 6):
            h.record(
                Command(f"set {i}",
                        lambda v=i: state.update(v=v),
                        lambda: state.update(v=0)),
                coalesce_key="v")
        h.undo()
        h.redo()
        assert state["v"] == 5


# ---------------------------------------------------------------------------
# 12. Settings – per-tool property persistence
# ---------------------------------------------------------------------------

class TestPerToolPersistence:
    def setup_method(self):
        self.sm = SettingsManager.__new__(SettingsManager)
        self.sm.settings = AppSettings()
        self.sm._path = None  # don't write to disk

    def test_tool_properties_initially_empty(self):
        assert self.sm.settings.tool_properties == {}

    def test_tool_properties_can_be_set(self):
        self.sm.settings.tool_properties["PEN"] = {
            "foreground_color": "#123456",
            "line_width": 7,
        }
        assert self.sm.settings.tool_properties["PEN"]["line_width"] == 7

    def test_side_panel_get_current_properties(self):
        sp = SidePanel()
        from paparaz.tools.base import ToolType
        sp.update_for_tool(ToolType.PEN)
        props = sp.get_current_properties()
        assert "foreground_color" in props
        assert "line_width" in props

    def test_side_panel_apply_properties_silent(self):
        sp = SidePanel()
        sp.update_for_tool(ToolType.PEN)
        sp.apply_properties_silent({"foreground_color": "#abcdef", "line_width": 9})
        assert sp._fg_color == "#abcdef"
        assert sp._width_slider.value() == 9

    def test_apply_silent_does_not_emit_signals(self):
        sp = SidePanel()
        sp.update_for_tool(ToolType.PEN)
        emitted = []
        sp.fg_color_changed.connect(lambda c: emitted.append(c))
        sp.apply_properties_silent({"foreground_color": "#aaaaaa"})
        assert emitted == []  # signal must NOT fire during silent apply

    def test_reset_tool_properties(self):
        self.sm.settings.tool_properties["PEN"] = {"foreground_color": "#ff0000"}
        self.sm.settings.tool_properties.clear()
        assert self.sm.settings.tool_properties == {}


# ---------------------------------------------------------------------------
# 13. Settings dialog – always on top
# ---------------------------------------------------------------------------

class TestSettingsDialog:
    def test_dialog_is_a_qdialog(self):
        from paparaz.ui.settings_dialog import SettingsDialog
        sm = SettingsManager.__new__(SettingsManager)
        sm.settings = AppSettings()
        sm._path = None
        dlg = SettingsDialog(sm)
        assert bool(dlg.windowFlags() & Qt.WindowType.Dialog)

    def test_dialog_reset_clears_tool_properties(self):
        from paparaz.ui.settings_dialog import SettingsDialog
        sm = SettingsManager.__new__(SettingsManager)
        sm.settings = AppSettings()
        sm._path = None
        sm.settings.tool_properties["PEN"] = {"foreground_color": "#ff0000"}

        class _FakeSave:
            called = False
        def fake_save():
            _FakeSave.called = True
        sm.save = fake_save

        dlg = SettingsDialog(sm)
        dlg._reset_tool_memory()
        assert sm.settings.tool_properties == {}
        assert _FakeSave.called


# ---------------------------------------------------------------------------
# 14. Element bounding rects and contains_point
# ---------------------------------------------------------------------------

class TestElementGeometry:
    def test_rect_contains_center(self):
        elem = RectElement(QRectF(50, 50, 100, 80), filled=True, style=ElementStyle())
        assert elem.contains_point(QPointF(100, 90))

    def test_rect_does_not_contain_outside(self):
        elem = RectElement(QRectF(50, 50, 100, 80), filled=True, style=ElementStyle())
        assert not elem.contains_point(QPointF(10, 10))

    def test_text_bounding_rect(self):
        elem = TextElement(QPointF(30, 40), "hi", ElementStyle())
        br = elem.bounding_rect()
        assert br.x() == pytest.approx(30)
        assert br.y() == pytest.approx(40)

    def test_number_bounding_rect(self):
        elem = NumberElement(QPointF(100, 100), number=1, size=30)
        br = elem.bounding_rect()
        assert br.contains(QPointF(100, 100))

    def test_line_bounding_rect(self):
        elem = LineElement(QPointF(0, 0), QPointF(200, 200), ElementStyle())
        br = elem.bounding_rect()
        assert br.width() > 0
        assert br.height() > 0

    def test_move_by(self):
        elem = RectElement(QRectF(0, 0, 100, 100), filled=True, style=ElementStyle())
        elem.move_by(25, 30)
        assert elem.rect.x() == pytest.approx(25)
        assert elem.rect.y() == pytest.approx(30)


# ---------------------------------------------------------------------------
# 15. Snap engine
# ---------------------------------------------------------------------------

from paparaz.core.snap import snap_move, snap_point, SnapGuide


class TestSnapEngine:
    """Tests for the snap-to-edges/grid engine."""

    def test_snap_to_canvas_left_edge(self):
        canvas = QRectF(0, 0, 800, 600)
        elem = QRectF(5, 100, 50, 30)  # left=5, close to 0
        offset, guides = snap_move(elem, canvas, [], threshold=8)
        assert offset.x() == pytest.approx(-5)
        assert any(g.orientation == "v" for g in guides)

    def test_snap_to_canvas_right_edge(self):
        canvas = QRectF(0, 0, 800, 600)
        elem = QRectF(745, 100, 50, 30)  # right=795, close to 800
        offset, guides = snap_move(elem, canvas, [], threshold=8)
        assert offset.x() == pytest.approx(5)

    def test_snap_to_canvas_top_edge(self):
        canvas = QRectF(0, 0, 800, 600)
        elem = QRectF(100, 3, 50, 30)  # top=3, close to 0
        offset, guides = snap_move(elem, canvas, [], threshold=8)
        assert offset.y() == pytest.approx(-3)

    def test_snap_to_canvas_bottom_edge(self):
        canvas = QRectF(0, 0, 800, 600)
        elem = QRectF(100, 565, 50, 30)  # bottom=595, close to 600
        offset, guides = snap_move(elem, canvas, [], threshold=8)
        assert offset.y() == pytest.approx(5)

    def test_snap_to_canvas_center(self):
        canvas = QRectF(0, 0, 800, 600)
        # center_x of elem = 127, canvas center = 400
        # elem left=102 close to nothing, right=152 close to nothing
        # center_y of elem = 303, canvas center = 300, diff=3 < threshold
        elem = QRectF(102, 288, 50, 30)  # cy = 303
        offset, guides = snap_move(elem, canvas, [], threshold=8)
        assert offset.y() == pytest.approx(-3)

    def test_no_snap_when_far(self):
        canvas = QRectF(0, 0, 800, 600)
        elem = QRectF(200, 200, 50, 30)
        offset, guides = snap_move(elem, canvas, [], threshold=8)
        assert abs(offset.x()) < 0.01
        assert abs(offset.y()) < 0.01
        assert len(guides) == 0

    def test_snap_to_other_element_edge(self):
        canvas = QRectF(0, 0, 800, 600)
        other = [QRectF(200, 200, 60, 40)]  # right=260
        elem = QRectF(253, 150, 50, 30)     # left=253, close to 260
        offset, guides = snap_move(elem, canvas, other, threshold=8)
        assert offset.x() == pytest.approx(7)

    def test_snap_to_grid(self):
        canvas = QRectF(0, 0, 800, 600)
        elem = QRectF(18, 42, 50, 30)  # left=18, nearest grid=20
        offset, guides = snap_move(elem, canvas, [], threshold=8,
                                   snap_to_canvas=False, grid_size=20)
        assert offset.x() == pytest.approx(2)

    def test_snap_disabled_returns_zero(self):
        canvas = QRectF(0, 0, 800, 600)
        elem = QRectF(5, 5, 50, 30)  # very close to edges
        offset, guides = snap_move(elem, canvas, [], threshold=0)
        # threshold=0 effectively disables snapping
        assert len(guides) == 0

    def test_snap_to_canvas_disabled(self):
        canvas = QRectF(0, 0, 800, 600)
        elem = QRectF(5, 5, 50, 30)
        offset, guides = snap_move(elem, canvas, [], threshold=8,
                                   snap_to_canvas=False)
        assert abs(offset.x()) < 0.01
        assert abs(offset.y()) < 0.01

    def test_snap_to_elements_disabled(self):
        canvas = QRectF(0, 0, 800, 600)
        other = [QRectF(55, 100, 60, 40)]  # right=115
        elem = QRectF(110, 150, 50, 30)    # left=110, close to 115
        offset, guides = snap_move(elem, canvas, other, threshold=8,
                                   snap_to_elements=False)
        # Should NOT snap to element (110 is far from canvas edges)
        assert abs(offset.x()) < 0.01

    def test_snap_point_to_canvas_edge(self):
        canvas = QRectF(0, 0, 800, 600)
        pt = QPointF(3, 597)
        snapped, guides = snap_point(pt, canvas, [], threshold=8)
        assert snapped.x() == pytest.approx(0)
        assert snapped.y() == pytest.approx(600)

    def test_snap_point_to_element(self):
        canvas = QRectF(0, 0, 800, 600)
        other = [QRectF(100, 100, 50, 30)]  # right=150, bottom=130
        pt = QPointF(147, 128)
        snapped, guides = snap_point(pt, canvas, other, threshold=8)
        assert snapped.x() == pytest.approx(150)
        assert snapped.y() == pytest.approx(130)

    def test_guide_lines_generated(self):
        canvas = QRectF(0, 0, 800, 600)
        elem = QRectF(5, 5, 50, 30)
        offset, guides = snap_move(elem, canvas, [], threshold=8)
        assert len(guides) >= 1
        for g in guides:
            assert g.orientation in ("h", "v")
            assert g.start < g.end

    def test_snap_both_axes(self):
        canvas = QRectF(0, 0, 800, 600)
        elem = QRectF(3, 4, 50, 30)  # close to both left=0 and top=0
        offset, guides = snap_move(elem, canvas, [], threshold=8)
        assert offset.x() == pytest.approx(-3)
        assert offset.y() == pytest.approx(-4)
        assert len(guides) == 2


# ---------------------------------------------------------------------------
# 16. Settings — snap fields
# ---------------------------------------------------------------------------

class TestSettingsSnap:
    """Tests that snap settings are correctly persisted."""

    def test_default_snap_settings(self):
        s = AppSettings()
        assert s.snap_enabled is True
        assert s.snap_to_canvas is True
        assert s.snap_to_elements is True
        assert s.snap_threshold == 8
        assert s.snap_grid_enabled is False
        assert s.snap_grid_size == 20
        assert s.show_grid is False

    def test_snap_settings_roundtrip(self):
        import json, tempfile, os
        from pathlib import Path
        tmpf = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        tmpf.close()
        try:
            sm = SettingsManager(Path(tmpf.name))
            sm.settings.snap_enabled = False
            sm.settings.snap_threshold = 12
            sm.settings.snap_grid_enabled = True
            sm.settings.snap_grid_size = 40
            sm.settings.show_grid = True
            sm.save()

            sm2 = SettingsManager(Path(tmpf.name))
            assert sm2.settings.snap_enabled is False
            assert sm2.settings.snap_threshold == 12
            assert sm2.settings.snap_grid_enabled is True
            assert sm2.settings.snap_grid_size == 40
            assert sm2.settings.show_grid is True
        finally:
            os.unlink(tmpf.name)


# ---------------------------------------------------------------------------
# 17. Canvas snap integration
# ---------------------------------------------------------------------------

class TestCanvasSnap:
    """Tests that canvas snap properties are set correctly."""

    def test_canvas_has_snap_attributes(self):
        c = make_canvas()
        assert hasattr(c, 'snap_enabled')
        assert hasattr(c, 'snap_to_canvas')
        assert hasattr(c, 'snap_to_elements')
        assert hasattr(c, 'snap_threshold')
        assert hasattr(c, 'snap_grid_enabled')
        assert hasattr(c, 'snap_grid_size')
        assert hasattr(c, 'show_grid')
        assert hasattr(c, '_snap_guides')

    def test_canvas_snap_defaults(self):
        c = make_canvas()
        assert c.snap_enabled is True
        assert c.snap_threshold == 8

    def test_canvas_rect_method(self):
        c = make_canvas(800, 600)
        cr = c.canvas_rect()
        assert cr.width() == 800
        assert cr.height() == 600

    def test_snap_guides_cleared_on_select_release(self):
        c = make_canvas()
        select = SelectTool(c)
        c._snap_guides = [SnapGuide("v", 100, 0, 600)]
        # Simulate release
        ev = _FakeEvent()
        select.on_release(QPointF(100, 100), ev)
        assert c._snap_guides == []


# ---------------------------------------------------------------------------
# 18. Select tool with snap
# ---------------------------------------------------------------------------

class TestSelectToolSnap:
    """Tests that snapping works during element dragging."""

    def setup_method(self):
        self.canvas = make_canvas(800, 600)
        self.select = SelectTool(self.canvas)
        self.canvas.set_tool(self.select)
        # Add a rect near the left edge
        self.elem = RectElement(QRectF(100, 100, 50, 30), filled=True, style=ElementStyle())
        self.canvas.add_element(self.elem)

    def test_drag_near_edge_snaps(self):
        """Dragging an element close to canvas edge should snap."""
        ev = _FakeEvent()
        # Select the element
        self.select.on_press(QPointF(125, 115), ev)
        self.select.on_release(QPointF(125, 115), ev)
        assert self.canvas.selected_element is self.elem

        # Drag it to near the left edge (left would be at 5)
        self.select.on_press(QPointF(125, 115), ev)
        # Move to x=30 (element left would be at 5, snap to 0)
        self.select.on_move(QPointF(30, 115), ev)
        # Element should have snapped
        assert len(self.canvas._snap_guides) > 0
        self.select.on_release(QPointF(30, 115), ev)
        # Guides cleared after release
        assert self.canvas._snap_guides == []

    def test_snap_disabled_no_guides(self):
        """With snap disabled, no guides should be generated."""
        self.canvas.snap_enabled = False
        ev = _FakeEvent()
        self.select.on_press(QPointF(125, 115), ev)
        self.select.on_release(QPointF(125, 115), ev)
        self.select.on_press(QPointF(125, 115), ev)
        self.select.on_move(QPointF(5, 115), ev)
        assert self.canvas._snap_guides == []
        self.select.on_release(QPointF(5, 115), ev)


# ---------------------------------------------------------------------------
# 19. Side panel animation
# ---------------------------------------------------------------------------

class TestSidePanelAnimation:
    """Tests that side panel fade animation objects exist."""

    def test_panel_has_fade_animation(self):
        panel = SidePanel()
        assert hasattr(panel, '_fade_anim')
        assert hasattr(panel, '_fade_target_visible')

    def test_panel_fade_anim_duration(self):
        panel = SidePanel()
        assert panel._fade_anim.duration() == 150


# ---------------------------------------------------------------------------
# 20. History (undo/redo) edge cases
# ---------------------------------------------------------------------------

class TestHistoryEdgeCases:
    def test_undo_empty_stack(self):
        from paparaz.core.history import HistoryManager
        h = HistoryManager()
        assert h.can_undo is False
        assert h.undo() is False

    def test_redo_empty_stack(self):
        from paparaz.core.history import HistoryManager
        h = HistoryManager()
        assert h.can_redo is False
        assert h.redo() is False

    def test_record_and_undo(self):
        from paparaz.core.history import HistoryManager, Command
        h = HistoryManager()
        state = {"val": 1}
        def do_it(): state["val"] = 2
        def undo_it(): state["val"] = 1
        do_it()
        h.record(Command("test", do_it, undo_it))
        assert state["val"] == 2
        h.undo()
        assert state["val"] == 1
        h.redo()
        assert state["val"] == 2

    def test_new_action_clears_redo(self):
        from paparaz.core.history import HistoryManager, Command
        h = HistoryManager()
        state = {"val": 0}
        h.record(Command("a", lambda: None, lambda: None))
        h.record(Command("b", lambda: None, lambda: None))
        h.undo()
        assert h.can_redo is True
        h.record(Command("c", lambda: None, lambda: None))
        assert h.can_redo is False


# ---------------------------------------------------------------------------
# 21. Filename pattern module
# ---------------------------------------------------------------------------

class TestFilenamePattern:
    def test_basic_pattern(self):
        from paparaz.core.filename_pattern import resolve
        result = resolve("{yyyy}-{MM}-{dd}")
        assert len(result) == 10  # e.g. "2026-04-01"
        assert result[4] == "-"

    def test_counter_token(self):
        from paparaz.core.filename_pattern import resolve
        result = resolve("shot_{n}", counter=42)
        assert "42" in result

    def test_counter_padded(self):
        from paparaz.core.filename_pattern import resolve
        result = resolve("shot_{n:4}", counter=7)
        assert result == "shot_0007"

    def test_dimensions_token(self):
        from paparaz.core.filename_pattern import resolve
        result = resolve("{w}x{h}", width=1920, height=1080)
        assert result == "1920x1080"

    def test_preview_returns_string(self):
        from paparaz.core.filename_pattern import preview
        result = preview("{yyyy}-{MM}-{dd}_{HH}-{mm}-{ss}")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_empty_pattern_returns_fallback(self):
        from paparaz.core.filename_pattern import resolve
        result = resolve("")
        assert isinstance(result, str)
        assert len(result) > 0  # empty pattern returns a fallback

    def test_literal_text(self):
        from paparaz.core.filename_pattern import resolve
        result = resolve("screenshot")
        assert result == "screenshot"

    def test_host_token(self):
        from paparaz.core.filename_pattern import resolve
        import platform
        result = resolve("{host}")
        assert result.lower() == platform.node().lower()


# ---------------------------------------------------------------------------
# 22. Element rotation and geometry
# ---------------------------------------------------------------------------

class TestElementRotation:
    def test_rotate_point_360_returns_original(self):
        from paparaz.core.elements import _rotate_point
        pt = QPointF(100, 50)
        center = QPointF(75, 75)
        rotated = _rotate_point(pt, center, 360)
        assert rotated.x() == pytest.approx(pt.x(), abs=0.01)
        assert rotated.y() == pytest.approx(pt.y(), abs=0.01)

    def test_rotate_point_180(self):
        from paparaz.core.elements import _rotate_point
        pt = QPointF(100, 50)
        center = QPointF(75, 75)
        rotated = _rotate_point(pt, center, 180)
        assert rotated.x() == pytest.approx(50, abs=0.01)
        assert rotated.y() == pytest.approx(100, abs=0.01)

    def test_rotated_element_contains_center(self):
        elem = RectElement(QRectF(50, 50, 100, 80), filled=True, style=ElementStyle())
        elem.rotation = 45
        # Center should still be inside
        center = QPointF(100, 90)
        assert elem.contains_point(center)

    def test_handle_at_detects_corners(self):
        elem = RectElement(QRectF(100, 100, 200, 150), filled=True, style=ElementStyle())
        elem.selected = True
        # Top-left corner handle
        handle = elem.handle_at(QPointF(100, 100))
        assert handle is not None

    def test_handle_at_returns_none_for_center(self):
        elem = RectElement(QRectF(100, 100, 200, 150), filled=True, style=ElementStyle())
        elem.selected = True
        handle = elem.handle_at(QPointF(200, 175))  # center
        assert handle is None


# ---------------------------------------------------------------------------
# 23. Drawing tool edge cases
# ---------------------------------------------------------------------------

class TestDrawingToolEdgeCases:
    """Targeted tests for edge cases in drawing tools."""

    def setup_method(self):
        self.canvas = make_canvas()

    # ── LineTool / ArrowTool / MeasureTool: zero-length guard ────────────────

    def test_line_zero_length_not_added(self):
        """A click without drag (start == end) must not add a LineElement."""
        tool = LineTool(self.canvas)
        self.canvas.set_tool(tool)
        click(tool, QPointF(100, 100))
        assert len(self.canvas.elements) == 0

    def test_arrow_zero_length_not_added(self):
        """A zero-length arrow must not be added to the canvas."""
        tool = ArrowTool(self.canvas)
        self.canvas.set_tool(tool)
        click(tool, QPointF(100, 100))
        assert len(self.canvas.elements) == 0

    def test_measure_zero_length_not_added(self):
        """A zero-length measure drag must not be added to the canvas."""
        tool = MeasureTool(self.canvas)
        self.canvas.set_tool(tool)
        click(tool, QPointF(50, 50))
        assert len(self.canvas.elements) == 0

    def test_line_near_zero_length_not_added(self):
        """A line shorter than _MIN_LENGTH_SQ (2 px) must not be added."""
        tool = LineTool(self.canvas)
        self.canvas.set_tool(tool)
        drag(tool, QPointF(100, 100), QPointF(101, 100))  # 1 px, < 2 px threshold
        assert len(self.canvas.elements) == 0

    def test_line_exactly_min_length_added(self):
        """A line of exactly 2 px (sqrt(4)) must be added."""
        tool = LineTool(self.canvas)
        self.canvas.set_tool(tool)
        drag(tool, QPointF(100, 100), QPointF(102, 100))  # 2 px, == threshold
        assert len(self.canvas.elements) == 1

    # ── LineTool / ArrowTool: on_release without on_press ────────────────────

    def test_line_release_without_press_no_crash(self):
        """Calling on_release before on_press must not raise."""
        tool = LineTool(self.canvas)
        self.canvas.set_tool(tool)
        ev = _FakeEvent()
        tool.on_release(QPointF(100, 100), ev)  # no prior on_press
        assert len(self.canvas.elements) == 0

    def test_arrow_release_without_press_no_crash(self):
        """Calling on_release before on_press must not raise."""
        tool = ArrowTool(self.canvas)
        self.canvas.set_tool(tool)
        ev = _FakeEvent()
        tool.on_release(QPointF(100, 100), ev)
        assert len(self.canvas.elements) == 0

    def test_measure_release_without_press_no_crash(self):
        """Calling on_release before on_press must not raise."""
        tool = MeasureTool(self.canvas)
        self.canvas.set_tool(tool)
        ev = _FakeEvent()
        tool.on_release(QPointF(100, 100), ev)
        assert len(self.canvas.elements) == 0

    # ── PenTool: on_move before on_press ─────────────────────────────────────

    def test_pen_move_without_press_no_crash(self):
        """on_move before on_press must not raise (self._current is None)."""
        tool = PenTool(self.canvas)
        self.canvas.set_tool(tool)
        ev = _FakeEvent()
        tool.on_move(QPointF(50, 50), ev)  # no prior on_press
        assert len(self.canvas.elements) == 0

    def test_pen_release_without_press_no_crash(self):
        """on_release before on_press must not raise."""
        tool = PenTool(self.canvas)
        self.canvas.set_tool(tool)
        ev = _FakeEvent()
        tool.on_release(QPointF(50, 50), ev)
        assert len(self.canvas.elements) == 0

    # ── RectangleTool: negative dimensions (drag left/up) ────────────────────

    def test_rect_drag_left_creates_element(self):
        """Dragging left of start (negative width) must still create a valid rect."""
        tool = RectangleTool(self.canvas)
        self.canvas.set_tool(tool)
        # Drag from (200, 100) to (50, 200) — width would be negative raw
        drag(tool, QPointF(200, 100), QPointF(50, 200))
        assert len(self.canvas.elements) == 1
        elem = self.canvas.elements[0]
        assert isinstance(elem, RectElement)

    def test_rect_drag_left_stored_rect_normalized(self):
        """Committed RectElement must have non-negative width and height."""
        tool = RectangleTool(self.canvas)
        self.canvas.set_tool(tool)
        drag(tool, QPointF(200, 150), QPointF(50, 50))  # left & up
        assert len(self.canvas.elements) == 1
        elem = self.canvas.elements[0]
        # The stored rect must be normalized (non-negative dimensions)
        assert elem.rect.width() >= 0, "RectElement.rect.width() must be >= 0 after commit"
        assert elem.rect.height() >= 0, "RectElement.rect.height() must be >= 0 after commit"

    def test_rect_drag_left_correct_bounds(self):
        """After dragging left, the rect bounds must match the normalized region."""
        tool = RectangleTool(self.canvas)
        self.canvas.set_tool(tool)
        drag(tool, QPointF(200, 100), QPointF(50, 200))
        elem = self.canvas.elements[0]
        r = elem.rect
        assert r.left() == pytest.approx(50)
        assert r.top() == pytest.approx(100)
        assert r.width() == pytest.approx(150)
        assert r.height() == pytest.approx(100)

    def test_ellipse_drag_left_stored_rect_normalized(self):
        """Committed EllipseElement must have non-negative width and height."""
        tool = EllipseTool(self.canvas)
        self.canvas.set_tool(tool)
        drag(tool, QPointF(200, 150), QPointF(50, 50))
        assert len(self.canvas.elements) == 1
        elem = self.canvas.elements[0]
        assert elem.rect.width() >= 0, "EllipseElement.rect.width() must be >= 0 after commit"
        assert elem.rect.height() >= 0, "EllipseElement.rect.height() must be >= 0 after commit"

    def test_ellipse_drag_left_correct_bounds(self):
        """After dragging left, the ellipse rect bounds must match the normalized region."""
        tool = EllipseTool(self.canvas)
        self.canvas.set_tool(tool)
        drag(tool, QPointF(200, 100), QPointF(50, 200))
        elem = self.canvas.elements[0]
        r = elem.rect
        assert r.left() == pytest.approx(50)
        assert r.top() == pytest.approx(100)
        assert r.width() == pytest.approx(150)
        assert r.height() == pytest.approx(100)

    def test_rect_move_by_after_negative_drag(self):
        """move_by on a committed rect (dragged left) must shift correctly."""
        tool = RectangleTool(self.canvas)
        self.canvas.set_tool(tool)
        drag(tool, QPointF(200, 100), QPointF(50, 200))
        elem = self.canvas.elements[0]
        original_left = elem.rect.left()
        elem.move_by(10, 0)
        assert elem.rect.left() == pytest.approx(original_left + 10)

    # ── RectangleTool / EllipseTool: on_release without on_press ─────────────

    def test_rect_release_without_press_no_crash(self):
        """Calling on_release before on_press must not raise."""
        tool = RectangleTool(self.canvas)
        self.canvas.set_tool(tool)
        ev = _FakeEvent()
        tool.on_release(QPointF(100, 100), ev)
        assert len(self.canvas.elements) == 0

    def test_ellipse_release_without_press_no_crash(self):
        """Calling on_release before on_press must not raise."""
        tool = EllipseTool(self.canvas)
        self.canvas.set_tool(tool)
        ev = _FakeEvent()
        tool.on_release(QPointF(100, 100), ev)
        assert len(self.canvas.elements) == 0

    # ── MeasureTool: distance calculations ───────────────────────────────────

    def test_measure_horizontal_distance(self):
        """MeasureElement _distance must be correct for a horizontal line."""
        elem = MeasureElement(QPointF(0, 100), QPointF(150, 100), ElementStyle())
        assert elem._distance == pytest.approx(150.0)

    def test_measure_vertical_distance(self):
        """MeasureElement _distance must be correct for a vertical line."""
        elem = MeasureElement(QPointF(100, 0), QPointF(100, 200), ElementStyle())
        assert elem._distance == pytest.approx(200.0)

    def test_measure_diagonal_distance(self):
        """MeasureElement _distance must be correct for a diagonal line (3-4-5 triple)."""
        elem = MeasureElement(QPointF(0, 0), QPointF(30, 40), ElementStyle())
        assert elem._distance == pytest.approx(50.0)

    def test_measure_zero_distance(self):
        """MeasureElement _distance must be 0 for a zero-length line."""
        elem = MeasureElement(QPointF(100, 100), QPointF(100, 100), ElementStyle())
        assert elem._distance == pytest.approx(0.0)

    # ── CurvedArrowTool: short / degenerate drags ─────────────────────────────

    def test_curved_arrow_same_start_end_not_added(self):
        """Clicking the same point for start and end must not add a degenerate element."""
        tool = CurvedArrowTool(self.canvas)
        self.canvas.set_tool(tool)
        ev = _FakeEvent()
        pos = QPointF(100, 100)
        # Phase 1: set start
        tool.on_press(pos, ev)
        # Phase 2: set end at SAME position
        tool.on_press(pos, ev)
        # Phase 3: commit
        tool.on_press(pos, ev)
        assert len(self.canvas.elements) == 0, (
            "CurvedArrowTool must not commit a degenerate (zero-length) element"
        )

    def test_curved_arrow_short_drag_not_added(self):
        """A very short curved arrow (< 2 px) must not be added."""
        tool = CurvedArrowTool(self.canvas)
        self.canvas.set_tool(tool)
        ev = _FakeEvent()
        start = QPointF(100, 100)
        end = QPointF(101, 100)   # 1 px apart
        tool.on_press(start, ev)
        tool.on_press(end, ev)
        tool.on_press(QPointF(105, 90), ev)  # commit
        assert len(self.canvas.elements) == 0, (
            "CurvedArrowTool must not commit a near-zero-length element"
        )

    def test_curved_arrow_normal_drag_added(self):
        """A normal curved arrow must be committed on third click."""
        tool = CurvedArrowTool(self.canvas)
        self.canvas.set_tool(tool)
        ev = _FakeEvent()
        tool.on_press(QPointF(50, 100), ev)   # start
        tool.on_press(QPointF(250, 100), ev)  # end
        tool.on_press(QPointF(150, 50), ev)   # control / commit
        assert len(self.canvas.elements) == 1
        assert isinstance(self.canvas.elements[0], CurvedArrowElement)

    def test_curved_arrow_esc_cancels(self):
        """Pressing Escape during phase 2 must discard the preview."""
        tool = CurvedArrowTool(self.canvas)
        self.canvas.set_tool(tool)
        ev = _FakeEvent()
        tool.on_press(QPointF(50, 100), ev)   # set start
        tool.on_press(QPointF(250, 100), ev)  # set end → phase CTRL
        key(tool, Qt.Key.Key_Escape)
        assert tool._phase == CurvedArrowTool._PHASE_IDLE
        assert len(self.canvas.elements) == 0


# ---------------------------------------------------------------------------
# 24. MeasureElement — dedicated unit tests
# ---------------------------------------------------------------------------

import math as _math


class TestMeasureElement:
    """Dedicated unit tests for MeasureElement geometry, serialisation, paint."""

    # ── Construction ─────────────────────────────────────────────────────────

    def test_default_construction(self):
        elem = MeasureElement()
        assert elem.start == QPointF(0, 0)
        assert elem.end == QPointF(0, 0)

    def test_construction_with_points(self):
        elem = MeasureElement(QPointF(10, 20), QPointF(110, 20), ElementStyle())
        assert elem.start == QPointF(10, 20)
        assert elem.end == QPointF(110, 20)

    # ── Distance property ─────────────────────────────────────────────────────

    def test_distance_zero(self):
        elem = MeasureElement(QPointF(5, 5), QPointF(5, 5), ElementStyle())
        assert elem._distance == pytest.approx(0.0)

    def test_distance_horizontal(self):
        elem = MeasureElement(QPointF(0, 0), QPointF(150, 0), ElementStyle())
        assert elem._distance == pytest.approx(150.0)

    def test_distance_vertical(self):
        elem = MeasureElement(QPointF(0, 0), QPointF(0, 80), ElementStyle())
        assert elem._distance == pytest.approx(80.0)

    def test_distance_pythagorean_triple(self):
        """3-4-5 * 20 → distance == 100."""
        elem = MeasureElement(QPointF(0, 0), QPointF(60, 80), ElementStyle())
        assert elem._distance == pytest.approx(100.0)

    def test_distance_is_symmetric(self):
        """Distance is identical regardless of start/end order."""
        a = MeasureElement(QPointF(0, 0), QPointF(30, 40), ElementStyle())
        b = MeasureElement(QPointF(30, 40), QPointF(0, 0), ElementStyle())
        assert a._distance == pytest.approx(b._distance)

    def test_distance_uses_euclidean_not_manhattan(self):
        """Verify Euclidean (not Manhattan) distance for a 45-degree line."""
        elem = MeasureElement(QPointF(0, 0), QPointF(10, 10), ElementStyle())
        expected = _math.sqrt(200)
        assert elem._distance == pytest.approx(expected)

    # ── Bounding rect ─────────────────────────────────────────────────────────

    def test_bounding_rect_non_empty_for_valid_line(self):
        elem = MeasureElement(QPointF(0, 0), QPointF(200, 0), ElementStyle())
        br = elem.bounding_rect()
        assert br.width() > 0
        assert br.height() > 0

    def test_bounding_rect_contains_start_and_end(self):
        elem = MeasureElement(QPointF(50, 80), QPointF(250, 80), ElementStyle())
        br = elem.bounding_rect()
        assert br.contains(QPointF(50, 80))
        assert br.contains(QPointF(250, 80))

    def test_bounding_rect_has_padding(self):
        """Bounding rect must extend beyond the raw segment (padding for ticks & label)."""
        elem = MeasureElement(QPointF(100, 100), QPointF(200, 100), ElementStyle())
        raw = QRectF(QPointF(100, 100), QPointF(200, 100)).normalized()
        br = elem.bounding_rect()
        assert br.left() < raw.left()
        assert br.right() > raw.right()

    def test_bounding_rect_diagonal(self):
        """Diagonal element bounding rect must enclose both endpoints."""
        elem = MeasureElement(QPointF(0, 0), QPointF(300, 400), ElementStyle())
        br = elem.bounding_rect()
        assert br.contains(QPointF(0, 0))
        assert br.contains(QPointF(300, 400))

    # ── contains_point ────────────────────────────────────────────────────────

    def test_contains_point_midpoint(self):
        elem = MeasureElement(QPointF(0, 100), QPointF(200, 100), ElementStyle())
        assert elem.contains_point(QPointF(100, 100))

    def test_contains_point_far_away(self):
        elem = MeasureElement(QPointF(0, 100), QPointF(200, 100), ElementStyle())
        assert not elem.contains_point(QPointF(100, 300))

    def test_contains_point_at_start(self):
        elem = MeasureElement(QPointF(50, 50), QPointF(250, 50), ElementStyle())
        assert elem.contains_point(QPointF(50, 50))

    def test_contains_point_at_end(self):
        elem = MeasureElement(QPointF(50, 50), QPointF(250, 50), ElementStyle())
        assert elem.contains_point(QPointF(250, 50))

    def test_contains_point_zero_length_near_point(self):
        """Degenerate element: clicks close to its single point should hit.

        The zero-length path uses manhattanLength < tolerance (default 8),
        so we use a point with Manhattan distance 6 (= |3| + |3| = 6 < 8).
        """
        elem = MeasureElement(QPointF(100, 100), QPointF(100, 100), ElementStyle())
        assert elem.contains_point(QPointF(103, 103))  # Manhattan distance = 6 < 8

    def test_contains_point_zero_length_far_away(self):
        elem = MeasureElement(QPointF(100, 100), QPointF(100, 100), ElementStyle())
        assert not elem.contains_point(QPointF(200, 200))

    # ── move_by ───────────────────────────────────────────────────────────────

    def test_move_by_translates_both_endpoints(self):
        elem = MeasureElement(QPointF(0, 0), QPointF(100, 0), ElementStyle())
        elem.move_by(25, 10)
        assert elem.start == QPointF(25, 10)
        assert elem.end == QPointF(125, 10)

    def test_move_by_preserves_distance(self):
        elem = MeasureElement(QPointF(0, 0), QPointF(100, 0), ElementStyle())
        d_before = elem._distance
        elem.move_by(50, 75)
        assert elem._distance == pytest.approx(d_before)

    def test_move_by_negative_delta(self):
        elem = MeasureElement(QPointF(100, 100), QPointF(200, 100), ElementStyle())
        elem.move_by(-50, -50)
        assert elem.start == QPointF(50, 50)
        assert elem.end == QPointF(150, 50)

    # ── to_dict / from_dict ───────────────────────────────────────────────────

    def test_to_dict_has_required_keys(self):
        elem = MeasureElement(QPointF(5, 10), QPointF(105, 10), ElementStyle())
        d = elem.to_dict()
        assert "type" in d
        assert "start" in d
        assert "end" in d

    def test_to_dict_type_value(self):
        elem = MeasureElement(QPointF(0, 0), QPointF(1, 1), ElementStyle())
        assert elem.to_dict()["type"] == "MEASURE"

    def test_to_dict_values_exact(self):
        elem = MeasureElement(QPointF(7, 13), QPointF(77, 130), ElementStyle())
        d = elem.to_dict()
        assert d["start"] == pytest.approx((7.0, 13.0))
        assert d["end"] == pytest.approx((77.0, 130.0))

    def test_from_dict_roundtrip_start_end(self):
        elem = MeasureElement(QPointF(11, 22), QPointF(333, 444), ElementStyle())
        restored = MeasureElement.from_dict(elem.to_dict())
        assert restored.start.x() == pytest.approx(11.0)
        assert restored.start.y() == pytest.approx(22.0)
        assert restored.end.x() == pytest.approx(333.0)
        assert restored.end.y() == pytest.approx(444.0)

    def test_from_dict_roundtrip_distance_preserved(self):
        elem = MeasureElement(QPointF(0, 0), QPointF(60, 80), ElementStyle())
        restored = MeasureElement.from_dict(elem.to_dict())
        assert restored._distance == pytest.approx(elem._distance)

    def test_from_dict_roundtrip_style_color(self):
        style = ElementStyle(foreground_color="#abcdef")
        elem = MeasureElement(QPointF(0, 0), QPointF(50, 50), style)
        restored = MeasureElement.from_dict(elem.to_dict())
        assert restored.style.foreground_color == "#abcdef"

    def test_from_dict_roundtrip_style_line_width(self):
        style = ElementStyle(line_width=7.0)
        elem = MeasureElement(QPointF(0, 0), QPointF(50, 0), style)
        restored = MeasureElement.from_dict(elem.to_dict())
        assert restored.style.line_width == pytest.approx(7.0)

    def test_from_dict_missing_keys_defaults_to_origin(self):
        """from_dict with no start/end keys should default to (0, 0)."""
        d = {"type": "MEASURE"}
        restored = MeasureElement.from_dict(d)
        assert restored.start == QPointF(0, 0)
        assert restored.end == QPointF(0, 0)

    # ── paint (headless) ──────────────────────────────────────────────────────

    def test_paint_no_crash_horizontal(self):
        from PySide6.QtGui import QPainter
        elem = MeasureElement(QPointF(10, 100), QPointF(390, 100), ElementStyle())
        pix = QPixmap(400, 200)
        pix.fill(Qt.GlobalColor.white)
        p = QPainter(pix)
        elem.paint(p)
        p.end()

    def test_paint_no_crash_vertical(self):
        from PySide6.QtGui import QPainter
        elem = MeasureElement(QPointF(200, 10), QPointF(200, 390), ElementStyle())
        pix = QPixmap(400, 400)
        pix.fill(Qt.GlobalColor.white)
        p = QPainter(pix)
        elem.paint(p)
        p.end()

    def test_paint_no_crash_diagonal(self):
        from PySide6.QtGui import QPainter
        elem = MeasureElement(QPointF(0, 0), QPointF(300, 400), ElementStyle())
        pix = QPixmap(500, 500)
        pix.fill(Qt.GlobalColor.white)
        p = QPainter(pix)
        elem.paint(p)
        p.end()

    def test_paint_no_crash_zero_length(self):
        """paint() with start==end must not crash (early return for length < 1)."""
        from PySide6.QtGui import QPainter
        elem = MeasureElement(QPointF(50, 50), QPointF(50, 50), ElementStyle())
        pix = QPixmap(200, 200)
        pix.fill(Qt.GlobalColor.white)
        p = QPainter(pix)
        elem.paint(p)
        p.end()

    def test_paint_with_rotation_no_crash(self):
        from PySide6.QtGui import QPainter
        elem = MeasureElement(QPointF(50, 50), QPointF(200, 50), ElementStyle())
        elem.rotation = 45
        pix = QPixmap(400, 400)
        pix.fill(Qt.GlobalColor.white)
        p = QPainter(pix)
        elem.paint(p)
        p.end()

    def test_paint_custom_color_no_crash(self):
        from PySide6.QtGui import QPainter
        style = ElementStyle(foreground_color="#ff0000", line_width=4.0)
        elem = MeasureElement(QPointF(20, 20), QPointF(180, 180), style)
        pix = QPixmap(300, 300)
        pix.fill(Qt.GlobalColor.white)
        p = QPainter(pix)
        elem.paint(p)
        p.end()
