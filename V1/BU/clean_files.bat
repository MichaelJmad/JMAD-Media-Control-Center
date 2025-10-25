@echo off
echo Deleting all images, text, and NFO files in and under: %cd%
echo.

REM Delete image files
del /s /q *.jpg *.jpeg *.png *.gif

REM Delete text and NFO files
del /s /q *.txt *.nfo *.srt

REM Delete Other
del /s /q *.mp3


echo.
echo Cleanup complete.
pause
