# Push hourly automation output to GitHub.
# Safe to run every hour: commits only if data/ changed, never force-pushes.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts/Push-ToGitHub.ps1
#   powershell -ExecutionPolicy Bypass -File scripts/Push-ToGitHub.ps1 -AddAll
#
# First-time setup (one time only, NOT hourly):
#   gh auth login
#   git config --global user.name "Your Name"
#   git config --global user.email "you@example.com"
#   gh repo create OpenAutomations --public --source=. --push
#   # or: git remote add origin https://github.com/<you>/OpenAutomations.git
param([switch]$AddAll)

$ErrorActionPreference = "Stop"
$Repo = Split-Path (Split-Path $MyInvocation.MyCommand.Path -Parent) -Parent
Set-Location -LiteralPath $Repo

# NOTE (PowerShell 5.1): native stderr (git errors/warnings) becomes a
# terminating error when $ErrorActionPreference is "Stop" -- even for
# harmless warnings like LF/CRLF notices. So every git call below runs
# under "Continue" and is checked via $LASTEXITCODE instead.
function Invoke-Git([string[]]$GitArgs, [switch]$Quiet) {
  $prev = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    if ($Quiet) { git @GitArgs 2>$null | Out-Null }
    else { git @GitArgs }
    return $LASTEXITCODE
  } finally {
    $ErrorActionPreference = $prev
  }
}

# 1. Must be a git repo with an 'origin' remote (checked BEFORE staging anything).
if ((Invoke-Git @("rev-parse", "--is-inside-work-tree") -Quiet) -ne 0) { throw "Not a git repo: $Repo" }
if ((Invoke-Git @("remote", "get-url", "origin") -Quiet) -ne 0) {
  throw "No 'origin' remote. One-time setup: gh repo create OpenAutomations --public --source=. --push"
}

# 2. First commit must be manual so scripts/workflows are included, not just data/.
if ((Invoke-Git @("rev-parse", "HEAD") -Quiet) -ne 0) {
  throw "No commits yet. One-time setup: git add -A; git commit -m 'initial commit'; git push -u origin <branch>"
}

# 3. Stage: by default only data/ (automation output). -AddAll also stages scripts/workflows.
if ($AddAll) { $code = Invoke-Git @("add", "-A") } else { $code = Invoke-Git @("add", "--", "data/") }
if ($code -ne 0) { throw "git add failed." }

# 4. Nothing to do if no staged changes (normal for most hourly runs).
# git diff --quiet exits 1 when differences exist and writes nothing, so it is
# safe to call directly: no stderr means no 5.1 error-record issue.
git diff --cached --quiet
if ($LASTEXITCODE -eq 0) { Write-Output "No changes to push."; exit 0 }

# 5. Commit with UTC timestamp. Uses your git identity; falls back to a
# per-commit bot identity (nothing persisted) so unattended hourly runs
# don't fail on machines without git configured.
$stamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mmZ")
if ((Invoke-Git @("config", "user.email") -Quiet) -eq 0) {
  $code = Invoke-Git @("commit", "-m", "hourly data $stamp")
} else {
  Write-Output "No git identity configured; committing as hourly-bot (this commit only)."
  $code = Invoke-Git @("-c", "user.name=hourly-bot", "-c", "user.email=hourly-bot@users.noreply.github.com", "commit", "-m", "hourly data $stamp")
}
if ($code -ne 0) { throw "git commit failed." }

# 6. Push current branch to origin (sets upstream on first run). No --force ever.
$prevEAP = $ErrorActionPreference
$ErrorActionPreference = "Continue"
try { $branch = (git branch --show-current 2>$null).Trim() } finally { $ErrorActionPreference = $prevEAP }
if (-not $branch) { $branch = "master" }
if ((Invoke-Git @("rev-parse", "--abbrev-ref", "@{u}") -Quiet) -ne 0) {
  $code = Invoke-Git @("push", "-u", "origin", $branch)
} else {
  $code = Invoke-Git @("push", "origin", $branch)
}
if ($code -ne 0) { throw "git push failed. Check 'gh auth status' and remote permissions." }
Write-Output "Pushed $branch to origin."
