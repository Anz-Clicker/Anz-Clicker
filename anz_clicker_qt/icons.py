from __future__ import annotations

from pathlib import Path
import sys

from PySide6.QtGui import QIcon


def resource_path(filename: str) -> Path:
    bundle_dir = getattr(sys, "_MEIPASS", None)
    if bundle_dir:
        return Path(bundle_dir) / filename
    return Path(__file__).resolve().parent.parent / filename


def app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def app_icon(name: str, size: int = 22, dark: bool = True) -> QIcon:
    theme = "dark" if dark else "light"
    icon_file = resource_path(f"icons/{theme}/{name}.svg")
    if icon_file.exists():
        return QIcon(str(icon_file))
    return QIcon(str(resource_path("zabian_logo.png")))
