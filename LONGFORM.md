# LONGFORM — make the weekly long-form video (16:9, 5–8 minutes)

The long-form "deep dive" answers one bigger question in 4–6 chapters. It builds watch hours (a second route into YouTube's Partner Program,
since Shorts-feed watch time doesn't count toward it) and shows the depth that YouTube's reviewers look for. Same cast, same rules
(RUNBOOK.md: cast, off-limits, sourcing, anonymity of SIGMA). Follow RUNBOOK steps 1 (setup, voice bank) and 4 (research) and the steps below.

1. **Topic**: a SIGMA long-form question (`channel/sigma_script.json` section L, ids `L01`…, with a clip in the bank, not yet in the LOG `Q` column),
   else a request marked `long:` in `topics/requests.md`, else your own broad question. Prefer subjects the recent Shorts did well on
   (TRACKER.md "Views 48h" column) and expand them.

2. **Research**: 12–20 solid, sourced numbers (same standards as RUNBOOK step 4) across 4–6 angles. Compute derived numbers in Python.
   Every chapter needs at least 2 numbers, and the video needs a real narrative: what, how big, how it changed, why, what it means for an ordinary person.

3. **Write `episodes/epNN_<slug>/episode.json`** (`SCHEMA.md`, long-form section; example: `episodes/_examples/longform.json`):
   - `"kind": "long"`, `"format": "long"`, `"hook": {"text": "<clip text>", "clip": "L0N"}`, `"sigma_intro": "x01"` (or `x02`).
   - `chapters`: 4–6, each `{"title": "...", "lines": [...]}` with 6–12 lines. Add `"bridge": "x03"` (or `x04`) to one or two chapters
     where the story turns. Chapter titles ≤ 40 chars, curiosity-driven ("The trains nobody sees", not "Freight").
   - Lines: same rules as Shorts (≤ 25 words `say`, ≤ 20 words `cap`, a visual for every number, no two identical visuals in a row),
     rotating speakers naturally, with the hosts reacting to each other between numbers. Target **5–8 minutes** in total (about 45–70 lines).
   - Top-level `lines`: just the closing `cta` line. `"last_word": {"react": "rNN", "close": "x05"}` (or `x06`).
   - Title ≤ 70 chars (search words first). `description`: 3 short paragraphs (what the video answers, the 3 most striking numbers,
     a question for comments). Chapters are added automatically. `hashtags` 3–5 (no #Shorts), `youtube.tags` 12–15.

4. **Preview**: `python3 engine/make_episode.py episodes/<folder> --dry` prints the length and chapter times. Then
   `--preview` with ~9 times (hook, each chapter card, a few numbers, last word). Check `work/preview.jpg` (16:9 tiles).

5. **Render**: `python3 engine/make_episode.py episodes/<folder>` takes about 2 minutes per minute of video. It also writes a
   thumbnail (set `"thumb_text"`: 3–6 punchy words with the key number, e.g. "2 CRORE people a day"; default is the title) (`*_thumb.jpg`) and chapter times (`*_chapters.json`) into `out/`.

6. **Deliver**: SendUserFile the thumbnail (not the mp4, it's large) plus a short SendUserMessage: question, chapter list, length,
   the most striking numbers, and the Issue link once published.

7. **Publish**: as RUNBOOK step 9 (LOG line with `long` in the kind column), with `--slot Weekly`. The uploader posts it as a normal
   video (not a Short), adds the chapters to the description and sets the custom thumbnail.
