# India in Numbers: keep a synced copy of the channel repo on your computer (Windows).
# Run once:  powershell -ExecutionPolicy Bypass -File windows-setup.ps1 [-Dest 'D:\India in Numbers']
# Default folder: D:\India in Numbers (falls back to the Desktop if there is no D: drive).
# Run it again with another -Dest to move the synced copy; the background task then follows the new folder.
# After that it syncs at every log-in and every 30 minutes whenever you are online. Nothing else to do.
#
# The synced folder is a MIRROR of GitHub: files that come from GitHub are reset on every sync, so copy a video
# somewhere else before editing it. Your own extra files in the folder are left alone.

param([string]$Dest = '')
$ErrorActionPreference = 'Stop'
$Repo   = 'https://github.com/ketu98/claude-indiainnumbers.git'
if (-not $Dest) {
    if (Test-Path 'D:\') { $Dest = 'D:\India in Numbers' }
    else { $Dest = Join-Path ([Environment]::GetFolderPath('Desktop')) 'India in Numbers' }
}
$drive = [System.IO.Path]::GetPathRoot($Dest)
if (-not (Test-Path -LiteralPath $drive)) { throw "The drive '$drive' does not exist. Pick another -Dest." }
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Dest) | Out-Null
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
    $hasFiles = (Test-Path -LiteralPath $Dest) -and @(Get-ChildItem -LiteralPath $Dest -Force -ErrorAction SilentlyContinue).Count -gt 0
    if (-not $hasFiles) {
        git clone $Repo "$Dest"
    } else {
        # Folder already has your own files: set up in place and leave them alone (they are never deleted by the sync).
        git -C "$Dest" init --quiet
        git -C "$Dest" remote add origin $Repo
        git -C "$Dest" fetch --quiet origin main
        git -C "$Dest" checkout --quiet -f -B main --track origin/main
    }
    if (-not (Test-Path (Join-Path $Dest '.git'))) { throw "Download failed. Check your internet connection and run this again." }
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
