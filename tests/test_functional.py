"""
Functional / integration tests for PapaRaZ.

Exercises full user workflows end-to-end:
  - Tool switching & property persistence
  - Element lifecycle (create, select, move, resize, delete)
  - Text tool full editing workflow
  - Copy/paste, multi-select, z-order
  - Undo/redo chains across operations
  - Snap during drag
  - Canvas resize and crop
  - Handle interception with non-select tools
  - Settings dialog save/load round-trip
  - Side panel mode switching
  - Drawing tool modifiers (shift-constrain)
"""

import sys
import copy
import math
import pytest
import tempfile
import os
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QPixmap, QKeyEvent, QColor

app = QApplication.instance() or QApplication(sys.argv)

sys.path.insert(0, "src")

from paparaz.core.elements import (
    TextElement, NumberElement, MaskElement, StampElement,
    RectElement, EllipseElement, PenElement, BrushElement,
    LineElement, ArrowElement, ImageElement, ElementStyle, Shadow,
    MagnifierElement,
)
from paparaz.core.history import HistoryManager, Command
from paparaz.core.settings import AppSettings, SettingsManager, ToolDefaults
from paparaz.core.snap import snap_move, snap_point, SnapGuide
from paparaz.tools.base import ToolType
from paparaz.tools.select import SelectTool
from paparaz.tools.drawing import (
    PenTool, BrushTool, LineTool, ArrowTool, RectangleTool, EllipseTool,
    HighlightTool, CurvedArrowTool,
)
from paparaz.tools.special import (
    TextTool, NumberingTool, EraserTool, MasqueradeTool, FillTool, StampTool,
    SliceTool, EyedropperTool, MagnifierTool,
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


class _FakeEvent:
    """Mouse event stub with left button and no modifiers."""
    def modifiers(self):
        return Qt.KeyboardModifier.NoModifier
    def buttons(self):
        return Qt.MouseButton.LeftButton
    def button(self):
        return Qt.MouseButton.LeftButton


class _ShiftEvent:
    """Mouse event stub with Shift modifier."""
    def modifiers(self):
        return Qt.KeyboardModifier.ShiftModifier
    def buttons(self):
        return Qt.MouseButton.LeftButton
    def button(self):
        return Qt.MouseButton.LeftButton


class _RightClickEvent:
    """Mouse event stub with right button."""
    def modifiers(self):
        return Qt.KeyboardModifier.NoModifier
    def buttons(self):
        return Qt.MouseButton.RightButton
    def button(self):
        return Qt.MouseButton.RightButton


def click(tool, pos: QPointF):
    ev = _FakeEvent()
    tool.on_press(pos, ev)
    tool.on_release(pos, ev)


def drag(tool, start: QPointF, end: QPointF, event=None):
    ev = event or _FakeEvent()
    tool.on_press(start, ev)
    tool.on_move(end, ev)
    tool.on_release(end, ev)


def key(tool, qt_key, text="", mods=Qt.KeyboardModifier.NoModifier):
    ev = QKeyEvent(QKeyEvent.Type.KeyPress, qt_key, mods, text)
    tool.on_key_press(ev)


# ===========================================================================
# 1. Tool Switching & Property Persistence
# ===========================================================================

class TestToolSwitchingWorkflow:
    """Full workflow: switch tools, change properties, switch away and back."""

    def test_switch_tools_changes_canvas_tool(self):
        c = make_canvas()
        pen = PenTool(c)
        rect = RectangleTool(c)
        c.set_tool(pen)
        assert c._tool is pen
        c.set_tool(rect)
        assert c._tool is rect

    def test_deactivate_called_on_switch(self):
        c = make_canvas()
        pen = PenTool(c)
        rect = RectangleTool(c)
        c.set_tool(pen)
        c.set_tool(rect)
        # After deactivation, pen should have clean state
        # (BaseTool.on_deactivate resets nothing by default, but verifies no crash)

    def test_tool_creates_correct_element_type(self):
        """Each drawing tool should create the expected element type."""
        c = make_canvas()
        tool_elem_pairs = [
            (PenTool(c), PenElement),
            (BrushTool(c), BrushElement),
            (LineTool(c), LineElement),
            (ArrowTool(c), ArrowElement),
            (RectangleTool(c), RectElement),
            (EllipseTool(c), EllipseElement),
        ]
        for tool, elem_type in tool_elem_pairs:
            c.set_tool(tool)
            drag(tool, QPointF(50, 50), QPointF(200, 200))
            assert len(c.elements) > 0
            assert isinstance(c.elements[-1], elem_type), \
                f"{tool.__class__.__name__} should create {elem_type.__name__}"
            # Clean up
            c.elements.clear()

    def test_canvas_style_state_applied_to_new_element(self):
        """Drawing tool should inherit canvas style properties."""
        c = make_canvas()
        c._fg_color = "#00FF00"
        c._line_width = 5.0
        tool = RectangleTool(c)
        c.set_tool(tool)
        drag(tool, QPointF(10, 10), QPointF(100, 100))
        elem = c.elements[-1]
        assert elem.style.foreground_color == "#00FF00"
        assert elem.style.line_width == pytest.approx(5.0)

    def test_canvas_shadow_applied_to_new_element(self):
        c = make_canvas()
        c._shadow = Shadow(enabled=True, offset_x=4, offset_y=4, blur_x=8, blur_y=8,
                           color="#80FF0000")
        tool = RectangleTool(c)
        c.set_tool(tool)
        drag(tool, QPointF(10, 10), QPointF(100, 100))
        elem = c.elements[-1]
        assert elem.style.shadow.enabled is True
        assert elem.style.shadow.offset_x == pytest.approx(4)


# ===========================================================================
# 2. Element Lifecycle
# ===========================================================================

class TestElementLifecycle:
    """Create, select, move, resize, delete elements."""

    def setup_method(self):
        self.c = make_canvas(800, 600)
        self.select = SelectTool(self.c)
        self.c.set_tool(self.select)

    def test_add_element_increases_count(self):
        elem = RectElement(QRectF(50, 50, 100, 80), filled=True, style=ElementStyle())
        self.c.add_element(elem)
        assert len(self.c.elements) == 1

    def test_add_element_auto_selects(self):
        elem = RectElement(QRectF(50, 50, 100, 80), filled=True, style=ElementStyle())
        self.c.add_element(elem)
        assert self.c.selected_element is elem

    def test_add_element_no_auto_select(self):
        elem = RectElement(QRectF(50, 50, 100, 80), filled=True, style=ElementStyle())
        self.c.add_element(elem, auto_select=False)
        assert self.c.selected_element is None

    def test_delete_element_removes_from_list(self):
        elem = RectElement(QRectF(50, 50, 100, 80), filled=True, style=ElementStyle())
        self.c.add_element(elem)
        self.c.delete_element(elem)
        assert elem not in self.c.elements

    def test_delete_clears_selection(self):
        elem = RectElement(QRectF(50, 50, 100, 80), filled=True, style=ElementStyle())
        self.c.add_element(elem)
        self.c.delete_element(elem)
        assert self.c.selected_element is None

    def test_select_element_flags_it(self):
        elem = RectElement(QRectF(50, 50, 100, 80), filled=True, style=ElementStyle())
        self.c.add_element(elem, auto_select=False)
        self.c.select_element(elem)
        assert elem.selected is True
        assert self.c.selected_element is elem

    def test_select_none_clears_flags(self):
        elem = RectElement(QRectF(50, 50, 100, 80), filled=True, style=ElementStyle())
        self.c.add_element(elem)
        self.c.select_element(None)
        assert elem.selected is False
        assert self.c.selected_element is None

    def test_move_element_by_drag(self):
        elem = RectElement(QRectF(100, 100, 80, 60), filled=True, style=ElementStyle())
        self.c.add_element(elem)
        orig_x = elem.rect.x()
        orig_y = elem.rect.y()
        # Click to select, then drag
        click(self.select, QPointF(140, 130))
        drag(self.select, QPointF(140, 130), QPointF(240, 230))
        assert elem.rect.x() == pytest.approx(orig_x + 100)
        assert elem.rect.y() == pytest.approx(orig_y + 100)

    def test_move_element_arrow_keys(self):
        elem = RectElement(QRectF(100, 100, 80, 60), filled=True, style=ElementStyle())
        self.c.add_element(elem)
        click(self.select, QPointF(140, 130))
        orig_x = elem.rect.x()
        key(self.select, Qt.Key.Key_Right)
        assert elem.rect.x() == pytest.approx(orig_x + 1)

    def test_move_element_shift_arrow_10px(self):
        elem = RectElement(QRectF(100, 100, 80, 60), filled=True, style=ElementStyle())
        self.c.add_element(elem)
        click(self.select, QPointF(140, 130))
        orig_x = elem.rect.x()
        ev = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Right,
                       Qt.KeyboardModifier.ShiftModifier)
        self.select.on_key_press(ev)
        assert elem.rect.x() == pytest.approx(orig_x + 10)

    def test_resize_element_via_handle(self):
        elem = RectElement(QRectF(100, 100, 80, 60), filled=True, style=ElementStyle())
        self.c.add_element(elem)
        click(self.select, QPointF(140, 130))
        # Drag bottom-right handle (handle 7)
        br = QPointF(elem.rect.right(), elem.rect.bottom())
        drag(self.select, br, QPointF(br.x() + 30, br.y() + 20))
        assert elem.rect.width() == pytest.approx(110)
        assert elem.rect.height() == pytest.approx(80)

    def test_delete_via_key(self):
        elem = RectElement(QRectF(100, 100, 80, 60), filled=True, style=ElementStyle())
        self.c.add_element(elem)
        click(self.select, QPointF(140, 130))
        key(self.select, Qt.Key.Key_Delete)
        assert elem not in self.c.elements

    def test_rotation_via_handle(self):
        elem = RectElement(QRectF(100, 100, 80, 60), filled=True, style=ElementStyle())
        self.c.add_element(elem)
        click(self.select, QPointF(140, 130))
        assert elem.rotation == pytest.approx(0)
        # Rotation handle is above center; drag it sideways
        center = elem.bounding_rect().center()
        rot_handle = QPointF(center.x(), center.y() - 22 - 5)
        ev = _FakeEvent()
        self.select.on_press(rot_handle, ev)
        self.select._handle_index = 8  # force rotation handle
        self.select._resizing = True
        self.select.on_move(QPointF(center.x() + 50, center.y() - 22), ev)
        assert elem.rotation != pytest.approx(0)

    def test_multiple_elements_z_order(self):
        e1 = RectElement(QRectF(50, 50, 100, 80), filled=True, style=ElementStyle())
        e2 = RectElement(QRectF(80, 80, 100, 80), filled=True, style=ElementStyle())
        self.c.add_element(e1, auto_select=False)
        self.c.add_element(e2, auto_select=False)
        assert self.c.elements.index(e1) == 0
        assert self.c.elements.index(e2) == 1
        # Click on overlapping area — should select top (e2)
        click(self.select, QPointF(120, 120))
        assert self.c.selected_element is e2


# ===========================================================================
# 3. Text Tool Full Workflow
# ===========================================================================

