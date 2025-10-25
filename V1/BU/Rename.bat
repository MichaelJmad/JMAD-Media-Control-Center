@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM Process each Season folder in the current directory
for /d %%S in ("Season*") do (
  call :GetDigits "%%~nxS" season
  if defined season (
    set "season=0!season!"
    set "season=!season:~-2!"
    echo Processing "%%~nxS" as season !season!

    REM Rename files that start with E inside this season folder
    for /f "delims=" %%F in ('dir /b /a-d "%%S"') do (
      set "filename=%%F"
      if /I "!filename:~0,1!"=="E" (
        ren "%%S\%%F" "S!season!!filename!"
      )
    )
  ) else (
    echo Skipping "%%~nxS" (no digits found in folder name)
  )
)

echo Done.
exit /b

:GetDigits
REM Extracts digits from a string. Usage: call :GetDigits "input" outVar
setlocal EnableDelayedExpansion
set "str=%~1"
set "digits="
for /l %%I in (0,1,255) do (
  set "ch=!str:~%%I,1!"
  if "!ch!"=="" goto :gddone
  for %%D in (0 1 2 3 4 5 6 7 8 9) do if "!ch!"=="%%D" set "digits=!digits!!ch!"
)
:gddone
endlocal & set "%~2=%digits%"
goto :eof
