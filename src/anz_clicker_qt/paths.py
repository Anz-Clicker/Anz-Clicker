from __future__ import annotations

import os
from pathlib import Path
import shutil
import sys


SOURCE_ROOT = Path(__file__).resolve().parents[2]


def app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return SOURCE_ROOT


def storage_root() -> Path:
    """Return the writable root for scripts and application-owned user data."""
    if not getattr(sys, "frozen", False):
        return SOURCE_ROOT

    override = os.environ.get("ANZ_CLICKER_DATA_DIR", "").strip()
    if override:
        return Path(override).expanduser().resolve()

    local_app_data = os.environ.get("LOCALAPPDATA", "").strip()
    if local_app_data:
        return Path(local_app_data) / "Anz Clicker"
    return Path.home() / "AppData" / "Local" / "Anz Clicker"


def user_data_dir() -> Path:
    return storage_root() / "user-data"


def scripts_dir() -> Path:
    return storage_root() / "scripts"


def captures_dir() -> Path:
    return user_data_dir() / "captures"


def settings_path() -> Path:
    return user_data_dir() / "anz_clicker_settings.json"


def presets_path() -> Path:
    return user_data_dir() / "anz_clicker_presets.json"


def update_relaunch_marker_path() -> Path:
    return user_data_dir() / "update_relaunch.json"


def ensure_user_directories() -> None:
    user_data_dir().mkdir(parents=True, exist_ok=True)
    scripts_dir().mkdir(parents=True, exist_ok=True)
    captures_dir().mkdir(parents=True, exist_ok=True)


def _copy_missing_tree(source: Path, destination: Path) -> None:
    if not source.is_dir():
        return
    destination.mkdir(parents=True, exist_ok=True)
    for item in source.rglob("*"):
        relative = item.relative_to(source)
        target = destination / relative
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif item.is_file() and not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


def migrate_legacy_user_data(
    base_dir: Path | None = None,
    data_dir: Path | None = None,
    script_dir: Path | None = None,
) -> None:
    base = Path(base_dir) if base_dir is not None else app_base_dir()
    destination = Path(data_dir) if data_dir is not None else user_data_dir()
    script_destination = Path(script_dir) if script_dir is not None else scripts_dir()
    destination.mkdir(parents=True, exist_ok=True)
    script_destination.mkdir(parents=True, exist_ok=True)

    for filename in ("anz_clicker_settings.json", "anz_clicker_presets.json"):
        target = destination / filename
        for source in (base / filename, base / "user-data" / filename):
            if source.is_file() and not target.exists():
                shutil.copy2(source, target)

    target_captures = destination / "captures"
    _copy_missing_tree(base / "captures", target_captures)
    _copy_missing_tree(base / "user-data" / "captures", target_captures)
    _copy_missing_tree(base / "scripts", script_destination)

    for legacy_root in (base, base / "user-data"):
        for source in legacy_root.glob("*.anzlicense"):
            target = destination / source.name
            if source.is_file() and not target.exists():
                shutil.copy2(source, target)