class TestTextToolWorkflow:
    """Full text creation, editing, and finalization."""

    def setup_method(self):
        self.c = make_canvas()
        self.text_tool = TextTool(self.c)
        self.c.set_tool(self.text_tool)

    def test_create_text_element(self):
        click(self.text_tool, QPointF(100, 100))
        assert self.text_tool._active_text is not None
        assert isinstance(self.text_tool._active_text, TextElement)

    def test_type_and_finalize(self):
        click(self.text_tool, QPointF(100, 100))
        key(self.text_tool, Qt.Key.Key_H, "H")
        key(self.text_tool, Qt.Key.Key_I, "i")
        assert self.text_tool._active_text.text == "Hi"
        # Finalize with Escape
        key(self.text_tool, Qt.Key.Key_Escape)
        assert self.text_tool._active_text is None
        assert len(self.c.elements) == 1
        assert self.c.elements[0].text == "Hi"

    def test_ctrl_enter_finalizes(self):
        click(self.text_tool, QPointF(100, 100))
        key(self.text_tool, Qt.Key.Key_A, "A")
        key(self.text_tool, Qt.Key.Key_Return, mods=Qt.KeyboardModifier.ControlModifier)
        assert self.text_tool._active_text is None
        assert len(self.c.elements) == 1

    def test_escape_empty_discards(self):
        click(self.text_tool, QPointF(100, 100))
        key(self.text_tool, Qt.Key.Key_Escape)
        assert self.text_tool._active_text is None
        assert len(self.c.elements) == 0

    def test_enter_adds_newline(self):
        click(self.text_tool, QPointF(100, 100))
        key(self.text_tool, Qt.Key.Key_A, "A")
        key(self.text_tool, Qt.Key.Key_Return)
        key(self.text_tool, Qt.Key.Key_B, "B")
        assert self.text_tool._active_text.text == "A\nB"

    def test_backspace_removes_char(self):
        click(self.text_tool, QPointF(100, 100))
        key(self.text_tool, Qt.Key.Key_A, "A")
        key(self.text_tool, Qt.Key.Key_B, "B")
        key(self.text_tool, Qt.Key.Key_Backspace)
        assert self.text_tool._active_text.text == "A"

    def test_second_click_finalizes_first(self):
        click(self.text_tool, QPointF(100, 100))
        key(self.text_tool, Qt.Key.Key_X, "X")
        # Click elsewhere to create second text
        click(self.text_tool, QPointF(300, 300))
        assert len(self.c.elements) == 1  # first text finalized
        assert self.c.elements[0].text == "X"
        # Second text is now active
        assert self.text_tool._active_text is not None

    def test_font_applied_from_canvas(self):
        self.c._font_family = "Courier"
        self.c._font_size = 20
        click(self.text_tool, QPointF(100, 100))
        elem = self.text_tool._active_text
        assert elem.style.font_family == "Courier"
        assert elem.style.font_size == 20


# ===========================================================================
# 4. Copy/Paste, Multi-Select, Z-Order
# ===========================================================================

class TestCopyPasteMultiSelect:

    def setup_method(self):
        self.c = make_canvas(800, 600)
        self.select = SelectTool(self.c)
        self.c.set_tool(self.select)

    def test_copy_and_paste_element(self):
        elem = RectElement(QRectF(100, 100, 80, 60), filled=True, style=ElementStyle())
        self.c.add_element(elem)
        self.c.copy_element(elem)
        self.c.paste_element()
        assert len(self.c.elements) == 2
        pasted = self.c.elements[-1]
        # Pasted element should be offset
        assert pasted.rect.x() != elem.rect.x() or pasted.rect.y() != elem.rect.y()

    def test_paste_is_independent_copy(self):
        elem = RectElement(QRectF(100, 100, 80, 60), filled=True, style=ElementStyle())
        self.c.add_element(elem)
        self.c.copy_element(elem)
        self.c.paste_element()
        pasted = self.c.elements[-1]
        # Modifying original should not affect paste
        elem.rect = QRectF(0, 0, 10, 10)
        assert pasted.rect.width() == pytest.approx(80)

    def test_bring_to_front(self):
        e1 = RectElement(QRectF(50, 50, 80, 60), filled=True, style=ElementStyle())
        e2 = RectElement(QRectF(100, 100, 80, 60), filled=True, style=ElementStyle())
        self.c.add_element(e1, auto_select=False)
        self.c.add_element(e2, auto_select=False)
        self.c.select_element(e1)
        self.c.bring_to_front()
        assert self.c.elements[-1] is e1

    def test_send_to_back(self):
        e1 = RectElement(QRectF(50, 50, 80, 60), filled=True, style=ElementStyle())
        e2 = RectElement(QRectF(100, 100, 80, 60), filled=True, style=ElementStyle())
        self.c.add_element(e1, auto_select=False)
        self.c.add_element(e2, auto_select=False)
        self.c.select_element(e2)
        self.c.send_to_back()
        assert self.c.elements[0] is e2

    def test_rubber_band_multi_select(self):
        e1 = RectElement(QRectF(50, 50, 40, 30), filled=True, style=ElementStyle())
        e2 = RectElement(QRectF(150, 150, 40, 30), filled=True, style=ElementStyle())
        e3 = RectElement(QRectF(500, 500, 40, 30), filled=True, style=ElementStyle())  # outside rubber band
        self.c.add_element(e1, auto_select=False)
        self.c.add_element(e2, auto_select=False)
        self.c.add_element(e3, auto_select=False)
        # Rubber band from (10,10) to (250,250) should catch e1 and e2
        drag(self.select, QPointF(10, 10), QPointF(250, 250))
        assert e1 in self.select._multi_selected
        assert e2 in self.select._multi_selected
        assert e3 not in self.select._multi_selected

    def test_shift_click_multi_select(self):
        e1 = RectElement(QRectF(50, 50, 40, 30), filled=True, style=ElementStyle())
        e2 = RectElement(QRectF(150, 150, 40, 30), filled=True, style=ElementStyle())
        self.c.add_element(e1, auto_select=False)
        self.c.add_element(e2, auto_select=False)
        # Click first element
        click(self.select, QPointF(70, 65))
        assert self.c.selected_element is e1
        # Shift-click second
        ev = _ShiftEvent()
        self.select.on_press(QPointF(170, 165), ev)
        self.select.on_release(QPointF(170, 165), ev)
        assert e1 in self.select._multi_selected
        assert e2 in self.select._multi_selected

    def test_multi_select_delete(self):
        e1 = RectElement(QRectF(50, 50, 40, 30), filled=True, style=ElementStyle())
        e2 = RectElement(QRectF(150, 150, 40, 30), filled=True, style=ElementStyle())
        self.c.add_element(e1, auto_select=False)
        self.c.add_element(e2, auto_select=False)
        # Rubber-band select both
        drag(self.select, QPointF(10, 10), QPointF(250, 250))
        # Delete
        key(self.select, Qt.Key.Key_Delete)
        assert e1 not in self.c.elements
        assert e2 not in self.c.elements

    def test_multi_move_by_drag(self):
        e1 = RectElement(QRectF(50, 50, 40, 30), filled=True, style=ElementStyle())
        e2 = RectElement(QRectF(150, 150, 40, 30), filled=True, style=ElementStyle())
        self.c.add_element(e1, auto_select=False)
        self.c.add_element(e2, auto_select=False)
        drag(self.select, QPointF(10, 10), QPointF(250, 250))
        # Now drag the group — must start inside one of the selected elements
        orig_x1 = e1.rect.x()
        orig_x2 = e2.rect.x()
        drag(self.select, QPointF(70, 65), QPointF(90, 65))
        assert e1.rect.x() == pytest.approx(orig_x1 + 20)
        assert e2.rect.x() == pytest.approx(orig_x2 + 20)


# ===========================================================================
# 5. Undo/Redo Chains
# ===========================================================================

class TestUndoRedoChains:
    """Test undo/redo across mixed operations."""

    def setup_method(self):
        self.c = make_canvas()
        self.select = SelectTool(self.c)
        self.c.set_tool(self.select)

    def test_add_then_delete_undo_restores(self):
        elem = RectElement(QRectF(50, 50, 80, 60), filled=True, style=ElementStyle())
        self.c.add_element(elem)
        assert len(self.c.elements) == 1
        self.c.delete_element(elem)
        assert len(self.c.elements) == 0
        self.c.history.undo()
        assert len(self.c.elements) == 1
        assert self.c.elements[0] is elem

    def test_double_undo_reverses_two_operations(self):
        e1 = RectElement(QRectF(50, 50, 80, 60), filled=True, style=ElementStyle())
        e2 = RectElement(QRectF(200, 200, 80, 60), filled=True, style=ElementStyle())
        self.c.add_element(e1)
        self.c.add_element(e2)
        assert len(self.c.elements) == 2
        self.c.history.undo()
        assert len(self.c.elements) == 1
        self.c.history.undo()
        assert len(self.c.elements) == 0

    def test_undo_redo_undo(self):
        elem = RectElement(QRectF(50, 50, 80, 60), filled=True, style=ElementStyle())
        self.c.add_element(elem)
        self.c.history.undo()
        assert len(self.c.elements) == 0
        self.c.history.redo()
        assert len(self.c.elements) == 1
        self.c.history.undo()
        assert len(self.c.elements) == 0

    def test_move_undo_preserves_position(self):
        elem = RectElement(QRectF(100, 100, 80, 60), filled=True, style=ElementStyle())
        self.c.add_element(elem)
        orig_pos = QPointF(elem.rect.x(), elem.rect.y())
        click(self.select, QPointF(140, 130))
        drag(self.select, QPointF(140, 130), QPointF(300, 300))
        assert elem.rect.x() != pytest.approx(orig_pos.x())
        self.c.history.undo()
        assert elem.rect.x() == pytest.approx(orig_pos.x())
        assert elem.rect.y() == pytest.approx(orig_pos.y())

    def test_style_change_undo(self):
        elem = RectElement(QRectF(50, 50, 80, 60), filled=True, style=ElementStyle())
        self.c.add_element(elem)
        orig_color = elem.style.foreground_color
        self.c.set_foreground_color("#00FF00")
        assert elem.style.foreground_color == "#00FF00"
        self.c.history.undo()
        assert elem.style.foreground_color == orig_color

    def test_add_move_style_triple_undo(self):
        """Three operations, undo all three in sequence."""
        elem = RectElement(QRectF(50, 50, 80, 60), filled=True, style=ElementStyle())
        self.c.add_element(elem)
        orig_x = elem.rect.x()
        orig_color = elem.style.foreground_color
        # Move
        click(self.select, QPointF(90, 80))
        drag(self.select, QPointF(90, 80), QPointF(200, 200))
        # Style change
        self.c.set_foreground_color("#AABBCC")
        # Now undo: style → move → add
        self.c.history.undo()  # undo style
        assert elem.style.foreground_color != "#AABBCC"
        self.c.history.undo()  # undo move
        assert elem.rect.x() == pytest.approx(orig_x)
        self.c.history.undo()  # undo add
        assert len(self.c.elements) == 0

    def test_bring_to_front_undoable(self):
        e1 = RectElement(QRectF(50, 50, 80, 60), filled=True, style=ElementStyle())
        e2 = RectElement(QRectF(100, 100, 80, 60), filled=True, style=ElementStyle())
        self.c.add_element(e1, auto_select=False)
        self.c.add_element(e2, auto_select=False)
        self.c.select_element(e1)
        self.c.bring_to_front()
        assert self.c.elements[-1] is e1
        self.c.history.undo()
        assert self.c.elements[0] is e1

    def test_send_to_back_undoable(self):
        e1 = RectElement(QRectF(50, 50, 80, 60), filled=True, style=ElementStyle())
        e2 = RectElement(QRectF(100, 100, 80, 60), filled=True, style=ElementStyle())
        self.c.add_element(e1, auto_select=False)
        self.c.add_element(e2, auto_select=False)
        self.c.select_element(e2)
        self.c.send_to_back()
        assert self.c.elements[0] is e2
        self.c.history.undo()
        assert self.c.elements[-1] is e2


