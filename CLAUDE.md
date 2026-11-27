# India in Numbers — channel pipeline

This repo makes YouTube Shorts for **India in Numbers** (@IndiaInNumbersPanel).

- To make the daily Short, follow **RUNBOOK.md** step by step. Weekly long-form (16:9): **LONGFORM.md**.
- **SIGMA (Σ)** is the anonymous narrator: pre-recorded clips in the PRIVATE repo `ketu98/iin-voice-bank` (`engine/voice_bank.py`,
  script `channel/sigma_script.json`, guide `channel/SIGMA_RECORDING.md`). Never name or hint at the person behind SIGMA, never write the
  owner's name in this public repo, never copy voice clips into it.
- Episode file format: **SCHEMA.md**. Working examples: `episodes/ep01…ep03`.
- Engine: `engine/make_episode.py` (render Shorts and long-form), `engine/clean_voice.py` (one-off recording cleanup). Setup: `bash setup.sh`.
- Topic ideas: `topics/backlog.md`. Owner's pitches: Issues labelled `idea` (form: "💡 Episode idea") come first, then `topics/requests.md`. History: `episodes/LOG.md`.
- Review flow: every episode gets a GitHub Issue (labels `ready-to-review` → `scheduled` → `uploaded`, or `needs-fix` / `skipped` / `upload-failed`), its video in `videos/YYYY-MM/`, and a row in `TRACKER.md` (built by `engine/publish_github.py` and the uploader).
- YouTube posting is done **only** by the GitHub workflow `.github/workflows/youtube.yml` (`engine/youtube_upload.py`, settings `channel/youtube.json`, setup `channel/YOUTUBE_SETUP.md`), which the owner authorized. It picks up every `ready-to-review` episode by itself.
- Local copy on the owner's computer: `sync/` scripts keep a mirror of this repo on the owner's computer.
- Claude sessions never upload or post anything themselves, never run `youtube_upload.py` without `--dry-run`, and never touch the YouTube secrets.
