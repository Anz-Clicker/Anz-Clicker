# Anz Clicker

Windows desktop automation tool for building and running queued mouse, keyboard, screen-wait, image, and OCR actions.

For developer conventions and reusable project patterns, see [docs/ANZ_CLICKER_WIKI.md](docs/ANZ_CLICKER_WIKI.md).

Version history is tracked in [docs/CHANGELOG.md](docs/CHANGELOG.md). The current app version is defined in `src/anz_clicker_qt/version.py`.

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
python src/anz_clicker_qt.py
```

Install development dependencies with:

```powershell
python -m pip install -r docs/requirements.txt
```

## Windows Installer

Install [Inno Setup 6](https://jrsoftware.org/isdl.php), merge the release into
a clean `main` branch, then double-click:

```text
Create Update.cmd
```

The launcher keeps its window open so the completed installer path or any
errors remain visible. The equivalent PowerShell command is:

```powershell
powershell -ExecutionPolicy Bypass -File packaging/create_release.ps1
```

Enter the new version when prompted. The script updates the application
version and changelog, runs tests, packages the application, and creates the
installer. The tested PyInstaller application is staged under
`dist/Anz Clicker/`, and the single distributable installer is created under
`release/`. Attach the setup EXE to the matching GitHub Release.

Installed program files live under `Program Files`. User-created scripts live
in `%LOCALAPPDATA%\Anz Clicker\scripts`; settings, custom actions, captures, and
future license files live in `%LOCALAPPDATA%\Anz Clicker\user-data`. Updates
and uninstall/reinstall operations do not replace those user-owned files.

## Repository Layout

```text
assets/       Branding and theme icons
config/       Example configuration and preset files
docs/         Changelog, developer wiki, requirements, and release notes
packaging/    Canonical PyInstaller specification and release builder
scripts/      Default user script workspace
src/          Application source code
tests/        Smoke and regression tests
user-data/    Ignored local settings, presets, captures, and licenses
vendor/       Bundled third-party runtimes such as Tesseract
```

## Notes

- Mouse and keyboard input is sent with Windows APIs via `ctypes`.
- Shared editor fields, helper popups, screen-area selection, theme/icons, settings, and runner behavior are documented in the developer wiki.