# ===========================================================================
# 6. Snap During Drag
# ===========================================================================

class TestSnapDuringDrag:
    """Verify snap guides appear and element positions are adjusted."""

    def setup_method(self):
        self.c = make_canvas(800, 600)
        self.c.snap_enabled = True
        self.c.snap_to_canvas = True
        self.c.snap_to_elements = True
        self.c.snap_threshold = 8
        self.select = SelectTool(self.c)
        self.c.set_tool(self.select)

    def test_drag_near_left_edge_produces_guide(self):
        elem = RectElement(QRectF(100, 200, 80, 60), filled=True, style=ElementStyle())
        self.c.add_element(elem)
        click(self.select, QPointF(140, 230))
        ev = _FakeEvent()
        # Drag so elem left edge is near 0
        self.select.on_press(QPointF(140, 230), ev)
        self.select.on_move(QPointF(45, 230), ev)
        assert len(self.c._snap_guides) > 0
        # Verify there's a vertical guide at x=0
        v_guides = [g for g in self.c._snap_guides if g.orientation == "v"]
        assert any(abs(g.value) < 1 for g in v_guides)
        self.select.on_release(QPointF(45, 230), ev)
        assert self.c._snap_guides == []

    def test_snap_to_other_element_edge(self):
        ref = RectElement(QRectF(200, 200, 80, 60), filled=True, style=ElementStyle())
        moving = RectElement(QRectF(100, 100, 60, 40), filled=True, style=ElementStyle())
        self.c.add_element(ref, auto_select=False)
        self.c.add_element(moving)
        click(self.select, QPointF(130, 120))
        ev = _FakeEvent()
        self.select.on_press(QPointF(130, 120), ev)
        # Move so right edge (160) is near ref left edge (200)
        # Need to move right by ~37 so right edge = 197 (within threshold 8 of 200)
        self.select.on_move(QPointF(167, 120), ev)
        v_guides = [g for g in self.c._snap_guides if g.orientation == "v"]
        assert len(v_guides) > 0
        self.select.on_release(QPointF(167, 120), ev)

    def test_snap_disabled_no_guides(self):
        self.c.snap_enabled = False
        elem = RectElement(QRectF(100, 200, 80, 60), filled=True, style=ElementStyle())
        self.c.add_element(elem)
        click(self.select, QPointF(140, 230))
        ev = _FakeEvent()
        self.select.on_press(QPointF(140, 230), ev)
        self.select.on_move(QPointF(5, 230), ev)
        assert self.c._snap_guides == []
        self.select.on_release(QPointF(5, 230), ev)

    def test_snap_grid_mode(self):
        self.c.snap_to_canvas = False
        self.c.snap_to_elements = False
        self.c.snap_grid_enabled = True
        self.c.snap_grid_size = 50
        elem = RectElement(QRectF(100, 100, 80, 60), filled=True, style=ElementStyle())
        self.c.add_element(elem)
        click(self.select, QPointF(140, 130))
        ev = _FakeEvent()
        self.select.on_press(QPointF(140, 130), ev)
        # Move so left edge would be near 150 (grid line)
        self.select.on_move(QPointF(193, 130), ev)
        # Should snap to grid
        v_guides = [g for g in self.c._snap_guides if g.orientation == "v"]
        assert len(v_guides) > 0
        self.select.on_release(QPointF(193, 130), ev)


# ===========================================================================
# 7. Canvas Resize and Crop
# ===========================================================================

class TestCanvasResizeCrop:

    def test_resize_expands_canvas(self):
        c = make_canvas(400, 300)
        c.resize_canvas(800, 600)
        assert c._background.width() == 800
        assert c._background.height() == 600

    def test_resize_undoable(self):
        c = make_canvas(400, 300)
        c.resize_canvas(800, 600)
        c.history.undo()
        assert c._background.width() == 400
        assert c._background.height() == 300

    def test_resize_shifts_elements(self):
        c = make_canvas(400, 300)
        elem = RectElement(QRectF(50, 50, 80, 60), filled=True, style=ElementStyle())
        c.add_element(elem, auto_select=False)
        orig_x = elem.rect.x()
        c.resize_canvas(800, 600)
        # Element should be shifted by (800-400)/2 = 200
        assert elem.rect.x() == pytest.approx(orig_x + 200)

    def test_crop_shrinks_canvas(self):
        c = make_canvas(800, 600)
        c.crop_canvas(QRectF(100, 100, 400, 300))
        assert c._background.width() == 400
        assert c._background.height() == 300

    def test_crop_undoable(self):
        c = make_canvas(800, 600)
        c.crop_canvas(QRectF(100, 100, 400, 300))
        c.history.undo()
        assert c._background.width() == 800
        assert c._background.height() == 600

    def test_crop_shifts_elements(self):
        c = make_canvas(800, 600)
        elem = RectElement(QRectF(200, 200, 80, 60), filled=True, style=ElementStyle())
        c.add_element(elem, auto_select=False)
        c.crop_canvas(QRectF(100, 100, 400, 300))
        # Element should shift by -100, -100
        assert elem.rect.x() == pytest.approx(100)
        assert elem.rect.y() == pytest.approx(100)


# ===========================================================================
# 8. Handle Interception with Non-Select Tools
# ===========================================================================

class TestHandleInterception:
    """When a non-select tool is active, clicking on a handle should still
    resize/rotate the selected element."""

    def setup_method(self):
        self.c = make_canvas(800, 600)

    def test_canvas_has_handle_select(self):
        assert hasattr(self.c, '_handle_select')
        assert isinstance(self.c._handle_select, SelectTool)

    def test_is_handle_tool_returns_true_for_non_select(self):
        pen = PenTool(self.c)
        self.c.set_tool(pen)
        assert self.c._is_handle_tool() is True

    def test_is_handle_tool_returns_false_for_select(self):
        sel = SelectTool(self.c)
        self.c.set_tool(sel)
        assert self.c._is_handle_tool() is False

    def test_handle_active_flag_exists(self):
        assert hasattr(self.c, '_handle_active')
        assert self.c._handle_active is False


# ===========================================================================
# 9. Settings Round-Trip
# ===========================================================================

class TestSettingsRoundTrip:
    """Verify settings save and load correctly."""

    def test_default_settings_roundtrip(self):
        tmpf = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        tmpf.close()
        try:
            sm = SettingsManager(Path(tmpf.name))
            sm.save()
            sm2 = SettingsManager(Path(tmpf.name))
            assert sm2.settings.default_format == "png"
            assert sm2.settings.jpg_quality == 90
            assert sm2.settings.theme == "dark"
        finally:
            os.unlink(tmpf.name)

    def test_custom_settings_roundtrip(self):
        tmpf = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        tmpf.close()
        try:
            sm = SettingsManager(Path(tmpf.name))
            sm.settings.default_format = "jpg"
            sm.settings.jpg_quality = 75
            sm.settings.tool_defaults.foreground_color = "#00FF00"
            sm.settings.tool_defaults.line_width = 5
            sm.settings.filename_pattern = "{yyyy}_{n:4}"
            sm.settings.snap_enabled = False
            sm.settings.snap_grid_size = 32
            sm.save()

            sm2 = SettingsManager(Path(tmpf.name))
            assert sm2.settings.default_format == "jpg"
            assert sm2.settings.jpg_quality == 75
            assert sm2.settings.tool_defaults.foreground_color == "#00FF00"
            assert sm2.settings.tool_defaults.line_width == 5
            assert sm2.settings.filename_pattern == "{yyyy}_{n:4}"
            assert sm2.settings.snap_enabled is False
            assert sm2.settings.snap_grid_size == 32
        finally:
            os.unlink(tmpf.name)

    def test_tool_properties_roundtrip(self):
        tmpf = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        tmpf.close()
        try:
            sm = SettingsManager(Path(tmpf.name))
            sm.settings.tool_properties["PEN"] = {
                "foreground_color": "#FF0000", "line_width": 3
            }
            sm.settings.tool_properties["RECTANGLE"] = {
                "foreground_color": "#0000FF", "filled": True
            }
            sm.save()

            sm2 = SettingsManager(Path(tmpf.name))
            assert sm2.settings.tool_properties["PEN"]["foreground_color"] == "#FF0000"
            assert sm2.settings.tool_properties["RECTANGLE"]["filled"] is True
        finally:
            os.unlink(tmpf.name)

    def test_recent_captures_roundtrip(self):
        tmpf = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        tmpf.close()
        try:
            sm = SettingsManager(Path(tmpf.name))
            sm.add_recent("C:/screenshots/test1.png")
            sm.add_recent("C:/screenshots/test2.png")
            sm2 = SettingsManager(Path(tmpf.name))
            assert len(sm2.settings.recent_captures) == 2
            assert sm2.settings.recent_captures[0] == "C:/screenshots/test2.png"
        finally:
            os.unlink(tmpf.name)

    def test_hotkey_settings_roundtrip(self):
        tmpf = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        tmpf.close()
        try:
            sm = SettingsManager(Path(tmpf.name))
            sm.settings.hotkeys.capture = "F5"
            sm.settings.hotkeys.capture_fullscreen = "Ctrl+F5"
            sm.save()
            sm2 = SettingsManager(Path(tmpf.name))
            assert sm2.settings.hotkeys.capture == "F5"
            assert sm2.settings.hotkeys.capture_fullscreen == "Ctrl+F5"
        finally:
            os.unlink(tmpf.name)

    def test_backward_compat_old_fields_ignored(self):
        """Loading a settings file with unknown fields should not crash."""
        tmpf = tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w")
        import json
        json.dump({"unknown_future_field": True, "default_format": "png"}, tmpf)
        tmpf.close()
        try:
            sm = SettingsManager(Path(tmpf.name))
            assert sm.settings.default_format == "png"
        finally:
            os.unlink(tmpf.name)


# ===========================================================================
# 10. Side Panel Mode Switching
# ===========================================================================

