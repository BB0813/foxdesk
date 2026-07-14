@echo off
:: Right-click -> Run as administrator
setlocal
echo [FoxDesk] Admin purge starting...
taskkill /F /IM FoxDesk.exe /T >nul 2>&1
timeout /t 1 /nobreak >nul

if exist "C:\Program Files\FoxDesk" (
  echo Removing C:\Program Files\FoxDesk ...
  takeown /F "C:\Program Files\FoxDesk" /R /D Y >nul 2>&1
  icacls "C:\Program Files\FoxDesk" /grant administrators:F /T /C /Q >nul 2>&1
  icacls "C:\Program Files\FoxDesk" /grant %USERNAME%:F /T /C /Q >nul 2>&1
  rmdir /s /q "C:\Program Files\FoxDesk"
)

if exist "%LOCALAPPDATA%\Programs\FoxDesk" (
  echo Removing %LOCALAPPDATA%\Programs\FoxDesk ...
  rmdir /s /q "%LOCALAPPDATA%\Programs\FoxDesk"
)
if exist "%APPDATA%\CamoufoxManager" rmdir /s /q "%APPDATA%\CamoufoxManager"
if exist "%LOCALAPPDATA%\CamoufoxManager" rmdir /s /q "%LOCALAPPDATA%\CamoufoxManager"
if exist "%TEMP%\FoxDesk" rmdir /s /q "%TEMP%\FoxDesk"
del /f /q "%USERPROFILE%\Desktop\FoxDesk.lnk" >nul 2>&1
del /f /q "%PUBLIC%\Desktop\FoxDesk.lnk" >nul 2>&1
if exist "%APPDATA%\Microsoft\Windows\Start Menu\Programs\FoxDesk" rmdir /s /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\FoxDesk"
if exist "%ProgramData%\Microsoft\Windows\Start Menu\Programs\FoxDesk" rmdir /s /q "%ProgramData%\Microsoft\Windows\Start Menu\Programs\FoxDesk"

echo.
if exist "C:\Program Files\FoxDesk" (
  echo STILL EXISTS: C:\Program Files\FoxDesk
  echo Close any Explorer windows opened on that folder and re-run this bat.
  exit /b 1
) else (
  echo CLEAN: C:\Program Files\FoxDesk is gone
)
if exist "%APPDATA%\CamoufoxManager" (
  echo STILL EXISTS: %APPDATA%\CamoufoxManager
) else (
  echo CLEAN: user data gone
)
echo Done. You can install FoxDesk-1.1.0-beta.6-Setup.exe now.
pause
