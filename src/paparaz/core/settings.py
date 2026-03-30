"""Settings management for PapaRaZ."""

import json
from pathlib import Path
from dataclasses import dataclass, field, asdict


DEFAULT_CONFIG_DIR = Path.home() / ".paparaz"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "settings.json"


@dataclass
class HotkeySettings:
    capture: str = "PrintScreen"
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
                   "save_counter", "auto_save", "recent_colors"):
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