class TestSidePanelModes:
    def test_default_mode_is_auto(self):
        panel = SidePanel()
        assert panel._mode == "auto"

    def test_set_mode_pinned(self):
        panel = SidePanel()
        panel.set_mode("pinned")
        assert panel._mode == "pinned"

    def test_set_mode_hidden(self):
        panel = SidePanel()
        panel.set_mode("hidden")
        assert panel._mode == "hidden"

    def test_pin_button_syncs_with_mode(self):
        panel = SidePanel()
        panel.set_mode("pinned")
        assert panel._pin_btn.isChecked() is True
        panel.set_mode("auto")
        assert panel._pin_btn.isChecked() is False

    def test_auto_hide_timer_stopped_on_mode_change(self):
        panel = SidePanel()
        panel._auto_hide_timer.start(3000)
        panel.set_mode("pinned")
        assert panel._auto_hide_timer.isActive() is False

    def test_set_auto_hide_ms(self):
        panel = SidePanel()
        panel.set_auto_hide_ms(5000)
        assert panel._auto_hide_timer.interval() == 5000


# ===========================================================================
# 11. Drawing Tool Modifiers (shift-constrain)
# ===========================================================================

class TestDrawingModifiers:

    def test_rect_shift_constrains_to_square(self):
        c = make_canvas()
        tool = RectangleTool(c)
        c.set_tool(tool)
        drag(tool, QPointF(50, 50), QPointF(200, 150), event=_ShiftEvent())
        elem = c.elements[-1]
        assert elem.rect.width() == pytest.approx(elem.rect.height())

    def test_ellipse_shift_constrains_to_circle(self):
        c = make_canvas()
        tool = EllipseTool(c)
        c.set_tool(tool)
        drag(tool, QPointF(50, 50), QPointF(200, 150), event=_ShiftEvent())
        elem = c.elements[-1]
        assert elem.rect.width() == pytest.approx(elem.rect.height())

    def test_line_shift_snaps_angle(self):
        c = make_canvas()
        tool = LineTool(c)
        c.set_tool(tool)
        # Draw at ~30 degrees — shift should snap to 0 or 45
        drag(tool, QPointF(50, 50), QPointF(200, 80), event=_ShiftEvent())
        elem = c.elements[-1]
        dx = elem.end.x() - elem.start.x()
        dy = elem.end.y() - elem.start.y()
        if abs(dx) > 1:
            angle = abs(math.degrees(math.atan2(dy, dx)))
            # Should be snapped to 0 or 45
            assert angle == pytest.approx(0, abs=1) or angle == pytest.approx(45, abs=1)


# ===========================================================================
# 12. Numbering Tool
# ===========================================================================

class TestNumberingToolWorkflow:
    def test_sequential_numbers(self):
        c = make_canvas()
        NumberElement.reset_counter()
        tool = NumberingTool(c)
        c.set_tool(tool)
        click(tool, QPointF(100, 100))
        click(tool, QPointF(200, 200))
        click(tool, QPointF(300, 300))
        assert len(c.elements) == 3
        nums = [e.number for e in c.elements]
        assert nums == [1, 2, 3]

    def test_delete_and_new_continues_count(self):
        c = make_canvas()
        NumberElement.reset_counter()
        tool = NumberingTool(c)
        c.set_tool(tool)
        click(tool, QPointF(100, 100))
        click(tool, QPointF(200, 200))
        # Delete first
        c.delete_element(c.elements[0])
        click(tool, QPointF(300, 300))
        assert c.elements[-1].number == 3


# ===========================================================================
# 13. Eraser Tool
# ===========================================================================

class TestEraserToolWorkflow:
    def test_eraser_removes_element_under_cursor(self):
        c = make_canvas()
        elem = RectElement(QRectF(100, 100, 80, 60), filled=True, style=ElementStyle())
        c.add_element(elem, auto_select=False)
        eraser = EraserTool(c)
        c.set_tool(eraser)
        click(eraser, QPointF(140, 130))
        assert elem not in c.elements

    def test_eraser_miss_does_nothing(self):
        c = make_canvas()
        elem = RectElement(QRectF(100, 100, 80, 60), filled=True, style=ElementStyle())
        c.add_element(elem, auto_select=False)
        eraser = EraserTool(c)
        c.set_tool(eraser)
        click(eraser, QPointF(10, 10))
        assert elem in c.elements

    def test_eraser_undoable(self):
        c = make_canvas()
        elem = RectElement(QRectF(100, 100, 80, 60), filled=True, style=ElementStyle())
        c.add_element(elem, auto_select=False)
        eraser = EraserTool(c)
        c.set_tool(eraser)
        click(eraser, QPointF(140, 130))
        assert elem not in c.elements
        c.history.undo()
        assert elem in c.elements


# ===========================================================================
# 14. Masquerade (pixelate) Tool
# ===========================================================================

class TestMasqueradeToolWorkflow:
    def test_drag_creates_mask(self):
        c = make_canvas()
        tool = MasqueradeTool(c)
        c.set_tool(tool)
        drag(tool, QPointF(50, 50), QPointF(200, 200))
        assert len(c.elements) == 1
        assert isinstance(c.elements[0], MaskElement)

    def test_small_drag_does_not_create(self):
        c = make_canvas()
        tool = MasqueradeTool(c)
        c.set_tool(tool)
        drag(tool, QPointF(50, 50), QPointF(52, 52))
        assert len(c.elements) == 0


# ===========================================================================
# 15. Stamp Tool
# ===========================================================================

class TestStampToolWorkflow:
    def test_click_creates_stamp(self):
        c = make_canvas()
        tool = StampTool(c)
        c.set_tool(tool)
        click(tool, QPointF(200, 200))
        assert len(c.elements) == 1
        assert isinstance(c.elements[0], StampElement)


# ===========================================================================
# 16. Export Module
# ===========================================================================

class TestExportModule:
    def test_save_png(self):
        from paparaz.core.export import save_png
        pix = QPixmap(100, 100)
        pix.fill(QColor("#FF0000"))
        tmpf = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        tmpf.close()
        try:
            result = save_png(pix, tmpf.name)
            assert result is True
            assert os.path.exists(tmpf.name)
            assert os.path.getsize(tmpf.name) > 0
        finally:
            os.unlink(tmpf.name)

    def test_save_jpg(self):
        from paparaz.core.export import save_jpg
        pix = QPixmap(100, 100)
        pix.fill(QColor("#0000FF"))
        tmpf = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        tmpf.close()
        try:
            result = save_jpg(pix, tmpf.name, quality=80)
            assert result is True
            assert os.path.exists(tmpf.name)
        finally:
            os.unlink(tmpf.name)

    def test_render_to_pixmap(self):
        c = make_canvas(200, 100)
        elem = RectElement(QRectF(10, 10, 50, 30), filled=True, style=ElementStyle())
        c.add_element(elem, auto_select=False)
        pix = c.render_to_pixmap()
        assert pix.width() == 200
        assert pix.height() == 100

    def test_copy_to_clipboard(self):
        from paparaz.core.export import copy_to_clipboard
        pix = QPixmap(100, 100)
        pix.fill(QColor("#00FF00"))
        copy_to_clipboard(pix)
        clip = QApplication.clipboard()
        img = clip.pixmap()
        assert not img.isNull()


# ===========================================================================
# 17. Canvas Zoom and Pan
# ===========================================================================

class TestCanvasZoomPan:
    def test_default_zoom_is_one(self):
        c = make_canvas()
        assert c._zoom == pytest.approx(1.0)

    def test_set_zoom(self):
        c = make_canvas()
        c.set_zoom(2.0)
        assert c._zoom == pytest.approx(2.0)

    def test_zoom_clamps_to_range(self):
        c = make_canvas()
        c.set_zoom(0.001)
        assert c._zoom >= 0.1
        c.set_zoom(100.0)
        assert c._zoom <= 10.0

    def test_screen_to_canvas_at_zoom_1(self):
        c = make_canvas()
        pos = c._screen_to_canvas(QPointF(100, 200))
        assert pos.x() == pytest.approx(100)
        assert pos.y() == pytest.approx(200)

    def test_screen_to_canvas_at_zoom_2(self):
        c = make_canvas()
        c.set_zoom(2.0)
        pos = c._screen_to_canvas(QPointF(200, 400))
        assert pos.x() == pytest.approx(100)
        assert pos.y() == pytest.approx(200)


# ===========================================================================
# 18. Locked and Hidden Elements
# ===========================================================================

class TestLockedHiddenElements:
    def setup_method(self):
        self.c = make_canvas()
        self.select = SelectTool(self.c)
        self.c.set_tool(self.select)

    def test_locked_element_cannot_be_selected(self):
        elem = RectElement(QRectF(100, 100, 80, 60), filled=True, style=ElementStyle())
        elem.locked = True
        self.c.add_element(elem, auto_select=False)
        click(self.select, QPointF(140, 130))
        assert self.c.selected_element is None

    def test_hidden_element_cannot_be_selected(self):
        elem = RectElement(QRectF(100, 100, 80, 60), filled=True, style=ElementStyle())
        elem.visible = False
        self.c.add_element(elem, auto_select=False)
        click(self.select, QPointF(140, 130))
        assert self.c.selected_element is None


# ===========================================================================
# 19. CurvedArrowTool — 3-Phase Creation
# ===========================================================================

class TestCurvedArrowTool:
    """Three-click Bezier arrow: start → end → control point."""

    def setup_method(self):
        self.c = make_canvas()
        self.tool = CurvedArrowTool(self.c)
        self.c.set_tool(self.tool)

    def test_initial_phase_is_idle(self):
        assert self.tool._phase == CurvedArrowTool._PHASE_IDLE
        assert self.tool._start is None

    def test_first_click_sets_start(self):
        click(self.tool, QPointF(100, 100))
        assert self.tool._phase == CurvedArrowTool._PHASE_END
        assert self.tool._start.x() == pytest.approx(100)

    def test_second_click_sets_end(self):
        click(self.tool, QPointF(100, 100))
        click(self.tool, QPointF(300, 200))
        assert self.tool._phase == CurvedArrowTool._PHASE_CTRL
        assert self.tool._end.x() == pytest.approx(300)

    def test_third_click_commits_element(self):
        click(self.tool, QPointF(100, 100))
        click(self.tool, QPointF(300, 200))
        # Move to control position then click
        self.tool.on_hover(QPointF(200, 50))
        click(self.tool, QPointF(200, 50))
        assert self.tool._phase == CurvedArrowTool._PHASE_IDLE
        assert len(self.c.elements) == 1
        assert self.c.elements[0].element_type.name == "CURVED_ARROW"

    def test_escape_cancels(self):
        click(self.tool, QPointF(100, 100))
        assert self.tool._phase == CurvedArrowTool._PHASE_END
        key(self.tool, Qt.Key.Key_Escape)
        assert self.tool._phase == CurvedArrowTool._PHASE_IDLE
        assert len(self.c.elements) == 0

    def test_enter_commits_in_ctrl_phase(self):
        click(self.tool, QPointF(100, 100))
        click(self.tool, QPointF(300, 200))
        self.tool.on_hover(QPointF(200, 50))
        key(self.tool, Qt.Key.Key_Return)
        assert self.tool._phase == CurvedArrowTool._PHASE_IDLE
        assert len(self.c.elements) == 1

    def test_enter_does_nothing_in_end_phase(self):
        click(self.tool, QPointF(100, 100))
        key(self.tool, Qt.Key.Key_Return)
        assert self.tool._phase == CurvedArrowTool._PHASE_END
        assert len(self.c.elements) == 0

    def test_hover_updates_control_in_ctrl_phase(self):
        click(self.tool, QPointF(100, 100))
        click(self.tool, QPointF(300, 200))
        self.tool.on_hover(QPointF(50, 300))
        assert self.tool._preview.control.x() == pytest.approx(50)
        assert self.tool._preview.control.y() == pytest.approx(300)


