from __future__ import annotations

import ctypes
import math
import random
import threading
import time
from ctypes import wintypes

from collections.abc import Callable

from actions import ScreenArea


user32 = ctypes.windll.user32
shell32 = ctypes.windll.shell32

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002

SW_SHOWNORMAL = 1
SW_SHOWMINIMIZED = 2
SW_SHOWMAXIMIZED = 3
SW_HIDE = 0

MODIFIER_KEYS = {"shift", "ctrl", "control", "alt", "win"}

MOUSE_ANIMATION_SPEED = 5
ENHANCED_HUMANLIKE_MOUSE = False
MOUSE_CLICK_DELAY_MIN_MS = 55
MOUSE_CLICK_DELAY_MAX_MS = 135
KEY_PRESS_DELAY_MIN_MS = 80
KEY_PRESS_DELAY_MAX_MS = 160
_MOUSE_ANIMATION_LOCK = threading.Lock()
_ENHANCED_MAX_STEP_PX = 32.0


def configure_input_timing(
    *,
    mouse_animation_speed: int = 5,
    enhanced_humanlike_mouse: bool = False,
    mouse_click_delay_min_ms: int = 55,
    mouse_click_delay_max_ms: int = 135,
    key_press_delay_min_ms: int = 80,
    key_press_delay_max_ms: int = 160,
) -> None:
    global MOUSE_ANIMATION_SPEED
    global ENHANCED_HUMANLIKE_MOUSE
    global MOUSE_CLICK_DELAY_MIN_MS
    global MOUSE_CLICK_DELAY_MAX_MS
    global KEY_PRESS_DELAY_MIN_MS
    global KEY_PRESS_DELAY_MAX_MS
    MOUSE_ANIMATION_SPEED = max(1, min(10, int(mouse_animation_speed)))
    ENHANCED_HUMANLIKE_MOUSE = bool(enhanced_humanlike_mouse)
    MOUSE_CLICK_DELAY_MIN_MS, MOUSE_CLICK_DELAY_MAX_MS = _ordered_delay(mouse_click_delay_min_ms, mouse_click_delay_max_ms)
    KEY_PRESS_DELAY_MIN_MS, KEY_PRESS_DELAY_MAX_MS = _ordered_delay(key_press_delay_min_ms, key_press_delay_max_ms)


def _ordered_delay(low_ms: int, high_ms: int) -> tuple[int, int]:
    low = max(0, int(low_ms))
    high = max(0, int(high_ms))
    return (low, high) if low <= high else (high, low)


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    ]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("union",)
    _fields_ = [("type", wintypes.DWORD), ("union", _INPUTUNION)]


VK_CODES = {
    "space": 0x20,
    "enter": 0x0D,
    "tab": 0x09,
    "esc": 0x1B,
    "escape": 0x1B,
    "backspace": 0x08,
    "shift": 0x10,
    "ctrl": 0x11,
    "control": 0x11,
    "alt": 0x12,
    "left": 0x25,
    "up": 0x26,
    "right": 0x27,
    "down": 0x28,
    "f6": 0x75,
}

SHOW_MODES = {
    "Show": SW_SHOWNORMAL,
    "Minimized": SW_SHOWMINIMIZED,
    "Maximized": SW_SHOWMAXIMIZED,
    "Hidden": SW_HIDE,
}


def _send_mouse(flags: int) -> None:
    input_struct = INPUT(type=INPUT_MOUSE, mi=MOUSEINPUT(0, 0, 0, flags, 0, None))
    user32.SendInput(1, ctypes.byref(input_struct), ctypes.sizeof(INPUT))


def _send_key(vk: int, key_up: bool = False) -> None:
    flags = KEYEVENTF_KEYUP if key_up else 0
    input_struct = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(vk, 0, flags, 0, None))
    user32.SendInput(1, ctypes.byref(input_struct), ctypes.sizeof(INPUT))


def _human_pause(low_ms: int, high_ms: int) -> None:
    low_ms, high_ms = _ordered_delay(low_ms, high_ms)
    time.sleep(random.randint(low_ms, high_ms) / 1000)


def current_position() -> tuple[int, int]:
    point = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(point))
    return point.x, point.y


def point_in_area(area: ScreenArea) -> tuple[int, int]:
    normalized = area.normalized()
    x = random.randint(normalized.left, normalized.left + normalized.width - 1)
    y = random.randint(normalized.top, normalized.top + normalized.height - 1)
    return x, y


