# Anz Clicker Developer Wiki

This document is the source of truth for project conventions that should be reused when changing Anz Clicker. The goal is to keep future changes consistent, modular, and easier to review.

## Project Shape

- `src/anz_clicker_qt.py` is the Qt entry point.
- `src/anz_clicker_qt/main_window.py` owns the main window, top-level layout, script commands, runner wiring, and high-level UI coordination.
- `src/anz_clicker_qt/action_editor.py` owns `ActionEditorDialog`, including action-specific editor panels, field loading, validation, and saving editor values back into `Action` objects.
- `src/anz_clicker_qt/dialogs.py` owns standalone dialogs such as Settings and Edit Action Order.
- `src/anz_clicker_qt/widgets.py` owns reusable widgets, table models/views, shared action editor controls, help buttons, and screen-area selection helpers.
- `src/anz_clicker_qt/constants.py` owns shared UI/action constants used across Qt modules.
- `src/anz_clicker_qt/theme.py` owns global light/dark Qt stylesheet generation.
- `src/anz_clicker_qt/icons.py` owns icon/resource lookup for source runs and PyInstaller bundles.
- `src/actions.py` owns serializable action data, action types, execution groups, position modes, and screen-area data.
- `src/runner.py` owns execution, pause/stop behavior, sampled runtime planning, and time-based progress.
- `src/input_controller.py` owns mouse/keyboard input and human-like timing behavior.
- `src/screen_tools.py` owns screenshots, picture matching, color checks, screen-change checks, and OCR helpers.
- `src/app_settings.py` owns persistent app-level settings.
- `src/preset_store.py` owns default actions, custom actions, action order, and visibility.
- `tests/smoke_test.py` is the quick regression suite for serialization/settings/preset behavior.

## Core Design Rules

- Prefer reusable widgets/helpers over re-implementing the same UI fields in each action panel.
- Keep saved action data in `actions.py`; do not serialize transient runtime-only state.
- Keep app-level preferences in `AppSettings`; do not mix them into script JSON unless the setting is script-specific.
- Keep action defaults/custom actions in `PresetStore`; do not hard-code user-editable defaults in the UI layer.
- Keep PyInstaller resource access behind `resource_path()`.
- Keep user settings, presets, captures, and license files under `user-data/`; keep saved scripts under `scripts/`.
- Use the shared helpers in `src/anz_clicker_qt/paths.py` instead of constructing persistent-data paths ad hoc.
- Keep shared constants in `constants.py`; avoid duplicating action groups, app labels, preset prefixes, or launch modes in multiple modules.
- Keep visual styling in `theme.py` and icons in `icons/`; avoid one-off inline colors/icons unless there is a clear reason.
- Any popup window should open relative to the main app/editor window, not at absolute screen origin.
- Any long-running action must respect stop and pause as much as possible.

## Shared Action Editor Fields

Every action supports the same general section at the top of the Action Editor:

- Delay: minutes, seconds, milliseconds
- Random delay: minutes, seconds, milliseconds
- Repeat count
- Random repeat count
- Comment

Use `GeneralActionSettings` from `anz_clicker_qt/widgets.py` for this section.

When adding or changing actions:

- Do not recreate delay/repeat/comment widgets manually in action-specific panels.
- Create unique fields only below the shared general section.
- Load defaults through `GeneralActionSettings.load_from_action(action)`.
- Save values through `GeneralActionSettings.apply_to_action(action)`.
- Use `plain_number_field()` for numeric fields that should not show spinner arrows.
- Use `time_row()` when a UI row needs minutes/seconds/milliseconds inputs.

The editor currently binds shared fields back to legacy names in `ActionEditorDialog._bind_general_settings_fields()`. That bridge keeps older action-specific code working while the shared widget becomes the canonical implementation.

## Action Editor Organization

`ActionEditorDialog` lives in `anz_clicker_qt/action_editor.py`.

When changing the editor:

- Keep the constructor orchestration small; put setup work in focused helpers such as `_init_state()`, `_build_action_header()`, `_create_reusable_fields()`, `_configure_reusable_fields()`, `_load_reusable_field_values()`, and `_add_footer()`.
- Keep action-specific UI in panel builders such as `_build_mouse_panel()`, `_build_picture_panel()`, and `_build_screen_text_panel()`.
- Keep saving split into clear steps: parse text fields, build the base action with `_action_from_fields()`, apply location/area fields with `_apply_location_fields()`, apply simple key overrides, validate, then accept.
- Do not put main-window script behavior in the action editor. The editor should return a configured `Action`; `MainWindow` decides where that action is inserted or saved.
- After changing editor behavior, construct every built-in action editor offscreen and run `python tests/smoke_test.py`.

## Help Question-Mark Buttons

Use the reusable help-button pattern for field explanations.