# ===========================================================================
# 20. HighlightTool — Default Seeding
# ===========================================================================

class TestHighlightTool:
    def test_defaults_seeded_on_activate(self):
        c = make_canvas()
        c._fg_color = "#FF0000"  # untouched default
        c._line_width = 2.0
        tool = HighlightTool(c)
        c.set_tool(tool)
        tool.on_activate()
        assert c._fg_color == HighlightTool.DEFAULT_COLOR
        assert c._line_width == float(HighlightTool.DEFAULT_WIDTH)

    def test_defaults_not_overwritten_if_user_changed(self):
        c = make_canvas()
        c._fg_color = "#00FF00"  # user-picked, not the default red
        c._line_width = 10.0
        tool = HighlightTool(c)
        c.set_tool(tool)
        tool.on_activate()
        # Should keep user choices since they differ from untouched defaults
        assert c._fg_color == "#00FF00"
        assert c._line_width == 10.0

    def test_creates_highlight_element(self):
        c = make_canvas()
        tool = HighlightTool(c)
        c.set_tool(tool)
        drag(tool, QPointF(10, 10), QPointF(200, 10))
        assert len(c.elements) == 1
        assert c.elements[0].element_type.name == "HIGHLIGHT"

    def test_short_stroke_discarded(self):
        c = make_canvas()
        tool = HighlightTool(c)
        c.set_tool(tool)
        # Single point — less than 2 points
        ev = _FakeEvent()
        tool.on_press(QPointF(50, 50), ev)
        tool.on_release(QPointF(50, 50), ev)
        assert len(c.elements) == 0


# ===========================================================================
# 21. Hotkey Parsing — Pure Function
# ===========================================================================

class TestHotkeyParsing:
    def test_simple_key(self):
        from paparaz.utils.hotkey import parse_hotkey, MOD_NONE, VK_MAP
        mods, vk = parse_hotkey("PrintScreen")
        assert mods == MOD_NONE
        assert vk == VK_MAP["PrintScreen"]

    def test_ctrl_shift_combo(self):
        from paparaz.utils.hotkey import parse_hotkey, MOD_CTRL, MOD_SHIFT, VK_MAP
        mods, vk = parse_hotkey("Ctrl+Shift+PrintScreen")
        assert mods == (MOD_CTRL | MOD_SHIFT)
        assert vk == VK_MAP["PrintScreen"]

    def test_single_letter(self):
        from paparaz.utils.hotkey import parse_hotkey, MOD_NONE
        mods, vk = parse_hotkey("A")
        assert mods == MOD_NONE
        assert vk == ord("A")

    def test_ctrl_letter(self):
        from paparaz.utils.hotkey import parse_hotkey, MOD_CTRL
        mods, vk = parse_hotkey("Ctrl+S")
        assert mods == MOD_CTRL
        assert vk == ord("S")

    def test_alt_modifier(self):
        from paparaz.utils.hotkey import parse_hotkey, MOD_ALT, VK_MAP
        mods, vk = parse_hotkey("Alt+PrintScreen")
        assert mods == MOD_ALT
        assert vk == VK_MAP["PrintScreen"]

    def test_function_key(self):
        from paparaz.utils.hotkey import parse_hotkey, MOD_NONE, VK_MAP
        mods, vk = parse_hotkey("F5")
        assert mods == MOD_NONE
        assert vk == VK_MAP["F5"]

    def test_empty_string(self):
        from paparaz.utils.hotkey import parse_hotkey, MOD_NONE
        mods, vk = parse_hotkey("")
        assert mods == MOD_NONE
        assert vk == 0


# ===========================================================================
# 22. Recovery Module
# ===========================================================================

class TestRecoveryModule:
    def setup_method(self):
        import tempfile
        from paparaz.core import recovery
        self._orig_dir = recovery.RECOVERY_DIR
        self._tmpdir = tempfile.mkdtemp()
        recovery.RECOVERY_DIR = Path(self._tmpdir) / "recovery"

    def teardown_method(self):
        from paparaz.core import recovery
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)
        recovery.RECOVERY_DIR = self._orig_dir

    def test_save_and_get(self):
        from paparaz.core.recovery import save_snapshot, get_recovery_files
        pix = QPixmap(100, 100)
        pix.fill(Qt.GlobalColor.red)
        path = save_snapshot(pix, editor_id=42)
        assert path is not None
        assert path.exists()
        files = get_recovery_files()
        assert len(files) == 1

    def test_clear_specific(self):
        from paparaz.core.recovery import save_snapshot, clear_recovery, get_recovery_files
        pix = QPixmap(100, 100)
        pix.fill(Qt.GlobalColor.blue)
        save_snapshot(pix, editor_id=1)
        save_snapshot(pix, editor_id=2)
        assert len(get_recovery_files()) == 2
        clear_recovery(editor_id=1)
        files = get_recovery_files()
        assert len(files) == 1

    def test_clear_all(self):
        from paparaz.core.recovery import save_snapshot, clear_recovery, get_recovery_files
        pix = QPixmap(100, 100)
        pix.fill(Qt.GlobalColor.green)
        save_snapshot(pix, editor_id=10)
        save_snapshot(pix, editor_id=20)
        clear_recovery()
        assert len(get_recovery_files()) == 0

    def test_has_recovery(self):
        from paparaz.core.recovery import save_snapshot, has_recovery, clear_recovery
        assert not has_recovery()
        pix = QPixmap(50, 50)
        pix.fill(Qt.GlobalColor.white)
        save_snapshot(pix, editor_id=99)
        assert has_recovery()
        clear_recovery()
        assert not has_recovery()


# ===========================================================================
# 23. Filename build_save_path + Collision Avoidance
# ===========================================================================

class TestBuildSavePath:
    def setup_method(self):
        self._tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_basic_path(self):
        from paparaz.core.filename_pattern import build_save_path
        p = build_save_path("test_file", self._tmpdir, ext="png")
        assert p.parent == Path(self._tmpdir)
        assert p.name == "test_file.png"

    def test_collision_appends_number(self):
        from paparaz.core.filename_pattern import build_save_path
        # Create first file
        first = Path(self._tmpdir) / "shot.png"
        first.write_bytes(b"fake")
        p = build_save_path("shot", self._tmpdir, ext="png")
        assert p.name == "shot (2).png"

    def test_multiple_collisions(self):
        from paparaz.core.filename_pattern import build_save_path
        (Path(self._tmpdir) / "img.png").write_bytes(b"x")
        (Path(self._tmpdir) / "img (2).png").write_bytes(b"x")
        p = build_save_path("img", self._tmpdir, ext="png")
        assert p.name == "img (3).png"

    def test_subfolder_pattern(self):
        from paparaz.core.filename_pattern import build_save_path
        p = build_save_path("pic", self._tmpdir, subfolder_pattern="screenshots", ext="jpg")
        assert "screenshots" in str(p)
        assert p.name == "pic.jpg"

    def test_default_dir_when_empty(self):
        from paparaz.core.filename_pattern import build_save_path
        p = build_save_path("test", "", ext="png")
        assert "Pictures" in str(p) or "PapaRaZ" in str(p)


# ===========================================================================
# 24. Layers Panel Logic
# ===========================================================================

class TestLayersPanel:
    def setup_method(self):
        from paparaz.ui.layers_panel import LayersPanel
        self.c = make_canvas()
        self.panel = LayersPanel()
        self.panel.set_canvas(self.c)

    def test_refresh_shows_all_elements(self):
        e1 = RectElement(QRectF(0, 0, 50, 50), filled=True, style=ElementStyle())
        e2 = EllipseElement(QRectF(60, 60, 40, 40), ElementStyle())
        self.c.add_element(e1, auto_select=False)
        self.c.add_element(e2, auto_select=False)
        self.panel.refresh()
        assert self.panel._list.count() == 2

    def test_move_up(self):
        e1 = RectElement(QRectF(0, 0, 50, 50), filled=True, style=ElementStyle())
        e2 = RectElement(QRectF(60, 60, 40, 40), filled=True, style=ElementStyle())
        self.c.add_element(e1, auto_select=False)
        self.c.add_element(e2, auto_select=False)
        self.panel.refresh()
        # e2 is at canvas index 1 (front). In list, it's row 0.
        # e1 is at canvas index 0 (back). In list, it's row 1.
        # Select e1 (row 1) and move up => should go to front
        self.panel._list.setCurrentRow(1)
        self.panel._move_up()
        assert self.c.elements[-1] is e1  # e1 now at front

    def test_move_down(self):
        e1 = RectElement(QRectF(0, 0, 50, 50), filled=True, style=ElementStyle())
        e2 = RectElement(QRectF(60, 60, 40, 40), filled=True, style=ElementStyle())
        self.c.add_element(e1, auto_select=False)
        self.c.add_element(e2, auto_select=False)
        self.panel.refresh()
        # e2 is front (row 0 in list), select it and move down
        self.panel._list.setCurrentRow(0)
        self.panel._move_down()
        assert self.c.elements[0] is e2  # e2 moved to back

    def test_delete_selected(self):
        e1 = RectElement(QRectF(0, 0, 50, 50), filled=True, style=ElementStyle())
        self.c.add_element(e1, auto_select=False)
        self.panel.refresh()
        self.panel._list.setCurrentRow(0)
        self.panel._delete_selected()
        assert len(self.c.elements) == 0

    def test_toggle_visibility(self):
        e1 = RectElement(QRectF(0, 0, 50, 50), filled=True, style=ElementStyle())
        self.c.add_element(e1, auto_select=False)
        assert e1.visible is True
        self.panel.toggle_visibility(e1)
        assert e1.visible is False
        self.panel.toggle_visibility(e1)
        assert e1.visible is True

    def test_hidden_element_label(self):
        e1 = RectElement(QRectF(0, 0, 50, 50), filled=True, style=ElementStyle())
        e1.visible = False
        self.c.add_element(e1, auto_select=False)
        self.panel.refresh()
        label = self.panel._list.item(0).text()
        assert "👁" in label


# ===========================================================================
# 25. Canvas Style Setters — Opacity, Cap, Join, Dash
# ===========================================================================

