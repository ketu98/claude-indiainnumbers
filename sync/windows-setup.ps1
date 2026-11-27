# India in Numbers: keep a synced copy of the channel repo on your Desktop (Windows).
# Run once:  right-click this file > "Run with PowerShell"   (or: powershell -ExecutionPolicy Bypass -File windows-setup.ps1)
# After that it syncs at every log-in and every 30 minutes whenever you are online. Nothing else to do.
#
# The Desktop folder is a MIRROR of GitHub: anything you change inside it is overwritten on the next sync.
# Copy a video somewhere else before editing it.

$ErrorActionPreference = 'Stop'
$Repo   = 'https://github.com/ketu98/claude-indiainnumbers.git'
$Dest   = Join-Path ([Environment]::GetFolderPath('Desktop')) 'India in Numbers'
$Home2  = Join-Path $env:LOCALAPPDATA 'IndiaInNumbers'
$Sync   = Join-Path $Home2 'sync.ps1'
$Log    = Join-Path $Home2 'sync.log'

# 1. Git
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host 'Installing Git (one time)...'
    winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'Git install did not finish. Install it from https://git-scm.com/download/win and run this script again.' }
}

# 2. First copy
if (-not (Test-Path (Join-Path $Dest '.git'))) {
    Write-Host "Downloading the channel to $Dest ..."
    git clone $Repo "$Dest"
}

# 3. The sync script that runs in the background
New-Item -ItemType Directory -Force -Path $Home2 | Out-Null
@"
`$ErrorActionPreference = 'Continue'
Set-Location -LiteralPath '$Dest'
`$t = Get-Date -Format 'yyyy-MM-dd HH:mm'
git fetch --quiet origin main 2>&1 | Out-Null
if (`$LASTEXITCODE -eq 0) {
    git reset --hard --quiet origin/main
    Add-Content -LiteralPath '$Log' "`$t synced `$(git log -1 --format='%h %s')"
} else {
    Add-Content -LiteralPath '$Log' "`$t offline or GitHub unreachable, will retry"
}
"@ | Set-Content -LiteralPath $Sync -Encoding UTF8

# 4. Background task: at log-on + every 30 minutes, only when online, catches up after sleep
$action   = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$Sync`""
$triggers = @(
    (New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"),
    (New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 30))
)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName 'India in Numbers sync' -Action $action -Trigger $triggers -Settings $settings -Principal $principal -Force | Out-Null

& powershell -NoProfile -ExecutionPolicy Bypass -File $Sync
Write-Host ''
Write-Host "Done. Your copy is in: $Dest"
Write-Host 'Videos:   videos\YYYY-MM\   ·   Tracker: TRACKER.md / TRACKER.csv'
Write-Host "It syncs every 30 minutes while online. Log: $Log"
Write-Host 'To stop syncing: Task Scheduler > "India in Numbers sync" > Delete.'
