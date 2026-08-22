@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================
echo   FoxDesk Installer Builder
echo ============================================

:: Read VERSION without trailing CR (Git Bash / CRLF safe)
set "APPVER=1.4.0"
if exist VERSION (
  for /f "usebackq tokens=* delims=" %%A in ("VERSION") do (
    set "APPVER=%%A"
    goto :ver_done
  )
)
:ver_done
:: strip spaces
for /f "tokens=* delims= " %%A in ("%APPVER%") do set "APPVER=%%A"
echo   Version: %APPVER%
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
python -m pip install pillow pyinstaller -q 2>nul

:: Convert logo to ICO
echo [2/6] Creating icon...
python make_ico.py

:: Sync VERSION into installer.iss (same as CI does)
echo       Syncing installer version...
python -c "import re,pathlib;v=pathlib.Path('VERSION').read_text().strip();s=pathlib.Path('installer.iss').read_text(encoding='utf-8');s=re.sub(r'#define MyAppVersion \".*?\"',f'#define MyAppVersion \"{v}\"',s);parts=(re.split(r'[^0-9.]',v)[0] or '0.0.0').split('.');parts+=['0']*(4-len(parts));fv='.'.join(parts[:4]);s=re.sub(r'VersionInfoVersion=.*',f'VersionInfoVersion={fv}',s);s=re.sub(r'VersionInfoProductVersion=.*',f'VersionInfoProductVersion={fv}',s);pathlib.Path('installer.iss').write_text(s,encoding='utf-8');print(f'      installer.iss -> {v} (file {fv})')"
if errorlevel 1 (
    echo [ERROR] installer.iss version sync failed
    exit /b 1
)

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

if not exist "dist\FoxDesk\FoxDesk.exe" (
    echo [ERROR] dist\FoxDesk\FoxDesk.exe missing after build
    exit /b 1
)

:: Check Inno Setup
set "ISCC="
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
) else if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" (
    set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
) else if exist "%USERPROFILE%\AppData\Local\Programs\Inno Setup 6\ISCC.exe" (
    set "ISCC=%USERPROFILE%\AppData\Local\Programs\Inno Setup 6\ISCC.exe"
) else (
    where iscc >nul 2>&1 && for /f "delims=" %%I in ('where iscc') do set "ISCC=%%I"
)

if not "%ISCC%"=="" echo [INFO] Using Inno Setup: "%ISCC%"
if "%ISCC%"=="" (
    echo.
    echo [INFO] Inno Setup not found. Trying winget install...
    winget install --id JRSoftware.InnoSetup -e --accept-source-agreements --accept-package-agreements --disable-interactivity
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
    echo Output: dist\FoxDesk\FoxDesk.exe - portable only
    goto :summary
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

:summary
echo.
echo ============================================
echo   Version:  %APPVER%
if exist "installer_output\FoxDesk-%APPVER%-Setup.exe" (
  echo   Installer: installer_output\FoxDesk-%APPVER%-Setup.exe
) else (
  echo   Installer: not built - Inno missing or failed
)
echo   Portable:  dist\FoxDesk\FoxDesk.exe
echo.
echo   NOTE: Playwright/Patchright browser caches are NOT bundled.
echo   After install, users may need:
echo     playwright install chromium
echo     patchright install chromium
echo   See docs\research\build-release-notes.md
echo ============================================

:end
endlocal