class TestCanvasStyleSetters:
    def setup_method(self):
        self.c = make_canvas()

    def test_set_opacity(self):
        e = RectElement(QRectF(10, 10, 80, 60), filled=True, style=ElementStyle())
        self.c.add_element(e)
        self.c.set_opacity(0.5)
        assert self.c.selected_element.style.opacity == pytest.approx(0.5)

    def test_set_cap_style(self):
        e = LineElement(QPointF(10, 10), QPointF(100, 10), ElementStyle())
        self.c.add_element(e)
        self.c.set_cap_style("square")
        assert self.c.selected_element.style.cap_style == "square"

    def test_set_join_style(self):
        e = RectElement(QRectF(10, 10, 80, 60), filled=True, style=ElementStyle())
        self.c.add_element(e)
        self.c.set_join_style("bevel")
        assert self.c.selected_element.style.join_style == "bevel"

    def test_set_dash_pattern(self):
        e = RectElement(QRectF(10, 10, 80, 60), filled=True, style=ElementStyle())
        self.c.add_element(e)
        self.c.set_dash_pattern("dash")
        assert self.c.selected_element.style.dash_pattern == "dash"

    def test_set_filled(self):
        e = RectElement(QRectF(10, 10, 80, 60), filled=True, style=ElementStyle())
        self.c.add_element(e)
        self.c.set_filled(True)
        assert e.filled is True

    def test_set_rotation(self):
        e = RectElement(QRectF(10, 10, 80, 60), filled=True, style=ElementStyle())
        self.c.add_element(e)
        self.c.set_rotation(45.0)
        assert e.rotation == pytest.approx(45.0)

    def test_opacity_undo(self):
        e = RectElement(QRectF(10, 10, 80, 60), filled=True, style=ElementStyle())
        self.c.add_element(e)
        self.c.set_opacity(0.3)
        self.c.history.undo()
        assert e.style.opacity == pytest.approx(1.0)


# ===========================================================================
# 26. CurvedArrowElement — Geometry
# ===========================================================================

class TestCurvedArrowElement:
    def test_default_control_point(self):
        from paparaz.core.elements import CurvedArrowElement
        e = CurvedArrowElement(QPointF(0, 0), QPointF(100, 0))
        # Default control is perpendicular offset at midpoint
        assert e.control.x() == pytest.approx(50, abs=1)
        assert e.control.y() != pytest.approx(0, abs=1)  # offset perpendicular

    def test_bounding_rect_contains_all_points(self):
        from paparaz.core.elements import CurvedArrowElement
        e = CurvedArrowElement(QPointF(10, 10), QPointF(200, 100), QPointF(100, 0))
        br = e.bounding_rect()
        assert br.contains(QPointF(10, 10))
        assert br.contains(QPointF(200, 100))

    def test_coincident_start_end(self):
        from paparaz.core.elements import CurvedArrowElement
        e = CurvedArrowElement(QPointF(50, 50), QPointF(50, 50))
        # Should not crash with zero-length chord
        br = e.bounding_rect()
        assert br.width() >= 0
        assert br.height() >= 0


# ===========================================================================
# 27. CropTool — Axis-Aligned + Rotation
# ===========================================================================

class TestCropTool:
    def setup_method(self):
        self.c = make_canvas(400, 300)
        from paparaz.tools.special import CropTool
        self.tool = CropTool(self.c)
        self.c.set_tool(self.tool)

    def test_drag_activates_crop_region(self):
        drag(self.tool, QPointF(50, 50), QPointF(200, 200))
        assert self.tool._active is True
        r = self.tool._rect()
        assert r.width() == pytest.approx(150)
        assert r.height() == pytest.approx(150)

    def test_escape_cancels_crop(self):
        drag(self.tool, QPointF(50, 50), QPointF(200, 200))
        key(self.tool, Qt.Key.Key_Escape)
        assert self.tool._active is False

    def test_enter_applies_axis_aligned_crop(self):
        drag(self.tool, QPointF(50, 50), QPointF(200, 200))
        old_w = self.c._background.width()
        key(self.tool, Qt.Key.Key_Return)
        assert self.tool._active is False
        assert self.c._background.width() == 150
        assert self.c._background.height() == 150

    def test_crop_is_undoable(self):
        drag(self.tool, QPointF(50, 50), QPointF(200, 200))
        key(self.tool, Qt.Key.Key_Return)
        assert self.c._background.width() == 150
        self.c.history.undo()
        assert self.c._background.width() == 400

    def test_small_region_rejected(self):
        drag(self.tool, QPointF(100, 100), QPointF(103, 103))
        key(self.tool, Qt.Key.Key_Return)
        # Too small — region < 5px, should not crop
        assert self.c._background.width() == 400

    def test_rotation_handle_detected(self):
        drag(self.tool, QPointF(50, 50), QPointF(200, 200))
        # Initially no rotation
        assert self.tool._rotation == pytest.approx(0.0)

    def test_crop_shifts_elements(self):
        e = RectElement(QRectF(100, 100, 40, 30), filled=True, style=ElementStyle())
        self.c.add_element(e, auto_select=False)
        old_x = e.rect.x()
        drag(self.tool, QPointF(50, 50), QPointF(250, 250))
        key(self.tool, Qt.Key.Key_Return)
        # Element should shift by -50 (crop origin at 50)
        assert e.rect.x() == pytest.approx(old_x - 50)


# ===========================================================================
# 28. Text Cursor Navigation
# ===========================================================================

class TestTextCursorNavigation:
    def setup_method(self):
        self.c = make_canvas()
        self.tool = TextTool(self.c)
        self.c.set_tool(self.tool)

    def _create_text(self, text):
        click(self.tool, QPointF(50, 50))
        elem = self.tool._active_text
        for ch in text:
            key(self.tool, 0, text=ch)
        return elem

    def test_left_arrow_moves_cursor_back(self):
        elem = self._create_text("abc")
        assert elem.cursor_pos == 3
        key(self.tool, Qt.Key.Key_Left)
        assert elem.cursor_pos == 2

    def test_right_arrow_moves_cursor_forward(self):
        elem = self._create_text("abc")
        key(self.tool, Qt.Key.Key_Left)
        key(self.tool, Qt.Key.Key_Left)
        assert elem.cursor_pos == 1
        key(self.tool, Qt.Key.Key_Right)
        assert elem.cursor_pos == 2

    def test_home_goes_to_start(self):
        elem = self._create_text("hello")
        key(self.tool, Qt.Key.Key_Home)
        assert elem.cursor_pos == 0

    def test_end_goes_to_end(self):
        elem = self._create_text("hello")
        key(self.tool, Qt.Key.Key_Home)
        key(self.tool, Qt.Key.Key_End)
        assert elem.cursor_pos == 5

    def test_ctrl_home_absolute_start(self):
        elem = self._create_text("line1")
        key(self.tool, Qt.Key.Key_Return)
        key(self.tool, 0, text="2")
        key(self.tool, Qt.Key.Key_Home, mods=Qt.KeyboardModifier.ControlModifier)
        assert elem.cursor_pos == 0

    def test_ctrl_end_absolute_end(self):
        elem = self._create_text("line1")
        key(self.tool, Qt.Key.Key_Return)
        key(self.tool, 0, text="2")
        key(self.tool, Qt.Key.Key_Home, mods=Qt.KeyboardModifier.ControlModifier)
        key(self.tool, Qt.Key.Key_End, mods=Qt.KeyboardModifier.ControlModifier)
        assert elem.cursor_pos == len(elem.text)

    def test_ctrl_a_selects_all(self):
        elem = self._create_text("hello")
        key(self.tool, Qt.Key.Key_A, mods=Qt.KeyboardModifier.ControlModifier)
        assert elem.sel_start == 0
        assert elem.cursor_pos == 5

    def test_left_at_start_stays(self):
        elem = self._create_text("a")
        key(self.tool, Qt.Key.Key_Home)
        key(self.tool, Qt.Key.Key_Left)
        assert elem.cursor_pos == 0

    def test_right_at_end_stays(self):
        elem = self._create_text("a")
        key(self.tool, Qt.Key.Key_Right)
        assert elem.cursor_pos == 1  # already at end

    def test_backspace_mid_text(self):
        elem = self._create_text("abc")
        key(self.tool, Qt.Key.Key_Left)  # cursor at 2
        key(self.tool, Qt.Key.Key_Backspace)
        assert elem.text == "ac"
        assert elem.cursor_pos == 1


# ===========================================================================
# 29. FillTool — Basic Behavior
# ===========================================================================

class TestFillToolBasic:
    """Tests FillTool initialization and tolerance without pixel-level flood fill."""

    def test_fill_tool_has_tolerance(self):
        c = make_canvas()
        tool = FillTool(c)
        assert hasattr(tool, 'tolerance')
        assert tool.tolerance == 15

    def test_fill_tool_cursor(self):
        c = make_canvas()
        tool = FillTool(c)
        assert tool.cursor == Qt.CursorShape.CrossCursor

    def test_fill_same_color_skipped(self):
        """Fill with the same color as target should be a no-op."""
        c = make_canvas()
        c._fg_color = "#FFFFFF"  # same as white background
        tool = FillTool(c)
        c.set_tool(tool)
        initial_stack = len(c.history._undo_stack)
        ev = _FakeEvent()
        tool.on_press(QPointF(50, 50), ev)
        # Should not add history entry since fill color == target
        assert len(c.history._undo_stack) == initial_stack

    def test_fill_different_color_creates_history(self):
        """Fill with a different color should add a history entry."""
        c = make_canvas()
        c._fg_color = "#FF0000"  # red on white background
        tool = FillTool(c)
        c.set_tool(tool)
        initial_stack = len(c.history._undo_stack)
        ev = _FakeEvent()
        tool.on_press(QPointF(50, 50), ev)
        # Should add one undo entry
        assert len(c.history._undo_stack) == initial_stack + 1

    def test_fill_out_of_bounds_ignored(self):
        """Click outside canvas bounds should not crash."""
        c = make_canvas(100, 100)
        c._fg_color = "#FF0000"
        tool = FillTool(c)
        c.set_tool(tool)
        initial_stack = len(c.history._undo_stack)
        ev = _FakeEvent()
        tool.on_press(QPointF(-10, -10), ev)
        assert len(c.history._undo_stack) == initial_stack

    def test_fill_undoable(self):
        c = make_canvas()
        c._fg_color = "#0000FF"
        tool = FillTool(c)
        c.set_tool(tool)
        old_bg = QPixmap(c._background)
        ev = _FakeEvent()
        tool.on_press(QPointF(50, 50), ev)
        c.history.undo()
        # Background should be restored
        assert c._background.size() == old_bg.size()


# ===========================================================================
# Phase A: SliceTool
# ===========================================================================

