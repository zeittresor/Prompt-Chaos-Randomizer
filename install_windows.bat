@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

title Prompt Chaos Randomizer - Smart Offline Installer

echo ================================================
echo Prompt Chaos Randomizer - Smart Offline Installer
echo ================================================
echo.
echo This creates a local .venv next to the app.
echo If PyQt6 wheels are already present in .\wheelhouse,
echo they are installed from there.
echo.
echo If .\wheelhouse is empty, this installer first tries to run
echo prepare_pyqt6_wheelhouse_online.bat automatically. If that online
echo download is not possible, installation continues with the built-in
echo offline Tkinter fallback GUI.
echo.

set "PYEXE="
where py >nul 2>nul
if %errorlevel%==0 (
    for %%V in (3.12 3.11 3.10 3.13 3.9) do (
        if not defined PYEXE (
            py -%%V -c "import sys; print(sys.executable)" >nul 2>nul
            if !errorlevel!==0 set "PYEXE=py -%%V"
        )
    )
)
if not defined PYEXE (
    where python >nul 2>nul
    if %errorlevel%==0 set "PYEXE=python"
)
if not defined PYEXE (
    echo [ERROR] No Python interpreter found. Please install Python 3.9 or newer.
    pause
    exit /b 1
)

echo [OK] Using interpreter: %PYEXE%

if not exist ".venv\Scripts\python.exe" (
    echo [STEP] Creating local venv...
    %PYEXE% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Could not create venv.
        pause
        exit /b 1
    )
) else (
    echo [OK] Existing .venv found.
)

set "VPY=.venv\Scripts\python.exe"

if not exist "wheelhouse\*.whl" (
    echo [STEP] No local PyQt6 wheels found. Trying automatic online wheelhouse preparation...
    if exist "prepare_pyqt6_wheelhouse_online.bat" (
        call prepare_pyqt6_wheelhouse_online.bat --auto
        if errorlevel 1 (
            echo [WARN] Automatic PyQt6 wheelhouse preparation failed or internet is unavailable.
            echo [WARN] The app will still run with the offline Tkinter fallback GUI.
        ) else (
            echo [OK] Automatic PyQt6 wheelhouse preparation finished.
        )
    ) else (
        echo [WARN] prepare_pyqt6_wheelhouse_online.bat was not found.
        echo [WARN] The app will still run with the offline Tkinter fallback GUI.
    )
)

if exist "wheelhouse\*.whl" (
    echo [STEP] Installing optional local wheels from wheelhouse...
    "%VPY%" -m pip install --no-index --find-links wheelhouse PyQt6
    if errorlevel 1 (
        echo [WARN] PyQt6 could not be installed from wheelhouse.
        echo [WARN] The app will still run with the Tkinter fallback GUI.
    ) else (
        echo [OK] PyQt6 installed from local wheelhouse.
    )
) else (
    echo [INFO] No usable PyQt6 wheels are available in wheelhouse.
    echo [INFO] The app remains offline-runnable with the built-in Tkinter fallback GUI.
)

echo.
echo [OK] Installation finished.
echo Start GUI now? [Y/N] default Y in 10s:
choice /C YN /D Y /T 10 /N >nul
if errorlevel 2 goto end
call run_windows.bat

:end
echo.
echo Done.
