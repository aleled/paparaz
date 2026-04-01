"""Snap engine — snaps element edges/centers to canvas edges, other elements, and grid.

Usage:
    engine = SnapEngine(canvas_rect, elements, snap_distance=8)
    snapped_pos, guides = engine.snap_move(elem, proposed_pos)
    snapped_rect, guides = engine.snap_resize(elem, proposed_rect, handle_index)

Returns the adjusted position/rect plus a list of SnapGuide objects for rendering.
"""

from __future__ import annotations

from dataclasses import dataclass
from PySide6.QtCore import QPointF, QRectF


@dataclass
class SnapGuide:
    """A visual guide line to render on the canvas."""
    orientation: str   # "h" (horizontal) or "v" (vertical)
    value: float       # the y-coordinate (for "h") or x-coordinate (for "v")
    start: float       # extent start (perpendicular axis)
    end: float         # extent end (perpendicular axis)


def _rect_edges(r: QRectF) -> dict[str, float]:
    """Extract snap-relevant positions from a rect."""
    return {
        "left": r.left(),
        "right": r.right(),
        "top": r.top(),
        "bottom": r.bottom(),
        "cx": r.center().x(),
        "cy": r.center().y(),
    }


def snap_move(
    elem_rect: QRectF,
    canvas_rect: QRectF,
    other_rects: list[QRectF],
    threshold: float = 8.0,
    snap_to_canvas: bool = True,
    snap_to_elements: bool = True,
    grid_size: int = 0,
) -> tuple[QPointF, list[SnapGuide]]:
    """Snap an element's bounding rect during a move.

    Args:
        elem_rect: The element's current bounding rect (proposed position).
        canvas_rect: The canvas/background bounding rect.
        other_rects: Bounding rects of other (non-selected) elements.
        threshold: Max pixel distance for snapping.
        snap_to_canvas: Whether to snap to canvas edges/center.
        snap_to_elements: Whether to snap to other element edges/center.
        grid_size: Grid spacing (0 = disabled).

    Returns:
        (offset, guides) — offset to apply to the element position, and guide lines.
    """
    guides: list[SnapGuide] = []
    dx = 0.0
    dy = 0.0

    e = _rect_edges(elem_rect)
    canvas_e = _rect_edges(canvas_rect)

    # Collect all reference lines
    v_refs: list[float] = []   # vertical reference lines (x values)
    h_refs: list[float] = []   # horizontal reference lines (y values)

    if snap_to_canvas:
        v_refs.extend([canvas_e["left"], canvas_e["right"], canvas_e["cx"]])
        h_refs.extend([canvas_e["top"], canvas_e["bottom"], canvas_e["cy"]])

    if snap_to_elements:
        for r in other_rects:
            oe = _rect_edges(r)
            v_refs.extend([oe["left"], oe["right"], oe["cx"]])
            h_refs.extend([oe["top"], oe["bottom"], oe["cy"]])

    # Snap to grid
    if grid_size > 0:
        # Add grid lines near the element edges
        for edge_val in [e["left"], e["right"], e["cx"]]:
            nearest = round(edge_val / grid_size) * grid_size
            v_refs.append(nearest)
        for edge_val in [e["top"], e["bottom"], e["cy"]]:
            nearest = round(edge_val / grid_size) * grid_size
            h_refs.append(nearest)

    # Find best vertical snap (x-axis)
    best_vdist = threshold + 1
    best_vsnap = 0.0
    best_vref = 0.0
    best_vedge = ""
    elem_v_edges = {"left": e["left"], "right": e["right"], "cx": e["cx"]}

    for ref in v_refs:
        for edge_name, edge_val in elem_v_edges.items():
            dist = abs(edge_val - ref)
            if dist < best_vdist:
                best_vdist = dist
                best_vsnap = ref - edge_val
                best_vref = ref
                best_vedge = edge_name

    if best_vdist <= threshold:
        dx = best_vsnap
        # Build guide line extent
        min_y = min(e["top"] + dy, canvas_e["top"])
        max_y = max(e["bottom"] + dy, canvas_e["bottom"])
        # Include the reference element bounds in the guide extent
        for r in other_rects:
            if abs(_rect_edges(r)["left"] - best_vref) < 1 or \
               abs(_rect_edges(r)["right"] - best_vref) < 1 or \
               abs(_rect_edges(r)["cx"] - best_vref) < 1:
                min_y = min(min_y, r.top())
                max_y = max(max_y, r.bottom())
        guides.append(SnapGuide("v", best_vref, min_y, max_y))

    # Find best horizontal snap (y-axis)
    best_hdist = threshold + 1
    best_hsnap = 0.0
    best_href = 0.0
    best_hedge = ""
    elem_h_edges = {"top": e["top"], "bottom": e["bottom"], "cy": e["cy"]}

    for ref in h_refs:
        for edge_name, edge_val in elem_h_edges.items():
            dist = abs(edge_val - ref)
            if dist < best_hdist:
                best_hdist = dist
                best_hsnap = ref - edge_val
                best_href = ref
                best_hedge = edge_name

    if best_hdist <= threshold:
        dy = best_hsnap
        min_x = min(e["left"] + dx, canvas_e["left"])
        max_x = max(e["right"] + dx, canvas_e["right"])
        for r in other_rects:
            if abs(_rect_edges(r)["top"] - best_href) < 1 or \
               abs(_rect_edges(r)["bottom"] - best_href) < 1 or \
               abs(_rect_edges(r)["cy"] - best_href) < 1:
                min_x = min(min_x, r.left())
                max_x = max(max_x, r.right())
        guides.append(SnapGuide("h", best_href, min_x, max_x))

    return QPointF(dx, dy), guides


def snap_point(
    point: QPointF,
    canvas_rect: QRectF,
    other_rects: list[QRectF],
    threshold: float = 8.0,
    snap_to_canvas: bool = True,
    snap_to_elements: bool = True,
    grid_size: int = 0,
) -> tuple[QPointF, list[SnapGuide]]:
    """Snap a single point (e.g., resize handle) to reference lines.

    Returns (snapped_point, guides).
    """
    guides: list[SnapGuide] = []
    px, py = point.x(), point.y()
    canvas_e = _rect_edges(canvas_rect)

    v_refs: list[float] = []
    h_refs: list[float] = []

    if snap_to_canvas:
        v_refs.extend([canvas_e["left"], canvas_e["right"], canvas_e["cx"]])
        h_refs.extend([canvas_e["top"], canvas_e["bottom"], canvas_e["cy"]])

    if snap_to_elements:
        for r in other_rects:
            oe = _rect_edges(r)
            v_refs.extend([oe["left"], oe["right"]])
            h_refs.extend([oe["top"], oe["bottom"]])

    if grid_size > 0:
        v_refs.append(round(px / grid_size) * grid_size)
        h_refs.append(round(py / grid_size) * grid_size)

    # Snap X
    best_vdist = threshold + 1
    snapped_x = px
    for ref in v_refs:
        dist = abs(px - ref)
        if dist < best_vdist:
            best_vdist = dist
            snapped_x = ref

    if best_vdist <= threshold:
        guides.append(SnapGuide("v", snapped_x, py - 20, py + 20))

    # Snap Y
    best_hdist = threshold + 1
    snapped_y = py
    for ref in h_refs:
        dist = abs(py - ref)
        if dist < best_hdist:
            best_hdist = dist
            snapped_y = ref

    if best_hdist <= threshold:
        guides.append(SnapGuide("h", snapped_y, px - 20, px + 20))

    return QPointF(snapped_x, snapped_y), guides
