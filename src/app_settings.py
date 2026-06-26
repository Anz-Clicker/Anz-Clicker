from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any


@dataclass
class AppSettings:
    mouse_animation_speed: int = 5
    enhanced_humanlike_mouse: bool = False
    mouse_click_delay_min_ms: int = 55
    mouse_click_delay_max_ms: int = 135
    key_press_delay_min_ms: int = 80
    key_press_delay_max_ms: int = 160
    default_script_folder: str = "scripts"
    dark_mode: bool = True
    remember_window_geometry: bool = True
    window_geometry: str = ""
    start_keybind: str = "F6"
    pause_keybind: str = "F8"

    @classmethod
    def load(cls, path: Path) -> "AppSettings":
        if not path.exists():
            return cls()
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return cls()
        return cls.from_dict(payload)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AppSettings":
        defaults = cls()
        values = asdict(defaults)
        values.update({key: payload.get(key, value) for key, value in values.items()})
        settings = cls(**values)
        settings.normalize()
        return settings

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    def normalize(self) -> None:
        self.mouse_animation_speed = _clamp_int(self.mouse_animation_speed, 1, 10)
        self.enhanced_humanlike_mouse = bool(self.enhanced_humanlike_mouse)
        self.mouse_click_delay_min_ms = max(0, int(self.mouse_click_delay_min_ms))
        self.mouse_click_delay_max_ms = max(0, int(self.mouse_click_delay_max_ms))
        self.key_press_delay_min_ms = max(0, int(self.key_press_delay_min_ms))
        self.key_press_delay_max_ms = max(0, int(self.key_press_delay_max_ms))
        self.default_script_folder = str(self.default_script_folder or "scripts")
        self.dark_mode = bool(self.dark_mode)
        self.remember_window_geometry = bool(self.remember_window_geometry)
        self.window_geometry = str(self.window_geometry or "")
        self.start_keybind = str(self.start_keybind or "")
        self.pause_keybind = str(self.pause_keybind or "")
        if self.mouse_click_delay_min_ms > self.mouse_click_delay_max_ms:
            self.mouse_click_delay_min_ms, self.mouse_click_delay_max_ms = self.mouse_click_delay_max_ms, self.mouse_click_delay_min_ms
        if self.key_press_delay_min_ms > self.key_press_delay_max_ms:
            self.key_press_delay_min_ms, self.key_press_delay_max_ms = self.key_press_delay_max_ms, self.key_press_delay_min_ms


def _clamp_int(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, int(value)))
