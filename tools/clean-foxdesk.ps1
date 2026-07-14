# FoxDesk full cleanup helper (Windows)
# Closes processes, removes install dirs, optional user data.
# Usage:
#   powershell -ExecutionPolicy Bypass -File tools/clean-foxdesk.ps1
#   powershell -ExecutionPolicy Bypass -File tools/clean-foxdesk.ps1 -KeepUserData

param(
    [switch]$KeepUserData,
    [switch]$Yes
)

$ErrorActionPreference = "Continue"
$AppName = "FoxDesk"
$ExeName = "FoxDesk.exe"

function Write-Step($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg) { Write-Host "  OK  $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "  !!  $msg" -ForegroundColor Yellow }

Write-Step "Stopping $AppName processes"
Get-Process -Name "FoxDesk" -ErrorAction SilentlyContinue | ForEach-Object {
    try {
        Stop-Process -Id $_.Id -Force -ErrorAction Stop
        Write-Ok "killed pid=$($_.Id)"
    } catch {
        Write-Warn "could not kill pid=$($_.Id): $_"
    }
}
& taskkill.exe /F /IM $ExeName /T 2>$null | Out-Null

Write-Step "Running registered uninstaller(s) if present"
$uninstallKeys = @(
    "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*",
    "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*",
    "HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*"
)
$found = $false
foreach ($path in $uninstallKeys) {
    Get-ItemProperty $path -ErrorAction SilentlyContinue |
        Where-Object { $_.DisplayName -like "*FoxDesk*" -or $_.DisplayName -like "*CamoufoxManager*" } |
        ForEach-Object {
            $found = $true
            $cmd = $_.UninstallString
            if (-not $cmd) { return }
            Write-Host "  uninstall: $($_.DisplayName) -> $cmd"
            try {
                if ($cmd -match '^\s*"?(.+?unins\d*\.exe)"?\s*(.*)$') {
                    $exe = $Matches[1]
                    # Silent-ish uninstall; user-data prompt is interactive in our iss —
                    # use /SILENT and clean data ourselves below.
                    Start-Process -FilePath $exe -ArgumentList "/VERYSILENT","/SUPPRESSMSGBOXES","/NORESTART" -Wait -ErrorAction Stop
                    Write-Ok "uninstaller finished"
                } else {
                    cmd /c $cmd
                }
            } catch {
                Write-Warn "uninstaller failed: $_"
            }
        }
}
if (-not $found) { Write-Warn "no registered uninstaller found" }

$candidates = @(
    "$env:LOCALAPPDATA\Programs\FoxDesk",
    "$env:ProgramFiles\FoxDesk",
    "${env:ProgramFiles(x86)}\FoxDesk",
    "$env:USERPROFILE\AppData\Local\Programs\FoxDesk"
) | Select-Object -Unique
# 1.1.0+ defaults to %LOCALAPPDATA%\Programs\FoxDesk; older betas may use Program Files.

Write-Step "Removing leftover install directories"
foreach ($dir in $candidates) {
    if (Test-Path $dir) {
        try {
            Remove-Item -LiteralPath $dir -Recurse -Force -ErrorAction Stop
            Write-Ok "removed $dir"
        } catch {
            Write-Warn "failed $dir : $_"
        }
    }
}

# Common desktop / start menu shortcuts
$shortcuts = @(
    "$env:USERPROFILE\Desktop\FoxDesk.lnk",
    "$env:PUBLIC\Desktop\FoxDesk.lnk",
    "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\FoxDesk",
    "$env:ProgramData\Microsoft\Windows\Start Menu\Programs\FoxDesk",
    "$env:TEMP\FoxDesk"
)
Write-Step "Removing shortcuts / temp locks"
foreach ($p in $shortcuts) {
    if (Test-Path $p) {
        try {
            Remove-Item -LiteralPath $p -Recurse -Force -ErrorAction Stop
            Write-Ok "removed $p"
        } catch {
            Write-Warn "failed $p : $_"
        }
    }
}

if (-not $KeepUserData) {
    if (-not $Yes) {
        $answer = Read-Host "Delete user data under %APPDATA%\FoxDesk (and legacy CamoufoxManager)? [y/N]"
        if ($answer -notmatch '^(y|yes)$') {
            Write-Warn "kept user data"
            Write-Host "Done."
            exit 0
        }
    }
    Write-Step "Removing user data"
    foreach ($dir in @(
        "$env:APPDATA\FoxDesk",
        "$env:APPDATA\CamoufoxManager",
        "$env:LOCALAPPDATA\FoxDesk",
        "$env:LOCALAPPDATA\CamoufoxManager"
    )) {
        if (Test-Path $dir) {
            try {
                Remove-Item -LiteralPath $dir -Recurse -Force -ErrorAction Stop
                Write-Ok "removed $dir"
            } catch {
                Write-Warn "failed $dir : $_"
            }
        }
    }
} else {
    Write-Warn "KeepUserData set — left %APPDATA%\FoxDesk / CamoufoxManager intact"
}

Write-Host ""
Write-Host "Cleanup finished. You can install the latest FoxDesk Setup now." -ForegroundColor Green
