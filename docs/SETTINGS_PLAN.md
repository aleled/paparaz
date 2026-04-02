# Settings Dialog — Overhaul Plan

**Status**: Most items implemented in v0.9.6–0.9.7
**Last updated**: 2026-04-02
**Scope**: Audit of all configurable behaviors vs. what is actually exposed in the settings UI.

---

## Current State Assessment

The settings dialog has 7 pages: Capture, Appearance, Tools, Shortcuts, Presets, Updates, About.

### Problems with the current dialog
1. **Shadow blur** — `settings.py` stores `shadow_default_blur_x` and `shadow_default_blur_y` separately, but the dialog only shows a single "Blur radius" spinbox — the Y axis is never saved
2. **Font family** — rendered as a plain `QLineEdit` instead of a `QFontComboBox` (the side panel already uses a font combo)
3. **Shortcuts page** — `select_all` hotkey is in `settings.py` but not shown in the configurable section
4. **Tools page** — QGroupBox cards too tall/bulky for the content they contain; default shadow settings use `shadow_default_blur` (old field) instead of the current X/Y fields
5. **Missing "Behavior" page** — dozens of timing, window, and interaction settings are hardcoded with no user control
6. **Recent colors** — stored in settings but no way to view or clear them from the UI
7. **Max recent captures** (`max_recent = 10`) — stored in settings but not configurable in UI
8. **Zoom presets** — stored in settings but not configurable in UI

---

## What's Missing: Full Audit

### A — Items in `settings.py` but NOT shown in the UI

| Field | Type | Where to add |
|-------|------|--------------|
| `max_recent` | int (default 10) | Capture page → Capture Behavior |
| `zoom_presets` | list | Behavior page (new) |
| `shadow_default_blur_x` / `_y` | float | Tools page (fix: replace single slider with two) |
| `select_all` hotkey | str | Shortcuts page → Global section |
| `recent_colors` | list | Appearance page → "Recent Colors" section with Clear button |

### B — Hardcoded values not in `settings.py` at all

#### Behavior (new settings + new Behavior page)
| What | Hardcoded value | Proposed setting |
|------|-----------------|-----------------|
| Panel auto-hide delay | `3000` ms | Slider 1–10 s |
| Zoom scroll factor | `1.1` / `0.9` | Slider 1.05–1.3 |
| Paste / duplicate offset | `20` px | Spinbox |
| Tray notification timeout | `3000` ms | Slider 1–10 s |
| Tray double-click action | capture (fixed) | Dropdown: Capture / Open last / Show menu |
| Window behavior after save | ask (fixed) | Dropdown: Always ask / Close / Stay open |
| Update check delay on startup | `3000` ms | Not user-relevant, keep hardcoded |

#### Tools
| What | Hardcoded value | Proposed setting |
|------|-----------------|-----------------|
| Highlight default color | `#FFFF00` | Color swatch in Tools defaults |
| Highlight default width | `16` px | Slider in Tools defaults |
| Arrow head size | `max(12, line_width * 4)` | Slider: Small / Medium / Large |
| Default stamp | `"check"` | Stamp picker preview |
| Default blur pixel size | `10` | Slider in Tools defaults |
| Eyedropper loupe zoom | `10×` | Dropdown: 5× / 10× / 15× |

#### Appearance
| What | Hardcoded value | Proposed setting |
|------|-----------------|-----------------|
| Side panel width | `186` px | Not needed — panel is compact by design |
| Selection handle size | `7` px | Slider 4–14 px (Appearance page) |

---

## Proposed New Structure

### Pages (8 → 9)

```
Capture        — save path, format, filename, delay, auto-save, max recent
Appearance     — theme cards, tray color, preset, recent colors (+ clear), handle size
Tools          — default colors, line width, font (combo), highlight defaults,
                  arrow head size, stamp default, shadow defaults (blur X+Y), tool memory
Behavior  [NEW] — panel auto-hide delay, zoom scroll speed, paste offset,
                  tray double-click, save behavior, window cascade
Shortcuts      — global hotkeys (+ select_all), editor fixed shortcuts reference
Presets        — style preset gallery (read-only)
Updates        — version, auto-check, start on login
About          — version, tech stack, license
```

---

## Implementation Tasks

### Priority 1 — Bug Fixes (settings already broken)
- [x] **Fix shadow blur** — replace single spinbox with two `_slider_row` widgets for blur_x and blur_y
- [x] **Fix font family** — replace `QLineEdit` with `QFontComboBox`
- [x] **Fix shadow save path** — `_save_and_close` writes `shadow_default_blur` not `blur_x/blur_y`
- [x] **Add select_all hotkey** to Shortcuts page configurable section

### Priority 2 — New Behavior Page
- [x] Add `AppSettings` fields: `panel_auto_hide_ms`, `zoom_scroll_factor`
- [x] Wire `panel_auto_hide_ms` into `side_panel.py` `AUTO_HIDE_DELAY_MS`
- [x] Wire `zoom_scroll_factor` into `canvas.py` scroll handler
- [x] Wire `hide_editor_before_capture` into `app.py` capture flow
- [x] Wire `confirm_close_unsaved` into `editor.py` `_confirm_close`
- [x] Build `_build_behavior()` page in settings dialog (with canvas background, panel auto-hide, zoom speed)
- [ ] Add `paste_offset`, `tray_notification_ms`, `tray_dbl_click_action`, `save_behavior` fields

