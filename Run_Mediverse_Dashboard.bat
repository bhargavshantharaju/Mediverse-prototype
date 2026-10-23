@echo off
setlocal
cd /d "%~dp0"
set "LOG=%~dp0dashboard_startup_error.log"
py -u mediverse_dashboard.py 1>>"%LOG%" 2>>&1
set "APP_EXIT=%ERRORLEVEL%"
if not "%APP_EXIT%"=="0" (
  echo.
  echo Mediverse dashboard exited with error code %APP_EXIT%.
  echo Diagnostic output is in:
  echo %LOG%
  echo.
  if exist "%LOG%" type "%LOG%"
  echo.
  pause
)
endlocal
