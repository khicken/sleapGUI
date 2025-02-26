# -*- mode: python ; coding: utf-8 -*-

import os
import platform

block_cipher = None

# Read the executable name from the environment variable
executable_name = os.getenv('EXECUTABLE_NAME', 'mediaGUI')

# Detect the operating system
os_name = platform.system().lower()

# Define platform-specific binaries
binaries = []
if os_name == 'windows':
    binaries.append(('mediagui/openh264-1.8.0-win64.dll', '.'))

a = Analysis(
    ['mediagui/gui.py', 'mediagui/worker.py', 'mediagui/list_widget.py'],
    pathex=['.'],
    binaries=binaries,
    datas=[],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=executable_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    windowed=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=executable_name,
)