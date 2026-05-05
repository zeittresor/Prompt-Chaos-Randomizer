@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

title Prompt Chaos Randomizer - Build PyQt6 Wheelhouse

set "AUTO_MODE=0"
if /I "%~1"=="--auto" set "AUTO_MODE=1"
if /I "%~1"=="/AUTO" set "AUTO_MODE=1"
if /I "%~1"=="-auto" set "AUTO_MODE=1"

echo ================================================
echo Build local PyQt6 wheelhouse for offline installs
echo ================================================
echo.
echo This downloads PyQt6 wheels into .\wheelhouse.
echo Run manually on a machine with internet access, or let
echo install_windows.bat try it automatically first.
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
    echo [ERROR] No Python interpreter found.
    if "%AUTO_MODE%"=="0" pause
    exit /b 1
)

echo [OK] Using interpreter: %PYEXE%

if not exist wheelhouse mkdir wheelhouse

echo [STEP] Downloading PyQt6 wheels into wheelhouse...
%PYEXE% -m pip download --only-binary=:all: --dest wheelhouse PyQt6
if errorlevel 1 (
    echo [ERROR] Download failed. This is expected on offline machines.
    if "%AUTO_MODE%"=="0" pause
    exit /b 1
)
echo.
echo [OK] Wheelhouse is ready. install_windows.bat can now install PyQt6 from local wheels.
if "%AUTO_MODE%"=="0" pause
exit /b 0
