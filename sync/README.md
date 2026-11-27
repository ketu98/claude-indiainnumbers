# Keep a copy on your computer

Puts a folder called **India in Numbers** on your Desktop and keeps it in sync with this repo:
every video (`videos/YYYY-MM/`), every upload text, the tracker (`TRACKER.md`, `TRACKER.csv`) and all scripts.
It syncs at log-in and every 30 minutes, only when you're online, and catches up after sleep or time offline.

**Windows**: download `windows-setup.ps1`, right-click it, choose **Run with PowerShell**. It installs Git if needed.
**Mac**: download `mac-setup.sh`, open Terminal and run `bash ~/Downloads/mac-setup.sh`.

The Desktop folder is a **mirror**: edits made inside it are overwritten on the next sync. Copy a video out before editing it.
Track status on GitHub instead: each episode's Issue, labelled `ready-to-review` → `uploaded`.
