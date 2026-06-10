# Release Packaging

Run the canonical release build from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File packaging/build_release.ps1
```

The script:

1. Reads the version from `src/anz_clicker_qt/version.py`.
2. Runs `tests/smoke_test.py`.
3. Builds with the canonical PyInstaller spec.
4. Creates `dist/Anz Clicker v<version>/`.
5. Creates `release/Anz Clicker Portable v<version>.zip`.
6. Prints the ZIP SHA-256 checksum.

Generated releases contain empty `scripts/` and `user-data/` directories. Those directories must be preserved by future updaters.