def resolve_coordinate_point(x: int, y: int, random_x: int = 0, random_y: int = 0) -> tuple[int, int]:
    target_x = x + random.randint(-random_x, random_x) if random_x else x
    target_y = y + random.randint(-random_y, random_y) if random_y else y
    return target_x, target_y


def set_position(x: int, y: int) -> None:
    user32.SetCursorPos(int(x), int(y))


def animate_mouse_human(target_x: int, target_y: int, duration_ms: int = 0, should_stop: Callable[[], bool] | None = None) -> None:
    if not _acquire_mouse_animation_lock(should_stop):
        return
    try:
        if ENHANCED_HUMANLIKE_MOUSE:
            _animate_mouse_enhanced(target_x, target_y, duration_ms, should_stop)
        else:
            _animate_mouse_standard(target_x, target_y, duration_ms, should_stop)
    finally:
        _MOUSE_ANIMATION_LOCK.release()


def _acquire_mouse_animation_lock(should_stop: Callable[[], bool] | None = None) -> bool:
    while True:
        if should_stop and should_stop():
            return False
        if _MOUSE_ANIMATION_LOCK.acquire(timeout=0.03):
            return True


def _sleep_interruptibly(seconds: float, should_stop: Callable[[], bool] | None = None, chunk_seconds: float = 0.02) -> bool:
    remaining = max(0.0, seconds)
    while remaining > 0:
        if should_stop and should_stop():
            return False
        chunk = min(chunk_seconds, remaining)
        time.sleep(chunk)
        remaining -= chunk
    return not (should_stop and should_stop())


def _mouse_speed_factor() -> float:
    speed = max(1, min(10, MOUSE_ANIMATION_SPEED))
    return (1 / 3) + ((speed - 1) * ((3 - (1 / 3)) / 9))


def estimate_mouse_animation_duration_ms(distance: float) -> int:
    return _distance_scored_duration_ms(distance, randomize=False)


def _animation_duration_ms(distance: float, _duration_ms: int = 0, *, minimum_ms: int = 120) -> int:
    return max(minimum_ms, _distance_scored_duration_ms(distance, randomize=True))


def _distance_scored_duration_ms(distance: float, *, randomize: bool) -> int:
    distance = max(0.0, float(distance))
    base_ms = 180 + (620 * pow(min(distance, 1800) / 500, 0.72))
    if distance > 1800:
        base_ms += min(900, (distance - 1800) * 0.22)

    if randomize:
        if base_ms < 600:
            random_add_ms = random.randint(90, 260)
        elif base_ms < 1000:
            random_add_ms = random.randint(140, 360)
        else:
            random_add_ms = random.randint(280, 560)
    else:
        if base_ms < 600:
            random_add_ms = 175
        elif base_ms < 1000:
            random_add_ms = 250
        else:
            random_add_ms = 420

    return int((base_ms + random_add_ms) / _mouse_speed_factor())