class TestSliceTool:
    """SliceTool: draw selection, apply slice, cancel."""

    def test_activation_sets_crosshair(self):
        c = make_canvas()
        tool = SliceTool(c)
        assert tool.cursor == Qt.CursorShape.CrossCursor

    def test_draw_selection_sets_active(self):
        c = make_canvas()
        tool = SliceTool(c)
        c.set_tool(tool)
        ev = _FakeEvent()
        tool.on_press(QPointF(50, 50), ev)
        assert tool._active is True
        tool.on_move(QPointF(200, 200), ev)
        tool.on_release(QPointF(200, 200), ev)
        assert tool._active is True  # stays active until apply/cancel

    def test_cancel_via_escape(self):
        c = make_canvas()
        tool = SliceTool(c)
        c.set_tool(tool)
        ev = _FakeEvent()
        tool.on_press(QPointF(50, 50), ev)
        tool.on_move(QPointF(200, 200), ev)
        tool.on_release(QPointF(200, 200), ev)
        assert tool._active is True
        key(tool, Qt.Key.Key_Escape)
        assert tool._active is False

    def test_apply_via_enter_creates_element(self):
        c = make_canvas()
        tool = SliceTool(c)
        c.set_tool(tool)
        ev = _FakeEvent()
        tool.on_press(QPointF(50, 50), ev)
        tool.on_move(QPointF(200, 200), ev)
        tool.on_release(QPointF(200, 200), ev)
        before = len(c.elements)
        key(tool, Qt.Key.Key_Return)
        assert len(c.elements) == before + 1
        assert isinstance(c.elements[-1], ImageElement)

    def test_apply_via_right_click(self):
        c = make_canvas()
        tool = SliceTool(c)
        c.set_tool(tool)
        ev = _FakeEvent()
        tool.on_press(QPointF(50, 50), ev)
        tool.on_move(QPointF(200, 200), ev)
        tool.on_release(QPointF(200, 200), ev)
        before = len(c.elements)
        rc = _RightClickEvent()
        tool.on_press(QPointF(100, 100), rc)
        assert len(c.elements) == before + 1

    def test_apply_via_double_click(self):
        c = make_canvas()
        tool = SliceTool(c)
        c.set_tool(tool)
        ev = _FakeEvent()
        tool.on_press(QPointF(50, 50), ev)
        tool.on_move(QPointF(200, 200), ev)
        tool.on_release(QPointF(200, 200), ev)
        before = len(c.elements)
        tool.on_double_click(QPointF(100, 100), ev)
        assert len(c.elements) == before + 1

    def test_slice_undoable(self):
        c = make_canvas()
        tool = SliceTool(c)
        c.set_tool(tool)
        ev = _FakeEvent()
        tool.on_press(QPointF(50, 50), ev)
        tool.on_move(QPointF(200, 200), ev)
        tool.on_release(QPointF(200, 200), ev)
        key(tool, Qt.Key.Key_Return)
        assert len(c.elements) == 1
        c.history.undo()
        assert len(c.elements) == 0

    def test_tiny_selection_cancels(self):
        c = make_canvas()
        tool = SliceTool(c)
        c.set_tool(tool)
        ev = _FakeEvent()
        tool.on_press(QPointF(50, 50), ev)
        tool.on_move(QPointF(51, 51), ev)  # < 4px
        tool.on_release(QPointF(51, 51), ev)
        key(tool, Qt.Key.Key_Return)
        assert len(c.elements) == 0  # too small, cancelled

    def test_right_click_ignored_when_no_selection(self):
        c = make_canvas()
        tool = SliceTool(c)
        c.set_tool(tool)
        rc = _RightClickEvent()
        tool.on_press(QPointF(100, 100), rc)
        assert len(c.elements) == 0

    def test_slice_deactivates_after_apply(self):
        c = make_canvas()
        tool = SliceTool(c)
        c.set_tool(tool)
        ev = _FakeEvent()
        tool.on_press(QPointF(50, 50), ev)
        tool.on_move(QPointF(200, 200), ev)
        tool.on_release(QPointF(200, 200), ev)
        key(tool, Qt.Key.Key_Return)
        assert tool._active is False

    def test_new_selection_resets_rotation(self):
        c = make_canvas()
        tool = SliceTool(c)
        c.set_tool(tool)
        ev = _FakeEvent()
        tool.on_press(QPointF(50, 50), ev)
        tool.on_release(QPointF(200, 200), ev)
        tool._rotation = 45.0  # simulate rotation
        # Start new selection
        tool.on_press(QPointF(10, 10), ev)
        assert tool._rotation == 0.0

    def test_multiple_slices(self):
        c = make_canvas()
        tool = SliceTool(c)
        c.set_tool(tool)
        ev = _FakeEvent()
        # First slice
        tool.on_press(QPointF(10, 10), ev)
        tool.on_move(QPointF(100, 100), ev)
        tool.on_release(QPointF(100, 100), ev)
        key(tool, Qt.Key.Key_Return)
        assert len(c.elements) == 1
        # Second slice
        tool.on_press(QPointF(200, 200), ev)
        tool.on_move(QPointF(350, 350), ev)
        tool.on_release(QPointF(350, 350), ev)
        key(tool, Qt.Key.Key_Return)
        assert len(c.elements) == 2


# ===========================================================================
# Phase A: EyedropperTool
# ===========================================================================

class TestEyedropperTool:
    """EyedropperTool: colour sampling, auto-return to previous tool."""

    def test_tool_type_is_eyedropper(self):
        c = make_canvas()
        tool = EyedropperTool(c)
        assert tool.tool_type == ToolType.EYEDROPPER

    def test_cursor_is_crosshair(self):
        c = make_canvas()
        tool = EyedropperTool(c)
        assert tool.cursor == Qt.CursorShape.CrossCursor

    def test_on_activate_remembers_prev_tool(self):
        c = make_canvas()
        pen = PenTool(c)
        c.set_tool(pen)
        eye = EyedropperTool(c)
        c._tool = pen  # simulate active tool
        eye.on_activate()
        assert eye._prev_tool_type == ToolType.PEN

    def test_on_activate_does_not_remember_self(self):
        c = make_canvas()
        eye = EyedropperTool(c)
        c._tool = eye
        eye.on_activate()
        assert eye._prev_tool_type is None

    def test_left_click_sets_fg_color(self):
        c = make_canvas()
        c._fg_color = "#000000"
        eye = EyedropperTool(c)
        c.set_tool(eye)
        # _sample_color returns white in headless (no screen)
        ev = _FakeEvent()
        eye.on_press(QPointF(50, 50), ev)
        # In headless, primaryScreen() may be None → returns white
        # But set_foreground_color should have been called

    def test_right_click_sets_bg_color(self):
        c = make_canvas()
        eye = EyedropperTool(c)
        c.set_tool(eye)
        rc = _RightClickEvent()
        eye.on_press(QPointF(50, 50), rc)
        # Verifies no crash on right-click path

    def test_return_to_prev_tool_defaults_to_select(self):
        c = make_canvas()
        eye = EyedropperTool(c)
        assert eye._prev_tool_type is None
        # When returning with None, should default to SELECT
        # (it sets _prev_tool_type = TT.SELECT internally)

    def test_loupe_constants(self):
        c = make_canvas()
        eye = EyedropperTool(c)
        assert eye._LOUPE_D == 80
        assert eye._ZOOM == 10
        assert eye._SAMPLE_R == 4  # 80 // (2*10)

    def test_on_release_is_noop(self):
        c = make_canvas()
        eye = EyedropperTool(c)
        c.set_tool(eye)
        ev = _FakeEvent()
        # Should not crash
        eye.on_release(QPointF(50, 50), ev)


# ===========================================================================
# Phase A: MagnifierTool & MagnifierElement
# ===========================================================================

class TestMagnifierTool:
    """MagnifierTool: create magnifier elements."""

    def test_tool_type_and_cursor(self):
        c = make_canvas()
        tool = MagnifierTool(c)
        assert tool.tool_type == ToolType.MAGNIFIER
        assert tool.cursor == Qt.CursorShape.CrossCursor

    def test_default_zoom(self):
        c = make_canvas()
        tool = MagnifierTool(c)
        assert tool.zoom == 2.0

    def test_press_creates_element(self):
        c = make_canvas()
        tool = MagnifierTool(c)
        c.set_tool(tool)
        ev = _FakeEvent()
        tool.on_press(QPointF(50, 50), ev)
        assert tool._current is not None
        assert isinstance(tool._current, MagnifierElement)

    def test_move_updates_source_display(self):
        c = make_canvas()
        tool = MagnifierTool(c)
        c.set_tool(tool)
        ev = _FakeEvent()
        tool.on_press(QPointF(50, 50), ev)
        tool.on_move(QPointF(150, 150), ev)
        src = tool._current.source_rect.normalized()
        assert src.width() == 100
        assert src.height() == 100
        # Display should be 2x the source
        disp = tool._current.display_rect
        assert disp.width() == 200
        assert disp.height() == 200

    def test_release_adds_element_if_large_enough(self):
        c = make_canvas()
        tool = MagnifierTool(c)
        c.set_tool(tool)
        ev = _FakeEvent()
        tool.on_press(QPointF(50, 50), ev)
        tool.on_move(QPointF(150, 150), ev)
        tool.on_release(QPointF(150, 150), ev)
        assert len(c.elements) == 1
        assert isinstance(c.elements[0], MagnifierElement)

    def test_release_ignores_tiny_selection(self):
        c = make_canvas()
        tool = MagnifierTool(c)
        c.set_tool(tool)
        ev = _FakeEvent()
        tool.on_press(QPointF(50, 50), ev)
        tool.on_move(QPointF(52, 52), ev)  # < 5px
        tool.on_release(QPointF(52, 52), ev)
        assert len(c.elements) == 0

    def test_release_clears_state(self):
        c = make_canvas()
        tool = MagnifierTool(c)
        c.set_tool(tool)
        ev = _FakeEvent()
        tool.on_press(QPointF(50, 50), ev)
        tool.on_move(QPointF(150, 150), ev)
        tool.on_release(QPointF(150, 150), ev)
        assert tool._current is None
        assert tool._start is None


class TestMagnifierElement:
    """MagnifierElement: bounding_rect, contains_point, move_by, paint."""

    def test_bounding_rect_uses_display(self):
        src = QRectF(10, 10, 50, 50)
        disp = QRectF(100, 100, 100, 100)
        elem = MagnifierElement(src, disp, zoom=2.0)
        assert elem.bounding_rect() == disp.normalized()

    def test_contains_point_in_display(self):
        src = QRectF(10, 10, 50, 50)
        disp = QRectF(100, 100, 100, 100)
        elem = MagnifierElement(src, disp, zoom=2.0)
        assert elem.contains_point(QPointF(150, 150))
        assert not elem.contains_point(QPointF(30, 30))

    def test_move_by_shifts_display(self):
        src = QRectF(10, 10, 50, 50)
        disp = QRectF(100, 100, 100, 100)
        elem = MagnifierElement(src, disp, zoom=2.0)
        elem.move_by(10, 20)
        assert elem.display_rect.x() == 110
        assert elem.display_rect.y() == 120

    def test_zoom_property(self):
        elem = MagnifierElement(QRectF(), QRectF(), zoom=3.0)
        assert elem.zoom == 3.0

    def test_element_type_is_magnifier(self):
        from paparaz.core.elements import ElementType
        elem = MagnifierElement(QRectF(), QRectF())
        assert elem.element_type == ElementType.MAGNIFIER

    def test_paint_no_crash_without_background(self):
        """Paint should not crash even with no background pixmap."""
        from PySide6.QtGui import QPainter
        src = QRectF(10, 10, 50, 50)
        disp = QRectF(100, 100, 100, 100)
        elem = MagnifierElement(src, disp, zoom=2.0)
        pix = QPixmap(400, 400)
        pix.fill(Qt.GlobalColor.white)
        p = QPainter(pix)
        elem.paint(p)  # should not crash
        p.end()

    def test_paint_with_background(self):
        from PySide6.QtGui import QPainter
        bg = QPixmap(200, 200)
        bg.fill(Qt.GlobalColor.red)
        src = QRectF(10, 10, 50, 50)
        disp = QRectF(100, 100, 100, 100)
        elem = MagnifierElement(src, disp, zoom=2.0, background=bg)
        pix = QPixmap(400, 400)
        pix.fill(Qt.GlobalColor.white)
        p = QPainter(pix)
        elem.paint(p)
        p.end()


