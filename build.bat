@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo   FoxDesk Installer Builder
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH
    exit /b 1
)

:: Install dependencies
echo [1/6] Installing dependencies...
python -m pip install -r requirements.txt -q 2>nul
python -m pip install pillow -q 2>nul

:: Convert logo to ICO
echo [2/6] Creating icon...
python make_ico.py

:: Clean previous builds
echo [3/6] Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist installer_output rmdir /s /q installer_output

:: Build with PyInstaller
echo [4/6] Building FoxDesk exe...
python -m PyInstaller foxdesk.spec --noconfirm --clean --log-level WARN
if errorlevel 1 (
    echo [ERROR] PyInstaller build failed
    exit /b 1
)

:: Check Inno Setup
set "ISCC="
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
) else (
    where iscc >nul 2>&1 && set "ISCC=iscc"
)

if "%ISCC%"=="" (
    echo.
    echo [INFO] Inno Setup not found. Installing via winget...
    winget install --id JRSoftware.InnoSetup --accept-source-agreements --accept-package-agreements -q 2>nul
    if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
        set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    ) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
        set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
    ) else if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" (
        set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
    )
)

if "%ISCC%"=="" (
    echo.
    echo [WARN] Inno Setup not available. Skipping installer.
    echo [WARN] Install from: https://jrsoftware.org/isinfo.php
    echo [WARN] Then re-run this script.
    echo.
    echo Output: dist\FoxDesk\FoxDesk.exe (portable)
    goto :end
)

:: Build installer
echo [5/6] Compiling installer...
"%ISCC%" installer.iss
if errorlevel 1 (
    echo [ERROR] Inno Setup compilation failed
    exit /b 1
)

:: Done
echo [6/6] Done!
echo.
echo ============================================
echo   Installer: installer_output\FoxDesk-1.0.0-Setup.exe
echo   Portable:  dist\FoxDesk\FoxDesk.exe
echo ============================================

:end
endlocal
