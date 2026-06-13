# Windows Installer Packaging

Install Inno Setup 6, then run the canonical release build from the repository
root:

```powershell
powershell -ExecutionPolicy Bypass -File packaging/build_release.ps1
```

Inno Setup requests that commercial users purchase a commercial license. Treat
locally compiled installers as internal/test builds until the project's
distribution licensing is in place.

The build:

1. Reads the version from `src/anz_clicker_qt/version.py`.
2. Runs `tests/smoke_test.py`.
3. Builds with the canonical PyInstaller spec.
4. Stages the tested application in `dist/Anz Clicker/`.
5. Compiles `release/Anz Clicker Setup v<version>.exe` with Inno Setup.
6. Prints the installer SHA-256 checksum.

Use `-SkipInstaller` to test and stage the PyInstaller application on a machine
without Inno Setup. This does not create a distributable release.

Installed builds keep mutable files outside the installation directory:

- `%LOCALAPPDATA%\Anz Clicker\scripts`
- `%LOCALAPPDATA%\Anz Clicker\user-data`

The installer neither creates nor removes those folders, so upgrading or
uninstalling the application does not erase user scripts or customization.
