# Hourly wrapper: run automations, then push data/ to GitHub. Called by Task Scheduler.
# Manual run: powershell -ExecutionPolicy Bypass -File scripts/Run-Hourly.ps1
$ErrorActionPreference = "Stop"
$Repo = Split-Path (Split-Path $MyInvocation.MyCommand.Path -Parent) -Parent
Set-Location -LiteralPath $Repo

$Py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $Py) { $Py = (Get-Command py -ErrorAction SilentlyContinue).Source }
if (-not $Py) { throw "Python not found on PATH." }

$prevEAP = $ErrorActionPreference
$ErrorActionPreference = "Continue"
try {
  & $Py scripts/run_all.py
  $pyCode = $LASTEXITCODE
} finally {
  $ErrorActionPreference = $prevEAP
}
if ($pyCode -ne 0) { throw "run_all.py failed with exit $pyCode." }

& powershell -ExecutionPolicy Bypass -File "$Repo/scripts/Push-ToGitHub.ps1"
