# Start the crypto desktop widget at Windows login (no console window).
# Run once: powershell -ExecutionPolicy Bypass -File scripts/Register-WidgetStartup.ps1
# Remove: delete "CryptoWidget" from shell:startup (or Task Manager > Startup apps).
$Repo = Split-Path (Split-Path $MyInvocation.MyCommand.Path -Parent) -Parent
$Pyw = (Get-Command pythonw -ErrorAction SilentlyContinue).Source
if (-not $Pyw) { $Pyw = Join-Path (Split-Path (Get-Command python).Source -Parent) "pythonw.exe" }
if (-not (Test-Path -LiteralPath $Pyw)) { throw "pythonw.exe not found." }

$Startup = [System.IO.Path]::Combine($env:APPDATA, "Microsoft\Windows\Start Menu\Programs\Startup")
$Link = Join-Path $Startup "CryptoWidget.lnk"
$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($Link)
$Shortcut.TargetPath = $Pyw
$Shortcut.Arguments = "`"crypto_widget.py`""
$Shortcut.WorkingDirectory = (Join-Path $Repo "scripts")
$Shortcut.Description = "Robinhood trending crypto desktop widget"
$Shortcut.Save()
Write-Output "Widget will start at login: $Link"
