# PapaRaZ - Tools Specification

## Tool Behavior Matrix

| Tool | Click | Drag | Shift | Hover Preview | Element Type |
|------|-------|------|-------|---------------|--------------|
| Select | Pick element | Move element | - | Dotted outline on hovered | - |
| Select | Double-click text | - | - | - | Re-edit TextElement |
| Pen | Dot | Freehand path | - | - | PenElement |
| Brush | Dot (soft) | Soft stroke | - | - | BrushElement |
| Line | - | Line start->end | Snap 45deg | - | LineElement |
| Arrow | - | Arrow start->end | Snap 45deg | - | ArrowElement |
| Rectangle | - | Rect corner->corner | Square | - | RectElement |
| Ellipse | - | Ellipse bounds | Circle | - | EllipseElement |
| Text | Place text area | - | - | Ghost text box | TextElement |
| Numbering | Place marker | - | - | Ghost circle + number | NumberElement |
| Fill | Fill shape | - | - | Color tint on target | (modifies target) |
| Eraser | Delete element | - | - | Red highlight + X | (deletes target) |
| Masquerade | - | Blur region | - | Crosshair | MaskElement |

## Element Properties (ElementStyle)

All elements share via `ElementStyle`:

| Property | Type | Default | Used By |
|----------|------|---------|---------|
| `foreground_color` | str (hex) | `#FF0000` | All |
| `background_color` | str (hex) | `#FFFFFF` | Rect/Ellipse fill, Fill tool |
| `line_width` | float | 3.0 | Pen, Brush, Line, Arrow, Rect, Ellipse |
| `opacity` | float (0-1) | 1.0 | All |
| `cap_style` | str | `round` | Pen, Line, Arrow, Rect, Ellipse |
| `join_style` | str | `round` | Pen, Line, Arrow, Rect, Ellipse |
| `dash_pattern` | str | `solid` | Pen, Line, Arrow, Rect, Ellipse |
| `font_family` | str | `Arial` | Text, Number |
| `font_size` | int | 14 | Text |

### Shadow (sub-object of ElementStyle)

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `enabled` | bool | False | Toggle shadow on/off |
| `color` | str (hex+alpha) | `#80000000` | Shadow color with alpha |
| `offset_x` | float | 3.0 | Horizontal offset (-30 to +30) |
| `offset_y` | float | 3.0 | Vertical offset (-30 to +30) |
| `blur_radius` | float | 5.0 | Blur amount (0-30) |

Shadow is painted on ALL drawing elements via `_paint_shadow()` base method.

### TextElement Extra Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `bold` | bool | False | Bold text |
| `italic` | bool | False | Italic text |
| `underline` | bool | False | Underlined text |
| `strikethrough` | bool | False | Strikethrough text |
| `alignment` | Qt.AlignmentFlag | AlignLeft | Left, Center, Right |
| `direction` | Qt.LayoutDirection | LeftToRight | LTR or RTL |
| `bg_enabled` | bool | False | Show text background |
| `bg_color` | str (hex) | `#FFFF00` | Text background color |

### NumberElement Extra Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `size` | float | 28.0 | Circle diameter (independent from font) |
| `text_color` | str | `""` (auto) | Number text color. Empty = auto-contrast |
| `number` | int | auto-increment | The displayed number |

### MaskElement Extra Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `pixel_size` | int | 10 | Pixelation block size (2-50) |

### RectElement / EllipseElement Extra Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `filled` | bool | False | Fill with background_color |

## Side Panel Sections Per Tool

| Section | SELECT | PEN | BRUSH | LINE | ARROW | RECT | ELLIPSE | TEXT | NUMBER | ERASER | MASK | FILL |
|---------|--------|-----|-------|------|-------|------|---------|------|--------|--------|------|------|
| Color (fg/bg) | Always visible | | | | | | | | | | | |
| Stroke | - | Y | Y | Y | Y | Y | Y | - | - | - | - | - |
| Line Style | - | Y | - | Y | Y | Y | Y | - | - | - | - | - |
| Fill | - | - | - | - | - | Y | Y | - | - | - | - | - |
| Text | - | - | - | - | - | - | - | Y | - | - | - | - |
| Marker | - | - | - | - | - | - | - | - | Y | - | - | - |
| Pixelate | - | - | - | - | - | - | - | - | - | - | Y | - |
| Effects | Y | Y | Y | Y | Y | Y | Y | Y | Y | - | Y | - |

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Capture screen | PrintScreen |
| Undo | Ctrl+Z |
| Redo | Ctrl+Y / Ctrl+Shift+Z |
| Save | Ctrl+S |
| Save As | Ctrl+Shift+S |
| Copy to clipboard | Ctrl+C |
| Paste from clipboard | Ctrl+V |
| Delete selected | Delete |
| Pen tool | P |
| Brush tool | B |
| Line tool | L |
| Arrow tool | A |
| Rectangle tool | R |
| Ellipse tool | E |
| Text tool | T |
| Numbering tool | N |
| Eraser tool | X |
| Masquerade tool | M |
| Select tool | V / Escape |
| Zoom in | Ctrl+= |
| Zoom out | Ctrl+- |
| Zoom reset | Ctrl+0 |
| Finalize text | Ctrl+Enter |
| Pan canvas | Middle-click drag |

## Zoom Levels

Predefined: 25%, 50%, 75%, 100%, 150%, 200%, 400%
Custom: User can type any value in the toolbar combo box.
Ctrl+Scroll: Continuous zoom at cursor position.
