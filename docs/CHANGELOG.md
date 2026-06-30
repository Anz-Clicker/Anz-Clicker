# Changelog

All notable Anz Clicker changes are grouped by version. The current source version is read from `src/anz_clicker_qt/version.py`.

## Unreleased

- Improved long-list drag reordering by adding edge auto-scroll and wheel-scroll support while dragging actions in the main queues and Edit Action Order.
- Tuned drag scrolling to move at a controlled pace and route mouse-wheel events to the active drag list while reordering.
- Replaced native drag loops with app-managed drag reordering so wheel scrolling works while dragging in action queues and Edit Action Order.
- Re-anchored drag insertion indicators after list scrolling so the placement line follows the current viewport while reordering.
- Highlighted Sequential/Background tabs while dragging actions over a valid destination tab.
- Stabilized the bottom run status layout by using lane-level running messages and fixed-width status metrics.
- Highlighted the active sequential action row while scripts run, and disabled user row selection/hover highlights during execution.
- Tightened bottom Run Time and Progress label spacing so metric values read more clearly while staying fixed in place.
- Grouped the bottom progress bar directly beside the Progress time text.

## 1.5.0 - 2026-06-28

- Began the v1.5 UI overhaul with a more compact workspace: run controls moved into the header, status/progress moved to a bottom bar, the right sidebar was removed from the active layout, action queue controls were simplified, and empty queues now show a guided empty state.
- Moved Start/Pause keybind editing into Settings, added duplicate-keybind validation, kept run button keybind labels synchronized, and cleaned up status/header text backgrounds.
- Tightened the v1.5 workspace width, narrowed and refined the sidebar buttons, and attached the Sequential/Background tabs visually to the action pane.
- Further narrowed the sidebar, inset the action tabs from the rounded pane corner, and refreshed Add/Edit Action dialogs with cleaner section cards and checkmark-style checkbox indicators.
- Polished the v1.5 workspace with immediate Settings theme preview, a slightly wider minimum window, tighter action-editor spacing, and a redesigned Tutorial window using matching section cards.
- Tightened the Tutorial window, cleaned up action-tab ghost outlines, and restyled action-type dropdown popups with the modern list and scrollbar treatment.
- Prevented Edit Default Actions from inheriting the currently selected queue action, and redesigned Settings into reusable grouped cards for timing, storage, keybinds, and behavior.
- Redesigned Edit Action Order with multi-selection, drag reordering, modern list styling, shared dialog Save-button styling, and matching scrollbar treatment.
- Fixed Edit Action Order drag drops so actions insert between rows instead of replacing rows, enabled auto-scroll while dragging, and tightened Settings dialog spacing.
- Replaced Settings and Tutorial placeholder section markers with theme-aware SVG icons from the shared icon palette.
- Replaced remaining placeholder UI glyphs with themed icons for the empty action queue and status bar, removed Settings icon outlines, and removed an unused legacy right-panel layout helper.

## 1.4.3 - 2026-06-26

- Brought Anz Clicker to the foreground when it reopens after an update, then shows the update-complete confirmation on top.

## 1.4.2 - 2026-06-26

- Changed update installs to open the standard interactive installer finish screen, allowing users to confirm completion and launch Anz Clicker from the installer checkbox.
- Removed the hidden relaunch watcher path because it could fail to reopen the app after installer completion on some systems.

## 1.4.1 - 2026-06-26

- Added a more robust updater relaunch watcher that reopens Anz Clicker after the installer finishes instead of relying on installer restart flags.
- Made action-queue drag tooltips row-specific so they only appear when hovering actual actions.

## 1.4.0 - 2026-06-26

- Added explicit updater relaunch handling so update installs reopen Anz Clicker and show a one-time success confirmation.
- Added a Start Menu shortcut option to the installer.
- Added multi-action selection in queue panes, including bulk delete, duplicate, move, transfer, drag-and-drop, and Ctrl+A selection.
- Moved Light/Dark mode selection into Settings and made theme preference persistent.
- Replaced the Settings theme checkbox with a clearer mode toggle button, improved checkbox contrast in light mode, and removed the sidebar collapse mode.

## 1.3.3 - 2026-06-26

- Added optional post-build release metadata commit and push automation to `create_release.ps1`.

## 1.3.2 - 2026-06-26

- Fixed update-check installer detection so GitHub release assets with dots, dashes, or underscores in the installer filename are recognized.

## 1.3.1 - 2026-06-26

