#!/bin/bash
# Build script for JMAD Media Tool executable

echo "Building JMAD Media Tool executable..."
echo "======================================="

# Clean previous builds
if [ -d "build" ]; then
    echo "Cleaning previous build directory..."
    rm -rf build
fi

if [ -d "dist" ]; then
    echo "Cleaning previous dist directory..."
    rm -rf dist
fi

# Run PyInstaller
echo "Running PyInstaller..."
pyinstaller JMAD-Media-Tool.spec --clean --noconfirm

# Check if build was successful
if [ -f "dist/JMAD-Media-Tool" ] || [ -f "dist/JMAD-Media-Tool.exe" ]; then
    echo ""
    echo "======================================="
    echo "Build completed successfully!"
    echo "Executable location: dist/JMAD-Media-Tool"
    echo "======================================="
    ls -lh dist/
else
    echo ""
    echo "======================================="
    echo "Build failed. Check the output above for errors."
    echo "======================================="
    exit 1
fi
