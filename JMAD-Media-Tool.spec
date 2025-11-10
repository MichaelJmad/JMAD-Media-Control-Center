# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for JMAD Media Tool
"""
import os
import sys
from PyInstaller.utils.hooks import collect_submodules, collect_all

# Get the absolute path to the project directory
project_dir = os.path.abspath(SPECPATH)

block_cipher = None

# Collect all submodules from our application packages
hidden = []
hidden += collect_submodules('config')
hidden += collect_submodules('domain')
hidden += collect_submodules('application')
hidden += collect_submodules('infrastructure')
hidden += collect_submodules('presentation')

# Collect all from PySide6
pyside_datas, pyside_binaries, pyside_hiddenimports = collect_all('PySide6')

a = Analysis(
    ['main.py'],
    pathex=[project_dir],  # Add project directory to Python path
    binaries=pyside_binaries,
    datas=pyside_datas,
    hiddenimports=hidden + pyside_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'pytest',
        'unittest',
        'tests',
        'tkinter',  # Exclude if not needed
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
    a.zipfiles,
    a.datas,
    [],
    name='JMAD-Media-Tool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to False for GUI application (no console window)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='version_info.txt',  # Optional: create version info file for Windows
    icon=None,  # Optional: add icon file path here if available
)
