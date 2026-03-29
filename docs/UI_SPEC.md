# PapaRaZ - UI Specification

## Design Philosophy
- **Minimal**: Tools appear when needed, disappear when not
- **Fast**: Sub-second capture to edit, no loading screens
- **Familiar**: Flameshot users feel at home
- **Discoverable**: Hover previews show what tools will do before clicking

## Color Scheme (Flameshot-inspired)

| Element | Color | Hex |
|---------|-------|-----|
| UI accent (buttons, selection) | Purple | `#740096` |
| Active tool button | Dark purple | `#270032` |
| Window background | Near black | `#0d0d1a` |
| Panel background | Dark blue-gray | `#1a1a2e` |
| Overlay (region selector) | Black 75% | `rgba(0,0,0,190)` |
| Selection handles | Purple circles | `#740096` |
| Selection border | Purple 2px | `#740096` |
| Edit mode banner | Purple pill | `#740096` |
| Dimension badge | Dark pill | `rgba(0,0,0,200)` |

## System Tray
- Icon: Red rounded square with "Pz" text
- Double-click: Trigger capture
- Right-click menu: Capture Screen, Open Image..., Settings, Quit

## Region Selector Overlay
- Full-screen dark veil (75% black) across all monitors
- **Selection hole**: Clear interior showing undimmed screenshot
- Purple 1px border on selection
- 8 purple circular handles (corners + midpoints)
- Dimension label (`W × H`) in purple pill below selection
- Coordinate readout near cursor before selection
- Right-click or Escape to cancel
- Enter to confirm

## Editor Window Layout
```
+-------------------------------------------------------+
|              Toolbar (centered, circular buttons)       |
+----------+--------------------------------------------+
|          |                                             |
|  Side    |             Canvas                          |
|  Panel   |          (scrollable, zoomable)             |
|  (250px) |                                             |
|          |                                             |
+----------+--------------------------------------------+
|  Tool | Hint text                    | Position | Zoom |
+-------------------------------------------------------+
```

## Toolbar (Flameshot-style)
- Horizontal row of circular buttons (40px diameter)
- White Material Design SVG icons (24px, 60% of button)
- Purple background (`#740096`), checked state dark purple (`#270032`)
- Drop shadow: blur=5, offset=0, black
- Gap between buttons: 10px (buttonSize/4)
- **Tool buttons**: Select, Pen, Brush, Line, Arrow, Rect, Ellipse, Text, Number, Eraser, Blur, Fill
- **Action buttons** (after separator): Undo, Redo, Save, Copy, Paste, Close

## Side Panel (250px, left)
- Scrollable with dark background
- **Edit mode banner**: Purple "Editing selected element" when element selected
- **COLOR section**: Foreground + Background swatches (always visible)
- **Per-tool sections** (auto-show/hide):
  - STROKE: Width slider (1-50) + spinbox
  - LINE STYLE: Dash pattern, Cap style, Join style dropdowns
  - FILL: Filled shape checkbox
  - TEXT: Font family, size, bold/italic/underline/strikethrough, alignment (L/C/R), direction (LTR/RTL), text background toggle + color
  - MARKER: Circle size, font family, text color
  - PIXELATE: Pixel size slider (2-50)
  - EFFECTS: Opacity slider, Shadow toggle + color + offset X/Y + blur

## Selection Visuals
- **Selected element**: Purple tinted overlay + 2px purple border + white inner border
- **8 circular handles**: 12px diameter, purple fill, white 2px outline
- **Dimension badge**: Black rounded pill showing `W×H (X,Y)` below element
- **Hover (Select tool)**: Dotted purple outline on non-selected hovered elements

## Tool Hover Previews
| Tool | Preview |
|------|---------|
| Text | Ghost dashed text box at cursor + "T" label |
| Numbering | Ghost circle at cursor showing next number |
| Eraser | Red highlight + X icon on target element |
| Fill | Color-tinted highlight on target shape |
| Masquerade | Crosshair at cursor |
| Select | Dotted outline on hovered element |

## Text Editing
- **Before click**: Ghost text box at cursor position
- **After click**: Purple dashed border around text area + light tint
- **Placeholder**: "Type here..." in gray when empty
- **Cursor**: 2px foreground-color line at end of text
- **Multi-line**: Enter for newline, Ctrl+Enter to finalize
- **Double-click**: Re-enter editing mode on existing text element

## Status Bar
- Current tool name
- Hint text (e.g., "Ctrl+Enter to finalize text | Middle-click to pan")
- Cursor position (X, Y)
- Zoom level (%)
