# Settings Dialog — Overhaul Plan

**Status**: Planning
**Last updated**: 2026-03-31
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
- [ ] **Fix shadow blur** — replace single spinbox with two `_slider_row` widgets for blur_x and blur_y
- [ ] **Fix font family** — replace `QLineEdit` with `QFontComboBox`
- [ ] **Fix shadow save path** — `_save_and_close` writes `shadow_default_blur` not `blur_x/blur_y`
- [ ] **Add select_all hotkey** to Shortcuts page configurable section

### Priority 2 — New Behavior Page
- [ ] Add `AppSettings` fields: `panel_auto_hide_ms`, `zoom_scroll_factor`, `paste_offset`, `tray_notification_ms`, `tray_dbl_click_action`, `save_behavior`
- [ ] Wire `panel_auto_hide_ms` into `side_panel.py` `AUTO_HIDE_DELAY_MS`
- [ ] Wire `zoom_scroll_factor` into `canvas.py` scroll handler
- [ ] Wire `save_behavior` into `editor.py` `_confirm_close`
- [ ] Build `_build_behavior()` page in settings dialog

### Priority 3 — Tools Page Improvements
- [ ] Add `highlight_default_color` and `highlight_default_width` to `AppSettings` + `ToolDefaults`
- [ ] Wire highlight defaults into `HighlightTool.on_activate()`
- [ ] Add `arrow_head_size` preference (small/medium/large) — stored as multiplier
- [ ] Add `default_stamp_id` to `AppSettings`; wire into `StampTool`
- [ ] Add `default_blur_pixels` to `AppSettings`; wire into `MasqueradeTool`

### Priority 4 — Appearance Page
- [ ] Show `recent_colors` list in Appearance page with individual remove + "Clear all" button
- [ ] Add `max_recent` spinbox to Capture page → Capture Behavior section
- [ ] Add selection handle size slider (visual preference, stored in `AppSettings`)

### Priority 5 — Layout & Polish
- [ ] Reduce QGroupBox card padding — currently `padding: 16px 14px` is too generous
- [ ] Convert font family `QLineEdit` → `QFontComboBox`
- [ ] Add tooltips to every settings control
- [ ] Use 2-column grid for Tool Defaults section (colors side by side, not stacked)

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

# Tools
highlight_default_color: str = "#FFFF00"
highlight_default_width: int = 16
arrow_head_size: str = "medium"          # "small" | "medium" | "large"
default_stamp_id: str = "check"
default_blur_pixels: int = 10

# Appearance
selection_handle_size: int = 7           # px, 4–14

# Capture
max_recent: int = 10                     # already in settings.py — just needs UI
```

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