### Priority 3 — Tools Page Improvements
- [x] Add `highlight_default_color` and `highlight_default_width` to `AppSettings`
- [x] Wire highlight defaults into `HighlightTool.on_activate()`
- [ ] Add `arrow_head_size` preference (small/medium/large) — stored as multiplier
- [x] Add `default_stamp_id` to `AppSettings`; wire into `StampTool`
- [x] Add `default_blur_pixels` to `AppSettings`; wire into `MasqueradeTool`
- [x] Add specialized tool defaults section in settings dialog (highlight color/width, blur pixels, default stamp)

### Priority 4 — Appearance Page
- [x] Show `recent_colors` list in Appearance page with "Clear all" button
- [x] Add `max_recent` spinbox to Capture page → Capture Behavior section
- [ ] Add selection handle size slider (visual preference, stored in `AppSettings`)

### Priority 5 — Layout & Polish
- [ ] Reduce QGroupBox card padding — currently `padding: 16px 14px` is too generous
- [x] Convert font family `QLineEdit` → `QFontComboBox`
- [ ] Add tooltips to every settings control
- [ ] Use 2-column grid for Tool Defaults section (colors side by side, not stacked)

### Priority 6 — Window Geometry
- [x] Save editor window geometry on close
- [x] Restore saved geometry when opening first editor window

---

## New `AppSettings` Fields Needed

```python
# Behavior
panel_auto_hide_ms: int = 3000
zoom_scroll_factor: float = 1.1
paste_offset: int = 20
tray_notification_ms: int = 3000
tray_dbl_click_action: str = "capture"   # "capture" | "last" | "menu"
save_behavior: str = "ask"               # "ask" | "close" | "stay"
hide_editor_before_capture: bool = True  # hide editor window when triggering a new capture
confirm_close_unsaved: bool = True       # warn before closing an annotation with unsaved changes
exit_on_editor_close: bool = False       # quit app entirely when editor is closed
remember_window_geometry: bool = True    # restore last editor position + size

# Capture
capture_fullscreen_hotkey: str = ""      # dedicated full-screen capture shortcut
capture_active_window_hotkey: str = ""   # capture window under cursor (no region drag)
capture_fixed_region_hotkey: str = ""    # re-capture last used region rectangle
repeat_last_capture_hotkey: str = ""     # shortcut to repeat the previous capture type
include_mouse_cursor: bool = False       # embed mouse pointer in the captured image
max_recent: int = 10                     # already in settings.py — just needs UI

# Output
png_compression: int = 6                # 0=fast/large .. 9=slow/small
auto_copy_after_save: bool = False       # silently copy to clipboard after every save
open_in_external_after_save: str = ""   # path to external app, "" = disabled
play_capture_sound: bool = False         # auditory shutter feedback on capture

# Editor
default_zoom: str = "fit"               # "fit" | "100" | "fill" | "last"
starting_panel_mode: str = "auto"       # "auto" | "pinned" | "hidden"
canvas_background: str = "dark"         # "dark" | "system" | "checkerboard" | hex color

# Tools
highlight_default_color: str = "#FFFF00"
highlight_default_width: int = 16
arrow_head_size: str = "medium"          # "small" | "medium" | "large"
default_stamp_id: str = "check"
default_blur_pixels: int = 10

# Appearance
selection_handle_size: int = 7           # px, 4–14
```

---

## PicPick-Inspired UI Patterns to Adopt

### File Name page — Live Preview (priority: HIGH)
PicPick renders the actual filename below the pattern field in accent color. Our `FilenamePatternWidget`
should show a live preview line updated on every keypress — e.g. `2026-04-01_08-24-55.png`

### Editor / Behavior page (priority: HIGH)
PicPick's "Editor" page groups boolean behaviors as indented checkboxes under a header.
For PapaRaZ, consolidate into a **Behavior** page with toggle pills:
- "Hide editor window before capturing a new screenshot"
- "Ask before closing with unsaved changes"
- "Exit app entirely when closing the editor"
- "Remember editor window position and size"

### Hotkeys — Modifier checkboxes + key dropdown (priority: MEDIUM)
PicPick shows each action as:  `[□ Shift] [□ Ctrl] [□ Alt]  [Key dropdown▼]`
More discoverable than the current freeform text input. Rebuild Shortcuts page
as a table widget with per-row modifier checkboxes + QComboBox key selector.

### Multiple capture mode hotkeys (priority: MEDIUM)
PicPick gives each capture mode its own hotkey entry:
- Capture Full-screen (instant, no overlay)
- Capture Active Window (window under cursor)
- Capture Fixed Region (last-used rectangle)
- Repeat Last Capture (same mode + parameters)
PapaRaZ currently has only one global PrintScreen hotkey for region capture.

### About page — Action buttons (priority: LOW)
Add Website / Check for Updates / Report Issue buttons to the About page
(currently only shows version text).

---

## Files to Modify

| File | Change |
|------|--------|
| `core/settings.py` | Add new fields listed above |
| `ui/settings_dialog.py` | Fix broken controls, add Behavior page, expand Tools/Appearance |
| `ui/side_panel.py` | Read `panel_auto_hide_ms` from settings instead of hardcoded |
| `ui/canvas.py` | Read `zoom_scroll_factor` from settings |
| `ui/editor.py` | Read `save_behavior` from settings, wire `selection_handle_size` |
| `tools/drawing.py` | Read `highlight_default_color/width`, `arrow_head_size` |
| `tools/special.py` | Read `default_stamp_id`, `default_blur_pixels` |
| `core/elements.py` | Read `selection_handle_size` from settings (or inject via `set_selection_accent`) |
