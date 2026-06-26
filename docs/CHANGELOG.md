# Changelog

All notable Anz Clicker changes are grouped by version. The current source version is read from `src/anz_clicker_qt/version.py`.

## Unreleased

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
