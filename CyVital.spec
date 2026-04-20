# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None
icon_dir = 'icons'

if sys.platform == 'darwin':
    # macOS expects .icns
    icon_path = os.path.join(icon_dir, 'CyVitalLogo.icns')
elif sys.platform == 'win32':
    # Windows expects .ico
    icon_path = os.path.join(icon_dir, 'CyVitalLogo.ico')
else:
    icon_path = None

hiddenimports = []
hiddenimports += collect_submodules("gui")
hiddenimports += collect_submodules("oscilloscope")
hiddenimports += collect_submodules("plots")

a = Analysis(
    [os.path.join('src', 'Main.py')],
    pathex=['src'],
    binaries=[],
    datas=[], 
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    a.zipfiles,
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
    icon=icon_path if sys.platform == 'win32' else None,
)

# This part is ignored on Windows but creates the .app folder on Mac
app = BUNDLE(
    exe,
    name='CyVital.app',
    icon=icon_path if sys.platform == 'darwin' else None, 
    bundle_identifier='com.yourdomain.cyvital',
)