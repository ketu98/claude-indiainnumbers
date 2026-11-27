# India in Numbers — channel pipeline

This repo makes YouTube Shorts for **India in Numbers** (@IndiaInNumbersPanel).

- To make an episode, follow **RUNBOOK.md** step by step.
- Episode file format: **SCHEMA.md**. Working examples: `episodes/ep01…ep03`.
- Engine: `engine/make_episode.py` (render), `engine/clean_voice.py` (narrator voice cleanup). Setup: `bash setup.sh`.
- Topic ideas: `topics/backlog.md`. Owner requests: `topics/requests.md`. History: `episodes/LOG.md`.
- Review flow: every episode gets a GitHub Issue (labels `ready-to-review` → `uploaded` / `needs-fix` / `skipped`), its video in `videos/YYYY-MM/`, and a row in `TRACKER.md` (built by `engine/publish_github.py`).
- Local copy on Aniket's computer: `sync/` scripts keep a mirror of this repo on his Desktop.
- Never upload or post anything. Aniket reviews and uploads every video himself.
