from __future__ import annotations

import json
import math
import random
from pathlib import Path
import shutil

from actions import Action, ActionType, ExecutionGroup, PositionMode, ScreenArea
from app_settings import AppSettings
import input_controller
from preset_store import PresetStore
from anz_clicker_qt.widgets import target_label


TMP_ROOT = Path("tmp_qt_doc_test") / "smoke_test"


def reset_tmp_root() -> None:
    if TMP_ROOT.exists():
        shutil.rmtree(TMP_ROOT, ignore_errors=True)
    TMP_ROOT.mkdir(parents=True, exist_ok=True)


def test_settings_round_trip() -> None:
    path = TMP_ROOT / "settings.json"
    settings = AppSettings(
        mouse_animation_speed=7,
        enhanced_humanlike_mouse=True,
        mouse_click_delay_min_ms=45,
        mouse_click_delay_max_ms=150,
        key_press_delay_min_ms=80,
        key_press_delay_max_ms=170,
        default_script_folder="scripts",
        remember_window_geometry=False,
        start_keybind="F6",
        pause_keybind="F8",
    )
    settings.save(path)
    loaded = AppSettings.load(path)
    assert loaded.mouse_animation_speed == 7
    assert loaded.enhanced_humanlike_mouse is True
    assert loaded.default_script_folder == "scripts"
    assert loaded.remember_window_geometry is False


def test_enhanced_mouse_path_is_interruptible_and_exact() -> None:
    original_current_position = input_controller.current_position
    original_set_position = input_controller.set_position
    original_sleep = input_controller.time.sleep
    positions: list[tuple[int, int]] = []

    def fake_current_position() -> tuple[int, int]:
        return positions[-1] if positions else (0, 0)

    def fake_set_position(x: int, y: int) -> None:
        positions.append((int(x), int(y)))

    try:
        input_controller.current_position = fake_current_position
        input_controller.set_position = fake_set_position
        input_controller.time.sleep = lambda _seconds: None
        input_controller.configure_input_timing(mouse_animation_speed=5, enhanced_humanlike_mouse=True)
        input_controller.animate_mouse_human(400, 240, 500)
        assert positions
        assert positions[-1] == (400, 240)
        trace = [(0, 0)] + positions
        assert max(math.dist(a, b) for a, b in zip(trace, trace[1:])) <= 36

        for seed in range(40):
            random.seed(seed)
            positions.clear()
            input_controller.animate_mouse_human(900, 620, 700)
            assert positions
            assert positions[-1] == (900, 620)
            trace = [(0, 0)] + positions
            assert max(math.dist(a, b) for a, b in zip(trace, trace[1:])) <= 36

        positions.clear()
        input_controller.animate_mouse_human(400, 240, 500, should_stop=lambda: True)
        assert positions == []
    finally:
        input_controller.current_position = original_current_position
        input_controller.set_position = original_set_position
        input_controller.time.sleep = original_sleep
        input_controller.configure_input_timing(mouse_animation_speed=5, enhanced_humanlike_mouse=False)


def test_mouse_animation_speed_scales_distance_duration() -> None:
    input_controller.configure_input_timing(mouse_animation_speed=5)
    normal = input_controller.estimate_mouse_animation_duration_ms(500)
    input_controller.configure_input_timing(mouse_animation_speed=10)
    fast = input_controller.estimate_mouse_animation_duration_ms(500)
    input_controller.configure_input_timing(mouse_animation_speed=1)
    slow = input_controller.estimate_mouse_animation_duration_ms(500)
    input_controller.configure_input_timing(mouse_animation_speed=5)
    short = input_controller.estimate_mouse_animation_duration_ms(80)
    long = input_controller.estimate_mouse_animation_duration_ms(1200)

    assert fast < normal < slow
    assert short < normal < long


def test_action_serialization_round_trip() -> None:
    action = Action(
        action_type=ActionType.WAIT_FOR_SCREEN_TEXT.value,
        execution_group=ExecutionGroup.SEQUENTIAL.value,
        position_mode=PositionMode.AREA.value,
        area=ScreenArea(10, 20, 300, 120),
        screen_text_area=ScreenArea(50, 60, 420, 90),
        screen_text_pattern=r"Hello\\s+World",
        screen_text_is_regex=True,
        delay_seconds=2,
        random_delay_milliseconds=250,
        repeat=3,
        random_repeat=2,
        comment="Smoke text wait",
    )
    restored = Action.from_dict(action.to_dict())
    assert restored.action_type == ActionType.WAIT_FOR_SCREEN_TEXT.value
    assert restored.area and restored.area.summary() == "10,20 300x120"
    assert restored.screen_text_area and restored.screen_text_area.summary() == "50,60 420x90"
    assert restored.screen_text_pattern == r"Hello\\s+World"
    assert restored.screen_text_is_regex is True


def test_keyboard_action_target_labels_show_keys() -> None:
    assert target_label(Action(action_type=ActionType.TYPE_KEY.value, key="ctrl+t")) == "ctrl+t"
    assert target_label(Action(action_type=ActionType.PRESS_KEY.value, key="t")) == "t"
    assert target_label(Action(action_type=ActionType.PRESS_SPACEBAR.value)) == "space"
    assert target_label(Action(action_type=ActionType.CTRL_V.value)) == "ctrl+v"