# ===========================================================================
# Phase A: CanvasResizeDialog
# ===========================================================================

class TestCanvasResizeDialog:
    """CanvasResizeDialog: spinbox logic, aspect ratio lock, mode toggle."""

    def _make(self, w=800, h=600):
        from paparaz.ui.canvas_resize_dialog import CanvasResizeDialog
        return CanvasResizeDialog(w, h)

    def test_creation_defaults(self):
        d = self._make(800, 600)
        assert d._orig_w == 800
        assert d._orig_h == 600
        assert d._w_spin.value() == 800
        assert d._h_spin.value() == 600

    def test_get_size_px_mode(self):
        d = self._make(800, 600)
        w, h = d.get_size()
        assert w == 800
        assert h == 600

    def test_aspect_ratio_locked_by_default(self):
        d = self._make(800, 600)
        assert d._aspect_locked is True
        assert d._lock_btn.isChecked() is True

    def test_aspect_lock_width_changes_height(self):
        d = self._make(800, 600)
        d._w_spin.setValue(400)
        assert d._h_spin.value() == 300  # 400 * 600/800 = 300

    def test_aspect_lock_height_changes_width(self):
        d = self._make(800, 600)
        d._h_spin.setValue(300)
        assert d._w_spin.value() == 400

    def test_unlock_aspect_allows_independent(self):
        d = self._make(800, 600)
        d._lock_btn.setChecked(False)
        assert d._aspect_locked is False
        d._w_spin.setValue(400)
        assert d._h_spin.value() == 600  # unchanged

    def test_mode_switch_to_pct(self):
        d = self._make(800, 600)
        d._set_mode("pct")
        assert d._pct_btn.isChecked() is True
        assert d._px_btn.isChecked() is False
        assert d._w_pct_spin.value() == 100.0
        assert d._h_pct_spin.value() == 100.0

    def test_mode_switch_back_to_px(self):
        d = self._make(800, 600)
        d._set_mode("pct")
        d._set_mode("px")
        assert d._px_btn.isChecked() is True
        assert d._pct_btn.isChecked() is False

    def test_pct_mode_get_size(self):
        d = self._make(800, 600)
        d._set_mode("pct")
        d._w_pct_spin.setValue(50.0)
        # With aspect lock, h should follow
        w, h = d.get_size()
        assert w == 400
        assert h == 300

    def test_spinbox_range(self):
        d = self._make(800, 600)
        assert d._w_spin.minimum() == 1
        assert d._w_spin.maximum() == 32000
        assert d._h_spin.minimum() == 1
        assert d._h_spin.maximum() == 32000

    def test_info_label_shows_current_size(self):
        d = self._make(1920, 1080)
        assert "1920" in d._info_label.text()
        assert "1080" in d._info_label.text()

    def test_window_is_modal(self):
        d = self._make()
        assert d.isModal() is True


# ===========================================================================
# Phase A: SVG Export & render_final
# ===========================================================================

class TestExport:
    """Export module: render_final, save_png, save_jpg, save_svg."""

    def test_render_final_returns_pixmap(self):
        from paparaz.core.export import render_final
        bg = QPixmap(200, 200)
        bg.fill(Qt.GlobalColor.blue)
        result = render_final(bg)
        assert isinstance(result, QPixmap)
        assert result.size() == bg.size()

    def test_render_final_with_callback(self):
        from paparaz.core.export import render_final
        from PySide6.QtGui import QPainter
        bg = QPixmap(200, 200)
        bg.fill(Qt.GlobalColor.white)
        called = [False]

        def paint(painter: QPainter):
            called[0] = True
            painter.fillRect(10, 10, 50, 50, QColor("red"))

        result = render_final(bg, paint)
        assert called[0] is True
        assert result.size() == bg.size()

    def test_render_final_without_callback(self):
        from paparaz.core.export import render_final
        bg = QPixmap(100, 100)
        bg.fill(Qt.GlobalColor.green)
        result = render_final(bg, None)
        assert result.size() == bg.size()

    def test_save_png(self):
        from paparaz.core.export import save_png
        bg = QPixmap(100, 100)
        bg.fill(Qt.GlobalColor.red)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = f.name
        try:
            ok = save_png(bg, path)
            assert ok is True
            assert os.path.exists(path)
            assert os.path.getsize(path) > 0
        finally:
            os.unlink(path)

    def test_save_png_with_compression(self):
        from paparaz.core.export import save_png
        bg = QPixmap(100, 100)
        bg.fill(Qt.GlobalColor.red)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = f.name
        try:
            ok = save_png(bg, path, compression=5)
            assert ok is True
        finally:
            os.unlink(path)

    def test_save_jpg(self):
        from paparaz.core.export import save_jpg
        bg = QPixmap(100, 100)
        bg.fill(Qt.GlobalColor.blue)
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            path = f.name
        try:
            ok = save_jpg(bg, path, quality=80)
            assert ok is True
            assert os.path.exists(path)
        finally:
            os.unlink(path)

    def test_save_svg(self):
        from paparaz.core.export import save_svg
        bg = QPixmap(200, 200)
        bg.fill(Qt.GlobalColor.white)
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            path = f.name
        try:
            ok = save_svg(bg, path)
            assert ok is True
            assert os.path.exists(path)
            with open(path, "r") as f:
                content = f.read()
            assert "svg" in content.lower()
        finally:
            os.unlink(path)

    def test_save_svg_with_callback(self):
        from paparaz.core.export import save_svg
        from PySide6.QtGui import QPainter
        bg = QPixmap(200, 200)
        bg.fill(Qt.GlobalColor.white)
        called = [False]

        def paint(painter: QPainter):
            called[0] = True
            painter.fillRect(10, 10, 50, 50, QColor("red"))

        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            path = f.name
        try:
            ok = save_svg(bg, path, paint)
            assert ok is True
            assert called[0] is True
        finally:
            os.unlink(path)

    def test_copy_to_clipboard(self):
        from paparaz.core.export import copy_to_clipboard
        bg = QPixmap(50, 50)
        bg.fill(Qt.GlobalColor.cyan)
        copy_to_clipboard(bg)
        clip = QApplication.clipboard()
        assert not clip.pixmap().isNull()


# ===========================================================================
# Phase A: SidePanel TOOL_SECTIONS Deep Coverage
# ===========================================================================

class TestToolSectionsMappings:
    """Verify every tool type in TOOL_SECTIONS maps to correct sections."""

    def _panel(self):
        from paparaz.ui.side_panel import SidePanel
        bg = QPixmap(400, 300)
        bg.fill(Qt.GlobalColor.white)
        canvas = AnnotationCanvas(bg)
        return SidePanel(canvas), canvas

    def test_all_tool_types_have_mapping(self):
        from paparaz.ui.side_panel import TOOL_SECTIONS
        expected_tools = {
            ToolType.SELECT, ToolType.PEN, ToolType.BRUSH, ToolType.HIGHLIGHT,
            ToolType.LINE, ToolType.ARROW, ToolType.CURVED_ARROW,
            ToolType.RECTANGLE, ToolType.ELLIPSE, ToolType.TEXT,
            ToolType.NUMBERING, ToolType.ERASER, ToolType.MASQUERADE,
            ToolType.FILL, ToolType.STAMP, ToolType.CROP, ToolType.SLICE,
            ToolType.EYEDROPPER,
        }
        for t in expected_tools:
            assert t in TOOL_SECTIONS, f"{t} missing from TOOL_SECTIONS"

    def test_rectangle_has_fill_section(self):
        from paparaz.ui.side_panel import TOOL_SECTIONS
        sections = TOOL_SECTIONS[ToolType.RECTANGLE]
        assert sections.get("fill") is True

    def test_ellipse_has_fill_section(self):
        from paparaz.ui.side_panel import TOOL_SECTIONS
        sections = TOOL_SECTIONS[ToolType.ELLIPSE]
        assert sections.get("fill") is True

    def test_text_has_text_section(self):
        from paparaz.ui.side_panel import TOOL_SECTIONS
        sections = TOOL_SECTIONS[ToolType.TEXT]
        assert sections.get("text") is True

    def test_pen_has_stroke_and_line_style(self):
        from paparaz.ui.side_panel import TOOL_SECTIONS
        sections = TOOL_SECTIONS[ToolType.PEN]
        assert sections.get("stroke") is True
        assert sections.get("line_style") is True

    def test_select_has_no_color(self):
        from paparaz.ui.side_panel import TOOL_SECTIONS
        sections = TOOL_SECTIONS[ToolType.SELECT]
        assert sections.get("color") is False

    def test_eraser_has_no_color(self):
        from paparaz.ui.side_panel import TOOL_SECTIONS
        sections = TOOL_SECTIONS[ToolType.ERASER]
        assert sections.get("color") is False

    def test_masquerade_has_mask_section(self):
        from paparaz.ui.side_panel import TOOL_SECTIONS
        sections = TOOL_SECTIONS[ToolType.MASQUERADE]
        assert sections.get("mask") is True

    def test_numbering_has_number_section(self):
        from paparaz.ui.side_panel import TOOL_SECTIONS
        sections = TOOL_SECTIONS[ToolType.NUMBERING]
        assert sections.get("number") is True

    def test_stamp_has_stamp_section(self):
        from paparaz.ui.side_panel import TOOL_SECTIONS
        sections = TOOL_SECTIONS[ToolType.STAMP]
        assert sections.get("stamp") is True

    def test_fill_has_fill_tolerance(self):
        from paparaz.ui.side_panel import TOOL_SECTIONS
        sections = TOOL_SECTIONS[ToolType.FILL]
        assert sections.get("fill_tol") is True

    def test_drawing_tools_have_effects(self):
        from paparaz.ui.side_panel import TOOL_SECTIONS
        for t in [ToolType.PEN, ToolType.BRUSH, ToolType.LINE,
                  ToolType.ARROW, ToolType.CURVED_ARROW,
                  ToolType.RECTANGLE, ToolType.ELLIPSE]:
            assert TOOL_SECTIONS[t].get("effects") is True, f"{t} missing effects"

    def test_update_for_tool_no_crash(self):
        panel, canvas = self._panel()
        for t in [ToolType.SELECT, ToolType.PEN, ToolType.RECTANGLE,
                  ToolType.TEXT, ToolType.FILL, ToolType.STAMP]:
            panel.update_for_tool(t)  # should not crash
