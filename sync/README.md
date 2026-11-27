# Keep a copy on your computer

Puts a folder called **India in Numbers** on your computer (Windows default: `D:\India in Numbers`; Mac: Desktop) and keeps it in sync with this repo:
every video (`videos/YYYY-MM/`), every upload text, the tracker (`TRACKER.md`, `TRACKER.csv`) and all scripts.
It syncs at log-in and every 30 minutes, only when you're online, and catches up after sleep or time offline.

**Windows**: open PowerShell and paste:
```powershell
irm https://raw.githubusercontent.com/ketu98/claude-indiainnumbers/main/sync/windows-setup.ps1 -OutFile "$env:TEMP\iin-setup.ps1"; powershell -ExecutionPolicy Bypass -File "$env:TEMP\iin-setup.ps1" -Dest 'D:\India in Numbers'
```
Change the `-Dest` folder if you like. It installs Git if needed.
**Mac**: download `mac-setup.sh`, open Terminal and run `bash ~/Downloads/mac-setup.sh`.

The synced folder is a **mirror**: edits made inside it are overwritten on the next sync. Copy a video out before editing it.
Track status on GitHub instead: each episode's Issue, labelled `ready-to-review` → `uploaded`.
