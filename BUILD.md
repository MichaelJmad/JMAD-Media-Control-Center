# Building JMAD Media Tool Executable

This guide explains how to build a standalone executable for JMAD Media Tool using PyInstaller.

## Prerequisites

1. Python 3.11 or higher
2. All dependencies installed (see requirements.txt)

## Quick Build

### Linux/macOS

```bash
./build.sh
```

### Windows

```cmd
build.bat
```

## Manual Build

If you prefer to build manually:

```bash
# Install dependencies
pip install -r requirements.txt

# Build executable
pyinstaller JMAD-Media-Tool.spec --clean --noconfirm
```

## Output

After a successful build, you'll find the executable in the `dist/` directory:

- **Linux/macOS**: `dist/JMAD-Media-Tool`
- **Windows**: `dist/JMAD-Media-Tool.exe`

## File Structure

- `JMAD-Media-Tool.spec`: PyInstaller specification file with all configuration
- `version_info.txt`: Version information for Windows executable
- `build.sh`: Linux/macOS build script
- `build.bat`: Windows build script

## Customization

### Adding an Icon

To add a custom icon to the executable:

1. Create or obtain an `.ico` file (Windows) or `.icns` file (macOS)
2. Place it in the project root
3. Edit `JMAD-Media-Tool.spec` and update the `icon` parameter:
   ```python
   icon='path/to/your/icon.ico'
   ```

### Changing Version Information

Edit `version_info.txt` to update version numbers and metadata.

### One-Directory vs One-File Build

The current configuration creates a **one-file** executable (everything bundled into a single file).

To create a **one-directory** build instead (faster startup, larger folder):

1. Edit `JMAD-Media-Tool.spec`
2. Replace the `EXE` section with:
   ```python
   exe = EXE(
       pyz,
       a.scripts,
       [],
       exclude_binaries=True,
       name='JMAD-Media-Tool',
       debug=False,
       bootloader_ignore_signals=False,
       strip=False,
       upx=True,
       console=False,
   )

   coll = COLLECT(
       exe,
       a.binaries,
       a.zipfiles,
       a.datas,
       strip=False,
       upx=True,
       upx_exclude=[],
       name='JMAD-Media-Tool',
   )
   ```

## Troubleshooting

### Import Errors

If you encounter import errors during runtime:

1. Add missing modules to `hiddenimports` in `JMAD-Media-Tool.spec`
2. Rebuild the executable

### Large Executable Size

The executable size can be reduced by:

1. Using one-directory build instead of one-file
2. Excluding unnecessary modules in the spec file
3. Using UPX compression (already enabled)

### Console Window Appears (Windows)

If a console window appears alongside the GUI:

1. Ensure `console=False` in the spec file
2. Rebuild the executable

### PySide6 Errors

If PySide6-related errors occur:

1. Ensure PySide6 is properly installed: `pip install PySide6>=6.6.0`
2. Try adding specific PySide6 modules to `hiddenimports`
3. Check PyInstaller hooks are up to date: `pip install --upgrade pyinstaller-hooks-contrib`

## Platform-Specific Notes

### macOS

- On macOS, you may need to code-sign the application
- Use `codesign` after building if distributing to other users

### Windows

- The executable may be flagged by antivirus software (false positive)
- Consider code-signing for distribution
- Version info is automatically embedded from `version_info.txt`

### Linux

- Ensure all Qt dependencies are available on the target system
- Consider using AppImage for better portability

## Distribution

The built executable can be distributed as-is. No Python installation is required on the target system.

### Recommended Distribution Methods

- **Windows**: Create a ZIP file or installer (e.g., Inno Setup, NSIS)
- **macOS**: Create a DMG or use a tool like `create-dmg`
- **Linux**: Create a tarball or AppImage

## Clean Build

To perform a clean build:

```bash
# Remove build artifacts
rm -rf build dist __pycache__ *.spec~

# Rebuild
./build.sh  # or build.bat on Windows
```
