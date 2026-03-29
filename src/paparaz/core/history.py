"""Undo/Redo command history using the Command pattern."""

from __future__ import annotations
from typing import Callable, Optional
from PySide6.QtCore import QObject, Signal


class Command:
    """Base command class. Stores a do and undo action."""

    def __init__(self, description: str, do_fn: Callable, undo_fn: Callable):
        self.description = description
        self._do = do_fn
        self._undo = undo_fn

    def execute(self):
        self._do()

    def undo(self):
        self._undo()


class HistoryManager(QObject):
    """Manages undo/redo stacks."""

    history_changed = Signal()

    def __init__(self, max_size: int = 200, parent=None):
        super().__init__(parent)
        self._undo_stack: list[Command] = []
        self._redo_stack: list[Command] = []
        self._max_size = max_size

    def execute(self, command: Command):
        """Execute a command and push it to the undo stack."""
        command.execute()
        self._undo_stack.append(command)
        if len(self._undo_stack) > self._max_size:
            self._undo_stack.pop(0)
        self._redo_stack.clear()
        self.history_changed.emit()

    def undo(self) -> bool:
        if not self._undo_stack:
            return False
        cmd = self._undo_stack.pop()
        cmd.undo()
        self._redo_stack.append(cmd)
        self.history_changed.emit()
        return True

    def redo(self) -> bool:
        if not self._redo_stack:
            return False
        cmd = self._redo_stack.pop()
        cmd.execute()
        self._undo_stack.append(cmd)
        self.history_changed.emit()
        return True

    @property
    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    @property
    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    def clear(self):
        self._undo_stack.clear()
        self._redo_stack.clear()
        self.history_changed.emit()
