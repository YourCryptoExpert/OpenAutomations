# Register the hourly automation on Windows Task Scheduler (runs while this PC is on).
# Runs scripts/Run-Hourly.ps1 = automations + git push to GitHub.
# Run once from an elevated PowerShell:
#   powershell -ExecutionPolicy Bypass -File scripts/Register-HourlyTask.ps1
$Repo = Split-Path (Split-Path $MyInvocation.MyCommand.Path -Parent) -Parent
$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -File `"$Repo\scripts\Run-Hourly.ps1`"" -WorkingDirectory $Repo
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(5) -RepetitionInterval (New-TimeSpan -Hours 1)
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName "OpenAutomations-Hourly" -Action $Action -Trigger $Trigger -Settings $Settings -Force
Write-Output "Registered OpenAutomations-Hourly -> $Repo"
