from __future__ import annotations

from pathlib import Path
import shutil
import sys


SOURCE_ROOT = Path(__file__).resolve().parents[2]


def app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return SOURCE_ROOT


def user_data_dir() -> Path:
    return app_base_dir() / "user-data"


def scripts_dir() -> Path:
    return app_base_dir() / "scripts"


def captures_dir() -> Path:
    return user_data_dir() / "captures"


def settings_path() -> Path:
    return user_data_dir() / "anz_clicker_settings.json"


def presets_path() -> Path:
    return user_data_dir() / "anz_clicker_presets.json"


def ensure_user_directories() -> None:
    user_data_dir().mkdir(parents=True, exist_ok=True)
    scripts_dir().mkdir(parents=True, exist_ok=True)
    captures_dir().mkdir(parents=True, exist_ok=True)


def migrate_legacy_user_data(base_dir: Path | None = None, data_dir: Path | None = None) -> None:
    base = Path(base_dir) if base_dir is not None else app_base_dir()
    destination = Path(data_dir) if data_dir is not None else user_data_dir()
    destination.mkdir(parents=True, exist_ok=True)

    for filename in ("anz_clicker_settings.json", "anz_clicker_presets.json"):
        source = base / filename
        target = destination / filename
        if source.is_file() and not target.exists():
            shutil.copy2(source, target)

    legacy_captures = base / "captures"
    target_captures = destination / "captures"
    if legacy_captures.is_dir() and not target_captures.exists():
        shutil.copytree(legacy_captures, target_captures)

    for source in base.glob("*.anzlicense"):
        target = destination / source.name
        if source.is_file() and not target.exists():
            shutil.copy2(source, target)
