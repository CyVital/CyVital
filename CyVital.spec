# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules

datas = []   # keep for non-python assets only
binaries = []
hiddenimports = []

# your own code (make PyInstaller include submodules)
hiddenimports += collect_submodules("gui")
hiddenimports += collect_submodules("oscilloscope")
hiddenimports += collect_submodules("plots")

a = Analysis(
    ['src\\Main.py'],
    pathex=['src'],          # important: lets PyInstaller import gui/oscilloscope/plots from src
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    a.binaries,
    a.datas,
    [],
    name='CyVital',
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
)
