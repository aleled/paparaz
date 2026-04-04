"""Settings management for PapaRaZ."""

import json
from pathlib import Path
from dataclasses import dataclass, field, asdict


DEFAULT_CONFIG_DIR = Path.home() / ".paparaz"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "settings.json"


@dataclass
class HotkeySettings:
    capture: str = "PrintScreen"
    capture_fullscreen: str = "Ctrl+PrintScreen"
    capture_window: str = "Alt+PrintScreen"
    capture_repeat: str = "Shift+PrintScreen"
    undo: str = "Ctrl+Z"
    redo: str = "Ctrl+Y"
    save: str = "Ctrl+S"
    save_as: str = "Ctrl+Shift+S"
    copy_clipboard: str = "Ctrl+C"
    select_all: str = "Ctrl+A"
    delete: str = "Delete"


@dataclass
class ToolDefaults:
    foreground_color: str = "#FF0000"
    background_color: str = "#FFFFFF"
    line_width: int = 3
    font_family: str = "Arial"
    font_size: int = 14
    shadow_enabled: bool = False
    shadow_offset: int = 3
    shadow_blur: int = 5
    shadow_color: str = "#80000000"


@dataclass
class AppSettings:
    hotkeys: HotkeySettings = field(default_factory=HotkeySettings)
    tool_defaults: ToolDefaults = field(default_factory=ToolDefaults)
    save_directory: str = ""
    default_format: str = "png"
    jpg_quality: int = 90
    start_on_login: bool = False
    show_tray_notification: bool = True
    theme: str = "dark"
    recent_captures: list = field(default_factory=list)
    max_recent: int = 10
    zoom_presets: list = field(default_factory=lambda: [25, 50, 75, 100, 150, 200, 400])
    # Per-tool property memory: {"PEN": {"foreground_color": "#f00", "line_width": 3, ...}, ...}
    tool_properties: dict = field(default_factory=dict)
    # Last applied theme preset ID ("" = none applied)
    default_theme_preset: str = ""
    app_theme: str = "dark"
    tray_icon_color: str = "#E53935"   # red default
    shadow_default_offset_x: float = 3.0
    shadow_default_offset_y: float = 3.0
    shadow_default_blur_x: float = 5.0
    shadow_default_blur_y: float = 5.0
    auto_check_updates: bool = True
    # File naming
    filename_pattern: str = "{yyyy}-{MM}-{dd}_{HH}-{mm}-{ss}"
    subfolder_pattern: str = ""
    save_counter: int = 1          # persistent auto-increment counter
    auto_save: bool = False        # True = save silently, False = show dialog
    # Recent colors (up to 16, hex strings)
    recent_colors: list = field(default_factory=list)
    # Behavior
    hide_editor_before_capture: bool = True
    confirm_close_unsaved: bool = True
    exit_on_close: bool = False              # True = quit app when last editor closes
    canvas_background: str = "dark"          # "dark" | "checkerboard" | hex color e.g. "#ffffff"
    panel_auto_hide_ms: int = 3000           # ms before panel auto-hides after deselect
    zoom_scroll_factor: float = 1.1          # multiplier per scroll notch (1.05 – 1.3)
    default_panel_mode: str = "auto"         # "auto" | "pinned" | "hidden"
    default_zoom: str = "fit"                # "fit" | "100" | "fill" | "remember"
    last_zoom_level: float = 1.0             # saved when default_zoom == "remember"
    # Capture
    capture_cursor: bool = True              # include mouse cursor in screenshots (as element)
    capture_sound: bool = False              # play shutter sound on capture
    # Output
    png_compression: int = 6                 # 0=fast/large .. 9=slow/small
    auto_copy_on_save: bool = False          # copy to clipboard after every save
    open_after_save: bool = False            # open saved file in default app
    # Auto-save / crash recovery
    auto_save_interval: int = 60             # seconds between auto-save snapshots (0 = disabled)
    crash_recovery: bool = True              # offer to restore on next launch
    # Tool defaults
    highlight_default_color: str = "#FFFF00"
    highlight_default_width: int = 16
    default_stamp_id: str = "check"
    default_blur_pixels: int = 10
    # Window geometry
    window_geometry: str = ""                # saved as "x,y,w,h" or empty
    # Snap
    snap_enabled: bool = True                # master snap toggle
    snap_to_canvas: bool = True              # snap to canvas/image edges & center
    snap_to_elements: bool = True            # snap to other element edges
    snap_threshold: int = 8                  # pixel distance for snapping
    snap_grid_enabled: bool = False          # snap to grid
    snap_grid_size: int = 20                 # grid spacing in pixels
    show_grid: bool = False                  # render grid overlay on canvas


class SettingsManager:
    def __init__(self, config_path: Path = DEFAULT_CONFIG_FILE):
        self._path = config_path
        self.settings = AppSettings()
        self._ensure_config_dir()
        self.load()

    def _ensure_config_dir(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def load(self):
        if self._path.exists():
            try:
                with open(self._path, "r") as f:
                    data = json.load(f)
                self._apply_dict(data)
            except (json.JSONDecodeError, KeyError):
                pass

    def save(self):
        with open(self._path, "w") as f:
            json.dump(asdict(self.settings), f, indent=2)

    def _apply_dict(self, data: dict):
        if "hotkeys" in data:
            for k, v in data["hotkeys"].items():
                if hasattr(self.settings.hotkeys, k):
                    setattr(self.settings.hotkeys, k, v)
        if "tool_defaults" in data:
            for k, v in data["tool_defaults"].items():
                if hasattr(self.settings.tool_defaults, k):
                    setattr(self.settings.tool_defaults, k, v)
        for k in ("save_directory", "default_format", "jpg_quality",
                   "start_on_login", "show_tray_notification", "theme",
                   "recent_captures", "max_recent", "zoom_presets",
                   "default_theme_preset", "app_theme", "tray_icon_color",
                   "shadow_default_offset_x", "shadow_default_offset_y",
                   "shadow_default_blur_x", "shadow_default_blur_y",
                   "auto_check_updates",
                   "filename_pattern", "subfolder_pattern",
                   "save_counter", "auto_save", "recent_colors",
                   "hide_editor_before_capture", "confirm_close_unsaved", "exit_on_close",
                   "canvas_background",
                   "panel_auto_hide_ms", "zoom_scroll_factor",
                   "default_panel_mode", "default_zoom", "last_zoom_level",
                   "capture_cursor", "capture_sound",
                   "png_compression", "auto_copy_on_save", "open_after_save",
                   "auto_save_interval", "crash_recovery",
                   "highlight_default_color", "highlight_default_width",
                   "default_stamp_id", "default_blur_pixels",
                   "window_geometry",
                   "snap_enabled", "snap_to_canvas", "snap_to_elements",
                   "snap_threshold", "snap_grid_enabled", "snap_grid_size",
                   "show_grid"):
            if k in data:
                setattr(self.settings, k, data[k])
        # Backward compatibility: migrate old single blur field to both axes
        if "shadow_default_blur" in data and "shadow_default_blur_x" not in data:
            self.settings.shadow_default_blur_x = float(data["shadow_default_blur"])
            self.settings.shadow_default_blur_y = float(data["shadow_default_blur"])
        if "tool_properties" in data and isinstance(data["tool_properties"], dict):
            self.settings.tool_properties = data["tool_properties"]

    def add_recent(self, path: str):
        if path in self.settings.recent_captures:
            self.settings.recent_captures.remove(path)
        self.settings.recent_captures.insert(0, path)
        self.settings.recent_captures = self.settings.recent_captures[:self.settings.max_recent]
        self.save()
