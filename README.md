# India in Numbers

Code and scripts for the YouTube channel **India in Numbers** (@IndiaInNumbersPanel): short, data-driven videos
about life in India, presented by the panel: VEDA, REGINALD and TARA.

- `RUNBOOK.md`: how each episode is made
- `SCHEMA.md`: episode script format
- `engine/`: the video engine (Python, Pillow, ffmpeg, Kokoro open-source voices)
- **`TRACKER.md`**: every episode with status, video and review links (newest first)
- `videos/YYYY-MM/`: every finished video + upload text, named by date and time (IST)
- `episodes/`: one folder per episode (script, upload text, sources)
- `sync/`: keep a synced copy on your computer's Desktop (Windows / Mac)
- Issues: one per episode, labelled `ready-to-review` → `scheduled` → `uploaded` (or `needs-fix` / `skipped` / `upload-failed`)
- **YouTube posting is automatic**: `.github/workflows/youtube.yml` + `engine/youtube_upload.py`. One-time setup: `channel/YOUTUBE_SETUP.md`
- `topics/`: topic backlog and requests
- `channel/`: profile picture, banner and channel setup text
