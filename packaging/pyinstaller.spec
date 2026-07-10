# PyInstaller spec for building standalone binary
# Run from repo root:
#   pyinstaller packaging/pyinstaller.spec
# Output: dist/citationer (Linux/macOS) or dist/citationer.exe (Windows)

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None
APP_NAME = "citationer"
# PyInstaller runs this spec via exec() so __file__ isn't always available.
# Use sys.argv[0] (path passed to pyinstaller CLI) as the anchor.
import sys  # noqa: E402

_SPEC_DIR = Path(os.path.dirname(os.path.abspath(sys.argv[0]))).parent
ENTRY = _SPEC_DIR / "src" / "citationer" / "__main__.py"

datas = []
datas += collect_data_files("citationer.data")
hiddenimports = []
hiddenimports += collect_submodules("citationer")


a = Analysis(
    [str(ENTRY)],
    pathex=[str(_SPEC_DIR / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib.tests",
        "pytest",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
