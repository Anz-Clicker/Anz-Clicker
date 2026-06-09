# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


ROOT = Path(SPECPATH).resolve()


a = Analysis(
    [str(ROOT / "anz_clicker_qt.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "zabian_logo.png"), "."),
        (str(ROOT / "icons"), "icons"),
        (str(ROOT / "tesseract"), "tesseract"),
        (str(ROOT / "scripts"), "scripts"),
        (str(ROOT / "docs"), "docs"),
        (str(ROOT / "README.md"), "."),
        (str(ROOT / "CHANGELOG.md"), "."),
        (str(ROOT / "PORTABLE_README.txt"), "."),
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
    icon=[str(ROOT / "anz_clicker.ico")],
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
