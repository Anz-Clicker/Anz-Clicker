# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


ROOT = Path(SPECPATH).resolve().parent
SRC = ROOT / "src"


a = Analysis(
    [str(SRC / "anz_clicker_qt.py")],
    pathex=[str(SRC)],
    binaries=[],
    datas=[
        (str(ROOT / "assets" / "icons" / "zabian_logo.png"), "."),
        (str(ROOT / "assets" / "icons" / "themes"), "icons"),
        (str(ROOT / "vendor" / "tesseract"), "tesseract"),
        (str(ROOT / "scripts"), "scripts"),
        (str(ROOT / "docs"), "docs"),
        (str(ROOT / "README.md"), "."),
        (str(ROOT / "docs" / "CHANGELOG.md"), "."),
        (str(ROOT / "docs" / "PORTABLE_README.txt"), "."),
    ],
    hiddenimports=[
        "PIL.Image",
        "PIL.ImageChops",
        "PIL.ImageGrab",
        "PIL.ImageOps",
        "pytesseract",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Anz Clicker",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[str(ROOT / "assets" / "icons" / "anz_clicker.ico")],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Anz Clicker Portable",
)
