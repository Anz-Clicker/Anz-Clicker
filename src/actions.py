from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import random
from typing import Any


class ActionType(str, Enum):
    ANIMATE_MOUSE = "Animate Mouse"
    MOVE_MOUSE = "Move Mouse"
    LEFT_CLICK = "Left Click"
    RIGHT_CLICK = "Right Click"
    WAIT = "Wait"
    TYPE_KEY = "Type Key"
    PRESS_KEY = "Press Key"
    RELEASE_KEY = "Release Key"
    PRESS_SPACEBAR = "Press Spacebar"
    PRESS_SHIFT_SPACEBAR = "Press Shift + Spacebar"
    SHIFT_CLICK = "Shift + Click"
    PRESS_ENTER = "Press Enter"
    CTRL_C = "Ctrl + C"
    CTRL_V = "Ctrl + V"
    PRESS_TAB = "Press Tab"
    PRESS_SHIFT_TAB = "Press Shift + Tab"
    PRESS_BACKSPACE = "Backspace"
    ALT_TAB = "Alt + Tab"
    DOUBLE_CLICK = "Double Click"
    MOUSE_DOWN = "Mouse Down"
    MOUSE_UP = "Mouse Up"
    LAUNCH_APP = "Launch App"
    LAUNCH_ANZ_SCRIPT = "Launch Anz Clicker Script"
    LAUNCH_ANZ_SCRIPT_AND_WAIT = "Launch Anz Clicker Script and Wait"
    WAIT_FOR_SCREEN_CHANGE = "Wait for Screen Change"
    WAIT_FOR_PIXEL_COLOR = "Wait for Pixel Color"
    WAIT_FOR_PICTURE = "Wait for Picture"
    WAIT_FOR_SCREEN_TEXT = "Wait for Screen Text"
    AUTO_PICTURE_CLICKER = "Auto Picture Clicker"
    STOP_ANZ_CLICKER = "Stop Anz Clicker"


class PositionMode(str, Enum):
    CURRENT = "current"
    COORDINATES = "coordinates"
    AREA = "area"


