@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Local venv not found. Running installer first.
    call install_windows.bat
    exit /b %errorlevel%
)

set "PYTHONUTF8=1"
".venv\Scripts\python.exe" "src\app.py"
if errorlevel 1 (
    echo.
    echo [ERROR] The app ended with an error.
    pause
)