def _animate_mouse_standard(target_x: int, target_y: int, duration_ms: int = 0, should_stop: Callable[[], bool] | None = None) -> None:
    start_x, start_y = current_position()
    distance = math.dist((start_x, start_y), (target_x, target_y))
    if distance < 2:
        return

    duration_ms = _animation_duration_ms(distance, duration_ms)
    steps = max(24, min(150, int(distance / 6.5) + duration_ms // 16))

    control_dx = target_x - start_x
    control_dy = target_y - start_y
    mid_x = (start_x + target_x) / 2
    mid_y = (start_y + target_y) / 2
    curve_strength = max(12.0, min(135.0, distance * 0.15))
    perpendicular_x = -control_dy
    perpendicular_y = control_dx
    perp_len = math.hypot(perpendicular_x, perpendicular_y) or 1.0
    offset_scale = random.uniform(-curve_strength, curve_strength)
    control_x = mid_x + (perpendicular_x / perp_len) * offset_scale
    control_y = mid_y + (perpendicular_y / perp_len) * offset_scale
    secondary_offset = random.uniform(-curve_strength * 0.45, curve_strength * 0.45)
    control2_x = ((mid_x + target_x) / 2) + (perpendicular_x / perp_len) * secondary_offset
    control2_y = ((mid_y + target_y) / 2) + (perpendicular_y / perp_len) * secondary_offset

    last_x = start_x
    last_y = start_y
    for step in range(1, steps + 1):
        if should_stop and should_stop():
            return
        t = step / steps
        accelerated = pow(t, 1.18)
        eased = 1 - pow(1 - accelerated, 2.2)
        inv = 1 - eased
        x = (
            (inv ** 3) * start_x
            + (3 * (inv ** 2) * eased * control_x)
            + (3 * inv * (eased ** 2) * control2_x)
            + (eased ** 3) * target_x
        )
        y = (
            (inv ** 3) * start_y
            + (3 * (inv ** 2) * eased * control_y)
            + (3 * inv * (eased ** 2) * control2_y)
            + (eased ** 3) * target_y
        )

        remaining = 1 - t
        jitter_scale = max(0.0, min(3.0, distance * 0.007)) * remaining
        if remaining > 0.05:
            x += random.uniform(-jitter_scale, jitter_scale)
            y += random.uniform(-jitter_scale, jitter_scale)
        if 0.18 < t < 0.82 and random.random() < 0.08:
            x += random.uniform(-1.6, 1.6)
            y += random.uniform(-1.6, 1.6)

        next_x = round(x)
        next_y = round(y)
        if next_x != last_x or next_y != last_y:
            set_position(next_x, next_y)
            last_x, last_y = next_x, next_y
        sleep_ms = duration_ms / steps
        if not _sleep_interruptibly(random.uniform(sleep_ms * 0.72, sleep_ms * 1.28) / 1000, should_stop):
            return

    if should_stop and should_stop():
        return
    if random.random() < 0.72:
        overshoot_x = target_x + random.randint(-2, 3)
        overshoot_y = target_y + random.randint(-2, 3)
        set_position(overshoot_x, overshoot_y)
        if not _sleep_interruptibly(random.uniform(0.008, 0.028), should_stop, 0.01):
            return
    if random.random() < 0.35:
        settle_x = target_x + random.randint(-1, 1)
        settle_y = target_y + random.randint(-1, 1)
        set_position(settle_x, settle_y)
        if not _sleep_interruptibly(random.uniform(0.006, 0.02), should_stop, 0.01):
            return
    if should_stop and should_stop():
        return
    set_position(target_x, target_y)


def _animate_mouse_enhanced(target_x: int, target_y: int, duration_ms: int = 0, should_stop: Callable[[], bool] | None = None) -> None:
    start_x, start_y = current_position()
    distance = math.dist((start_x, start_y), (target_x, target_y))
    if distance < 2:
        return
    if should_stop and should_stop():
        return

    profile = _choose_enhanced_profile(distance)
    duration_ms = _enhanced_duration_ms(distance, duration_ms, profile)
    if distance > 180 and random.random() < profile["nudge_chance"]:
        nudge_x, nudge_y = _wrong_direction_nudge(start_x, start_y, target_x, target_y)
        set_position(nudge_x, nudge_y)
        if not _sleep_interruptibly(random.uniform(0.018, 0.07), should_stop, 0.012):
            return
        start_x, start_y = current_position()

    path_points = _enhanced_path_points(start_x, start_y, target_x, target_y, distance, duration_ms, profile)
    for x, y, delay_seconds in path_points:
        if should_stop and should_stop():
            return
        set_position(x, y)
        if not _sleep_interruptibly(delay_seconds, should_stop, 0.018):
            return

    if should_stop and should_stop():
        return
    _enhanced_settle(target_x, target_y, distance, profile, should_stop)


def _choose_enhanced_profile(distance: float) -> dict[str, float | str]:
    roll = random.random()
    if distance < 90:
        mode = "direct" if roll < 0.78 else ("subtle" if roll < 0.96 else "small_miss")
    elif distance < 260:
        mode = "direct" if roll < 0.45 else ("subtle" if roll < 0.82 else ("arc" if roll < 0.94 else "small_miss"))
    elif distance < 650:
        mode = "direct" if roll < 0.22 else ("subtle" if roll < 0.56 else ("arc" if roll < 0.86 else "large_miss"))
    else:
        mode = "direct" if roll < 0.14 else ("subtle" if roll < 0.42 else ("arc" if roll < 0.78 else "large_miss"))

    arc_scale = {
        "direct": random.uniform(0.0, 0.035),
        "subtle": random.uniform(0.035, 0.11),
        "arc": random.uniform(0.11, 0.26),
        "small_miss": random.uniform(0.03, 0.12),
        "large_miss": random.uniform(0.08, 0.22),
    }[mode]
    jitter = {
        "direct": 0.0 if random.random() < 0.82 else random.uniform(0.05, 0.18),
        "subtle": random.uniform(0.05, 0.28),
        "arc": random.uniform(0.08, 0.38),
        "small_miss": random.uniform(0.02, 0.18),
        "large_miss": random.uniform(0.04, 0.24),
    }[mode]
    return {
        "mode": mode,
        "arc_scale": arc_scale,
        "jitter": jitter,
        "nudge_chance": 0.02 if distance < 180 else min(0.26, distance / 2600),
        "speed_variance": random.uniform(0.78, 1.28),
    }


def _enhanced_duration_ms(distance: float, duration_ms: int, profile: dict[str, float | str]) -> int:
    base = _animation_duration_ms(distance, duration_ms, minimum_ms=150 if distance < 120 else 190)
    mode = str(profile["mode"])
    mode_scale = {"direct": 0.72, "subtle": 0.92, "arc": 1.08, "small_miss": 1.12, "large_miss": 1.22}[mode]
    speed_variance = float(profile["speed_variance"])
    return max(90 if distance < 90 else 160, int(base * mode_scale * speed_variance))


def _wrong_direction_nudge(start_x: int, start_y: int, target_x: int, target_y: int) -> tuple[int, int]:
    dx = target_x - start_x
    dy = target_y - start_y
    length = math.hypot(dx, dy) or 1.0
    nudge = random.uniform(1.0, 3.0)
    return round(start_x - (dx / length) * nudge), round(start_y - (dy / length) * nudge)


def _enhanced_path_points(
    start_x: int,
    start_y: int,
    target_x: int,
    target_y: int,
    distance: float,
    duration_ms: int,
    profile: dict[str, float | str],
) -> list[tuple[int, int, float]]:
    steps = max(18, min(210, int(distance / 5.8) + duration_ms // 16))
    controls = _enhanced_controls(start_x, start_y, target_x, target_y, distance, profile)
    points: list[tuple[int, int, float]] = []
    last_x, last_y = start_x, start_y
    base_sleep_ms = duration_ms / steps
    jitter_amount = float(profile["jitter"])

    for step in range(1, steps + 1):
        t = step / steps
        eased = _enhanced_ease(t)
        x, y = _cubic_point(start_x, start_y, controls[0], controls[1], target_x, target_y, eased)
        remaining = 1 - t
        jitter = jitter_amount * (remaining ** 1.7)
        if jitter > 0 and 0.1 < t < 0.88:
            x += random.uniform(-jitter, jitter)
            y += random.uniform(-jitter, jitter)
        next_x = round(x)
        next_y = round(y)
        delay_scale = _enhanced_delay_scale(t, str(profile["mode"]))
        delay = random.uniform(base_sleep_ms * 0.62, base_sleep_ms * 1.42) * delay_scale / 1000
        last_x, last_y = _append_limited_path_segment(points, last_x, last_y, next_x, next_y, delay)

    return points


def _append_limited_path_segment(
    points: list[tuple[int, int, float]],
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    delay_seconds: float,
    max_step_px: float = _ENHANCED_MAX_STEP_PX,
) -> tuple[int, int]:
    if end_x == start_x and end_y == start_y:
        return start_x, start_y
    distance = math.dist((start_x, start_y), (end_x, end_y))
    segments = max(1, math.ceil(distance / max_step_px))
    step_delay = delay_seconds / segments if segments else delay_seconds
    last_x, last_y = start_x, start_y
    for segment in range(1, segments + 1):
        ratio = segment / segments
        x = round(start_x + (end_x - start_x) * ratio)
        y = round(start_y + (end_y - start_y) * ratio)
        if x == last_x and y == last_y:
            continue
        points.append((x, y, step_delay))
        last_x, last_y = x, y
    return end_x, end_y


def _enhanced_controls(
    start_x: int,
    start_y: int,
    target_x: int,
    target_y: int,
    distance: float,
    profile: dict[str, float | str],
) -> tuple[tuple[float, float], tuple[float, float]]:
    dx = target_x - start_x
    dy = target_y - start_y
    perpendicular_x = -dy
    perpendicular_y = dx
    perp_len = math.hypot(perpendicular_x, perpendicular_y) or 1.0
    arc_strength = min(220.0, distance * float(profile["arc_scale"]))
    if random.random() < 0.45:
        arc_strength *= -1
    lift_bias = -abs(distance) * random.uniform(0.01, 0.055) if distance > 320 and str(profile["mode"]) in {"arc", "large_miss"} and random.random() < 0.38 else 0
    c1_x = start_x + dx * random.uniform(0.2, 0.42) + (perpendicular_x / perp_len) * arc_strength
    c1_y = start_y + dy * random.uniform(0.18, 0.38) + (perpendicular_y / perp_len) * arc_strength + lift_bias
    c2_x = start_x + dx * random.uniform(0.6, 0.9) - (perpendicular_x / perp_len) * arc_strength * random.uniform(0.05, 0.4)
    c2_y = start_y + dy * random.uniform(0.58, 0.88) - (perpendicular_y / perp_len) * arc_strength * random.uniform(0.05, 0.4) + lift_bias * random.uniform(0.1, 0.35)
    return (c1_x, c1_y), (c2_x, c2_y)


def _cubic_point(
    start_x: float,
    start_y: float,
    control1: tuple[float, float],
    control2: tuple[float, float],
    target_x: float,
    target_y: float,
    t: float,
) -> tuple[float, float]:
    inv = 1 - t
    c1_x, c1_y = control1
    c2_x, c2_y = control2
    x = (inv**3 * start_x) + (3 * inv**2 * t * c1_x) + (3 * inv * t**2 * c2_x) + (t**3 * target_x)
    y = (inv**3 * start_y) + (3 * inv**2 * t * c1_y) + (3 * inv * t**2 * c2_y) + (t**3 * target_y)
    return x, y


def _enhanced_ease(t: float) -> float:
    return min(1.0, max(0.0, t * t * (3 - 2 * t)))


def _enhanced_delay_scale(t: float, mode: str) -> float:
    if t < 0.12:
        return random.uniform(1.05, 1.45)
    if t > 0.82:
        return random.uniform(1.2, 1.95)
    if mode in {"arc", "large_miss"} and 0.42 < t < 0.72:
        return random.uniform(0.58, 0.9)
    return random.uniform(0.68, 1.08)


def _enhanced_settle(
    target_x: int,
    target_y: int,
    distance: float,
    profile: dict[str, float | str],
    should_stop: Callable[[], bool] | None = None,
) -> None:
    mode = str(profile["mode"])
    overshoot_chance = 0.04 if distance < 120 else (0.16 if distance < 300 else (0.36 if mode != "large_miss" else 0.72))
    overshot = False
    if random.random() < overshoot_chance:
        if mode == "large_miss" and distance > 300:
            overshoot = random.randint(50, 100)
        elif mode == "small_miss":
            overshoot = random.randint(6, 22)
        else:
            overshoot = max(2, min(26, int(distance * random.uniform(0.006, 0.035))))
        angle = random.uniform(0, math.tau)
        overshoot_x = round(target_x + math.cos(angle) * overshoot)
        overshoot_y = round(target_y + math.sin(angle) * overshoot)
        if not _move_mouse_segment(overshoot_x, overshoot_y, random.uniform(0.045, 0.15), should_stop):
            return
        if not _sleep_interruptibly(random.uniform(0.012, 0.055), should_stop, 0.01):
            return
        overshot = True
    if overshot:
        correction_x = target_x + random.randint(-1, 1)
        correction_y = target_y + random.randint(-1, 1)
        if not _move_mouse_segment(correction_x, correction_y, random.uniform(0.04, 0.14), should_stop):
            return
    settle_steps = random.randint(1, 2 if distance < 220 else 3)
    for _ in range(settle_steps):
        if should_stop and should_stop():
            return
        set_position(target_x + random.randint(-1, 1), target_y + random.randint(-1, 1))
        if not _sleep_interruptibly(random.uniform(0.008, 0.026), should_stop, 0.01):
            return
    if should_stop and should_stop():
        return
    set_position(target_x, target_y)


def _move_mouse_segment(
    target_x: int,
    target_y: int,
    duration_seconds: float,
    should_stop: Callable[[], bool] | None = None,
    max_step_px: float = 24.0,
) -> bool:
    start_x, start_y = current_position()
    distance = math.dist((start_x, start_y), (target_x, target_y))
    steps = max(1, math.ceil(distance / max_step_px))
    sleep_seconds = max(0.0, duration_seconds) / steps
    for step in range(1, steps + 1):
        if should_stop and should_stop():
            return False
        t = step / steps
        eased = t * t * (3 - 2 * t)
        x = round(start_x + (target_x - start_x) * eased)
        y = round(start_y + (target_y - start_y) * eased)
        set_position(x, y)
        if not _sleep_interruptibly(sleep_seconds, should_stop, 0.01):
            return False
    return True


def left_click() -> None:
    _send_mouse(MOUSEEVENTF_LEFTDOWN)
    _human_pause(MOUSE_CLICK_DELAY_MIN_MS, MOUSE_CLICK_DELAY_MAX_MS)
    _send_mouse(MOUSEEVENTF_LEFTUP)


def right_click() -> None:
    _send_mouse(MOUSEEVENTF_RIGHTDOWN)
    _human_pause(MOUSE_CLICK_DELAY_MIN_MS, MOUSE_CLICK_DELAY_MAX_MS)
    _send_mouse(MOUSEEVENTF_RIGHTUP)


def mouse_down() -> None:
    _send_mouse(MOUSEEVENTF_LEFTDOWN)


def mouse_up() -> None:
    _send_mouse(MOUSEEVENTF_LEFTUP)


def double_click() -> None:
    left_click()
    _human_pause(40, 120)
    left_click()


def key_press(key: str) -> None:
    perform_key_tap(key)


def key_down(key: str) -> None:
    _send_key(_key_to_vk(key), key_up=False)


def key_up(key: str) -> None:
    _send_key(_key_to_vk(key), key_up=True)


def combo_press(*keys: str) -> None:
    perform_key_tap("+".join(keys))


def shift_click() -> None:
    key_down("shift")
    _human_pause(20, 50)
    left_click()
    _human_pause(20, 50)
    key_up("shift")


def perform_key_tap(key_spec: str) -> None:
    modifiers, main_key = parse_key_spec(key_spec)
    for key in modifiers:
        key_down(key)
        _human_pause(22, 65)
    if main_key:
        key_down(main_key)
        _human_pause(KEY_PRESS_DELAY_MIN_MS, KEY_PRESS_DELAY_MAX_MS)
        key_up(main_key)
    elif modifiers:
        _human_pause(KEY_PRESS_DELAY_MIN_MS, KEY_PRESS_DELAY_MAX_MS)
    for key in reversed(modifiers):
        _human_pause(18, 52)
        key_up(key)


def perform_key_hold(key_spec: str) -> None:
    modifiers, main_key = parse_key_spec(key_spec)
    for key in modifiers:
        key_down(key)
        _human_pause(22, 65)
    if main_key:
        key_down(main_key)


def perform_key_release(key_spec: str) -> None:
    modifiers, main_key = parse_key_spec(key_spec)
    if main_key:
        key_up(main_key)
        _human_pause(18, 52)
    for key in reversed(modifiers):
        key_up(key)
        _human_pause(18, 52)


def parse_key_spec(key_spec: str) -> tuple[list[str], str]:
    parts = [normalize_key_name(part) for part in key_spec.split("+") if part.strip()]
    if not parts:
        raise ValueError("No key specified.")
    modifiers = [part for part in parts[:-1] if part in MODIFIER_KEYS]
    main_key = parts[-1]
    if main_key in MODIFIER_KEYS and len(parts) == 1:
        return [], main_key
    if main_key in MODIFIER_KEYS and len(parts) > 1:
        modifiers.append(main_key)
        main_key = ""
    return modifiers, main_key


def launch(path: str, args: str = "", verb: str = "", mode: str = "Show") -> None:
    show_mode = SHOW_MODES.get(mode, SW_SHOWNORMAL)
    result = shell32.ShellExecuteW(None, verb or None, path, args or None, None, show_mode)
    if result <= 32:
        raise OSError(f"Unable to launch: {path}")


def normalize_key_name(key: str) -> str:
    normalized = key.strip().lower()
    aliases = {
        "return": "enter",
        "control": "ctrl",
        "spacebar": "space",
    }
    return aliases.get(normalized, normalized)


def _key_to_vk(key: str) -> int:
    normalized = normalize_key_name(key)
    if normalized in VK_CODES:
        return VK_CODES[normalized]
    if len(normalized) == 1:
        return ord(normalized.upper())
    raise ValueError(f"Unsupported key: {key}")
