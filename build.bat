@echo off
REM Build script for JMAD Media Tool executable (Windows)

echo Building JMAD Media Tool executable...
echo =======================================

REM Clean previous builds
if exist "build" (
    echo Cleaning previous build directory...
    rmdir /s /q build
)

if exist "dist" (
    echo Cleaning previous dist directory...
    rmdir /s /q dist
)

REM Run PyInstaller
echo Running PyInstaller...
pyinstaller JMAD-Media-Tool.spec --clean --noconfirm

REM Check if build was successful
if exist "dist\JMAD-Media-Tool.exe" (
    echo.
    echo =======================================
    echo Build completed successfully!
    echo Executable location: dist\JMAD-Media-Tool.exe
    echo =======================================
    dir dist\JMAD-Media-Tool.exe
) else (
    echo.
    echo =======================================
    echo Build failed. Check the output above for errors.
    echo =======================================
    exit /b 1
)
