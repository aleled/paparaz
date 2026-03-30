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
    LineElement, ArrowElement, ImageElement, ElementStyle, Shadow,
)
from paparaz.core.history import HistoryManager, Command
from paparaz.core.settings import AppSettings, SettingsManager, ToolDefaults
from paparaz.tools.base import ToolType
from paparaz.tools.select import SelectTool
from paparaz.tools.drawing import (
    PenTool, BrushTool, LineTool, ArrowTool, RectangleTool, EllipseTool,
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


def click(tool, pos: QPointF):
    tool.on_press(pos, None)
    tool.on_release(pos, None)


class _FakeEvent:
    """Minimal mouse-event stub with no modifiers and left button."""
    def modifiers(self):
        return Qt.KeyboardModifier.NoModifier
    def buttons(self):
        return Qt.MouseButton.LeftButton
    def button(self):
        return Qt.MouseButton.LeftButton


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
        self.elem = RectElement(QRectF(100, 100, 100, 60), ElementStyle())
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
        self.elem = RectElement(QRectF(50, 50, 100, 80), ElementStyle())
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
        new_elem = RectElement(QRectF(200, 200, 50, 50), ElementStyle())
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
        self.elem = RectElement(QRectF(100, 100, 50, 50), ElementStyle())
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
    def test_dialog_has_stays_on_top_flag(self):
        from paparaz.ui.settings_dialog import SettingsDialog
        sm = SettingsManager.__new__(SettingsManager)
        sm.settings = AppSettings()
        sm._path = None
        dlg = SettingsDialog(sm)
        assert bool(dlg.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)

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
        dlg._reset_all_tool_properties()
        assert sm.settings.tool_properties == {}
        assert _FakeSave.called


# ---------------------------------------------------------------------------
# 14. Element bounding rects and contains_point
# ---------------------------------------------------------------------------

class TestElementGeometry:
    def test_rect_contains_center(self):
        elem = RectElement(QRectF(50, 50, 100, 80), ElementStyle())
        assert elem.contains_point(QPointF(100, 90))

    def test_rect_does_not_contain_outside(self):
        elem = RectElement(QRectF(50, 50, 100, 80), ElementStyle())
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
        elem = RectElement(QRectF(0, 0, 100, 100), ElementStyle())
        elem.move_by(25, 30)
        assert elem.rect.x() == pytest.approx(25)
        assert elem.rect.y() == pytest.approx(30)
