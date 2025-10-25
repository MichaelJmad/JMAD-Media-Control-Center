@echo off
setlocal enabledelayedexpansion

REM Loop through all files in the current directory
for %%f in (*.*) do (
    REM Skip directories
    if not "%%~ff"=="%%~dpf." (
        REM Get file name without extension
        set "filename=%%~nf"
        
        REM Create folder if it doesn't exist
        if not exist "!filename!" (
            mkdir "!filename!"
        )
        
        REM Move file into the folder
        move "%%f" "!filename!\"
    )
)

echo All files moved into folders.
pause