class ExecutionGroup(str, Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"


@dataclass
class ScreenArea:
    left: int = 0
    top: int = 0
    width: int = 0
    height: int = 0

    def normalized(self) -> "ScreenArea":
        left = min(self.left, self.left + self.width)
        top = min(self.top, self.top + self.height)
        width = abs(self.width)
        height = abs(self.height)
        return ScreenArea(left=left, top=top, width=width, height=height)

    def is_valid(self) -> bool:
        normalized = self.normalized()
        return normalized.width > 0 and normalized.height > 0

    def as_tuple(self) -> tuple[int, int, int, int]:
        normalized = self.normalized()
        return (
            normalized.left,
            normalized.top,
            normalized.left + normalized.width,
            normalized.top + normalized.height,
        )

    def summary(self) -> str:
        normalized = self.normalized()
        return f"{normalized.left},{normalized.top} {normalized.width}x{normalized.height}"


def parts_to_ms(minutes: int, seconds: int, milliseconds: int) -> int:
    return (minutes * 60 * 1000) + (seconds * 1000) + milliseconds


@dataclass
class Action:
    action_type: str
    enabled: bool = True
    comment: str = ""
    preset_name: str = ""
    execution_group: str = ExecutionGroup.SEQUENTIAL.value
    start_as_background: bool = False
    position_mode: str = PositionMode.CURRENT.value
    x: int | None = None
    y: int | None = None
    area: ScreenArea | None = None
    random_x: int = 0
    random_y: int = 0
    delay_minutes: int = 0
    delay_seconds: int = 0
    delay_milliseconds: int = 0
    random_delay_minutes: int = 0
    random_delay_seconds: int = 0
    random_delay_milliseconds: int = 0
    repeat: int = 1
    random_repeat: int = 0
    key: str = ""
    movement_duration_minutes: int = 0
    movement_duration_seconds: int = 0
    movement_duration_milliseconds: int = 800
    launch_path: str = ""
    launch_args: str = ""
    launch_verb: str = ""
    launch_mode: str = "Show"
    screen_change_min_percent: float = 0.0
    screen_change_max_percent: float = 0.0
    screen_change_check_minutes: int = 0
    screen_change_check_seconds: int = 0
    screen_change_check_milliseconds: int = 200
    pixel_x: int | None = None
    pixel_y: int | None = None
    pixel_r: int = 0
    pixel_g: int = 0
    pixel_b: int = 0
    pixel_tolerance_percent: float = 0.0
    pixel_wait_minutes: int = 0
    pixel_wait_seconds: int = 0
    pixel_wait_milliseconds: int = 0
    picture_area: ScreenArea | None = None
    picture_path: str = ""
    picture_tolerance_percent: float = 0.0
    picture_wait_minutes: int = 0
    picture_wait_seconds: int = 0
    picture_wait_milliseconds: int = 0
    picture_found_animate: bool = False
    picture_found_random_point: bool = False
    screen_text_area: ScreenArea | None = None
    screen_text_pattern: str = ""
    screen_text_is_regex: bool = False

    def display_name(self) -> str:
        parts = [self.preset_name or self.action_type]
        target = self.position_summary()
        if target:
            parts.append(target)
        if self.key:
            parts.append(f"[{self.key}]")
        if self.action_type in {ActionType.LAUNCH_APP.value, ActionType.LAUNCH_ANZ_SCRIPT.value, ActionType.LAUNCH_ANZ_SCRIPT_AND_WAIT.value} and self.launch_path:
            parts.append(f"[{self.launch_path}]")
        if self.repeat != 1 or self.random_repeat:
            parts.append(f"x{self.repeat}+r{self.random_repeat}")
        if self.comment:
            parts.append(f"- {self.comment}")
        return " ".join(parts)

    def position_summary(self) -> str:
        if self.position_mode == PositionMode.AREA.value and self.area and self.area.is_valid():
            return f"[Area {self.area.summary()}]"
        if self.position_mode == PositionMode.COORDINATES.value and self.x is not None and self.y is not None:
            summary = f"({self.x}, {self.y})"
            if self.random_x or self.random_y:
                summary += f" +/-({self.random_x}, {self.random_y})"
            return summary
        if self.position_mode == PositionMode.CURRENT.value:
            return "[Current Cursor]"
        return ""

    def delay_ms(self) -> int:
        return parts_to_ms(self.delay_minutes, self.delay_seconds, self.delay_milliseconds)

    def random_delay_ms(self) -> int:
        return parts_to_ms(self.random_delay_minutes, self.random_delay_seconds, self.random_delay_milliseconds)

    def screen_check_interval_ms(self) -> int:
        return max(
            10,
            parts_to_ms(
                self.screen_change_check_minutes,
                self.screen_change_check_seconds,
                self.screen_change_check_milliseconds,
            ),
        )

    def movement_duration_ms(self) -> int:
        return max(0, parts_to_ms(self.movement_duration_minutes, self.movement_duration_seconds, self.movement_duration_milliseconds))

    def pixel_wait_timeout_ms(self) -> int:
        return parts_to_ms(self.pixel_wait_minutes, self.pixel_wait_seconds, self.pixel_wait_milliseconds)

    def picture_wait_timeout_ms(self) -> int:
        return parts_to_ms(self.picture_wait_minutes, self.picture_wait_seconds, self.picture_wait_milliseconds)

    def resolve_repeat_count(self) -> int:
        extra = random.randint(1, self.random_repeat) if self.random_repeat > 0 else 0
        return max(1, self.repeat + extra)

    def resolve_delay_ms(self) -> int:
        extra = random.randint(0, self.random_delay_ms()) if self.random_delay_ms() > 0 else 0
        return max(0, self.delay_ms() + extra)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if self.area is None:
            data["area"] = None
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Action":
        payload = dict(data)
        area_data = payload.get("area")
        if isinstance(area_data, dict):
            payload["area"] = ScreenArea(**area_data)
        picture_area_data = payload.get("picture_area")
        if isinstance(picture_area_data, dict):
            payload["picture_area"] = ScreenArea(**picture_area_data)
        screen_text_area_data = payload.get("screen_text_area")
        if isinstance(screen_text_area_data, dict):
            payload["screen_text_area"] = ScreenArea(**screen_text_area_data)
        return cls(**payload)