def test_script_payload_round_trip() -> None:
    path = TMP_ROOT / "script.json"
    sequential = [
        Action(action_type=ActionType.LEFT_CLICK.value, x=100, y=200, position_mode=PositionMode.COORDINATES.value),
        Action(action_type=ActionType.WAIT.value, delay_seconds=1),
    ]
    background = [
        Action(action_type=ActionType.PRESS_SPACEBAR.value, key="space", delay_seconds=30, repeat=5, execution_group=ExecutionGroup.PARALLEL.value)
    ]
    payload = {
        "sequential_actions": [action.to_dict() for action in sequential],
        "parallel_actions": [action.to_dict() for action in background],
        "sequential_repeat_count": 2,
        "sequential_random_repeat_count": 1,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    loaded = json.loads(path.read_text(encoding="utf-8"))
    loaded_sequential = [Action.from_dict(item) for item in loaded["sequential_actions"]]
    loaded_background = [Action.from_dict(item) for item in loaded["parallel_actions"]]
    assert len(loaded_sequential) == 2
    assert loaded_sequential[0].x == 100
    assert len(loaded_background) == 1
    assert loaded_background[0].execution_group == ExecutionGroup.PARALLEL.value
    assert loaded["sequential_repeat_count"] == 2


def test_nested_script_runtime_planning() -> None:
    nested_path = TMP_ROOT / "nested_script.json"
    nested_payload = {
        "sequential_actions": [
            Action(action_type=ActionType.WAIT.value, delay_seconds=2).to_dict(),
        ],
        "parallel_actions": [
            Action(action_type=ActionType.WAIT.value, delay_seconds=5, execution_group=ExecutionGroup.PARALLEL.value).to_dict(),
        ],
        "sequential_repeat_count": 1,
        "sequential_random_repeat_count": 0,
    }
    nested_path.write_text(json.dumps(nested_payload, indent=2), encoding="utf-8")

    import runner

    action_wait = Action(action_type=ActionType.LAUNCH_ANZ_SCRIPT_AND_WAIT.value, launch_path=str(nested_path))
    wait_plan = runner.ActionRunner()._build_runtime_plan([action_wait], 1)
    assert wait_plan.total_estimated_ms == 5000

    action_nowait = Action(action_type=ActionType.LAUNCH_ANZ_SCRIPT.value, launch_path=str(nested_path))
    main_actions = [
        Action(action_type=ActionType.WAIT.value, delay_seconds=1),
        action_nowait,
        Action(action_type=ActionType.WAIT.value, delay_seconds=1),
    ]
    nowait_plan = runner.ActionRunner()._build_runtime_plan(main_actions, 1)
    assert nowait_plan.total_estimated_ms == 6000


def test_stop_anz_clicker_action_sets_global_stop() -> None:
    import runner

    statuses: list[str] = []
    action_runner = runner.ActionRunner(statuses.append)
    stop_action = Action(action_type=ActionType.STOP_ANZ_CLICKER.value, repeat=99, random_repeat=99)
    planned = action_runner._plan_action_run(stop_action)
    assert planned.repeat_count == 1
    action_runner._execute_action(stop_action)
    assert action_runner._stop_event.is_set()
    assert statuses[-1] == "Stop Anz Clicker action executed."


def test_runtime_planning_rejects_circular_nested_scripts() -> None:
    import runner

    first_path = TMP_ROOT / "cycle_a.json"
    second_path = TMP_ROOT / "cycle_b.json"
    first_path.write_text(
        json.dumps({"sequential_actions": [Action(action_type=ActionType.LAUNCH_ANZ_SCRIPT_AND_WAIT.value, launch_path=str(second_path)).to_dict()]}),
        encoding="utf-8",
    )
    second_path.write_text(
        json.dumps({"sequential_actions": [Action(action_type=ActionType.LAUNCH_ANZ_SCRIPT_AND_WAIT.value, launch_path=str(first_path)).to_dict()]}),
        encoding="utf-8",
    )
    try:
        runner.ActionRunner()._plan_nested_script(str(first_path))
    except runner.RuntimePlanError as exc:
        assert "Circular nested script reference" in str(exc)
    else:
        raise AssertionError("Circular nested script was not rejected")


def test_runtime_planning_rejects_unreasonable_runtime() -> None:
    import runner

    long_action = Action(action_type=ActionType.WAIT.value, delay_minutes=60, repeat=16)
    try:
        runner.ActionRunner()._build_runtime_plan([long_action], 1)
    except runner.RuntimePlanError as exc:
        assert "Estimated runtime is too long" in str(exc)
    else:
        raise AssertionError("Unreasonable runtime was not rejected")


def test_preset_store_round_trip() -> None:
    path = TMP_ROOT / "presets.json"
    store = PresetStore(path)
    action = Action(action_type=ActionType.RIGHT_CLICK.value, delay_milliseconds=100, comment="Default right click")
    store.set_default(action)
    loaded = PresetStore(path)
    restored = loaded.default_for(ActionType.RIGHT_CLICK.value)
    assert restored is not None
    assert restored.comment == "Default right click"


def main() -> int:
    reset_tmp_root()
    tests = [
        test_settings_round_trip,
        test_enhanced_mouse_path_is_interruptible_and_exact,
        test_mouse_animation_speed_scales_distance_duration,
        test_action_serialization_round_trip,
        test_keyboard_action_target_labels_show_keys,
        test_script_payload_round_trip,
        test_nested_script_runtime_planning,
        test_stop_anz_clicker_action_sets_global_stop,
        test_runtime_planning_rejects_circular_nested_scripts,
        test_runtime_planning_rejects_unreasonable_runtime,
        test_preset_store_round_trip,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print("Smoke tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
