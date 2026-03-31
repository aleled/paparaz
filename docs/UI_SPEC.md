# PapaRaZ - UI Specification

## Design Philosophy
- **Minimal**: Tools appear when needed, disappear when not
- **Fast**: Sub-second capture to edit, no loading screens
- **Familiar**: Users feel at home
- **Discoverable**: Hover previews show what tools will do before clicking

## Color Scheme (Default Dark Theme)

| Element | Color | Hex |
|---------|-------|-----|
| UI accent (buttons, selection) | Purple | `#740096` |
| Active tool button | Dark purple | `#270032` |
| Window background | Near black | `#0d0d1a` |
| Panel background | Dark blue-gray | `#1a1a2e` |
| Overlay (region selector) | Black 75% | `rgba(0,0,0,190)` |
| Selection handles | Small white squares, accent border | theme accent |
| Selection border | 1px, no fill | theme accent |
| Edit mode banner | Purple pill | `#740096` |
| Dimension badge | Dark pill | `rgba(0,0,0,200)` |

**5 built-in themes**: Dark (default), Midnight Blue, Ocean, Forest, Warm Dark — all selection and tool visuals adapt to the chosen accent color.

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

## Toolbar
- Horizontal row of circular buttons (40px diameter)
- White Material Design SVG icons (24px, 60% of button)
- Purple background (`#740096`), checked state dark purple (`#270032`)
- Drop shadow: blur=5, offset=0, black
- Gap between buttons: 10px (buttonSize/4)
- **Tool buttons**: Select, Pen, Brush, Line, Arrow, Rect, Ellipse, Text, Number, Eraser, Blur, Fill
- **Action buttons** (after separator): Undo, Redo, Save, Copy, Paste, Close

## Side Panel (260px, floating)
- Free-floating top-level window; draggable via header grip
- **Three modes**: auto (shows on element select, hides 3 s after deselect), pinned (always visible), hidden (grip tab on canvas edge to restore)
- **Header bar** (40 px):
  - `⠿` drag grip with `SizeAllCursor`
  - **Title**: "Properties" at rest; updates to element type name when element selected ("Text", "Rectangle", "Arrow", etc.)
  - **📌 Pin** toggle (40 × 28 px): checked = pinned, unchecked = auto-hide
  - **✕ Close** (28 × 28 px): hides panel, sets hidden mode
- **Element preview strip** (80 px): scaled `paint()` render of the selected element; "No selection" placeholder when empty
- **Edit mode banner**: Purple "Editing selected element" when element selected
- **COLOR section**: Foreground + Background swatches; labeled **RECENT COLORS** palette below with left/right-click tooltip
- **Per-tool sections** (auto-show/hide):
  - STROKE: Width slider (0–50 px); 0 px = borderless fill
  - LINE STYLE: Dash pattern; Cap (stacked row); Join (stacked row)
  - FILL: "Filled shape" toggle button (labeled)
  - TEXT: Font family, size (6–120 pt), **B/I/U/S̶** labeled toggle buttons, `≡←/≡/≡→` alignment, LTR/RTL direction, Bg + Outline toggles with dependent swatches
  - MARKER: Circle size, font family, text color
  - PIXELATE: Pixel size slider (2–50)
  - EFFECTS: Opacity slider, Shadow toggle + color + offset X/Y + linked Blur slider (≠ unlink for independent Blur X/Y)
- All toggle controls are `QToolButton` (checkable, labeled) — no checkboxes

## Selection Visuals
- **Selected element**: Thin 1px accent-color border only — **no fill overlay** (fully transparent)
- **8 square handles**: 7px, white fill, 1px accent-color border
- **Rotation handle**: Small circle above element, connected by dotted line
- **Dimension badge**: Black rounded pill showing `W×H (X,Y)` below element
- **Hover (Select tool)**: Dotted accent-color outline on non-selected hovered elements
- **Theme-aware**: All selection visuals use the current app theme accent color, updated live on theme change
- **Precision movement**: Arrow keys move selected element(s) 1 px; Shift+arrow moves 10 px (undoable)

## Tool Hover Previews
| Tool | Preview |
|------|---------|
| Text | Ghost dashed text box at cursor + "Aa" label in current font/color/style |
| Numbering | Ghost circle at cursor showing next number |
| Eraser | Accent-color circle + X icon on target element (theme-aware) |
| Fill | Color-tinted highlight on target shape |
| Masquerade | Crosshair at cursor |
| Select | Dotted outline on hovered element |
| Eyedropper | 80 px magnifying loupe (10× zoom), hex label beneath |

## Text Editing
- **Before click**: Ghost text box at cursor position
- **After click**: Purple dashed border around text area + light tint
- **Placeholder**: "Type here..." in gray when empty
- **Cursor**: 2px foreground-color line; click inside text to reposition cursor to exact character
- **Multi-line**: Enter for newline, Ctrl+Enter to finalize
- **Double-click**: Re-enter editing mode on existing text element
- **Resize handle**: Purple 3-line grip on right edge; drag horizontally to change box width
- **Navigation**: Up/Down arrows move across visual lines (x-hint preserved); Ctrl+Left/Right jumps word boundaries; Home/End go to visual line start/end; Ctrl+Home/End jump to document start/end
- **Font size**: 6–120 pt

## Status Bar
- Current tool name
- Hint text (e.g., "Ctrl+Enter to finalize text | Middle-click to pan")
- Cursor position (X, Y)
- Zoom level (%)