- Added a root-level `Create Update.cmd` launcher for starting the interactive release builder by double-clicking.
- Added an interactive release creator that validates a clean `main` branch, updates the version and changelog, runs the canonical build, and restores release metadata automatically if packaging fails.
- Added a Settings update checker backed by the latest published GitHub release.
- Added in-app installer download progress, cancellation, SHA-256 verification when supplied by GitHub, and automatic installer handoff with application restart.
- Moved the version label to the Settings header.
- Strengthened selected-row hover contrast and added drag ghosting plus a full-width insertion marker for queue reordering.
- Fixed queue drag initiation by advertising draggable/drop-enabled model rows, added a full-row drag preview, and changed action hover feedback from individual cells to the complete row.
- Added drag-and-drop action reordering within queues and transfers through the Sequential/Background tab headers.
- Locked script editing while execution is running while retaining Stop and Pause controls.
- Changed zero-valued action number fields to show `0` as placeholder text for easier replacement.
- Added an application disclaimer covering anti-cheat detection and use-at-your-own-risk behavior.
- Clarified and normalized `Start Action as Background Action` so it has no effect on actions already in the Background Actions lane.
- Added code signing to the production-release checklist.
- Replaced portable ZIP releases with a Windows installer built through Inno Setup 6.
- Moved installed-build scripts to `%LOCALAPPDATA%\Anz Clicker\scripts`.
- Moved installed-build settings, custom actions, captures, and future license files to `%LOCALAPPDATA%\Anz Clicker\user-data`.
- Added non-destructive migration for legacy portable scripts, settings, presets, captures, and `.anzlicense` files.
- Kept source-code development data repo-local for straightforward testing.
- Added a staged application-only build mode for validating PyInstaller output before compiling an installer.

## 1.2.0 - 2026-06-08

- Added `Launch Anz Clicker Script` and `Launch Anz Clicker Script and Wait` actions for running nested Anz Clicker JSON scripts.
- Added nested-script runtime planning so launched scripts are included in time-based progress estimates.
- Changed `Run Time` to track active runtime only, excluding time spent paused.
- Standardized unsaved-change prompts to `Save / Discard / Cancel`, including brand-new unsaved scripts.
- Removed per-action `Movement Time` from `Animate Mouse`.
- Changed animated mouse duration to use distance scoring, distance-scaled randomization, and the global Settings mouse-speed multiplier.
- Added `Stop Anz Clicker`, an action that stops the entire currently running script, including nested script execution.
- Added top-level script metadata with creation time, modified time, script name, and app version.
- Added `Save As` with `Ctrl+Shift+S` for duplicating scripts and continuing work from the new file.
- Added strict script JSON validation so unrelated or malformed JSON files are rejected before replacing the current script.
- Improved Background Actions tab behavior when loading background-only scripts.
- Kept action transfer between Sequential and Background tabs on the current tab for easier bulk moves.

## 1.1.0 - Portable Qt Release

- Rebuilt the app as the modern PySide6/Qt interface with dark/light mode styling.
- Added portable PyInstaller packaging through `Anz Clicker Portable.spec`.
- Added static theme-aware icons, now stored under `assets/icons/themes/dark` and `assets/icons/themes/light`.
- Added Settings persistence for mouse animation speed, enhanced humanlike movement, click/key press timing, default script folder, keybinds, and window position/size.
- Added a reusable Settings panel with reset-to-defaults support.
- Added custom action presets, custom action overwrite confirmation, custom-action deletion, default-action editing, and action order/hide controls.
- Added Sequential Actions and Background Actions tabs with visible action counts.
- Added sequence repeat and random sequence repeat controls.
- Added time-based progress reporting instead of action-count progress.
- Added pause/unpause support for sequential and background action execution.
- Added support for deleting selected actions with `Delete` or `Backspace`.
- Added script save/load behavior with remembered current script path and dirty-state indicators.
- Added a custom Tutorial window with fuller workflow explanations.
- Added reusable question-mark help buttons for confusing settings and action fields.

## 1.0.0 - Core Automation Prototype

- Added the first Anz Clicker action queue foundation.
- Added core mouse actions: move, animate, left click, right click, double click, shift-click, mouse down, and mouse up.
- Added keyboard actions: type key, press key, release key, spacebar, shifted spacebar, enter, tab, shifted tab, backspace, `Ctrl+C`, `Ctrl+V`, and `Alt+Tab`.
- Added `Launch App`, `Wait`, `Wait for Screen Change`, `Wait for Pixel Color`, `Wait for Picture`, `Wait for Screen Text`, and `Auto Picture Clicker`.
- Added shared action editor general fields for delay, random delay, repeat count, random repeat count, enabled state, and comments.
- Added screen area selection and view/edit overlays for random mouse areas and screen-search actions.
- Added coordinate capture with `F6` inside mouse-action editors.
- Added image matching and OCR support through bundled Tesseract integration.
- Added script serialization to JSON.
- Added smoke tests for settings, action serialization, script payloads, presets, nested scripts, and mouse movement behavior.

## 0.1.0 - Legacy Tkinter Prototype

- Built the original Tkinter proof-of-concept inspired by MurGee-style action queues.
- Proved out editable action rows, basic script saving/loading, and early mouse/keyboard execution.
- Superseded by the Qt rewrite.