- Use `make_help_button(parent, title, message)` from `anz_clicker_qt/widgets.py` for a standalone `?` button.
- Use `make_help_label(parent, text, message)` from `anz_clicker_qt/widgets.py` when a label and `?` should appear together.
- Tooltip text should be `What does this do?`.
- Use short, user-facing explanations. These messages are for clarity, not internal implementation details.
- Prefer this helper for new settings, action fields, tolerance/deviation fields, and any option whose behavior is not obvious.

## Screen Area Selection

Use the shared screen-area picker flow for all features that select or view a screen region.

- Use `choose_screen_area(parent, initial_area, auto_close)` from `anz_clicker_qt/widgets.py`.
- The picker should hide/minimize the relevant app/editor windows so users can select the real screen area underneath.
- Selection mode should allow click-and-drag to define an area.
- View/edit mode should show the existing area, allow moving/resizing it, and save only when the user confirms.
- Store selected areas as `ScreenArea` instances.
- Before calling area methods, be defensive if older JSON produced a `dict`; normalize through `ScreenArea.from_dict()` where needed.

Use this shared flow for random mouse areas, picture search areas, screen-change areas, and OCR/text-search areas.

For mouse actions, randomizing a target location should use selected areas rather than separate Random X/Y coordinate offsets. The editor intentionally clears legacy `random_x` and `random_y` values when coordinate-based actions are saved.

## Adding A New Action

Use this checklist when adding an action type:

1. Add the new value to `ActionType` in `actions.py`.
2. Add any new persisted fields to `Action`.
3. Update `Action.to_dict()` and `Action.from_dict()` only if the field is not already covered.
4. Add a default/preset entry path through `PresetStore` if the action should appear in the action list.
5. Add UI-specific constants in `main_window.py` only when needed, such as position-capable actions.
6. Add only the unique panel fields in `ActionEditorDialog`; reuse `GeneralActionSettings` for the general section.
7. Add validation in `ActionEditorDialog._validate_action()` for required fields.
8. Add execution logic in `runner.py`.
9. Add table labels in `widgets.py` if the Target/Delay/Repeat/Notes display needs special handling.
10. Add screen, OCR, picture, or input helpers to `screen_tools.py` or `input_controller.py`, not directly in the UI.
11. Update this wiki if the action introduces a reusable pattern.
12. Run `python tests/smoke_test.py`.

`Launch Anz Clicker Script` and `Launch Anz Clicker Script and Wait` reuse the Launch-style path field but must point to an Anz Clicker JSON script. The non-wait action starts the nested script as a background timeline and immediately lets the parent sequence continue. The wait action runs the nested script as a nested sequence and blocks the parent sequence until the nested script's sequential and background work is finished.

`Stop Anz Clicker` is a global stop action. It may use delay/random delay/comment fields, but it must not expose repeat controls and should always save/execute with repeat `1` and random repeat `0`. Execution should set the runner's shared stop event so parent, nested, sequential, and background execution all stop.

## Runtime Planning And Progress

Progress is time-based, not action-count-based.

- `runner.py` builds a sampled runtime plan at script start.
- Random sequence repeats, action repeats, and random delays are resolved once into that plan.
- Execution consumes the sampled plan; do not call random delay/repeat resolution independently during execution.
- Background actions run as parallel timelines.
- Sequential actions marked `Start Action as Background Action` begin a background timeline when the sequential runner reaches them.
- `Launch Anz Clicker Script` should be planned like a background timeline that starts when the parent sequence reaches that action.
- `Launch Anz Clicker Script and Wait` should add the nested script's estimated duration to the parent sequential timeline.
- Nested script actions should carry their sampled nested runtime plan into execution so random delays/repeats match the estimate.
- Total estimated duration is the longest timeline.
- Pause should freeze progress time and resume from the same point.
- Unknown-duration waits use configured delay/max wait where possible and should hold below completion until the action finishes.

## Settings

Use `AppSettings` for persistent application preferences:

- Mouse animation speed
- Enhanced humanlike animated mouse movement
- Mouse click down/up random delay
- Key press down/up random delay
- Default script folder
- Remember last window position/size
- Start/pause keybinds

When adding settings:

- Add fields and defaults in `app_settings.py`.
- Normalize values in `AppSettings.normalize()`.
- Load/save through `AppSettings.load()` and `AppSettings.save()`.
- Add UI in `SettingsDialog`.
- Apply settings to `ActionRunner` and `input_controller` if they affect execution.
- Add smoke-test coverage if the setting needs serialization safety.

Enhanced humanlike mouse movement is a global Settings toggle that applies only to explicit animated movement paths, such as `Animate Mouse` and Auto Picture Clicker when `Animate mouse to picture` is enabled. Keep ordinary click/move actions direct unless a future user-facing requirement changes that behavior. Enhanced movement should be distance-weighted: short moves are usually direct and quick, long moves may vary between direct, subtle, arced, and overshoot/correction profiles. Avoid heavy continuous jitter. Animated mouse movement is serialized through the input controller so two animated actions cannot fight over the cursor at the same time. Overshoots and corrections should always be smoothed through short path segments, not applied as instant cursor jumps.

