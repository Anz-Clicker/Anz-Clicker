# Anz Clicker

Windows desktop automation tool for building and running queued mouse, keyboard, screen-wait, image, and OCR actions.

For developer conventions and reusable project patterns, see [docs/ANZ_CLICKER_WIKI.md](docs/ANZ_CLICKER_WIKI.md).

Version history is tracked in [CHANGELOG.md](CHANGELOG.md). The current app version is defined in `anz_clicker_qt/version.py`.

## Features in this prototype

- Add, edit, delete, and reorder actions
- Save and load action sequences as JSON
- Run queued actions on a background thread
- Leave X/Y blank to use the live cursor position at execution time
- Capture coordinates with `F6` inside mouse-action editors
- Select an on-screen area and click a random point inside it
- Per-action delay with minutes / seconds / milliseconds plus random delay
- Repeat count plus random repeat expansion
- Action types included:
  - Move Mouse
  - Left Click
  - Right Click
  - Wait
  - Key Press
  - Launch App
  - Wait for Screen Change
- Optional random offset ranges for coordinate-based actions
- Optional smooth mouse animation for mouse actions

## Run

```powershell
python anz_clicker_qt.py
```

## Portable Build

The repository's `portable/` directory contains a ready-to-run Windows build.
Open that directory and double-click `Anz Clicker.exe`; Python does not need to
be installed.

For published versions, the same portable directory should also be compressed
and attached to the corresponding GitHub Release.

## Notes

- Mouse and keyboard input is sent with Windows APIs via `ctypes`.
- Shared editor fields, helper popups, screen-area selection, theme/icons, settings, and runner behavior are documented in the developer wiki.
