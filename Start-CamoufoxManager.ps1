# Legacy launcher name — prefer Start-FoxDesk.ps1
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
& "$PSScriptRoot\Start-FoxDesk.ps1"
