# Windows Installer Packaging

Install Inno Setup 6, merge the intended changes into a clean `main` branch,
then double-click `Create Update.cmd` in the repository root. The launcher
keeps the result visible after the build completes.

The equivalent interactive command is:

```powershell
powershell -ExecutionPolicy Bypass -File packaging/create_release.ps1
```

The script prompts for the new semantic version, updates `version.py`, rolls
the Unreleased changelog entries into the new version, and invokes the
canonical release build. If the build fails, the version and changelog edits
are restored automatically.

For automation, provide the version directly:

```powershell
powershell -ExecutionPolicy Bypass -File packaging/create_release.ps1 -Version 1.4.0
```

The low-level build command remains available when the version and changelog
have already been prepared:

```powershell
powershell -ExecutionPolicy Bypass -File packaging/build_release.ps1
```

Inno Setup requests that commercial users purchase a commercial license. Treat
locally compiled installers as internal/test builds until the project's
distribution licensing is in place.

The build:

1. Confirms that Anz Clicker is not running, because Windows locks loaded packaged files.
2. Reads the version from `src/anz_clicker_qt/version.py`.
3. Runs `tests/smoke_test.py`.
4. Builds with the canonical PyInstaller spec.
5. Stages the tested application in `dist/Anz Clicker/`.
6. Compiles `release/Anz Clicker Setup v<version>.exe` with Inno Setup.
7. Prints the installer SHA-256 checksum.

Close every Anz Clicker window before starting a release build. The builder
retries cleanup for temporary antivirus or indexing locks, but it cannot
replace `.pyd` or `.dll` files loaded by a running application.

Use `-SkipInstaller` to test and stage the PyInstaller application on a machine
without Inno Setup. This does not create a distributable release.

Installed builds keep mutable files outside the installation directory:

- `%LOCALAPPDATA%\Anz Clicker\scripts`
- `%LOCALAPPDATA%\Anz Clicker\user-data`

The installer neither creates nor removes those folders, so upgrading or
uninstalling the application does not erase user scripts or customization.
