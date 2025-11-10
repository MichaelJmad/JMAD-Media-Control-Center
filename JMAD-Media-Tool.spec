# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for JMAD Media Tool
"""

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        # PySide6 modules
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',

        # Application modules (explicit imports for PyInstaller)
        'config',
        'config.settings',
        'config.constants',

        'domain',
        'domain.models',
        'domain.models.series',
        'domain.models.season',
        'domain.models.episode',
        'domain.models.movie',
        'domain.value_objects',
        'domain.value_objects.file_path',
        'domain.value_objects.episode_number',
        'domain.value_objects.media_type',

        'application',
        'application.commands',
        'application.commands.base_command',
        'application.commands.cleanup_command',
        'application.commands.organize_command',
        'application.use_cases',
        'application.use_cases.scan_media',
        'application.use_cases.cleanup_files',
        'application.use_cases.move_series',
        'application.use_cases.organize_folders',
        'application.dto',
        'application.dto.scan_result',
        'application.dto.organize_result',

        'infrastructure',
        'infrastructure.services',
        'infrastructure.services.file_system_service',
        'infrastructure.services.history_service',
        'infrastructure.services.undo_redo_manager',
        'infrastructure.services.media_scanner',
        'infrastructure.parsers',
        'infrastructure.parsers.episode_parser',
        'infrastructure.parsers.fluff_parser',
        'infrastructure.parsers.movie_parser',
        'infrastructure.repositories',
        'infrastructure.repositories.settings_repository',

        'presentation',
        'presentation.main_window',
        'presentation.widgets',
        'presentation.widgets.cleanup_panel',
        'presentation.widgets.settings_panel',
        'presentation.widgets.hotkeys_panel',
        'presentation.widgets.toast',
        'presentation.dialogs',
        'presentation.dialogs.organize_dialog',
        'presentation.dialogs.media_type_dialog',
        'presentation.dialogs.series_organize_dialog',
        'presentation.dialogs.movies_organize_dialog',
        'presentation.view_models',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'pytest',
        'unittest',
        'tests',
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
