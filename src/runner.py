from __future__ import annotations

import json
import math
import random
import re
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from actions import Action, ActionType, ExecutionGroup, PositionMode
from app_settings import AppSettings
import input_controller
import screen_tools


StatusCallback = Callable[[str], None]
MAX_REASONABLE_RUNTIME_MS = 15 * 60 * 60 * 1000
MAX_ACTION_REPEAT_COUNT = 50_000
MAX_PLANNED_ACTION_RUNS = 250_000


class RuntimePlanError(ValueError):
    pass


@dataclass
class PlannedActionRun:
    action: Action
    delays_ms: list[int]
    nested_plans: list["RuntimePlan"] | None = None
    cycle: int = 1
    index: int = 1
    total_in_cycle: int = 1
    start_offset_ms: int = 0
    source_row: int = -1

    @property
    def repeat_count(self) -> int:
        return len(self.delays_ms)


@dataclass
class RuntimePlan:
    sequential_runs: list[PlannedActionRun]
    initial_background_runs: list[PlannedActionRun]
    total_estimated_ms: int
    sequential_cycles: int


class ActionRunner:
    PROGRESS_PREFIX = "__progress__:"
    ACTIVE_SEQUENTIAL_PREFIX = "__active_sequential__:"

    def __init__(self, status_callback: StatusCallback | None = None, settings: AppSettings | None = None) -> None:
        self._thread: threading.Thread | None = None
        self._parallel_threads: list[threading.Thread] = []
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._status_callback = status_callback
        self.settings = settings or AppSettings()
        self._progress_done = threading.Event()
        self._progress_thread: threading.Thread | None = None
        self._progress_total_ms = 0
        self._progress_elapsed_ms = 0

    @property
    def is_running(self) -> bool:
        if self._thread is not None and self._thread.is_alive():
            return True
        return any(thread.is_alive() for thread in self._parallel_threads)

    def start(self, actions: list[Action], sequential_cycles: int = 1) -> None:
        if self.is_running:
            return
        self._apply_settings()
        self._stop_event.clear()
        self._pause_event.clear()
        self._progress_done.clear()
        self._parallel_threads = []
        plan = self._build_runtime_plan(actions, max(1, sequential_cycles))
        self._thread = threading.Thread(target=self._run, args=(plan,), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._pause_event.clear()
        self._publish("Stopping...")

    @property
    def is_paused(self) -> bool:
        return self._pause_event.is_set()

    def pause(self) -> None:
        if self.is_running:
            self._pause_event.set()
            self._publish("Paused")

    def resume(self) -> None:
        if self.is_running:
            self._pause_event.clear()
            self._publish("Running")

    def _run(self, plan: RuntimePlan) -> None:
        final_status = "Completed"
        self._publish_progress(0, plan.total_estimated_ms)
        self._start_progress_monitor(plan.total_estimated_ms)
        self._publish("Running")
        try:
            if plan.initial_background_runs:
                self._start_parallel_runs(plan.initial_background_runs)
                if not plan.sequential_runs:
                    self._publish("Background actions running")

            for planned in plan.sequential_runs:
                if self._stop_event.is_set():
                    final_status = "Stopped"
                    return
                if not self._wait_if_paused():
                    final_status = "Stopped"
                    return

                action = planned.action
                self._publish_active_sequential(planned.source_row)
                self._publish("Sequential actions running")
                if action.start_as_background:
                    self._start_parallel_runs([planned])
                    continue
                if not self._execute_planned_run(planned):
                    final_status = "Stopped"
                    return

            self._publish_active_sequential(-1)
            if self._parallel_threads and not self._stop_event.is_set():
                self._publish("Background actions running")
                while not self._stop_event.is_set() and any(thread.is_alive() for thread in self._parallel_threads):
                    if not self._wait_if_paused():
                        final_status = "Stopped"
                        return
                    time.sleep(0.1)

            if self._stop_event.is_set():
                final_status = "Stopped"
        except InterruptedError:
            final_status = "Stopped"
        except Exception as exc:
            final_status = f"Error: {exc}"
        finally:
            self._publish_active_sequential(-1)
            self._finish_progress(final_status == "Completed")
            self._publish(final_status)

    def _build_runtime_plan(self, actions: list[Action], sequential_cycles: int, script_stack: tuple[Path, ...] = ()) -> RuntimePlan:
        sequential_entries = [(index, action) for index, action in enumerate(actions) if action.enabled and action.execution_group != ExecutionGroup.PARALLEL.value]
        sequential_actions = [action for _index, action in sequential_entries]
        background_actions = [action for action in actions if action.enabled and action.execution_group == ExecutionGroup.PARALLEL.value]
        projected_runs = (len(sequential_actions) * max(1, sequential_cycles)) + len(background_actions)
        if projected_runs > MAX_PLANNED_ACTION_RUNS:
            raise RuntimePlanError(f"Script expands to {projected_runs:,} planned action runs, which is too large to run safely.")
        sequential_runs: list[PlannedActionRun] = []
        background_runs: list[PlannedActionRun] = []
        sequential_elapsed_ms = 0

        for action in background_actions:
            planned = self._plan_action_run(action, script_stack=script_stack)
            background_runs.append(planned)

        total_in_cycle = len(sequential_actions)
        for cycle in range(1, sequential_cycles + 1):
            for index, (source_row, action) in enumerate(sequential_entries, start=1):
                planned = self._plan_action_run(action, cycle=cycle, index=index, total_in_cycle=total_in_cycle, start_offset_ms=sequential_elapsed_ms, source_row=source_row, script_stack=script_stack)
                sequential_runs.append(planned)
                if action.start_as_background:
                    background_runs.append(planned)
                elif action.action_type == ActionType.LAUNCH_ANZ_SCRIPT.value:
                    background_runs.append(planned)
                    sequential_elapsed_ms += self._planned_launch_only_blocking_duration_ms(planned)
                else:
                    sequential_elapsed_ms += self._planned_run_duration_ms(planned)

        background_finish_ms = max((run.start_offset_ms + self._planned_background_duration_ms(run) for run in background_runs), default=0)
        total_estimated_ms = max(sequential_elapsed_ms, background_finish_ms)
        if total_estimated_ms > MAX_REASONABLE_RUNTIME_MS:
            raise RuntimePlanError(
                "Estimated runtime is too long to run safely "
                f"({self._format_duration(total_estimated_ms)}). Limit is {self._format_duration(MAX_REASONABLE_RUNTIME_MS)}."
            )
        return RuntimePlan(
            sequential_runs=sequential_runs,
            initial_background_runs=[run for run in background_runs if run.start_offset_ms == 0 and run.action.execution_group == ExecutionGroup.PARALLEL.value],
            total_estimated_ms=total_estimated_ms,
            sequential_cycles=sequential_cycles,
        )

    def _plan_action_run(
        self,
        action: Action,
        cycle: int = 1,
        index: int = 1,
        total_in_cycle: int = 1,
        start_offset_ms: int = 0,
        source_row: int = -1,
        script_stack: tuple[Path, ...] = (),
    ) -> PlannedActionRun:
        repeat_count = self._sample_repeat_count(action)
        if repeat_count > MAX_ACTION_REPEAT_COUNT:
            raise RuntimePlanError(f"{action.action_type} expands to {repeat_count:,} repeats, which is too large to run safely.")
        delays = [self._sample_delay_ms(action) for _ in range(repeat_count)]
        nested_plans = None
        if action.action_type in {ActionType.LAUNCH_ANZ_SCRIPT.value, ActionType.LAUNCH_ANZ_SCRIPT_AND_WAIT.value}:
            nested_plans = [self._plan_nested_script(action.launch_path, script_stack) for _ in range(repeat_count)]
        return PlannedActionRun(action=action, delays_ms=delays, nested_plans=nested_plans, cycle=cycle, index=index, total_in_cycle=total_in_cycle, start_offset_ms=start_offset_ms, source_row=source_row)

    @staticmethod
    def _sample_repeat_count(action: Action) -> int:
        if action.action_type == ActionType.STOP_ANZ_CLICKER.value:
            return 1
        extra = random.randint(1, action.random_repeat) if action.random_repeat > 0 else 0
        return max(1, action.repeat + extra)

    @staticmethod
    def _sample_delay_ms(action: Action) -> int:
        extra = random.randint(0, action.random_delay_ms()) if action.random_delay_ms() > 0 else 0
        return max(0, action.delay_ms() + extra)

    def _planned_run_duration_ms(self, planned: PlannedActionRun) -> int:
        total = 0
        for index, delay in enumerate(planned.delays_ms):
            nested_duration = planned.nested_plans[index].total_estimated_ms if planned.nested_plans and index < len(planned.nested_plans) else 0
            total += delay + max(nested_duration, self._known_action_duration_ms(planned.action))
        return total

    @staticmethod
    def _planned_launch_only_blocking_duration_ms(planned: PlannedActionRun) -> int:
        return sum(planned.delays_ms) if planned.action.action_type == ActionType.LAUNCH_ANZ_SCRIPT.value else 0

    def _planned_background_duration_ms(self, planned: PlannedActionRun) -> int:
        if planned.action.action_type != ActionType.LAUNCH_ANZ_SCRIPT.value:
            return self._planned_run_duration_ms(planned)
        elapsed_before_launch_ms = 0
        finish_ms = 0
        for index, delay in enumerate(planned.delays_ms):
            elapsed_before_launch_ms += delay
            nested_duration = planned.nested_plans[index].total_estimated_ms if planned.nested_plans and index < len(planned.nested_plans) else 0
            finish_ms = max(finish_ms, elapsed_before_launch_ms + nested_duration)
        return finish_ms

    def _known_action_duration_ms(self, action: Action) -> int:
        if action.action_type == ActionType.ANIMATE_MOUSE.value:
            return input_controller.estimate_mouse_animation_duration_ms(self._estimated_mouse_distance(action))
        if action.action_type in {ActionType.WAIT_FOR_PICTURE.value, ActionType.AUTO_PICTURE_CLICKER.value}:
            return action.picture_wait_timeout_ms()
        if action.action_type == ActionType.WAIT_FOR_PIXEL_COLOR.value:
            return action.pixel_wait_timeout_ms()
        return 0

    def _start_parallel_runs(self, runs: list[PlannedActionRun]) -> list[threading.Thread]:
        started_threads: list[threading.Thread] = []
        for index, planned in enumerate(runs, start=1):
            thread = threading.Thread(
                target=self._run_parallel_action,
                args=(planned, index, len(runs)),
                daemon=True,
            )
            self._parallel_threads.append(thread)
            started_threads.append(thread)
            thread.start()
        return started_threads

    def _run_parallel_action(self, planned: PlannedActionRun, index: int, total: int) -> None:
        action = planned.action
        self._publish(f"Background {index}/{total}: {action.display_name()} [{planned.repeat_count} run(s)]")
        self._execute_planned_run(planned)

    def _execute_planned_run(self, planned: PlannedActionRun) -> bool:
        for index, delay_ms in enumerate(planned.delays_ms):
            if self._stop_event.is_set():
                return False
            if not self._wait_if_paused():
                return False
            if not self._sleep_interruptible(delay_ms):
                return False
            nested_plan = planned.nested_plans[index] if planned.nested_plans and index < len(planned.nested_plans) else None
            self._execute_action(planned.action, nested_plan)
        return True

    def _wait_if_paused(self) -> bool:
        while self._pause_event.is_set():
            if self._stop_event.is_set():
                return False
            time.sleep(0.05)
        return not self._stop_event.is_set()

    def _sleep_interruptible(self, delay_ms: int) -> bool:
        remaining = max(0, delay_ms) / 1000
        while remaining > 0:
            if self._stop_event.is_set():
                return False
            if not self._wait_if_paused():
                return False
            chunk = min(0.1, remaining)
            time.sleep(chunk)
            remaining -= chunk
        return not self._stop_event.is_set()

    def _start_progress_monitor(self, total_ms: int) -> None:
        self._progress_total_ms = max(0, int(total_ms))
        self._progress_elapsed_ms = 0
        self._progress_thread = threading.Thread(target=self._progress_loop, daemon=True)
        self._progress_thread.start()

    def _progress_loop(self) -> None:
        last_tick = time.monotonic()
        while not self._progress_done.is_set():
            time.sleep(0.2)
            if self._progress_done.is_set():
                break
            now = time.monotonic()
            delta_ms = int((now - last_tick) * 1000)
            last_tick = now
            if self._pause_event.is_set():
                continue
            self._progress_elapsed_ms += max(0, delta_ms)
            if self._progress_total_ms > 0:
                current = min(self._progress_elapsed_ms, max(0, self._progress_total_ms - 1))
                self._publish_progress(current, self._progress_total_ms)
            else:
                self._publish_progress(0, 0)

    def _finish_progress(self, completed: bool) -> None:
        self._progress_done.set()
        if completed:
            self._progress_elapsed_ms = self._progress_total_ms
        elif self._progress_total_ms > 0:
            self._progress_elapsed_ms = min(self._progress_elapsed_ms, max(0, self._progress_total_ms - 1))
        else:
            self._progress_elapsed_ms = 0
        self._publish_progress(self._progress_elapsed_ms, self._progress_total_ms)

    def _execute_action(self, action: Action, nested_plan: RuntimePlan | None = None) -> None:
        if not self._wait_if_paused():
            raise InterruptedError("Paused action stopped.")
        if action.action_type == ActionType.WAIT.value:
            return

        if action.action_type == ActionType.STOP_ANZ_CLICKER.value:
            self._publish("Stop Anz Clicker action executed.")
            self._stop_event.set()
            return

        if action.action_type == ActionType.ANIMATE_MOUSE.value:
            x, y = self._resolve_point(action)
            input_controller.animate_mouse_human(x, y, should_stop=self._stop_event.is_set)
            return

        if action.action_type == ActionType.MOVE_MOUSE.value:
            x, y = self._resolve_point(action)
            input_controller.set_position(x, y)
            return

        if action.action_type == ActionType.LEFT_CLICK.value:
            x, y = self._resolve_point(action)
            input_controller.set_position(x, y)
            input_controller.left_click()
            return

        if action.action_type == ActionType.RIGHT_CLICK.value:
            x, y = self._resolve_point(action)
            input_controller.set_position(x, y)
            input_controller.right_click()
            return

        if action.action_type == ActionType.TYPE_KEY.value:
            if not action.key:
                raise ValueError("Type Key action is missing a key.")
            input_controller.perform_key_tap(action.key)
            return

        if action.action_type == ActionType.PRESS_KEY.value:
            if not action.key:
                raise ValueError("Press Key action is missing a key.")
            input_controller.perform_key_hold(action.key)
            return

        if action.action_type == ActionType.RELEASE_KEY.value:
            if not action.key:
                raise ValueError("Release Key action is missing a key.")
            input_controller.perform_key_release(action.key)
            return

        if action.action_type == ActionType.PRESS_SPACEBAR.value:
            input_controller.key_press("space")
            return

        if action.action_type == ActionType.PRESS_SHIFT_SPACEBAR.value:
            input_controller.combo_press("shift", "space")
            return

        if action.action_type == ActionType.PRESS_ENTER.value:
            input_controller.key_press("enter")
            return

        if action.action_type == ActionType.CTRL_C.value:
            input_controller.combo_press("ctrl", "c")
            return

        if action.action_type == ActionType.CTRL_V.value:
            input_controller.combo_press("ctrl", "v")
            return

        if action.action_type == ActionType.PRESS_TAB.value:
            input_controller.key_press("tab")
            return

        if action.action_type == ActionType.PRESS_SHIFT_TAB.value:
            input_controller.perform_key_tap("shift+tab")
            return

        if action.action_type == ActionType.PRESS_BACKSPACE.value:
            input_controller.key_press("backspace")
            return

        if action.action_type == ActionType.ALT_TAB.value:
            input_controller.perform_key_tap("alt+tab")
            return

        if action.action_type == ActionType.SHIFT_CLICK.value:
            x, y = self._resolve_point(action)
            input_controller.set_position(x, y)
            input_controller.shift_click()
            return

        if action.action_type == ActionType.DOUBLE_CLICK.value:
            x, y = self._resolve_point(action)
            input_controller.set_position(x, y)
            input_controller.double_click()
            return

        if action.action_type == ActionType.MOUSE_DOWN.value:
            x, y = self._resolve_point(action)
            input_controller.set_position(x, y)
            input_controller.mouse_down()
            return

        if action.action_type == ActionType.MOUSE_UP.value:
            x, y = self._resolve_point(action)
            input_controller.set_position(x, y)
            input_controller.mouse_up()
            return

        if action.action_type == ActionType.LAUNCH_APP.value:
            if not action.launch_path.strip():
                raise ValueError("Launch App action is missing a file path or command.")
            input_controller.launch(
                path=action.launch_path,
                args=action.launch_args,
                verb=action.launch_verb,
                mode=action.launch_mode,
            )
            return

        if action.action_type == ActionType.LAUNCH_ANZ_SCRIPT.value:
            self._launch_nested_script(action, wait=False, plan=nested_plan)
            return

        if action.action_type == ActionType.LAUNCH_ANZ_SCRIPT_AND_WAIT.value:
            self._launch_nested_script(action, wait=True, plan=nested_plan)
            return

        if action.action_type == ActionType.WAIT_FOR_SCREEN_CHANGE.value:
            self._wait_for_screen_change(action)
            return

        if action.action_type == ActionType.WAIT_FOR_PIXEL_COLOR.value:
            self._wait_for_pixel_color(action)
            return

        if action.action_type == ActionType.WAIT_FOR_PICTURE.value:
            self._wait_for_picture(action)
            return

        if action.action_type == ActionType.WAIT_FOR_SCREEN_TEXT.value:
            self._wait_for_screen_text(action)
            return

        if action.action_type == ActionType.AUTO_PICTURE_CLICKER.value:
            self._auto_picture_clicker(action)
            return

        raise ValueError(f"Unsupported action type: {action.action_type}")

    def _launch_nested_script(self, action: Action, *, wait: bool, plan: RuntimePlan | None = None) -> None:
        plan = plan or self._plan_nested_script(action.launch_path)
        if wait:
            self._publish("Sequential actions running")
            if not self._run_plan_body(plan, wait_for_background=True):
                raise InterruptedError("Nested script stopped.")
            return

        thread = threading.Thread(target=self._run_nested_script_thread, args=(plan, Path(action.launch_path).name), daemon=True)
        self._parallel_threads.append(thread)
        thread.start()

    def _run_nested_script_thread(self, plan: RuntimePlan, name: str) -> None:
        self._publish("Background actions running")
        self._run_plan_body(plan, wait_for_background=True)

    def _plan_nested_script(self, script_path: str, script_stack: tuple[Path, ...] = ()) -> RuntimePlan:
        path = Path(script_path).resolve()
        if path in script_stack:
            chain = " -> ".join(item.name for item in (*script_stack, path))
            raise RuntimePlanError(f"Circular nested script reference detected: {chain}")
        nested_actions, nested_cycles = self._load_script_actions(str(path))
        return self._build_runtime_plan(nested_actions, nested_cycles, (*script_stack, path))

    @staticmethod
    def _format_duration(milliseconds: int) -> str:
        total_seconds = max(0, int(milliseconds) // 1000)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours}h {minutes}m {seconds}s"

    def _run_plan_body(self, plan: RuntimePlan, *, wait_for_background: bool) -> bool:
        child_threads: list[threading.Thread] = []
        if plan.initial_background_runs:
            child_threads.extend(self._start_parallel_runs(plan.initial_background_runs))

        for planned in plan.sequential_runs:
            if self._stop_event.is_set() or not self._wait_if_paused():
                return False
            if planned.action.start_as_background:
                child_threads.extend(self._start_parallel_runs([planned]))
                continue
            thread_count_before = len(self._parallel_threads)
            if not self._execute_planned_run(planned):
                return False
            child_threads.extend(self._parallel_threads[thread_count_before:])

        if wait_for_background:
            while not self._stop_event.is_set() and any(thread.is_alive() for thread in child_threads):
                if not self._wait_if_paused():
                    return False
                time.sleep(0.1)
        return not self._stop_event.is_set()

    def _load_script_actions(self, script_path: str) -> tuple[list[Action], int]:
        path = Path(script_path)
        if not path.exists():
            raise FileNotFoundError(f"Anz Clicker script not found: {script_path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            actions = [Action.from_dict(item) for item in payload]
            return actions, 1
        sequential = [Action.from_dict(item) for item in payload.get("sequential_actions", [])]
        background = [Action.from_dict(item) for item in payload.get("parallel_actions", [])]
        for nested_action in sequential:
            nested_action.execution_group = ExecutionGroup.SEQUENTIAL.value
        for nested_action in background:
            nested_action.execution_group = ExecutionGroup.PARALLEL.value
            nested_action.start_as_background = False
        cycles = max(1, int(payload.get("sequential_repeat_count", 1) or 1))
        random_cycles = max(0, int(payload.get("sequential_random_repeat_count", 0) or 0))
        if random_cycles:
            cycles += random.randint(1, random_cycles)
        return sequential + background, cycles

    def _resolve_point(self, action: Action) -> tuple[int, int]:
        if action.position_mode == PositionMode.AREA.value:
            if not action.area or not action.area.is_valid():
                raise ValueError("A valid area is required for area-based actions.")
            return input_controller.point_in_area(action.area)
        if action.position_mode == PositionMode.COORDINATES.value:
            if action.x is None or action.y is None:
                raise ValueError("Coordinate-based action is missing X or Y.")
            return input_controller.resolve_coordinate_point(action.x, action.y, action.random_x, action.random_y)
        return input_controller.current_position()

    def _wait_for_screen_change(self, action: Action) -> None:
        if not action.area or not action.area.is_valid():
            raise ValueError("Wait for Screen Change requires a capture area.")

        baseline = screen_tools.capture_area(action.area)
        minimum = max(0.0, action.screen_change_min_percent)
        maximum = max(0.0, action.screen_change_max_percent)
        interval = action.screen_check_interval_ms() / 1000

        while not self._stop_event.is_set():
            if not self._wait_if_paused():
                raise InterruptedError("Screen change wait stopped.")
            time.sleep(interval)
            current = screen_tools.capture_area(action.area)
            percent = screen_tools.changed_percent(baseline, current)
            if percent >= minimum and (maximum == 0 or percent <= maximum):
                self._publish(f"Screen changed by {percent:.2f}%")
                return

    def _wait_for_pixel_color(self, action: Action) -> None:
        if action.pixel_x is None or action.pixel_y is None:
            raise ValueError("Wait for Pixel Color requires X and Y coordinates.")

        expected = (action.pixel_r, action.pixel_g, action.pixel_b)
        timeout_ms = action.pixel_wait_timeout_ms()
        started = time.time()
        while not self._stop_event.is_set():
            if not self._wait_if_paused():
                raise InterruptedError("Pixel wait stopped.")
            actual = screen_tools.capture_screen_pixel(action.pixel_x, action.pixel_y)
            if screen_tools.pixel_matches(actual, expected, action.pixel_tolerance_percent):
                self._publish(f"Pixel matched at {action.pixel_x}, {action.pixel_y}")
                return
            if timeout_ms > 0 and (time.time() - started) * 1000 >= timeout_ms:
                raise TimeoutError("Wait for Pixel Color timed out.")
            time.sleep(0.1)

    def _wait_for_picture(self, action: Action) -> tuple[int, int, int, int]:
        if not action.picture_area or not action.picture_area.is_valid():
            raise ValueError("Wait for Picture requires a valid search area.")
        if not action.picture_path:
            raise ValueError("Wait for Picture requires a picture file.")

        timeout_ms = action.picture_wait_timeout_ms()
        started = time.time()
        while not self._stop_event.is_set():
            if not self._wait_if_paused():
                raise InterruptedError("Picture search stopped.")
            match = screen_tools.find_picture(
                action.picture_area,
                action.picture_path,
                action.picture_tolerance_percent,
                should_stop=self._stop_event.is_set,
            )
            if self._stop_event.is_set():
                raise InterruptedError("Picture search stopped.")
            if match:
                left, top, width, height = match
                self._publish(f"Picture found at {left}, {top} ({width}x{height})")
                return match
            if timeout_ms > 0 and (time.time() - started) * 1000 >= timeout_ms:
                raise TimeoutError("Wait for Picture timed out.")
            time.sleep(0.2)
        raise InterruptedError("Picture search stopped.")

    def _wait_for_screen_text(self, action: Action) -> None:
        if not action.screen_text_area or not action.screen_text_area.is_valid():
            raise ValueError("Wait for Screen Text requires a valid screen area.")
        pattern = action.screen_text_pattern.strip()
        if not pattern:
            raise ValueError("Wait for Screen Text requires text or a regular expression to match.")
        matcher = re.compile(pattern, re.IGNORECASE) if action.screen_text_is_regex else None

        while not self._stop_event.is_set():
            if not self._wait_if_paused():
                raise InterruptedError("Screen text wait stopped.")
            text = screen_tools.read_text_in_area(action.screen_text_area)
            if matcher:
                if matcher.search(text):
                    self._publish("Screen text matched.")
                    return
            elif pattern.lower() in text.lower():
                self._publish("Screen text matched.")
                return
            time.sleep(0.25)
        raise InterruptedError("Screen text wait stopped.")

    def _auto_picture_clicker(self, action: Action) -> None:
        left, top, width, height = self._wait_for_picture(action)
        if action.picture_found_random_point:
            target_x = left + random.randint(0, width - 1)
            target_y = top + random.randint(0, height - 1)
        else:
            target_x = left + width // 2
            target_y = top + height // 2
        if action.picture_found_animate:
            input_controller.animate_mouse_human(target_x, target_y, should_stop=self._stop_event.is_set)
        else:
            input_controller.set_position(target_x, target_y)
        if self._stop_event.is_set():
            return
        input_controller.left_click()

    def _estimated_mouse_distance(self, action: Action) -> float:
        if action.position_mode == PositionMode.COORDINATES.value and action.x is not None and action.y is not None:
            try:
                current_x, current_y = input_controller.current_position()
                return math.dist((current_x, current_y), (action.x, action.y))
            except Exception:
                return 500.0
        if action.position_mode == PositionMode.AREA.value and action.area and action.area.is_valid():
            normalized = action.area.normalized()
            return max(120.0, math.hypot(normalized.width, normalized.height) / 2)
        return 500.0

    def _publish(self, text: str) -> None:
        if self._status_callback:
            self._status_callback(text)

    def _publish_progress(self, current: int, total: int) -> None:
        self._publish(f"{self.PROGRESS_PREFIX}{current}/{total}")

    def _publish_active_sequential(self, row: int) -> None:
        self._publish(f"{self.ACTIVE_SEQUENTIAL_PREFIX}{row}")

    def _apply_settings(self) -> None:
        screen_tools.configure_ocr(Path(__file__).resolve().parent.parent)
        input_controller.configure_input_timing(
            mouse_animation_speed=self.settings.mouse_animation_speed,
            enhanced_humanlike_mouse=self.settings.enhanced_humanlike_mouse,
            mouse_click_delay_min_ms=self.settings.mouse_click_delay_min_ms,
            mouse_click_delay_max_ms=self.settings.mouse_click_delay_max_ms,
            key_press_delay_min_ms=self.settings.key_press_delay_min_ms,
            key_press_delay_max_ms=self.settings.key_press_delay_max_ms,
        )
