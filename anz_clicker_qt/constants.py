from __future__ import annotations

from actions import ActionType, ExecutionGroup
from .version import APP_VERSION


APP_TITLE = "Anz Clicker"
SEQUENTIAL_GROUP = ExecutionGroup.SEQUENTIAL.value
BACKGROUND_GROUP = ExecutionGroup.PARALLEL.value
PICTURE_ACTIONS = {ActionType.WAIT_FOR_PICTURE.value, ActionType.AUTO_PICTURE_CLICKER.value}
SCRIPT_ACTIONS = {ActionType.LAUNCH_ANZ_SCRIPT.value, ActionType.LAUNCH_ANZ_SCRIPT_AND_WAIT.value}
BUILT_IN_ACTION_TYPES = [item.value for item in ActionType]
PRESET_PREFIX = "Custom: "
POSITION_ACTIONS = {
    ActionType.ANIMATE_MOUSE.value,
    ActionType.MOVE_MOUSE.value,
    ActionType.LEFT_CLICK.value,
    ActionType.RIGHT_CLICK.value,
    ActionType.SHIFT_CLICK.value,
    ActionType.DOUBLE_CLICK.value,
    ActionType.MOUSE_DOWN.value,
    ActionType.MOUSE_UP.value,
}
CAPTURE_KEY_ACTIONS = {ActionType.TYPE_KEY.value, ActionType.PRESS_KEY.value, ActionType.RELEASE_KEY.value}
SIMPLE_ACTION_KEYS = {
    ActionType.PRESS_SPACEBAR.value: "space",
    ActionType.PRESS_SHIFT_SPACEBAR.value: "shift+space",
    ActionType.PRESS_ENTER.value: "enter",
    ActionType.CTRL_C.value: "ctrl+c",
    ActionType.CTRL_V.value: "ctrl+v",
    ActionType.PRESS_TAB.value: "tab",
    ActionType.PRESS_SHIFT_TAB.value: "shift+tab",
    ActionType.PRESS_BACKSPACE.value: "backspace",
    ActionType.ALT_TAB.value: "alt+tab",
}
LAUNCH_MODES = ("Show", "Minimized", "Maximized", "Hidden")