Animated movement duration is controlled globally by Settings, not by an action-specific Movement Time field. `input_controller.py` scores duration from cursor travel distance, applies distance-scaled random timing, then applies the Settings speed factor. Speed `5` is the standard 1x timing, speed `10` is about 3x faster, and speed `1` is about one-third speed.

## Versioning

- The source of truth for the app version is `src/anz_clicker_qt/version.py`.
- UI code should import `APP_VERSION` from `anz_clicker_qt.constants`, which re-exports the version for existing callers.
- Update `docs/CHANGELOG.md` whenever changing `APP_VERSION`.
- Use semantic versioning loosely: patch for bug fixes, minor for user-facing features, and major only for breaking workflow or storage changes.
- Packaging scripts read `APP_VERSION` so installer names stay consistent.

## Icons And Theme

- Static icons live under `assets/icons/themes/dark/` and `assets/icons/themes/light/`.
- Load icons through `app_icon(name, dark=...)`.
- Do not hard-code paths to icon files in UI code.
- Theme-aware UI should request the current theme variant when icons are refreshed.
- Global colors and widget states belong in `build_stylesheet()` in `anz_clicker_qt/theme.py`.
- If Qt stylesheet backgrounds bleed past rounded corners, prefer a focused custom-painted widget surface over stacking multiple rounded stylesheet backgrounds. `QueuePane` paints its own rounded card for this reason.
- Disabled buttons should be visibly lower opacity/contrast than enabled buttons.
- Light and dark modes should both be checked after adding widgets or object names.

## Script Save/Load Behavior

- New scripts start empty.
- Save Script writes top-level metadata, both action panes, and sequence repeat settings to JSON.
- Save As always prompts for a new JSON path, writes a copy, and makes the new path the active script. `Ctrl+Shift+S` invokes Save As.
- Load Script restores both panes and sequence repeat settings.
- Load Script must validate the top-level JSON shape, action-lane types, and every action type before replacing the current document. Unrelated JSON must produce a user-facing load error.
- The current script name should appear in the window title/header.
- Unsaved changes should prompt before New Script, Load Script, or close.
- The default folder comes from `AppSettings.default_script_folder`.
- Script metadata lives under the top-level `metadata` key and should include `created_at`, `modified_at`, `app_version`, and `name`.
- Legacy scripts without metadata should be backfilled with the current timestamp and current `APP_VERSION` when loaded, then saved with metadata next time.

## Custom Actions

- `Save as Custom Action` must confirm before overwriting an existing custom action with the same name.
- Custom actions can be deleted from `Edit Action Order`.
- Built-in/default actions must not be deletable from `Edit Action Order`; they can only be reordered or hidden.
- Custom-action deletions from `Edit Action Order` should commit only when the dialog is saved.
- Use `PresetStore.delete_custom_action()` for custom deletion so the custom action, action catalog entry, and hidden entry stay in sync.

## OCR And Tesseract

Wait-for-screen-text uses OCR through `screen_tools.py`.

- Prefer bundled `vendor/tesseract/tesseract.exe` during source runs and packaged `tesseract/tesseract.exe` in releases.
- Keep OCR temp files under the app/captures area, not arbitrary system temp paths.
- OCR text matching should support plain string and regular expression modes.
- OCR-related packaging changes belong in `packaging/Anz Clicker.spec`.

## Testing And Packaging

Run the smoke test after refactors:

```powershell
python tests/smoke_test.py
```

Useful import check:

```powershell
python -c "import sys; sys.path.insert(0, 'src'); import anz_clicker_qt.widgets, anz_clicker_qt.main_window, anz_clicker_qt.app; print('imports ok')"
```

Packaging should use the single canonical spec:

```powershell
pyinstaller "packaging/Anz Clicker.spec"
```

Do not add new duplicate spec files. Update `packaging/Anz Clicker.spec` when bundled assets change.

Official Windows installers should be built with:

```powershell
powershell -ExecutionPolicy Bypass -File packaging/build_release.ps1
```

Do not commit generated `dist/`, `release/`, or `build/` output. Attach the
generated setup EXE to GitHub Releases. Installed program files belong under
`Program Files`; scripts and user-owned configuration belong under
`%LOCALAPPDATA%\Anz Clicker` and must never be deleted by normal upgrades or
uninstall operations.

### Production Release Checklist

- Run the complete smoke suite and launch-test the frozen executable.
- Build and hash the Windows installer.
- Obtain and configure a trusted Windows code-signing certificate before public production distribution.
- Sign both the application executable and installer, then verify their signatures.
- Confirm upgrades preserve `%LOCALAPPDATA%\Anz Clicker\scripts` and `user-data`.

## Future Refactor Targets

- Continue moving reusable dialog/widget code from `main_window.py` into `widgets.py` or focused dialog modules.
- Consider extracting action-specific editor panels into separate classes once the action list grows further.
- Consider extracting action-specific panel builders from `ActionEditorDialog` into smaller panel classes once the action list grows further.
- Add more smoke tests for runtime-plan sampling and script save/load behavior.
