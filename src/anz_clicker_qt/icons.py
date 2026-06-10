from __future__ import annotations

from pathlib import Path
import sys

from PySide6.QtGui import QIcon

from .paths import SOURCE_ROOT, app_base_dir


def resource_path(filename: str) -> Path:
    bundle_dir = getattr(sys, "_MEIPASS", None)
    if bundle_dir:
        return Path(bundle_dir) / filename
    if filename == "zabian_logo.png":
        return SOURCE_ROOT / "assets" / "icons" / filename
    if filename.startswith("icons/"):
        return SOURCE_ROOT / "assets" / "icons" / "themes" / filename.removeprefix("icons/")
    return SOURCE_ROOT / filename


def app_icon(name: str, size: int = 22, dark: bool = True) -> QIcon:
    theme = "dark" if dark else "light"
    icon_file = resource_path(f"icons/{theme}/{name}.svg")
    if icon_file.exists():
        return QIcon(str(icon_file))
    return QIcon(str(resource_path("zabian_logo.png")))
